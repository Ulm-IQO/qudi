# -*- coding: utf-8 -*-

"""
ToDo: Document
This file contains a dummy hardware module for the

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

import time
import numpy as np
from enum import Enum
from qudi.core.module import Base
from qudi.interface.finite_sampling_input_interface import FiniteSamplingInputInterface
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption


class SimulationMode(Enum):
    RANDOM = 0
    ODMR = 1


class FiniteSamplingInputDummy(Base, FiniteSamplingInputInterface):
    """
    ToDo: Document
    """

    _sample_rate_limits = ConfigOption(name='sample_rate_limits', default=(1, 1e6))
    _frame_size_limits = ConfigOption(name='frame_size_limits', default=(1, 1e9))
    _channel_units = ConfigOption(name='channel_units',
                                  default={'APD counts': 'c/s', 'Photodiode': 'V'})
    _simulation_mode = ConfigOption(name='simulation_mode', default='ODMR')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()
        self._sample_rate = -1
        self._frame_size = -1
        self._active_channels = frozenset()

        self.__start_time = 0.0
        self.__returned_samples = 0
        self.__simulated_samples = None
        self.__constraints = dict()

    def on_activate(self):
        # Check and refine ConfigOptions
        assert len(self._channel_units) > 0, 'Specify at least one channel with unit in config'
        assert all(isinstance(name, str) and name for name in self._channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(unit, str) for unit in self._channel_units.values()), \
            'Channel units must be strings'
        assert len(self._sample_rate_limits) == 2, 'Sample rate limits must be iterable of length 2'
        assert len(self._frame_size_limits) == 2, 'Frame size limits must be iterable of length 2'
        assert all(lim > 0 for lim in self._sample_rate_limits), 'Sample rate limits must be > 0'
        assert all(lim > 0 for lim in self._frame_size_limits), 'Frame size limits must be > 0'
        self._simulation_mode = SimulationMode[self._simulation_mode.upper()]
        self._sample_rate_limits = (float(min(self._sample_rate_limits)),
                                    float(max(self._sample_rate_limits)))
        self._frame_size_limits = (int(round(min(self._frame_size_limits))),
                                    int(round(max(self._frame_size_limits))))

        # initialize default settings
        self._sample_rate = self._sample_rate_limits[1]
        self._frame_size = self._frame_size_limits[1]
        self._active_channels = frozenset(self._channel_units)
        self.__constraints = {'sample_rate_limits': self._sample_rate_limits,
                              'frame_size_limits': self._frame_size_limits,
                              'channel_units': self._channel_units.copy()}

        # process parameters
        self.__start_time = 0.0
        self.__returned_samples = 0
        self.__simulated_samples = None

    def on_deactivate(self):
        self.__simulated_samples = None

    @property
    def constraints(self):
        return self.__constraints.copy()

    @property
    def active_channels(self):
        return self._active_channels

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def samples_in_buffer(self):
        with self._thread_lock:
            if self.module_state() == 'locked':
                elapsed_time = time.time() - self.__start_time
                acquired_samples = min(self._frame_size,
                                       int(elapsed_time * self._sample_rate))
                return max(0, acquired_samples - self.__returned_samples)
            return 0

    def set_sample_rate(self, rate):
        sample_rate = float(rate)
        assert self._sample_rate_limits[0] <= sample_rate <= self._sample_rate_limits[1], \
            f'Sample rate "{sample_rate}Hz" to set is out of bounds {self._sample_rate_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set sample rate. Data acquisition in progress.'
            self._sample_rate = sample_rate

    def set_active_channels(self, channels):
        chnl_set = frozenset(channels)
        assert chnl_set.issubset(self._channel_units), \
            'Invalid channels encountered to set active'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set active channels. Data acquisition in progress.'
            self._active_channels = chnl_set

    def set_frame_size(self, size):
        samples = int(round(size))
        assert self._frame_size_limits[0] <= samples <= self._frame_size_limits[1], \
            f'frame size "{samples}" to set is out of bounds {self._frame_size_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set frame size. Data acquisition in progress.'
            self._frame_size = samples

    def start_buffered_acquisition(self):
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to start data acquisition. Data acquisition already in progress.'
            assert isinstance(self._simulation_mode, SimulationMode), 'Invalid simulation mode'
            self.module_state.lock()

            # ToDo: discriminate between different types of data
            if self._simulation_mode is SimulationMode.ODMR:
                self.__simulate_odmr(self._frame_size)
            elif self._simulation_mode is SimulationMode.RANDOM:
                self.__simulate_random(self._frame_size)

            self.__returned_samples = 0
            self.__start_time = time.time()

    def stop_buffered_acquisition(self):
        with self._thread_lock:
            if self.module_state() == 'locked':
                remaining_samples = self._frame_size - self.__returned_samples
                if remaining_samples > 0:
                    self.log.warning(
                        f'Buffered sample acquisition stopped before all samples have '
                        f'been read. {remaining_samples} remaining samples will be lost.'
                    )
                self.module_state.unlock()

    def get_buffered_samples(self, number_of_samples=None):
        with self._thread_lock:
            available_samples = self.samples_in_buffer
            if number_of_samples is None:
                number_of_samples = available_samples
            else:
                remaining_samples = self._frame_size - self.__returned_samples
                assert number_of_samples <= remaining_samples, \
                    f'Number of samples to read ({number_of_samples}) exceeds remaining samples ' \
                    f'in this frame ({remaining_samples})'

            # Return early if no samples are requested
            if number_of_samples < 1:
                return dict()

            # Wait until samples have been acquired if requesting more samples than in the buffer
            pending_samples = number_of_samples - available_samples
            if pending_samples > 0:
                time.sleep(pending_samples / self._sample_rate)
            # return data and increment sample counter
            data = {ch: samples[self.__returned_samples:self.__returned_samples + number_of_samples]
                    for ch, samples in self.__simulated_samples.items()}
            self.__returned_samples += number_of_samples
            return data

    def acquire_frame(self, frame_size=None):
        with self._thread_lock:
            if frame_size is None:
                buffered_frame_size = None
            else:
                buffered_frame_size = self._frame_size
                self.set_frame_size(frame_size)

            self.start_buffered_acquisition()
            data = self.get_buffered_samples()
            self.stop_buffered_acquisition()

            if buffered_frame_size is not None:
                self._frame_size = buffered_frame_size
            return data

    def __simulate_random(self, length):
        self.__simulated_samples = {
            ch: np.random.rand(length) for ch in self._channel_units if ch in self._active_channels
        }

    def __simulate_odmr(self, length):
        if length < 3:
            self.__simulate_random(length)
            return
        gamma = 2
        data = dict()
        x = np.arange(length, dtype=np.float64)
        for ch in self._channel_units:
            if ch in self._active_channels:
                pos = length / 2 + (np.random.rand() - 0.5) * length / 3
                offset = np.random.rand() * 1000
                amp = offset / 30
                noise = np.sqrt(amp)
                data[ch] = amp + (np.random.rand() - 0.5) * noise + amp * gamma ** 2 / (
                            (x - pos) ** 2 + gamma ** 2)
        self.__simulated_samples = data
