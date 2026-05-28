import pandas as pd
from ..dvh_processor import connect_db, verify_full, collect_patients_dicom, calculate_dvh_curves
from ..Config.global_var import QUERY_PATIENT
import logging
import traceback


class DataAPI:
    def __init__(self):
        self.df = None
        self.db = connect_db()

    def get_data_api(self, patient_id):

        try:
            self.df = pd.read_sql_query(QUERY_PATIENT, self.db.conn, params=(patient_id,))
        except Exception as e:
            raise e

    def dvh_api(self, structure_name):
        if not verify_full(self.df):
            return None
        dicom_bundles = collect_patients_dicom(self.df)
        if not dicom_bundles:
            return None

        for dicom_bundle in dicom_bundles:
            try:
                res = calculate_dvh_curves(dicom_bundle, str_name=structure_name, gdp=False)
            except Exception as e:
                logging.warning(
                    f"Bundle for patient {dicom_bundle.patient_id} failed: {e}"
                )
                logging.warning(traceback.format_exc())
                continue
            if res:
                eff_type = getattr(dicom_bundle, "effective_dose_type", "unknown")
                logging.info(
                    f"DVH for patient {dicom_bundle.patient_id} "
                    f"structure '{structure_name}' found "
                    f"(effective_dose_type={eff_type})"
                )
                return res

        logging.warning(
            f"No bundle yielded a DVH for structure '{structure_name}'"
        )
        return None

    def close(self):
        if self.db:
            self.db.disconnect()
