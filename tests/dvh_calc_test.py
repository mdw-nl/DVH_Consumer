#!/usr/bin/env python

import unittest
import os
import zipfile
import urllib.request
from rt_utils import RTStructBuilder
import numpy as np

import DICOM_solver.roi_handler as roi_handler
import DICOM_solver.DVH.dvh as dvh
from DICOM_solver.config_handler import Config

ZIP_PATH = 'dicomtestdata.zip'
DICOM_DATA_PATH = 'dicomdata'
DICOM_URL = 'https://github.com/mdw-nl/test-data/releases/download/dicom-data-1.0.0/dicomdata.zip'
RTSTRUCT_FILENAME = "RS.PYTIM05_.dcm"
ROI_KIDNEY_LEFT = "Kidney - left_P"
ROI_KIDNEY_RIGHT = "Kidney - right_P"
ROI_GTV = "GTV_P"
ROI_PTV = "PTV_P"
ROI_CTV = "CTV_P"
ROI_VESSELS = "Vessels_P"
OPERATION_ADDITION = "+"
OPERATION_SUBTRACTION = "-"

class TestROIHandler(unittest.TestCase):
    rtstruct = None

    def setUp(self):
        if not os.path.exists(ZIP_PATH):
            urllib.request.urlretrieve(DICOM_URL, ZIP_PATH)
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall('')
        rtstruct_path = os.path.join(DICOM_DATA_PATH, RTSTRUCT_FILENAME)
        dicom_series_path = os.path.join(DICOM_DATA_PATH)
        self.rtstruct = RTStructBuilder.create_from(dicom_series_path, rtstruct_path)

    def calc_d_mean(self):
        print()

if __name__ == '__main__':
    unittest.main()