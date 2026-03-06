#!/usr/bin/env python
# ruff: noqa: T201
import os

os.environ.setdefault("UPLOAD_DESTINATION", "")
os.environ.setdefault("DELETE_END", "false")

import argparse
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import pydicom

from DICOM_solver.DVH.dicom_bundle import DicomBundle
from DICOM_solver.DVH.dvh import DVH_calculation
from DICOM_solver.dvh_processor import combine

REQUIRED_MODALITIES = {"CT", "RTSTRUCT", "RTPLAN", "RTDOSE"}


def scan_dicom_files(data_path):
    studies = defaultdict(lambda: defaultdict(list))
    for root, _, files in os.walk(data_path):
        for fname in files:
            if not fname.lower().endswith(".dcm"):
                continue
            fpath = os.path.join(root, fname)
            try:
                ds = pydicom.dcmread(fpath, stop_before_pixels=True)
                uid = str(getattr(ds, "StudyInstanceUID", "UNKNOWN"))
                modality = str(getattr(ds, "Modality", "UNKNOWN"))
                studies[uid][modality].append(fpath)
            except Exception as e:
                print(f"  [warn] could not read {fpath}: {e}", file=sys.stderr)
    return studies


def build_bundles(uid, modalities):
    ct_files = modalities.get("CT", [])
    structs = modalities.get("RTSTRUCT", [])
    plans = modalities.get("RTPLAN", [])
    doses = modalities.get("RTDOSE", [])

    if not (ct_files and structs and plans and doses):
        missing = REQUIRED_MODALITIES - {m for m, v in modalities.items() if v}
        return None, f"missing modalities: {', '.join(sorted(missing))}"

    bundles = []
    for plan_path in plans:
        try:
            plan_ds = pydicom.dcmread(plan_path, stop_before_pixels=True)
            plan_sop = str(plan_ds.SOPInstanceUID)
            linked_doses = []
            for dose_path in doses:
                dose_ds = pydicom.dcmread(dose_path, stop_before_pixels=True)
                refs = getattr(dose_ds, "ReferencedRTPlanSequence", [])
                if refs and str(refs[0].ReferencedSOPInstanceUID) == plan_sop:
                    linked_doses.append(dose_path)
            if not linked_doses:
                linked_doses = doses
            patient_id = str(getattr(plan_ds, "PatientID", uid))
            bundle = DicomBundle(
                patient_id=patient_id,
                rt_plan=plan_path,
                rt_struct=structs[0],
                rt_dose=linked_doses,
                rt_ct=ct_files[0],
            )
            bundles.append(bundle)
        except Exception as e:
            return None, str(e)
    return bundles, None


def process_bundle(bundle):
    bundle = combine(bundle)
    structures = bundle.rt_struct.GetStructures()
    dvh_c = DVH_calculation()
    dvh_c.calculate_dvh_all(bundle, structures)


def run_study(uid, modalities, repeat):
    bundles, err = build_bundles(uid, modalities)
    if err:
        return uid, None, err

    start = time.monotonic()
    for _ in range(repeat):
        for bundle in bundles:
            process_bundle(bundle)
    elapsed = time.monotonic() - start
    return uid, elapsed, None


def main():
    parser = argparse.ArgumentParser(description="Standalone DVH Consumer load test")
    parser.add_argument("--data-path", required=True, help="Directory to scan for .dcm files")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent processing threads")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each study N times")
    args = parser.parse_args()

    print(f"Scanning {args.data_path} ...")
    studies = scan_dicom_files(args.data_path)
    print(f"Found {len(studies)} study(s)\n")

    complete = {}
    skipped = {}
    for uid, modalities in studies.items():
        present = {m for m, v in modalities.items() if v}
        if REQUIRED_MODALITIES.issubset(present):
            complete[uid] = modalities
        else:
            missing = REQUIRED_MODALITIES - present
            skipped[uid] = f"missing: {', '.join(sorted(missing))}"

    for uid, reason in skipped.items():
        print(f"  [skip] {uid[:20]}... — {reason}")
    if skipped:
        print()

    if not complete:
        print("No complete studies to process.")
        return

    timings = []
    errors = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_study, uid, modalities, args.repeat): uid for uid, modalities in complete.items()
        }
        for future in as_completed(futures):
            uid, elapsed, err = future.result()
            short = uid[:20] + "..."
            if err:
                print(f"  [error] {short} — {err}")
                errors.append((uid, err))
            else:
                print(f"  [done]  {short}  {elapsed:.2f}s")
                timings.append((uid, elapsed))

    print()
    print("=" * 55)
    print("Summary")
    print("=" * 55)
    total = len(timings) + len(errors)
    print(f"  Studies attempted : {total}")
    print(f"  Completed         : {len(timings)}")
    print(f"  Errors            : {len(errors)}")

    if timings:
        times = [t for _, t in timings]
        total_time = sum(times)
        mean_time = total_time / len(times)
        throughput = len(times) / total_time if total_time > 0 else 0
        slowest_uid, slowest_time = max(timings, key=lambda x: x[1])
        print(f"  Total wall time   : {total_time:.2f}s")
        print(f"  Mean per study    : {mean_time:.2f}s")
        print(f"  Throughput        : {throughput:.3f} studies/s")
        print(f"  Slowest study     : {slowest_uid[:20]}... ({slowest_time:.2f}s)")
        outliers = [(uid, t) for uid, t in timings if t > 2 * mean_time]
        if outliers:
            print("  Outliers (>2x mean):")
            for uid, t in outliers:
                print(f"    {uid[:20]}... {t:.2f}s")
    print("=" * 55)


if __name__ == "__main__":
    main()
