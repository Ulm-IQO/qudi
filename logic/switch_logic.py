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
    switch = Connector(interface='SwitchInterface', optional=True)
    switch0 = Connector(interface='SwitchInterface', optional=True)
    switch1 = Connector(interface='SwitchInterface', optional=True)
    switch2 = Connector(interface='SwitchInterface', optional=True)
    switch3 = Connector(interface='SwitchInterface', optional=True)
    switch4 = Connector(interface='SwitchInterface', optional=True)
    switch5 = Connector(interface='SwitchInterface', optional=True)
    switch6 = Connector(interface='SwitchInterface', optional=True)
    switch7 = Connector(interface='SwitchInterface', optional=True)
    switch8 = Connector(interface='SwitchInterface', optional=True)
    switch9 = Connector(interface='SwitchInterface', optional=True)

    sig_switch_updated = QtCore.Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hw_switches = list()
        self._magic_commands = dict()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        if self.switch.is_connected:
            self._hw_switches.append(self.switch)

        for i in range(10):
            if getattr(self, f'switch{i:d}').is_connected:
                self._hw_switches.append(getattr(self, f'switch{i:d}'))

        self._build_magic()

    def on_deactivate(self):
        """ Deactivate module.
        """
        self._hw_switches = list()

    def _switch(self, index):
        if 0 <= index < len(self._hw_switches):
            return self._hw_switches[int(index)]()
        self.log.error(f'The index of the hardware was {index} '
                       f'but needs to be in the range from 0 to {self.number_of_hardware - 1}.')
        return None

    @property
    def names_of_states(self):
        return [switch().names_of_states for switch in self._hw_switches]

    @property
    def names_of_hardware(self):
        return [switch().name for switch in self._hw_switches]

    @property
    def names_of_switches(self):
        return [switch().names_of_switches for switch in self._hw_switches]

    @property
    def number_of_switches(self):
        return [switch().number_of_switches for switch in self._hw_switches]

    @property
    def number_of_hardware(self):
        return len(self._hw_switches)

    @property
    def states(self):
        return [switch().states for switch in self._hw_switches]

    @states.setter
    def states(self, value):
        if np.isscalar(value):
            for index, hw_switch in enumerate(self._hw_switches):
                hw_switch().states = value
            self.sig_switch_updated.emit(self.states)
        elif np.shape(value) == (self.number_of_hardware,):
            for index, hw_switch in enumerate(self._hw_switches):
                if np.isscalar(value[index]) or len(value[index]) == hw_switch().number_of_switches:
                    hw_switch().states = value[index]
                else:
                    self.log.error(f'The dimension of the switch named "{hw_switch().name}" was {len(value[index])} '
                                   f'but needs to be {hw_switch().number_of_switches}.')
            self.sig_switch_updated.emit(self.states)
        else:
            self.log.error(f'The length of the first dimension of the states was {len(value)} '
                           f'but needs to be {self.number_of_hardware}.')

    def set_state(self, hardware_index=None, switch_index=None, state=False):
        if hardware_index is None:
            if isinstance(state, str):
                self.log.error(f'You set the state "{state}" for undefined hardware.')
                return -11
            self.states = state
        else:
            if isinstance(hardware_index, str):
                try:
                    hardware_index = self.__names_of_hardware.index(hardware_index.lower().replace(' ', '_'))
                except ValueError:
                    self.log.error(f'keyword "{hardware_index}" not found. Options are: {self.__names_of_hardware}')
                    return -1
            if switch_index is None:
                if isinstance(state, str) \
                        and self.__names_of_states[hardware_index][1:] == self.__names_of_states[hardware_index][:-1]:
                    try:
                        state = self.__names_of_states[hardware_index][0].index(state.lower().replace(' ', '_'))
                    except ValueError:
                        self.log.error(f'keyword "{state}" not found. '
                                       f'Options are: {self.__names_of_states[hardware_index][0]}')
                        return -4
                if isinstance(state, str):
                    self.log.error(f'You set the state "{state}" for undefined switches.')
                    return -12
                self._switch(hardware_index).states = state
                self.sig_switch_updated.emit(self.states)
            else:
                if isinstance(switch_index, str):
                    try:
                        switch_index = self.__names_of_switches[hardware_index].index(
                            switch_index.lower().replace(' ', '_'))
                    except ValueError:
                        self.log.error(f'keyword "{switch_index}" not found. '
                                       f'Options are: {self.__names_of_switches[hardware_index]}')
                        return -2
                if isinstance(state, str):
                    try:
                        state = self.__names_of_states[hardware_index][switch_index].index(
                            state.lower().replace(' ', '_'))
                    except ValueError:
                        self.log.error(f'keyword "{state}" not found. '
                                       f'Options are: {self.__names_of_states[hardware_index][switch_index]}')
                        return -3
                self._switch(hardware_index).set_state(switch_index, state)
                self.sig_switch_updated.emit(self.states)

    def get_state(self, hardware_index, switch_index):
        if isinstance(hardware_index, str):
            try:
                hardware_index = self.__names_of_hardware.index(hardware_index.lower().replace(' ', '_'))
            except ValueError:
                self.log.error(f'keyword "{hardware_index}" not found. Options are: {self.__names_of_hardware}')
                return -1
        if isinstance(switch_index, str):
            try:
                switch_index = self.__names_of_switches[hardware_index].index(
                    switch_index.lower().replace(' ', '_'))
            except ValueError:
                self.log.error(f'keyword "{switch_index}" not found. '
                               f'Options are: {self.__names_of_switches[hardware_index]}')
                return -2

        if 0 <= hardware_index < self.number_of_hardware \
                and 0 <= switch_index < self._switch(hardware_index).number_of_switches:
            return self._switch(hardware_index).get_state(switch_index)

        if not 0 <= hardware_index < self.number_of_hardware:
            self.log.error(f'The hardware_index was {hardware_index} '
                           f'but needs to be in the range from 0 to {self.number_of_hardware - 1}.')
        elif not 0 <= switch_index < self._switch(hardware_index).number_of_switches:
            self.log.error(f'The switch_index of the hardware {self._switch(hardware_index).name} was {switch_index} '
                           f'but needs to be in the range from 0 to '
                           f'{self._switch(hardware_index).number_of_switches - 1}.')
        else:
            self.log.error('Error in get_state.')
        return False

    def _build_magic(self):
        self._magic_commands = dict()
        self.__names_of_hardware = [name.lower().replace(' ', '_') for name in self.names_of_hardware]
        for hw_index, hardware in enumerate(self.__names_of_hardware):
            if self.__names_of_hardware.count(hardware) > 1:
                self.log.warning(f'Hardware hardware "{hardware}" not unambiguous, adding numbers to the hardware.')
                occurences = [i for i, x in enumerate(self.__names_of_hardware) if x == hardware]
                for i, position in enumerate(occurences):
                    self.__names_of_hardware[position] = hardware + str(i + 1)

        self.__names_of_states = [[[name.lower().replace(' ', '_') for name in switch]
                                   for switch in hardware]
                                  for hardware in self.names_of_states]
        flat_states = list()
        self.__names_of_switches = [[name.lower().replace(' ', '_') for name in hardware]
                                    for hardware in self.names_of_switches]
        flat_switches = list()
        for hw_index, hardware in enumerate(self.__names_of_switches):
            for sw_index, switch in enumerate(hardware):
                if hardware.count(switch) > 1:
                    self.log.warning(f'Switch name "{switch}" not unambiguous '
                                     f'for hardware "{self.__names_of_hardware[hw_index]}", '
                                     f'adding numbers to the switch.')
                    occurences = [i for i, x in enumerate(hardware) if x == switch]
                    for i, position in enumerate(occurences):
                        hardware[position] = switch + str(i + 1)

                if self.__names_of_states[hw_index][sw_index][0] == self.__names_of_states[hw_index][sw_index][1]:
                    self.log.warning(f'State name "{self.__names_of_states[hw_index][sw_index][0]}" '
                                     f'of switch "{self.__names_of_switches[hw_index][sw_index]}" '
                                     f'in "{self.__names_of_hardware[hw_index]}" is not unambiguous '
                                     f'using "down" and "up" instead.')
                    self.__names_of_states[hw_index][sw_index][0] = 'down'
                    self.__names_of_states[hw_index][sw_index][1] = 'up'

                flat_switches.extend(
                    [self.__names_of_switches[hw_index][sw_index] + '.' + self.__names_of_states[hw_index][sw_index][0],
                     self.__names_of_switches[hw_index][sw_index] + '.' + self.__names_of_states[hw_index][sw_index][
                         1]])
                flat_states.extend(
                    [self.__names_of_states[hw_index][sw_index][0], self.__names_of_states[hw_index][sw_index][1]])

        for hw_index, hardware in enumerate(self.__names_of_switches):
            for sw_index, switch in enumerate(hardware):
                if flat_states.count(self.__names_of_states[hw_index][sw_index][0]) == 1:
                    self._magic_commands[self.__names_of_states[hw_index][sw_index][0]] = [hw_index, sw_index, False]
                if flat_states.count(self.__names_of_states[hw_index][sw_index][1]) == 1:
                    self._magic_commands[self.__names_of_states[hw_index][sw_index][1]] = [hw_index, sw_index, True]

                down = self.__names_of_switches[hw_index][sw_index] + '.' \
                       + self.__names_of_states[hw_index][sw_index][0]
                if flat_switches.count(down) == 1:
                    self._magic_commands[down] = [hw_index, sw_index, False]
                up = self.__names_of_switches[hw_index][sw_index] + '.' + self.__names_of_states[hw_index][sw_index][1]
                if flat_switches.count(up) == 1:
                    self._magic_commands[up] = [hw_index, sw_index, True]

                self._magic_commands[self.__names_of_hardware[hw_index] + '.'
                                     + self.__names_of_switches[hw_index][sw_index] + '.'
                                     + self.__names_of_states[hw_index][sw_index][0]] = [hw_index, sw_index, False]

                self._magic_commands[self.__names_of_hardware[hw_index] + '.'
                                     + self.__names_of_switches[hw_index][sw_index] + '.'
                                     + self.__names_of_states[hw_index][sw_index][1]] = [hw_index, sw_index, True]

        self.log.info(f'The following switch magic commands are available: {list(self._magic_commands)}')

    def magic(self, command):
        command = str(command).lower().replace(' ', '_')
        if command in self._magic_commands:
            self.set_state(self._magic_commands[command][0],
                           self._magic_commands[command][1],
                           self._magic_commands[command][2])
        else:
            self.log.error(f'Your command "{command}" was not among the magic commands: {list(self._magic_commands)}')
