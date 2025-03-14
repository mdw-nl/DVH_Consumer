import logging
from .PostgresInterface import PostgresInterface
from .config_handler import Config
from .DVH.dvh import DVH_calculation
import logging
import pandas as pd
import traceback

from .dicom_process import dicom_object
from .DVH.output import return_output


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
    try:
        df = pd.read_sql_query(query, db.conn)
    except Exception as e:
        raise e
    return df


def check_if_all_in(list_v):
    list_m = ['CT', 'RTSTRUCT', 'RTPLAN', 'RTDOSE']
    value_ = False
    for e in list_v:
        if e not in list_m:
            return False
        else:
            value_ = True
    return value_


def verify_full(df: pd.DataFrame):
    """

    :param df:
    :return:
    """
    result = True
    list_patient = list(set(df["patient_id"].values.tolist()))
    n_patients = len(list_patient)
    if len(list_patient) > 1:
        logging.info(f"More than one patients in the database {n_patients}")
        result = any(
            check_if_all_in(list(set(df.loc[df["patient_id"] == p_id]["modality"].values.tolist())))
            for p_id in list_patient
        )
    elif len(list_patient) == 1:
        logging.info("Only one patient")
        p_id = list_patient[0]
        result = check_if_all_in(
            list(set(df.loc[df["patient_id"] == p_id]["modality"].values.tolist()))
        )
    logging.debug(f"All dicom component received ? {result}")

    return result


def link_rt_plan_dose(df, rt_plan_uid_list,p_id, ct, rt_struct):
    """

    :param df:
    :param rt_plan_uid_list:
    :param p_id:
    :param ct:
    :param rt_struct:
    :return:
    """
    list_do = []
    for k in rt_plan_uid_list:
        logging.info(f"Dose Sop instance uid to match: {k}")
        rt_dose = df.loc[(df["referenced_rt_plan_uid"] == k) & (df["modality"] == "RTDOSE")][
            "file_path"].values.tolist()
        rt_plan = df.loc[(df["sop_instance_uid"] == k) & (df["modality"] == "RTPLAN")][
            "file_path"].values.tolist()
        logging.info(f"RT dose and plan :{rt_dose}, {rt_plan}")
        do = dicom_object(p_id, ct, rt_plan, rt_dose, rt_struct)
        list_do.append(do)
    return list_do


def collect_patients_dicom(df: pd.DataFrame):
    """

    :param df:
    :return:
    """
    list_patient = list(set(df["patient_id"].values.tolist()))
    result_list = []
    for p_id in list_patient:
        df_o_p: pd.DataFrame = df.loc[df["patient_id"] == p_id]
        ref_rt_plan_uid_list = df_o_p["referenced_rt_plan_uid"].values.tolist()
        rt_struct = df_o_p.loc[df["modality"] == "RTSTRUCT"]["file_path"].values.tolist()
        ct = df_o_p.loc[df["modality"] == "CT"]["file_path"].values.tolist()
        ref_rt_plan_uid_list = [uid for uid in ref_rt_plan_uid_list if uid != "UNKNOWN"]
        list_do = link_rt_plan_dose(df_o_p,ref_rt_plan_uid_list,p_id, ct, rt_struct)
        result_list.extend(list_do)

    return result_list


def execute_dvh(list_do):
    logging.warning(f"Patients to analyze:{len(list_do)} ")
    for p in list_do:
        dvh_c = DVH_calculation()
        logging.info(f"RTdose path :{p.rt_dose[0]}")
        logging.info(f"RTstruct path :{p.rt_struct[0]}")
        logging.info(f"RTplan path :{p.rt_plan[0]}")
        dvh_c.get_RT_Dose(p.rt_dose[0])
        dvh_c.get_RT_Plan(p.rt_plan[0])
        dvh_c.get_RT_Struct(p.rt_struct[0])
        dvh_c.get_structures()
        dvh_c.calculate_dvh_all()
        return_output("x", dvh_c.output)
        logging.info(f"Calculation complete for {p.p_id}")


def process_message(study_uid):
    try:
        db = connect_db()

        if study_uid is None:
            raise Exception(f"Study uid is : {study_uid}")
        logging.info(f"The study uid is :{study_uid}")
        result = get_all_uid(db, study_uid)

        verified = verify_full(result)
        if verified:
            logging.info(f"result is :{result}")
            list_do = collect_patients_dicom(result)
            execute_dvh(list_do)

    except Exception as e:
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(f"Exception Message: {e}")
        logging.warning("Error something wrong")
        logging.warning(traceback.format_exc())


def callback(ch, method, properties, body, executor):
    study_uid = body.decode()
    try:
        future = executor.submit(process_message, study_uid)  # Run processing in a separate thread
        result = future.result()  # Wait for the thread to complete
        logging.info("Finish")

        ch.basic_ack(delivery_tag=method.delivery_tag)  # ACK if successful

    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
