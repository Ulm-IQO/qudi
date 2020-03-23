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
    _extend_hardware_name = ConfigOption(name='extend_hardware_name',
                                         default=False,
                                         missing='nothing')

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
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        if self._extend_hardware_name:
            new_dict = {f'{self.switch1().name}.{switch}': states
                        for switch, states in self.switch1().available_states.items()}
            new_dict.update({f'{self.switch2().name}.{switch}': states
                             for switch, states in self.switch2().available_states.items()})
        else:
            new_dict = {**self.switch1().available_states, **self.switch2().available_states}
        return new_dict

    @property
    def number_of_switches(self):
        """ Number of switches provided by the hardware.

        @return int: number of switches
        """
        return self.switch1().number_of_switches + self.switch2().number_of_switches

    @property
    def switch_names(self):
        """ Names of all available switches as tuple.

        @return str[]: Tuple of strings of available switch names.
        """
        return tuple(self.available_states)

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        if self._extend_hardware_name:
            hw_name = self.switch1().name
            new_dict = {
                f'{hw_name}.{switch}': states for switch, states in self.switch1().states.items()
            }
            hw_name = self.switch2().name
            new_dict.update(
                {f'{hw_name}.{switch}': states for switch, states in self.switch2().states.items()}
            )
        else:
            new_dict = {**self.switch1().states, **self.switch2().states}
        return new_dict

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        assert isinstance(state_dict,
                          dict), f'Property "state" must be dict type. Received: {type(state_dict)}'
        states1 = dict()
        states2 = dict()
        hardware1 = self.switch1()
        hardware2 = self.switch2()
        for switch, state in state_dict.items():
            if self._extend_hardware_name:
                if switch.startswith(f'{hardware2.name}.'):
                    states2[switch[len(hardware2.name) + 1:]] = state
                elif switch.startswith(f'{hardware1.name}.'):
                    states1[switch[len(hardware1.name) + 1:]] = state
            else:
                if switch in hardware2.available_states:
                    states2[switch] = state
                else:
                    states1[switch] = state
        if states1:
            hardware1.states = states1
        if states2:
            hardware2.states = states2

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, f'Invalid switch name: "{switch}"'
        if self._extend_hardware_name:
            hardware = self.switch2()
            if switch.startswith(f'{hardware.name}.'):
                return hardware.get_state(switch[len(hardware.name) + 1:])
            hardware = self.switch1()
            if switch.startswith(f'{hardware.name}.'):
                return hardware.get_state(switch[len(hardware.name) + 1:])
        else:
            hardware = self.switch2()
            if switch in hardware.available_states:
                return hardware.get_state(switch)
            return self.switch1().get_state(switch)

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        if self._extend_hardware_name:
            hardware = self.switch2()
            if switch.startswith(f'{hardware.name}.'):
                return hardware.set_state(switch[len(hardware.name) + 1:], state)
            hardware = self.switch1()
            if switch.startswith(f'{hardware.name}.'):
                return hardware.set_state(switch[len(hardware.name) + 1:], state)
        else:
            hardware = self.switch2()
            if switch in hardware.available_states:
                return hardware.set_state(switch, state)
            return self.switch1().set_state(switch, state)
