# -*- coding: utf-8 -*-
"""
Interface for logging small amounts of time series data to some place.
First use case is Influxdb.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
from core.util.customexceptions import *
from enum import Enum

class DataLoggerInterface:
    _modtype = 'DataLoggerInterface'
    _modclass = 'interface'

    def get_log_channels(self):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def set_log_channels(self, channelspec):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

    def log_to_channel(self, channel, value):
        raise InterfaceImplementationError('{}->{}'.format(type(self).__name__, function_signature()))

