# -*- coding: utf-8 -*-
"""
This module controls spectrometers from Ocean Optics Inc.
All spectrometers supported by python-seabreeze should work.

Do "conda install -c poehlmann python-seabreeze to install python-seabreeze"
before using this module.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Derived from the pyPL project (https://github.com/kaseyrussell/pyPL)
Copyright 2010 Kasey Russell ( email: krussell _at_ post.harvard.edu )

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

"""

from core.module import Base
from interface.spectrometer_interface import SpectrometerInterface
import numpy as np
import time
import seabreeze.spectrometers as sb

import datetime



class OceanOptics(Base, SpectrometerInterface):
    """ Hardware module for reading spectra from the WinSpec32 spectrometer software.

    Example config for copy-paste:

    spectrometer_dummy:
        module.Class: 'spectrometer.winspec_spectrometer.WinSpec32'

    """

    def on_activate(self):
        """ Activate module.
        """
        self.integration_time_micros = 100e3
        self.spec = sb.Spectrometer.from_serial_number()
        self.spec.integration_time_micros(self.integration_time_micros)

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.spec.close()

    def recordSpectrum(self):
        """ Record spectrum from WinSpec32 software.

            @return []: spectrum data
        """
        wavelengths = self.spec.wavelengths()
        specdata = np.empty((2, len(wavelengths)), dtype=np.double)
        specdata[0] = wavelengths/1e9
        specdata[1] = self.spec.intensities()
        return specdata

    def getExposure(self):
        """ Get exposure.

            @return float: exposure

            Not implemented.
        """
        return self.integration_time_micros

    def setExposure(self, exposureTime):
        """ Set exposure.

            @param float exposureTime: exposure time in microseconds

        """
        self.integration_time_micros = exposureTime
        self.spec.integration_time_micros(self.integration_time_micros)
