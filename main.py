import logging
import sys
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from DICOM_solver.API.retrieve_Data import DataAPI
from DICOM_solver.api_poller import APIPoller
from DICOM_solver.dvh_processor import process_message

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger()
app = FastAPI()


@app.get("/calculate_DVH", tags=["DVH"], summary="Calculate DVH")
def calculate_dvh(patient_id: str, structure: str):
    try:
        dp = DataAPI()
        dp.get_data_api(patient_id)
        res = dp.dvh_api(structure_name=structure)
        json_ld_data = res
        logger.info(json_ld_data)
    except Exception as e:
        raise e
    return JSONResponse(content=json_ld_data, media_type="application/ld+json")


def start_poller():
    try:
        poller = APIPoller()
        poller.poll(process_message)
    except Exception as e:
        logger.error(f"An error occurred in the API poller: {e}")
        raise


# Function to expose API
def api_start():
    logging.info("Starting API server on port 8000")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    consumer_t = threading.Thread(target=start_poller, daemon=True)
    consumer_t.start()
    api_start()
