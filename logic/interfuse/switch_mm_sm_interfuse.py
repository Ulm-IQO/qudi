# -*- coding: utf-8 -*-

"""
Combine two hardware switches into one.

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
from core.connector import Connector
import time

class SmMmSwitchInterfuse(Base, SwitchInterface):
    """
    MM_SM_switch:
        module.Class: 'interfuse.switch_mm_sm_interfuse.SmMmSwitchInterfuse'
        routing:
            'SM': '/Dev1/PFI8'
            'MM': '/Dev1/PFI9'
        connect:
            arduino_pwm_switch: 'myadulino_pwm'
            counter_logic: 'counterlogic'
            my_ni: 'mynicard'
    """

    # connectors for the switches to be combined
    routing = ConfigOption()
    arduino_pwm_switch = Connector(interface='SwitchInterface')
    counter_logic = Connector(interface='CounterLogic')
    my_ni = Connector(interface='NationalInstrumentsXSeries')

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        assert 'fiber' in self.arduino_pwm_switch().available_states.keys()
        assert ('SM', 'MM') == self.arduino_pwm_switch().available_states['fiber']

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        pass

    @property
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self.arduino_pwm_switch().name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        return self.arduino_pwm_switch().available_states

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        return self.arduino_pwm_switch().get_state(switch)

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        if switch == 'fiber':
            fiber_state = self.get_state('fiber')
            if state != fiber_state:
                self.arduino_pwm_switch().set_state(switch, state)
                self.log.info(f'Switching to {"Multimode fiber" if state=="MM" else "Singlemode fiber"}')
                self.my_ni()._photon_sources = [self.routing[state]]
                if self.counter_logic().module_state() == 'locked':
                    self.counter_logic().stopCount()
                    time.sleep(0.1) # need to give the counter some time to stop
                    self.counter_logic().startCount()
        else:
            self.arduino_pwm_switch().set_state(switch, state)

    # Non-abstract default implementations below

    @property
    def number_of_switches(self):
        """ Number of switches provided by the hardware.

        @return int: number of switches
        """
        return len(self.available_states)

    @property
    def switch_names(self):
        """ Names of all available switches as tuple.

        @return str[]: Tuple of strings of available switch names.
        """
        return tuple(self.available_states)

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        return {switch: self.get_state(switch) for switch in self.available_states}

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

    @staticmethod
    def _chk_refine_available_switches(switch_dict):
        """ Perform some general checking of the configured available switches and their possible
        states. When implementing a hardware module, you can overwrite this method to include
        custom checks, but make sure to call this implementation first via super().

        @param dict switch_dict: available switches in a dict like {"switch1": ["state1", "state2"]}
        @return dict: The refined switch dict to replace the dict passed as argument
        """
        assert isinstance(switch_dict, dict), 'switch_dict must be a dict of tuples'
        assert all((isinstance(sw, str) and sw) for sw in
                   switch_dict), 'Switch name must be non-empty string'
        assert all(len(states) > 1 for states in
                   switch_dict.values()), 'State tuple must contain at least 2 states'
        assert all(all((s and isinstance(s, str)) for s in states) for states in
                   switch_dict.values()), 'Switch states must be non-empty strings'
        # Convert state lists to tuples in order to restrict mutation
        return {switch: tuple(states) for switch, states in switch_dict.items()}
