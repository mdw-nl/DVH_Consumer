from dicompylercore.dicomparser import DicomParser

class DicomBundle:

    def __init__(self, patient_id, rt_plan: DicomParser, rt_struct: DicomParser, rt_dose: DicomParser, rt_ct: DicomParser):
        self.patient_id = patient_id
        self.rt_plan: DicomParser = rt_plan
        self.rt_struct: DicomParser = rt_struct
        self.rt_dose: DicomParser = rt_dose
        self.rt_ct: DicomParser = rt_ct

    
    def __eq__(self, other):
        if not isinstance(other, DicomBundle):
            return False
        if self.ct == other.ct and self.p_id == other.p_id and self.rt_plan == other.rt_plan and \
                self.rt_dose == other.rt_dose and self.rt_struct == other.rt_struct:
            return True
        else:
            return False