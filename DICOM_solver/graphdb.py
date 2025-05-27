import logging

import requests
import json
import traceback


def upload_jsonld_to_graphdb(jsonld_data, graphdb_url):
    """
    Uploads a JSON-LD dictionary to a GraphDB repository via the REST API.

    :param jsonld_data: The JSON-LD data to upload (as a Python dictionary).
    :param graphdb_url: The GraphDB repository URL for uploading the data (including the `/statements` endpoint).

    :return: A response message indicating success or failure.
    """
    # Headers to indicate that we are sending JSON-LD data
    headers = {
        "Content-Type": "application/ld+json"
    }
    logging.info(f"Uploading")
    try:
        # Sending POST request to the GraphDB REST API
        response = requests.post(graphdb_url, headers=headers, data=json.dumps(jsonld_data))

        # Check if the request was successful
        if response.status_code in [200, 204]:
            logging.info("Success upload..")

        else:
            logging.warning(response.status_code)
            logging.warning(response.text)
            logging.warning(f"Failed to upload data. Status code: {response.status_code}, {response.text}")
            raise Exception


    except Exception as e:
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(f"Exception Message: {e}")
        logging.warning("Error something wrong")
        logging.warning(traceback.format_exc())
        raise e


"""if __name__ == "__main__":
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
        "@id": "http://data.local/ldcm-rt/" + str("12321414"),
        "PatientID": "111",
        "doseFraction": 0,
        "references": ["", ""],
        "software": {
            "@id": "https://github.com/dicompyler/dicompyler-core",
            "version": "nada"
        },
        "dateCreated": datetime.datetime.now().isoformat(),
        "containsStructureDose": ["Nada"]
    }
    upload_jsonld_to_graphdb(resultDict,"http://localhost:7200/repositories/protrait/statements")




"""
