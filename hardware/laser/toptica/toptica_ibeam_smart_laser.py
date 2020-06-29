# -*- coding: utf-8 -*-
"""
This module serves as qudi laser module for the Toptica iBeam Smart series.

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

from core.module import Base
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import LaserState
from interface.simple_laser_interface import ShutterState
from interface.simple_laser_interface import ControlMode
from .ibeam_smart import IBeamSmart


class IBeamSmartLaser(Base, SimpleLaserInterface):
    """ iBeam Smart laser hardware module.

    Example config for copy-paste:

    ibeam_smart:
        module.Class: 'laser.toptica_ibeam_smart_laser.IBeamSmartLaser'

    """

    _com_port = ConfigOption('com_port', missing='error')
    _com_timeout = ConfigOption('com_timeout', default=2)
    _max_power = ConfigOption('max_power', default=0.1, missing='warn')

    def __init__(self, **kwargs):
        """
        """
        super().__init__(**kwargs)
        self._laser = None

    def on_activate(self):
        """ Activate module.
        """
        self._laser = IBeamSmart(com_port=self._com_port,
                                 timeout=self._com_timeout,
                                 max_power=self._max_power)
        self.

    def on_deactivate(self):
        """ Deactivate module.
        """
        self._laser.terminate()
        self._laser = None

    def get_power_range(self):
        """ Return optical power range

            @return (float, float): power range
        """
        return 0, self._max_power

    def get_power(self):
        """ Return laser power

            @return float: Laser power in watts
        """
        return self._laser.laser_power

    def get_power_setpoint(self):
        """ Return optical power setpoint.

            @return float: power setpoint in watts
        """
        return self._laser.get_power(0)

    def set_power(self, power):
        """ Set power setpoint.

            @param float power: power setpoint

            @return float: actual new power setpoint
        """
        return self._laser.set_power(0, power)

    def get_current_unit(self):
        """ Get unit for laser current.

            @return str: unit
        """
        return '%'

    def get_current_range(self):
        """ Get laser current range.

            @return (float, float): laser current range
        """
        return 0, 100

    def get_current(self):
        """ Get current laser current

            @return float: laser current in current curent units
        """
        return self._laser.diode_current

    def get_current_setpoint(self):
        """ Get laser curent setpoint

            @return float: laser current setpoint
        """
        return self._laser.diode_current

    def set_current(self, current):
        """ Set laser current setpoint

            @prarm float current: desired laser current setpoint

            @return float: actual laser current setpoint
        """
        return self._laser.diode_current

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
        state = self._laser.toggle_laser_driver(True)
        return LaserState.ON if state else LaserState.OFF

    def off(self):
        """ Turn off laser.

            @return LaserState: actual laser state
        """
        state = self._laser.toggle_laser_driver(False)
        return LaserState.ON if state else LaserState.OFF

    def get_laser_state(self):
        """ Get laser state

            @return LaserState: actual laser state
        """
        return self._laser.laser_driver_state

    def set_laser_state(self, state):
        """ Set laser state.

            @param LaserState state: desired laser state

            @return LaserState: actual laser state
        """
        if state == LaserState.OFF:
            return self.off()
        elif state == LaserState.ON:
            return self.on()

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

            @return dict: dict of temperature name and value in degrees Celsius
        """
        return {'base': self._laser.base_temperature, 'diode': self._laser.base_temperature}

    def set_temperatures(self, temps):
        """ Set temperatures for lasers with tunable temperatures.

            @return {}: empty dict, dummy not a tunable laser
        """
        return {}

    def get_temperature_setpoints(self):
        """ Get temperature setpoints.

            @return dict: temperature setpoints for temperature tunable lasers
        """
        return {'base': 32.2, 'diode': 42.0}

    def get_extra_info(self):
        """ Multiple lines of dignostic information

            @return str: much laser, very useful
        """
        return ""

