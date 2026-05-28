import threading

from DICOM_solver.queue_processing import Consumer
from DICOM_solver.dvh_processor import callback_tread, reprocess_study
import logging
from DICOM_solver.config_handler import Config
import uvicorn
from fastapi import FastAPI, Body, Query, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from DICOM_solver.API.retrieve_Data import DataAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()
app = FastAPI()


@app.get("/calculate_DVH", tags=["DVH"], summary="Calculate DVH")
def calculate_dvh(patient_id: str, structure: str):
    dp = None
    try:
        dp = DataAPI()
        dp.get_data_api(patient_id)
        res = dp.dvh_api(structure_name=structure)
        if not res:
            raise HTTPException(
                status_code=404,
                detail=f"No DVH data for patient '{patient_id}', structure '{structure}'",
            )
    finally:
        if dp:
            dp.close()
    return JSONResponse(content=res, media_type="application/ld+json")


@app.post("/reprocess/{study_uid}", tags=["DVH"], summary="Reprocess a previously-ingested study")
def reprocess(study_uid: str, background_tasks: BackgroundTasks):
    """Schedule a re-run of the DVH calculations for a study that was already ingested.

    Requires the original DICOM files to still exist on disk (DELETE_END must
    have been false during the original run, or the data re-uploaded by the listener).

    Returns 202 immediately; the calculation runs in the background.
    Final outcome (success or failure) is recorded in calculation_status.
    """
    background_tasks.add_task(reprocess_study, study_uid)
    return JSONResponse(
        status_code=202,
        content={"study_uid": study_uid, "status": "reprocessing scheduled"},
    )


# Function to start the consumer and handle exceptions
def start_consumer():
    try:
        rabbitMQ_config = Config("rabbitMQ")
        cons = Consumer(rmq_config=rabbitMQ_config)
        cons.open_connection_rmq()
        cons.create_channel()
        cons.start_consumer(callback=callback_tread)

    except Exception as e:
        logger.error(f"An error occurred while trying to start the server: {e}")
        logger.error("Please check the configuration and the RabbitMQ server status.")
        raise e


# Function to expose API
def api_start():
    logging.info("Starting API server on port 8000")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":

    consumer_t = threading.Thread(target=start_consumer, daemon=True)
    consumer_t.start()
    api_start()
