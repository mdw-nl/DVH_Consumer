import yaml
import logging


def read_config():
    with open('DICOM_solver/Config/config.yaml', 'r') as file:
        file_red = yaml.safe_load(file)
        return file_red


class Config:
    def __init__(self, section_name):
        file = read_config()
        self.config = None
        self.read_config_section(file, section_name)

    def read_config_section(self, file, sect):
        self.config = file.get(sect, {})
        logging.info(f"Config data : {self.config}")

class RoiConfig:
    rois = {}

    def __init__(self):
        with open('roi_name_mappings.yaml', 'r') as file:
            roiNameObject = yaml.safe_load(file)
            for standardName, synonymList in roiNameObject.items():
                for synonym in synonymList:
                    self.rois[synonym] = standardName
