FROM python:3.12-slim

WORKDIR /DICOM_solver

COPY DICOM_solver DICOM_solver
COPY main.py main.py
COPY requirements.txt requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/DICOM_solver"
ENV GRAPHDB_URL="http://host.docker.internal:7200/repositories/protrait/statements"

RUN pip install --no-cache-dir -r requirements.txt


CMD ["python", "main.py"]