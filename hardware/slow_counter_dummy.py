# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware dummy for slow counting devices.

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

import random
import time

from core.module import Base, ConfigOption
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode


class SlowCounterDummy(Base, SlowCounterInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'SlowCounterDummy'
    _modtype = 'hardware'

    # config
    _clock_frequency = ConfigOption('clock_frequency', 100, missing='warn')
    _samples_number = ConfigOption('samples_number', 10, missing='warn')
    source_channels = ConfigOption('source_channels', 2, missing='warn')
    dist = ConfigOption('count_distribution', 'dark_bright_gaussian')

    # 'No parameter "count_distribution" given in the configuration for the'
    # 'Slow Counter Dummy. Possible distributions are "dark_bright_gaussian",'
    # '"uniform", "exponential", "single_poisson", "dark_bright_poisson"'
    # 'and "single_gaussian".'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # parameters
        if self.dist == 'dark_bright_poisson':
            self.mean_signal = 250
            self.contrast = 0.2
        else:
            self.mean_signal = 260 * 1000
            self.contrast = 0.3

        self.mean_signal2 = self.mean_signal - self.contrast * self.mean_signal
        self.noise_amplitude = self.mean_signal * 0.1

        self.life_time_bright = 0.08  # 80 millisecond
        self.life_time_dark = 0.04  # 40 milliseconds

        # needed for the life time simulation
        self.current_dec_time = self.life_time_bright
        self.curr_state_b = True
        self.total_time = 0.0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.log.warning('slowcounterdummy>deactivation')

    def get_constraints(self):
        """ Return a constraints class for the slow counter."""
        constraints = SlowCounterConstraints()
        constraints.min_count_frequency = 5e-5
        constraints.max_count_frequency = 5e5
        constraints.counting_mode = [
            CountingMode.CONTINUOUS,
            CountingMode.GATED,
            CountingMode.FINITE_GATED]

        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """

        if clock_frequency is not None:
            self._clock_frequency = float(clock_frequency)
        self.log.warning('slowcounterdummy>set_up_clock')
        time.sleep(0.1)
        return 0

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter

        @return int: error code (0:OK, -1:error)
        """

        self.log.warning('slowcounterdummy>set_up_counter')
        time.sleep(0.1)
        return 0

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return float: the photon counts per second
        """
        count_data = np.array(
            [self._simulate_counts(samples) + i * self.mean_signal
                for i, ch in enumerate(self.get_counter_channels())]
            )

        time.sleep(1 / self._clock_frequency * samples)
        return count_data

    def get_counter_channels(self):
        """ Returns the list of counter channel names.
        @return tuple(str): channel names
        Most methods calling this might just care about the number of channels, though.
        """
        return ['Ctr{0}'.format(i) for i in range(self.source_channels)]

    def _simulate_counts(self, samples=None):
        """ Simulate counts signal from an APD.  This can be called for each dummy counter channel.

        @param int samples: if defined, number of samples to read in one go

        @return float: the photon counts per second
        """

        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)

        timestep = 1 / self._clock_frequency * samples

        # count data will be written here in the NumPy array
        count_data = np.empty([samples], dtype=np.uint32)

        for i in range(samples):
            if self.dist == 'single_gaussian':
                count_data[i] = np.random.normal(self.mean_signal, self.noise_amplitude / 2)
            elif self.dist == 'dark_bright_gaussian':
                self.total_time = self.total_time + timestep
                if self.total_time > self.current_dec_time:
                    if self.curr_state_b:
                        self.curr_state_b = False
                        self.current_dec_time = np.random.exponential(self.life_time_dark)
                        count_data[i] = np.random.poisson(self.mean_signal)
                    else:
                        self.curr_state_b = True
                        self.current_dec_time = np.random.exponential(self.life_time_bright)
                    self.total_time = 0.0

                count_data[i] = (np.random.normal(self.mean_signal, self.noise_amplitude) * self.curr_state_b
                                + np.random.normal(self.mean_signal2, self.noise_amplitude) * (1-self.curr_state_b))

            elif self.dist == 'uniform':
                count_data[i] = self.mean_signal + random.uniform(-self.noise_amplitude / 2, self.noise_amplitude / 2)

            elif self.dist == 'exponential':
                count_data[i] = np.random.exponential(self.mean_signal)

            elif self.dist == 'single_poisson':
                count_data[i] = np.random.poisson(self.mean_signal)

            elif self.dist == 'dark_bright_poisson':
                self.total_time = self.total_time + timestep

                if self.total_time > self.current_dec_time:
                    if self.curr_state_b:
                        self.curr_state_b = False
                        self.current_dec_time = np.random.exponential(self.life_time_dark)
                        count_data[i] = np.random.poisson(self.mean_signal)
                    else:
                        self.curr_state_b = True
                        self.current_dec_time = np.random.exponential(self.life_time_bright)
                    self.total_time = 0.0

                count_data[i] = (np.random.poisson(self.mean_signal) * self.curr_state_b
                                + np.random.poisson(self.mean_signal2) * (1-self.curr_state_b))
            else:
                # make uniform as default
                count_data[0][i] = self.mean_signal + random.uniform(-self.noise_amplitude/2, self.noise_amplitude/2)

        return count_data

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.log.warning('slowcounterdummy>close_counter')
        return 0

    def close_clock(self,power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.log.warning('slowcounterdummy>close_clock')
        return 0
