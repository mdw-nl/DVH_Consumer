from .PostgresInterface import PostgresInterface
from .config_handler import Config
from .DVH.dvh import DVH_calculation
import logging
import pandas as pd
import traceback
from .DVH.output import return_output
from .DVH.dicom_bundle import DicomBundle
from dicompylercore.dicomparser import DicomParser
from DICOM_solver.roi_lookup_service import set_standarized_names, get_standarized_names
from DICOM_solver.roi_handler import roi_list, roi_operation, combine_rois, check_if_roi_exist
import re
from rt_utils import RTStructBuilder
from DICOM_solver.roi_handler import combine_rois


def callback_tread(ch, method, properties, body, executor):
    study_uid = body.decode()
    try:
        future = executor.submit(process_message, study_uid)
        result = future.result()
        logging.info("Finish")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


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
            dicom_bundles = collect_patients_dicom(result)
            for dicom_bundle in dicom_bundles:
                logging.info(f"Patients to analyze:{len(dicom_bundles)} ")
                logging.info(f"{dicom_bundles[0]}")
                calculate_dvh_curves(dicom_bundle)

    except Exception as e:
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(f"Exception Message: {e}")
        logging.warning("Error something wrong")
        logging.warning(traceback.format_exc())
        raise e


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
            check_if_all_in(list(set(df.loc[df["patient_id"] == patient_id]["modality"].values.tolist())))
            for patient_id in list_patient
        )
    elif len(list_patient) == 1:
        logging.info("Only one patient")
        patient_id = list_patient[0]
        result = check_if_all_in(
            list(set(df.loc[df["patient_id"] == patient_id]["modality"].values.tolist()))
        )
    logging.debug(f"All dicom component received ? {result}")

    return result


def link_rt_plan_dose(df, rt_plan_uid_list, patient_id, ct, rt_struct):
    """

    :param df:
    :param rt_plan_uid_list:
    :param patient_id:
    :param ct:
    :param rt_struct:
    :return:
    """
    list_do = []
    for k in rt_plan_uid_list:
        # logging.info(f"Dose Sop instance uid to match: {k}")
        rt_dose = df.loc[(df["referenced_rt_plan_uid"] == k) & (df["modality"] == "RTDOSE")][
            "file_path"].values.tolist()
        rt_plan = df.loc[(df["sop_instance_uid"] == k) & (df["modality"] == "RTPLAN")][
            "file_path"].values.tolist()
        logging.info(f"RT dose and plan :{rt_dose}, {rt_plan}")
        logging.info(f"rt struct {rt_struct[0]}")
        logging.info(f"rt plan  {rt_plan[0]}")
        logging.info(f"ct  {ct[0]}")
        logging.info(f"rt doe   {rt_dose}")
        dicom_bundle = DicomBundle(patient_id=patient_id, rt_ct=ct[0], rt_plan=rt_plan[0],
                                   rt_dose=rt_dose, rt_struct=rt_struct[0])
        list_do.append(dicom_bundle)
    return list_do


def collect_patients_dicom(df: pd.DataFrame):
    """

    :param df:
    :return:
    """
    list_patient = list(set(df["patient_id"].values.tolist()))
    result_list = []
    for patient_id in list_patient:
        df_o_p: pd.DataFrame = df.loc[df["patient_id"] == patient_id]
        ref_rt_plan_uid_list = df_o_p["referenced_rt_plan_uid"].values.tolist()
        rt_struct = df_o_p.loc[df["modality"] == "RTSTRUCT"]["file_path"].values.tolist()
        ct = df_o_p.loc[df["modality"] == "CT"]["file_path"].values.tolist()
        ref_rt_plan_uid_list = [uid for uid in ref_rt_plan_uid_list if uid != "UNKNOWN"]
        dicom_bundles = link_rt_plan_dose(df_o_p, ref_rt_plan_uid_list, patient_id, ct, rt_struct)
        result_list.extend(dicom_bundles)

    return result_list


# def add_combined_structures(rt_struct):
#    """
#
#    :param rt_struct:
#    :return:
#    """
#    roi_lookup_sevice = roi_lookup_sevice()
#    standarized_name_dict = roi_lookup_sevice.get_standarized_names(rt_struct)
#    dvh_c = DVH_calculation()
#    dvh_calculations_list = Config("dvh-calculations").config
#    for item in dvh_calculations_list:
#        for key, value in item.items():
#            roi_string = value["roi"]
#
#        string_parts = re.split(r'\s+', roi_string)
#
#        ROI_total_string = ""
#        operations_list = []
#        ROI_list = []
#        for i, parts in enumerate(string_parts, start=1):
#            ROI_total_string = ROI_total_string + parts
#            if i % 2 == 0:
#                operations_list.append(parts)
#            else:
#                ROI_list.append(standarized_name_dict[parts])
#
#        combined_mask = roi_handler.combine_rois(rt_struct, ROI_list, operations_list)
#        rt_struct.add_roi(mask=combined_mask, name=ROI_total_string, approximate_contours=False)
#        return rt_struct


def calculate_dvh_curves(dicom_bundle):
    """

    """
    dvh_c = DVH_calculation()
    logging.info(f"RTstruct {dicom_bundle.rt_struct}")
    logging.info(f"RTPlan :{dicom_bundle.rt_plan}")
    logging.info(f"RTdose :{dicom_bundle.rt_dose}")
    dicom_bundle = combine(dicom_bundle)
    structures = dicom_bundle.rt_struct.GetStructures()
    logging.info(f"Structures :{structures}")
    output = dvh_c.calculate_dvh_all(dicom_bundle, structures)
    return_output(dicom_bundle.patient_id, output)
    logging.info(f"Calculation complete for {dicom_bundle.patient_id}")


def structure_combination(item, rt_struct):
    roi_string = next(iter(item.values()))["roi"]
    ROI_total_string = roi_string
    string_parts = re.split(r'\s+', roi_string)
    operations_list = roi_operation(string_parts)
    ROI_list = roi_list(string_parts)
    rt_struct_rois = rt_struct.get_roi_names()
    for k in ROI_list:
        if not check_if_roi_exist(k, rt_struct_rois):
            logging.info(f"Roi combination cancelled. {k} not in the roi list")
            return rt_struct
    combined_mask = combine_rois(rt_struct, ROI_list, operations_list)
    rt_struct.add_roi(mask=combined_mask, name=ROI_total_string, approximate_contours=False)
    logging.info(f"Combination completed. {ROI_total_string}")
    return rt_struct


def combine(dicom_bundle: DicomBundle):
    rt_struct = RTStructBuilder.create_from(dicom_bundle.rt_ct_path, dicom_bundle.rt_struct_path)
    logging.info("Starting combination")
    dvh_calculations_list = Config("dvh-calculations").config
    rt_struct = set_standarized_names(rt_struct)
    for item in dvh_calculations_list:
        rt_struct = structure_combination(item, rt_struct)
    rt_struct: DicomParser = DicomParser(rt_struct.ds)
    dicom_bundle.rt_struct = rt_struct
    return dicom_bundle
