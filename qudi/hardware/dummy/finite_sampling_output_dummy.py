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
from PySide2.QtCore import QTimer
from qudi.interface.finite_sampling_output_interface import FiniteSamplingOutputInterface
from qudi.interface.finite_sampling_output_interface import SamplingOutputMode
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption


class FiniteSamplingOutputDummy(FiniteSamplingOutputInterface):
    """
    ToDo: Document
    """

    _sample_rate_limits = ConfigOption(name='sample_rate_limits', default=(1, 1e6))
    _frame_size_limits = ConfigOption(name='frame_size_limits', default=(1, 1e9))
    _channel_units = ConfigOption(name='channel_units',
                                  default={'Frequency': 'Hz', 'Voltage': 'V'})
    _output_mode = ConfigOption(name='output_mode',
                                default='JUMP_LIST',
                                constructor=lambda x: SamplingOutputMode[x])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()
        self._sample_rate = -1
        self._frame_size = -1
        self._active_channels = frozenset()

        self.__start_time = 0.0
        self.__emitted_samples = 0
        self.__frame_buffer = None
        self.__constraints = dict()

    def on_activate(self):
        # Check and refine ConfigOptions
        assert len(self._channel_units) > 0, 'Specify at least one channel with unit in config'
        assert all(isinstance(name, str) and name for name in self._channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(unit, str) for unit in self._channel_units.values()), \
            'Channel units must be strings'
        assert len(self._sample_rate_limits) == 2, 'Sample rate limits must be iterable of length 2'
        assert len(self._frame_size_limits) == 2, 'Acquisition limits must be iterable of length 2'
        assert all(lim > 0 for lim in self._sample_rate_limits), 'Sample rate limits must be > 0'
        assert all(lim > 0 for lim in self._frame_size_limits), 'Acquisition limits must be > 0'
        self._sample_rate_limits = (float(min(self._sample_rate_limits)),
                                    float(max(self._sample_rate_limits)))
        self._frame_size_limits = (int(round(min(self._frame_size_limits))),
                                   int(round(max(self._frame_size_limits))))

        # initialize default settings
        self._sample_rate = self._sample_rate_limits[1]
        self._frame_size = self._frame_size_limits[1]
        self._active_channels = frozenset(self._channel_units)
        self.__constraints = {
            'sample_rate_limits': self._sample_rate_limits,
            'frame_size_limits': self._frame_size_limits,
            'channel_units': self._channel_units.copy(),
            'output_modes': frozenset(SamplingOutputMode)
        }

        # process parameters
        self.__start_time = 0.0
        self.__emitted_samples = 0
        self.__frame_buffer = None

    def on_deactivate(self):
        self.__frame_buffer = None

    @property
    def constraints(self):
        return self.__constraints.copy()

    @property
    def active_channels(self):
        with self._thread_lock:
            return self._active_channels

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def frame_size(self):
        self._frame_size

    @property
    def output_mode(self):
        return self._output_mode

    @property
    def samples_in_buffer(self):
        with self._thread_lock:
            if self.module_state() == 'locked':
                elapsed_time = time.time() - self.__start_time
                emitted_samples = min(self._frame_size, int(elapsed_time * self._sample_rate))
                return max(0, emitted_samples - self.__emitted_samples)
            return 0

    def set_sample_rate(self, rate):
        sample_rate = float(rate)
        assert self._sample_rate_limits[0] <= sample_rate <= self._sample_rate_limits[1], \
            f'Sample rate "{sample_rate}Hz" to set is out of bounds {self._sample_rate_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set sample rate. Sampling output in progress.'
            self._sample_rate = sample_rate

    def set_active_channels(self, channels):
        chnl_set = frozenset(channels)
        assert chnl_set.issubset(self._channel_units), \
            'Invalid channels encountered to set active'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set active channels. Sampling output in progress.'
            if (self.__frame_buffer is not None) and (self._active_channels != chnl_set):
                self.__frame_buffer = None
            self._active_channels = chnl_set

    def set_frame_data(self, data):
        assert isinstance(data, dict) or (data is None)
        if data is not None:
            assert frozenset(data) == self._active_channels, \
                f'Must provide data for all active channels: {self._active_channels}'
            if self._output_mode == SamplingOutputMode.JUMP_LIST:
                frame_size = len(next(iter(data.values())))
                assert all(len(d) == frame_size for d in data.values()), \
                    'Frame data arrays for all channels must be of equal length.'
            elif self._output_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert all(len(d) == 3 for d in data.values()), \
                    'EQUIDISTANT_SWEEP output mode requires value tuples of length 3 for each ' \
                    'active channel.'
                frame_size = next(iter(data.values()))[-1]
                assert all(d[-1] == frame_size for d in data.values()), \
                    'Frame data arrays for all channels must be of equal length.'
            assert self._frame_size_limits[0] <= frame_size <= self._frame_size_limits[1], \
                f'Frame size "{frame_size}" to set is out of bounds {self._frame_size_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set frame data. Sampling output in progress.'
            if data is None:
                self._frame_size = 0
                self.__frame_buffer = None
            elif self._output_mode == SamplingOutputMode.JUMP_LIST:
                self._frame_size = frame_size
                self.__frame_buffer = data.copy()
            elif self._output_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                self._frame_size = frame_size
                self.__frame_buffer = {ch: np.linspace(*d) for ch, d in data.items()}

    def set_output_mode(self, mode):
        assert mode in self.__constraints['output_modes'], f'Invalid output mode "{mode}"'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set output mode. Sampling output in progress.'
            self.__frame_buffer = None
            self._output_mode = mode

    def start_buffered_output(self):
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to start sampling output. Sampling output already in progress.'
            assert self.__frame_buffer is not None, \
                'Unable to start sampling output. No frame data set.'
            self.module_state.lock()

            self.__emitted_samples = 0
            total_time = 1000 * (self._frame_size / self._sample_rate)
            self.__start_time = time.time()
            QTimer.singleShot(total_time, self.stop_buffered_output)

    def stop_buffered_output(self):
        with self._thread_lock:
            if self.module_state() == 'locked':
                remaining_samples = self._frame_size - self.__emitted_samples
                if remaining_samples > 0:
                    self.log.warning(
                        f'Buffered sampling output stopped before all samples have '
                        f'been emitted. {remaining_samples} remaining samples will be discarded.'
                    )
                self.__frame_buffer = None
                self.module_state.unlock()

    def emit_samples(self, data):
        with self._thread_lock:
            buffered_frame_size = self._frame_size
            self.set_frame_data(data)

            self.start_buffered_acquisition()
            time.sleep(self._frame_size / self._sample_rate)
            self.stop_buffered_acquisition()

            self._frame_size = buffered_frame_size
