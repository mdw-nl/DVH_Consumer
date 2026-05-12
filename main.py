import threading

from DICOM_solver.queue_processing import Consumer
from DICOM_solver.dvh_processor import callback_tread
import logging
from DICOM_solver.config_handler import Config
import uvicorn
from fastapi import FastAPI, Body, Query, HTTPException
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
        if res is None:
            raise HTTPException(
                status_code=404,
                detail=f"No DVH data for patient '{patient_id}', structure '{structure}'",
            )
    finally:
        if dp:
            dp.close()
    return JSONResponse(content=res, media_type="application/ld+json")


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
