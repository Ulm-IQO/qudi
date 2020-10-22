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
import numpy as np


class SwitchCombinerInterfuse(Base, SwitchInterface):
    """ Methods to control slow (mechanical) laser switching devices.
    This interfuse in particular combines two switches into one.
    """

    switch1 = Connector(interface='SwitchInterface')
    switch2 = Connector(interface='SwitchInterface')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _extend_hardware_name = ConfigOption(name='extend_hardware_name', default=False, missing='nothing')

    def on_activate(self):
        """
        Activate the module and fill status variables.
        """
        if self._hardware_name is None:
            self._hardware_name = self._name

    def on_deactivate(self):
        """
        Deactivate the module and clean up.
        """
        pass

    @property
    def name(self):
        """
        Name can either be defined as ConfigOption (name) or it defaults to the name of the hardware module.
            @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def states(self):
        """
        The states of the system as a list of boolean values.
            @return list(bool): All the current states of the switches in a list
        """
        return list(self.switch1().states) + list(self.switch2().states)

    @states.setter
    def states(self, value):
        """
        The states of the system can be set in two ways:
        Either as a single boolean value to define all the states to be the same
        or as a list of boolean values to define the state of each switch individually.
            @param [bool/list(bool)] value: switch state to be set as single boolean or list of booleans
            @return: None
        """
        if np.isscalar(value):
            self.switch1().states = value
            self.switch2().states = value
        else:
            if len(value) != self.number_of_switches:
                self.log.error(f'The states either have to be a scalar or a list af length {self.number_of_switches}')
            else:
                self.switch1().states = value[:self.switch1().number_of_switches]
                self.switch2().states = value[self.switch1().number_of_switches:]

    @property
    def names_of_states(self):
        """
        Names of the states as a list of lists. The first list contains the names for each of the switches
        and each of switches has two elements representing the names in the state order [False, True].
            @return list(list(str)): 2 dimensional list of names in the state order [False, True]
        """
        return list(self.switch1().names_of_states) + list(self.switch2().names_of_states)

    @property
    def number_of_switches(self):
        """
        Number of switches provided by this hardware.
            @return int: number of switches
        """
        return self.switch1().number_of_switches + self.switch2().number_of_switches

    @property
    def names_of_switches(self):
        """
        Names of the switches as a list of length number_of_switches.
        If the ConfigOption extend_hardware_name is True, all switch names start
        with the individual hardware name followed by a "." and then the name of the switch.
            @return list(str): names of the switches
        """
        if self._extend_hardware_name:
            return [self.switch1().name + '.' + switch for switch in self.switch1().names_of_switches] \
                   + [self.switch2().name + '.' + switch for switch in self.switch2().names_of_switches]
        else:
            return list(self.switch1().names_of_switches) + list(self.switch2().names_of_switches)

    def get_state(self, index_of_switch):
        """
        Returns the state of a specific switch which was specified by its switch index.
            @param int index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @return bool: boolean value of this specific switch
        """
        if index_of_switch < self.switch1().number_of_switches:
            return self.switch1().get_state(index_of_switch)
        else:
            return self.switch2().get_state(index_of_switch - self.switch1().number_of_switches)

    def set_state(self, index_of_switch, state):
        """
        Sets the state of a specific switch which was specified by its switch index.
            @param int index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @param bool state: boolean state of the switch to be set
            @return int: state of the switch actually set
        """
        if index_of_switch < self.switch1().number_of_switches:
            return self.switch1().set_state(index_of_switch, state)
        else:
            return self.switch2().set_state(index_of_switch - self.switch1().number_of_switches, state)
