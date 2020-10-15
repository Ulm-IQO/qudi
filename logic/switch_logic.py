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

    def on_activate(self):
        """ Prepare logic module for work.
        """
        if self.switch.is_connected:
            self._hw_switches.append(self.switch)

        for i in range(10):
            if getattr(self, f'switch{i:d}').is_connected:
                self._hw_switches.append(getattr(self, f'switch{i:d}'))

    def on_deactivate(self):
        """ Deactivate modeule.
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
        print(np.shape(value))
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
            self.states = state
        else:
            if switch_index is None:
                self._switch(hardware_index).states = state
                self.sig_switch_updated.emit(self.states)
            else:
                self._switch(hardware_index).set_state(switch_index, state)
                self.sig_switch_updated.emit(self.states)

    def get_state(self, hardware_index, switch_index):
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
