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

from qudi.core.module import Base
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.core.util.helpers import natural_sort


class FiniteSamplingDummy(Base):
    """
    ToDo: Document
    """

    _sample_rate_limits = ConfigOption(name='sample_rate_limits', default=(1, 1e6))
    _acquisition_limits = ConfigOption(name='acquisition_limits', default=(1, 1e9))
    _channel_units = ConfigOption(name='channel_units',
                                  default={'APD counts': 'c/s', 'Photodiode': 'V'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()
        self._sample_rate = -1
        self._number_of_samples = 0
        self._active_channels = frozenset()

        self.__start_time = 0.0

    def on_activate(self):
        # Check and refine ConfigOptions
        assert len(self._channel_units) > 0, 'Specify at least one channel with unit in config'
        assert all(isinstance(name, str) and name for name in self._channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(unit, str) for unit in self._channel_units.values()), \
            'Channel units must be strings'
        assert len(self._sample_rate_limits) == 2, 'Sample rate limits must be iterable of length 2'
        assert len(self._acquisition_limits) == 2, 'Acquisition limits must be iterable of length 2'
        assert all(lim > 0 for lim in self._sample_rate_limits), 'Sample rate limits must be > 0'
        assert all(lim > 0 for lim in self._acquisition_limits), 'Acquisition limits must be > 0'
        self._sample_rate_limits = (float(min(self._sample_rate_limits)),
                                    float(max(self._sample_rate_limits)))
        self._acquisition_limits = (int(round(min(self._acquisition_limits))),
                                    int(round(max(self._acquisition_limits))))

        # initialize default settings
        self._sample_rate = self._sample_rate_limits[1]
        self._acquisition_length = self._acquisition_limits[1]
        self._active_channels = frozenset(self._channel_units)

        # process parameters
        self.__start_time = 0.0

    def on_deactivate(self):
        pass

    @property
    def active_channels(self):
        return self._active_channels

    @property
    def channel_units(self):
        return self._channel_units.copy()

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def acquisition_length(self):
        return self._acquisition_length

    @property
    def available_samples(self):
        with self._thread_lock:


    def set_sample_rate(self, rate):
        sample_rate = float(rate)
        assert self._sample_rate_limits[0] <= sample_rate <= self._sample_rate_limits[1], \
            f'Sample rate "{sample_rate}Hz" to set is out of bounds {self._sample_rate_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set sample rate. Data acquisition in progress.'
            self._sample_rate = sample_rate

    def set_active_channels(self, channels):
        channel_set = frozenset(channels)
        assert channel_set.issubset(self._channel_units), \
            'Invalid channels encountered to set active'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set active channels. Data acquisition in progress.'
            self._active_channels = channel_set

    def set_acquisition_length(self, length):
        samples = int(round(length))
        assert self._acquisition_limits[0] <= samples <= self._acquisition_limits[1], \
            f'acquisition length "{samples}" to set is out of bounds {self._acquisition_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set acquisition length. Data acquisition in progress.'
            self._acquisition_length = samples

    def start_acquisition(self):
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to start data acquisition. Data acquisition already in progress.'
            self.module_state.lock()

