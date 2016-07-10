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

class VacuumPumpInterface:
    _modtype = 'PumpInterface'
    _modclass = 'interface'

    def get_extra_info(self):
        """ Present extra information about pump controller/device.
        
          @return str: arbitrary information about pump, like model nr, hardware version, firmware version
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_pressures(self):
        """All available pressures in Pascal.

          @return dict: dict of gauge name and pressure
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_pump_speeds(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))
        
    def get_pump_powers(self):
        """ All available pump powers in watts.

          @return dict: dict of pump name and pump power
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_pump_states(self):
        """All available pump states.

          @return dict: dict of pump name and pump state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_pump_states(self, states):
        """Control the pump state.
          @param dict states: dict of pump name and desired state
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def get_system_state(self):
        """Get overall system state.
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_system_state(self, state):
        """Control the system state.
        """
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

