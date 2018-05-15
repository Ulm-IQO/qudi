# -*- coding: utf-8 -*-

"""
This hardware module implement the camera spectrometer interface to use an Andor Camera.
It use a dll to interface with instruments via USB (only available physical interface)
This module does aim at replacing Solis.

---

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
"""

from enum import Enum

from core.module import Base, ConfigOption

from interface.camera_interface import CameraInterface
from interface.setpoint_controller_interface import SetpointControllerInterface
from interface.spectrometer_interface import SpectrometerInterface

from .api import Camera

import numpy as np


class ReadMode(Enum):
    FVB = 0
    MULTI_TRACK = 1
    RANDOM_TRACK = 2
    SINGLE_TRACK = 3
    IMAGE = 4


class ScectrometerCameraAndor(Base, CameraInterface, SetpointControllerInterface, SpectrometerInterface):
    """
    Main class for the camera/spectro
    """

    _modtype = 'Spectrometer camera'
    _modclass = 'hardware'

    _default_exposure = ConfigOption('default_exposure', 1.0)
    _default_read_mode = ConfigOption('default_read_mode', ReadMode.FVB)
    _default_temperature = ConfigOption('default_temperature', -70)
    _default_cooler_on = ConfigOption('default_cooler_on', True)

    _exposure = _default_exposure
    _temperature = _default_temperature
    _cooler_on = _default_cooler_on
    _read_mode = _default_read_mode
    _gain = 0
    _width = 0
    _height = 0
    cam = None
    _last_acquisition_mode = None  # useful if config changes during acq
    _supported_read_mode = [ReadMode.FVB.value, ReadMode.IMAGE.value]  # TODO: read this from camera
    _max_cooling = -100
    _live = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
         """

        self.cam = Camera()
        self.cam.SetVerbose(False)
        self.set_read_mode(self._read_mode)
        self.cam.SetAcquisitionMode(1)  # single
        self.cam.SetTriggerMode(0)  # internal
        self.cam.SetShutter(1, 0, 50, 50)  # is this even useful ?
        self.cam.SetCoolerMode(0)  # Returns to ambient temperature on ShutDown
        self.set_cooler_on_state(self._cooler_on)
        self.set_exposure(self._exposure)
        self.set_setpoint_temperature(self._temperature)
        self._width = self.cam.getResolutionWdith()
        self._height = self.cam.getResolutionHeight()


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stop_acquisition()
        if self.cam:  # the camera might not be initialised in case of error
            self.cam.CoolerOFF()
            self.cam.ShutDown()
        self.cam = None

    def get_name(self):
        """
        Return a name for the camera
        """
        return "Andor " + self.cam.GetCameraSerialNumber()

    def get_size(self):
        """ Return the maximum size of the camera """
        return self._width, self._height

    def set_read_mode(self, mode):
        """ Set the read mode of the camera for image or full vertical binning"""
        if mode in self._supported_read_mode:
            self._read_mode = mode
            self.cam.SetReadMode(mode)
            if self._read_mode==4:  #image
                self.set_image(1,1,1, self._width, 1, self._height)
        else:
            self.log.info('Read mode is not supported')
            return -1

    def get_read_mode(self):
        """Get the read mode of the camrea """
        return self._read_mode

    def get_bit_depth(self):
        """ Return the bit depth of the camera """
        return 8  # TODO: clean this

    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        """ dll mapped function to acquire jsut part of the image """
        error_code = self.cam.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        return self._check_success(error_code)

    def support_live_acquisition(self):
        """ Return True if the camera support live acquisition """
        return False

    def start_single_acquisition(self):
        """ Start a single acquisition and return when it's finish """
        if self.get_ready_state():
            self._last_acquisition_mode = self.get_read_mode()
            self.cam.StartAcquisition()
            self.cam.WaitForIdle()
            return 0
        else:
            return -1

    def stop_acquisition(self):
        """ If in acquisition, abort it """
        if self.cam and self.cam.GetStatus() == 'DRV_ACQUIRING':
            self.cam.AbortAcquisition()

    def start_live_acquisition(self):
        """ Interface function not supported here """
        return False

    def _check_success (self, error_code):
        """ Internal function  to check if dll call is a success"""
        if error_code == 'DRV_SUCCESS':
            return 0
        else:
            return -1

    def get_acquired_data(self):
        """ Get the last acquired data from the dll """
        data = []
        if not self.cam:
            return [[0]]
        self.cam.GetAcquiredData(data)
        if data == []:
            self.log.warning('Could get acquired data')
        data = np.array(data, dtype=np.double)
        result = []
        if self._last_acquisition_mode == ReadMode.FVB.value:
            result = [data]
        elif self._last_acquisition_mode == ReadMode.IMAGE.value:
            result = np.reshape(data, (self._height, self._width))

        return result

    def set_exposure(self, time):
        """ Set the exposure in seconds """
        self._exposure = time
        error_code = self.cam.SetExposureTime(time)
        return self._check_success(error_code)

    def get_exposure(self):
        """ Get the exposure in seconds """
        return self._exposure
    
    def set_gain(self, gain):
        """ Set the gain"""
        pass

    def get_gain(self):
        """ Get the gain """
        return self._gain

    def set_cooler_on_state(self, on_state):
        """ The the cooler of the camera on or off """
        if not self.cam:
            return False
        self._cooler_on = on_state
        if on_state:
            error_code = self.cam.CoolerON()
        else:
            error_code = self.cam.CoolerOFF()
        return self._check_success(error_code)

    def get_cooler_on_state(self):
        """ Return if the cooler of the camera is on """
        return self._cooler_on

    def get_measured_temperature(self):
        """ Return measured temperature of the camera """
        if self.cam:
            return float(self.cam.GetTemperature())

    def set_setpoint_temperature(self, temperature):
        """ setpoint_interface : Set the setpoint temperature of the camera """
        if temperature < self._max_cooling:
            return -1
        self._temperature = temperature
        error_code = self.cam.SetTemperature(int(temperature))
        return self._check_success(error_code)

    def get_setpoint_temperature(self):
        """ setpoint_interface : Get the setpoint temperature of the camera """
        return self._temperature

    def get_ready_state(self):
        """ Return True if the camera is ready for an acquisition """
        return self.cam and self.cam.GetStatus() == 'DRV_IDLE'

    # Setpoint controller interface to control cooling

    def get_enabled(self):
        """ setpoint_controller_interface : get if the cooling is on """
        return self.get_cooler_on_state()

    def set_enabled(self, enabled):
        """ setpoint_controller_interface : set if the cooling is on """
        self.set_cooler_on_state(enabled)

    def get_process_value(self):
        """ process_interface : Get measured value of the temperature """
        return self.get_measured_temperature()

    def get_process_unit(self):
        """ process_interface : Return the unit of measured temperature """
        return '°C', 'Degrees Celsius'

    def set_setpoint(self, value):
        """ 'setpoint_interface' : set the setpoint temperature for the camera """
        self.set_setpoint_temperature(value)

    def get_setpoint(self):
        """ 'setpoint_interface' : get the setpoint temperature for the camera """
        return self.get_setpoint_temperature()

    def get_setpoint_unit(self):
        """ setpoint_interface : Return the unit of setpoint temperature """
        return self.get_process_unit()

    def get_setpoint_limits(self):
        """ setpoint_interface : Return the limits for the setpoint temperature """
        return -75., 0.

    # To be compatible with simple spectrometer interface

    def recordSpectrum(self):
        """ Record a spectrum and return it """
        self.set_read_mode(ReadMode.FVB.value)
        self.start_acqusition()
        data = self.get_aquired_data()[0]
        length = len(data)
        res = np.empty((2, length), dtype=np.double)
        res[0] = np.arange(length)
        res[1] = data
        return res

    def setExposure(self, exposureTime):
        """ SpectrometerInterface : set exposure in seconds """
        self.set_exposure(exposureTime)

    def getExposure(self):
        """ SpectrometerInterface : get exposure in seconds """
        return self.get_exposure()
