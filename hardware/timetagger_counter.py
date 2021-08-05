# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module to use TimeTagger as a counter.

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

import TimeTagger as tt
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from core.connector import Connector
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode


class TimeTaggerCounter(Base, SlowCounterInterface):
    """ Using the TimeTagger as a slow counter.

    Example config for copy-paste:

    timetagger_slowcounter:
        module.Class: 'timetagger_counter.TimeTaggerCounter'
        timetagger_channel_apd_0: 0
        timetagger_channel_apd_1: 1
        timetagger_sum_channels: 2

    """

    _channel_apd_0 = ConfigOption('timetagger_channel_apd_0', missing='error')
    _channel_apd_1 = ConfigOption('timetagger_channel_apd_1', None, missing='warn')
    timetagger = Connector(interface='TT')

    def on_activate(self):
        """ Start up TimeTagger interface
        """
        
        self._tagger = self.timetagger()
        self._count_frequency = 50  # Hz

        ## self._mode can take 3 values:
        # 0: single channel, no summing
        # 1: single channel, summed over apd_0 and apd_1
        # 2: dual channel for apd_0 and apd_1
        self.set_up_counter()

    def on_deactivate(self):
        """ Shut down the TimeTagger.
        """
        #self.reset_hardware()
        pass

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the TimeTagger for timing

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """

        self._count_frequency = clock_frequency
        return 0

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param str counter_channel: optional, physical channel of the counter
        @param str photon_source: optional, physical channel where the photons
                                  are to count from
        @param str counter_channel2: optional, physical channel of the counter 2
        @param str photon_source2: optional, second physical channel where the
                                   photons are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)
        """

        # currently, parameters passed to this function are ignored -- the channels used and clock frequency are
        # set at startup
       
        
        self.counter = self._tagger.counter(
            channels=[self._channel_apd_0, self._channel_apd_1, self._tagger._combined_channels.getChannel()],
            bins_width=int((1 / self._count_frequency) * 1e12),
            n_values=1)
    

        self.log.info('set up counter with {0}'.format(self._count_frequency))
        return 0

    def get_counter_channels(self):
            return [self._channel_apd_0, self._channel_apd_1, self._tagger._combined_channels.getChannel()]

    def get_constraints(self):
        """ Get hardware limits the device

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 2
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array(uint32): the photon counts per second
        """

        time.sleep(2 / self._count_frequency)
        return np.array(self.counter.getData()) * self._count_frequency

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        self._tagger.tagger.reset()
        return 0

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0
