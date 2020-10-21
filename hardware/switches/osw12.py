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


class HBridge(Base, SwitchInterface):
    """ This class is implements communication with Thorlabs OSW12(22) fibered switch

    Example config for copy-paste:

    fibered_switch:
        module.Class: 'switches.osw12.Main'
        interface: 'ASRL1::INSTR'
        names_of_states: ['Off', 'On']
        names_of_switches: ['Detection']
        name: 'MEMS Fibre Switch'

    Description of the hardware provided by Thorlabs:
        Thorlabs offers a line of bidirectional fiber optic switch kits that include a MEMS optical switch with an
         integrated control circuit that offers a USB 2.0 interface for easy integration into your optical system.
          Choose from 1x2 or 2x2 MEMS modules with any of the following operating wavelengths:
        480 - 650 nm, 600 - 800 nm, 750 - 950 nm, 800 - 1000 nm, 970 - 1170 nm, or 1280 - 1625 nm.
        These bidirectional switches have low insertion loss and excellent repeatability.
    """

    _names_of_states = ConfigOption(name='names_of_states', default=['Down', 'Up'], missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _reset_states = ConfigOption(name='reset_states', default=False, missing='nothing')
    _switch_time = ConfigOption(name='switch_time', default=1e-3, missing='nothing')

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

        # initialize channels to saved status if requested
        if self._reset_states:
            self.states = False

        if self._states is None or len(self._states) != self.number_of_switches:
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
        return [self.get_state()]

    @states.setter
    def states(self, value):
        if np.isscalar(value):
            self.set_state(index_of_switch=None, state=value)
        else:
            self.set_state(index_of_switch=None, state=value[0])

    @property
    def names_of_states(self):
        return self._names_of_states.copy()

    @property
    def names_of_switches(self):
        return self._names_of_switches.copy()

    @property
    def number_of_switches(self):
        return 1

    def get_state(self, index_of_switch=None):
        with self.lock:
            state = self._instrument.query('S?\n').strip()
            if state == '1':
                self._states[0] = True
            elif state == '2':
                self._states[0] = False
            else:
                self.log.error(f'Hardware returned {state} as switch state.')
            return self._states[0]

    def set_state(self, index_of_switch=None, state=False):
        with self.lock:
            self._inst.write('S {0:d}'.format(1 if state else 2))
        return self.get_state(index_of_switch)
