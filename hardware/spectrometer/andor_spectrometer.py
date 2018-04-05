# -*- coding: utf-8 -*-
"""
This hardware module implement the simple spectrometer interface to use the Andor SR303i and Newton Camera.
It use a dll to inteface with instruments via SUB (only available physical interface)
This module does not aim at replacing Solis completely.

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
from interface.spectrometer_interface import SpectrometerInterface
from time import strftime, localtime

from libraries.pyandor.Andor.camera import Camera
from libraries.pyandor.Andor.errorcodes import ERROR_CODE

import time
import numpy as np


class SimpleSpectrometerAndor(Base,SpectrometerInterface):
    """ Hardware module to record spectra from the Andor camera.
    """

    _modtype = 'Spectrometer'
    _modclass = 'hardware'

    _default_exposure = ConfigOption('default_exposure', 1.0)
    _default_temperature = ConfigOption('temperature', -70)
    _min_wavelength = ConfigOption('min_wavelength', missing='error')
    _max_wavelegnth = ConfigOption('max_wavelength', missing='error')

    def on_activate(self):
        """ Activate module.
        """

        self.cam = Camera()
        self.cam.SetVerbose(False)
        self.cam.SetReadMode(0)
        self.cam.SetAcquisitionMode(1)
        self.cam.SetImage(1, 1, 1, self.cam._width, 1, 1) # necessary ?
        self.cam.SetTriggerMode(0)
        self.cam.SetShutter(1, 0, 50, 50)
        self.setExposure(self._default_exposure)
        self.cam.CoolerON()
        self.cam.SetTemperature(self._default_temperature)


    def on_deactivate(self):
        """ Deactivate module.
        """
        self.cam.CoolerOFF() # necessary ?
        self.cam.ShutDown()

    def recordSpectrum(self):
        """ Record a dummy spectrum.

            @return ndarray: 1024-value ndarray containing wavelength and intensity of simulated spectrum
        """
        self.log.debug('recordSpectrum executed.')
        self.cam.StartAcquisition()
        data = []
        self.cam.GetAcquiredData(data)
        length = len(data)
        res = np.empty((2, length), dtype=np.double)
        res[0] = np.arange(self._min_wavelength , self._max_wavelegnth, (self._max_wavelegnth-self._min_wavelength) / length)
        res[1] = np.array(data)
        return res

    def getExposure(self):
        """ Get exposure time.

            @return float: exposure time
        """
        return self.exposure

    def setExposure(self, exposureTime):
        """ Set exposure time.

            @param float exposureTime: exposure time
        """
        self.exposure = exposureTime
        self.cam.SetExposureTime(self.exposure)