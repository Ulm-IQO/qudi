# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for analog reader.

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


class AnalogReaderInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the simple
    analog input hardware.
    """

    _modtype = 'AnalogReaderInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_up_analog_reader(self,
                             analog_channel=None,
                             voltage_levels=None,
                             clock_channel=None,
                             analog_buffer=None,
                             analog_mode=None,
                             channel=None):
        """ Configures the actual counter with a given clock.

        @param str analog_channel: optional, physical channel of the voltage input, list of two
                                    for differential reading
        @param str voltage_levels: optional, list with two inputs that specifies the max. and
                                  minimum voltage levels of the input
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int analog_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.
        @param str analog_mode: optional, decides on the read mode of the counter (res,
        nres or differential)
        @param int channel: optional handler, distinguishes between different analog inputs as
                                   up to 31 are possible in parallel.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_analog_levels(self, samples=None):
        """ Returns the current voltages per bin at the analog input.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array(uint32): the voltage per time bin
        """
        pass

    @abc.abstractmethod
    def close_analog_reader(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass