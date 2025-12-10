import re
from DICOM_solver.roi_handler import roi_list, roi_operation, combine_rois, check_if_roi_exist
import logging
from .DVH.dicom_bundle import DicomBundle
from rt_utils import RTStructBuilder
from .config_handler import Config
from DICOM_solver.roi_lookup_service import set_standarized_names, get_standarized_names
from dicompylercore.dicomparser import DicomParser


def structure_combination(item, rt_struct):
    """

    :param item:
    :param rt_struct:

    """
    roi_string = next(iter(item.values()))["roi"]
    ROI_total_string = roi_string
    string_parts = re.split(r'\s+', roi_string)
    operations_list = roi_operation(string_parts)
    ROI_list = roi_list(string_parts)
    rt_struct_rois = rt_struct.get_roi_names()
    for k in ROI_list:
        if not check_if_roi_exist(k, rt_struct_rois):
            logging.info(f"Roi combination cancelled. {k} not in the roi list")
            return rt_struct
    combined_mask = combine_rois(rt_struct, ROI_list, operations_list)
    rt_struct.add_roi(mask=combined_mask, name=ROI_total_string, approximate_contours=False)
    logging.info(f"Combination completed. {ROI_total_string}")
    return rt_struct


def combine(dicom_bundle: DicomBundle):
    """
    Combine structures based on configuration
    """
    rt_struct = RTStructBuilder.create_from(dicom_bundle.rt_ct_path, dicom_bundle.rt_struct_path)
    logging.info("Starting combination")
    dvh_calculations_list = Config("dvh-calculations").config
    rt_struct = set_standarized_names(rt_struct)
    for item in dvh_calculations_list:
        rt_struct = structure_combination(item, rt_struct)
    rt_struct: DicomParser = DicomParser(rt_struct.ds)
    dicom_bundle.rt_struct = rt_struct
    return dicom_bundle
