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

    This interface pythonic properties and setters to access the switch states.
    Both need to be implemented but can rely on each other.
    """

    @property
    @abstract_interface_method
    def number_of_switches(self):
        """ Number of switches provided by the hardware.

        @return int: number of switches
        """
        pass

    @property
    @abstract_interface_method
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        pass

    @property
    @abstract_interface_method
    def names_of_states(self):
        """ Names of the states as a dict of lists.

        The keys contain the names for each of the switches and each of switches
        has a list of elements representing the names in the state order.

        @return dict: A dict of the form {"switch": ["state1", "state2"]}
        """
        pass

    @property
    @abstract_interface_method
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        pass

    @states.setter
    @abstract_interface_method
    def states(self, value):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict value: state dict of the form {"switch": "state"}
        @return: None
        """
        pass
