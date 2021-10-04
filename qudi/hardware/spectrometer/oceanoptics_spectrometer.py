# -*- coding: utf-8 -*-
"""
This module controls spectrometers from Ocean Optics Inc.
All spectrometers supported by python-seabreeze should work.

Do "conda install -c poehlmann python-seabreeze"
before using this module.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

"""

from core.module import Base
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from interface.spectrometer_interface import SpectrometerInterface
import numpy as np
import seabreeze.spectrometers as sb


class OceanOptics(Base, SpectrometerInterface):
    """ Hardware module for reading spectra from the Ocean Optics spectrometer software.

    Example config for copy-paste:

    myspectrometer:
        module.Class: 'spectrometer.oceanoptics_spectrometer.OceanOptics'
        spectrometer_serial: 'QEP01583' #insert here the right serial number.

    """
    _serial = ConfigOption('spectrometer_serial', missing='warn')
    _integration_time = StatusVar('integration_time', default=10000)

    def on_activate(self):
        """ Activate module.
        """

        self.spec = sb.Spectrometer.from_serial_number(self._serial)
        self.log.info(''.format(self.spec.model, self.spec.serial_number))
        self.spec.integration_time_micros(self._integration_time)
        self.log.info('Exposure set to {} microseconds'.format(self._integration_time))

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.spec.close()

    def recordSpectrum(self):
        """ Record spectrum from Ocean Optics spectrometer.

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
        return self._integration_time

    def setExposure(self, exposureTime):
        """ Set exposure.

            @param float exposureTime: exposure time in microseconds

        """
        self._integration_time = exposureTime
        self.spec.integration_time_micros(self._integration_time)
