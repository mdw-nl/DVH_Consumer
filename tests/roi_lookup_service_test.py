#!/usr/bin/env python

import unittest
from DICOM_solver.roi_lookup_service import RoiLookupService

ROI_NAME = "LungL"
STANDARDIZED_NAME = "Lung_L"
INVALID_ROI_NAME = "InvalidName"

class TestRoiLookupService(unittest.TestCase):

    def test_get_roi_name(self):
        roi_lookup_service = RoiLookupService()
        standardized_name = roi_lookup_service.get_standardized_name(ROI_NAME)
        self.assertEqual(standardized_name, STANDARDIZED_NAME)
    
    def test_get_roi_name_invalid(self):
        roi_lookup_service = RoiLookupService()
        standardized_name = roi_lookup_service.get_standardized_name(INVALID_ROI_NAME)
        self.assertIsNone(standardized_name)

if __name__ == '__main__':
    unittest.main()