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

from logic.generic_logic import GenericLogic
from core.connector import Connector
from interface.trigger_interface import TriggerInterface
from qtpy import QtCore


class TriggerLogic(GenericLogic, TriggerInterface):
    """ Logic module for interacting with the hardware switches.
    This logic has the same structure as the SwitchInterface but supplies additional functionality:
        - switches can either be manipulated by index or by their names
        - signals are generated on state changes
    """

    sig_trigger_done = QtCore.Signal(int, object)

    # connector for one trigger, if multiple switches are needed use the TriggerCombinerInterfuse.
    trigger_hardware = Connector(interface='TriggerInterface')

    def on_activate(self):
        """ Prepare logic module for work.
        """

    def on_deactivate(self):
        """ Deactivate module.
        """

    @property
    def number_of_triggers(self):
        """ The number of triggers provided by this hardware file.
        @return int: number of triggers
        """
        return self.trigger_hardware().number_of_triggers

    @property
    def names_of_triggers(self):
        """ Names of the triggers as list of strings.
        @return list(str): names of the triggers
        """
        return self.trigger_hardware().names_of_triggers

    def trigger(self, trigger=None):
        """ Triggers the hardware.
        The trigger is performed either
        on all channels, if trigger is None,
        on a single channel, if trigger is a single channel name or
        on a list of channels, if trigger is a list of channel names.
        @param [None/str/list(str)] trigger: trigger name to be triggered
        @return int: negative error code or 0 at success
        """
        results = self.trigger_hardware().trigger(trigger)
        self.sig_trigger_done.emit(results, trigger)
        return results

    @property
    def trigger_length(self):
        """ Returns the length of all the triggers of this hardware in seconds.
        @return int: length of the trigger
        """
        return self.trigger_hardware().trigger_length

    @trigger_length.setter
    def trigger_length(self, value):
        """ Sets the trigger length in seconds.
        @param float value: length of the trigger to be set
        """
        self.trigger_hardware().trigger_length = value
