FROM python:3.12-slim

WORKDIR /DICOM_solver

COPY DICOM_solver DICOM_solver
COPY main.py main.py
COPY output output
COPY requirements.txt requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/DICOM_solver"

RUN pip install --no-cache-dir -r requirements.txt


CMD ["python", "main.py"]