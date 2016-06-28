# -*- coding: utf-8 -*-
"""
Interface file for lasers where current and power can be set.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
from core.util.customexceptions import *
from enum import Enum

class ControlMode(Enum):
    MIXED = 0
    POWER = 1
    CURRENT = 2

class ShutterState(Enum):
    CLOSED = 0
    OPEN = 1
    UNKNOWN = 2
    NOSHUTTER = 3

class LaserState(Enum):
    OFF = 0
    ON = 1
    BLOCKED = 2
    UNKNOWN = 3

class SimpleLaserInterface:
    _modtype = 'SimpleLaserInterface'
    _modclass = 'interface'

    def get_power(self):
        """ Return laser power
        @return float: Actual laser power in watts
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def set_power(self, power):
        """ Set laer power ins watts
          @param float power: laser power setpoint in watts

          @return float: laser power setpoint in watts
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_power_setpoint(self):
        """ Return laser power setpoint
        @return float: Laser power setpoint in watts
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
    
    def get_current(self):
        """ Return laser current
        @return float: Actual laser current in amperes
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_current_setpoint(self):
        """ Return laser current
        @return float: Laser current setpoint in amperes
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_current(self, current):
        """ Set laser current
        @param float current: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_control_mode(self):
        """ Get control mode of laser
          @return enum ControlMode: control mode
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_control_mode(self, control_mode):
        """ Set laser control mode.
          @param enum control_mode: desired control mode
          @return enum ControlMode: actual control mode
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def on(self):
        """ Turn on laser. Does not open shutter if one is present.
          @return enum LaserState: actual laser state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def off(self):
        """ Turn ooff laser. Does not close shutter if one is present.
          @return enum LaserState: actual laser state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_laser_state(self):
        """ Get laser state.
          @return enum LaserState: laser state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
    
    def set_laser_state(self, state):
        """ Set laser state.
          @param enum state: desired laser state
          @return enum LaserState: actual laser state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_shutter_state(self):
        """ Get shutter state. Has a state for no shutter present.
          @return enum ShutterState: actual shutter state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_shutter_state(self, state):
        """ Set shutter state.
          @param enum state: desired shutter state
          @return enum ShutterState: actual shutter state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_temperatures(self):
        """ Get all available temperatures from laser.
          @return dict: dict of name, value for temperatures
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_temperature_setpoints(self):
        """ Get all available temperature setpoints from laser.
          @return dict: dict of name, value for temperature setpoints
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_temperatures(self, temps):
        """ Set laser temperatures.
          @param temps: dict of name, value to be set
          @return dict: dict of name, value of temperatures that were set
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
