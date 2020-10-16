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
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface
import numpy as np


class HBridge(Base, SwitchInterface):
    """ Methods to control slow laser switching devices.

    Example config for copy-paste:

    h_bridge_switch:
        module.Class: 'switches.hbrindge.HBridge'
        interface: 'ASRL1::INSTR'
        names_of_states: ['Spectrometer', 'APD']
        names_of_switches: ['Detection']
        name: 'HBridge'

    """

    _names_of_states = ConfigOption(name='names_of_states', default=['Down', 'Up'], missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _reset_states = ConfigOption(name='reset_states', default=False, missing='nothing')
    _switch_time = ConfigOption(name='switch_time', default=0.5, missing='warn')

    _states = StatusVar(name='states', default=None)

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
            baud_rate=9600,
            write_termination='\r\n',
            read_termination='\r\n',
            timeout=10,
            send_end=True
        )

        if self._hardware_name is None:
            self._hardware_name = 'HBridge Switch'

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
        else:
            self._names_of_switches = [str(index + 1) for index in range(self.number_of_switches)]

        # initialize channels to saved status if requested
        if self._reset_states:
            self.states = False

        if self.states is None or len(self.states) != self.number_of_switches:
            self.states = [False] * self.number_of_switches
        else:
            self.states = self._states

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        self._instrument.close()
        self._resource_manager.close()

    @property
    def name(self):
        return self._hardware_name

    @property
    def states(self):
        with self.lock:
            pos = self.inst.ask('STATUS')
            self._states = [bool(i) for i in pos.split()]
        return self._states

    @states.setter
    def states(self, value):
        if np.isscalar(value):
            self._states = [bool(value)] * self.number_of_switches
        else:
            if len(value) != self.number_of_switches:
                self.log.error(f'The states either have to be a scalar or a list af length {self.number_of_switches}')
            else:
                self._states = list(value)

        with self.lock:
            for index in range(self.number_of_switches):
                answer = self._instrument.ask('P{0:d}={1:d}'.format(int(index) + 1, int(bool(self._states[index]))))
                if answer != 'P{0:d}={1:d}'.format(int(index) + 1, int(bool(self._states[index]))):
                    self.log.error(f'Error in setting state. Answer was: {answer}')
                    return

            time.sleep(self._switch_time)

    @property
    def names_of_states(self):
        return self._names_of_states.copy()

    @property
    def names_of_switches(self):
        return self._names_of_switches.copy()

    @property
    def number_of_switches(self):
        return 4

    def get_state(self, index_of_switch):
        if 0 <= index_of_switch < self.number_of_switches:
            return self.states[int(index_of_switch)]
        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return False

    def set_state(self, index_of_switch=None, state=False):
        if 0 <= index_of_switch < self.number_of_switches:
            with self.lock:
                answer = self._instrument.ask('P{0:d}={1:d}'.format(int(index_of_switch) + 1, int(bool(state))))
                if answer != 'P{0:d}={1:d}'.format(int(index_of_switch) + 1, int(bool(state))):
                    self.log.error(f'Error in setting state. Answer was: {answer}')
                    return self.get_state(index_of_switch)

                time.sleep(self._switch_time)
                self.log.info('{0}: {1}'.format(self.name, self.names_of_states[int(bool(state))]))
                return self.get_state(index_of_switch)

        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return -1
