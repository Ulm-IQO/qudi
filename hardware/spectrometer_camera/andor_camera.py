# -*- coding: utf-8 -*-

"""
This hardware module implement the camera spectrometer interface to use an Andor Camera.
It use a dll to inteface with instruments via USB (only available physical interface)
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

from core.module import Base, ConfigOption
from interface.spectrometer_camera_interface import SpectrometerCameraInterface, ReadMode, SpectrometerCameraConstraints
from time import strftime, localtime

from libraries.pyandor.Andor.camera import Camera
from libraries.pyandor.Andor.errorcodes import ERROR_CODE

import time
import numpy as np


class ScectrometerCameraAndor(Base, SpectrometerCameraInterface):
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
    _width = 0
    _height = 0
    cam = None
    _acquiring = False
    _last_acquisitioon_mode = None # useful if config changes during acq

    def on_activate(self):

        self.cam = Camera()
        self.cam.SetVerbose(False)
        self.set_read_mode(self._read_mode)
        self.cam.SetAcquisitionMode(1) # single
        self.cam.SetTriggerMode(0) # internal
        self.cam.SetShutter(1, 0, 50, 50) # is this even useful ?
        self.cam.SetCoolerMode(0) # Returns to ambient temperature on ShutDown
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

    def get_constraints(self):
        cons = SpectrometerCameraConstraints()
        cons.cooling = True
        cons.width = self._width
        cons.height = self._height
        cons.max_cooling = -100.0
        cons.read_mode = [ReadMode.FVB, ReadMode.IMAGE]
        return cons

    def set_read_mode(self, mode):
        if mode in self.get_constraints().read_mode:
            self._read_mode = mode
            self.cam.SetReadMode(mode.value)
        else:
            return -1

    def get_read_mode(self):
        return self._read_mode

    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        error_code = self.cam.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        if error_code == 'DRV_SUCCESS':
            return 0
        else:
            return -1

    def start_acqusition(self):
        if self.get_ready_state():
            self._acquiring = True
            self._last_acquisitioon_mode = self.get_read_mode()
            self.cam.StartAcquisition()
            return 0
        else:
            return -1


    def get_aquired_data(self):
        data = []
        self.cam.GetAcquiredData(data)
        data = np.array(data, dtype=np.double)
        result = []
        if self._last_acquisitioon_mode == ReadMode.FVB:
            result = [data]
        elif self._last_acquisitioon_mode == ReadMode.IMAGE:
            result = np.reshape(data, (self._wdith, self._height))

        self._acquiring = False
        return result

    def set_exposure(self, time):
        self._exposure = time
        error_code = self.cam.SetExposureTime(time)
        if error_code == 'DRV_SUCCESS':
            return 0
        else:
            return -1
    def get_exposure(self):
        return self._exposure

    def set_cooler_on_state(self, on_state):
        self._cooler_on = on_state
        if on_state:
            error_code = self.cam.CoolerON()
        else:
            error_code = self.cam.CoolerOFF()

        if error_code == 'DRV_SUCCESS':
            return 0
        else:
            return -1

    def get_cooler_on_state(self):
        return self._cooler_on

    def get_measured_temperature(self):
        return float(self.cam.GetTemperature())

    def set_setpoint_temperature(self, temperature):
        if temperature < self.get_constraints().max_cooling:
            return -1
        self._temperature = temperature
        error_code = self.cam.SetTemperature(int(temperature))
        if error_code == 'DRV_SUCCESS':
            return 0
        else:
            return -1

    def get_setpoint_temperature(self):
        return self._temperature

    def get_ready_state(self):
        return not self._acquiring

    ### To be compatible with simple spectro interface
    def recordSpectrum(self):
        self.set_read_mode(ReadMode.FVB)
        self.start_acqusition()
        data = self.get_aquired_data()[0]
        length = len(data)
        res = np.empty((2, length), dtype=np.double)
        res[0] = np.arange(length)
        res[1] = data
        return res

    def setExposure(self, exposureTime):
        set_exposure(exposureTime)

    def getExposure(self):
        return get_exposure()
