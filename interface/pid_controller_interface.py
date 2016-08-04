# -*- coding: utf-8 -*-
"""
Interface file for vacuum turbopumps with prepumps and pressure sensors.

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

class PIDControllerInterface:
    _modtype = 'PIDControllerInterface'
    _modclass = 'interface'

    def get_kp(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_kp(self, kp):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_ki(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_ki(self, ki):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_kd(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_kd(self, kd):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_setpoint(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_setpoint(self, setpoint):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_manual_value(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def set_manual_value(self, manualvalue):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_enabled(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_enabled(self, enabled):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_control_limits(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
    
    def set_control_limits(self, limits):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_process_value(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_control_value(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_extra(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
