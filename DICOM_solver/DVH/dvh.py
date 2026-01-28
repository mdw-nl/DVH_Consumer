from dicompylercore import dicomparser, dvh, dvhcalc
from uuid import uuid4
import numpy as np
import logging
import traceback
from .dicom_bundle import DicomBundle
from ..config_handler import Config


def prepare_output(dvh_points, structure, calc_dvh, dict_value_v, list_value_d):
    id_data = "http://data.local/ldcm-rt/" + str(uuid4())
    structOut = {
        "@id": id_data,
        "structureName": structure["name"],
        "min": {"@id": f"{id_data}/min", "unit": "Gray", "value": float(calc_dvh.min)},
        "mean": {"@id": f"{id_data}/mean", "unit": "Gray", "value": float(calc_dvh.mean)},
        "max": {"@id": f"{id_data}/max", "unit": "Gray", "value": float(calc_dvh.max)},
        "volume": {"@id": f"{id_data}/volume", "unit": "cc", "value": float(calc_dvh.volume)},
        #"D2": {"@id": f"{id_data}/D2", "unit": "Gray", "value": float(calc_dvh.D2.value)},
        #"D50": {"@id": f"{id_data}/D50", "unit": "Gray", "value": float(calc_dvh.D50.value)},
        #"D95": {"@id": f"{id_data}/D95", "unit": "Gray", "value": float(calc_dvh.D95.value)},
        #"D98": {"@id": f"{id_data}/D98", "unit": "Gray", "value": float(calc_dvh.D98.value)},
        "color": ','.join(str(e) for e in structure.get("color", np.array([])).tolist()),
        "dvh_curve": {
            "@id": f"{id_data}/dvh_curve",
            "dvh_points": dvh_points
        }
    }
    logging.info(f"Preparing additional DVH values for output...{dict_value_v}")
    for k, v in dict_value_v.items():
        logging.debug(f"Processing key: {k} with value: {v}")
        structOut[k] = {"@id": f"{id_data}/{k}", "unit": "Gray", "value": float(v)}
        logging.debug(f"Added {k} with value {v} to output.")

    for k in list_value_d:
        logging.debug(f"Processing {k}")
        structOut[k] = {"@id": f"{id_data}/{k}", "unit": "Gray", "value": float(getattr(calc_dvh, k).value)}
        logging.debug(f"Added {k} ")


    return structOut


class DVH_calculation:
    """
    Starting point for the dvh calculation.
    Base on the arguments that you provide you will query the data from a ttl file or from Graph service.
    Tested only on GraphDB
    """

    def read_config(self):
        pass

    def process_dvh_result(self, calculation_r, index, structures):
        """
        :param calculation_r:
        :param index:
        :param structures:
        """
        dvh_d = calculation_r.bincenters.tolist()
        dvh_v = calculation_r.counts.tolist()
        dvh_points = []
        dict_values_v = {}
        v_values = Config("V-values").config
        d_values = Config("D-values").config

        for i in range(0, len(dvh_d)):
            dvh_points.append({
                "d_point": dvh_d[i],
                "v_point": dvh_v[i]
            })
        for v in v_values:
            key = f"V{v}"
            try:
                dict_values_v[key] = float(getattr(calculation_r, f"V{v}").value)
                logging.info(f"Calculated dad {key}: {dict_values_v[key]}")
            except (AttributeError, ValueError, TypeError) as e:
                logging.warning(f"Value not available for {key}, setting to None.")
                logging.error(e)
                dict_values_v[key] = None
        d_value_list = ["D"+str(d) for d in d_values]

        structOut = prepare_output(dvh_points, structures[index], calculation_r, dict_values_v,d_value_list)
        n_s = structOut["structureName"]
        logging.info(f"Structure: {n_s}")
        return structOut

    def calculate_dvh_all(self, dicom_bundle: DicomBundle, structures, str_name=None):
        output = []
        # todo add function to select which structures use for the dvh calculation
        # ls = []
        if len(structures) > 0:
            for index in structures:

                logging.warning("Calculating structures " + str(structures[index]))
                if (str_name and structures[index]["name"] == str_name) or not str_name:
                    try:
                        calc_dvh = self.calculate_dvh(index, dicom_bundle)
                    except Exception as except_t:
                        logging.warning(except_t)
                        logging.warning("Error something wrong")
                        logging.warning(traceback.format_exc())
                        logging.warning("Skipping...")
                        continue
                    try:
                        logging.info("DVh calculation complete. Processing output...")
                        result = self.process_dvh_result(calc_dvh, index, structures)
                        output.append(result)
                    except Exception as e:
                        logging.info("error")
                        logging.warning(e)
                        logging.warning(traceback.format_exc())
                        continue
                else:
                    logging.info(f"Skipping structure {structures[index]['name']} as it is not in the list.")
        else:
            logging.info("NO structures")
        return output

    def calculate_dvh(self, index, dicom_bundle: DicomBundle):
        """
        :param dicom_bundle:
        :param index:
        :return:
        """
        # TODO check if multiple rt dose are in the dicom bundle. Also we need to add dose summation
        calc_dvh = self.get_dvh_v(structure=dicom_bundle.rt_struct, dose_data=dicom_bundle.rt_dose[0], roi=index,
                                  rt_plan_p=dicom_bundle.rt_plan)

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
