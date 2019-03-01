# -*- coding: utf-8 -*-
"""
This module controls spectrometers from Ocean Optics Inc.
All spectrometers supported by python-seabreeze should work.

Do "conda install -c poehlmann python-seabreeze to install python-seabreeze"
before using this module.

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

import time
import numpy as np

import seabreeze.spectrometers as sbs


class OceanOpticsSpectrometer(Base, SpectrometerInterface):
    """ Dummy spectrometer module.

    Shows a silicon vacancy spectrum at liquid helium temperatures.

    Example config for copy-paste:

    ocean_spectrometer:
        module.Class: 'spectrometer.ocean_optics_spectrometer.OceanOpticsSpectrometer'
        spectrometer_serial: 'QEP01111'  # Optional, necessary when running multiple spectrometers

    """

    _serial = ConfigOption('spectrometer_serial', missing='warn')

    def on_activate(self):
        """ Activate module.
        """
        self.spec = sbs.Spectrometer.from_serial_number(self._serial)
        self.log.info(''.format(self.spec.model, self.spec.serial_number))

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.spec.close()

    def record_spectrum(self):
        """ Record a dummy spectrum.

            @return ndarray: numpy array containing wavelength and intensity of simulated spectrum
        """
        return np.vstack((self.spec.wavelengths() * 1e-9, self.spec.intensities()))

    def saveSpectrum(self, path, postfix = ''):
        """ Dummy save function.

            @param str path: path of saved spectrum
            @param str postfix: postfix of saved spectrum file
        """
        timestr = strftime("%Y%m%d-%H%M-%S_", localtime())
        print( 'Dummy would save to: ' + str(path) + timestr + str(postfix) + ".spe" )

    def get_exposure(self):
        """ Get exposure time.

            @return float: exposure time
        """
        return self.spec.ex

    def set_exposure(self, exposureTime):
        """ Set exposure time.

            @param float exposureTime: exposure time
        """
        self.exposure = exposureTime
        self.spec.integration_time_micros(20000)
