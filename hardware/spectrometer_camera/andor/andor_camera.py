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
    _acquiring = False
    _last_acquisition_mode = None  # useful if config changes during acq
    _supported_read_mode = [ReadMode.FVB.value, ReadMode.IMAGE.value]  # TODO: read this from camera
    _max_cooling = -100

    def on_activate(self):

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
        self._acquiring = False

    def on_deactivate(self):
        self.cam.CoolerOFF()
        self.cam.ShutDown()

    def get_name(self):
        return "Andor " + self.cam.GetCameraSerialNumber()

    def get_size(self):
        return self._width, self._height

    def set_read_mode(self, mode):
        if mode in self._supported_read_mode:
            self._read_mode = mode
            self.cam.SetReadMode(mode)
            if self._read_mode==4:  #image
                self.set_image(1,1,1, self._width, 1, self._height)
        else:
            self.log.info('Read mode is not supported')
            return -1

    def get_read_mode(self):
        return self._read_mode

    def get_bit_depth(self):
        return 8  # TODO: clean this

    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        error_code = self.cam.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        return self._check_success(error_code)

    def start_acquisition(self):
        if self.get_ready_state():
            self._acquiring = True
            self._last_acquisition_mode = self.get_read_mode()
            self.cam.StartAcquisition()
            return 0
        else:
            return -1

    def stop_acquisition(self):
        pass

    def _check_success (self, error_code):
        if error_code == 'DRV_SUCCESS':
            return 0
        else:
            return -1

    def get_acquired_data(self):
        data = []
        self.cam.GetAcquiredData(data)
        data = np.array(data, dtype=np.double)
        result = []
        if self._last_acquisition_mode == ReadMode.FVB.value:
            result = [data]
        elif self._last_acquisition_mode == ReadMode.IMAGE.value:
            result = np.reshape(data, (self._height, self._width))

        self._acquiring = False
        return result

    def set_exposure(self, time):
        self._exposure = time
        error_code = self.cam.SetExposureTime(time)
        return self._check_success(error_code)

    def get_exposure(self):
        return self._exposure
    
    def set_gain(self, gain):
        pass

    def get_gain(self):
        return self._gain

    def set_cooler_on_state(self, on_state):
        self._cooler_on = on_state
        if on_state:
            error_code = self.cam.CoolerON()
        else:
            error_code = self.cam.CoolerOFF()
        return self._check_success(error_code)

    def get_cooler_on_state(self):
        return self._cooler_on

    def get_measured_temperature(self):
        return float(self.cam.GetTemperature())

    def set_setpoint_temperature(self, temperature):
        if temperature < self._max_cooling:
            return -1
        self._temperature = temperature
        error_code = self.cam.SetTemperature(int(temperature))
        return self._check_success(error_code)

    def get_setpoint_temperature(self):
        return self._temperature

    def get_ready_state(self):
        return not self._acquiring

    # Setpoint controller interface to control cooling

    def get_enabled(self):
        return self.get_cooler_on_state()

    def set_enabled(self, enabled):
        self.set_cooler_on_state(enabled)

    def get_process_value(self):
        return self.get_measured_temperature()

    def get_process_unit(self):
        return '°C', 'Degrees Celsius'

    def set_setpoint(self, value):
        self.set_setpoint_temperature(value)

    def get_setpoint(self):
        return self.get_setpoint_temperature()

    def get_setpoint_unit(self):
        return self.get_process_unit()

    def get_setpoint_limits(self):
        return 0.,75.

    # To be compatible with simple spectrometer interface

    def recordSpectrum(self):
        self.set_read_mode(ReadMode.FVB.value)
        self.start_acqusition()
        data = self.get_aquired_data()[0]
        length = len(data)
        res = np.empty((2, length), dtype=np.double)
        res[0] = np.arange(length)
        res[1] = data
        return res

    def setExposure(self, exposureTime):
        self.set_exposure(exposureTime)

    def getExposure(self):
        return self.get_exposure()
