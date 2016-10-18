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

import abc
from core.util.interfaces import InterfaceMetaclass


class PIDControllerInterface(metaclass=InterfaceMetaclass):
    _modtype = 'PIDControllerInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_kp(self):
        pass

    @abc.abstractmethod
    def set_kp(self, kp):
        pass

    @abc.abstractmethod
    def get_ki(self):
        pass

    @abc.abstractmethod
    def set_ki(self, ki):
        pass

    @abc.abstractmethod
    def get_kd(self):
        pass

    @abc.abstractmethod
    def set_kd(self, kd):
        pass

    @abc.abstractmethod
    def get_setpoint(self):
        pass

    @abc.abstractmethod
    def set_setpoint(self, setpoint):
        pass

    @abc.abstractmethod
    def get_manual_value(self):
        pass

    @abc.abstractmethod
    def set_manual_value(self, manualvalue):
        pass

    @abc.abstractmethod
    def get_enabled(self):
        pass

    @abc.abstractmethod
    def set_enabled(self, enabled):
        pass

    @abc.abstractmethod
    def get_control_limits(self):
        pass

    @abc.abstractmethod
    def set_control_limits(self, limits):
        pass

    @abc.abstractmethod
    def get_process_value(self):
        pass

    @abc.abstractmethod
    def get_control_value(self):
        pass

    @abc.abstractmethod
    def get_extra(self):
        pass
