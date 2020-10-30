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

from core.module import Base
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
import numpy as np
import time

from interface.trigger_interface import TriggerInterface


class DummyTrigger(Base, TriggerInterface):
    """ This is a dummy to simulate a simple trigger.
    """

    # ConfigOptions
    # names_of_triggers defined as list of strings
    _names_of_triggers = ConfigOption(name='names_of_triggers', default=['one', 'two'], missing='nothing')

    # StatusVariables
    # trigger_length in seconds
    _trigger_length = StatusVar(name='trigger_length', default=0.5)

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
        return len(self._names_of_triggers)

    @property
    def names_of_triggers(self):
        """ Names of the triggers as list of strings.
        @return list(str): names of the triggers
        """
        return self._names_of_triggers.copy()

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
            trigger = self.names_of_triggers
        elif isinstance(trigger, str):
            if trigger in self.names_of_triggers:
                trigger = [trigger]
            else:
                self.log.error(f'trigger name "{trigger}" was requested, but the options are: {self.names_of_triggers}')
                return -1
        elif isinstance(trigger, (list, tuple, np.ndarray, set)):
            for index, item in enumerate(trigger):
                if item not in self.names_of_triggers:
                    self.log.error(f'trigger name "{trigger}" was requested, '
                                   f'but the options are: {self.names_of_triggers}')
                    del trigger[index]
        else:
            self.log.error(f'The trigger name was {trigger} but either has to be one of {self.names_of_triggers} '
                           f'or a list of trigger names.')
            return -2

        for item in trigger:
            self.log.info(f'Trigger on channel: {item}.')

        time.sleep(self.trigger_length)
        return 0

    @property
    def trigger_length(self):
        """ Returns the length of all the triggers of this hardware in seconds.
        @return int: length of the trigger
        """
        return self._trigger_length

    @trigger_length.setter
    def trigger_length(self, value):
        """ Sets the trigger length in seconds.
        @param float value: length of the trigger to be set
        """
        if not isinstance(value, (int, float)):
            self.log.error(f'trigger_length has to be of type float but was {value}.')
            return
        self._trigger_length = float(value)
