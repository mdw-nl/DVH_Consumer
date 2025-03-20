
from typing import List
from array import array
import numpy as np
from rt_utils import RTStruct

def combine_rois(rtstruct: RTStruct, rois: List[str], operators: List[str]) -> array[bool]:    
    assert len(rois) - 1 == len(operators), "There should be exactly one operator less than the number of ROIs."

    # Sort the rois based on the operators, so that first the additiosn is done and then the substractions.
    # This will make sure that the order of the operations does not matter
    roi_operator_pairs = list(zip(rois[1:], operators))
    sorted_pairs = sorted(roi_operator_pairs, key=lambda x: x[1] == "-")  # "-" evaluates to True (1), so it moves to the end
    sorted_rois, sorted_operators = zip(*sorted_pairs) if sorted_pairs else ([], [])

    # Initiate the combined mask based on the first ROI
    combined_mask = rtstruct.get_roi_mask_by_name(rois[0])

    # Iterate through the sorted ROIs and operators
    for roi, operator in zip(sorted_rois, sorted_operators):
        roi_mask = rtstruct.get_roi_mask_by_name(roi)

        if operator == "+":
            combined_mask = np.logical_or(combined_mask, roi_mask)
        elif operator == "-":
            combined_mask = np.logical_and(combined_mask, np.logical_not(roi_mask))
        else:
            raise ValueError(f"Invalid operator '{operator}'. Expected '+' or '-'.")

    return combined_mask