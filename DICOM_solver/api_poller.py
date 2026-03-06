import concurrent.futures
import logging
import os
import time
from datetime import datetime

import requests
from croniter import croniter

DICOM_SERVICE_URL = os.getenv("DICOM_SERVICE_URL", "http://dicom-service:9000")
POLL_CRON = os.getenv("POLL_CRON", "*/5 * * * *")


class APIPoller:
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._pending: set[concurrent.futures.Future] = set()

    def _is_idle(self) -> bool:
        self._pending = {f for f in self._pending if not f.done()}
        return len(self._pending) == 0

    def poll(self, callback):
        cron = croniter(POLL_CRON, datetime.now())
        while True:
            next_run = cron.get_next(datetime)
            sleep_seconds = (next_run - datetime.now()).total_seconds()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            if not self._is_idle():
                logging.info("Skipping poll: computations still running")
                continue

            try:
                response = requests.post(
                    f"{DICOM_SERVICE_URL}/rt_package",
                    json={"modality": "RTDOSE"},
                    timeout=30,
                )
                response.raise_for_status()
                packages = response.json().get("packages", [])
                for package in packages:
                    study_uid = package["study_uid"]
                    logging.info(f"Dispatching study_uid from API: {study_uid}")
                    future = self.executor.submit(callback, study_uid)
                    self._pending.add(future)
            except Exception as e:
                logging.exception(f"Error polling DICOM service: {e}")
