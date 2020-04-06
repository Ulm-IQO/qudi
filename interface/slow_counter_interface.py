# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface for Slow counter.

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
from enum import Enum
from core.meta import InterfaceMetaclass


class SlowCounterInterface(metaclass=InterfaceMetaclass):
    """ Define the controls for a slow counter.

    A slow counter is a measuring device that measures with a precise frequency one or multiple physical quantities.

    An example is a device that counts photons in real time with a given frequency.

    The main idea of such a device is that the hardware handles the timing, and measurement of one or multiple
    time varying quantities. The logic will periodically (but with imprecise timing) poll the hardware for the new
    reading, not knowing if there is one, multiple or none.
    """

    @abstract_interface_method
    def get_constraints(self):
        """ Retrieve the hardware constrains from the counter device.

        @return (SlowCounterConstraints): object with constraints for the counter

        The constrains are defined as a SlowCounterConstraints object, defined at  the end of this file
        """
        pass

    @abstract_interface_method
    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Set the frequency of the counter by configuring the hardware clock

        @param (float) clock_frequency: if defined, this sets the frequency of the clock
        @param (string) clock_channel: if defined, this is the physical channel of the clock
        @return int: error code (0:OK, -1:error)

        TODO: Should the logic know about the different clock channels ?
        """
        pass

    @abstract_interface_method
    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param list(str) counter_channels: optional, physical channel of the counter
        @param list(str) sources: optional, physical channel where the photons
                                   photons are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)

        There need to be exactly the same number sof sources and counter channels and
        they need to be given in the same order.
        All counter channels share the same clock.
        """
        pass

    @abstract_interface_method
    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array((n, uint32)): the measured quantity of each channel
        """
        pass

    @abstract_interface_method
    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        pass
 
    @abstract_interface_method
    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)

        TODO: This method is very hardware specific, it should be deprecated
        """
        pass


class CountingMode(Enum):
    """
    TODO: Explain what are the counting mode and how they are used
    """
    CONTINUOUS = 0
    GATED = 1
    FINITE_GATED = 2


class SlowCounterConstraints:

    def __init__(self):
        # maximum numer of possible detectors for slow counter
        self.max_detectors = 0
        # frequencies in Hz
        self.min_count_frequency = 5e-5
        self.max_count_frequency = 5e5
        # TODO: add CountingMode enums to this list in instances
        self.counting_mode = []

