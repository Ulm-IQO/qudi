# -*- coding: utf-8 -*-
"""
This file contains the QuDi Interface file for ODMRCounter.

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

Copyright (C) 2015 Kay Jahnke kay.jahnke@alumni.uni-ulm.de
"""

from core.util.customexceptions import InterfaceImplementationError


class ODMRCounterInterface():
    """ This is the Interface class supplies the controls for a simple ODMR."""

    _modtype = 'ODMRCounterInterface'
    _modclass = 'interface'

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ODMRCounterInterface>set_up_odmr_clock')
        return -1

    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """ Configures the actual counter with a given clock.

        @param str counter_channel: if defined, this is the physical channel of
                                    the counter
        @param str photon_source: if defined, this is the physical channel where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str odmr_trigger_channel: if defined, this specifies the trigger
                                         output for the microwave

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ODMRCounterInterface>set_up_odmr')
        return -1

    def set_odmr_length(self, length=100):
        """Set up the trigger sequence for the ODMR and the triggered microwave.

        @param int length: length of microwave sweep in pixel

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ODMRCounterInterface>set_odmr_length')
        return -1

    def count_odmr(self, length = 100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel

        @return float[]: the photon counts per second
        """

        raise InterfaceImplementationError('ODMRCounterInterface>count_odmr')
        return [0.0]

    def close_odmr(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ODMRCounterInterface>close_odmr')
        return -1

    def close_odmr_clock(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ODMRCounterInterface>close_odmr_clock')
        return -1
