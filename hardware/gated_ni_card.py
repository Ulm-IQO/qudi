# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module NICard class.

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

import numpy as np
import re

import PyDAQmx as daq

from core.module import Base, ConfigOption
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
from interface.odmr_counter_interface import ODMRCounterInterface
from interface.confocal_scanner_interface import ConfocalScannerInterface
from .national_instruments_x_series import NationalInstrumentsXSeries


class SlowGatedNICard(NationalInstrumentsXSeries):
    """ Enable the usage of the gated counter in the slow counter interface.
    Overwrite in this new class therefore the appropriate methods. """

    _modtype = 'SlowGatedNICard'
    _modclass = 'hardware'

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        self._gated_counter_daq_task = None
        self._counter_channels = []
        self._counter_channel = '/NIDAQ/Ctr0'

        config = self.getConfiguration()

        if 'photon_source' in config.keys():
            self._photon_source = config['photon_source']
        else:
            self.log.error(
                'No parameter "photon_source" configured.\n'
                'Assign to that parameter an appropriated channel from your NI Card!')

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 4
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.FINITE_GATED]
        return constraints

    #overwrite the SlowCounterInterface commands of the class NICard:
    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """
        # ignore that command. For an gated counter (with external trigger
        # you do not need a clock signal).
        return 0

    def set_up_counter(self,
                       counter_channel=None,
                       photon_source=None,
                       counter_channel2=None,
                       photon_source2=None,
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
        if self.set_up_gated_counter(buffer_length=counter_buffer) < 0:
            return -1
        return self.start_gated_counter()

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array(uint32): the photon counts per second
        """
        return self.get_gated_counts(samples=samples)

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        if self.stop_gated_counter() < 0:
            return -1
        return self.close_gated_counter()

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0

