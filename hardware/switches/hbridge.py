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


class HBridge(Base, SwitchInterface):
    """ Methods to control slow laser switching devices.

    Example config for copy-paste:

    h_bridge_switch:
        module.Class: 'switches.hbridge.HBridge'
        interface: 'ASRL1::INSTR'
        name: 'HBridge Switch'  # optional
        switch_time: 0.5  # optional
        remember_states: False  # optional
        switches:               # optional
            One: ['Spectrometer', 'APD']
            Two: ['Spectrometer', 'APD']
            Three: ['Spectrometer', 'APD']
            Four: ['Spectrometer', 'APD']
    """

    # ConfigOptions

    # customize all 4 available switches in config. Each switch needs a tuple of 2 state names.
    _switches = ConfigOption(name='switches',
                             default={str(ii): ('Off', 'On') for ii in range(1, 5)},
                             missing='nothing')
    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='HBridge Switch', missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=False, missing='nothing')
    # switch_time to wait after setting the states for the solenoids to react
    _switch_time = ConfigOption(name='switch_time', default=0.5, missing='nothing')
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

    def on_activate(self):
        """ Prepare module, connect to hardware.
        """
        self._switches = self._chk_refine_available_switches(self._switches)

        self._resource_manager = visa.ResourceManager()
        self._instrument = self._resource_manager.open_resource(
            self.serial_interface,
            baud_rate=9600,
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
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        with self.lock:
            binary = tuple(int(pos == '1') for pos in self.inst.ask('STATUS').strip().split())
            avail_states = self.available_states
            self._states = {switch: states[binary[index]] for index, (switch, states) in
                            enumerate(avail_states.items())}
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

        if state_dict:
            with self.lock:
                for switch, state in state_dict.items():
                    self.set_state(switch, state)

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, 'Invalid switch name "{0}"'.format(switch)
        return self.states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        avail_states = self.available_states
        assert switch in avail_states, f'Invalid switch name: "{switch}"'
        assert state in avail_states[switch], f'Invalid state name "{state}" for switch "{switch}"'

        with self.lock:
            switch_index = self.switch_names.index(switch) + 1
            state_index = avail_states[switch].index(state) + 1
            cmd = 'P{0:d}={1:d}'.format(switch_index, state_index)
            answer = self._instrument.ask(cmd)
            assert answer == cmd, \
                f'setting of state "{state}" in switch "{switch}" failed with return value "{answer}"'
            time.sleep(self._switch_time)

    @staticmethod
    def _chk_refine_available_switches(switch_dict):
        """ See SwitchInterface class for details

        @param dict switch_dict:
        @return dict:
        """
        refined = super()._chk_refine_available_switches(switch_dict)
        assert len(refined) == 4, 'Exactly 4 switches or None must be specified in config'
        assert all(len(s) == 2 for s in refined.values()), 'Switches can only take exactly 2 states'
        return refined
