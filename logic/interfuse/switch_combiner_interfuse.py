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

    def on_activate(self):
        if self._hardware_name is None:
            self._hardware_name = self._name

    def on_deactivate(self):
        pass

    @property
    def name(self):
        return self._hardware_name

    @property
    def states(self):
        return list(self.switch1().states) + list(self.switch2().states)

    @states.setter
    def states(self, value):
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
        return list(self.switch1().names_of_states) + list(self.switch2().names_of_states)

    @property
    def number_of_switches(self):
        return self.switch1().number_of_switches + self.switch2().number_of_switches

    @property
    def names_of_switches(self):
        return list(self.switch1().names_of_switches) + list(self.switch2().names_of_switches)

    def get_state(self, number_of_switch):
        if number_of_switch < self.switch1().number_of_switches:
            return self.switch1().get_state(number_of_switch)
        else:
            return self.switch2().get_state(number_of_switch - self.switch1().number_of_switches)

    def set_state(self, number_of_switch, state):
        if number_of_switch < self.switch1().number_of_switches:
            return self.switch1().set_state(number_of_switch, state)
        else:
            return self.switch2().set_state(number_of_switch - self.switch1().number_of_switches, state)
