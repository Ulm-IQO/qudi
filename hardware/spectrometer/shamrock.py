# -*- coding: utf-8 -*-
"""
This module interface Shamrock spectrometer from Andor.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
na=not applicable
"""
import os
import numpy as np
import ctypes as ct

from core.module import Base
from core.configoption import ConfigOption

from interface.grating_spectrometer_interface import GratingSpectrometerInterface
from interface.grating_spectrometer_interface import Grating, PortType, Port, Constraints

ERROR_CODE = {
    20201: "SHAMROCK_COMMUNICATION_ERROR",
    20202: "SHAMROCK_SUCCESS",
    20266: "SHAMROCK_P1INVALID",
    20267: "SHAMROCK_P2INVALID",
    20268: "SHAMROCK_P3INVALID",
    20269: "SHAMROCK_P4INVALID",
    20270: "SHAMROCK_P5INVALID",
    20275: "SHAMROCK_NOT_INITIALIZED"
}

OK_CODE = 20202  # Status code associated with DRV_SUCCESS

INPUT_CODE = 1
OUTPUT_CODE = 2

FRONT_CODE = 0
SIDE_CODE = 1


class Shamrock(Base, GratingSpectrometerInterface):
    """ Hardware module that interface a Shamrock spectrometer from Andor

    Tested with :
    - Shamrock 500

    Example config for copy-paste:

    shamrock:
        module.Class: 'spectrometer.shamrock.Shamrock'
    """

    _dll_path = ConfigOption('dll_path', r'C:\Program Files\Andor SDK\Shamrock64\C\All')
    # for some reason, the dll in Shamrock64 doesn't work..
    _serial_number = ConfigOption('serial_number', None)  # Optional - needed if multiple Shamrock are connected

    SLIT_MIN_WIDTH = 10e-6  # todo: can this be get from the DLL ? Or else is it the same for ALL spectro ? If not, maybe a config option ?
    SLIT_MAX_WIDTH = 2500e-6  # todo: same

    # Declarations of attributes to make Pycharm happy
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._constraints = None
        self._dll = None
        self._shutter_status = None
        self._device_id = None

    ##############################################################################
    #                            Basic functions
    ##############################################################################
    def on_activate(self):
        """ Activate module """
        os.environ['PATH'] = os.environ['PATH']+';' if os.environ['PATH'][-1] != ';' else os.environ['PATH']
        os.environ['PATH'] += self._dll_path

        try:
            self._dll = ct.windll.LoadLibrary('ShamrockCIF.dll')
        except OSError:
            self.log.error('Error during dll loading of the Shamrock spectrometer, check the dll path.')
            return

        status_code = self._dll.ShamrockInitialize()
        if status_code != OK_CODE:
            self.log.error('Problem during Shamrock initialization')
            return

        if self._serial_number is not None:
            # Check that the right hardware is connected and connect to the right one
            devices = self._get_connected_devices()
            target = str(self._serial_number)
            if target in devices:
                self._device_id = devices.index(target)
            else:
                self.log.error('Serial number {} not found in connected devices : {}'.format(target, devices))
                return
        else:
            self._device_id = 0

        self._constraints = self._build_constraints()

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        return self._dll.ShamrockClose()

    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only once by on_activate
         """
        constraints = Constraints()

        optical_param = self._get_optical_parameters()
        constraints.focal_length = optical_param['focal_length']
        constraints.angular_deviation = optical_param['angular_deviation']
        constraints.focal_tilt = optical_param['focal_tilt']

        number_of_gratings = self._get_number_gratings()
        for i in range(number_of_gratings):
            grating_info = self._get_grating_info(i)
            grating = Grating()
            grating.ruling = grating_info['ruling']
            grating.blaze = grating_info['blaze']
            grating.wavelength_max = self._get_wavelength_limit(i)[1]
            constraints.gratings.append(grating)

        # Add the ports one by one
        input_port_front = Port(PortType.INPUT_FRONT)
        input_port_front.is_motorized = self._auto_slit_is_present('input', 'front')
        constraints.ports.append(input_port_front)

        if self._flipper_mirror_is_present('input'):
            input_port_side = Port(PortType.INPUT_SIDE)
            input_port_side.is_motorized = self._auto_slit_is_present('input', 'side')
            constraints.ports.append(input_port_side)

        output_port_front = Port(PortType.OUTPUT_FRONT)
        output_port_front.is_motorized = self._auto_slit_is_present('output', 'front')
        constraints.ports.append(output_port_front)

        if self._flipper_mirror_is_present('output'):
            output_port_side = Port(PortType.OUTPUT_SIDE)
            output_port_side.is_motorized = self._auto_slit_is_present('output', 'side')
            constraints.ports.append(output_port_side)

        for port in constraints.ports:
            port.constraints.min = self.SLIT_MIN_WIDTH
            port.constraints.max = self.SLIT_MAX_WIDTH

        return constraints

    ##############################################################################
    #                            DLL useful functions
    ##############################################################################
    def _check(self, status_code):
        """ Check routine for the received error codes.

        @param (int) status_code: The code returned by the DLL

        @return (int): The code given in parameter is returned """
        if status_code != OK_CODE:
            self.log.error('Error in Shamrock with error code {}: {}'.format(status_code, ERROR_CODE[status_code]))
        return status_code

    ##############################################################################
    #                            Interface functions
    ##############################################################################
    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware

        Tested
        """
        return self._constraints

    def get_ready_state(self):
        """ Get the status of the camera, to know if the acquisition is finished or still ongoing.

        @return (bool): True if the camera is ready, False if an acquisition is ongoing

        As there is no synchronous acquisition in the interface, the logic needs a way to check the acquisition state.
        """
        return self.module_state() == "idle"

    def get_grating(self):
        """ Returns the current grating index

        @return (int): Current grating index

        Tested
        """
        grating = ct.c_int()
        self._check(self._dll.ShamrockGetGrating(self._device_id, ct.byref(grating)))
        return grating.value-1  # DLL starts at 1

    def set_grating(self, value):
        """ Sets the grating by index

        @param (int) value: grating index

        Tested
        """
        self._check(self._dll.ShamrockSetGrating(self._device_id, value+1))  # DLL starts at 1

    def get_wavelength(self):
        """ Returns the current central wavelength in meter

        @return (float): current central wavelength (meter)

        Tested - si
        """
        wavelength = ct.c_float()
        self._check(self._dll.ShamrockGetWavelength(self._device_id, ct.byref(wavelength)))
        return wavelength.value * 1e-9

    def set_wavelength(self, value):
        """ Sets the new central wavelength in meter

        @params (float) value: The new central wavelength (meter)

        Tested - si - go to 0 order
        """
        maxi = self.get_constraints().gratings[self._device_id].wavelength_max
        if 0 <= value <= maxi:
            self._dll.ShamrockSetWavelength.argtypes = [ct.c_int32, ct.c_float]
            self._check(self._dll.ShamrockSetWavelength(self._device_id, value * 1e9))
        else:
            self.log.error('The wavelength {} is not in the range {}, {}'.format(value*1e9, 0, maxi*1e9))

    def get_spectrometer_dispersion(self, number_pixels, pixel_width):
        """ Returns the wavelength calibration of each pixel

        Shamrock DLL can give an estimation of the calibration if the required parameters are given.
        This feature is not used by Qudi but is useful to check everything is ok.

        """
        self._set_number_of_pixels(number_pixels)
        self._set_pixel_width(pixel_width)
        wl_array = np.ones((number_pixels,), dtype=np.float32)
        self._dll.ShamrockGetCalibration.argtypes = [ct.c_int32, ct.c_void_p, ct.c_int32]
        self._check(self._dll.ShamrockGetCalibration(self._device_id, wl_array.ctypes.data, number_pixels))
        return wl_array*1e-9  # DLL uses nanometer

    def get_input_port(self):
        """ Returns the current input port

        @return (PortType): current port side

        Tested
        """
        input_port = ct.c_int()
        self._dll.ShamrockGetFlipperMirror(self._device_id, INPUT_CODE, ct.byref(input_port))
        return PortType.INPUT_FRONT if input_port.value == FRONT_CODE else PortType.INPUT_SIDE

    def set_input_port(self, value):
        """ Set the current input port

        @param (PortType) value: The port side to set

        Tested
        """
        if not value in PortType:
            self.log.error('Function parameter is not a PortType value ')
            return
        if value in [PortType.OUTPUT_FRONT, PortType.OUTPUT_SIDE]:
            self.log.error('Function parameter must be an INPUT value of PortType ')
            return
        if not self._flipper_mirror_is_present('input'):
            self.log.debug('No flipper mirror is present on the input port : PortType.INPUT_SIDE value is forbidden ')
            return
        code = FRONT_CODE if value == PortType.INPUT_FRONT else SIDE_CODE
        self._check(self._dll.ShamrockSetFlipperMirror(self._device_id, INPUT_CODE, code))

    def get_output_port(self):
        """ Returns the current output port

        @return (PortType): current port side

        Tested
        """
        output_port = ct.c_int()
        self._dll.ShamrockGetFlipperMirror(self._device_id, OUTPUT_CODE, ct.byref(output_port))
        return PortType.OUTPUT_FRONT if output_port.value == FRONT_CODE else PortType.OUTPUT_SIDE

    def set_output_port(self, value):
        """ Set the current output port

        @param (PortType) value: The port side to set

        Tested
        """
        if not value in PortType:
            self.log.error('Function parameter is not a PortType value ')
            return
        if value in [PortType.INPUT_FRONT, PortType.INPUT_SIDE]:
            self.log.error('Function parameter must be an OUTPUT value of PortType ')
            return
        if not self._flipper_mirror_is_present('output'):
            self.log.debug('No flipper mirror is present on the input port : PortType.OUTPUT_SIDE value is forbidden ')
            return
        code = FRONT_CODE if value == PortType.OUTPUT_FRONT else SIDE_CODE
        self._check(self._dll.ShamrockSetFlipperMirror(self._device_id, OUTPUT_CODE, code))

    def get_slit_width(self, port_type):
        """ Getter for the current slit width in meter on a given port

        @param (PortType) port_type: The port to inquire

        @return (float): input slit width (in meter)
        """
        if not port_type in PortType:
            self.log.error('Function parameter is not a PortType value ')
            return
        if not self._flipper_mirror_is_present('output') and port_type == PortType.OUTPUT_FRONT:
            self.log.debug('No flipper mirror is present on the input port : PortType.OUTPUT_SIDE value is forbidden ')
            return
        if not self._flipper_mirror_is_present('input') and port_type == PortType.INPUT_FRONT:
            self.log.debug('No flipper mirror is present on the input port : PortType.OUTPUT_SIDE value is forbidden ')
            return
        index = self._get_slit_index(port_type)
        slit_width = ct.c_float()
        self._check(self._dll.ShamrockGetAutoSlitWidth(self._device_id, index, ct.byref(slit_width)))
        return slit_width.value*1e-6

    def set_slit_width(self, port_type, value):
        """ Setter for the input slit width in meter

        @param (PortType) port_type: The port to set
        @param (float) value: input slit width (in meter)
        """
        if not port_type in PortType:
            self.log.error('Function parameter is not a PortType value ')
            return

        if self.SLIT_MIN_WIDTH <= value <= self.SLIT_MAX_WIDTH:

            index = self._get_slit_index(port_type)
            self._dll.ShamrockSetAutoSlitWidth.argtypes = [ct.c_int32, ct.c_int32, ct.c_float]
            self._check(self._dll.ShamrockSetAutoSlitWidth(self._device_id, index, value*1e6))
        else:
            self.log.error('Slit width ({} um) out of range.'.format(value*1e6))

    ##############################################################################
    #                            DLL tools functions
    ##############################################################################
    def _get_number_devices(self):
        """ Returns the number of devices

        @return (int): the number of devices detected by the DLL
        """
        number_of_devices = ct.c_int()
        self._check(self._dll.ShamrockGetNumberDevices(ct.byref(number_of_devices)))
        return number_of_devices.value

    def _get_connected_devices(self):
        """ Return a list of serial numbers of the connected devices

         @result (list(str)): A list of the serial numbers as string """
        result = []
        for i in range(self._get_number_devices()):
            result.append(self._get_device_serial_number(i))
        return result

    def _get_device_serial_number(self, index):
        """ Return the serial number of a hardware by the index number

        @param (int) index: The index the hardware

        @result (str): The serial number as a string
        """
        # todo: This function
        return 'Please fix me !'

    def _get_slit_index(self, port_type):
        """ Returns the slit DLL index of the given port

        @param (PortType) port_type: The port to inquire

        @return (int): slit index as defined by Andor shamrock conventions
        """
        conversion_dict = {PortType.INPUT_FRONT: 2,
                           PortType.INPUT_SIDE: 1,
                           PortType.OUTPUT_FRONT: 4,
                           PortType.OUTPUT_SIDE: 3}
        return conversion_dict[port_type]

    ##############################################################################
    #                 DLL wrappers used by the interface functions
    ##############################################################################
    def _get_optical_parameters(self):
        """ Returns the spectrometer optical parameters

        @return (dict): A dictionary with keys 'focal_length', 'angular_deviation' and 'focal_tilt'

        The unit of the given parameters are SI, so meter for the focal_length and radian for the other two
        """
        focal_length, angular_deviation, focal_tilt = ct.c_float(), ct.c_float(), ct.c_float()
        self._check(self._dll.ShamrockEepromGetOpticalParams(self._device_id, ct.byref(focal_length),
                                                            ct.byref(angular_deviation), ct.byref(focal_tilt)))
        return {'focal_length': focal_length.value,
                'angular_deviation': angular_deviation.value*np.pi/180,
                'focal_tilt': focal_tilt.value*np.pi/180}

    def _get_number_gratings(self):
        """ Returns the number of gratings in the spectrometer

        @return (int): The number of gratings
        """
        number_of_gratings = ct.c_int()
        self._check(self._dll.ShamrockGetNumberGratings(self._device_id, ct.byref(number_of_gratings)))
        return number_of_gratings.value

    def _get_grating_info(self, grating):
        """ Returns the information on a grating

        @param (int) grating: grating index
        @return (dict): A dictionary containing keys : 'ruling', 'blaze', 'home' and 'offset'

        All parameters are in SI

        'ruling' : The number of line per meter (l/m)
        'blaze' : The wavelength for which the grating is blazed
        'home' : #todo
        'offset' : #todo
        """
        line = ct.c_float()
        blaze = ct.create_string_buffer(32)
        home, offset = ct.c_int(), ct.c_int()

        self._check(self._dll.ShamrockGetGratingInfo(self._device_id, grating+1,
                                                    ct.byref(line), ct.byref(blaze), ct.byref(home), ct.byref(offset)))
        return {'ruling': line.value * 1e3,  # DLL use l/mm
                'blaze': blaze.value,  # todo: check unit directly in nm ?
                'home': home.value,
                'offset': offset.value}

    def _get_wavelength_limit(self, grating):
        """ Returns the wavelength limits of a given grating

        @params (int) grating: grating index

        @return tuple(float, float): The minimum and maximum central wavelength permitted by the grating
        """
        wavelength_min, wavelength_max = ct.c_float(), ct.c_float()

        self._check(self._dll.ShamrockGetWavelengthLimits(self._device_id, grating+1,
                                                         ct.byref(wavelength_min), ct.byref(wavelength_max)))
        return wavelength_min.value*1e-9, wavelength_max.value*1e-9  # DLL uses nanometer

    def _flipper_mirror_is_present(self, flipper):
        """ Returns true if flipper mirror is present on the given side

        @param (str) flipper: 'input' or 'output'

        @param (bool): Whether there is a flipper, hence a second input/output on the side
        """
        conversion_dict = {'input': INPUT_CODE, 'output': OUTPUT_CODE}
        code = conversion_dict[flipper]
        present = ct.c_int()
        self._check(self._dll.ShamrockFlipperMirrorIsPresent(self._device_id, code, ct.byref(present)))
        return present.value

    def _auto_slit_is_present(self, flipper, port):
        """ Return whether the given motorized slit is present or not

        @param (str) flipper: 'input' or 'output'
        @param (str) port: 'front' or 'side'

        @return (bool): True if a motorized slit is present
        """
        conversion_dict = {('input', 'front'): 2,  # todo: Check this, it does not match the rest of code. If there is a discrepency, we should mention it
                           ('input', 'side'): 1,
                           ('output', 'front'): 4,
                           ('output', 'side'): 3}
        slit_index = conversion_dict[(flipper, port)]
        present = ct.c_int()
        self._check(self._dll.ShamrockAutoSlitIsPresent(self._device_id, slit_index, ct.byref(present)))
        return present.value

    ##############################################################################
    #                    DLL wrapper for calibration functions
    #
    # This methods can be used to check the calibration of the logic
    ##############################################################################
    def _set_number_of_pixels(self, value):
        """ Internal function to sets the number of pixels of the detector

        @param (int) value: The number of pixels of the detector

        Shamrock DLL can give a estimate of the calibration if the required parameters are given.
        This feature is not used by Qudi but is useful to check everything is ok.
        """
        self._check(self._dll.ShamrockSetNumberPixels(self._device_id, value))

    def _get_number_of_pixels(self):
        """ Returns the number of pixel previously set with self._set_number_of_pixels """
        pixel_number = ct.c_int()
        self._check(self._dll.ShamrockGetNumberPixels(self._device_id, ct.byref(pixel_number)))
        return pixel_number.value

    def _set_pixel_width(self, value):
        """ Internal function to set the pixel width along the dispersion axis

        @param (float) value: The pixel width of the detector in meter

        Shamrock DLL can give a estimate of the calibration if the required parameters are given.
        This feature is not used by Qudi but is useful to check everything is ok.
        """
        if not (1e-6 <= value <= 100e-6):
            self.log.warning('The pixel width you ask ({} um) raises a warning.'.format(value*1e6))

        self._dll.ShamrockSetPixelWidth.argtypes = [ct.c_int32, ct.c_float]
        self._check(self._dll.ShamrockSetPixelWidth(self._device_id, value*1e6))

    def _get_pixel_width(self):
        """ Returns the pixel width previously set with self._set_pixel_width """
        pixel_width = ct.c_float()
        self._check(self._dll.ShamrockGetPixelWidth(self._device_id, ct.byref(pixel_width)))
        return pixel_width.value*1e-6

    def _set_detector_offset(self, value):
        """ Sets the detector offset in pixels

        @param (int) value: The offset to set

        Shamrock DLL can give a estimate of the calibration if the required parameters are given.
        This feature is not used by Qudi but is useful to check everything is ok.
        """
        self._check(self._dll.ShamrockSetDetectorOffset(self._device_id, int(value)))

    def _get_detector_offset(self):
        """ Returns the detector offset previously set with self._set_detector_offset """
        offset = ct.c_int()
        self._check(self._dll.ShamrockGetDetectorOffset(self._device_id, ct.byref(offset)))
        return offset.value

    def get_spectrometer_dispersion(self, number_pixels, pixel_width):
        """ Returns the wavelength calibration of each pixel

        Shamrock DLL can give a estimate of the calibration if the required parameters are given.
        This feature is not used by Qudi but is useful to check everything is ok.

        Call _set_number_of_pixels and _set_pixel_width before calling this function.
        """
        self._set_number_of_pixels(number_pixels)
        self._set_pixel_width(pixel_width)
        wl_array = np.ones((number_pixels,), dtype=np.float32)
        self._dll.ShamrockGetCalibration.argtypes = [ct.c_int32, ct.c_void_p, ct.c_int32]
        self._check(self._dll.ShamrockGetCalibration(self._device_id, wl_array.ctypes.data, number_pixels))
        return wl_array*1e-9  # DLL uses nanometer

    ##############################################################################
    #                    DLL wrapper unused by this module
    ##############################################################################
    def _shamrock_grating_is_present(self):
        """ Wrapper for ShamrockGratingIsPresent DLL function

        @returns (bool): True if grating is present

        #todo: what does this function mean ???
        """
        present = ct.c_int()
        self._check(self._dll.ShamrockGratingIsPresent(self._device_id, ct.byref(present)))
        return present.value

    def _get_grating_offset(self, grating):
        """ Returns the grating offset (in motor steps)

        @param (int) grating: grating index

        @return (int): grating offset (step)
        """
        grating_offset = ct.c_int()
        self._check(self._dll.ShamrockGetGratingOffset(self._device_id, grating+1, ct.byref(grating_offset)))
        return grating_offset.value

    def _set_grating_offset(self, grating, value):
        """ Sets the grating offset (in motor step)

        @param (int) grating : grating index
        @param (int) value: The offset to set
        """
        self._check(self._dll.ShamrockSetGratingOffset(self._device_id, grating+1, value))
