# -*- coding: utf-8 -*-
"""
Control the Radiant Dyes flip mirror driver through the serial interface.

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

import visa
import time
from core.module import Base
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.util.mutex import RecursiveMutex
from interface.switch_interface import SwitchInterface


class FlipMirror(Base, SwitchInterface):
    """ This class is implements communication with the Radiant Dyes flip mirror driver using pyVISA

    Example config for copy-paste:

    flipmirror_switch:
        module.Class: 'switches.flipmirror.FlipMirror'
        interface: 'ASRL1::INSTR'
        name: 'Flipmirror Switch'  # optional
        switch_time: 2  # optional
        remember_states: False  # optional
        switch_name: 'Detection'  # optional
        switch_states: ['Spectrometer', 'APD']  # optional
    """

    # ConfigOptions to give the single switch and its states custom names
    _switch_name = ConfigOption(name='switch_name', default='1', missing='nothing')
    _switch_states = ConfigOption(name='switch_states', default=['Down', 'Up'], missing='nothing')
    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='Flipmirror Switch', missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=False, missing='nothing')
    # switch_time to wait after setting the states for the solenoids to react
    _switch_time = ConfigOption(name='switch_time', default=2.0, missing='nothing')
    # name of the serial interface where the hardware is connected.
    # Use e.g. the Keysight IO connections expert to find the device.
    serial_interface = ConfigOption('interface', 'ASRL1::INSTR', missing='error')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = RecursiveMutex()
        self._resource_manager = None
        self._instrument = None
        self._switches = dict()

    def on_activate(self):
        """ Prepare module, connect to hardware.
        """
        assert isinstance(self._switch_name, str), 'ConfigOption "switch_name" must be str type'
        assert len(self._switch_states) == 2, 'ConfigOption "switch_states" must be len 2 iterable'
        self._switches = self._chk_refine_available_switches(
            {self._switch_name: self._switch_states}
        )

        self._resource_manager = visa.ResourceManager()
        self._instrument = self._resource_manager.open_resource(
            self.serial_interface,
            baud_rate=115200,
            write_termination='\r\n',
            read_termination='\r\n',
            timeout=10,
            send_end=True
        )

        # reset states if requested, otherwise use the saved states
        if self._remember_states and isinstance(self._states, dict) and \
                set(self._states) == set(self._switches):
            self._states = {switch: self._states[switch] for switch in self._switches}
            self.states = self._states
        else:
            self._states = dict()
            self.states = {switch: states[0] for switch, states in self._switches.items()}

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        self._instrument.close()
        self._resource_manager.close()

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

    @property
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        with self.lock:
            response = self._instrument.query('GP1').strip().upper()
            assert response in {'H1', 'V1'}, f'Unexpected hardware return value: "{response}"'
            switch, avail_states = next(iter(self.available_states.items()))
            self._states = {switch: avail_states[int(response == 'V1')]}
            return self._states.copy()

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        assert isinstance(state_dict, dict), \
            f'Property "state" must be dict type. Received: {type(state_dict)}'
        assert all(switch in self.available_states for switch in state_dict), \
            f'Invalid switch name(s) encountered: {tuple(state_dict)}'
        assert all(isinstance(state, str) for state in state_dict.values()), \
            f'Invalid switch state(s) encountered: {tuple(state_dict.values())}'

        if state_dict:
            with self.lock:
                switch, state = next(iter(state_dict.items()))
                down = self.available_states[switch][0] == state
                answer = self._instrument.query('SH1' if down else 'SV1', delay=self._switch_time)
                assert answer == 'OK1', \
                    f'setting of state "{state}" in switch "{switch}" failed with return value "{answer}"'
                self._states = {switch: state}
                self.log.debug('{0}-{1}: {2}'.format(self.name, switch, state))

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, f'Invalid switch name: "{switch}"'
        return self.states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        self.states = {switch: state}
