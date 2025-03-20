#!/usr/bin/env python

import unittest
import os
import zipfile
import DICOM_solver.roi_handler as roi_handler
from DICOM_solver.loading_mask import load_mask
import urllib.request
from rt_utils import RTStructBuilder
import numpy as np

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
# Schrijf nog wat addition testjes voor substraction misschien zelfs voor combine
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
    
    def test_combine_rois_addition_to_base_ROI(self):
        ROIS = [ROI_PTV, ROI_VESSELS]
        combined_mask = roi_handler.combine_rois(self.rtstruct, ROIS, [OPERATION_ADDITION])
        
        test_values = []
        for roi in ROIS:
            mask_roi = load_mask("dicomdata", "RS.PYTIM05_.dcm", roi)
            is_subset = np.all(mask_roi <= combined_mask)
            test_values.append(is_subset)
            
        self.assertTrue(np.all(test_values))
    
    def test_combine_rois_substraction_to_base_ROI(self):
        ROIS = [ROI_PTV, ROI_VESSELS]
        combined_mask = roi_handler.combine_rois(self.rtstruct, ROIS, [OPERATION_SUBTRACTION])
        
        first_roi_mask = self.rtstruct.get_roi_mask_by_name(ROIS[0])
        second_roi_mask = self.rtstruct.get_roi_mask_by_name(ROIS[1])
        condition_mask = np.logical_and(first_roi_mask, np.logical_not(second_roi_mask))
        # First condition check: when ROI[0] = pos and ROI[1] = neg that combined_mask = pos
        # Second condition check: when ROI[1] = pos that combined_mask = neg
        condition_met_ROI1_pos_ROI2_neg = np.all(combined_mask[condition_mask] == True)
        condition_met_ROI2_pos = np.all(combined_mask[second_roi_mask] == False)
        
        self.assertTrue(np.all([condition_met_ROI1_pos_ROI2_neg, condition_met_ROI2_pos])) 
        
    def test_combine_rois_addition(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, [ROI_PTV, ROI_VESSELS], [OPERATION_ADDITION])
        mask_3d_comp = load_mask("dicomdata", "RS_PTV+Vessels.dcm","PTV+Vessels")
        are_equal = np.array_equal(combined_mask, mask_3d_comp)
        self.assertTrue(are_equal) 
        
    def test_combine_rois_subtraction(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, [ROI_PTV, ROI_VESSELS], [OPERATION_SUBTRACTION])
        mask_3d_comp = load_mask("dicomdata", "RS_PTV-Vessels.dcm","PTV-Vessels")
        are_equal = np.array_equal(combined_mask, mask_3d_comp)
        self.assertTrue(are_equal)        
        
    def test_combine_rois_multiple(self):
        combined_mask = roi_handler.combine_rois(self.rtstruct, [ROI_PTV, ROI_CTV, ROI_VESSELS], [OPERATION_SUBTRACTION, OPERATION_ADDITION])
        mask_3d_comp = load_mask("dicomdata", "RS_PTV+Vessels-CTV.dcm","PTV+Vessels-CTV")
        are_equal = np.array_equal(combined_mask, mask_3d_comp)
        self.assertTrue(are_equal) 
            
    def test_combine_rois_invalid(self):
        with self.assertRaises(AssertionError):
            roi_handler.combine_rois(self.rtstruct, [ROI_KIDNEY_LEFT, ROI_KIDNEY_RIGHT], [OPERATION_ADDITION, OPERATION_SUBTRACTION])

if __name__ == '__main__':
    unittest.main()