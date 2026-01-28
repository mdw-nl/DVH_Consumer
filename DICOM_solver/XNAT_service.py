import json
import logging
import pydicom
import os
import requests
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth
from DICOM_solver.queue_processing import Consumer
from DICOM_solver.config_handler import Config
import xml.etree.ElementTree as ET
import xmltodict


class upload_XNAT:

    def __init__(self):
        self.path = "DVH_data"
        self.message_folder = "messages"
        self.output_file = "message.json"

        os.makedirs(self.path, exist_ok=True)

    def create_json_metadata(self, dicom_bundle):
        ds = pydicom.dcmread(
            dicom_bundle.rt_struct_path,
            stop_before_pixels=True
        )

        info_dict = {
            "project": str(ds.BodyPartExamined),
            "subject": str(ds.PatientName),
            "experiment": str(ds.StudyInstanceUID).replace(".", "_")
        }

        info_path = os.path.join(self.path, "metadata_xnat.json")
        with open(info_path, "w") as f:
            json.dump(info_dict, f, indent=4)

        logging.info(f"Metadata saved to {info_path}")

    def save_DVH(self, output):
        dvh_path = os.path.join(self.path, "DVH.json")
        with open(dvh_path, "w") as f:
            json.dump(output, f, indent=4)

        logging.info(f"DVH saved to {dvh_path}")

    def _send_to_next_queue(self, queue, data_folder):
        output_file_path = os.path.join(
            self.message_folder,
            self.output_file
        )
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        message = {
            "folder_path": data_folder,
            "action": queue
        }

        with open(output_file_path, "w") as file:
            json.dump(message, file, indent=2)

        logging.info(f"RabbitMQ message created at: {output_file_path}")

        rabbitmq_config = Config(queue)
        consumer = Consumer(rmq_config=rabbitmq_config)
        consumer.open_connection_rmq()
        consumer.send_message(self.message_folder)

        logging.info(f"Sent data {data_folder} to queue '{queue}'")

    def run(self, output, dicom_bundle):
        self.create_json_metadata(dicom_bundle)
        self.save_DVH(output)
        self._send_to_next_queue("xnat", self.path)
        

class XNATRetriever:
    """
    Retrieve RTDOSE, RTPLAN, RTSTRUCT, and CTs from XNAT
    using patient ID and SOPInstanceUID.
    """

    def __init__(self, username="admin", password="admin", base_url="http://localhost:8080"):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.base_url_projects = f"{self.base_url}/data/projects"

    def _get(self, url):
        """Authenticated GET request"""
        resp = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()

        # dict for JSON responses
        if "application/json" in content_type:
            return resp.json()

        # dict for XML respnses
        if "xml" in content_type:
            return xmltodict.parse(resp.text)

        raise ValueError(
            f"Unsupported Content-Type '{content_type}' for URL {url}"
        )

    def get_projects(self):
        """Return dict of project nameL"""
        data = self._get(self.base_url_projects)
        projects = data.get("ResultSet", {}).get("Result", [])
        project_urls = {
            proj["name"]: f"{self.base_url_projects}/{proj['ID']}/subjects"
            for proj in projects
        }
        return project_urls
        
    def get_subjects(self, project_url):
            """Return dict of subject label"""
            subjects_data = self._get(project_url).get("ResultSet", {}).get("Result", [])
            subjects = {}
            for subj in subjects_data:
                subject_url = f"{project_url}/{subj['ID']}/experiments"
                subjects[subj["label"]] = subject_url
            return subjects
        
    def get_experiments(self, subject_url):
        """Return dict of experiment label → scans URL"""
        experiments_data = self._get(subject_url).get("ResultSet", {}).get("Result", [])
        experiments = {}
        for exp in experiments_data:
            scans_url = f"{subject_url}/{exp['ID']}/scans"
            experiments[exp["label"]] = scans_url
        return experiments
    
    def get_scans(self, scans_url):
        """Return list of scan info dicts"""
        scans_data = self._get(scans_url).get("ResultSet", {}).get("Result", [])
        return scans_data
    

    def get_dicom_catalog(self, scan_uri):
        """Retrieve the DICOM catalog XML for a scan"""
        url = f"{self.base_url}{scan_uri}/resources/DICOM"
        resp = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
        resp.raise_for_status()
        return resp.text
    

    def extract_and_check_sopinstance_entries(self, catalog_dict, SOPinstanceUID):
        """Extract SOPInstanceUIDs and file URIs from an XNAT DICOM catalog. Also checks if SOPinstanceUID correspond"""
        try:
            entries = (
                catalog_dict
                .get("cat:DCMCatalog", {})
                .get("cat:entries", {})
                .get("cat:entry", [])
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("Invalid catalog structure") from exc

        if isinstance(entries, dict):
            entries = [entries]

        for entry in entries:
            sop_uid = entry.get("@UID")
            file_uri = entry.get("@URI")

            if not sop_uid or not file_uri:
                continue

            if sop_uid == SOPinstanceUID:
                return {
                    "sop_uid": sop_uid,
                    "file_uri": file_uri,
                    "filename": entry.get("@ID"),
                    "format": entry.get("@format"),
                }

        # No matching SOPInstanceUID found
        return False
    
    def download_dicom_to_file(self, url, out_dir, filename):
        """Download a DICOM file from XNAT"""
        os.makedirs(out_dir, exist_ok=True)

        out_path = os.path.join(out_dir, filename)

        with requests.get(
            url,
            auth=HTTPBasicAuth(self.username, self.password),
            stream=True
        ) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return out_path

    def check_patient_location(self,  patient_name, patient_id):
        """Return a list of all the urls where the patient name and is found in xnat"""
        self.patient_urls = []
        
        projects = self.get_projects()
        for project in projects:
            subjects = self.get_subjects(projects[project])

            if patient_name not in subjects:
                continue

            experiments = self.get_experiments(subjects[patient_name])

            if patient_id not in experiments:
                continue
            
            url = experiments[patient_id]
            self.patient_urls.append(url)

    
    def get_rtdose(self, SOPinstanceUID):
        """Download the RTDOSE based on patient_name, patient_id, and SOPInstanceUID from XNAT"""

        # Loop over all patient experiment URLs where the patient exists
        for url in self.patient_urls:
            scans = self.get_scans(url)

            # Iterate through each scan looking for RTDOSE series
            for scan in scans:
                # Build the URL to the DICOM resource for this scan
                uri = scan["URI"]
                url = self.base_url + uri + "/resources/DICOM"
                    
                try:
                    catalog = self._get(url)
                except Exception as e:
                    continue
                
                uid = self.extract_and_check_sopinstance_entries(catalog, SOPinstanceUID)
                if uid is False:  # Skip if SOPInstanceUID not found
                    continue
                
                folder_path = "data/xnat_listener"
                file_name = f"rt_dose_{uid['filename']}"
                
                donwload_url = f"{url}/files/{uid['file_uri']}"
                
                # Download the RTDOSE file to the local directory
                self.download_dicom_to_file(donwload_url, folder_path, file_name)
                
                return os.path.join(folder_path, file_name)
        raise FileNotFoundError(f"SOPInstanceUID {SOPinstanceUID} not found for this patient.")    
        
    def download_by_sop(self, sop):
        """Download the RTPLAN file corresponding to a given RTDOSE."""
        # Read RTDOSE to get the referenced RTPLAN SOPInstanceUID

        for patient_url in self.patient_urls:
            scans = self.get_scans(patient_url)

            for scan in scans:
                scan_uri = scan["URI"]

                # Fetch available resources for this scan
                resources_url = f"{self.base_url}{scan_uri}/resources"
                resources_catalog = self._get(resources_url)
                resources = resources_catalog.get("ResultSet", {}).get("Result", [])
                for resource in resources:
                    resource_uri = resource["content"]
                    dicom_resource_url = f"{self.base_url}{scan_uri}/resources/{resource_uri}"
                    try:
                        catalog_dict = self._get(dicom_resource_url)
                    except Exception as e:
                        continue
                    
                    uid_entry = self.extract_and_check_sopinstance_entries(catalog_dict, sop)
                
                    if not uid_entry:
                        continue
                    # Build download URL and save locally
                    download_url = f"{dicom_resource_url}/files/{uid_entry['file_uri']}"
                    filename = f"{uid_entry['filename']}"
                    folder_path = "data/xnat_listener"
                    
                    self.download_dicom_to_file(download_url, folder_path, filename)
                    return os.path.join(folder_path, filename)
        raise FileNotFoundError(f"SOPInstanceUID {sop} not found for this patient.")
            


    def run(self, patient_name, patient_id, dose_SOPinstanceUID):
        self.check_patient_location(patient_name, patient_id)

        rtdose_path = self.get_rtdose(dose_SOPinstanceUID)

        ds_dose = pydicom.dcmread(rtdose_path)
        try:
            rtplan_sop = ds_dose.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
        except (AttributeError, IndexError):
            raise ValueError("RTDOSE does not reference any RTPLAN.")

        rtplan_path = self.download_by_sop(rtplan_sop)

        ds_plan = pydicom.dcmread(rtplan_path)
        try:
            rtstruct_sop = ds_plan.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
        except (AttributeError, IndexError):
            raise ValueError("RTPLAN does not reference any RTSTRUCT.")

        rtstruct_path = self.download_by_sop(rtstruct_sop)

        
if __name__ == "__main__":
    retriever = XNATRetriever(base_url="http://localhost:8080", username="admin", password="admin")
    patient_name = "SEDI_TEST001"
    patient_id = "99999_8088316119225601241627216725805872478376234007905444525746"
    SOPinstanceUID = "99999.1254976680351246889122584535917886712943150884553757806011"
    retriever.run(patient_name, patient_id, SOPinstanceUID)
