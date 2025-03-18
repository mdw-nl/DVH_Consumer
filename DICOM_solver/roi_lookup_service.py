import yaml

class RoiLookupService:
    rois = dict()

    def __init__(self):
        with open('roi_name_mappings.yaml', 'r') as file:
            roiNameObject = yaml.safe_load(file)
            for standardName, synonymList in roiNameObject.items():
                for synonym in synonymList:
                    self.rois[synonym] = standardName

    def get_standardized_name(self, synonym):
        try:
            standardized_name = self.rois[synonym]
        except KeyError:
            standardized_name = None
        return standardized_name
