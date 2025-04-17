from dicompylercore.dicomparser import DicomParser
import logging


class DicomBundle:

    def __init__(self, patient_id, rt_plan: str, rt_struct: str, rt_dose: [],
                 rt_ct: str):
        self.patient_id = patient_id
        self.rt_plan: DicomParser = DicomParser(rt_plan)
        self.rt_plan_path = rt_plan
        self.rt_struct: DicomParser = DicomParser(rt_struct)
        self.rt_struct_path: str = rt_struct
        self.rt_dose: [] = [DicomParser(rt) for rt in rt_dose]
        self.rt_ct_path: str = rt_ct[:rt_ct.rindex("/") + 1]
        logging.info(f"Ct path is {self.rt_ct_path}")

    # def __eq__(self, other):
    #    if not isinstance(other, DicomBundle):
    #        return False
    #    if self.rt_ct == other.rt_ct and self.rt_ct == other.rt_ct and self.rt_plan == other.rt_plan and \
    #            self.rt_dose == other.rt_dose and self.rt_struct == other.rt_struct:
    #        return True
    #    else:
    #        return False
