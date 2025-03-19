
import datetime
import dicompylercore
from uuid import uuid4
import json
import os
import logging
from ..graphdb import upload_jsonld_to_graphdb
from ..config_handler import Config



class DVH_Output:
    def __init__(self):
        self.structure_name = None,
        self.min = None
        self.max = None
        self.mean = None
        self.volume = None


def return_output(patient_id, calculatedDose):
    """


    :param patient_id:
    :param calculatedDose:

    :return:
    """

    uuid_for_calculation = uuid4()
    gdb = Config("GraphDB")
    config_dict_gdb = gdb.config
    host = config_dict_gdb["host"]
    port = config_dict_gdb["port"]
    repo = config_dict_gdb["repo"]
    graphdb_url = f"http://{host}:{port}/repositories/{repo}/statements"

    for j in calculatedDose:
        resultDict = {
            "@context": {
                "CalculationResult": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/CalculationResult",
                "PatientID": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/PatientIdentifier",
                "doseFraction": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/DoseFractionNumbers",
                "references": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/references",
                    "@type": "@id"
                },
                "software": {
                    "@id": "https://schema.org/SoftwareApplication",
                    "@type": "@id"
                },
                "version": "https://schema.org/version",
                "dateCreated": "https://schema.org/dateCreated",
                "containsStructureDose": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/containsStructureDose",
                    "@type": "@id"
                },
                "structureName": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/structureName",
                "min": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/min",
                    "@type": "@id"
                },
                "mean": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/mean",
                    "@type": "@id"
                },
                "max": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/max",
                    "@type": "@id"
                },
                "volume": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/volume",
                    "@type": "@id"
                },
                "D10": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/D10",
                    "@type": "@id"
                },
                "D20": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/D20",
                    "@type": "@id"
                },
                "D30": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/D30",
                    "@type": "@id"
                },
                "D40": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/D40",
                    "@type": "@id"
                },
                "D50": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/D50",
                    "@type": "@id"
                },
                "D60": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/D60",
                    "@type": "@id"
                },
                "V5": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/V5",
                    "@type": "@id"
                },
                "V10": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/V10",
                    "@type": "@id"
                },
                "V20": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/V20",
                    "@type": "@id"
                },
                "dvh_points": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/dvh_point",
                    "@type": "@id"
                },
                "dvh_curve": {
                    "@id": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/dvh_curve",
                    "@type": "@id"
                },
                "d_point": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/dvh_d_point",
                "v_point": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/dvh_v_point",
                "Gray": "http://purl.obolibrary.org/obo/UO_0000134",
                "cc": "http://purl.obolibrary.org/obo/UO_0000097",
                "unit": "@type",
                "value": "https://schema.org/value",
                "has_color": "https://johanvansoest.nl/ontologies/LinkedDicom-dvh/has_color"
            },
            "@type": "CalculationResult",
            "@id": "http://data.local/ldcm-rt/" + str(uuid_for_calculation),
            "PatientID": patient_id,
            "doseFraction": 0,
            "references": ["", ""],
            "software": {
                "@id": "https://github.com/dicompyler/dicompyler-core",
                "version": dicompylercore.__version__
            },
            "dateCreated": datetime.datetime.now().isoformat(),
            "containsStructureDose": [j]
        }
        upload_jsonld_to_graphdb(resultDict, graphdb_url=graphdb_url)


