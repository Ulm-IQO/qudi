# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware interface for fast counting devices.

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


class FiniteCounterInterface(metaclass=InterfaceMetaclass):
    """ Interface class to define the controls for counting devices with a finite time length
    acquisition. """

    _modtype = 'FiniteCounterInterface'
    _modclass = 'interface'


    @abc.abstractmethod
    def get_scanner_count_channels(self):
        """ Returns the list of channels that are recorded while scanning an image.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels.
        """
        pass
        # Todo this is connected to NIDAQ not attocube and has to be checked later

    @abc.abstractmethod
    def set_up_finite_counter(self, samples,
                             counter_channel=None,
                             photon_source=None,
                             clock_channel=None):
        """ Initializes task for couting a certain number of samples with given
        frequency. This ensures a handwaving synch between the counter and other devices.

        It works pretty much like the normal counter. Here you connect a
        created clock with a counting task. However here you only count for a predefined
        amount of time that is given by samples*frequency. The counts are sampled by
        the underlying clock.

        @param int samples: Defines how many counts should be gathered within one period
        @param string counter_channel: if defined, this is the physical channel
                                       of the counter
        @param string photon_source: if defined, this is the physical channel
                                     from where the photons are to be counted
        @param string clock_channel: if defined, this specifies the clock for
                                     the counter

        @return int:  error code (0: OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_up_finite_counter_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def start_finite_counter(self):
        """Starts the preconfigured counter task

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def stop_finite_counter(self):
        """Stops the preconfigured counter task

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_finite_counter(self):
        """ Clear tasks, so that counters are not in use any more.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_finite_counter_clock(self):
        """ Closes the finite counter clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_finite_counts(self):
        """ Returns latest count samples acquired by finite photon counting.

        @return np.array, samples:The photon counts per second and the amount of samples read. For
        error array with length 1 and entry -1
        """
        pass

    @abc.abstractmethod
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
      -1 = error state
        """
        pass
