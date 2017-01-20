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

from hardware.ni_card import NICard

class SlowGatedNICard(NICard):
    """ Enable the usage of the gated counter in the slow counter interface.
    Overwrite in this new class therefore the appropriate methods. """

    _modtype = 'SlowGatedNICard'
    _modclass = 'hardware'

    # connectors
    _out = {'gatedslowcounter1' : 'SlowCounterInterface'}

    def on_activate(self, e=None):
        """ Starts up the NI Card at activation.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """
        self._gated_counter_daq_task = None
        # used as a default for expected maximum counts
        self._max_counts = 3e7
        # timeout for the Read or/and write process in s
        self._RWTimeout = 5
        # in Hz
        self._clock_frequency_default = 100
        # number of readout samples mainly used for gated counter
        self._samples_number_default = 50
        # count on rising edge mainly used for gated counter
        self._counting_edge_default = True

        #self._counter_channels = '/NIDAQ/Ctr0'

        config = self.getConfiguration()

        self._counter_channels = []

        if 'counter_channel' in config.keys():
            self._counter_channels.append(config['counter_channel'])
            n = 2
            while 'counter_channel{0}'.format(n) in config.keys():
                self._counter_channels.append(config['counter_channel{0}'.format(n)])
                n += 1
        else:
            self.log.error(
                'No parameter "counter_channel" configured.\n'
                'Assign to that parameter an appropriate channel from your NI Card!')

        if 'photon_source' in config.keys():
            self._photon_source=config['photon_source']
        else:
            self.log.error(
                'No parameter "photon_source" configured.\n'
                'Assign to that parameter an appropriated channel from your NI Card!')

        if 'gate_in_channel' in config.keys():
            self._gate_in_channel = config['gate_in_channel']
        else:
            self.log.error(
                'No parameter "gate_in_channel" configured. '
                'Choose the proper channel on your NI Card and assign it to that parameter!')

        if 'counting_edge_rising' in config.keys():
            if config['counting_edge_rising']:
                self._counting_edge = daq.DAQmx_Val_Rising
            else:
                self._counting_edge = daq.DAQmx_Val_Falling
        else:
            self.log.warning(
                'No parameter "counting_edge_rising" configured.\n'
                'Set this parameter either to True (rising edge) or to False (falling edge).\n'
                'Taking the default value {0}'.format(self._counting_edge_default))

            self._counting_edge = self._counting_edge_default

        if 'samples_number' in config.keys():
            self._samples_number = config['samples_number']
        else:
            self._samples_number = self._samples_number_default
            self.log.warning(
                'No parameter "samples_number" configured taking the default value "{0}" instead.'
                ''.format(self._samples_number_default))
            self._samples_number = self._samples_number_default

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

