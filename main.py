from DICOM_solver.queue_processing import Consumer
from DICOM_solver.dvh_processor import callback_tread
import logging
from DICOM_solver.config_handler import Config

import yaml


class RoiLookupService:
    rois = dict()

    def __init__(self):
        with open('DICOM_solver/Config/roi_name_mappings.yaml', 'r') as file:
            roiNameObject = yaml.safe_load(file)
            for standardName, synonymList in roiNameObject.items():
                for synonym in synonymList:
                    self.rois[synonym] = standardName

    def get_standardized_name(self, synonym):
        try:
            standardized_name = self.rois[synonym]
        except KeyError:
            standardized_name = None
        return standardized_name


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

if __name__ == "__main__":
    rabbitMQ_config = Config("rabbitMQ")
    cons = Consumer(rmq_config=rabbitMQ_config)
    cons.open_connection_rmq()
    cons.start_consumer(callback=callback_tread)
