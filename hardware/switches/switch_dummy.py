# -*- coding: utf-8 -*-
"""
Dummy implementation for switching interface.

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
from core.statusvariable import StatusVar
import numpy as np


class SwitchDummy(Base, SwitchInterface):
    """ Methods to control slow switching devices.

    Example config for copy-paste:

    switch_dummy:
        module.Class: 'switches.switch_dummy.SwitchDummy'
        names_of_states: ['down', 'up']
        names_of_switches: ['one', 'two', 'tree']
        name: 'First'
    """

    # ConfigOptions
    _number_of_switches = ConfigOption(name='number_of_switches', default=1, missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _remember_states = ConfigOption(name='remember_states', default=True, missing='nothing')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    def on_activate(self):
        """
        Activate the module and fill status variables.
        """

        # Fill internal variables depending on ConfigOptions
        if self._hardware_name is None:
            self._hardware_name = self._name

        if isinstance(self._names_of_switches, str):
            self._names_of_switches = [str(self._names_of_switches)]
        else:
            try:
                self._names_of_switches = [str(name) for name in self._names_of_switches]
            except TypeError:
                self._names_of_switches = [str(index + 1) for index in range(self._number_of_switches)]

        try:
            if len(self._names_of_states) == len(self._names_of_switches) \
                    and len(self._names_of_states[0]) > 1 \
                    and not isinstance(self._names_of_states[0], str):
                self._names_of_states = {switch: [str(name) for name in self._names_of_states[index]]
                                         for index, switch in enumerate(self._names_of_switches)}
            else:
                raise TypeError
        except TypeError:
            if not isinstance(self._names_of_states, str) and len(self._names_of_states) > 1:
                self._names_of_states = {switch: [str(name) for name in self._names_of_states]
                                         for index, switch in enumerate(self._names_of_switches)}
            else:
                self.log.error(f'names_of_states must either be a list of two or more names for the states '
                               f'which are applied to all switched or it must be a list '
                               f'of length {len(self._names_of_switches)} with elements of the aforementioned shape.')

        # initialize channels to saved status if requested
        if not self._remember_states \
                or not isinstance(self._states, dict) \
                or len(self._states) != self.number_of_switches:
            self._states = {name: self._names_of_states[name][0] for name in self._names_of_switches}

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
        return self._states.copy()

    @states.setter
    def states(self, value):
        """
        The states of the system can be set in two ways:
        Either as a single boolean value to define all the states to be the same
        or as a list of boolean values to define the state of each switch individually.
            @param [bool/list(bool)] value: switch state to be set as single boolean or list of booleans
            @return: None
        """
        if isinstance(value, dict):
            for switch, state in value.items():
                if switch not in self._names_of_switches:
                    self.log.warning(f'Attempted to set a switch of name "{switch}" but it does not exist.')
                    continue

                states = self.names_of_states[switch]
                if isinstance(state, str):
                    if state not in states:
                        self.log.error(f'"{state}" is not among the possible states: {states}')
                        continue
                    self._states[switch] = state
        else:
            self.log.error(f'attempting to set states as "{value}" while states have be a dict '
                           f'having the switch names as keys and the state names as values.')

    @property
    def names_of_states(self):
        """
        Names of the states as a list of lists. The first list contains the names for each of the switches
        and each of switches has two elements representing the names in the state order [False, True].
        The names can be defined by a ConfigOption (names_of_states) or they default to ['Off', 'On'].
            @return list(list(str)): 2 dimensional list of names in the state order [False, True]
        """
        return self._names_of_states.copy()

    @property
    def number_of_switches(self):
        """
        Number of switches provided by this hardware. Can be set by ConfigOption (number_of_switches) or defaults to 1.
            @return int: number of switches
        """
        return len(self._names_of_switches)
