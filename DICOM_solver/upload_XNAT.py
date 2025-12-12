import json
import logging
import pydicom
import os
from DICOM_solver.RabbitMQ_messenger import messenger

class upload_XNAT:
    def __init__(self):
        self.path = "DVH_data"
        os.makedirs(self.path, exist_ok=True)
    
    def create_json_metadata(self, dicom_bundle):
        ds = pydicom.dcmread(dicom_bundle.rt_struct_path, stop_before_pixels=True)

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
        DVH_path = os.path.join(self.path, "DVH.json")
        with open(DVH_path, "w") as f:
            json.dump(output, f, indent=4)
        
        logging.info(f"Metadata saved to {DVH_path}")
        
    def send_next_queue(self, queue, data_folder):
        message_creator = messenger()
        message_creator.create_message_next_queue(queue, data_folder)
    
    def run(self, output, dicom_bundle):
        self.create_json_metadata(dicom_bundle)
        self.save_DVH(output)
        self.send_next_queue("xnat", self.path)