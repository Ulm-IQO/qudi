# -*- coding: utf-8 -*-
"""
This module acts like a laser.

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

from core.base import Base
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import LaserState
from interface.simple_laser_interface import ShutterState
from interface.simple_laser_interface import ControlMode


class SimpleLaserDummy(Base, SimpleLaserInterface):
    """
    Lazors
    """
    _modclass = 'laserdummy'
    _modtype = 'hardware'

    # connectors
    _out = {'laser': 'SimpleLaser'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lstate = LaserState.OFF
        self.shutter = ShutterState.CLOSED
        self.mode = ControlMode.POWER
        self.current_setpoint = 0
        self.power_setpoint = 0

    def on_activate(self, e):
        """

        @param e:
        @return:
        """
        pass

    def on_deactivate(self, e):
        """
        @param e:
        @return:
        """
        pass

    def get_power(self):
        """ Return laser power
        @return float: Laser power in watts
        """
        return self.power_setpoint

    def get_power_setpoint(self):
        return self.power_setpoint

    def set_power(self, power):
        self.power_setpoint = power
        return self.power_setpoint

    def get_current(self):
        """ Return laser current
        @return float: laser current in amperes
        """
        return self.current_setpoint

    def get_current_setpoint(self):
        return self.current_setpoint

    def set_current(self, current):
        self.current_setpoint = current
        return self.current_setpoint

    def allowed_control_modes(self):
        return [ControlMode.POWER, ControlMode.CURRENT]

    def get_control_mode(self):
        return self.mode

    def set_control_mode(self, control_mode):
        self.mode = control_mode
        return self.mode

    def on(self):
        self.lstate = LaserState.ON
        return self.lstate

    def off(self):
        self.lstate = LaserState.OFF
        return self.lstate

    def get_laser_state(self):
        return self.lstate

    def set_laser_state(self, state):
        self.lstate = state
        return self.lstate

    def get_shutter_state(self):
        return self.shutter

    def set_shutter_state(self, state):
        self.shutter = state
        return self.shutter

    def get_temperatures(self):
        return {'psu': 32.2, 'head': 42.0}

    def set_temperatures(self, temps):
        return {}

    def get_extra_info(self):
        return "Dummy laser v0.9.9\nnot used very much\nvery cheap price good quality"
