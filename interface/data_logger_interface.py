# -*- coding: utf-8 -*-
"""
Interface for logging small amounts of time series data to some place.
First use case is Influxdb.

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


class DataLoggerInterface(metaclass=InterfaceMetaclass):
    """

    TODO: This interface has no documentation nor dummy module or logic :'(
    """

    @abstract_interface_method
    def get_log_channels(self):
        pass

    @abstract_interface_method
    def set_log_channels(self, channelspec):
        pass

    @abstract_interface_method
    def log_to_channel(self, channel, value):
        pass

