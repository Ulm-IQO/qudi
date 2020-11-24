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

    digital_switch_ni:
        module.Class: 'switches.digital_switch_ni.DigitalSwitchNI'
        channel: '/Dev1/port0/line30:31'  # optional
        name: 'My Switch Hardware Name'  # optional
        switch_time: 0.1
        remember_states: True
        switches:                       # optional
            One: ['Low', 'High']
            Two: ['Off', 'On']
    """
    # ToDo: Implement this switch module for PFI channels. These do not clash with other tasks
    #  contrary to a digital out port.
    # Channels of the NI Card to be used for switching.
    # Can either be a single channel or multiple lines.
    _channel = ConfigOption(name='channel', default='/Dev1/port0/line31', missing='warn')
    # switch_time to wait after setting the states for the connected hardware to react
    _switch_time = ConfigOption(name='switch_time', default=0.1, missing='nothing')
    # optionally customize all switches in config. Each switch needs a tuple of 2 state names.
    # If used, you must specify as many switches as you have specified channels
    _switches = ConfigOption(name='switches', default=None, missing='nothing')
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

        self._channels = tuple()

    def on_activate(self):
        """ Prepare module, connect to hardware.
        The number of switches is automatically determined from the ConfigOption channel:
            /Dev1/port0/line31 lead to 1 switch
            /Dev1/port0/line29:31 leads to 3 switches
        """
        # Determine DO lines to use. This defines the number of switches for this module.
        assert isinstance(self._channel, str), 'ConfigOption "channel" must be str type'
        match = re.match(r'(.*?dev\d/port\d/line)(\d+)(?::(\d+))?', self._channel, re.IGNORECASE)
        assert match is not None, 'channel string invalid. Valid example: "/Dev1/port0/line29:31"'
        if match.groups()[2] is None:
            self._channels = (match.group(),)
        else:
            first, last = sorted(int(ch) for ch in match.groups()[1:])
            prefix = match.groups()[0]
            self._channels = tuple('{0}{1:d}'.format(prefix, ii) for ii in range(first, last + 1))

        # Determine available switches and states
        if self._switches is None:
            self._switches = {str(ii): ('Off', 'On') for ii in range(1, len(self._channels) + 1)}
        self._switches = self._chk_refine_available_switches(self._switches)

        if self._hardware_name is None:
            self._hardware_name = 'NICard' + str(self._channel).replace('/', ' ')

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
        return self._switches.copy()

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

    def _chk_refine_available_switches(self, switch_dict):
        """ See SwitchInterface class for details

        @param dict switch_dict:
        @return dict:
        """
        refined = super()._chk_refine_available_switches(switch_dict)
        num = len(self._channels)
        assert len(refined) == num, f'Exactly {num} switches or None must be specified in config'
        assert all(len(s) == 2 for s in refined.values()), 'Switches can only take exactly 2 states'
        return refined
