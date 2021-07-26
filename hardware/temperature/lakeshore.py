# -*- coding: utf-8 -*-
"""
Hardware module for the lakeshore temperature controller model No. 335

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

from interface.pid_controller_interface import PIDControllerInterface

import visa
import numpy as np
from core.module import Base
from core.configoption import ConfigOption


class Lakeshore(Base, PIDControllerInterface):
    """ This interface is used to control a PID device.

    From Wikipedia : https://en.wikipedia.org/wiki/PID_controller
    A proportional–integral–derivative controller (PID controller or three-term controller) is a control loop mechanism
    employing feedback that is widely used in industrial control systems and a variety of other applications requiring
    continuously modulated control. A PID controller continuously calculates an error value e(t) as the difference
    between a desired setpoint (SP) and a measured process variable (PV) and applies a correction based on proportional,
    integral, and derivative terms (denoted P, I, and D respectively), hence the name.

    If the device is enabled, the control value is computed by the the PID system of the hardware. If the device is
    disabled, the control value is set by the manual value.

    """

    _visa_address = ConfigOption('visa_address')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.open_resource()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        try:
            self._inst.close()
        except visa.VisaIOError:
            self.log.warning('Crycon connexion has not been closed properly.')

    def open_resource(self):
        """ Open a new visa connection """
        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._visa_address,write_termination='\r\n', read_termination='\r\n')
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')
            raise visa.VisaIOError

    def get_temperature(self):
        try:
            temperature = float(self._query('KRDG?'))
        except:
            temperature = np.NaN
        return temperature

    def _query(self, text):
        """ Helper function to send query and deal with errors """
        try:
            response = self._inst.query(text)
        except visa.VisaIOError:
            if self.module_state() != 'idle':
                return None
            self.log.warning('Lakeshore connetion lost')
#            self.open_resource()
#            self._inst.query(text)
        return response

    def get_kp(self):
        """ Get the coefficient associated with the proportional term

         @return (float): The current kp coefficient associated with the proportional term
         """
        try:
            value = float(self._query('PID?')[1:7])
        except:
            value = np.NaN
        return value

    def set_kp(self, kp):
        """ Set the coefficient associated with the proportional term

         @param (float) kp: The new kp coefficient associated with the proportional term
         """
        pass

    def get_ki(self):
        """ Get the coefficient associated with the integral term

         @return (float): The current ki coefficient associated with the integral term
         """
        try:
            value = float(self._query('PID?')[9:15])
        except:
            value = np.NaN
        return value

    def set_ki(self, ki):
        """ Set the coefficient associated with the integral term

         @param (float) ki: The new ki coefficient associated with the integral term
         """
        pass

    def get_kd(self):
        """ Get the coefficient associated with the derivative term

         @return (float): The current kd coefficient associated with the derivative term
         """
        try:
            value = float(self._query('PID?')[17:23])
        except:
            value = np.NaN
        return value

    def set_kd(self, kd):
        """ Set the coefficient associated with the derivative term

         @param (float) kd: The new kd coefficient associated with the derivative term
         """
        pass

    def get_setpoint(self):
        """ Get the setpoint value of the hardware device

         @return (float): The current setpoint value
         """
        pass

    def set_setpoint(self, setpoint):
        """ Set the setpoint value of the hardware device

        @param (float) setpoint: The new setpoint value
        """
        pass

    def get_manual_value(self):
        """ Get the manual value, used if the device is disabled

        @return (float): The current manual value
        """
        return 1

    def set_manual_value(self, manualvalue):
        """ Set the manual value, used if the device is disabled

        @param (float) manualvalue: The new manual value
        """
        pass

    def get_enabled(self):
        """ Get if the PID is enabled (True) or if it is disabled (False) and the manual value is used

        @return (bool): True if enabled, False otherwise
        """
        return True

    def set_enabled(self, enabled):
        """ Set if the PID is enabled (True) or if it is disabled (False) and the manual value is used

        @param (bool) enabled: True to enabled, False otherwise
        """
        pass

    def get_control_limits(self):
        """ Get the current limits of the control value as a tuple

        @return (tuple(float, float)): The current control limits
        """
        pass

    def set_control_limits(self, limits):
        """ Set the current limits of the control value as a tuple

        @param (tuple(float, float)) limits: The new control limits

        The hardware should check if these limits are within the maximum limits set by a config option.
        """
        pass

    def get_process_value(self):
        """ Get measured value of the temperature """
        return self.get_temperature()

    def get_process_unit(self):
        """ Return the unit of measured temperature """
        return 'K', 'Kelvin'

    def get_control_value(self):
        """ Get the current control value read

        @return (float): The current control value
        """
        pass

    def get_extra(self):
        """ Get the P, I and D terms computed bu the hardware if available

         @return dict(): A dict with keys 'P', 'I', 'D' if available, an empty dict otherwise
         """
        return dict()