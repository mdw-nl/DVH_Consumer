import yaml
import logging
import os


def read_config():
    config_path = os.path.join(os.path.dirname(__file__), 'Config', 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


class Config:
    def __init__(self, section_name):
        file = read_config()
        self.config = None
        self.read_config_section(file, section_name)

    def read_config_section(self, file, sect):
        self.config = file.get(sect, {})


class RoiConfig:
    _rois = {}
    _instance = None

    @property
    def rois(self):
        return self.__class__._rois

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RoiConfig, cls).__new__(cls)
            cls._load_config()
        return cls._instance

    @classmethod
    def _load_config(cls):

        config_path = os.path.join(os.path.dirname(__file__), 'Config', 'roi_name_mappings.yaml')
        logging.info(f"The config path is {config_path}")
        with open(config_path, 'r') as file:
            logging.info(f"The file path is {file}")
            roi_name_object = yaml.safe_load(file)
            cls._rois.clear()
            for standard_name, synonym_list in roi_name_object.items():
                for synonym in synonym_list:
                    cls._rois[synonym] = standard_name

