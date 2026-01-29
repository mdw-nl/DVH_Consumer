from .DVH.dvh import DVH_calculation
import logging
import traceback
import threading
from .DVH.output import return_output
from .Config.global_var import INSERT_QUERY_DICOM_META, DELETE_END
from datetime import datetime
from .combination import combine
from .utilities import connect_db, get_all_uid
from .dicom_operation import collect_patients_dicom, verify_full


def callback_tread(ch, method, properties, body, executor, connection):
    study_uid = body.decode()
    logging.info(f"Message received with uid: {study_uid}")
    executor.submit(process_message_async, study_uid, method.delivery_tag, ch, connection)


def process_message_async(study_uid, delivery_tag, channel, connection):
    db = None
    dicom_bundles = []
    try:
        dicom_bundles = process_message(study_uid)
        db = connect_db()
        params = (
            study_uid,
            True,
            datetime.now()
        )
        db.execute_query(INSERT_QUERY_DICOM_META, params)
        if _ack_message(connection, channel, delivery_tag):
            if DELETE_END and dicom_bundles:
                logging.info(f"Deleting patient data from the database, {DELETE_END}")
                try:
                    for dicom_bundle in dicom_bundles:
                        dicom_bundle.rm_data_patient()
                except Exception as e:
                    logging.warning(f"Error during delete of patient data, Exception Message: {e}")
                    logging.warning(f"Exception Type: {type(e).__name__}")
                    logging.warning(traceback.format_exc())
                    raise
    except Exception as e:
        logging.warning(f"Error during calculation, Exception Message: {e}")
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(traceback.format_exc())
        params = (
            study_uid,
            False,
            datetime.now()
        )
        if db is None:
            db = connect_db()
        db.execute_query(INSERT_QUERY_DICOM_META, params)
        _nack_message(connection, channel, delivery_tag)
    finally:
        if db:
            db.disconnect()


def _ack_message(connection, channel, delivery_tag):
    ack_event = threading.Event()
    ack_result = {"success": False}

    def _ack():
        try:
            channel.basic_ack(delivery_tag=delivery_tag)
            ack_result["success"] = True
        except Exception as e:
            logging.warning(f"Error acknowledging message, Exception Message: {e}")
            logging.warning(f"Exception Type: {type(e).__name__}")
            logging.warning(traceback.format_exc())
        finally:
            ack_event.set()

    connection.add_callback_threadsafe(_ack)
    ack_event.wait(timeout=10)
    return ack_result["success"]


def _nack_message(connection, channel, delivery_tag):
    def _nack():
        try:
            if channel.is_open:
                channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
            else:
                logging.warning("Channel is closed; unable to nack message.")
        except Exception as e:
            logging.warning(f"Error nacking message, Exception Message: {e}")
            logging.warning(f"Exception Type: {type(e).__name__}")
            logging.warning(traceback.format_exc())

    connection.add_callback_threadsafe(_nack)


def process_message(study_uid):
    """
    The function use the study_uid to retrieve the data from the database.
    Verify that for each patient we have all dicom required nad start the dvh calculation
    """
    db = None
    dicom_bundles = []
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
    return dicom_bundles


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
