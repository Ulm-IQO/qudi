# -*- coding: utf-8 -*-
"""
Interface file for a controller of process variable via setpoint value only.
(Please refer to PID controller interface for full PID features.

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

import abc
from core.util.interfaces import InterfaceMetaclass
from interface.process_interface import ProcessInterface
from interface.setpoint_interface import SetpointInterface


class SetpointControllerInterface(ProcessInterface, SetpointInterface, metaclass=InterfaceMetaclass):
    _modtype = 'SetpointControllerInterface'
    _modclass = 'interface'

    # Most function are defined via ProcessInterface, SetpointInterface

    @abc.abstractmethod
    def get_enabled(self):
        """ Get the current state of the controller

        @return boolean:
        """
        pass

    @abc.abstractmethod
    def set_enabled(self, enabled):
        """ Set the current state of the controller

        @return boolean:
        """
        pass
