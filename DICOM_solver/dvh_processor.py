from .DVH.dvh import DVH_calculation
import logging
import traceback
from .DVH.output import return_output
from .Config.global_var import INSERT_QUERY_DICOM_META, DELETE_END
from datetime import datetime
from .combination import combine
from .utilities import connect_db, get_all_uid
from .dicom_operation import collect_patients_dicom, verify_full


def callback_tread(ch, method, properties, body, executor):
    study_uid = body.decode()
    db = None
    try:
        logging.info(f"Message received with uid: {study_uid}")
        db = connect_db()
        ch.basic_ack(delivery_tag=method.delivery_tag, )
        future = executor.submit(process_message, study_uid)
        future.result()
        logging.info("Process completed")
        params = (
            study_uid,
            True,
            datetime.now()
        )
        db.execute_query(INSERT_QUERY_DICOM_META, params)

    except Exception as e:
        logging.warning(f"Error during calculation, Exception Message: {e}")
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(traceback.format_exc())
        params = (
            study_uid,
            False,
            datetime.now()
        )
        if db:
            db.execute_query(INSERT_QUERY_DICOM_META, params)
        raise
    finally:

        if db:
            db.disconnect()


def process_message(study_uid):
    """
    The function use the study_uid to retrieve the data from the database.
    Verify that for each patient we have all dicom required nad start the dvh calculation
    """
    db = None
    try:

        logging.info(f"Delete is : {DELETE_END}")
        db = connect_db()
        if study_uid is None:
            raise Exception(f"Study uid is : {study_uid}")
        logging.info(f"The study uid is :{study_uid}")
        result = get_all_uid(db, study_uid)
        verified = verify_full(result)
        if verified:
            logging.info(f"result is :{result}")
            dicom_bundles = collect_patients_dicom(result)
            if dicom_bundles:
                for dicom_bundle in dicom_bundles:
                    logging.info(f"Patients to analyze:{len(dicom_bundles)} ")
                    logging.info(f"{dicom_bundles[0]}")
                    try:
                        calculate_dvh_curves(dicom_bundle)
                    except Exception as e:
                        logging.warning(f"Error during calculation, Exception Message: {e}")
                        logging.warning(f"Exception Type: {type(e).__name__}")
                        logging.warning(traceback.format_exc())
                        raise e
                logging.info(DELETE_END)
                if DELETE_END:
                    logging.info(f"Deleting patient data from the database, {DELETE_END}")
                    try:

                        for dicom_bundle in dicom_bundles:
                            dicom_bundle.rm_data_patient()
                    except Exception as e:
                        logging.warning(f"Error during delete of patient data, Exception Message: {e}")
                        logging.warning(f"Exception Type: {type(e).__name__}")
                        logging.warning(traceback.format_exc())
                        raise e
            else:
                logging.info("No dicom bundles found for the study uid")
    except Exception as e:
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(f"Exception Message: {e}")
        logging.warning(traceback.format_exc())
        raise
    finally:
        if db:
            db.disconnect()


def calculate_dvh_curves(dicom_bundle, str_name=None, gdp=True):
    """
    Calculate dvh curves for the dicom bundle provided
    :param dicom_bundle:
    :param str_name:
    :param gdp:
    """
    dvh_c = DVH_calculation()
    logging.info(f"RTstruct {dicom_bundle.rt_struct}")
    logging.info(f"RTPlan :{dicom_bundle.rt_plan}")
    logging.info(f"RTdose :{dicom_bundle.rt_dose}")
    # Combination happen here with renaiming
    dicom_bundle = combine(dicom_bundle)
    structures = dicom_bundle.rt_struct.GetStructures()

    output = dvh_c.calculate_dvh_all(dicom_bundle, structures, str_name)
    if not gdp:
        return output
    else:
        return_output(dicom_bundle.patient_id, output)
    logging.info(f"Calculation complete for {dicom_bundle.patient_id}")
