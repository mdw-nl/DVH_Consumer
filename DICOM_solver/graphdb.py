import logging

import requests
import traceback
from .config_handler import Config


def upload_jsonld_to_graphdb(jsonld_data, graphdb_url):
    """
    Uploads a JSON-LD dictionary to a GraphDB repository via the REST API.

    :param jsonld_data: The JSON-LD data to upload (as a Python dictionary).
    :param graphdb_url: The GraphDB repository URL for uploading the data (including the `/statements` endpoint).

    :return: A response message indicating success or failure.
    """
    gdb = Config("API")
    config_dict_api = gdb.config
    host = config_dict_api["host"]
    port = config_dict_api["port"]
    logging.info(f"GraphDB URL: {graphdb_url}, Host: {host}, Port: {port}")
    # Headers to indicate that we are sending JSON-LD data
    headers = {
        "Content-Type": "application/ld+json"
    }
    logging.info(f"Uploading")
    params = {"endpoint": graphdb_url}
    try:
        url = f"http://{host}:{port}/upload_json"

        response = requests.post(
            url,
            headers=headers,
            json=jsonld_data,
            params=params
        )

        # Check if the request was successful
        if response.status_code in [200, 204]:
            logging.info("Success upload..")

        else:
            logging.warning(response.status_code)
            logging.warning(response.text)
            logging.warning(f"Failed to upload data. Status code: {response.status_code}, {response.text}")
            raise Exception(
                f"Failed to upload data to GraphDB. Status code: {response.status_code}, {response.text}"
            )

    except Exception as e:
        logging.warning(f"Exception Type: {type(e).__name__}")
        logging.warning(f"Exception Message: {e}")
        logging.warning("Error something wrong")
        logging.warning(traceback.format_exc())
        raise e
