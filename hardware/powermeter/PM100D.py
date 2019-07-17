# -*- coding: utf-8 -*-
"""

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
import numpy as np
import visa

from core.module import Base
from core.configoption import ConfigOption

from interface.simple_data_interface import SimpleDataInterface
from interface.process_interface import ProcessInterface

try:
    from ThorlabsPM100 import ThorlabsPM100
except ImportError:
    raise ImportError('ThorlabsPM100 module not found. Please install it by typing command "pip install ThorlabsPM100"')


class PM100D(Base, SimpleDataInterface, ProcessInterface):
    """ Hardware module for Thorlabs PM100D powermeter.

    Example config :
    powermeter:
        module.Class: 'powermeter.PM100D.PM100D'
        address: 'USB0::0x1313::0x8078::P0013645::INSTR'

    This module needs the ThorlabsPM100 package from PyPi, this package is not included in the environment
    To add install it, type :
    pip install ThorlabsPM100
    in the Anaconda prompt after having activated qudi environment
    """

    _address = ConfigOption('address', missing='error')
    _timeout = ConfigOption('timeout', 1)
    _power_meter = None

    def on_activate(self):
        """ Startup the module """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._address, timeout=self._timeout)
        except:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

        self._power_meter = ThorlabsPM100(inst=self._inst)

    def on_deactivate(self):
        """ Stops the module """
        self._inst.close()

    def getData(self):
        """ SimpleDataInterface function to get the power from the powermeter """
        return np.array([self.get_power()])

    def getChannels(self):
        """ SimpleDataInterface function to know how many data channel the device has, here 1. """
        return 1

    def get_power(self):
        """ Return the power read from the ThorlabsPM100 package """
        return self._power_meter.read

    def get_process_value(self):
        """ Return a measured value """
        return self.get_power()

    def get_process_unit(self):
        """ Return the unit that hte value is measured in as a tuple of ('abreviation', 'full unit name') """
        return ('W', 'watt')

    def get_wavelength(self):
        """ Return the current wavelength in nanometers """
        return self._power_meter.sense.correction.wavelength

    def set_wavelength(self, value=None):
        """ Set the new wavelength in nanometers """
        mini, maxi = self.get_wavelength_range()
        if value is not None:
            if mini <= value <= maxi:
                self._power_meter.sense.correction.wavelength = value
            else:
                self.log.error('Wavelength {} is out of the range [{}, {}].'.format(
                    value, mini, maxi
                ))
        return self.get_wavelength()

    def get_wavelength_range(self):
        """ Return the wavelength range of the power meter in nanometers """
        return self._power_meter.sense.correction.minimum_beamdiameter,\
               self._power_meter.sense.correction.maximum_wavelength

