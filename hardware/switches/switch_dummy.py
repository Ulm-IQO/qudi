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


class SwitchDummy(Base, SwitchInterface):
    """ Methods to control slow switching devices.

    Example config for copy-paste:

    switch_dummy:
        module.Class: 'switches.switch_dummy.SwitchDummy'
        name: 'First'  # optional
        remember_states: True  # optional
        switches:
            one: ['down', 'up']
            two: ['down', 'up']
            three: ['low', 'middle', 'high']
    """

    # ConfigOptions
    # customize available switches in config. Each switch needs a tuple of at least 2 state names.
    _switches = ConfigOption(name='switches', missing='error')
    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=True, missing='nothing')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        self._switches = self._chk_refine_available_switches(self._switches)

        # Choose config name for this module if no name is given in ConfigOptions
        if self._hardware_name is None:
            self._hardware_name = self._name

        # reset states if requested, otherwise use the saved states
        if self._remember_states and isinstance(self._states, dict) and \
                set(self._states) == set(self._switches):
            self._states = {switch: self._states[switch] for switch in self._switches}
        else:
            self._states = {switch: states[0] for switch, states in self._switches.items()}

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        pass

    @property
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        return self._switches.copy()

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, f'Invalid switch name: "{switch}"'
        return self._states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        avail_states = self.available_states
        assert switch in avail_states, f'Invalid switch name: "{switch}"'
        assert state in avail_states[switch], f'Invalid state name "{state}" for switch "{switch}"'
        self._states[switch] = state
