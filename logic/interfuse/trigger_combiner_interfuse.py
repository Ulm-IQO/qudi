# -*- coding: utf-8 -*-

"""
Combine two hardware triggers into one.

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
from core.configoption import ConfigOption
from core.connector import Connector
import numpy as np

from interface.trigger_interface import TriggerInterface


class TriggerCombinerInterfuse(Base, TriggerInterface):
    """ Combine two hardware triggers into one.
    """

    # connectors for the switches to be combined
    trigger1 = Connector(interface='TriggerInterface')
    trigger2 = Connector(interface='TriggerInterface')

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        pass

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        pass

    @property
    def number_of_triggers(self):
        """ The number of triggers provided by this hardware file.
        @return int: number of triggers
        """
        return self.trigger1().number_of_triggers + self.trigger2().number_of_triggers

    @property
    def names_of_triggers(self):
        """ Names of the triggers as list of strings.
        @return list(str): names of the triggers
        """
        return self.trigger1().names_of_triggers + self.trigger2().names_of_triggers

    def trigger(self, trigger=None):
        """ Triggers the hardware.
        The trigger is performed either
        on all channels, if trigger is None,
        on a single channel, if trigger is a single channel name or
        on a list of channels, if trigger is a list of channel names.
        @param [None/str/list(str)] trigger: trigger name to be triggered
        @return int: negative error code or 0 at success
        """
        if trigger is None:
            return self.trigger1().trigger() + self.trigger2().trigger()
        elif isinstance(trigger, str):
            results = 0
            if trigger in self.trigger1().names_of_triggers:
                results += self.trigger1().trigger(trigger)
            if trigger in self.trigger2().names_of_triggers:
                results += self.trigger2().trigger(trigger)
            if trigger not in self.names_of_triggers:
                self.log.error(f'trigger name "{trigger}" was requested, but the options are: {self.names_of_triggers}')
                return -1
            return results
        elif isinstance(trigger, (list, tuple, np.ndarray, set)):
            trigger1 = list()
            trigger2 = list()
            for index, item in enumerate(trigger):
                if item in self.trigger1().names_of_triggers:
                    trigger1.append(item)
                if item in self.trigger2().names_of_triggers:
                    trigger2.append(item)
                if item not in self.names_of_triggers:
                    self.log.warning(f'trigger name "{item}" was requested, '
                                     f'but the options are: {self.names_of_triggers}')
            results = 0
            if len(trigger1):
                results += self.trigger1().trigger(trigger1)
            if len(trigger2):
                results += self.trigger2().trigger(trigger2)
            return results
        else:
            self.log.error(f'The trigger name was {trigger} but either has to be one of {self.names_of_triggers} '
                           f'or a list of trigger names.')
            return -2

    @property
    def trigger_length(self):
        """ Returns the length of all the triggers of this hardware in seconds.
        @return int: length of the trigger
        """
        if self.trigger1().trigger_length != self.trigger2().trigger_length:
            self.log.warning(f'trigger_length of individual triggers do not match. '
                             f'Trigger1: {self.trigger1().trigger_length}, '
                             f'Trigger2: {self.trigger2().trigger_length}')
        return max(self.trigger1().trigger_length, self.trigger2().trigger_length)

    @trigger_length.setter
    def trigger_length(self, value):
        """ Sets the trigger length in seconds.
        @param float value: length of the trigger to be set
        """
        if not isinstance(value, (int, float)):
            self.log.error(f'trigger_length has to be of type float but was {value}.')
            return
        self.trigger1().trigger_length = float(value)
        self.trigger2().trigger_length = float(value)
