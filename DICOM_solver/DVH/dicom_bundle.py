from dicompylercore.dicomparser import DicomParser
import logging


class DicomBundle:

    def __init__(self, patient_id, rt_plan: str, rt_struct: str, rt_dose: [],
                 rt_ct: str, read=True):
        self.patient_id = patient_id
        self.rt_plan_path = rt_plan
        self.rt_struct_path: str = rt_struct
        self.rt_ct_path: str = rt_ct[:rt_ct.rindex("/") + 1]
        if read:
            self.rt_plan: DicomParser = DicomParser(rt_plan)
            self.rt_struct: DicomParser = DicomParser(rt_struct)
            self.rt_dose: [] = [DicomParser(rt) for rt in rt_dose]
        logging.info(f"Ct path is {self.rt_ct_path}")

    def __eq__(self, other):
        if not isinstance(other, DicomBundle):
            return False
        if self.rt_plan_path == other.rt_plan_path and self.rt_ct_path == other.rt_ct_path and \
                self.rt_struct_path == other.rt_struct_path:

            return True
        else:
            return False
