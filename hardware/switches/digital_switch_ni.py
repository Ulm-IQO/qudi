# -*- coding: utf-8 -*-
"""
Control external hardware by the output of the digital channels of a NI card.

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

import time
import re
import nidaqmx
from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import RecursiveMutex
from interface.switch_interface import SwitchInterface

from core.statusvariable import StatusVar


class DigitalSwitchNI(Base, SwitchInterface):
    """ This class enables to control a switch via the NI card.
    Control external hardware by the output of the digital channels of a NI card.

    Example config for copy-paste:

    cw_laser_switch:
        module.Class: 'switches.digital_switch_ni.DigitalSwitchNI'
        channel: '/Dev1/port0/line30:31'
        switch_time: 0.1
        reset_states: False
        names_of_states: [['Low', 'High'], ['Low', 'High']]
        names_of_switches: ['One', 'Two']

    """

    # channels of the NI Card to be used for switching. This can either be a single channel or multiple lines.
    _channel = ConfigOption(name='channel', default='/Dev1/port0/line31', missing='warn')

    # switch_time to wait after setting the states for the connected hardware to react
    _switch_time = ConfigOption(name='switch_time', default=0.1, missing='nothing')

    # names_of_switches defines the switch names.
    # This has to be a list of names in the length of the number_of_switches.
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')

    # names_of_states defines states for each switch, it can define any number of two states per switch.
    # A 2D list of lists defined specific states for each switch
    # and a simple 1D list defines the same states for each of the switches.
    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')

    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')

    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=True, missing='nothing')

    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        """ Create the digital switch output control module
        """
        super().__init__(*args, **kwargs)
        self.lock = RecursiveMutex()

        self._number_of_channels = 0
        self._channels = list()

    def on_activate(self):
        """ Prepare module, connect to hardware.
        The number of switches is automatically determined from the ConfigOption channel:
            /Dev1/port0/line31 lead to 1 switch
            /Dev1/port0/line29:31 leads to 3 switches
        """

        if not self._channel.__contains__(':'):
            self._number_of_channels = 1
            self._channels.append(self._channel)
        else:
            int_parts = re.split(r'\D', str(self._channel))
            start_number = int(int_parts[-2])
            stop_number = int(int_parts[-1])
            front_part = str(self._channel).split(int_parts[-2])[0]

            self._number_of_channels = abs(start_number - stop_number) + 1
            for number in range(start_number,
                                stop_number + 1 if start_number < stop_number else stop_number - 1,
                                1 if start_number < stop_number else -1):
                self._channels.append(front_part + str(number))

        if self._hardware_name is None:
            self._hardware_name = 'NICard' + str(self._channel).replace('/', ' ')

        if isinstance(self._names_of_switches, str) and self.number_of_switches == 1:
            self._names_of_switches = [str(self._names_of_switches)]
        else:
            try:
                self._names_of_switches = [str(name) for name in self._names_of_switches]
            except TypeError:
                self._names_of_switches = [str(index + 1) for index in range(self._number_of_switches)]

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

        # catch and adjust empty _states or _states not matching to the number of channels
        if self._states is None or len(self._states) != self._number_of_channels:
            self._states = dict()
            self.states = {name: self._names_of_states[name][0] for name in self._names_of_switches}

        # initialize channels to saved _states if requested otherwise initialize to 0
        if self._remember_states:
            self.states = self._states
        else:
            self.states = {name: self._names_of_states[name][0] for name in self._names_of_switches}

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        pass

    @property
    def name(self):
        """ Name of the hardware as string.

        The name can either be defined as ConfigOption (name) or it defaults to the name of the hardware module.

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
        return self._states.copy()

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        avail_states = self.available_states
        assert isinstance(state_dict,
                          dict), f'Property "state" must be dict type. Received: {type(state_dict)}'
        assert all(switch in avail_states for switch in
                   state_dict), f'Invalid switch name(s) encountered: {tuple(state_dict)}'
        assert all(isinstance(state, str) for state in
                   state_dict.values()), f'Invalid switch state(s) encountered: {tuple(state_dict.values())}'

        if state_dict:
            with self.lock:
                new_states = self._states.copy()
                new_states.update(state_dict)
                with nidaqmx.Task('NISwitchTask' + self.name.replace(':', ' ')) as switch_task:
                    binary = list()
                    for channel_index, (switch, state) in enumerate(new_states.items()):
                        switch_task.do_channels.add_do_chan(self._channels[channel_index])
                        binary.append(avail_states[switch][0] != state)
                    switch_task.write(binary, auto_start=True)
                    time.sleep(self._switch_time)
                    self._states = new_states

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self._states, f'Invalid switch name: "{switch}"'
        return self._states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        self.states = {switch: state}
