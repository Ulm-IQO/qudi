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

from core.base import Base
from interface.slow_counter_interface import SlowCounterInterface


class SlowCounterDummy(Base, SlowCounterInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'SlowCounterDummy'
    _modtype = 'hardware'
    # connectors
    _out = {'counter': 'SlowCounterInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        config = self.getConfiguration()

        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency = 100
            self.log.warning('No parameter "clock_frequency" configured in '
                    'Slow Counter Dummy, taking the default value of {0} Hz '
                    'instead.'.format(self._clock_frequency))

        if 'samples_number' in config.keys():
            self._samples_number = config['samples_number']
        else:
            self._samples_number = 10
            self.log.warning('No parameter "samples_number" configured in '
                    'Slow Counter Dummy, taking the default value of {0} '
                    'instead.'.format(self._samples_number))

        if 'photon_source2' in config.keys():
            self._photon_source2 = 1
        else:
            self._photon_source2 = None

        if 'count_distribution' in config.keys():
            self.dist = config['count_distribution']
        else:
            self.dist = 'dark_bright_gaussian'
            self.log.warning('No parameter "count_distribution" given in the '
                        'configuration for the Slow Counter Dummy. Possible '
                        'distributions are "dark_bright_gaussian", "uniform", '
                        '"exponential", "single_poisson", '
                        '"dark_bright_poisson" and "single_gaussian". Taking '
                        'the default distribution "{0}".'.format(self.dist))

        # possibilities are:
        # dark_bright_gaussian, uniform, exponential, single_poisson,
        # dark_bright_poisson, single_gaussian

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

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """
        pass

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
                       counter_channel=None,
                       photon_source=None,
                       counter_channel2=None,
                       photon_source2=None,
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

        count_data_1 = self._simulate_counts(samples)

        count_data = count_data_1

        if self._photon_source2 is not None:
            count_data_2 = self._simulate_counts(samples) + self.mean_signal
            count_data = np.array([count_data_1, count_data_2])

        time.sleep(1. / self._clock_frequency * samples)

        return count_data

    def _simulate_counts(self, samples=None):
        """ Simulate counts signal from an APD.  This can be called for each dummy counter channel.

        @param int samples: if defined, number of samples to read in one go

        @return float: the photon counts per second
        """

        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)

        timestep = 1. / self._clock_frequency * samples

        count_data = np.empty([samples], dtype=np.uint32)  # count data will be written here in the NumPy array

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

                count_data[i] = np.random.normal(self.mean_signal, self.noise_amplitude) * self.curr_state_b + \
                                   np.random.normal(self.mean_signal2, self.noise_amplitude) * (1-self.curr_state_b)

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

                count_data[i] = np.random.poisson(self.mean_signal)*self.curr_state_b + np.random.poisson(self.mean_signal2)*(1-self.curr_state_b)

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
