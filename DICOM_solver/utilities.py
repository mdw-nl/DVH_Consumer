import logging
import os
from .config_handler import Config
from .PostgresInterface import PostgresInterface
from .Config.global_var import QUERY_UID
import pandas as pd


def connect_db():
    postgres_config = Config("postgres")
    if postgres_config is None:
        raise Exception("Postgres config is None")

    config_dict_db = postgres_config.config
    host, port, user, pwd, db = config_dict_db["host"], config_dict_db["port"], \
        config_dict_db["username"], config_dict_db["password"], config_dict_db["db"]
    db = PostgresInterface(host=host, database=db, user=user, password=pwd, port=port)
    db.connect()
    logging.info("Connected to the database")

    return db

def get_all_uid(db, uid):
    """

    :param db:
    :param uid:
    :return:
    """
    try:
        df = pd.read_sql_query(QUERY_UID, db.conn,params=(uid,))
    except Exception as e:
        raise e
    return df


def verify_bundle(dicom_bundle):
    """
    Verify that the dicom bundle component path exist using os
    :param dicom_bundle:
    :return:
    """
    logging.info(f"Verifying DicomBundle for patient {dicom_bundle.patient_id}")
    logging.info(f"RT Plan path: {dicom_bundle.rt_plan_path}")
    logging.info(f"RT Struct path: {dicom_bundle.rt_struct_path}")
    logging.info(f"RT Dose path: {dicom_bundle.rt_dose_path}")
    if not dicom_bundle.rt_plan_path or not dicom_bundle.rt_struct_path:
        logging.warning("Missing RT Plan, RT Struct  path in the DicomBundle")
        return False
    if not os.path.exists(dicom_bundle.rt_plan_path):
        logging.warning(f"RT Plan file does not exist: {dicom_bundle.rt_plan_path}")
        return False
    if not os.path.exists(dicom_bundle.rt_struct_path):
        logging.warning(f"RT Struct file does not exist: {dicom_bundle.rt_struct_path}")
        return False
    return True
