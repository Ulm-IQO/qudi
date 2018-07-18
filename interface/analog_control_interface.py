# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for confocal scanner.

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

import abc
from core.util.interfaces import InterfaceMetaclass


class AnalogControlInterface(metaclass=InterfaceMetaclass):
    """ Interface class to define the analog control of multiple channels. """

    _modtype = 'AnalogControlInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_channels(self):
        """ Ask for the available channels. 

        @return list: all the available analog channel names in the form
                        ['<channel_name1>','<channel_name2>',...]
        """
        pass

    @abc.abstractmethod
    def get_voltage(self, channels=None):
        """ Retrieve the analog voltages.

        @param list channels: optional, if specific voltage values are 
                              requested. The input should be in the form
                                    ['<channel_name1>','<channel_name2>',...]  

        @return dict: the channels with the corresponding analog voltage. If
                      channels=None, all the available channels are returned.
                      The dict will have the form 
                        {'<channel_name1>': voltage-float-value,
                         '<channel_name2>': voltage-float-value, ...} 
        """
        pass

    @abc.abstractmethod
    def set_voltage(self, volt_dict):
        """ Set the voltages. 

        @param dict volt_dict: the input voltages in the form
                                    {'<channel_name1>': voltage-float-value,
                                     '<channel_name2>': voltage-float-value, 
                                     ...}

        @return dict: All the actual voltage values, which were set to the 
                      device. The return value has the same form as the input
                      dict.
        """
        pass