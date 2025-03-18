
from typing import List
from array import array
import numpy as np
from rt_utils import RTStruct

def combine_rois(rtstruct: RTStruct, rois: List[str], operators: List[str]) -> array[bool]:
    assert rois.__len__() - 1 == operators.__len__(), "There should be exactly one operator less than the number of ROIs in order to combine the ROIs."
    combined_mask = np.zeros((512, 512, 290), dtype=bool)
    operatorCount = -1
    for roi in rois:
        roiMask = rtstruct.get_roi_mask_by_name(roi)
        if operatorCount == -1:
            combinedMask = roiMask
        if operators[operatorCount] == "+":
            combined_mask = np.logical_or(combinedMask, roiMask)
        elif operators[operatorCount] == "-":
            combined_mask = np.logical_and(combinedMask, np.logical_not(roiMask))
        operatorCount += 1
    print(f"Mask for {roi}: {combined_mask}")
    return combined_mask
