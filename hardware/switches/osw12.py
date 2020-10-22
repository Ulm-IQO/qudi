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

    _names_of_states = ConfigOption(name='names_of_states', default=['Down', 'Up'], missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _switch_time = ConfigOption(name='switch_time', default=1e-3, missing='nothing')

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

        if np.shape(self._names_of_states) == (2,):
            self._names_of_states = [list(self._names_of_states)] * self.number_of_switches
        elif np.shape(self._names_of_states) == (self.number_of_switches, 2):
            self._names_of_states = list(self._names_of_states)
        else:
            self.log.error(f'names_of_states must either be a list of two names for the states [low, high] '
                           f'which are applied to all switched or it must be a list '
                           f'of length {self._number_of_switches} with elements of the aforementioned shape.')

        if np.shape(self._names_of_switches) == (self.number_of_switches,):
            self._names_of_switches = list(self._names_of_switches)
        elif isinstance(self._names_of_switches, str):
            self._names_of_switches = [self._names_of_switches]
        else:
            self._names_of_switches = [str(index + 1) for index in range(self.number_of_switches)]

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        self._instrument.close()
        self._resource_manager.close()

    @property
    def name(self):
        """
        Name can either be defined as ConfigOption (name) or it defaults to "MEMS Fiber-Optic Switch".
            @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def states(self):
        """
        The states of the system as a list of boolean values.
        This functions just calls the function self.get_state.
            @return list(bool): All the current states of the switches in a list
        """
        return [self.get_state()]

    @states.setter
    def states(self, value):
        """
        The states of the system can be set in two ways:
        Either as a single boolean value to define all the states to be the same
        or as a list of boolean values to define the state of each switch individually.
        This functions just calls the function self.set_state.
            @param [bool/list(bool)] value: switch state to be set as single boolean or list of booleans
            @return: None
        """
        if np.isscalar(value):
            self.set_state(state=value)
        else:
            self.set_state(state=value[0])

    @property
    def names_of_states(self):
        """
        Names of the states as a list of lists. The first list contains the names for each of the switches
        and each of switches has two elements representing the names in the state order [False, True].
        The names can be defined by a ConfigOption (names_of_states) or they default to ['Off', 'On'].
            @return list(list(str)): 2 dimensional list of names in the state order [False, True]
        """
        return self._names_of_states.copy()

    @property
    def names_of_switches(self):
        """
        Names of the switches as a list of length number_of_switches.
        These can either be set as ConfigOption (names_of_switches) or default to a simple range starting at 1.
            @return list(str): names of the switches
        """
        return self._names_of_switches.copy()

    @property
    def number_of_switches(self):
        """
        Number of switches provided by this hardware. Constant 1 for this hardware.
            @return int: number of switches
        """
        return 1

    def get_state(self, index_of_switch=None, attempt=0):
        """
        Returns the state of a specific switch which was specified by its switch index.
        As there is only 1 switch, the index_of_switch is ignored.
            @param int index_of_switch: index of the switch is ignored
            @return bool: boolean value of this specific switch
        """
        try:
            with self.lock:
                response = self._instrument.query('S?').strip()
            if response not in ['1', '2']:
                self.log.error('Hardware returned {} as switch state.'.format(response))
            state = response == '1'
        except visa.VisaIOError:
            if attempt >= 3:
                self.log.error('Hardware did not respond after 3 attempts. Visa error')
            else:
                state = self.get_state(attempt=attempt+1)
        return state

    def set_state(self, index_of_switch=None, state=False):
        """
        Sets the state of a specific switch which was specified by its switch index.
        After setting the output of the switches, a certain wait time is applied to wait for the hardware to react.
        The wait time can be set by the ConfigOption (switch_time).
            @param int index_of_switch: index of the switch is ignored
            @param bool state: boolean state of the switch to be set
            @return int: state of the switch actually set
        """
        with self.lock:
            self._instrument.write('S {0:d}'.format(1 if state else 2))
            time.sleep(0.1)
        _ = self.get_state()  # For some reason first returned value is not updated yet, let's clear it.
