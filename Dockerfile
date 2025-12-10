FROM python:3.12-slim

WORKDIR /DICOM_solver

COPY DICOM_solver DICOM_solver
COPY main.py main.py
COPY requirements.txt requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/DICOM_solver"
ENV DELETE_END=True

RUN pip install --no-cache-dir -r requirements.txt
# Required for rtutils
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000
CMD ["python", "main.py"]