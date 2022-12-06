# -*- coding: utf-8 -*-
"""
A hardware module for communicating with the Swabian Instruments fast counter FPGA.
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
Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at thes
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
import time
import okfrontpanel

from interface.slow_counter_interface import SlowCounterInterface, SlowCounterConstraints, CountingMode
import numpy as np
import ctypes as ct
import TimeTagger as TimeTagger
from core.module import Base
from core.configoption import ConfigOption


class TimeTaggerSlowCounter(Base, SlowCounterInterface):
    """ Hardware class to controls a Time Tagger from Swabian Instruments.
    Example config for copy-paste:
    fastcounter_timetagger:
        module.Class: 'swabian_instruments.TimeTagger_ungated_Fastcounter.TimeTaggerFastCounter'
        network: True
        address: '134.60.31.152:5353'
        channel_apd: 2
        timetagger_serial: '1924000QHS'
        timetagger_resolution: 'Standard'
    """
    _network = ConfigOption('network', missing='error')
    _address = ConfigOption('address', missing='error')
    _channel_apd = ConfigOption('channel_apd', missing='error')
    _timetagger_serial = ConfigOption('timetagger_serial', 'Standard', missing='warn')
    _timetagger_resolution = ConfigOption('timetagger_resolution', 'Standard', missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._record_length = int(4000)

        if self._network:
            try:
                self.timetagger = TimeTagger.createTimeTaggerNetwork(address=self._address)
                self.timetagger.setTriggerLevel(2, 1)
            except RuntimeError:
                self.log.error("TimeTagger can't be accessed. Check if it's turned on and if it's properly connected to" 
                              "to the network")
        else:
            self.timetagger = TimeTagger.createTimeTagger(self._timetagger_serial)

    def on_deactivate(self):
        """ Initialisation performed during deactivation of the module.
        """
        try:
            if self.module_state() == 'locked':
                self.histogram.stop()
                self.histogram_control.stop()

            self.histogram.clear()
            self.histogram_control.clear()

            TimeTagger.freeTimeTagger(self.timetagger)
            del self.timetagger, self.histogram, self.histogram_control
        except AttributeError:
            TimeTagger.freeTimeTagger(self.timetagger)
            del self.timetagger


    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.
        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.
         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).
                    NO OTHER KEYS SHOULD BE INVENTED!
        If you are not sure about the meaning, look in other hardware files tomy
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.
        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}
        Only the key 'hardware_binwidth_list' differs, since they
        contain the list of possible binwidths.
        If the constraints cannot be set in the fast counting hardware then
        write just zero to each key of the generic dicts.
        Note that there is a difference between float input (0.0) and
        integer input (0), because some logic modules might rely on that
        distinction.
        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """

        constraints = SlowCounterConstraints()
        constraints.max_detectors = 1
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 1e3
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        @return int: error code (0:OK, -1:error)
        """
        self.clock_frequency = clock_frequency
        return 0

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

        # Bin width is measured in ps
        self.counter_binwidth = 20e-3 *1/1e-12
        # n_values is chose such that the whole buffer contains data of 10s equaling a 0.1Hz countrate
        if counter_buffer:
            self.n_max_values = counter_buffer
        else:
            self.n_max_values = 5000
        try:
            self.counter = TimeTagger.Counter(self.timetagger, [self._channel_apd], self.counter_binwidth, self.n_max_values)
            return 0
        except Exception as e:
            self.log.error(e)
            return -1

    def get_counter(self, samples=1):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array((n, uint32)): the photon counts per second for n channels
        """

        if samples > self.n_max_values:
            self.log.warning("The TimeTagger is programmed to not return more than 1e4 samples for cts/s")

        counter_data = self.counter.getDataNormalized(rolling=True)
        time.sleep(1/self.clock_frequency)
        return counter_data[:, -samples:]

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        return [self._channel_apd]

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0