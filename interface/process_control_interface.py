# -*- coding: utf-8 -*-

"""
This interface is used to manage a control value.

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


class ProcessControlInterface(metaclass=InterfaceMetaclass):
    """ A very simple interface to control a single value.
        Used for PID control.

        This interface can be used to command the power, flow or any value of a device that can be turned on or off.

    """

    _modtype = 'ProcessControlInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def set_control_value(self, value):
        """ Set the value of the controlled process variable """
        pass

    @abc.abstractmethod
    def get_control_value(self):
        """ Get the value of the controlled process variable """
        pass

    @abc.abstractmethod
    def get_control_unit(self):
        """ Return the unit that the value is set in as a tuple of ('abreviation', 'full unit name') """
        pass

    @abc.abstractmethod
    def get_control_limits(self):
        """ Return limits within which the controlled value can be set as a tuple of (low limit, high limit)
        """
        pass

    @abc.abstractmethod
    def get_enabled(self):
        """ Return the enabled state of the control device
        """
        pass

    @abc.abstractmethod
    def set_enabled(self, enabled):
        """ Set the enabled state of the control device
         """
        pass
