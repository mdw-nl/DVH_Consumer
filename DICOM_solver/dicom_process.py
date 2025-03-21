class dicom_object:
    def __init__(self, p_id, ct, rtplan, rtdose, rtstruct):
        self.p_id = p_id
        self.rt_plan = rtplan
        self.rt_struct = rtstruct
        self.rt_dose = rtdose
        self.ct = ct

    def __eq__(self, other):
        if not isinstance(other, dicom_object):
            return False
        if self.ct == other.ct and self.p_id == other.p_id and self.rt_plan == other.rt_plan and \
                self.rt_dose == other.rt_dose and self.rt_struct == other.rt_struct:
            return True
        else:
            return False
