# -*- coding: utf-8 -*-

"""
Combine two hardware switches into one.

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

from core.module import Base
from interface.switch_interface import SwitchInterface
from core.configoption import ConfigOption
from core.connector import Connector


class SwitchCombinerInterfuse(Base, SwitchInterface):
    """ Methods to control slow (mechanical) laser switching devices.
    This interfuse in particular combines two switches into one.
    """

    # connectors for the switches to be combined
    switch1 = Connector(interface='SwitchInterface')
    switch2 = Connector(interface='SwitchInterface')

    # optional name of the combined hardware
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')

    # if extend_hardware_name is True the switch names will be extended by the hardware name
    # of the individual switches in front.
    _extend_hardware_name = ConfigOption(name='extend_hardware_name', default=False, missing='nothing')

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        if self._hardware_name is None:
            self._hardware_name = self._name

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        pass

    @property
    def number_of_switches(self):
        """ Number of switches provided by this hardware.

        @return int: number of switches
        """
        return self.switch1().number_of_switches + self.switch2().number_of_switches

    @property
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def names_of_states(self):
        """ Names of the states as a dict of lists.

        The keys contain the names for each of the switches and each of switches
        has a list of elements representing the names in the state order.
        The switch names might be extended by the name of the hardware as a prefix if extend_hardware_name is True.

        @return dict: A dict of the form {"switch": ["state1", "state2"]}
        """
        if self._extend_hardware_name:
            new_dict = {self.switch1().name + '.' + switch: states
                        for switch, states in self.switch1().names_of_states.items()}
            for switch, states in self.switch2().names_of_states.items():
                new_dict[self.switch2().name + '.' + switch] = states
        else:
            new_dict = self.switch1().names_of_states + self.switch2().names_of_states
        return new_dict

    @property
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.
        The switch names might be extended by the name of the hardware as a prefix if extend_hardware_name is True.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        if self._extend_hardware_name:
            new_dict = {self.switch1().name + '.' + switch: states
                        for switch, states in self.switch1().states.items()}
            for switch, states in self.switch2().states.items():
                new_dict[self.switch2().name + '.' + switch] = states
        else:
            new_dict = self.switch1().states + self.switch2().states
        return new_dict

    @states.setter
    def states(self, value):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.
        The switch names might need to be extended by the name of the hardware as a prefix
        if extend_hardware_name is True.

        @param dict value: state dict of the form {"switch": "state"}
        @return: None
        """
        if isinstance(value, dict):
            states1 = dict()
            states2 = dict()
            for switch, state in value.items():
                if self._extend_hardware_name:
                    if switch.startswith(self.switch1().name):
                        switch = switch[len(self.switch1().name) + 1:]
                    elif switch.startswith(self.switch2().name):
                        switch = switch[len(self.switch2().name) + 1:]

                if switch in self.switch1().names_of_states:
                    states1[switch] = state
                else:
                    states2[switch] = state
            self.switch1().states = states1
            self.switch2().states = states2
        else:
            self.log.error(f'attempting to set states as "{value}" while states have be a dict '
                           f'having the switch names as keys and the state names as values.')
