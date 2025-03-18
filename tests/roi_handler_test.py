#!/usr/bin/env python

import unittest
import os
import zipfile
import DICOM_solver.roi_handler as roi_handler
import urllib.request
from rt_utils import RTStructBuilder

ZIP_PATH = 'dicomtestdata.zip'
DICOM_DATA_PATH = 'dicomdata'
DICOM_URL = 'https://github.com/mdw-nl/test-data/releases/download/dicom-data-1.0.0/dicomdata.zip'
RTSTRUCT_FILENAME = "RS.PYTIM05_.dcm"
ROI_KIDNEY_LEFT = "Kidney - left_P"
ROI_KIDNEY_RIGHT = "Kidney - right_P"
ROI_GTV = "GTV_P"
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

    def test_combine_rois_addition(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, [ROI_KIDNEY_LEFT, ROI_KIDNEY_RIGHT], [OPERATION_ADDITION])
        print(combined_mask)

    def test_combine_rois_subtraction(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, [ROI_KIDNEY_LEFT, ROI_GTV], [OPERATION_SUBTRACTION])
        print(combined_mask)

    def test_combine_rois_multiple(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, [ROI_KIDNEY_LEFT, ROI_KIDNEY_RIGHT, ROI_GTV], [OPERATION_ADDITION, OPERATION_SUBTRACTION])
        print(combined_mask)

    def test_combine_rois_invalid(self):
        with self.assertRaises(AssertionError):
            roi_handler.combine_rois(self.rtstruct, [ROI_KIDNEY_LEFT, ROI_KIDNEY_RIGHT], [OPERATION_ADDITION, OPERATION_SUBTRACTION])

if __name__ == '__main__':
    unittest.main()