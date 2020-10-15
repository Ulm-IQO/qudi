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
from qtpy import QtWidgets, QtGui, QtCore


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
    def states(self):
        return [switch().states for switch in self._hw_switches]

    def set_state(self, hardware_index, switch_index, state):
        self._hw_switches[hardware_index]().set_state(switch_index, state)
        self.sig_switch_updated.emit(self.states)
