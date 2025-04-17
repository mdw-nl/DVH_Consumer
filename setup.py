from setuptools import setup, find_packages

# Read dependencies from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="DICOM_solver",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,  # Use requirements.txt dependencies
    python_requires=">=3.7",
)