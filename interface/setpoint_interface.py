# -*- coding: utf-8 -*-

"""
Interface file to define a setpoint for a process variable.

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


class SetpointInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to manage a setpoint value.
    """

    _modtype = 'ProcessControlInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_setpoint(self):
        """ Getter for the setpoint value

        Return a value in unit
        """
        pass

    @abc.abstractmethod
    def set_setpoint(self, setpoint):
        """ Set the current setpoint

        Parameter : new value desired in unit
        Return the real new value
        """
        pass

    @abc.abstractmethod
    def get_setpoint_unit(self):
        """ Return the unit that the setpoint value is set in as a tuple of ('abbreviation', 'full unit name') """
        pass

    @abc.abstractmethod
    def get_setpoint_limits(self):
        """ Return limits within which the setpoint value can be set as a tuple of (low limit, high limit)
        """
        pass
