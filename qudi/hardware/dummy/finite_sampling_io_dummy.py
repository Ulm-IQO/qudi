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
from qudi.interface.finite_sampling_io_interface import FiniteSamplingIOInterface
from qudi.interface.finite_sampling_io_interface import FiniteSamplingIOConstraints
from qudi.hardware.dummy.finite_sampling_input_dummy import SimulationMode
from qudi.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption
from qudi.util.enums import SamplingOutputMode


class FiniteSamplingIODummy(FiniteSamplingIOInterface):
    """
    ToDo: Document
    """

    _sample_rate_limits = ConfigOption(name='sample_rate_limits', default=(1, 1e6))
    _frame_size_limits = ConfigOption(name='frame_size_limits', default=(1, 1e9))
    _input_channel_units = ConfigOption(name='input_channel_units',
                                        default={'APD counts': 'c/s', 'Photodiode': 'V'})
    _output_channel_units = ConfigOption(name='output_channel_units',
                                         default={'Frequency': 'Hz', 'Voltage': 'V'})
    _default_output_mode = ConfigOption(name='default_output_mode',
                                        default='JUMP_LIST',
                                        constructor=lambda x: SamplingOutputMode[x.upper()])
    _simulation_mode = ConfigOption(name='simulation_mode',
                                    default='ODMR',
                                    constructor=lambda x: SimulationMode[x.upper()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()
        self._sample_rate = -1
        self._frame_size = -1
        self._active_output_channels = frozenset()
        self._active_input_channels = frozenset()
        self._output_mode = None
        self._constraints = None

        self.__start_time = 0.0
        self.__returned_samples = 0
        self.__elapsed_samples = 0
        self.__simulated_samples = None
        self.__frame_buffer = None

    def on_activate(self):
        # Create constraints object and perform sanity/type checking
        self._constraints = FiniteSamplingIOConstraints(
            supported_output_modes=frozenset(SamplingOutputMode),
            input_channel_units=self._input_channel_units,
            output_channel_units=self._output_channel_units,
            frame_size_limits=self._frame_size_limits,
            sample_rate_limits=self._sample_rate_limits
        )
        # Make sure the ConfigOptions have correct values and types
        # (ensured by FiniteSamplingOutputConstraints)
        self._sample_rate_limits = self._constraints.sample_rate_limits
        self._frame_size_limits = self._constraints.frame_size_limits
        self._input_channel_units = self._constraints.input_channel_units
        self._output_channel_units = self._constraints.output_channel_units
        if not self._constraints.output_mode_supported(self._default_output_mode):
            self._default_output_mode = next(iter(self._constraints.supported_output_modes))

        # initialize default settings
        self._sample_rate = self._constraints.max_sample_rate
        self._frame_size = 0
        self._active_input_channels = frozenset(self._constraints.input_channel_names)
        self._active_output_channels = frozenset(self._constraints.output_channel_names)
        self._output_mode = self._default_output_mode

        # process parameters
        self.__start_time = 0.0
        self.__returned_samples = 0
        self.__elapsed_samples = 0
        self.__simulated_samples = None
        self.__frame_buffer = None

    def on_deactivate(self):
        self.__simulated_samples = None

    @property
    def constraints(self):
        return self._constraints

    @property
    def active_channels(self):
        return self._active_input_channels, self._active_output_channels

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def output_mode(self):
        return self._output_mode

    @property
    def samples_in_buffer(self):
        with self._thread_lock:
            if self.module_state() == 'locked':
                elapsed_time = time.time() - self.__start_time
                self.__elapsed_samples = min(self._frame_size,
                                             int(elapsed_time * self._sample_rate))

            input_buffer_count = max(0, self.__elapsed_samples - self.__returned_samples)
            return input_buffer_count

    def set_output_mode(self, mode):
        assert self._constraints.output_mode_supported(mode), f'Invalid output mode "{mode}"'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set output mode. Sampling IO in progress.'
            if mode != self._output_mode:
                self._output_mode = mode
                self.__frame_buffer = None
                self.__elapsed_samples = 0

    def set_sample_rate(self, rate):
        sample_rate = float(rate)
        assert self._constraints.sample_rate_in_range(sample_rate)[0], \
            f'Sample rate "{sample_rate}Hz" to set is out of ' \
            f'bounds {self._constraints.sample_rate_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set sample rate. Sampling IO in progress.'
            self._sample_rate = sample_rate

    def set_active_channels(self, input_channels, output_channels):
        input_chnl_set = frozenset(input_channels)
        output_chnl_set = frozenset(output_channels)
        assert input_chnl_set.issubset(self._constraints.input_channel_names), \
            'Invalid input channels encountered to set active'
        assert output_chnl_set.issubset(self._constraints.output_channel_names), \
            'Invalid output channels encountered to set active'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set active channels. Sampling IO in progress.'
            self._active_input_channels = input_chnl_set
            self._active_output_channels = output_chnl_set

    def _set_frame_size(self, size):
        samples = int(round(size))
        assert self._constraints.frame_size_in_range(samples)[0], \
            f'frame size "{samples}" to set is out of bounds {self._constraints.frame_size_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set frame size. Sampling IO in progress.'
            if samples != self._frame_size:
                self._frame_size = samples
                self.__frame_buffer = None
                self.__elapsed_samples = 0
                self.__returned_samples = 0

    def set_frame_data(self, data):
        assert isinstance(data, dict) or (data is None)
        if data is not None:
            assert frozenset(data) == self._active_output_channels, \
                f'Must provide data for all active output channels: {self._active_output_channels}'
            if self._output_mode == SamplingOutputMode.JUMP_LIST:
                frame_size = len(next(iter(data.values())))
                assert all(len(d) == frame_size for d in data.values()), \
                    'Frame data arrays for all active output channels must be of equal length.'
            elif self._output_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert all(len(d) == 3 for d in data.values()), \
                    'EQUIDISTANT_SWEEP output mode requires value tuples of length 3 for each ' \
                    'active output channel.'
                frame_size = next(iter(data.values()))[-1]
                assert all(d[-1] == frame_size for d in data.values()), \
                    'Frame data arrays for all channels must be of equal length.'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set frame data. Sampling IO in progress.'
            if data is None:
                self._set_frame_size(0)
                self.__frame_buffer = None
            elif self._output_mode == SamplingOutputMode.JUMP_LIST:
                self._set_frame_size(frame_size)
                self.__frame_buffer = data.copy()
            elif self._output_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                self._set_frame_size(frame_size)
                self.__frame_buffer = {ch: np.linspace(*d) for ch, d in data.items()}

    def start_buffered_frame(self):
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to start sampling IO. Already in progress.'
            assert isinstance(self._simulation_mode, SimulationMode), 'Invalid simulation mode'
            assert self.__frame_buffer is not None, \
                'Unable to start sampling IO. No frame data has been set for output'
            self.module_state.lock()

            # ToDo: discriminate between different types of data
            if self._simulation_mode is SimulationMode.ODMR:
                self.__simulate_odmr(self._frame_size)
            elif self._simulation_mode is SimulationMode.RANDOM:
                self.__simulate_random(self._frame_size)

            self.__returned_samples = 0
            self.__elapsed_samples = 0
            self.__start_time = time.time()

    def stop_buffered_frame(self):
        with self._thread_lock:
            if self.module_state() == 'locked':
                elapsed_time = time.time() - self.__start_time
                self.__elapsed_samples = min(self._frame_size,
                                             int(elapsed_time * self._sample_rate))
                remaining_samples = self._frame_size - self.__elapsed_samples
                if remaining_samples > 0:
                    self.log.warning(
                        f'Buffered sample IO stopped before all samples have been read/written. '
                        f'{remaining_samples} samples remain unread/unwritten.'
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

    def get_frame(self, data=None):
        with self._thread_lock:
            if data is not None:
                self.set_frame_data(data)
            self.start_buffered_frame()
            data = self.get_buffered_samples(self._frame_size)
            self.stop_buffered_frame()
            return data

    def __simulate_random(self, length):
        self.__simulated_samples = {
            ch: np.random.rand(length) for ch in self._active_input_channels
        }

    def __simulate_odmr(self, length):
        if length < 3:
            self.__simulate_random(length)
            return
        gamma = 2
        data = dict()
        x = np.arange(length, dtype=np.float64)
        for ch in self._active_input_channels:
            offset = ((np.random.rand() - 0.5) * 0.05 + 1) * 200000
            pos = length / 2 + (np.random.rand() - 0.5) * length / 10
            amp = offset / 20
            noise = amp
            data[ch] = offset + (np.random.rand(length) - 0.5) * noise - amp * gamma ** 2 / (
                        (x - pos) ** 2 + gamma ** 2)
        self.__simulated_samples = data
