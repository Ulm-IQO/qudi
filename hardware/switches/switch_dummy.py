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
    """ Methods to control slow laser switching devices.

    Example config for copy-paste:

    switch_dummy:
        module.Class: 'switches.switch_dummy.SwitchDummy'
        number_of_switches: 3
        names_of_states: ['down', 'up']
        names_of_switches: ['one', 'two', 'one']
        name: 'First'
    """

    _number_of_switches = ConfigOption(name='number_of_switches', default=1, missing='nothing')
    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _reset_states = ConfigOption(name='reset_states', default=False, missing='nothing')

    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):

        if self._hardware_name is None:
            self._hardware_name = self._name

        if np.shape(self._names_of_states) == (2,):
            self._names_of_states = [list(self._names_of_states)] * self.number_of_switches
        elif np.shape(self._names_of_states) == (self.number_of_switches, 2):
            self._names_of_states = list(self._names_of_states)
        else:
            self.log.error(f'names_of_states must either be a list of two names for the states [low, high] '
                           f'which are applied to all switched or it must be a list '
                           f'of length {self._number_of_switches} with elements of the aforementioned shape.')

        if np.shape(self._names_of_switches) == (self.number_of_switches,):
            self._names_of_switches = list(self._names_of_switches)
        else:
            self._names_of_switches = [str(index + 1) for index in range(self.number_of_switches)]

        # initialize channels to saved status if requested
        if self._reset_states:
            self.states = False

        if self.states is None or len(self.states) != self.number_of_switches:
            self.states = [False] * self.number_of_switches

    def on_deactivate(self):
        pass

    @property
    def name(self):
        return self._hardware_name

    @property
    def states(self):
        return self._states.copy()

    @states.setter
    def states(self, value):
        if np.isscalar(value):
            self._states = [bool(value)] * self.number_of_switches
        else:
            if len(value) != self.number_of_switches:
                self.log.error(f'The states either have to be a scalar or a list af length {self.number_of_switches}')
            else:
                self._states = [bool(state) for state in value]

    @property
    def names_of_states(self):
        return self._names_of_states.copy()

    @property
    def names_of_switches(self):
        return self._names_of_switches.copy()

    @property
    def number_of_switches(self):
        return int(self._number_of_switches)

    def get_state(self, index_of_switch):
        if 0 <= index_of_switch < self.number_of_switches:
            return self._states[int(index_of_switch)]
        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return False

    def set_state(self, index_of_switch, state):
        if 0 <= index_of_switch < self.number_of_switches:
            self._states[int(index_of_switch)] = bool(state)
            return self._states[int(index_of_switch)]

        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return -1
