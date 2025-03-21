import pandas as pd
from datetime import datetime


def generate_df_sample():
    # Define sample data
    data = {
        "id": [1, 2, 3, 4, 5, 6, 7, 8],
        "timestamp": [datetime(2024, 3, 19, 12, 0, 0)] * 8,  # Same timestamp for all rows
        "patient_id": ["P001", "P001", "P001", "P001", "P002", "P002", "P002", "P002"],
        "study_instance_uid": [
            "1.2.3.4.5.6.1", "1.2.3.4.5.6.1", "1.2.3.4.5.6.1", "1.2.3.4.5.6.1",
            "1.2.3.4.5.6.2", "1.2.3.4.5.6.2", "1.2.3.4.5.6.2", "1.2.3.4.5.6.2"
        ],
        "series_instance_uid": [
            "1.2.3.4.5.6.1.1", "1.2.3.4.5.6.1.2", "1.2.3.4.5.6.1.3", "1.2.3.4.5.6.1.4",
            "1.2.3.4.5.6.2.1", "1.2.3.4.5.6.2.2", "1.2.3.4.5.6.2.3", "1.2.3.4.5.6.2.4"
        ],
        "modality": ["CT", "RTSTRUCT", "RTPLAN", "RTDOSE", "CT", "RTSTRUCT", "RTPLAN", "RTDOSE"],
        "sop_instance_uid": [
            "1.2.3.4.5.6.1.1.1", "1.2.3.4.5.6.1.2.1", "1.2.3.4.5.6.1.3.1", "1.2.3.4.5.6.1.4.1",
            "1.2.3.4.5.6.2.1.1", "1.2.3.4.5.6.2.2.1", "1.2.3.4.5.6.2.3.1", "1.2.3.4.5.6.2.4.1"
        ],
        "sop_class_uid": [
            "1.2.840.10008.5.1.4.1.1.2", "1.2.840.10008.5.1.4.1.1.481.3",
            "1.2.840.10008.5.1.4.1.1.481.5", "1.2.840.10008.5.1.4.1.1.481.2",
            "1.2.840.10008.5.1.4.1.1.2", "1.2.840.10008.5.1.4.1.1.481.3",
            "1.2.840.10008.5.1.4.1.1.481.5", "1.2.840.10008.5.1.4.1.1.481.2"
        ],
        "instance_number": ["1", "1", "1", "1", "1", "1", "1", "1"],
        "file_path": [
            "/dicom/P001/study1/ct.dcm", "/dicom/P001/study1/rtstruct.dcm",
            "/dicom/P001/study1/rtplan.dcm", "/dicom/P001/study1/rtdose.dcm",
            "/dicom/P002/study2/ct.dcm", "/dicom/P002/study2/rtstruct.dcm",
            "/dicom/P002/study2/rtplan.dcm", "/dicom/P002/study2/rtdose.dcm"
        ],
        "referenced_sop_class_uid": [None, None, None, "1.2.840.10008.5.1.4.1.1.481.5",
                                     None, None, None, "1.2.840.10008.5.1.4.1.1.481.5"],
        "referenced_rt_plan_uid": [None, None, None, "1.2.3.4.5.6.1.3.1",
                                   None, None, None, "1.2.3.4.5.6.2.3.1"],
        "modality_type": ["CT", "RTSTRUCT", "RTPLAN", "RTDOSE",
                          "CT", "RTSTRUCT", "RTPLAN", "RTDOSE"],
        "assoc_id": ["A001", "A001", "A001", "A001", "A002", "A002", "A002", "A002"]
    }

    # Create DataFrame
    df_res = pd.DataFrame(data)
    return df_res
