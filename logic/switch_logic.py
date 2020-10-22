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

    sig_switch_updated = QtCore.Signal(list)
    _sig_start_watchdog = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_states = list()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._ensure_unambiguous_names()
        self._sig_start_watchdog.connect(self._watchdog, QtCore.Qt.QueuedConnection)
        self._sig_start_watchdog.emit()

    def _ensure_unambiguous_names(self):
        """
        Helper function called at the module start for checking unambiguity of switch and state names.
        A warning is thrown if names are ambiguous and in this case unambiguous names are creates
        by appending numbers to the ambiguous names.
            @return: None
        """
        self.__names_of_states = [[name.lower().replace(' ', '_') for name in switch]
                                  for switch in self.names_of_states]
        self.__names_of_switches = [name.lower().replace(' ', '_') for name in self.names_of_switches]

        for sw_index, switch in enumerate(self.__names_of_switches):
            if self.__names_of_switches.count(switch) > 1:
                self.log.warning(f'Switch name "{switch}" not unambiguous, adding numbers to the switch.')
                occurrences = [i for i, x in enumerate(self.__names_of_switches) if x == switch]
                for i, position in enumerate(occurrences):
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
        self._sig_start_watchdog.disconnect(self._watchdog)

    def _watchdog(self):
        temp_states = self.states
        if self._old_states != temp_states:
            self._old_states = temp_states
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
    def names_of_switches(self):
        """
        Names of the switches as a list of length number_of_switches.
            @return list(str): names of the switches
        """
        return self.switch().names_of_switches

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
        if np.isscalar(value):
            if isinstance(value, str):
                if all(x == self.__names_of_states[0] for x in self.__names_of_states):
                    state = self._get_state_value(index_of_switch=0, state=value)
                    if state is not None:
                        self.switch().states = state
                else:
                    self.log.error(f'The state names of the switches are not the same, '
                                   f'so the value of the switch state "{value}" cannot be determined.')
            else:
                self.switch().states = value
        elif np.shape(value) == (self.number_of_switches,):
            for switch_index in range(self.number_of_switches):
                value[switch_index] = self._get_state_value(index_of_switch=switch_index, state=value[switch_index])
            if None not in value:
                self.switch().states = value
        else:
            self.log.error(f'The shape of the states was {np.shape(value)} '
                           f'but needs to be ({self.number_of_switches}, ).')
        self.sig_switch_updated.emit(self.states)

    def set_state(self, index_of_switch, state):
        """
        Sets the state of a specific switch which was specified by its switch index.
        The index_of_switch can either be int or a string representing the name of the switch.
        The values of the state can either be boolean or a string representing the name of the state.
        Names are automatically converted to booleans by a helper function if the names of the states are unambiguous.
            @param [int/str] index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @param bool state: boolean state of the switch to be set
            @return int: state of the switch actually set
        """
        index_of_switch = self._get_switch_index(index_of_switch)
        state = self._get_state_value(index_of_switch=index_of_switch, state=state)
        if 0 <= index_of_switch < self.number_of_switches and state is not None:
            self.switch().set_state(index_of_switch, state)
            self.sig_switch_updated.emit(self.states)

    def get_state(self, index_of_switch):
        """
        Returns the state of a specific switch which was specified by its switch index.
        The index_of_switch can either be int or a string representing the name of the switch.
            @param [int/str] index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @return bool: boolean value of this specific switch
        """
        index_of_switch = self._get_switch_index(index_of_switch)
        if 0 <= index_of_switch < self.number_of_switches:
            return self.switch().get_state(index_of_switch)
        else:
            if index_of_switch > 0:
                self.log.error(f'The switch_index was {index_of_switch} '
                               f'but needs to be in the range from 0 to {self.number_of_switches - 1}.')
            return False

    def _get_switch_index(self, index_of_switch):
        """
        Helper function to convert a name of a switch into its index.
        If an index is already given it is just returned.
        The function uses the unambiguous switch names created at activation.
            @param [int/str] index_of_switch: index or name of the switch
            @return int: index of the switch
        """
        if isinstance(index_of_switch, (int, float)):
            return int(index_of_switch)
        elif isinstance(index_of_switch, str):
            switch_name = index_of_switch.lower().replace(' ', '_')
            if switch_name in self.__names_of_switches:
                return self.__names_of_switches.index(switch_name)
            self.log.error(f'switch "{index_of_switch}" not found, options are {self.__names_of_switches}.')
            return -1
        self.log.error(f'The index_of_switch was "{index_of_switch}" but either has to be an '
                       f'int or the name of the switch as a string.')
        return -2

    def _get_state_value(self, index_of_switch, state):
        """
        Helper function to convert a name of a switch state into its boolean expression.
        If a boolean is already given it is just returned. None is returned in the error case.
        The function uses the unambiguous state names created at activation.
            @param int index_of_switch: index or name of the switch
            @param [bool/str] state: state or name of the state
            @return bool: state as boolean
        """
        if not isinstance(state, str):
            return bool(state)

        state = state.lower().replace(' ', '_')
        if 0 <= index_of_switch < self.number_of_switches:
            if state in self.__names_of_states[index_of_switch]:
                return bool(self.__names_of_states[index_of_switch].index(state))
            else:
                self.log.error(f'state name "{state}" not found for switch "{index_of_switch}", '
                               f'options are "{self.__names_of_states[index_of_switch]}".')
                return None
        else:
            self.log.error(f'The index_of_switch was {index_of_switch} '
                           f'but needs to be in the range from 0 to {self.number_of_switches - 1}.')
            return None
