import copy
import logging
from dataclasses import dataclass
from typing import List

import numpy as np
from dicompylercore.dicomparser import DicomParser


@dataclass
class EffectiveDose:
    """One dose grid suitable for a single DVH calculation.

    Produced by ``analyze_doses``. May be an existing dose (when only one
    PLAN/SINGLE dose is involved) or a synthetic dose (when multiple BEAM
    or FRACTION doses had to be summed).
    """
    type: str                  # SINGLE, PLAN, BEAM, FRACTION, SUMMED_BEAM, SUMMED_FRACTION, FALLBACK
    dose_parser: DicomParser   # ready to feed into dvhcalc
    source_paths: List[str]    # the RT Dose file paths that contributed
    description: str = ""


def _group_by_summation_type(parsers, paths):
    """Group dose parsers + paths by their DICOM DoseSummationType."""
    groups = {}
    for parser, path in zip(parsers, paths):
        st = getattr(parser.ds, "DoseSummationType", "UNKNOWN")
        groups.setdefault(st, []).append((parser, path))
    return groups


def _can_sum(parsers):
    """Triage doses for summation.

    Returns a tuple ``(mode, reason)``:
      - ``("exact", None)``     : all doses share FrameOfReferenceUID AND grid; sum directly.
      - ``("resample", None)``  : FrameOfReferenceUID matches but grids differ; resample + sum.
      - ``("reject", reason)``  : FrameOfReferenceUID differs (or another fatal mismatch).
    """
    if len(parsers) <= 1:
        return "exact", None

    ref = parsers[0].ds
    ref_for = getattr(ref, "FrameOfReferenceUID", None)
    for p in parsers[1:]:
        if getattr(p.ds, "FrameOfReferenceUID", None) != ref_for:
            return (
                "reject",
                "Frame of Reference UIDs differ; doses cannot be summed without spatial registration",
            )

    ref_shape = ref.pixel_array.shape
    ref_origin = list(ref.ImagePositionPatient)
    ref_spacing = (
        float(ref.SliceThickness),
        float(ref.PixelSpacing[0]),
        float(ref.PixelSpacing[1]),
    )
    for p in parsers[1:]:
        ds = p.ds
        if ds.pixel_array.shape != ref_shape:
            return "resample", None
        if list(ds.ImagePositionPatient) != ref_origin:
            return "resample", None
        ds_spacing = (
            float(ds.SliceThickness),
            float(ds.PixelSpacing[0]),
            float(ds.PixelSpacing[1]),
        )
        if ds_spacing != ref_spacing:
            return "resample", None

    return "exact", None


def _build_target_grid(parsers):
    """Build the target grid: finest spacing per axis, covering the union of extents.

    Returns dict with:
      - ``origin``  : (x, y, z) physical coordinates of voxel (0, 0, 0) center
      - ``spacing`` : (z, y, x) — matches numpy axis order of pixel_array
      - ``shape``   : (nz, ny, nx)
    """
    finest_z = float("inf")
    finest_y = float("inf")
    finest_x = float("inf")
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    for p in parsers:
        ds = p.ds
        origin = [float(c) for c in ds.ImagePositionPatient]
        z_sp = float(ds.SliceThickness)
        y_sp = float(ds.PixelSpacing[0])
        x_sp = float(ds.PixelSpacing[1])
        shape = ds.pixel_array.shape  # (nz, ny, nx)

        finest_z = min(finest_z, z_sp)
        finest_y = min(finest_y, y_sp)
        finest_x = min(finest_x, x_sp)

        end_x = origin[0] + (shape[2] - 1) * x_sp
        end_y = origin[1] + (shape[1] - 1) * y_sp
        end_z = origin[2] + (shape[0] - 1) * z_sp

        min_x = min(min_x, origin[0])
        max_x = max(max_x, end_x)
        min_y = min(min_y, origin[1])
        max_y = max(max_y, end_y)
        min_z = min(min_z, origin[2])
        max_z = max(max_z, end_z)

    nx = int(np.ceil((max_x - min_x) / finest_x)) + 1
    ny = int(np.ceil((max_y - min_y) / finest_y)) + 1
    nz = int(np.ceil((max_z - min_z) / finest_z)) + 1

    return {
        "origin": (min_x, min_y, min_z),
        "spacing": (finest_z, finest_y, finest_x),
        "shape": (nz, ny, nx),
    }


def _resample_to_grid(parser, target):
    """Trilinearly resample one dose onto the target grid. Returns a Gy array of shape target['shape']."""
    import scipy.ndimage as ndi

    ds = parser.ds
    src_origin = [float(c) for c in ds.ImagePositionPatient]
    src_z_sp = float(ds.SliceThickness)
    src_y_sp = float(ds.PixelSpacing[0])
    src_x_sp = float(ds.PixelSpacing[1])
    src_gy = ds.pixel_array.astype(np.float64) * float(ds.DoseGridScaling)

    target_origin = target["origin"]
    target_spacing = target["spacing"]
    target_shape = target["shape"]

    iz, iy, ix = np.indices(target_shape, dtype=np.float64)
    phys_x = target_origin[0] + ix * target_spacing[2]
    phys_y = target_origin[1] + iy * target_spacing[1]
    phys_z = target_origin[2] + iz * target_spacing[0]

    src_kz = (phys_z - src_origin[2]) / src_z_sp
    src_jy = (phys_y - src_origin[1]) / src_y_sp
    src_kx = (phys_x - src_origin[0]) / src_x_sp

    coords = np.stack([src_kz, src_jy, src_kx])
    return ndi.map_coordinates(src_gy, coords, order=1, mode="constant", cval=0.0)


def _encode_summed_dose(template_ds, summed_gy):
    """Encode a Gy array back into PixelData on ``template_ds`` and return a fresh DicomParser."""
    bits = int(getattr(template_ds, "BitsAllocated", 32))
    if bits == 16:
        pixel_dtype = np.uint16
        max_pixel_value = (1 << 16) - 1
    else:
        pixel_dtype = np.uint32
        max_pixel_value = (1 << 32) - 1

    max_dose = float(summed_gy.max())
    new_scaling = max_dose / max_pixel_value if max_dose > 0 else 1e-6
    new_pixels = (summed_gy / new_scaling).astype(pixel_dtype)

    template_ds.PixelData = new_pixels.tobytes()
    template_ds.DoseGridScaling = new_scaling
    template_ds.DoseSummationType = "PLAN"

    if hasattr(template_ds, "_pixel_array"):
        template_ds._pixel_array = None

    return DicomParser(template_ds)


def _sum_same_grid(dose_parsers):
    """Fast path: voxel-wise sum of already-aligned doses."""
    ref_ds = dose_parsers[0].ds
    summed_gy = np.zeros(ref_ds.pixel_array.shape, dtype=np.float64)
    for d in dose_parsers:
        ds = d.ds
        summed_gy += ds.pixel_array.astype(np.float64) * float(ds.DoseGridScaling)
    return _encode_summed_dose(copy.deepcopy(ref_ds), summed_gy)


def _sum_with_resampling(dose_parsers):
    """Build the finest-per-axis target grid covering the union of extents, then resample + sum."""
    target = _build_target_grid(dose_parsers)
    summed_gy = np.zeros(target["shape"], dtype=np.float64)
    for p in dose_parsers:
        summed_gy += _resample_to_grid(p, target)

    template_ds = copy.deepcopy(dose_parsers[0].ds)
    template_ds.ImagePositionPatient = [
        float(target["origin"][0]),
        float(target["origin"][1]),
        float(target["origin"][2]),
    ]
    template_ds.SliceThickness = float(target["spacing"][0])
    template_ds.PixelSpacing = [float(target["spacing"][1]), float(target["spacing"][2])]
    template_ds.Rows = int(target["shape"][1])
    template_ds.Columns = int(target["shape"][2])
    template_ds.NumberOfFrames = int(target["shape"][0])
    template_ds.GridFrameOffsetVector = [
        float(i * target["spacing"][0]) for i in range(target["shape"][0])
    ]
    return _encode_summed_dose(template_ds, summed_gy)


def sum_doses(dose_parsers):
    """Sum multiple RT Dose objects into a synthetic ``DicomParser``.

    Strategy:
      - 1 dose                       -> returned as-is.
      - Multiple doses, same FoR + same grid     -> direct voxel-wise sum.
      - Multiple doses, same FoR + different grids -> build a target grid with finest
        per-axis spacing covering the union of extents, resample each dose with
        trilinear interpolation, then sum.
      - Multiple doses, different FoR -> raises ValueError.
    """
    if not dose_parsers:
        raise ValueError("Cannot sum: no doses provided")
    if len(dose_parsers) == 1:
        return dose_parsers[0]

    mode, reason = _can_sum(dose_parsers)
    if mode == "reject":
        raise ValueError(f"Cannot sum doses: {reason}")
    if mode == "exact":
        return _sum_same_grid(dose_parsers)
    return _sum_with_resampling(dose_parsers)


def analyze_doses(rt_dose_parsers, rt_dose_paths):
    """Triage RT Dose files into a list of effective doses for DVH calculation.

    Triage rules (based on DICOM ``DoseSummationType``):
      - 1 dose                       -> 1 effective dose (used as-is).
      - Multiple doses:
        (a) Any PLAN doses           -> one effective dose per PLAN (independent).
        (b) Only BEAM / FRACTION     -> sum them; one effective dose for the sum.
        (c) Mixed (PLAN + BEAM/FX)   -> PLAN(s) untouched + summed BEAM/FX as
                                       additional effective doses.
        (d) Unknown / unclassified   -> first dose as fallback, with warning.
    """
    if not rt_dose_parsers:
        return []

    if len(rt_dose_parsers) == 1:
        return [EffectiveDose(
            type="SINGLE",
            dose_parser=rt_dose_parsers[0],
            source_paths=[rt_dose_paths[0]],
            description="Single dose",
        )]

    groups = _group_by_summation_type(rt_dose_parsers, rt_dose_paths)
    results = []

    for parser, path in groups.get("PLAN", []):
        results.append(EffectiveDose(
            type="PLAN",
            dose_parser=parser,
            source_paths=[path],
            description=f"PLAN dose: {path}",
        ))

    beam = groups.get("BEAM", [])
    if beam:
        try:
            if len(beam) == 1:
                logging.warning("Single BEAM dose with no PLAN sibling; using as-is")
                results.append(EffectiveDose(
                    type="BEAM",
                    dose_parser=beam[0][0],
                    source_paths=[beam[0][1]],
                    description="Single BEAM dose",
                ))
            else:
                summed = sum_doses([p for p, _ in beam])
                results.append(EffectiveDose(
                    type="SUMMED_BEAM",
                    dose_parser=summed,
                    source_paths=[path for _, path in beam],
                    description=f"Sum of {len(beam)} BEAM doses",
                ))
        except Exception:
            logging.error("Failed to handle BEAM doses", exc_info=True)

    fraction = groups.get("FRACTION", [])
    if fraction:
        try:
            if len(fraction) == 1:
                results.append(EffectiveDose(
                    type="FRACTION",
                    dose_parser=fraction[0][0],
                    source_paths=[fraction[0][1]],
                    description="Single FRACTION dose",
                ))
            else:
                summed = sum_doses([p for p, _ in fraction])
                results.append(EffectiveDose(
                    type="SUMMED_FRACTION",
                    dose_parser=summed,
                    source_paths=[path for _, path in fraction],
                    description=f"Sum of {len(fraction)} FRACTION doses",
                ))
        except Exception:
            logging.error("Failed to handle FRACTION doses", exc_info=True)

    if not results:
        other = [pp for ppls in groups.values() for pp in ppls]
        if other:
            parser, path = other[0]
            logging.warning(
                f"No recognized DoseSummationType; falling back to first dose: {path}"
            )
            results.append(EffectiveDose(
                type="FALLBACK",
                dose_parser=parser,
                source_paths=[path],
                description=f"Fallback (unclassified): {path}",
            ))

    return results
