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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class TriggerInterface(metaclass=InterfaceMetaclass):

    @property
    @abstract_interface_method
    def number_of_triggers(self):
        """ The number of triggers provided by this hardware file.
        @return int: number of triggers
        """
        pass

    @property
    @abstract_interface_method
    def names_of_triggers(self):
        """ Names of the triggers as list of strings.
        @return list(str): names of the triggers
        """
        pass

    @abstract_interface_method
    def trigger(self, trigger=None):
        """ Triggers the hardware.
        The trigger is performed either
        on all channels, if trigger is None,
        on a single channel, if trigger is a single channel name or
        on a list of channels, if trigger is a list of channel names.
        @param [None/str/list(str)] trigger: trigger name to be triggered
        @return int: negative error code or 0 at success
        """
        pass

    @property
    @abstract_interface_method
    def trigger_length(self):
        """ Returns the length of all the triggers of this hardware in seconds.
        @return int: length of the trigger
        """
        pass

    @trigger_length.setter
    @abstract_interface_method
    def trigger_length(self, value):
        """ Sets the trigger length in seconds.
        @param float value: length of the trigger to be set
        """
        pass
