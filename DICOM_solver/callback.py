import logging
from .PostgresInterface import PostgresInterface
from .config_handler import Config
from .DVH.dvh import DVH_calculation
import logging
import pandas as pd


class dicom_object:
    def __init__(self, ct, rtplan, rtdose, rtstruct):
        self.rt_plan = rtplan
        self.rt_struct = rtstruct
        self.rt_dose = rtdose
        self.ct = ct


def connect_db():
    postgres_config = Config("postgres")

    config_dict_db = postgres_config.config
    host, port, user, pwd, db = config_dict_db["host"], config_dict_db["port"], \
        config_dict_db["username"], config_dict_db["password"], config_dict_db["db"]
    db = PostgresInterface(host=host, database=db, user=user, password=pwd, port=port)
    db.connect()
    return db


def get_all_uid(db, uid):
    """

    :param db:
    :param uid:
    :return:
    """
    query = f"Select * from public.dicom_insert where study_instance_uid ='{uid}';"
    logging.info(f"the query:  {query}")
    df = pd.read_sql_query(query, db.conn)
    # return db.fetch_all(query=query)
    return df


def check_if_all_in(list_v):
    list_m = ['CT', 'RTSTRUCT', 'RTPLAN', 'RTDOSE']
    value_ = None
    for e in list_v:
        if e not in list_m:
            return False
        else:
            value_ = True
    return value_


def verify_full(df: pd.DataFrame):
    result = True
    list_patient = list(set(df["patient_id"].values.tolist()))
    n_patients = len(list_patient)
    if len(list_patient) > 1:
        logging.info(f"More than one patients in the database {n_patients}")
        val_bool = []
        for p_id in list_patient:
            logging.debug(f"Examining patient: {p_id}")
            df_o_p = df.loc[df["patient_id"] == p_id]
            list_modality = list(set(df_o_p["modality"].value.tolist()))
            logging.debug(f"List modality here: {list_modality}")
            val = check_if_all_in(list_modality)
            val_bool.append(val)
        result = any(val_bool)
        logging.debug(f"All dicom component received ? {result}")
    elif len(list_patient) == 1:
        logging.info("Only one patient")
        p_id = list_patient[0]
        logging.debug(f"Examining patient: {p_id}")
        df_o_p = df.loc[df["patient_id"] == p_id]
        list_modality = list(set(df_o_p["modality"].values.tolist()))
        logging.debug(f"List modality here: {list_modality}")
        result = check_if_all_in(list_modality)
        logging.debug(f"All dicom component received ? {result}")

    return result


def collect_patients_dicom(df: pd.DataFrame):
    list_patient = df["patient_id"].values.tolist()
    list_m = ['CT', 'RTSTRUCT', 'RTPLAN', 'RTDOSE']
    list_do = []
    for p_id in list_patient:
        df_o_p: pd.DataFrame = df.loc[df["patient_id"] == p_id]
        rt_struct = df_o_p.loc[df["modality"] == "RTSTRUCT"]["file_path"].values.tolist()
        ct = df_o_p.loc[df["modality"] == "CT"]["file_path"].values.tolist()
        rt_plan = df_o_p.loc[df["modality"] == "RTPLAN"]["file_path"].values.tolist()
        rt_dose = df_o_p.loc[df["modality"] == "RTDOSE"]["file_path"].values.tolist()
        do = dicom_object(ct, rt_plan, rt_dose, rt_struct)
        list_do.append(do)
    return list_do


def execute_dvh(list_do):
    for p in list_do:
        dvh_c = DVH_calculation()
        dvh_c.get_RT_Dose(p.rt_dose[0])
        dvh_c.get_RT_Plan(p.rt_plan[0])
        dvh_c.get_RT_Struct(p.rt_struct[0])
        dvh_c.get_structures()
        dvh_c.calculate_dvh_all()


def callback(ch, method, properties, body):
    try:
        db = connect_db()

        study_uid = body.decode()
        if study_uid is None:
            raise Exception
        logging.info(f"The study uid is :{study_uid}")
        result = get_all_uid(db, study_uid)
        logging.info(f"result is :{result}")
        verified = verify_full(result)
        if verified:
            list_do = collect_patients_dicom(result)
            execute_dvh(list_do)
        ch.basic_ack(delivery_tag=method.delivery_tag)


    except Exception as e:
        logging.warning(e)
        logging.warning("Error")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
