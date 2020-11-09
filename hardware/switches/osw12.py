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
        names_of_switches: ['Detection']
        name: 'MEMS Fibre Switch'
    """

    # names_of_switches defines what switches there are, it should be a list of strings
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')

    # names_of_states defines states for each switch, it can define any number of states greater one per switch.
    # A 2D list of lists defined specific states for each switch
    # and a simple 1D list defines the same states for each of the switches.
    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')

    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')

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

        if self._hardware_name is None:
            self._hardware_name = 'MEMS Fiber-Optic Switch'

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

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        self._instrument.close()
        self._resource_manager.close()

    @property
    def number_of_switches(self):
        """ The number of switches provided by this hardware is 1.

        @return int: number of switches
        """
        return 1

    @property
    def name(self):
        """ Name of the hardware as string.

        The name can either be defined as ConfigOption (name) or it defaults to the name of the hardware module.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def names_of_states(self):
        """ Names of the states as a dict of lists.

        The keys contain the names for each of the switches and each of switches
        has a list of elements representing the names in the state order.
        The names can be defined by a ConfigOption (names_of_states) or they default to ['Off', 'On'].

        @return dict: A dict of the form {"switch": ["state1", "state2"]}
        """
        return self._names_of_states.copy()

    @property
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        for attempt in range(3):
            try:
                with self.lock:
                    response = self._instrument.query('S?').strip()
                if response not in ['1', '2']:
                    self.log.error('Hardware returned {} as switch state.'.format(response))
                return {name: self._names_of_states[name][int(response == '1')] for name in self._names_of_switches}
            except visa.VisaIOError:
                self.log.debug('Hardware returned with Visa error, trying again.')

        self.log.error('Hardware did not respond after 3 attempts. Visa error')
        return {name: self._names_of_states[name][0] for name in self._names_of_switches}

    @states.setter
    def states(self, value):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict value: state dict of the form {"switch": "state"}
        @return: None
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

        if direction:
            self.log.error('No state to set.')
            return

        with self.lock:
            self._instrument.write('S {0:d}'.format(1 if direction else 2))
            time.sleep(0.1)

        # For some reason first returned value is not updated yet, let's clear it.
        _ = self.states
