#!/usr/bin/env python
import unittest
import numpy as np
import os
import math
import zipfile
import urllib.request
from rt_utils import RTStructBuilder
import re
import DICOM_solver.roi_handler as roi_handler
from DICOM_solver.DVH.dvh import DVH_calculation
from DICOM_solver.config_handler import Config
from dicompylercore import dicomparser
from DICOM_solver.roi_lookup_service import RoiLookupService
from DICOM_solver.DVH.dicom_bundle import DicomBundle

ZIP_PATH = 'dicomtestdata.zip'
DICOM_DATA_PATH = 'dicomdata'
DICOM_URL = 'https://github.com/mdw-nl/test-data/releases/download/dicom-data-1.0.0/dicomdata.zip'
RTSTRUCT_FILENAME = "RS.PYTIM05_.dcm"
ROI_KIDNEY_LEFT = "Kidney - left_P"
ROI_KIDNEY_RIGHT = "Kidney - right_P"
PTV_VESSELS = "PTV-Vessels"
PTV_VESSELS_CTV = "PTV+Vessels-CTV"
ROI_GTV = "GTV_P"
ROI_PTV = "PTV_P"
ROI_CTV = "CTV_P"
ROI_VESSELS = "Vessels_P"
OPERATION_ADDITION = "+"
OPERATION_SUBTRACTION = "-"
YAML_PTV_VESSELS = "TestPTV_P-Vessels_P"

# Haal de config labels uit de yaml file, doe de addit/substration met de handler, bereken de DVH en dan .mean/.volume
# Vul de yaml file aan

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
    
    def standarized_name_dict(self):
        roi_lookup_service = RoiLookupService()
        rtstruct_roi = self.rtstruct.get_roi_names()
        
        standardized_name_dict = {}
        for roi in rtstruct_roi:
            standardized_name = roi_lookup_service.get_standardized_name(roi)
            standardized_name_dict[standardized_name] = roi
            
        return standardized_name_dict

    def test_calc_d_mean(self):
        # Get the dvh-calculations from the config file and get the dict for the standarized names
        dvh_calculations_list = Config("dvh-calculations").config
        standarized_name_dict = self.standarized_name_dict()
        
        # Loop over all the items in the config file
        for item in dvh_calculations_list:
            for key, value in item.items():
                roi_string = value["roi"]

            string_parts = re.split(r'\s+', roi_string)
            
            # create two list for the operations and the ROIS with rtstruct names    
            ROI_total_string = ""
            operations_list = []
            ROI_list = []
            for i, parts in enumerate(string_parts, start=1):
                ROI_total_string = ROI_total_string + parts
                if i%2 == 0:
                    operations_list.append(parts)
                else:
                    print(standarized_name_dict)
                    ROI_list.append(standarized_name_dict[parts])
            
            # Add the new ROI to the rtstruct
            combined_mask = roi_handler.combine_rois(self.rtstruct, ROI_list, operations_list)
            self.rtstruct.add_roi(mask=combined_mask, name=ROI_total_string, approximate_contours=False)

            roiNumber = None
            for structure_roi in self.rtstruct.ds.StructureSetROISequence:
                if structure_roi.ROIName == ROI_total_string:
                    roiNumber = structure_roi.ROINumber
                    break        
            rt_struct = dicomparser.DicomParser(self.rtstruct.ds)

            file_path_RTdose = os.path.join("dicomdata", "RD.PYTIM05_.dcm")
            file_path_RTplan = os.path.join("dicomdata", "RP.PYTIM05_PS2.dcm")
            
            dose_data = dicomparser.DicomParser(file_path_RTdose)
            rt_plan = dicomparser.DicomParser(file_path_RTplan)

            dvh_c = DVH_calculation()
            result = dvh_c.get_dvh_v(rt_struct,
                    dose_data,
                    roiNumber,
                    rt_plan)
            output = dvh_c.process_dvh_result(result, roiNumber, rt_struct.GetStructures())

            print(f"mean {ROI_total_string} {output["mean"]["value"]}")
            print(f"volume {ROI_total_string} {output["volume"]["value"]}")
            break

    # This test check if the determined values of PTV-Vessels is close to the actual values
    def test_values_ptv_vessels(self):
        dvh_calculations_list = Config("dvh-calculations").config
        dict_DVH_ROI = next((item[YAML_PTV_VESSELS] for item in dvh_calculations_list if "TestPTV_P-Vessels_P" in item), None)
        roi_string = dict_DVH_ROI["roi"]
        string_parts = re.split(r'\s+', roi_string)
        
        operations_list = []
        ROI_list = []
        for i, parts in enumerate(string_parts, start=1):
            if i%2 == 0:
                operations_list.append(parts)
            else:
                ROI_list.append(parts)
        
        combined_mask = roi_handler.combine_rois(self.rtstruct, ROI_list, operations_list)
        self.rtstruct.add_roi(mask=combined_mask, name=PTV_VESSELS, approximate_contours=False)

        roiNumber = None
        for structure_roi in self.rtstruct.ds.StructureSetROISequence:
            if structure_roi.ROIName == PTV_VESSELS:
                roiNumber = structure_roi.ROINumber
                break
                    

        file_path_RTdose = os.path.join("dicomdata", "RD.PYTIM05_.dcm")
        file_path_RTplan = os.path.join("dicomdata", "RP.PYTIM05_PS2.dcm")
        
        

        rt_struct = dicomparser.DicomParser(self.rtstruct.ds)
        dose_data = dicomparser.DicomParser(file_path_RTdose)
        rt_plan = dicomparser.DicomParser(file_path_RTplan)

        dvh_c = DVH_calculation()
        result = dvh_c.get_dvh_v(rt_struct,
                  dose_data,
                  roiNumber,
                  rt_plan)
        output = dvh_c.process_dvh_result(result, roiNumber, rt_struct.GetStructures())

        mean = output["mean"]["value"]
        volume = output["volume"]["value"]
        
        real_volume = 48.4625
        real_mean_dose = 4.47565
        
        test_list = []
        test_list.append(math.isclose(real_volume, volume, rel_tol=0.1))
        test_list.append(math.isclose(real_mean_dose, mean, rel_tol=0.1))
        self.assertTrue(np.all(test_list))
        
if __name__ == '__main__':
    unittest.main()