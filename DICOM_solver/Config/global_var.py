NUMBER_ATTEMPTS = 5
RETRY_DELAY_IN_SECONDS = 10
#QUERY_UID = "Select * from public.dicom_insert where study_instance_uid ='{uid}';"
QUERY_UID = "SELECT * FROM public.dicom_insert WHERE study_instance_uid = %s;"