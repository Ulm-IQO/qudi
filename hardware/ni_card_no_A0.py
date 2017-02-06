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
from ctypes import *

import PyDAQmx as daq

from hardware.ni_card import NICard
from interface.slow_counter_interface import CountingMode, SlowCounterConstraints
class SlowNICard(NICard):
    """ Enable the usage of the gated counter in the slow counter interface.
    Overwrite in this new class therefore the appropriate methods. """

    _modtype = 'SlowNICard'
    _modclass = 'hardware'

    # connectors
    _out = {'slowcounter1' : 'SlowCounterInterface'}


    def on_activate(self, e=None):
        """ Starts up the NI Card at activation.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        # the tasks used on that hardware device:
        self._counter_daq_tasks = []
        self._clock_daq_task = None
        self._scanner_clock_daq_task = None
        self._scanner_ao_task = None
        self._scanner_counter_daq_tasks = []
        self._line_length = None
        self._odmr_length = None
        self._gated_counter_daq_task = None

        # used as a default for expected maximum counts
        self._max_counts = 3e7
        # timeout for the Read or/and write process in s
        self._RWTimeout = 10

        self._clock_frequency_default = 100             # in Hz
        self._scanner_clock_frequency_default = 100     # in Hz
        # number of readout samples, mainly used for gated counter
        self._samples_number_default = 50

        config = self.getConfiguration()

        self._scanner_ao_channels = []
        self._voltage_range = []
        self._position_range = []
        self._current_position = []
        self._counter_channels = []
        self._scanner_counter_channels = []
        self._photon_sources = []

        self._scanner_clock_channel = []
        # handle all the parameters given by the config

        self._odmr_trigger_channel = None

        if 'clock_channel' in config.keys():
            self._clock_channel = config['clock_channel']
        else:
            self.log.error(
                'No parameter "clock_channel" configured.'
                'Assign to that parameter an appropriate channel from your NI Card!')

        if 'photon_source' in config.keys():
            self._photon_sources.append(config['photon_source'])
            n = 2
            while 'photon_source{0}'.format(n) in config.keys():
                self._photon_sources.append(config['photon_source{0}'.format(n)])
                n += 1
        else:
            self.log.error(
                'No parameter "photon_source" configured.\n'
                'Assign to that parameter an appropriated channel from your NI Card!')

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

        if 'clock_frequency' in config.keys():
            self._clock_frequency = config['clock_frequency']
        else:
            self._clock_frequency = self._clock_frequency_default
            self.log.warning(
                'No clock_frequency configured, taking 100 Hz instead.')

        if 'gate_in_channel' in config.keys():
            self._gate_in_channel = config['gate_in_channel']
        else:
            self.log.error(
                'No parameter "gate_in_channel" configured.\n'
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


    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 4
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = 'continuous'
        return constraints