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
import numpy as np
import nidaqmx
from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import Mutex
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
        names_of_states: ['Low', 'High']
        names_of_switches: ['One', 'Two']

    """

    _channel = ConfigOption(name='channel', default='/Dev1/port0/line31', missing='warn')
    _switch_time = ConfigOption(name='switch_time', default=0.1, missing='nothing')
    _reset_states = ConfigOption(name='reset_states', default=False, missing='nothing')

    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')

    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        """ Create the digital switch output control module
        """
        super().__init__(*args, **kwargs)
        self.lock = Mutex()

        self._number_of_channels = 0
        self._channels = list()

    def on_activate(self):
        """ Prepare module, connect to hardware.
        The number of switches is automatically determined from the ConfigOption channel:
            /Dev1/port0/line31 lead to 1 switch
            /Dev1/port0/line29:31 leads to 3 switches
        """

        self._hardware_name = 'NICard' + str(self._channel).replace('/', ' ') \
            if self._hardware_name is None else self._hardware_name

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
        elif self.number_of_switches == 1 and isinstance(self._names_of_switches, str):
            self._names_of_switches = [self._names_of_switches]
        else:
            self._names_of_switches = [str(index + 1) for index in range(self.number_of_switches)]

        # catch and adjust empty _states or _states not matching to the number of channels
        if self._states is None or len(self._states) != self._number_of_channels:
            self._states = [False] * self._number_of_channels

        # initialize channels to saved _states if requested
        if not self._reset_states:
            for index, channel in enumerate(self._channels):
                self.set_state(index_of_switch=index, state=self._states[index])

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        pass

    @property
    def name(self):
        """
        Name can either be defined as ConfigOption (name) or it defaults to "NICard" plus the channel name.
            @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def states(self):
        """
        The states of the system as a list of boolean values.
            @return list(bool): All the current states of the switches in a list
        """
        return self._states.copy()

    @states.setter
    def states(self, value):
        """
        The states of the system can be set in two ways:
        Either as a single boolean value to define all the states to be the same
        or as a list of boolean values to define the state of each switch individually.
        After setting the output of the switches, a certain wait time is applied to wait for the hardware to react.
        The wait time can be set by the ConfigOption (switch_time).
            @param [bool/list(bool)] value: switch state to be set as single boolean or list of booleans
            @return: None
        """
        if np.isscalar(value):
            self._states = [bool(value)] * self.number_of_switches
        else:
            if len(value) != self.number_of_switches:
                self.log.error(f'The states either have to be a scalar or a list af length {self.number_of_switches}')
                return
            else:
                self._states = [bool(state) for state in value]

        with self.lock:
            with nidaqmx.Task('NISwitchTask' + self.name) as switch_task:
                binary = 0
                for chan, state in enumerate(self._states):
                    switch_task.do_channels.add_do_chan(self._channels[chan])
                    binary += int(2 ** chan)
                switch_task.write(binary, auto_start=True)
                time.sleep(self._switch_time)

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
        Number of switches provided by this hardware.
        This is automatically determined form the used channels defined by the ConfigOption channel:
            /Dev1/port0/line31 lead to 1 switch
            /Dev1/port0/line29:31 leads to 3 switches
            @return int: number of switches
        """
        return int(self._number_of_channels)

    def get_state(self, index_of_switch):
        """
        Returns the state of a specific switch which was specified by its switch index.
            @param int index_of_switch: index of the switch in the range from 0 to number_of_switches -1
            @return bool: boolean value of this specific switch
        """
        if 0 <= index_of_switch < self.number_of_switches:
            return self._states[int(index_of_switch)]
        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return False

    def set_state(self, index_of_switch=None, state=False):
        """
        Sets the state of a specific switch which was specified by its switch index.
            @param (int/list(int)) index_of_switch: index of the switch in the range from 0 to number_of_switches -1
                                                    or a list of indices in that range
            @param bool state: boolean state of the switch to be set
            @return int: state of the switch actually set
        """
        if index_of_switch is None:
            index_of_switch = list(range(self._number_of_channels))
        elif isinstance(index_of_switch, int):
            if 0 <= index_of_switch < self._number_of_channels:
                index_of_switch = [index_of_switch]
            else:
                self.log.error(f'A switch was requested on channel {index_of_switch} '
                               f'while the number of channels is only {self._number_of_channels}.')
                return -1
        elif isinstance(index_of_switch, (list, tuple, np.ndarray, set)):
            for chan in index_of_switch:
                if not 0 <= index_of_switch < self._number_of_channels:
                    self.log.error(f'A switch was requested on channel {chan} '
                                   f'while the number of channels is only {self._number_of_channels}.')
                    return -2
        else:
            self.log.error(f'The channel either has to be a number or a list of channel numbers'
                           f' but was {index_of_switch}.')
            return -3

        new_state = self.states.copy()
        for chan in index_of_switch:
            new_state[chan] = bool(state)
        self.states = new_state
        return state
