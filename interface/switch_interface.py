# -*- coding: utf-8 -*-

"""
Control the Radiant Dyes flip mirror driver through the serial interface.

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


class SwitchInterface(metaclass=InterfaceMetaclass):
    """ Methods to control slow (mechanical) laser switching devices.

    Warning: This interface use CamelCase. This is should not be done in future versions. See more info here :
    documentation/programming_style.md
    """

    @property
    @abstract_interface_method
    def name(self):
        pass

    @property
    @abstract_interface_method
    def states(self):
        pass

    @states.setter
    @abstract_interface_method
    def states(self, value):
        pass

    @property
    @abstract_interface_method
    def names_of_states(self):
        pass

    @property
    @abstract_interface_method
    def number_of_switches(self):
        pass

    @property
    @abstract_interface_method
    def names_of_switches(self):
        pass

    @abstract_interface_method
    def get_state(self, number_of_switch):
        pass

    @abstract_interface_method
    def set_state(self, number_of_switch, state):
        pass