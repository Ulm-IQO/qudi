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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
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
    NOSHUTTER = 4

class LaserState(Enum):
    OFF = 0
    ON = 1
    UNKNOWN = 2

class SimpleLaserInterface:
    _modtype = 'SimpleLaserInterface'
    _modclass = 'interface'

    def get_power(self):
        """ Return laser power
        @return float: Laser power in watts
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def set_power(self, power):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_power_setpoint(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
    
    def get_current(self):
        """ Return laser current
        @return float: laser current in amperes
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_current_setpoint(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_current(self, current):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_control_mode(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_control_mode(self, control_mode):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def on(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def off(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_laser_state(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
    
    def set_laser_state(self, state):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_shutter_state(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_shutter_state(self, state):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_temperatures(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_temperatures(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_extra_info(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
