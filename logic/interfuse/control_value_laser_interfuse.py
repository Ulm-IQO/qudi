# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interfuse between a laser interface and control value control.

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

import time

from core.connector import Connector
from core.statusvariable import StatusVar
from logic.generic_logic import GenericLogic
from interface.simple_laser_interface import SimpleLaserInterface, ControlMode, ShutterState, LaserState


class Interfuse(GenericLogic, SimpleLaserInterface):
    """ This interfuse can be used to control the laser power by setting a set_setpoint to as pid controller,
    and reading the current power through get_process_value

    control_laser_interfuse:
        module.Class: 'interfuse.control_value_laser_interfuse.Interfuse'
        connect:
            control: 'processdummy'
            #process: 'processdummy' # optional
    """

    control = Connector(interface='ProcessControlInterface')
    process = Connector(interface='ProcessInterface', optional=True)

    _power = StatusVar('power', 0)
    _max_power = StatusVar('max_power', 1e-100)
    _laser_state = StatusVar('laser_state', False)

    def on_activate(self):
        """ Activate module.
        """
        self.set_power(self._power)

    def on_deactivate(self):
        """ Deactivate module.
        """
        pass

    def get_power_range(self):
        """ Return optical power range

            @return (float, float): power range
        """
        return 0, self._max_power

    def get_power(self):
        """ Return laser power

            @return float: Laser power in watts
        """
        if self.process.is_connected:
            return self.process().get_process_value()
        else:
            return 0

    def get_power_setpoint(self):
        """ Return optical power setpoint.

            @return float: power setpoint in watts
        """
        return self._power

    def _set_power(self, power):
        """ Function that set the control value no matter what """
        if self._max_power != 0:
            self.control().set_control_value(power/self._max_power)
        else:
            self.control().set_control_value(0)

    def set_power(self, power):
        """ Set power setpoint.

            @param float power: power setpoint

            @return float: actual new power setpoint
        """
        mini, maxi = self.get_power_range()
        if mini <= power <= maxi:
            self._power = power
            if self._laser_state:
                self._set_power(power)
            else:
                self._set_power(0)
        return self._power

    def get_current_unit(self):
        """ Get unit for laser current.

            @return str: unit
        """
        return '%'

    def get_current_range(self):
        """ Get laser current range.

            @return (float, float): laser current range
        """
        return (0, 100)

    def get_current(self):
        """ Get current laser current

            @return float: laser current in current curent units
        """
        return 0

    def get_current_setpoint(self):
        """ Get laser curent setpoint

            @return float: laser current setpoint
        """
        return 0

    def set_current(self, current):
        """ Set laser current setpoint

            @prarm float current: desired laser current setpoint

            @return float: actual laser current setpoint
        """
        return 0

    def allowed_control_modes(self):
        """ Get supported control modes

            @return list(): list of supported ControlMode
        """
        return [ControlMode.POWER]

    def get_control_mode(self):
        """ Get the currently active control mode

            @return ControlMode: active control mode
        """
        return ControlMode.POWER

    def set_control_mode(self, control_mode):
        """ Set the active control mode

            @param ControlMode control_mode: desired control mode

            @return ControlMode: actual active ControlMode
        """
        return ControlMode.POWER

    def on(self):
        """ Turn on laser.

            @return LaserState: actual laser state
        """
        return self.set_laser_state(LaserState.ON)

    def off(self):
        """ Turn off laser.

            @return LaserState: actual laser state
        """
        return self.set_laser_state(LaserState.OFF)

    def get_laser_state(self):
        """ Get laser state

            @return LaserState: actual laser state
        """
        return LaserState.ON if self._laser_state else LaserState.OFF

    def set_laser_state(self, state):
        """ Set laser state.

            @param LaserState state: desired laser state

            @return LaserState: actual laser state
        """
        self._laser_state = True if state == LaserState.ON else False
        self.set_power(self._power)
        return self.get_laser_state()

    def get_shutter_state(self):
        """ Get laser shutter state

            @return ShutterState: actual laser shutter state
        """
        return ShutterState.NOSHUTTER

    def set_shutter_state(self, state):
        """ Set laser shutter state.

            @param ShutterState state: desired laser shutter state

            @return ShutterState: actual laser shutter state
        """
        return ShutterState.NOSHUTTER

    def get_temperatures(self):
        """ Get all available temperatures.

            @return dict: dict of temperature namce and value in degrees Celsius
        """
        return {}

    def set_temperatures(self, temps):
        """ Set temperatures for lasers with tunable temperatures.

            @return {}: empty dict, dummy not a tunable laser
        """
        return {}

    def get_temperature_setpoints(self):
        """ Get temperature setpoints.

            @return dict: temperature setpoints for temperature tunable lasers
        """
        return {}

    def get_extra_info(self):
        """ Multiple lines of dignostic information

            @return str: much laser, very useful
        """
        return "Virtual laser, real nice !"

    def set_max_power(self, maxi):
        """ Function to redefine the max power if the value has changed """
        self._max_power = maxi
        if self._power > maxi:
            self.set_power(maxi)

