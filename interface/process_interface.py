# -*- coding: utf-8 -*-

"""
Interface file to use processes.

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


class ProcessInterface(metaclass=InterfaceMetaclass):
    """ A simple interface to measure one or multiple value(s).
    """

    @abstract_interface_method
    def get_process_value(self, channel=None):
        """ Return a measured value

        @param (int) channel: (Optional) The number of the channel
        @return (float): The measured process value
        """
        pass

    @abstract_interface_method
    def get_process_unit(self, channel=None):
        """ Return the unit that the value is measured in as a tuple of ('abbreviation', 'full unit name')

        @param (int) channel: (Optional) The number of the channel

        @return: The unit as a tuple of ('abbreviation', 'full unit name')

         """
        pass

    def process_supports_multiple_channels(self):
        """ Function to test if hardware support multiple channels

        @return (bool): Whether the hardware supports multiple channels

        This function is not abstract - Thus it is optional and if a hardware do not implement it, the answer is False.
        """
        return False

    def process_get_number_channels(self):
        """ Function to get the number of channels available for measure

        @return (int): The number of channel(s)

        This function is not abstract - Thus it is optional and if a hardware do not implement it, the answer is 1.
        """
        return 1
