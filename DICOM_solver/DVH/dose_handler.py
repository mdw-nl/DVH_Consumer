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


def _grids_compatible(parsers):
    """True if all parsers share the same dose grid (shape, origin, spacing)."""
    if len(parsers) <= 1:
        return True
    ref = parsers[0].ds
    ref_shape = ref.pixel_array.shape
    ref_origin = list(ref.ImagePositionPatient)
    ref_spacing = list(ref.PixelSpacing)
    for p in parsers[1:]:
        ds = p.ds
        if ds.pixel_array.shape != ref_shape:
            return False
        if list(ds.ImagePositionPatient) != ref_origin:
            return False
        if list(ds.PixelSpacing) != ref_spacing:
            return False
    return True


def sum_doses(dose_parsers):
    """Sum multiple RT Dose objects with matching grids.

    Returns a synthetic ``DicomParser`` whose pixel data is the voxel-wise sum
    of the inputs (converted to Gy first via each dose's ``DoseGridScaling``).

    Requires all input doses to share the same grid (shape, origin, spacing).
    Raises ``ValueError`` if grids differ. Resampling for mismatched grids is
    not implemented yet.
    """
    if not dose_parsers:
        raise ValueError("Cannot sum: no doses provided")
    if len(dose_parsers) == 1:
        return dose_parsers[0]
    if not _grids_compatible(dose_parsers):
        raise ValueError(
            "Cannot sum doses with mismatched grids; resampling not implemented"
        )

    ref_ds = dose_parsers[0].ds
    summed_gy = np.zeros(ref_ds.pixel_array.shape, dtype=np.float64)
    for d in dose_parsers:
        ds = d.ds
        scaling = float(ds.DoseGridScaling)
        summed_gy += ds.pixel_array.astype(np.float64) * scaling

    new_ds = copy.deepcopy(ref_ds)
    bits = int(getattr(ref_ds, "BitsAllocated", 32))
    if bits == 16:
        pixel_dtype = np.uint16
        max_pixel_value = (1 << 16) - 1
    else:
        pixel_dtype = np.uint32
        max_pixel_value = (1 << 32) - 1

    max_dose = float(summed_gy.max())
    new_scaling = max_dose / max_pixel_value if max_dose > 0 else 1e-6
    new_pixels = (summed_gy / new_scaling).astype(pixel_dtype)

    new_ds.PixelData = new_pixels.tobytes()
    new_ds.DoseGridScaling = new_scaling
    new_ds.DoseSummationType = "PLAN"

    # Invalidate pydicom's pixel_array cache so consumers re-decode from PixelData.
    if hasattr(new_ds, "_pixel_array"):
        new_ds._pixel_array = None

    return DicomParser(new_ds)


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
