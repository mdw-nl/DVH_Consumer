from DICOM_solver.config_handler import RoiConfig

def get_standardized_name(synonym):
    config = RoiConfig()
    try:
        standardized_name = config.rois[synonym]
    except KeyError:
        standardized_name = None
    return standardized_name

def get_standarized_names(rtstruct):
    rtstruct_roi = rtstruct.get_roi_names()
    
    standardized_name_dict = {}
    for roi in rtstruct_roi:
        standardized_name = get_standardized_name(roi)
        standardized_name_dict[standardized_name] = roi
        
    return standardized_name_dict

def set_standarized_names(rtstruct):
    rtstruct_roi = rtstruct.get_roi_names()
    
    standardized_name_dict = get_standarized_names(rtstruct)
    for roi in rtstruct_roi:
        roi_mask = rtstruct.get_roi_mask_by_name(roi)
        rtstruct.add_roi(mask=roi_mask, name=standardized_name_dict[roi], approximate_contours=False)
    
    return rtstruct