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
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
from .national_instruments_x_series import NationalInstrumentsXSeries


class SlowGatedNICard(NationalInstrumentsXSeries):
    """ Enable the usage of the gated counter in the slow counter interface.
    Overwrite in this new class therefore the appropriate methods.

    Example config for copy-paste:

    slowgated_ni:
        module.Class: 'gated_ni_card.SlowGatedNICard'
        photon_sources:
            - '/Dev1/PFI8'
        #    - '/Dev1/PFI9'
        clock_channel: '/Dev1/Ctr0'
        default_clock_frequency: 100 # optional, in Hz
        counter_channels:
            - '/Dev1/Ctr1'
        counter_ai_channels:
            - '/Dev1/AI0'
        default_scanner_clock_frequency: 100 # optional, in Hz
        scanner_clock_channel: '/Dev1/Ctr2'
        pixel_clock_channel: '/Dev1/PFI6'
        scanner_ao_channels:
            - '/Dev1/AO0'
            - '/Dev1/AO1'
            - '/Dev1/AO2'
            - '/Dev1/AO3'
        scanner_ai_channels:
            - '/Dev1/AI1'
        scanner_counter_channels:
            - '/Dev1/Ctr3'
        scanner_voltage_ranges:
            - [-10, 10]
            - [-10, 10]
            - [-10, 10]
            - [-10, 10]
        scanner_position_ranges:
            - [0e-6, 200e-6]
            - [0e-6, 200e-6]
            - [-100e-6, 100e-6]
            - [-10, 10]

        odmr_trigger_channel: '/Dev1/PFI7'

        gate_in_channel: '/Dev1/PFI9'
        default_samples_number: 50
        max_counts: 3e7
        read_write_timeout: 10
        counting_edge_rising: True

    """

    _photon_sources = ConfigOption('photon_sources', missing='error')

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        self._gated_counter_daq_task = None
        self._counter_channels = []
        self._counter_channel = '/Dev1/Ctr0'

        self._ph_source = self._photon_sources[0]

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
    def set_up_clock(self, clock_frequency=None, clock_channel=None, scanner=False, idle=False):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock in Hz
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock within the NI card.
        @param bool scanner: if set to True method will set up a clock function
                             for the scanner, otherwise a clock function for a
                             counter will be set.
        @param bool idle: set whether idle situation of the counter (where
                          counter is doing nothing) is defined as
                                True  = 'Voltage High/Rising Edge'
                                False = 'Voltage Low/Falling Edge'

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

    def close_counter(self, scanner=False):
        """ Closes the counter or scanner and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             will be excecuted to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """
        if self.stop_gated_counter() < 0:
            return -1
        return self.close_gated_counter()

    def close_clock(self, scanner=False):
        """ Closes the clock and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             should be used to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """
        return 0

