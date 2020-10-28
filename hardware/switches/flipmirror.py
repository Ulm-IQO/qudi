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
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')

    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=True, missing='nothing')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    # switch_time to wait after setting the states for the solenoids to react
    _switch_time = ConfigOption(name='switch_time', default=2.0, missing='nothing')

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
            write_termination='\r\n',
            read_termination='\r\n',
            timeout=10,
            send_end=True
        )

        if self._hardware_name is None:
            self._hardware_name = 'Flipmirror Switch'

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
        with self.lock:
            response = self._instrument.ask('GP1').strip()
            if response not in ['H1', 'V1']:
                self.log.error('Hardware returned {} as switch state.'.format(response))
            return {name: self._names_of_states[name][int(response == 'V1')] for name in self._names_of_switches}

    @states.setter
    def states(self, value):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict value: state dict of the form {"switch": "state"}
        @return: None
        """
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
                    self._states[switch] = state
        else:
            self.log.error(f'attempting to set states as "{value}" while states have be a dict '
                           f'having the switch names as keys and the state names as values.')
            return

        with self.lock:
            switch = self._names_of_switches[0]
            state = self.names_of_states[self._names_of_switches[0]].index(self._states[switch])
            answer = self._instrument.ask('SV1' if state else 'SH1')
            if answer != 'OK1':
                self.log.error(f'Error in setting state. Answer was: {answer}')
                return

            time.sleep(self._switch_time)
            self.log.debug('{0}-{1}: {2}'.format(self.name, switch, self._states[switch]))

    def get_calibration(self, state):
        """ Get calibration parameter for switch.
        NOT part of the SwitchInterface!
        In this case, the calibration parameter is a integer number that says where the
        horizontal and vertical position of the flip mirror is in the 16 bit PWM range of the motor driver.
        The number is returned as a string, not as an int, and needs to be converted.
        @param bool state: for which to get calibration parameter
        @return int: calibration parameter for switch and state.
        """
        with self.lock:
            if state:
                answer = self._instrument.ask('GVT1')
            else:
                answer = self._instrument.ask('GHT1')
            return int(answer.split('=')[1])

    def set_calibration(self, state, value):
        """ Set calibration parameter for switch.
        NOT part of the SwitchInterface!
        @param bool state: for which to get calibration parameter
        @param int value: calibration parameter to be set.
        @return bool: True if success, False on error
        """
        with self.lock:
            answer = self._instrument.ask('S{0}T1 {1}'.format('V' if state else 'H', int(value)))
            if answer != 'OK1':
                return False
