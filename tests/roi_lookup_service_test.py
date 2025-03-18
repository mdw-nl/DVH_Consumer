#!/usr/bin/env python

import unittest
from DICOM_solver.roi_lookup_service import RoiLookupService

class TestRoiLookupService(unittest.TestCase):

    def test_get_roi_name(self):
        roi_lookup_service = RoiLookupService()
        standardized_name = roi_lookup_service.get_standardized_name("LungL")
        self.assertEqual(standardized_name, "Lung_L")
    
    def test_get_roi_name_invalid(self):
        roi_lookup_service = RoiLookupService()
        standardized_name = roi_lookup_service.get_standardized_name("InvalidName")
        self.assertIsNone(standardized_name)

if __name__ == '__main__':
    unittest.main()