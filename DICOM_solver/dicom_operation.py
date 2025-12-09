import logging
import os
from .DVH.dicom_bundle import DicomBundle
import pandas as pd


def check_if_all_in(list_v):
    list_m = ['CT', 'RTSTRUCT', 'RTPLAN', 'RTDOSE']
    value_ = False
    logging.info(f"Checking if all modalities are present in the list: {list_v}")
    for e in list_m:
        if e not in list_v:
            return False
        else:
            value_ = True
    return value_


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


def verify_full(df: pd.DataFrame) -> bool:
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
        logging.info(f"All dicom component received ? {result} for {n_patients} patients")
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
    logging.info(f"Dataframe is {df.columns}")
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
