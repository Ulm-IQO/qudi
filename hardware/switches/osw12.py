# -*- coding: utf-8 -*-
"""
Control for a Thorlabs OWS12 MEMS Fiber-Optic Switch through the serial interface.

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
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface
import numpy as np


class OSW12(Base, SwitchInterface):
    """ This class is implements communication with Thorlabs OSW12(22) fibered switch.

    Description of the hardware provided by Thorlabs:
        Thorlabs offers a line of bidirectional fiber optic switch kits that include a MEMS optical switch with an
        integrated control circuit that offers a USB 2.0 interface for easy integration into your optical system.
        Choose from 1x2 or 2x2 MEMS modules with any of the following operating wavelengths:
        480 - 650 nm, 600 - 800 nm, 750 - 950 nm, 800 - 1000 nm, 970 - 1170 nm, or 1280 - 1625 nm.
        These bidirectional switches have low insertion loss and excellent repeatability.

    Example config for copy-paste:

    fibered_switch:
        module.Class: 'switches.osw12.OSW12'
        interface: 'ASRL1::INSTR'
        names_of_states: ['Off', 'On']
        names_of_switches: 'Detection'
        name: 'MEMS Fibre Switch'
    """

    # names_of_switches defines what switches there are, it should be a list of strings
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')

    # names_of_states defines states for each switch, it can define any number of states greater one per switch.
    # A 2D list of lists defined specific states for each switch
    # and a simple 1D list defines the same states for each of the switches.
    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')

    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='MEMS Fiber-Optic Switch', missing='nothing')

    # name of the serial interface were the hardware is connected.
    # E.g. use the Keysight IO connections expert to find the device.
    serial_interface = ConfigOption('interface', 'ASRL1::INSTR', missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = Mutex()
        self._resource_manager = None
        self._instrument = None

    def on_activate(self):
        """ Prepare module, connect to hardware.
        """
        self._resource_manager = visa.ResourceManager()
        self._instrument = self._resource_manager.open_resource(
            self.serial_interface,
            baud_rate=115200,
            write_termination='\n',
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
        elif isinstance(self._names_of_states, (list, tuple)) \
                and isinstance(self._names_of_states[0], str):
            self._names_of_states = {self._names_of_switches[0]: list(self._names_of_states)}
        else:
            self.log.error(f'names_of_states must be a list of length {len(self._names_of_switches)}, '
                           f'with the elements being a list of two or more names for the states.')
            self._names_of_states = dict()
            return

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
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """


    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        direction = None
        if isinstance(value, dict):
            for switch, state in value.items():
                if switch not in self._names_of_switches:
                    self.log.warning(f'Attempted to set a switch of name "{switch}" but it does not exist.')
                    continue

                states = self.names_of_states[switch]
                if isinstance(state, str):
                    if state not in states:
                        self.log.error(f'"{state}" is not among the possible states: {states}')
                        continue
                    direction = self.names_of_states[switch].index(state)
        else:
            self.log.error(f'attempting to set states as "{value}" while states have be a dict '
                           f'having the switch names as keys and the state names as values.')
            return

        if direction is None:
            self.log.error('No state to set.')
            return

        with self.lock:
            self._instrument.write('S {0:d}'.format(1 if direction else 2))
            time.sleep(0.1)

        # For some reason first returned value is not updated yet, let's clear it.
        _ = self.states

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        avail_states = self.available_states
        assert switch in avail_states, 'Invalid switch name "{0}"'.format(switch)

        with self.lock:
            for attempt in range(3):
                try:
                    response = self._instrument.query('S?').strip()
                except visa.VisaIOError:
                    self.log.debug('Hardware query raised VisaIOError, trying again...')
                else:
                    assert response in {'1', '2'}, f'Unexpected return value "{response}"'
                    return {switch: avail_states[switch][int(response == '1')]}
            raise Exception('Hardware did not respond after 3 attempts. Visa error')

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
            assert answer == cmd, f'setting of state "{state}" in switch "{switch}" failed with return value "{answer}"'
            time.sleep(self._switch_time)
