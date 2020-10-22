# -*- coding: utf-8 -*-

"""
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
    """ Methods to control slow (mechanical) switching devices.

    This interface uses pythonic properties and setters as well as get_ and set_ methods to access the switch states.
    Both need to be implemented but can rely on each other.
    """

    @property
    @abstract_interface_method
    def name(self):
        """
        Name of the hardware module.
            @return str: The name of the hardware
        """
        pass

    @property
    @abstract_interface_method
    def states(self):
        """
        The states of the system as a list of boolean values.
            @return list(bool): All the current states of the switches in a list
        """
        pass

    @states.setter
    @abstract_interface_method
    def states(self, value):
        """
        The states of the system can be set in two ways:
        Either as a single boolean value to define all the states to be the same
        or as a list of boolean values to define the state of each switch individually.
            @param [bool/list(bool)] value: switch state to be set as single boolean or list of booleans
            @return: None
        """
        pass

    @property
    @abstract_interface_method
    def names_of_states(self):
        """
        Names of the states as a list of lists. The first list contains the names for each of the switches
        and each of switches has two elements representing the names in the state order [False, True].
            @return list(list(str)): 2 dimensional list of names in the state order [False, True]
        """
        pass

    @property
    @abstract_interface_method
    def names_of_switches(self):
        """
        Names of the switches as a list of length number_of_switches.
            @return list(str): names of the switches
        """
        pass

    @property
    @abstract_interface_method
    def number_of_switches(self):
        """
        Number of switches provided by this hardware.
            @return int: number of switches
        """
        pass

    @abstract_interface_method
    def get_state(self, index_of_switch):
        """
        Returns the state of a specific switch which was specified by its switch index.
            @param int index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @return bool: boolean value of this specific switch
        """
        pass

    @abstract_interface_method
    def set_state(self, index_of_switch, state):
        """
        Sets the state of a specific switch which was specified by its switch index.
            @param int index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @param bool state: boolean state of the switch to be set
            @return int: state of the switch actually set
        """
        pass
