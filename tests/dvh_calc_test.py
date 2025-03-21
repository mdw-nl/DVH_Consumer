#!/usr/bin/env python
import unittest
import os
import zipfile
import urllib.request
from rt_utils import RTStructBuilder
import re
import DICOM_solver.roi_handler as roi_handler
from DICOM_solver.DVH.dvh import DVH_calculation
from DICOM_solver.config_handler import Config
from dicompylercore import dicomparser

ZIP_PATH = 'dicomtestdata.zip'
DICOM_DATA_PATH = 'dicomdata'
DICOM_URL = 'https://github.com/mdw-nl/test-data/releases/download/dicom-data-1.0.0/dicomdata.zip'
RTSTRUCT_FILENAME = "RS.PYTIM05_.dcm"
ROI_KIDNEY_LEFT = "Kidney - left_P"
ROI_KIDNEY_RIGHT = "Kidney - right_P"
PTV_VESSELS_CTV = "PTV+Vessels-CTV"
ROI_GTV = "GTV_P"
ROI_PTV = "PTV_P"
ROI_CTV = "CTV_P"
ROI_VESSELS = "Vessels_P"
OPERATION_ADDITION = "+"
OPERATION_SUBTRACTION = "-"
YAML_DVH_MDSUBMANDIBULARGLANDS = "MeanDoseSubmandibularGlands"

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

    def test_calc_d_mean(self):
        dvh_calculations_list = Config("dvh-calculations").config
        dict_DVH_ROI = next((item[YAML_DVH_MDSUBMANDIBULARGLANDS] for item in dvh_calculations_list if "MeanDoseSubmandibularGlands" in item), None)
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
        self.rtstruct.add_roi(mask=combined_mask, name=PTV_VESSELS_CTV, approximate_contours=False)

        roiNumber = None
        index = 0
        for structure_roi in self.rtstruct.ds.StructureSetROISequence:
            if structure_roi.ROIName == PTV_VESSELS_CTV:
                roiNumber = structure_roi.ROINumber
                break
            index += 1
                    
        rt_struct = dicomparser.DicomParser(self.rtstruct.ds)

        file_path_RTdose = os.path.join("dicomdata", "RD.PYTIM05_.dcm")
        file_path_RTplan = os.path.join("dicomdata", "RP.PYTIM05_PS2.dcm")
        
        dvh_c = DVH_calculation()
        dvh_c.get_RT_Dose(file_path_RTdose)
        dvh_c.get_RT_Plan(file_path_RTplan)
        dvh_c.get_RT_Struct(self.rtstruct.ds)
        dvh_c.get_structures()

        dose_data = dicomparser.DicomParser(file_path_RTdose)
        rt_plan = dicomparser.DicomParser(file_path_RTplan)

        output = dvh_c.get_dvh_v(rt_struct,
                  dose_data,
                  roiNumber,
                  rt_plan)
        dvh_c.process_dvh_result(output, index)

        print(dvh_c.output)

        # Iterate over the output list to access the mean values
        # for structure in output:
        #     if structure["structureName"] == PTV_VESSELS_CTV:
        #         print(f"mean {PTV_VESSELS_CTV} {structure["mean"]["value"]}")
        #         print(f"volume {PTV_VESSELS_CTV} {structure["volume"]["value"]}")# Extract the mean dose value
        #         break
        
if __name__ == '__main__':
    unittest.main()