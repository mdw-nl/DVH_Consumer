import json
import logging
import pydicom
import os
from DICOM_solver.queue_processing import Consumer
from DICOM_solver.config_handler import Config


class upload_XNAT:

    def __init__(self):
        self.path = "DVH_data"
        self.message_folder = "messages"
        self.output_file = "message.json"

        os.makedirs(self.path, exist_ok=True)

    def create_json_metadata(self, dicom_bundle):
        ds = pydicom.dcmread(
            dicom_bundle.rt_struct_path,
            stop_before_pixels=True
        )

        info_dict = {
            "project": str(ds.BodyPartExamined),
            "subject": str(ds.PatientName),
            "experiment": str(ds.StudyInstanceUID).replace(".", "_")
        }

        info_path = os.path.join(self.path, "metadata_xnat.json")
        with open(info_path, "w") as f:
            json.dump(info_dict, f, indent=4)

        logging.info(f"Metadata saved to {info_path}")

    def save_DVH(self, output):
        dvh_path = os.path.join(self.path, "DVH.json")
        with open(dvh_path, "w") as f:
            json.dump(output, f, indent=4)

        logging.info(f"DVH saved to {dvh_path}")

    def _send_to_next_queue(self, queue, data_folder):
        output_file_path = os.path.join(
            self.message_folder,
            self.output_file
        )
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        message = {
            "folder_path": data_folder,
            "action": queue
        }

        with open(output_file_path, "w") as file:
            json.dump(message, file, indent=2)

        logging.info(f"RabbitMQ message created at: {output_file_path}")

        rabbitmq_config = Config(queue)
        consumer = Consumer(rmq_config=rabbitmq_config)
        consumer.open_connection_rmq()
        consumer.send_message(self.message_folder)

        logging.info(f"Sent data {data_folder} to queue '{queue}'")

    def run(self, output, dicom_bundle):
        self.create_json_metadata(dicom_bundle)
        self.save_DVH(output)
        self._send_to_next_queue("xnat", self.path)