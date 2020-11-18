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
    """ This class is implements communication with the Radiant Dyes flip mirror driver
        through pyVISA.

    Example config for copy-paste:

    flipmirror_switch:
        module.Class: 'switches.flipmirror.FlipMirror'
        interface: 'ASRL1::INSTR'
        names_of_states: ['Spectrometer', 'APD']
        names_of_switches: ['Detection']
        name: 'Flipmirror'

    """

    # names_of_switches defines what switches there are, it should be a list of strings
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')

    # names_of_states defines states for each switch, it can define any number of states greater one per switch.
    # A 2D list of lists defined specific states for each switch
    # and a simple 1D list defines the same states for each of the switches.
    _names_of_states = ConfigOption(name='names_of_states', default=['Down', 'Up'], missing='nothing')

    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='Flipmirror Switch', missing='nothing')

    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=False, missing='nothing')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    # switch_time to wait after setting the states for the solenoids to react
    _switch_time = ConfigOption(name='switch_time', default=2.0, missing='nothing')

    # name of the serial interface were the hardware is connected.
    # E.g. use the Keysight IO connections expert to find the device.
    serial_interface = ConfigOption('interface', 'ASRL1::INSTR', missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = RecursiveMutex()
        self._resource_manager = None
        self._instrument = None

    def on_activate(self):
        """ Prepare module, connect to hardware.
        """
        self._resource_manager = visa.ResourceManager()
        self._instrument = self._resource_manager.open_resource(
            self.serial_interface,
            baud_rate=115200,
            write_termination='\r\n',
            read_termination='\r\n',
            timeout=10,
            send_end=True
        )

        if isinstance(self._names_of_switches, str):
            self._names_of_switches = [str(self._names_of_switches)]
        else:
            try:
                self._names_of_switches = [str(self._names_of_switches[0])]
            except TypeError:
                self._names_of_switches = ['1']

        if isinstance(self._names_of_states, (list, tuple)) \
                and len(self._names_of_states) == len(self._names_of_switches) \
                and isinstance(self._names_of_states[0], (list, tuple)) \
                and len(self._names_of_states[0]) > 1:
            self._names_of_states = {switch: [str(name) for name in self._names_of_states[index]]
                                     for index, switch in enumerate(self._names_of_switches)}
        else:
            self.log.error(f'names_of_states must be a list of length {len(self._names_of_switches)}, '
                           f'with the elements being a list of two or more names for the states.')
            self._names_of_states = dict()
            return

        # reset states if requested, otherwise use the saved states
        if not self._remember_states \
                or not isinstance(self._states, dict) \
                or len(self._states) != self.number_of_switches:
            self._states = {name: self._names_of_states[name][0] for name in self._names_of_switches}

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
        return self._names_of_states.copy()

    @property
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        with self.lock:
            response = self._instrument.ask('GP1').strip().upper()
            assert response in {'H1', 'V1'}, f'Unexpected hardware return value: "{response}"'
            switch, avail_states = next(iter(self.available_states.items()))
            self._states = {switch: avail_states[int(response == 'V1')]}
            return

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        assert isinstance(state_dict,
                          dict), f'Property "state" must be dict type. Received: {type(state_dict)}'
        assert all(switch in self.available_states for switch in
                   state_dict), f'Invalid switch name(s) encountered: {tuple(state_dict)}'
        assert all(isinstance(state, str) for state in
                   state_dict.values()), f'Invalid switch state(s) encountered: {tuple(state_dict.values())}'

        if state_dict:
            with self.lock:
                switch, state = next(iter(state_dict.items()))
                down = self.available_states[switch][0] == state
                answer = self._instrument.ask('SH1' if down else 'SV1')
                assert answer == 'OK1', f'setting of state "{state}" in switch "{switch}" failed with return value "{answer}"'
                self._states = {switch: state}
                time.sleep(self._switch_time)
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
