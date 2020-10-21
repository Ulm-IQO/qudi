# -*- coding: utf-8 -*-
"""
Aggregate multiple switches.

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

from logic.generic_logic import GenericLogic
from core.connector import Connector
from qtpy import QtCore
import numpy as np


class SwitchLogic(GenericLogic):
    """ Logic module aggregating multiple hardware switches.
    """
    switch = Connector(interface='SwitchInterface')

    sig_switch_updated = QtCore.Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._ensure_unambiguous_names()

    def _ensure_unambiguous_names(self):
        self.__names_of_states = [[name.lower().replace(' ', '_') for name in switch]
                                  for switch in self.names_of_states]
        self.__names_of_switches = [name.lower().replace(' ', '_') for name in self.names_of_switches]
        for sw_index, switch in enumerate(self.__names_of_switches):
            if self.__names_of_switches.count(switch) > 1:
                self.log.warning(f'Switch name "{switch}" not unambiguous, adding numbers to the switch.')
                occurences = [i for i, x in enumerate(self.__names_of_switches) if x == switch]
                for i, position in enumerate(occurences):
                    self.__names_of_switches[position] = switch + str(i + 1)

            if self.__names_of_states[sw_index][0] == self.__names_of_states[sw_index][1]:
                self.log.warning(f'State name "{self.__names_of_states[sw_index][0]}" '
                                 f'of switch "{self.__names_of_switches[sw_index]}" is not unambiguous '
                                 f'using "down" and "up" instead.')
                self.__names_of_states[sw_index][0] = 'down'
                self.__names_of_states[sw_index][1] = 'up'

    def on_deactivate(self):
        """ Deactivate module.
        """

    @property
    def names_of_states(self):
        return self.switch().names_of_states

    @property
    def name_of_hardware(self):
        return self.switch().name

    @property
    def names_of_switches(self):
        return self.switch().names_of_switches

    @property
    def number_of_switches(self):
        return self.switch().number_of_switches

    @property
    def states(self):
        return self.switch().states

    @states.setter
    def states(self, value):
        if np.isscalar(value):
            if isinstance(value, str):
                if all(x == self.__names_of_states[0] for x in self.__names_of_states):
                    state = self._get_state_value(value, switch_index=0)
                    if state is not None:
                        self.switch().states = state
                else:
                    self.log.error(f'The state names of the switches are not the same, '
                                   f'so the value of the switch state "{value}" cannot be determined.')
            else:
                self.switch().states = value
        elif np.shape(value) == (self.number_of_switches,):
            for switch_index in range(self.number_of_switches):
                value[switch_index] = self._get_state_value(value[switch_index], switch_index)
            if None not in value:
                self.switch().states = value
        else:
            self.log.error(f'The shape of the states was {np.shape(value)} '
                           f'but needs to be ({self.number_of_switches}, ).')
        self.sig_switch_updated.emit(self.states)

    def _get_switch_index(self, switch_index):
        if isinstance(switch_index, (int, float)):
            return int(switch_index)
        elif isinstance(switch_index, str):
            switch_name = switch_index.lower().replace(' ', '_')
            if switch_name in self.__names_of_switches:
                return self.__names_of_switches.index(switch_name)
            self.log.error(f'switch "{switch_index}" not found, options are {self.__names_of_switches}.')
            return -1
        self.log.error(f'The switch_index was "{switch_index}" but either has to be an '
                       f'int or the name of the switch as a string.')
        return -2

    def _get_state_value(self, state, switch_index):
        if not isinstance(state, str):
            return bool(state)

        state = state.lower().replace(' ', '_')
        if 0 <= switch_index < self.number_of_switches:
            if state in self.__names_of_states[switch_index]:
                return bool(self.__names_of_states[switch_index].index(state))
            else:
                self.log.error(f'state name "{state}" not found for switch "{switch_index}", '
                               f'options are "{self.__names_of_states[switch_index]}".')
                return None
        else:
            self.log.error(f'The switch_index was {switch_index} '
                           f'but needs to be in the range from 0 to {self.number_of_switches - 1}.')
            return None

    def set_state(self, switch_index, state):
        switch_index = self._get_switch_index(switch_index)
        if 0 <= switch_index < self.number_of_switches:
            self.switch().set_state(switch_index, self._get_state_value(state, switch_index=switch_index))
            self.sig_switch_updated.emit(self.states)

    def get_state(self, switch_index):
        switch_index = self._get_switch_index(switch_index)
        if 0 <= switch_index < self.number_of_switches:
            return self.switch().get_state(switch_index)
        else:
            if switch_index > 0:
                self.log.error(f'The switch_index was {switch_index} '
                               f'but needs to be in the range from 0 to {self.number_of_switches - 1}.')
            return False
