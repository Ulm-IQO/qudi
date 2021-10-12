# -*- coding: utf-8 -*-

"""
This file contains the qudi hardware module to use a National Instruments X-series card as finite sampled
signal input and output device.

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

import ctypes
import numpy as np
import nidaqmx as ni
from nidaqmx._lib import lib_importer  # Due to NIDAQmx C-API bug needed to bypass property getter
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader
from nidaqmx.stream_writers import AnalogMultiChannelWriter

from qudi.core.configoption import ConfigOption
from qudi.util.helpers import natural_sort
from qudi.interface.finite_sampling_io_interface import FiniteSamplingIOInterface, FiniteSamplingIOConstraints
from qudi.util.enums import SamplingOutputMode
from qudi.util.mutex import RecursiveMutex
import time


class NIXSeriesFiniteSamplingIO(FiniteSamplingIOInterface):
    """
    A National Instruments device that can #TODO Document

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    Example config for copy-paste:

    ni_finite_sampling_io:
        module.Class: 'ni_x_series.ni_x_series_finite_sampling_io.NIXSeriesFiniteSamplingIO'
        device_name: 'Dev1'
        input_channel_units:  # optional
            'PFI8': 'c/s'
            'ai0': 'V'
            'ai1': 'V'
        output_channel_units:
            'ao0': 'V'
            'ao1': 'V'
        adc_voltage_ranges:
            ai0: [-10, 10]  # optional
            ai1: [-10, 10]  # optional
        output_voltage_ranges:
            ao0: [-5, 5]
            ao1: [-10, 10]
        #TODO output range, also limits need to be included in constraints
        frame_size_limits: [1, 1e9]  # optional #TODO actual HW constraint?
        output_mode: 'JUMP_LIST' # optional, must be name of SamplingOutputMode
        read_write_timeout: 10  # optional
        sample_clock_output: '/Dev1/PFI15' # optional

    """

    # config options
    _device_name = ConfigOption(name='device_name', default='Dev1', missing='warn')
    _max_channel_samples_buffer = ConfigOption(
        'max_channel_samples_buffer', default=25e6, missing='info')
    _rw_timeout = ConfigOption('read_write_timeout', default=10, missing='nothing')

    # Finite Sampling #TODO Frame size hardware limits?
    _frame_size_limits = ConfigOption(name='frame_size_limits', default=(1, 1e9))
    _input_channel_units = ConfigOption(name='input_channel_units',
                                        missing='error')
    _output_channel_units = ConfigOption(name='output_channel_units',
                                         default={'ao{}'.format(channel_index): 'V' for channel_index in range(0, 4)},
                                         missing='error')
    _default_output_mode = ConfigOption(name='output_mode', default='JUMP_LIST',
                                        constructor=lambda x: SamplingOutputMode[x.upper()], missing='nothing')

    _physical_sample_clock_output = ConfigOption(name='sample_clock_output',
                                                 default=None)

    # Hardcoded data type
    __data_type = np.float64

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NIDAQmx device handle
        self._device_handle = None
        # Task handles for NIDAQmx tasks
        self._di_task_handles = list()
        self._ai_task_handle = None
        self._clk_task_handle = None
        self._ao_task_handle = None
        # nidaqmx stream reader instances to help with data acquisition
        self._di_readers = list()
        self._ai_reader = None
        self._ao_writer = None

        # Internal settings
        self.__output_mode = None
        self.__sample_rate = -1.0

        # Internal settings
        self.__frame_size = -1
        self.__frame_buffer = -1

        # unread samples buffer
        self.__unread_samples_buffer = None
        self.__number_of_unread_samples = 0

        # List of all available counters and terminals for this device
        self.__all_counters = tuple()
        self.__all_digital_terminals = tuple()
        self.__all_analog_in_terminals = tuple()
        self.__all_analog_out_terminals = tuple()

        # currently active channels
        self.__active_channels = dict(di_channels=frozenset(), ai_channels=frozenset(), ao_channels=frozenset())

        # Stored hardware constraints
        self._constraints = None
        self._thread_lock = RecursiveMutex()
        return

    def on_activate(self):
        """
        Starts up the NI-card and performs sanity checks.
        """
        self._input_channel_units = {self._extract_terminal(key): value
                                     for key, value in self._input_channel_units.items()}
        self._output_channel_units = {self._extract_terminal(key): value
                                      for key, value in self._output_channel_units.items()}

        # Check if device is connected and set device to use
        dev_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in set(dev.lower() for dev in dev_names):
            raise ValueError(
                f'Device name "{self._device_name}" not found in list of connected devices: '
                f'{dev_names}\nActivation of NIXSeriesFiniteSamplingIO failed!'
            )
        for dev in dev_names:
            if dev.lower() == self._device_name.lower():
                self._device_name = dev
                break
        self._device_handle = ni.system.Device(self._device_name)

        self.__all_counters = tuple(
            self._extract_terminal(ctr) for ctr in self._device_handle.co_physical_chans.channel_names if
            'ctr' in ctr.lower())
        self.__all_digital_terminals = tuple(
            self._extract_terminal(term) for term in self._device_handle.terminals if 'pfi' in term.lower())
        self.__all_analog_in_terminals = tuple(
            self._extract_terminal(term) for term in self._device_handle.ai_physical_chans.channel_names)
        self.__all_analog_out_terminals = tuple(
            self._extract_terminal(term) for term in self._device_handle.ao_physical_chans.channel_names)

        # Get digital input terminals from _input_channel_units
        digital_sources = tuple(src for src in self._input_channel_units if 'pfi' in src)

        if digital_sources:
            source_set = set(digital_sources)
            invalid_sources = source_set.difference(set(self.__all_digital_terminals))
            if invalid_sources:
                self.log.error(
                    'Invalid digital source terminals encountered. Following sources will '
                    'be ignored:\n  {0}\nValid digital input terminals are:\n  {1}'
                    ''.format(', '.join(natural_sort(invalid_sources)),
                              ', '.join(self.__all_digital_terminals)))
            digital_sources = natural_sort(source_set.difference(invalid_sources))

        analog_sources = tuple(src for src in self._input_channel_units if 'ai' in src)

        # Get analog input channels from _input_channel_units
        if analog_sources:
            source_set = set(analog_sources)
            invalid_sources = source_set.difference(set(self.__all_analog_in_terminals))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(self.__all_analog_in_terminals)))
            analog_sources = natural_sort(source_set.difference(invalid_sources))

        # Get analog output channels from _output_channel_units
        analog_outputs = tuple(src for src in self._output_channel_units if 'ao' in src)

        if analog_outputs:
            source_set = set(analog_outputs)
            invalid_sources = source_set.difference(set(self.__all_analog_out_terminals))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(self.__all_analog_in_terminals)))
            analog_outputs = natural_sort(source_set.difference(invalid_sources))

        # Check if all input channels fit in the device
        if len(digital_sources) > 3:  # TODO is it just 2, since a clock is needed for a scanner?
            raise ValueError(
                'Too many digital channels specified. Maximum number of digital channels is 3.'
            )
        if len(analog_sources) > 16:
            raise ValueError(
                'Too many analog channels specified. Maximum number of analog channels is 16.'
            )

        # If there are any invalid inputs or outputs specified, raise an error
        defined_channel_set = set.union(set(self._input_channel_units), set(self._output_channel_units))
        detected_channel_set = set.union(set(analog_sources),
                                         set(digital_sources),
                                         set(analog_outputs))
        invalid_channels = set.difference(defined_channel_set, detected_channel_set)

        if invalid_channels:
            raise ValueError(
                f'The channels "{", ".join(invalid_channels)}", specified in the config, were not recognized.'
            )

        # Check Physical clock output if specified
        if self._physical_sample_clock_output is not None:
            self._physical_sample_clock_output = self._extract_terminal(self._physical_sample_clock_output)
            assert self._physical_sample_clock_output in self.__all_digital_terminals, \
                f'Physical sample clock terminal specified in config is invalid'

        # Get correct sampling frequency limits based on config specified channels
        if analog_sources and len(analog_sources) > 1:  # Probably "Slowest" case
            sample_rate_limits = (
                max(self._device_handle.ai_min_rate, self._device_handle.ao_min_rate),
                min(self._device_handle.ai_max_multi_chan_rate, self._device_handle.ao_max_rate)
            )
        elif analog_sources and len(analog_sources) == 1:  # Potentially faster than ai multi channel
            sample_rate_limits = (
                max(self._device_handle.ai_min_rate, self._device_handle.ao_min_rate),
                min(self._device_handle.ai_max_single_chan_rate, self._device_handle.ao_max_rate)
            )
        else:  # Only ao and di, therefore probably the fastest possible
            sample_rate_limits = (
                self._device_handle.ao_min_rate,
                min(self._device_handle.ao_max_rate, self._device_handle.ci_max_timebase)
            )

        # Create constraints
        self._constraints = FiniteSamplingIOConstraints(
            supported_output_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP),
            input_channel_units=self._input_channel_units,
            output_channel_units=self._output_channel_units,
            frame_size_limits=self._frame_size_limits,
            sample_rate_limits=sample_rate_limits
        )

        assert self._constraints.output_mode_supported(self._default_output_mode), \
            f'Config output "{self._default_output_mode}" mode not supported'

        self.__output_mode = self._default_output_mode
        self.__frame_size = 0
        return

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.terminate_all_tasks()
        # Free memory if possible while module is inactive
        self.__frame_buffer = np.empty(0, dtype=self.__data_type)
        return

    @property
    def constraints(self):
        """
        @return Finite sampling constraints
        """
        return self._constraints

    @property
    def active_channels(self):
        """ Names of all currently active input and output channels.

        @return (frozenset, frozenset): active input channels, active output channels
        """
        return self.__active_channels['di_channels'].union(self.__active_channels['ai_channels']), \
               self.__active_channels['ao_channels']

    def set_active_channels(self, input_channels, output_channels):
        """ Will set the currently active input and output channels.
        All other channels will be deactivated.

        @param iterable(str) input_channels: Iterable of input channel names to set active
        @param iterable(str) output_channels: Iterable of output channel names to set active
        """

        assert hasattr(input_channels, '__iter__') and not isinstance(input_channels, str), \
            f'Given input channels {input_channels} are not iterable'

        assert hasattr(output_channels, '__iter__') and not isinstance(output_channels, str), \
            f'Given output channels {output_channels} are not iterable'

        assert not self.is_running, \
            'Unable to change active channels while IO is running. New settings ignored.'

        input_channels = tuple(self._extract_terminal(channel) for channel in input_channels)
        output_channels = tuple(self._extract_terminal(channel) for channel in output_channels)

        assert set(input_channels).issubset(set(self._constraints.input_channel_names)), \
            f'Trying to set invalid input channels "' \
            f'{set(input_channels).difference(set(self._constraints.input_channel_names))}" not defined in config '

        assert set(output_channels).issubset(set(self._constraints.output_channel_names)), \
            f'Trying to set invalid input channels "' \
            f'{set(output_channels).difference(set(self._constraints.output_channel_names))}" not defined in config '

        di_channels, ai_channels = self._extract_ai_di_from_input_channels(input_channels)

        with self._thread_lock:
            self.__active_channels['di_channels'], self.__active_channels['ai_channels'] \
                = frozenset(di_channels), frozenset(ai_channels)

            self.__active_channels['ao_channels'] = frozenset(output_channels)

    @property
    def sample_rate(self):
        """ The sample rate (in Hz) at which the samples will be emitted.

        @return float: The current sample rate in Hz
        """
        return self.__sample_rate

    def set_sample_rate(self, rate):
        """ Sets the sample rate to a new value.

        @param float rate: The sample rate to set
        """
        assert not self.is_running, \
            'Unable to set sample rate while IO is running. New settings ignored.'
        in_range_flag, rate_val = self._constraints.sample_rate_in_range(rate)
        min_val, max_val = self._constraints.sample_rate_limits
        if not in_range_flag:
            self.log.warning(
                f'Sample rate requested ({rate:.3e}Hz) is out of bounds.'
                f'Please choose a value between {min_val:.3e}Hz and {max_val:.3e}Hz.'
                f'Value will be clipped to {rate_val:.3e}Hz.')
        with self._thread_lock:
            self.__sample_rate = float(rate_val)

    def set_output_mode(self, mode):
        """ Setter for the current output mode.

        @param SamplingOutputMode mode: The output mode to set as SamplingOutputMode Enum
        """
        assert not self.is_running, \
            'Unable to set output mode while IO is running. New settings ignored.'
        assert self._constraints.output_mode_supported(mode), f'Output mode {mode} not supported'
        # TODO: in case of assertion error, set output mode to SamplingOutputMode.INVALID?
        with self._thread_lock:
            self.__output_mode = mode

    @property
    def output_mode(self):
        """ Currently set output mode.

        @return SamplingOutputMode: Enum representing the currently active output mode
        """
        return self.__output_mode

    @property
    def samples_in_buffer(self):
        """ Current number of acquired but unread samples per channel in the input buffer.

        @return int: Unread samples in input buffer
        """
        if not self.is_running:
            return 0

        if self._ai_task_handle is None:
            return self._di_task_handles[0].in_stream.avail_samp_per_chan
        else:
            return self._ai_task_handle.in_stream.avail_samp_per_chan

    @property
    def frame_size(self):
        """ Currently set number of samples per channel to emit for each data frame.

        @return int: Number of samples per frame
        """
        return self.__frame_size

    def _set_frame_size(self, size):
        samples_per_channel = int(round(size))  # TODO Warn if not integer
        assert self._constraints.frame_size_in_range(samples_per_channel)[0], f'Frame size "{size}" is out of range'
        assert not self.is_running, f'Module is running. Cannot set frame size'

        with self._thread_lock:
            self.__frame_size = samples_per_channel
            self.__frame_buffer = None

    def set_frame_data(self, data):
        """ Fills the frame buffer for the next data frame to be emitted. Data must be a dict
        containing exactly all active channels as keys with corresponding sample data as values.

        If <output_mode> is SamplingOutputMode.JUMP_LIST, the values must be 1D numpy.ndarrays
        containing the entire data frame.
        If <output_mode> is SamplingOutputMode.EQUIDISTANT_SWEEP, the values must be iterables of
        length 3 representing the entire data frame to be constructed with numpy.linspace(),
        i.e. (start, stop, steps).

        Calling this method will alter read-only property <frame_size>

        @param dict data: The frame data (values) to be set for all active output channels (keys)
        """
        assert data is None or isinstance(data, dict), f'Wrong arguments passed to set_frame_data,' \
                                                       f'expected dict and got {type(data)}'

        assert not self.is_running, f'IO is running. Can not set frame data'

        active_output_channels_set = self.active_channels[1]

        if data is not None:
            # assure dict keys are striped from device name and are lower case
            data = {self._extract_terminal(ch): value for ch, value in data.items()}
            # Check for invalid keys
            assert not set(data).difference(active_output_channels_set), \
                f'Invalid keys in data {*set(data).difference(active_output_channels_set),} '
            # Check if all active channels are in data
            assert set(data) == active_output_channels_set, f'Keys of data {*data,} do not match active' \
                                                            f'channels {*active_output_channels_set,}'

            # set frame size
            if self.output_mode == SamplingOutputMode.JUMP_LIST:
                frame_size = len(next(iter(data.values())))
                assert all(isinstance(d, np.ndarray) and len(d.shape) == 1 for d in data.values()), \
                    f'Data values are no 1D numpy.ndarrays'
                assert all(len(d) == frame_size for d in data.values()), f'Length of data values not the same'
            elif self.output_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert all(len(tup) == 3 and isinstance(tup, tuple) for tup in data.values()), \
                    f'EQUIDISTANT_SWEEP output mode requires value tuples of length 3 for each output channel'
                assert all(isinstance(tup[-1], int) for tup in data.values()), \
                    f'Linspace number of points not integer'
                frame_size = next(iter(data.values()))[-1]
            else:
                frame_size = 0

        with self._thread_lock:
            self._set_frame_size(frame_size)
            # set frame buffer
            if data is not None:
                if self.output_mode == SamplingOutputMode.JUMP_LIST:
                    self.__frame_buffer = {output_ch: jump_list for output_ch, jump_list in data.items()}
                elif self.output_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                    self.__frame_buffer = {output_ch: np.linspace(*tup) for output_ch, tup in data.items()}
            if data is None:
                self._set_frame_size(0)  # Sets frame buffer to None

    def start_buffered_frame(self):
        """ Will start the input and output of the previously set data frame in a non-blocking way.
        Must return immediately and not wait for the frame to finish.

        Must raise exception if frame output can not be started.
        """

        assert self._constraints.sample_rate_in_range(self.sample_rate)[0],\
            f'Cannot start frame as sample rate {self.sample_rate:.2g}Hz not valid'
        assert self.frame_size != 0, f'No frame data set, can not start buffered frame'
        assert not self.is_running, f'Frame IO already running. Can not start'

        assert self.active_channels[1] == set(self.__frame_buffer), \
            f'Channels in active channels and frame buffer do not coincide'

        self.module_state.lock()

        # # set up all tasks
        if self._init_sample_clock() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Sample clock initialization failed; all tasks terminated')

        if self._init_digital_tasks() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Counter task initialization failed; all tasks terminated')

        if self._init_analog_in_task() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Analog in task initialization failed; all tasks terminated')

        if self._init_analog_out_task() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Analog out task initialization failed; all tasks terminated')

        output_data = np.ndarray((len(self.active_channels[1]), self.frame_size))

        self.__number_of_unread_samples = self.frame_size  # TODO thread lock? When to use?

        for num, output_channel in enumerate(self.active_channels[1]):
            output_data[num] = self.__frame_buffer[output_channel]

        try:
            self._ao_writer.write_many_sample(output_data)
        except ni.DaqError:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise

        if self._ao_task_handle is not None:
            try:
                self._ao_task_handle.start()
            except ni.DaqError:
                self.terminate_all_tasks()
                self.module_state.unlock()
                raise

        if self._ai_task_handle is not None:
            try:
                self._ai_task_handle.start()
            except ni.DaqError:
                self.terminate_all_tasks()
                self.module_state.unlock()
                raise

        if len(self._di_task_handles) > 0:
            try:
                for di_task in self._di_task_handles:
                    di_task.start()
            except ni.DaqError:
                self.terminate_all_tasks()
                self.module_state.unlock()
                raise

        try:
            self._clk_task_handle.start()
        except ni.DaqError:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise

    def stop_buffered_frame(self):
        """ Will abort the currently running data frame input and output.
        Will return AFTER the io has been terminated without waiting for the frame to finish
        (if possible).

        After the io operation has been stopped, the output frame buffer will keep its state and
        can be re-run or overwritten by calling <set_frame_data>.
        The input frame buffer will also stay and can be emptied by reading the available samples.

        Must NOT raise exceptions if no frame output is running.
        """
        if self.is_running:
            with self._thread_lock:
                self.__unread_samples_buffer = self.get_buffered_samples()
                self.__number_of_unread_samples = 0

            self.terminate_all_tasks()
            self.module_state.unlock()

    def get_buffered_samples(self, number_of_samples=None):
        """ Returns a chunk of the current data frame for all active input channels read from the
        input frame buffer.
        If parameter <number_of_samples> is omitted, this method will return the currently
        available samples within the input frame buffer (i.e. the value of property
        <samples_in_buffer>).
        If <number_of_samples> is exceeding the currently available samples in the frame buffer,
        this method will block until the requested number of samples is available.
        If the explicitly requested number of samples is exceeding the number of samples pending
        for acquisition in the rest of this frame, raise an exception.

        Samples that have been already returned from an earlier call to this method are not
        available anymore and can be considered discarded by the hardware. So this method is
        effectively decreasing the value of property <samples_in_buffer> (until new samples have
        been read).

        If the data acquisition has been stopped before the frame has been acquired completely,
        this method must still return all available samples already read into buffer.

        @param int number_of_samples: optional, the number of samples to read from buffer

        @return dict: Sample arrays (values) for each active input channel (keys)
        """

        if number_of_samples is not None:
            assert isinstance(number_of_samples, (int, np.integer)), f'Number of requested samples not integer'#
        
        samples_to_read = number_of_samples if number_of_samples is not None else self.samples_in_buffer

        assert samples_to_read <= self.__number_of_unread_samples,\
            f'Requested samples are more than the pending in frame'

        if number_of_samples is not None and self.is_running:
            request_time = time.time()
            while number_of_samples > self.samples_in_buffer:  # TODO: Check whether this works with a real HW
                # TODO could one use the ni timeout of the reader class here?
                if time.time() - request_time < 1.1*self.frame_size*self.sample_rate:  # TODO Is this timeout ok?
                    time.sleep(0.05)
                else:
                    raise TimeoutError(f'Acquiring {number_of_samples} samples took longer then the whole frame')

        data = dict()

        if samples_to_read == 0:
            return dict.fromkeys(self.__frame_buffer)

        with self._thread_lock:
            if not self.is_running:
                # When the IO was stopped with samples in buffer, return the ones in
                if number_of_samples is None:
                    data = self.__unread_samples_buffer.copy()
                    self.__unread_samples_buffer = dict.fromkeys(self.__frame_buffer)
                    return data
                else:
                    for key in self.__unread_samples_buffer:
                        data[key] = self.__unread_samples_buffer[key][:samples_to_read]
                    self.__number_of_unread_samples -= samples_to_read
                    self.__unread_samples_buffer = {key: arr[samples_to_read:] for (key, arr)
                                                    in self.__unread_samples_buffer.items()}
                    return data
            else:
                if self._di_readers:
                    write_offset = 0
                    di_data = np.zeros(len(self.__active_channels['di_channels']) * samples_to_read)
                    for di_reader in self._di_readers:
                        di_reader.read_many_sample_double(
                            di_data[write_offset:],
                            number_of_samples_per_channel=samples_to_read)
                        write_offset += samples_to_read

                    di_data = di_data.reshape(len(self.__active_channels['di_channels']), samples_to_read)
                    for num, di_channel in enumerate(self.__active_channels['di_channels']):
                        data[di_channel] = di_data[num]

                if self._ai_reader is not None:
                    ai_data = np.zeros((len(self.__active_channels['ai_channels']), samples_to_read))
                    self._ai_reader.read_many_sample(
                            ai_data,
                            number_of_samples_per_channel=samples_to_read)
                    for num, ai_channel in enumerate(self.__active_channels['ai_channels']):
                        data[ai_channel] = ai_data[num]

                self.__number_of_unread_samples -= samples_to_read
                return data

    def get_frame(self, data=None):
        """ Performs io for a single data frame for all active channels.
        This method call is blocking until the entire data frame has been emitted.

        See <start_buffered_output>, <stop_buffered_output> and <set_frame_data> for more details.

        @param dict data: The frame data (values) to be emitted for all active channels (keys)

        @return dict: Frame data (values) for all active input channels (keys)
        """
        with self._thread_lock:
            if data is not None:
                self.set_frame_data(data)
            self.start_buffered_frame()
            return_data = self.get_buffered_samples(self.frame_size)
            self.stop_buffered_frame()

            return return_data

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Finite IO is running (True) or not (False)
        """
        assert self.module_state() in ('locked', 'idle')  # TODO what about other module states?
        if self.module_state() == 'locked':
            return True
        else:
            return False

    # =============================================================================================
    def _init_sample_clock(self):
        """
        Configures a counter to provide the sample clock for all
        channels. # TODO external sample clock?

        @return int: error code (0: OK, -1: Error)
        """
        # # Return if sample clock is externally supplied
        # if self._external_sample_clock_source is not None:
        #     return 0

        if self._clk_task_handle is not None:
            self.log.error('Sample clock task is already running. Unable to set up a new clock '
                           'before you close the previous one.')
            return -1

        # Try to find an available counter
        for src in self.__all_counters:
            # Check if task by that name already exists
            task_name = 'SampleClock_{0:d}'.format(id(self))
            try:
                task = ni.Task(task_name)
            except ni.DaqError:
                self.log.exception('Could not create task with name "{0}".'.format(task_name))
                return -1

            # Try to configure the task
            try:
                task.co_channels.add_co_pulse_chan_freq(
                    '/{0}/{1}'.format(self._device_name, src),
                    freq=self.sample_rate,
                    idle_state=ni.constants.Level.LOW)
                task.timing.cfg_implicit_timing(
                    sample_mode=ni.constants.AcquisitionType.FINITE,
                    samps_per_chan=self.frame_size)
            except ni.DaqError:
                self.log.exception('Error while configuring sample clock task.')
                try:
                    task.close()
                    del task
                except NameError:
                    pass
                return -1

            # Try to reserve resources for the task
            try:
                task.control(ni.constants.TaskMode.TASK_RESERVE)
            except ni.DaqError:
                # Try to clean up task handle
                try:
                    task.close()
                except ni.DaqError:
                    pass
                try:
                    del task
                except NameError:
                    pass

                # Return if no counter could be reserved
                if src == self.__all_counters[-1]:
                    self.log.exception('Error while setting up clock. Probably because no free '
                                       'counter resource could be reserved.')
                    return -1
                continue
            break
        self._clk_task_handle = task

        if self._physical_sample_clock_output is not None:
            clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
            ni.system.System().connect_terms(source_terminal=clock_channel,
                                             destination_terminal='/{0}/{1}'.format(
                                                 self._device_name, self._physical_sample_clock_output))
        return 0

    def _init_digital_tasks(self):
        """
        Set up tasks for digital event counting.

        @return int: error code (0:OK, -1:error)
        """
        digital_channels = self.__active_channels['di_channels']
        if not digital_channels:
            return 0
        if self._di_task_handles:
            self.log.error('Digital counting tasks have already been generated. '
                           'Setting up counter tasks has failed.')
            self.terminate_all_tasks()
            return -1

        if self._clk_task_handle is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create digital counting tasks.')
            self.terminate_all_tasks()
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        # sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up digital counting tasks
        for i, chnl in enumerate(digital_channels):
            chnl_name = '/{0}/{1}'.format(self._device_name, chnl)
            task_name = 'PeriodCounter_{0}'.format(chnl)
            # Try to find available counter
            for ctr in self.__all_counters:
                ctr_name = '/{0}/{1}'.format(self._device_name, ctr)
                try:
                    task = ni.Task(task_name)
                except ni.DaqError:
                    self.log.error('Could not create task with name "{0}"'.format(task_name))
                    self.terminate_all_tasks()
                    return -1

                try:
                    task.ci_channels.add_ci_period_chan(
                        ctr_name,
                        min_val=0,
                        max_val=100000000,
                        units=ni.constants.TimeUnits.TICKS,
                        edge=ni.constants.Edge.RISING)
                    # NOTE: The following two direct calls to C-function wrappers are a
                    # workaround due to a bug in some NIDAQmx.lib property getters. If one of
                    # these getters is called, it will mess up the task timing.
                    # This behaviour has been confirmed using pure C code.
                    # nidaqmx will call these getters and so the C function is called directly.
                    try:
                        lib_importer.windll.DAQmxSetCIPeriodTerm(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(clock_channel.encode('ascii')))
                        lib_importer.windll.DAQmxSetCICtrTimebaseSrc(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(chnl_name.encode('ascii')))
                    except:
                        lib_importer.cdll.DAQmxSetCIPeriodTerm(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(clock_channel.encode('ascii')))
                        lib_importer.cdll.DAQmxSetCICtrTimebaseSrc(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(chnl_name.encode('ascii')))

                    task.timing.cfg_implicit_timing(
                        sample_mode=ni.constants.AcquisitionType.FINITE,
                        samps_per_chan=self.frame_size)
                except ni.DaqError:
                    try:
                        task.close()
                        del task
                    except NameError:
                        pass
                    self.terminate_all_tasks()
                    self.log.exception('Something went wrong while configuring digital counter '
                                       'task for channel "{0}".'.format(chnl))
                    return -1

                try:
                    task.control(ni.constants.TaskMode.TASK_RESERVE)
                except ni.DaqError:
                    try:
                        task.close()
                    except ni.DaqError:
                        self.log.exception('Unable to close task.')
                    try:
                        del task
                    except NameError:
                        self.log.exception('Some weird namespace voodoo happened here...')

                    if ctr == self.__all_counters[-1]:
                        self.log.exception('Unable to reserve resources for digital counting task '
                                           'of channel "{0}". No available counter found!'
                                           ''.format(chnl))
                        self.terminate_all_tasks()
                        return -1
                    continue

                try:
                    self._di_readers.append(CounterReader(task.in_stream))
                    self._di_readers[-1].verify_array_shape = False
                except ni.DaqError:
                    self.log.exception(
                        'Something went wrong while setting up the digital counter reader for '
                        'channel "{0}".'.format(chnl))
                    self.terminate_all_tasks()
                    try:
                        task.close()
                    except ni.DaqError:
                        self.log.exception('Unable to close task.')
                    try:
                        del task
                    except NameError:
                        self.log.exception('Some weird namespace voodoo happened here...')
                    return -1

                self._di_task_handles.append(task)
                break
        return 0

    def _init_analog_in_task(self):
        """
        Set up task for analog voltage measurement.

        @return int: error code (0:OK, -1:error)
        """
        analog_channels = self.__active_channels['ai_channels']
        if not analog_channels:
            return 0
        if self._ai_task_handle:
            self.log.error(
                'Analog input task has already been generated. Unable to set up analog in task.')
            self.terminate_all_tasks()
            return -1
        if self._clk_task_handle is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create analog voltage measurement tasks.')
            self.terminate_all_tasks()
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up analog input task
        task_name = 'AnalogIn_{0:d}'.format(id(self))
        try:
            ai_task = ni.Task(task_name)
        except ni.DaqError:
            self.log.exception('Unable to create analog-in task with name "{0}".'.format(task_name))
            self.terminate_all_tasks()
            return -1

        try:
            ai_ch_str = ','.join(['/{0}/{1}'.format(self._device_name, c) for c in analog_channels])
            ai_task.ai_channels.add_ai_voltage_chan(ai_ch_str,  # TODO constraints for ADC range
                                                    max_val=10,  # max(self._adc_voltage_range),
                                                    min_val=0)  # min(self._adc_voltage_range))
            ai_task.timing.cfg_samp_clk_timing(sample_freq,
                                               source=clock_channel,
                                               active_edge=ni.constants.Edge.RISING,
                                               sample_mode=ni.constants.AcquisitionType.FINITE,
                                               samps_per_chan=self.frame_size)
        except ni.DaqError:
            self.log.exception(
                'Something went wrong while configuring the analog-in task.')
            try:
                del ai_task
            except NameError:
                pass
            self.terminate_all_tasks()
            return -1

        try:
            ai_task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                ai_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ai_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')

            self.log.exception('Unable to reserve resources for analog-in task.')
            self.terminate_all_tasks()
            return -1

        try:
            self._ai_reader = AnalogMultiChannelReader(ai_task.in_stream)
            self._ai_reader.verify_array_shape = False
        except ni.DaqError:
            try:
                ai_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ai_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')
            self.log.exception('Something went wrong while setting up the analog input reader.')
            self.terminate_all_tasks()
            return -1

        self._ai_task_handle = ai_task
        return 0

    def _init_analog_out_task(self):
        analog_channels = self.__active_channels['ao_channels']
        if not analog_channels:
            self.log.error('No output channels defined. Can initialize output task')
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up analog input task
        task_name = 'AnalogOut_{0:d}'.format(id(self))

        try:
            ao_task = ni.Task(task_name)
        except ni.DaqError:
            self.log.exception('Unable to create analog-in task with name "{0}".'.format(task_name))
            self.terminate_all_tasks()
            return -1

        try:
            ao_ch_str = ','.join(['/{0}/{1}'.format(self._device_name, c) for c in analog_channels])
            ao_task.ao_channels.add_ao_voltage_chan(ao_ch_str,  # TODO constraints for range
                                                    max_val=10,  # max(self._adc_voltage_range),
                                                    min_val=0)  # min(self._adc_voltage_range))
            ao_task.timing.cfg_samp_clk_timing(sample_freq,
                                               source=clock_channel,
                                               active_edge=ni.constants.Edge.RISING,
                                               sample_mode=ni.constants.AcquisitionType.FINITE,
                                               samps_per_chan=self.frame_size)
        except ni.DaqError:
            self.log.exception(
                'Something went wrong while configuring the analog-in task.')
            try:
                del ao_task
            except NameError:
                pass
            self.terminate_all_tasks()
            return -1

        try:
            ao_task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                ao_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ao_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')

            self.log.exception('Unable to reserve resources for analog-out task.')
            self.terminate_all_tasks()
            return -1

        try:
            self._ao_writer = AnalogMultiChannelWriter(ao_task.in_stream)
            self._ao_writer.verify_array_shape = False
        except ni.DaqError:
            try:
                ao_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ao_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')
            self.log.exception('Something went wrong while setting up the analog input reader.')
            self.terminate_all_tasks()
            return -1

        self._ao_task_handle = ao_task
        return 0

    def reset_hardware(self):
        """
        Resets the NI hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._device_handle.reset_device()
            self.log.info('Reset device {0}.'.format(self._device_name))
        except ni.DaqError:
            self.log.exception('Could not reset NI device {0}'.format(self._device_name))
            return -1
        return 0

    def terminate_all_tasks(self):
        err = 0

        self._di_readers = list()
        self._ai_reader = None

        while len(self._di_task_handles) > 0:
            try:
                if not self._di_task_handles[-1].is_task_done():
                    self._di_task_handles[-1].stop()
                self._di_task_handles[-1].close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate digital counter task.')
                err = -1
            finally:
                del self._di_task_handles[-1]
        self._di_task_handles = list()

        if self._ai_task_handle is not None:
            try:
                if not self._ai_task_handle.is_task_done():
                    self._ai_task_handle.stop()
                self._ai_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate analog input task.')
                err = -1
        self._ai_task_handle = None

        if self._ao_task_handle is not None:
            try:
                if not self._ao_task_handle.is_task_done():
                    self._ao_task_handle.stop()
                self._ao_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate analog input task.')
                err = -1
            self._ao_task_handle = None

        if self._clk_task_handle is not None:
            try:
                if not self._clk_task_handle.is_task_done():
                    self._clk_task_handle.stop()
                self._clk_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate clock task.')
                err = -1

        self._clk_task_handle = None
        return err

    @staticmethod
    def _extract_terminal(term_str):
        """
        Helper function to extract the bare terminal name from a string and strip it of the device
        name and dashes.
        Will return the terminal name in lower case.

        @param str term_str: The str to extract the terminal name from
        @return str: The terminal name in lower case
        """
        term = term_str.strip('/').lower()
        if 'dev' in term:
            term = term.split('/', 1)[-1]
        return term

    def _extract_ai_di_from_input_channels(self, input_channels):
        """
        Takes an iterable with output channels and returns the split up ai and di channels

        @return tuple(di_channels), tuple(ai_channels))
        """
        input_channels = tuple(self._extract_terminal(src) for src in input_channels)

        di_channels = tuple(channel for channel in input_channels if 'pfi' in channel)
        ai_channels = tuple(channel for channel in input_channels if 'ai' in channel)

        assert (di_channels or ai_channels), f'No channels could be extracted from {*input_channels,}'

        return tuple(di_channels), tuple(ai_channels)


class NiInitError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
