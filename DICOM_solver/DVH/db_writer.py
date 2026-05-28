import json
import logging


INSERT_DVH_ROW = """
INSERT INTO dvh_results (
    patient_id, study_uid, structure_name,
    min_dose_gy, mean_dose_gy, max_dose_gy, volume_cc,
    color, metrics, dvh_points, payload,
    rt_plan_path, rt_dose_paths, effective_dose_type
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def _scalar(struct_out, key):
    entry = struct_out.get(key)
    return entry.get("value") if isinstance(entry, dict) else None


def _metrics(struct_out):
    out = {}
    for key, entry in struct_out.items():
        if isinstance(entry, dict) and (key.startswith("V") or key.startswith("D")):
            value = entry.get("value")
            if value is not None:
                out[key] = value
    return out


def _curve(struct_out):
    curve = struct_out.get("dvh_curve") or {}
    return curve.get("dvh_points") or []


def save_dvh_to_db(db, patient_id, study_uid, output,
                   rt_plan_path=None, rt_dose_paths=None, effective_dose_type=None):
    if not output:
        logging.info("save_dvh_to_db: empty output, nothing to save")
        return
    dose_paths_json = json.dumps(rt_dose_paths) if rt_dose_paths is not None else None
    for struct_out in output:
        try:
            params = (
                patient_id,
                study_uid,
                struct_out.get("structureName"),
                _scalar(struct_out, "min"),
                _scalar(struct_out, "mean"),
                _scalar(struct_out, "max"),
                _scalar(struct_out, "volume"),
                struct_out.get("color"),
                json.dumps(_metrics(struct_out)),
                json.dumps(_curve(struct_out)),
                json.dumps(struct_out),
                rt_plan_path,
                dose_paths_json,
                effective_dose_type,
            )
            db.execute_query(INSERT_DVH_ROW, params)
        except Exception:
            sname = struct_out.get("structureName")
            logging.error(
                f"Failed to insert DVH row for patient={patient_id} structure={sname}",
                exc_info=True,
            )
