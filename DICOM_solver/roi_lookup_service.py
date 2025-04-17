
from DICOM_solver.config_handler import RoiConfig
from dicompylercore.dicomparser import DicomParser



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
        if standardized_name is None:
            continue
        else:
            standardized_name_dict[standardized_name] = roi

    return standardized_name_dict


def set_standarized_names(rtstruct):


    standardized_name_dict = get_standarized_names(rtstruct)
    for standardize_name, old_name in standardized_name_dict.items():
        roi_mask = rtstruct.get_roi_mask_by_name(old_name)
        rtstruct.add_roi(mask=roi_mask, name=standardize_name, approximate_contours=False)
    #for roi in rtstruct_roi:
    #    roi_mask = rtstruct.get_roi_mask_by_name(roi)
    #
    #    rtstruct.add_roi(mask=roi_mask, name=standardized_name_dict[roi], approximate_contours=False)

    return rtstruct




def get_standardized_name2(synonym):
    config = RoiConfig()
    try:
        standardized_name = config.rois[synonym]
    except KeyError:
        standardized_name = None
    return standardized_name


def get_standarized_names2(rtstruct: DicomParser):
    """
    Returns a dictionary mapping original ROI names -> standardized names.
    """
    ds = rtstruct.ds  # access pydicom dataset from DicomParser
    standardized_name_dict = {}

    for roi in ds.StructureSetROISequence:
        original_name = roi.ROIName
        standardized_name = get_standardized_name2(original_name)
        if standardized_name:
            standardized_name_dict[original_name] = standardized_name

    return standardized_name_dict


def set_standarized_names2(rtstruct: DicomParser):
    """
    Modifies ROI names in the underlying pydicom dataset from a DicomParser object,
    replacing original ROI names with standardized ones (in-place).
    """
    ds = rtstruct.ds  # access the pydicom dataset from dicompylercore

    standardized_name_dict = get_standarized_names2(rtstruct)

    # Update ROI names in StructureSetROISequence
    for roi in ds.StructureSetROISequence:
        original_name = roi.ROIName
        if original_name in standardized_name_dict:
            standardized_name = standardized_name_dict[original_name]
            roi.ROIName = standardized_name


    # Update corresponding ROIObservationLabel in RTROIObservationsSequence
    if "RTROIObservationsSequence" in ds:
        for obs in ds.RTROIObservationsSequence:
            roi_number = obs.ReferencedROINumber
            matching_roi = next((r for r in ds.StructureSetROISequence if r.ROINumber == roi_number), None)
            if matching_roi:
                obs.ROIObservationLabel = matching_roi.ROIName

    return rtstruct  # same DicomParser object, updated internally

