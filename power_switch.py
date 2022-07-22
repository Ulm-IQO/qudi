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
from core.util.mutex import RecursiveMutex
from interface.switch_interface import SwitchInterface


class PowerSwitch(Base, SwitchInterface):
    """ This class is implements communication with the Keysight E36234A power supply using pyVISA

    Example config for copy-paste:

    power_switch:
        module.Class: 'switches.power_switch.PowerSwitch'
        interface: 'USB0::0x2A8D::0x3402::MY59001224::INSTR'
        hardware_name: 'Power Switch'  # optional
        switch_time: 1  # optional
        remember_states: False  # optional
        switches:
            APD: ['OFF', 'ON']  # optional
    """

    # customize available switches in config. Each switch needs a tuple of at least 2 state names.
    _switches = ConfigOption(name='switches', missing='error')
    # optional name of the hardware
    _hardware_name = ConfigOption(name='hardware_name', default='power_supply', missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=False, missing='nothing')
    # switch_time to wait after setting the states for the solenoids to react
    _switch_time = ConfigOption(name='switch_time', default=0.5, missing='nothing')
    # name of the serial interface where the hardware is connected.
    # Use e.g. the Keysight IO connections expert to find the device.
    serial_interface = ConfigOption('interface', 'USB0::0x2A8D::0x3402::MY59001224::INSTR')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = RecursiveMutex()
        self._resource_manager = None
        self._instrument = None
        self._switches = self._chk_refine_available_switches(self._switches)

    def on_activate(self):
        """ Prepare module, connect to hardware.
        """

        self._resource_manager = visa.ResourceManager()
        self._instrument = self._resource_manager.open_resource(self.serial_interface)
        # set the maximum/protection output Voltage/current of the power supply
        # Excelitas APD: 5V,1.3A
        self._instrument.write('INST CH1')
        self._instrument.write('OUTP 0')
        self._instrument.write('VOLT 5')
        self._instrument.write('CURR 1.3')
        # Minicircuits amplifier: 28V, 4A
        self._instrument.write('INST CH2')
        self._instrument.write('OUTP 0')
        self._instrument.write('VOLT 28')
        self._instrument.write('CURR 4')

        # To be safe, power off during activation
        self._states = dict()
        self._states = {switch: states[0] for switch, states in self._switches.items()}


    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        # switch off outputs of the power supply
        for switch in (0, len(self._switches)):
            self._instrument.write('INST CH{}'.format(switch+1))
            self._instrument.write('OUTP 0')
        self._instrument.close()
        self._resource_manager.close()

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
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        return self._states.copy()

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        assert isinstance(state_dict, dict), 'Parameter "state_dict" must be dict type'
        for switch, state in state_dict.items():
            self.set_state(switch, state)

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        # find the correlated output channel for the switch
        switch_index = list(self._switches).index(switch)
        # Select the switch
        self._instrument.write('INST CH{}'.format(switch_index+1))
        response = self._instrument.query('OUTP?').strip()
        assert int(response) in [0, 1], 'Device not giving proper response'
        self._states[switch] = self._switches[switch][int(response)]

        return self._states[switch]

    def set_state(self, switch, state):
        """ Set state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        # find the correlated output channel for the switch
        switch_index = list(self._switches).index(switch)
        # get the state index, 0==off, 1==on
        state_index = self._switches[switch].index(state)
        # do the job
        if self._states[switch] != state:
            # Select the output channel
            self._instrument.write('INST CH{}'.format(switch_index+1))
            # Switch the switch
            self._instrument.write('OUTP {}'.format(int(state_index)))
        self._states[switch] = state


