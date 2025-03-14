from abc import ABC, abstractmethod
from dicompylercore import dicomparser, dvh, dvhcalc
from uuid import uuid4
import numpy as np
import logging
import traceback



def prepare_output(dvh_points, structure, calc_dvh, dict_value):
    id_data = "http://data.local/ldcm-rt/" + str(uuid4())
    structOut = {
        "@id": id_data,
        "structureName": structure["name"],
        "min": {"@id": f"{id_data}/min", "unit": "Gray", "value": calc_dvh.min},
        "mean": {"@id": f"{id_data}/mean", "unit": "Gray", "value": calc_dvh.mean},
        "max": {"@id": f"{id_data}/max", "unit": "Gray", "value": calc_dvh.max},
        "volume": {"@id": f"{id_data}/volume", "unit": "cc", "value": int(calc_dvh.volume)},
        "D10": {"@id": f"{id_data}/D10", "unit": "Gray", "value": float(calc_dvh.D10.value)},
        "D20": {"@id": f"{id_data}/D20", "unit": "Gray", "value": float(calc_dvh.D20.value)},
        "D30": {"@id": f"{id_data}/D30", "unit": "Gray", "value": float(calc_dvh.D30.value)},
        "D40": {"@id": f"{id_data}/D40", "unit": "Gray", "value": float(calc_dvh.D40.value)},
        "D50": {"@id": f"{id_data}/D50", "unit": "Gray", "value": float(calc_dvh.D50.value)},
        "D60": {"@id": f"{id_data}/D60", "unit": "Gray", "value": float(calc_dvh.D60.value)},
        "V5": {"@id": f"{id_data}/V5", "unit": "Gray", "value": dict_value["V5value"]},
        "V10": {"@id": f"{id_data}/V10", "unit": "Gray", "value": dict_value["V10value"]},
        "V20": {"@id": f"{id_data}/V20", "unit": "Gray", "value": dict_value["V20value"]},
        "V30": {"@id": f"{id_data}/V5", "unit": "Gray", "value": dict_value["V30value"]},
        "V40": {"@id": f"{id_data}/V10", "unit": "Gray", "value": dict_value["V40value"]},
        "V50": {"@id": f"{id_data}/V20", "unit": "Gray", "value": dict_value["V50value"]},
        "V60": {"@id": f"{id_data}/V20", "unit": "Gray", "value": dict_value["V60value"]},
        "color": ','.join(str(e) for e in structure.get("color", np.array([])).tolist()),
        "dvh_curve": {
            "@id": f"{id_data}/dvh_curve",
            "dvh_points": dvh_points
        }
    }

    return structOut


class DVH_calculation:
    """
    Starting point for the dvh calculation.
    Base on the arguments that you provide you will query the data from a ttl file or from Graph service.
    Tested only on GraphDB
    """

    def __init__(self):
        """
        :param file_path:
        :param urls:
        """
        self.RT_plan = None
        self.RT_struct = None
        self.RT_dose = None
        self.output = []
        self.structures = None

    def get_RT_Struct(self, file_path):
        self.RT_struct = dicomparser.DicomParser(file_path)

    def get_RT_Plan(self, file_path):
        self.RT_plan = dicomparser.DicomParser(file_path)

    def get_RT_Dose(self, file_path):
        self.RT_dose = dicomparser.DicomParser(file_path)

    def get_structures(self):
        self.structures = self.RT_struct.GetStructures()

    def process_dvh_result(self, calculation_r, index):
        dvh_d = calculation_r.bincenters.tolist()
        dvh_v = calculation_r.counts.tolist()
        dvh_points = []
        dict_values = {}

        for i in range(0, len(dvh_d)):
            dvh_points.append({
                "d_point": dvh_d[i],
                "v_point": dvh_v[i]
            })
            for v in [5, 10, 20, 30, 40, 50, 60]:
                key = f"V{v}value"
                try:
                    dict_values[key] = float(getattr(calculation_r, f"V{v}").value)
                except (AttributeError, ValueError, TypeError) as e:
                    logging.warning(f"Value not available for {key}, setting to None.")
                    logging.error(e)

                    dict_values[key] = None

            structOut = prepare_output(dvh_points, self.structures[index], calculation_r, dict_values)
            self.output.append(structOut)

    def calculate_dvh_all(self):
        for index in self.structures:
            logging.warning("Calculating structures " + str(self.structures[index]))

            try:
                # calc_dvh = self.get_dvh_v(self.RT_struct, self.RT_dose, index, self.RT_plan)
                calc_dvh = self.calculate_dvh(index)
            except Exception as except_t:
                logging.warning(except_t)
                logging.warning("Error something wrong")
                logging.warning(traceback.format_exc())
                logging.warning("Skipping...")

                continue

            try:
                self.process_dvh_result(calc_dvh, index)
            except Exception as e:
                logging.info("error")
                logging.warning(e)
                logging.warning(traceback.format_exc())
                continue

    def calculate_dvh(self, index):
        """

        :param index:
        :return:
        """
        calc_dvh = self.get_dvh_v(structure=self.RT_struct, dose_data=self.RT_dose, roi=index, rt_plan_p=self.RT_plan)

        return calc_dvh

    def get_dvh_v(self, structure,
                  dose_data,
                  roi,
                  rt_plan_p=None,
                  limit=None,
                  calculate_full_volume=True,
                  use_structure_extents=False,
                  interpolation_resolution=None,
                  interpolation_segments_between_planes=0,
                  thickness=None,
                  memmap_rtdose=False,
                  callback=None):
        """Calculate a cumulative DVH in Gy from a DICOM RT Structure Set & Dose.
            Take as input the RTplan to calculate the Vx (v10,20 etc..)

        Parameters
        ----------
        structure : pydicom Dataset or filename
            DICOM RT Structure Set used to determine the structure data.
        dose_data : pydicom Dataset or filename
            DICOM RT Dose used to determine the dose grid.
        roi : int
            The ROI number used to uniquely identify the structure in the structure
            set.
        rt_plan_p : pydicom Dataset or filename
            DICOM RT plan path

        limit : int, optional
            Dose limit in cGy as a maximum bin for the histogram.
        calculate_full_volume : bool, optional
            Calculate the full structure volume including contours outside the
            dose grid.
        use_structure_extents : bool, optional
            Limit the DVH calculation to the in-plane structure boundaries.
        interpolation_resolution : tuple or float, optional
            Resolution in mm (row, col) to interpolate structure and dose data to.
            If float is provided, original dose grid pixel spacing must be square.
        interpolation_segments_between_planes : integer, optional
            Number of segments to interpolate between structure slices.
        thickness : float, optional
            Structure thickness used to calculate volume of a voxel.
        memmap_rtdose : bool, optional
            Use memory mapping to access the pixel array of the DICOM RT Dose.
            This reduces memory usage at the expense of increased calculation time.
        callback : function, optional
            A function that will be called at every iteration of the calculation.

        Returns
        -------
        dvh.DVH
            An instance of dvh.DVH in cumulative dose. This can be converted to
            different formats using the attributes and properties of the DVH class.
        """

        rt_str = structure
        if type(dose_data) is str:
            rt_dose = dicomparser.DicomParser(dose_data, memmap_pixel_array=memmap_rtdose)
        else:
            rt_dose = dose_data
        structures = rt_str.GetStructures()
        s = structures[roi]
        logging.debug(f"Structure selected {s}")
        s['planes'] = rt_str.GetStructureCoordinates(roi)
        s['thickness'] = thickness if thickness else rt_str.CalculatePlaneThickness(
            s['planes'])

        calc_dvh = dvhcalc._calculate_dvh(s, rt_dose, limit, calculate_full_volume,
                                          use_structure_extents, interpolation_resolution,
                                          interpolation_segments_between_planes,
                                          callback)
        if rt_plan_p is not None:
            rt_plan = rt_plan_p

            plan = rt_plan.GetPlan()
            if plan['rxdose'] is not None:
                logging.debug("rx dose does exist in the rt plan")

                return dvh.DVH(counts=calc_dvh.histogram,
                               bins=(np.arange(0, 2) if (calc_dvh.histogram.size == 1) else
                                     np.arange(0, calc_dvh.histogram.size + 1) / 100),
                               dvh_type='differential',
                               dose_units='Gy',
                               notes=calc_dvh.notes,
                               name=s['name'],
                               rx_dose=plan['rxdose'] / 100).cumulative
            else:
                logging.debug("rx dose does not exist in the rt plan")
                return dvh.DVH(counts=calc_dvh.histogram,
                               bins=(np.arange(0, 2) if (calc_dvh.histogram.size == 1) else
                                     np.arange(0, calc_dvh.histogram.size + 1) / 100),
                               dvh_type='differential',
                               dose_units='Gy',
                               notes=calc_dvh.notes,
                               name=s['name']).cumulative
        else:
            return dvh.DVH(counts=calc_dvh.histogram,
                           bins=(np.arange(0, 2) if (calc_dvh.histogram.size == 1) else
                                 np.arange(0, calc_dvh.histogram.size + 1) / 100),
                           dvh_type='differential',
                           dose_units='Gy',
                           notes=calc_dvh.notes,
                           name=s['name']).cumulative
