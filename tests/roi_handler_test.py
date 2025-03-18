#!/usr/bin/env python

import unittest
import os
import zipfile
import DICOM_solver.roi_handler as roi_handler
import urllib.request
from rt_utils import RTStructBuilder

class TestROIHandler(unittest.TestCase):
    rtstruct = None

    def setUp(self):
        url = 'https://github.com/mdw-nl/test-data/releases/download/dicom-data-1.0.0/dicomdata.zip'
        zip_path = 'dicomtestdata.zip'
        if not os.path.exists(zip_path):
            urllib.request.urlretrieve(url, zip_path)
        zip_path = 'dicomtestdata.zip'
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('')
        rtstruct_path = os.path.join("dicomdata","RS.PYTIM05_.dcm")
        dicom_series_path = os.path.join("dicomdata")
        self.rtstruct = RTStructBuilder.create_from(dicom_series_path, rtstruct_path)

    def test_combine_rois_addition(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, ["Kidney - left_P","Kidney - right_P"], ["+"])
        print(combined_mask)

    def test_combine_rois_subtraction(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, ["Kidney - left_P","GTV_P"], ["-"])
        print(combined_mask)

    def test_combine_rois_multiple(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, ["Kidney - left_P","Kidney - right_P", "GTV_P"], ["+","-"])
        print(combined_mask)

    def test_combine_rois_invalid(self):
        with self.assertRaises(AssertionError):
            roi_handler.combine_rois(self.rtstruct, ["Kidney - left_P","Kidney - right_P"], ["+","-"])

if __name__ == '__main__':
    unittest.main()