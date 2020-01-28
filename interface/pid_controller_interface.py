# -*- coding: utf-8 -*-
"""
Interface file for vacuum turbopumps with prepumps and pressure sensors.

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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class PIDControllerInterface(metaclass=InterfaceMetaclass):
    """
    """

    @abstract_interface_method
    def get_kp(self):
        pass

    @abstract_interface_method
    def set_kp(self, kp):
        pass

    @abstract_interface_method
    def get_ki(self):
        pass

    @abstract_interface_method
    def set_ki(self, ki):
        pass

    @abstract_interface_method
    def get_kd(self):
        pass

    @abstract_interface_method
    def set_kd(self, kd):
        pass

    @abstract_interface_method
    def get_setpoint(self):
        pass

    @abstract_interface_method
    def set_setpoint(self, setpoint):
        pass

    @abstract_interface_method
    def get_manual_value(self):
        pass

    @abstract_interface_method
    def set_manual_value(self, manualvalue):
        pass

    @abstract_interface_method
    def get_enabled(self):
        pass

    @abstract_interface_method
    def set_enabled(self, enabled):
        pass

    @abstract_interface_method
    def get_control_limits(self):
        pass

    @abstract_interface_method
    def set_control_limits(self, limits):
        pass

    @abstract_interface_method
    def get_process_value(self):
        pass

    @abstract_interface_method
    def get_control_value(self):
        pass

    @abstract_interface_method
    def get_process_unit(self):
        pass

    @abstract_interface_method
    def get_control_unit(self):
        pass

    @abstract_interface_method
    def get_extra(self):
        pass
