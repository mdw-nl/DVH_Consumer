
from typing import List
from array import array
import numpy as np
from rt_utils import RTStruct

def combine_rois(rtstruct: RTStruct, rois: List[str], operators: List[str]) -> array[bool]:
    assert len(rois) - 1 == len(operators), "There should be exactly one operator less than the number of ROIs."

    # Start with the first ROI mask
    combined_mask = rtstruct.get_roi_mask_by_name(rois[0])

    # Iterate through the remaining ROIs along with their corresponding operators
    for i in range(1, len(rois)):
        roi_mask = rtstruct.get_roi_mask_by_name(rois[i])

        if operators[i - 1] == "+":
            combined_mask = np.logical_or(combined_mask, roi_mask)
        elif operators[i - 1] == "-":
            combined_mask = np.logical_and(combined_mask, np.logical_not(roi_mask))
        else:
            raise ValueError(f"Invalid operator '{operators[i - 1]}'. Expected '+' or '-'.")

    return combined_mask
