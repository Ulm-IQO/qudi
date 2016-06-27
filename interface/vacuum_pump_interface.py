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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
"""
from core.util.customexceptions import *
from enum import Enum

class VacuumPumpInterface:
    _modtype = 'PumprInterface'
    _modclass = 'interface'

    def get_extra_info(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_pressures(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_pump_speeds(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def get_pump_powers(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_pump_states(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_pump_states(self, states):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_system_state(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_system_state(self, state):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
