# -*- coding: utf-8 -*-
"""
Interact with switches.

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
from core.configoption import ConfigOption
from qtpy import QtCore
import numpy as np
from interface.switch_interface import SwitchInterface


class SwitchLogic(GenericLogic, SwitchInterface):
    """ Logic module for interacting with the hardware switches.
    This logic has the same structure as the SwitchInterface but supplies additional functionality:
        - switches can either be manipulated by index or by their names
        - signals are generated on state changes
    """

    # connector for one switch, if multiple switches are needed use the SwitchCombinerInterfuse
    switch = Connector(interface='SwitchInterface')

    _watchdog_timing = ConfigOption(name='watchdog_timing', default=1.0, missing='nothing')

    sig_switch_updated = QtCore.Signal(dict)
    _sig_start_watchdog = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_states = dict()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._sig_start_watchdog.connect(self._watchdog, QtCore.Qt.QueuedConnection)
        self._sig_start_watchdog.emit()

    def on_deactivate(self):
        """ Deactivate module.
        """
        self._sig_start_watchdog.disconnect(self._watchdog)

    def _watchdog(self):
        if self._old_states != self.states:
            self._old_states = self.states
            self.sig_switch_updated.emit(self._old_states)
        QtCore.QTimer.singleShot(int(self._watchdog_timing * 1e3), self._watchdog)

    @property
    def name(self):
        """
        Name of the hardware module.
            @return str: The name of the hardware
        """
        return self.switch().name

    @property
    def names_of_states(self):
        """
        Names of the states as a list of lists. The first list contains the names for each of the switches
        and each of switches has two elements representing the names in the state order [False, True].
            @return list(list(str)): 2 dimensional list of names in the state order [False, True]
        """
        return self.switch().names_of_states

    @property
    def number_of_switches(self):
        """
        Number of switches provided by this hardware.
            @return int: number of switches
        """
        return self.switch().number_of_switches

    @property
    def states(self):
        """
        The states of the system as a list of boolean values.
            @return list(bool): All the current states of the switches in a list
        """
        return self.switch().states

    @states.setter
    def states(self, value):
        """
        The states of the system can be set in two ways:
        Either as a single value to define all the states to be the same
        or as a list of values to define the state of each switch individually.
        The values of the state can either be boolean or a string representing the name of the state.
        Names are automatically converted to booleans by a helper function if the names of the states are unambiguous.
            @param [bool/list(bool)/str/list(str)] value: switch state to be set as single value or list of values,
                the values can either be boolean or a strign representing the name of the boolean state
            @return: None
        """
        self.switch().states = value
        self.sig_switch_updated.emit(self.states)
