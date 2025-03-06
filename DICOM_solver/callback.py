import logging
from .PostgresInterface import PostgresInterface
from .config_handler import Config
import logging
import pandas as pd


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


def callback(ch, method, properties, body):
    try:
        db = connect_db()

        study_uid = body.decode()
        if study_uid is None:
            raise Exception
        logging.info(f"The study uid is :{study_uid}")
        result = get_all_uid(db, study_uid)
        logging.info(f"result is :{result}")
        verify_full(result)
        ch.basic_ack(delivery_tag=method.delivery_tag)


    except:
        logging.warning("Error")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


#if __name__ == "__main__":
#    db = connect_db()
#
#    study_uid = "1.3.6.1.4.1.22361.100850137389660.1876094375.1683296334941.2"
#    if study_uid is None:
#        raise Exception
#    logging.info(f"The study uid is :{study_uid}")
#    result = get_all_uid(db, study_uid)
#    print(verify_full(result))


