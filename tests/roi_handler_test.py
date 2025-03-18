#!/usr/bin/env python

import unittest
import os
import zipfile
import DICOM_solver.roi_handler as roi_handler
import urllib.request

class TestROIHandler(unittest.TestCase):
    def setUp(self):
        url = 'https://github.com/mdw-nl/test-data/releases/download/dicom-data-1.0.0/dicomdata.zip'
        zip_path = 'dicomtestdata.zip'
        if not os.path.exists(zip_path):
            urllib.request.urlretrieve(url, zip_path)
        zip_path = 'dicomtestdata.zip'
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('')

    def test_combine_rois(self):
        
        roi_handler.combineRois([], [], [])

if __name__ == '__main__':
    unittest.main()