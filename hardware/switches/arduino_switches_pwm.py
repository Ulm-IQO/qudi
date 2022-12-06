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
from core.util.mutex import RecursiveMutex

import time
import visa
import numpy as np

class ArduinoSwitch(Base, SwitchInterface):
    """ Methods to control slow switching devices.

    Example config for copy-paste:

    arduino_switch:
        module.Class: 'switches.arduino_switches_pwm.ArduinoSwitch'
        name: 'Arduino'  # optional
        remember_states: True  # optional
        interface: 'ASRL4::INSTR'
        baudrate: 9600
        outputport: [1, 2, 3, 17, 18, 4]
        switches:
            camera: ['in', 'out']
            fiber: ['SM', 'MM']
            detection: ['open', 'closed']
            confocal: ['open', 'closed']
            green: ['open', 'closed']
            powermeter: ['in', 'out']
    """

    # ConfigOptions
    # customize available switches in config. Each switch needs a tuple of at least 2 state names.
    _switches = ConfigOption(name='switches', missing='error')
    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='ArduinoSwitches', missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=True, missing='nothing')
    _serial_interface = ConfigOption('interface', missing='error')
    _serial_baudrate = ConfigOption(name='baudrate', default=9600, missing='nothing')
    _output_port = ConfigOption(name='outputport', missing='error')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)
    _ontimes = StatusVar(name='ontimes', default=np.ones(32)*800)
    _offtimes = StatusVar(name='offtimes', default=np.ones(32)*2200)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resource_manager = None
        self._instrument = None
        self._lock = RecursiveMutex()

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        self._switches = self._chk_refine_available_switches(self._switches)

        # reset states if requested, otherwise use the saved states
        if self._remember_states and isinstance(self._states, dict) and \
                set(self._states) == set(self._switches):
            self._states = {switch: self._states[switch] for switch in self._switches}
        else:
            self._states = {switch: states[0] for switch, states in self._switches.items()}

        try:
            self._resource_manager = visa.ResourceManager()
            self._instrument = self._resource_manager.open_resource(
                self._serial_interface,
                baud_rate=self._serial_baudrate,
                write_termination='\n',
                read_termination='\r\n',
                timeout=5000
            )
            time.sleep(1)
        except visa.VisaIOError as e:
            self.log.exception("PID Controller nicht connected")


    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        self._instrument.close()
        self._resource_manager.close()
        time.sleep(1)
        # del self._instrument, self._resource_manager

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
        # with self._lock:
        with self._lock:
            new_state = self.serial_read(command='state?')
            self._states = dict()
            for channel_index, (switch, valid_states) in enumerate(self.available_states.items()):
                if int(new_state[self._output_port[channel_index]-1]) == 1:
                    self._states[switch] = valid_states[1]
                else:
                    self._states[switch] = valid_states[0]
        return self._states

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

        new_states = self.states.copy()
        new_states.update(state_dict)
        command = self.convert_state(new_states)
        # apply changes in hardware
        self.serial_write('setstate'+command)
        # Check for success
        assert self.states == new_states, 'Setting of channel states failed'

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
        self.states = {switch: state}



    def convert_state(self, new_states):
        """


        :return:
        """
        return str(sum(self._switches[key].index(new_states[key])*10**(32-self._output_port[i]) for i, key in enumerate(self._switches))).zfill(32)

    def serial_read(self, command):
        try:
            response = self._instrument.query(command).strip()
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError, trying again...')
            self._resource_manager = visa.ResourceManager()
            self._instrument.close()
            self._resource_manager.close()
            time.sleep(1)
            try:
                self._resource_manager = visa.ResourceManager()
                self._instrument = self._resource_manager.open_resource(
                    self._serial_interface,
                    baud_rate=self._serial_baudrate,
                    write_termination='\n',
                    read_termination='\r\n',
                    timeout=5000
                )
                time.sleep(1)
            except visa.VisaIOError as e:
                self.log.exception("PID Controller nicht connected")
        else:
            return response
        raise Exception('Hardware did not respond after 3 attempts. Visa error')

    def serial_write(self, command):
        try:
            self._instrument.write(command)
            time.sleep(0.1)
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError')
            self._resource_manager = visa.ResourceManager()
            self._instrument.close()
            self._resource_manager.close()
            time.sleep(1)
            try:
                self._resource_manager = visa.ResourceManager()
                self._instrument = self._resource_manager.open_resource(
                    self._serial_interface,
                    baud_rate=self._serial_baudrate,
                    write_termination='\n',
                    read_termination='\r\n',
                    timeout=5000
                )
                time.sleep(1)
            except visa.VisaIOError as e:
                self.log.exception("PID Controller nicht connected")


    def set_on_time(self,channel,time):
        self._ontimes[channel-1] = time
        command = "setontime"
        for i, a in enumerate(self._ontimes):
            command = command + str(int(a)).zfill(4)
        print(command)
        self.serial_write(command)

    def set_off_time(self,channel, time):
        self._offtimes[channel-1] = time
        command = "setofftime"
        for i, a in enumerate(self._offtimes):
            command = command + str(int(a)).zfill(4)
        print(command)
        self.serial_write(command)


