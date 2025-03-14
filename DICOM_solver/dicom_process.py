class dicom_object:
    def __init__(self, p_id, ct, rtplan, rtdose, rtstruct):
        self.p_id = p_id
        self.rt_plan = rtplan
        self.rt_struct = rtstruct
        self.rt_dose = rtdose
        self.ct = ct
