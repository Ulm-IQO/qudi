# -*- coding: utf-8 -*-
"""
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

import requests

from core.module import Base
from core.configoption import ConfigOption
from interface.switch_interface import SwitchInterface


class SpdtSwitch(Base, SwitchInterface):
    """ This class is implements communication with Minicricuit RC-xSPDT-Axx hardware

    This hardware controls one or multiple switch via SMA cables. It can connect either port 1 or port 2 to a COM port.
    This type of hardware can automatize the change of cabling configuration for SMA, BNC, etc. cables.

    It has been tested with :
        - RC-4SPDT-A26

    This module use the web api running on the hardware. Interfacing with dll via USB is supported by hardware but not
    implemented in this module (yet).

    Example config for copy-paste:

    spdt_switch:
        module.Class: 'switches.minicircuit_RC_SPDT.SpdtSwitch'
        http_address: 'http://192.168.1.10/' # 'http://ADDRESS:PORT/PWD;'
        number_of_switch: 4
    """

    _http_address = ConfigOption('http_address', missing='error')
    _number_of_switch = ConfigOption('number_of_switch', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._model = None

    def on_activate(self):
        """ Module activation method """
        try:
            self._model = self._get('MN?', split=True)
            self.log.info('Connected to {}'.format(self._model))
        except requests.exceptions.RequestException:
            self.log.error('Can not connect to hardware. Check cables and config address.')

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        pass

    def _get(self, command, split=False):
        """ Send a command via the web api and return the result

        @param (str) command: The command to send to hardware
        @param (bool) split: Wheter to return only the part after the "=" in the response or full text.

        @return (str): The result of the web request as text
        """
        url = '{}{} '.format(self._http_address, command)  # the space at the end prevent request from removing "?"
        response = requests.get(url, timeout=1).text
        if split:
            response = response.split('=')[1]
        return response

    @property
    def name(self):
        """ Name of the hardware as string. """
        return self._model

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        states = {}
        for i in range(self.number_of_switches):
            states[(chr(65+i))] = ('1', '2')
        return states

    def get_state(self, switch):
        """ Query state of single switch by name """
        return self.states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name """
        states = {'1': 0,  '2': 1}
        self._get('SET{}={}'.format(switch, states[state]))

    # Non-abstract default implementations below
    @property
    def number_of_switches(self):
        """ Number of switches provided by the hardware. """
        return int(self._number_of_switch)

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        binary_state = int(self._get('SWPORT?'))
        result = {}
        conversion = ['1', '2']
        for i in range(self.number_of_switches):
            result[(chr(65+i))] = conversion[binary_state >> i & 1]
        return result
