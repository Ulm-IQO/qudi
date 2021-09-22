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

from qudi.core.module import Base
from qudi.core.configoption import ConfigOption

#from qudi.interface.process_control_interface import ProcessControlConstraints
#from qudi.interface.process_control_interface import ProcessSetpointInterface
from qudi.interface.process_control_interface import ProcessValueInterface

#from interface.process_control_interface import ProcessInterface

try:
    from ThorlabsPM100 import ThorlabsPM100
except ImportError:
    raise ImportError('ThorlabsPM100 module not found. Please install it by typing command "pip install ThorlabsPM100"')


#class PM100D(Base, SimpleDataInterface, ProcessInterface):
class PM100D(ProcessValueInterface):
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

    def is_active(self):
        """ Current activity state.
        State is bool type and refers to active (True) and inactive (False).

        @return bool: Activity state (active: True, inactive: False)
        """
        pass

    def process_values(self):
        """ Read-Only property returning a snapshot of current process values for all channels.

        @return dict: Snapshot of the current process values (values) for all channels (keys)
        """
        return self.get_process_value()

    def set_activity_state(self, active):
        """ Set activity state. State is bool type and refers to active (True) and inactive (False).

        @param bool active: Activity state to set (active: True, inactive: False)
        """
        pass

    def constraints(self):
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.

        @return ProcessControlConstraints: Hardware constraints
        """
        return (self.get_process_unit(), self.get_wavelength_range(), self.get_wavelength())

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