from dicompylercore.dicomparser import DicomParser

class DicomBundle:

    def __init__(self, rt_plan: DicomParser, rt_struct: DicomParser, rt_dose: DicomParser, rt_ct: DicomParser):
        self.rt_plan: DicomParser = rt_plan
        self.rt_struct: DicomParser = rt_struct
        self.rt_dose: DicomParser = rt_dose
        self.rt_ct: DicomParser = rt_ct