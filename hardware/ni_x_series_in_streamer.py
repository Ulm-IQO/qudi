# -*- coding: utf-8 -*-

"""
This file contains the qudi hardware module to use a National Instruments X-series card as mixed
signal input data streamer.

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

import copy
import numpy as np
import ctypes
import nidaqmx as ni
from nidaqmx._lib import lib_importer
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader

from core.module import Base, ConfigOption
# from core.configoption import ConfigOption
from core.util.helpers import natural_sort
from interface.data_instream_interface import DataInStreamInterface, DataInStreamConstraints
from interface.data_instream_interface import StreamingMode, StreamChannelType


class NIXSeriesInStreamer(Base, DataInStreamInterface):
    """
    A National Instruments device that can detect and count digital pulses and measure analog
    voltages as data stream.

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    Example config for copy-paste:

    nicard_6343_instreamer:
        module.Class: 'ni_x_series_counter.NationalInstrumentsXSeriesCounter'
        device_name: 'Dev1'
        digital_sources:  # optional
            - 'PFI15'
        analog_sources:  # optional
            - 'ai1'
        # external_sample_clock_source: 'PFI0'  # optional
        # external_sample_clock_frequency: 1000  # optional
        adc_voltage_range: [-10, 10]  # optional
        max_channel_samples_buffer: 10000000  # optional
        read_write_timeout: 10  # optional

    """

    # config options
    _device_name = ConfigOption(name='device_name', default='Dev1', missing='warn')
    _digital_sources = ConfigOption(name='digital_sources', default=tuple(), missing='info')
    _analog_sources = ConfigOption(name='analog_sources', default=tuple(), missing='info')
    _external_sample_clock_source = ConfigOption(
        name='external_sample_clock_source', default=None, missing='nothing')
    _external_sample_clock_frequency = ConfigOption(
        name='external_sample_clock_frequency', default=None, missing='nothing')

    _adc_voltage_range = ConfigOption('adc_voltage_range', default=(-10, 10), missing='info')
    _max_channel_samples_buffer = ConfigOption(
        'max_channel_samples_buffer', default=25e6, missing='info')
    _rw_timeout = ConfigOption('read_write_timeout', default=10, missing='nothing')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NIDAQmx device handle
        self._device_handle = None
        # Task handles for NIDAQmx tasks
        self._di_task_handles = list()
        self._ai_task_handle = None
        self._clk_task_handle = None
        # nidaqmx stream reader instances to help with data acquisition
        self._di_readers = list()
        self._ai_reader = None

        # Internal settings
        self.__sample_rate = -1.0
        self.__data_type = np.float64
        self.__total_number_of_samples = None
        self.__buffer_size = -1
        self.__use_circular_buffer = False
        self.__streaming_mode = None

        # Data buffer
        self._data_buffer = np.empty((0, 0), dtype=self.__data_type)
        self._has_overflown = False

        # List of all available counters for this device
        self.__all_counters = tuple()
        self.__channel_props = dict()

        # Stored hardware constraints
        self._constraints = None
        return

    def on_activate(self):
        """
        Starts up the NI-card and performs sanity checks.
        """
        # Check if device is connected and set device to use
        dev_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in [dev.lower() for dev in dev_names]:
            raise Exception('Device name "{0}" not found in list of connected devices: {1}\n'
                            'Activation of NIXSeriesInStreamer failed!'
                            ''.format(self._device_name, dev_names))
        for dev in dev_names:
            if dev.lower() == self._device_name.lower():
                self._device_name = dev
                break
        self._device_handle = ni.system.Device(self._device_name)

        self.__all_counters = tuple(
            ctr.split('/')[-1] for ctr in self._device_handle.co_physical_chans.channel_names if
            'ctr' in ctr.lower())

        # Check digital input terminals
        if self._digital_sources:
            term_names = [term.rsplit('/', 1)[-1] for term in self._device_handle.terminals if
                          'PFI' in term]
            new_source_names = [src.strip('/').split('/')[-1].upper() for src in
                                self._digital_sources]
            invalid_sources = set(new_source_names).difference(set(term_names))
            if invalid_sources:
                self.log.error(
                    'Invalid digital source terminals encountered. Following sources will '
                    'be ignored:\n  {0}\nValid digital input terminals are:\n  {1}'
                    ''.format(', '.join(natural_sort(invalid_sources)),
                              ', '.join(term_names)))
            self._digital_sources = natural_sort(set(new_source_names).difference(invalid_sources))

        # Check analog input channels
        if self._analog_sources:
            channel_names = [chnl.rsplit('/', 1)[-1] for chnl in
                             self._device_handle.ai_physical_chans.channel_names]
            new_source_names = [src.strip('/').split('/')[-1].lower() for src in
                                self._analog_sources]
            invalid_sources = set(new_source_names).difference(set(channel_names))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(channel_names)))
            self._analog_sources = natural_sort(set(new_source_names).difference(invalid_sources))

        # Check if there are any valid input channels left
        if not self._analog_sources and not self._digital_sources:
            raise Exception('No valid analog or digital sources defined in config. '
                            'Activation of NIXSeriesInStreamer failed!')

        # Create constraints
        self._constraints = DataInStreamConstraints()
        self._constraints.max_simultaneous_analog_channels = 16
        self._constraints.max_simultaneous_digital_channels = 3

        self._constraints.analog_sample_rate.min = self._device_handle.ai_min_rate
        self._constraints.analog_sample_rate.max = self._device_handle.ai_max_multi_chan_rate
        self._constraints.analog_sample_rate.step = 1
        self._constraints.analog_sample_rate.unit = 'Hz'
        # FIXME: What is the minimum frequency for the digital counter timebase?
        self._constraints.digital_sample_rate.min = 0
        self._constraints.digital_sample_rate.max = self._device_handle.ci_max_timebase
        self._constraints.digital_sample_rate.step = 0.1
        self._constraints.digital_sample_rate.unit = 'Hz'
        self._constraints.combined_sample_rate = self._constraints.analog_sample_rate

        self._constraints.read_block_size.min = 1
        self._constraints.read_block_size.max = int(self._max_channel_samples_buffer)
        self._constraints.read_block_size.step = 1

        # TODO: Implement FINITE streaming mode
        self._constraints.streaming_modes = (StreamingMode.CONTINUOUS,)  # , StreamingMode.FINITE)
        if self._analog_sources:
            self._constraints.data_types = (np.float64,)
        else:
            self._constraints.data_types = (np.uint32, np.float64)
        self._constraints.allow_circular_buffer = True

        # Check external sample clock source
        if self._external_sample_clock_source is not None:
            new_name = self._external_sample_clock_source.strip('/').lower()
            if 'dev' in new_name:
                new_name = new_name.split('/', 1)[-1]
            if new_name not in [src.split('/', 2)[-1].lower() for src in self._device_handle.terminals]:
                self.log.error('No valid source terminal found for external_sample_clock_source '
                               '"{0}". Falling back to internal sampling clock.'
                               ''.format(self._external_sample_clock_source))
                self._external_sample_clock_source = None
            else:
                self._external_sample_clock_source = new_name

        # Check external sample clock frequency
        if self._external_sample_clock_source is None:
            self._external_sample_clock_frequency = None
        elif self._external_sample_clock_frequency is None:
            self.log.error('External sample clock source supplied but no clock frequency. '
                           'Falling back to internal clock instead.')
            self._external_sample_clock_source = None
        elif not self._clk_frequency_valid(self._external_sample_clock_frequency):
            if self._analog_sources:
                self.log.error('External sample clock frequency requested ({0:.3e}Hz) is out of '
                               'bounds. Please choose a value between {1:.3e}Hz and {2:.3e}Hz.'
                               ' Value will be clipped to the closest boundary.'
                               ''.format(self._external_sample_clock_frequency,
                                         self._constraints.combined_sample_rate.min,
                                         self._constraints.combined_sample_rate.max))
                self._external_sample_clock_frequency = min(
                    self._external_sample_clock_frequency,
                    self._constraints.combined_sample_rate.max)
                self._external_sample_clock_frequency = max(
                    self._external_sample_clock_frequency,
                    self._constraints.combined_sample_rate.min)
            else:
                self.log.error('External sample clock frequency requested ({0:.3e}Hz) is out of '
                               'bounds. Please choose a value between {1:.3e}Hz and {2:.3e}Hz.'
                               ' Value will be clipped to the closest boundary.'
                               ''.format(self._external_sample_clock_frequency,
                                         self._constraints.digital_sample_rate.min,
                                         self._constraints.digital_sample_rate.max))
                self._external_sample_clock_frequency = min(
                    self._external_sample_clock_frequency,
                    self._constraints.digital_sample_rate.max)
                self._external_sample_clock_frequency = max(
                    self._external_sample_clock_frequency,
                    self._constraints.digital_sample_rate.min)
        if self._external_sample_clock_frequency is not None:
            self.__sample_rate = float(self._external_sample_clock_frequency)

        self.terminate_all_tasks()
        self._di_task_handles = list()
        self._di_readers = list()
        self._ai_task_handle = None
        self._ai_reader = None
        self._clk_task_handle = None

        self.__sample_rate = self._constraints.combined_sample_rate.min
        self.__data_type = np.float64
        self.__total_number_of_samples = None
        self.__buffer_size = min(self._max_channel_samples_buffer, 1000000)
        self.__use_circular_buffer = False
        self.__streaming_mode = StreamingMode.CONTINUOUS

        # Check if all input channels fit in the device
        if self._constraints.max_simultaneous_digital_channels < len(self._digital_sources):
            raise Exception('Too many digital channels specified. Maximum number of digital '
                            'channels is {0:d}.'
                            ''.format(self._constraints.max_simultaneous_digital_channels))
        if self._constraints.max_simultaneous_analog_channels < len(self._analog_sources):
            raise Exception('Too many analog channels specified. Maximum number of analog '
                            'channels is {0:d}.'
                            ''.format(self._constraints.max_simultaneous_analog_channels))

        # Reset data buffer
        self._data_buffer = np.empty((0, 0), dtype=self.__data_type)
        self._has_overflown = False

        # Create channel properties
        self.__channel_props = dict()
        for chnl in self._digital_sources:
            self.__channel_props[chnl] = {'unit': 'counts', 'type': StreamChannelType.DIGITAL}
        for chnl in self._analog_sources:
            self.__channel_props[chnl] = {'unit': 'V', 'type': StreamChannelType.ANALOG}
        return

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.terminate_all_tasks()
        # Free memory if possible while module is inactive
        self._data_buffer = np.empty((0, 0), dtype=self.__data_type)
        return

    @property
    def sample_rate(self):
        """
        Read-only property to return the currently set sample rate

        @return float: current sample rate in Hz
        """
        return self.__sample_rate

    @property
    def data_type(self):
        """
        Read-only property to return the currently set data type

        @return type: current data type
        """
        return self.__data_type

    @property
    def buffer_size(self):
        """
        Read-only property to return the currently buffer size.
        Buffer size corresponds to the number of samples per channel that can be buffered. So the
        actual buffer size in bytes can be estimated by:
            buffer_size * number_of_channels * size_in_bytes(data_type)

        @return int: current buffer size in samples per channel
        """
        return self.__buffer_size

    @property
    def use_circular_buffer(self):
        """
        Read-only property to return a flag indicating if circular sample buffering is being used
        or not.

        @return bool: indicate if circular sample buffering is used (True) or not (False)
        """
        return self.__use_circular_buffer

    @property
    def streaming_mode(self):
        """
        Read-only property to return the currently configured streaming mode Enum.

        @return StreamingMode: Finite (StreamingMode.FINITE) or continuous
                               (StreamingMode.CONTINUOUS) data acquisition
        """
        return self.__streaming_mode

    @property
    def number_of_channels(self):
        """
        Read-only property to return the currently configured number of data channels.

        @return int: the currently set number of channels
        """
        return len(self._analog_sources) + len(self._digital_sources)

    @property
    def channel_names(self):
        """
        Read-only property to return the currently used data channel names.

        @return tuple: current data channel names
        """
        return tuple(self._digital_sources + self._analog_sources)

    @property
    def channel_properties(self):
        """
        Read-only property to return the currently used data channel properties.
        The channel properties are a dict of the following form:
            channel_property = {'unit': 'V', 'type': StreamChannelType.ANALOG}
            channel_property = {'unit': 'counts', 'type': StreamChannelType.DIGITAL}
            ...

        @return dict: current data channel properties with keys being the channel names and values
        being the corresponding property dicts.
        """
        return copy.deepcopy(self.__channel_props)

    @property
    def available_samples(self):
        """
        Read-only property to return the currently available number of samples per channel ready
        to read from buffer.

        @return int: Number of available samples per channel
        """
        if not self.is_running:
            return 0

        if self._ai_task_handle is None:
            # avail_samples = self._di_task_handles[0].in_stream.total_samp_per_chan_acquired - \
            #                 self._di_task_handles[0].in_stream.curr_read_pos
            return self._di_task_handles[0].in_stream.avail_samp_per_chan
        else:
            # avail_samples = self._ai_task_handle.in_stream.total_samp_per_chan_acquired - \
            #                 self._ai_task_handle.in_stream.curr_read_pos
            return self._ai_task_handle.in_stream.avail_samp_per_chan

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        return self._ai_reader is not None or self._di_readers

    @property
    def buffer_overflown(self):
        """
        Read-only flag to check if the read buffer has overflown.
        In case of a circular buffer it indicates data loss.
        In case of a non-circular buffer the data acquisition should have stopped if this flag is
        coming up.
        Flag will only be reset after starting a new data acquisition.

        @return bool: Flag indicates if buffer has overflown (True) or not (False)
        """
        return self._has_overflown

    @property
    def all_settings(self):
        """
        Read-only property to return a dict containing all current settings and values that can be
        configured using the method "configure". Basically returns the same as "configure".

        @return dict: Dictionary containing all configurable settings
        """
        return {'sample_rate': self.__sample_rate,
                'data_type': self.__data_type,
                'total_number_of_samples': self.__total_number_of_samples,
                'buffer_size': self.__buffer_size,
                'use_circular_buffer': self.__use_circular_buffer}

    def configure(self, sample_rate=None, data_type=None, streaming_mode=None,
                  total_number_of_samples=None, buffer_size=None, use_circular_buffer=None):
        """
        Method to configure all possible settings of the data input stream.

        @param float sample_rate: The sample rate in Hz at which data points are acquired
        @param type data_type: The data type of the acquired data. Must be numpy.ndarray compatible.
        @param StreamingMode streaming_mode: The streaming mode to use (finite or continuous)
        @param int total_number_of_samples: In case of a finite data stream, the total number of
                                            samples to read per channel
        @param int buffer_size: The size of the data buffer to pre-allocate in samples per channel
        @param bool use_circular_buffer: Use circular buffering (True) or stop upon buffer overflow
                                         (False)

        @return dict: All current settings in a dict. Keywords are the same as kwarg names.
        """
        if self.is_running:
            self.log.warning('Unable to configure NI x-series data-in streamer while data '
                             'acquisition is in progress. Stop the device and try again.')
            return self.all_settings

        # Handle sample rate change
        if sample_rate is not None:
            if not self._clk_frequency_valid(sample_rate):
                if self._analog_sources:
                    min_val = self._constraints.combined_sample_rate.min
                    max_val = self._constraints.combined_sample_rate.max
                    self.log.warning(
                        'Sample rate requested ({0:.3e}Hz) is out of bounds. Please choose '
                        'a value between {1:.3e}Hz and {2:.3e}Hz. Value will be clipped to '
                        'the closest boundary.'.format(sample_rate, min_val, max_val))
                else:
                    min_val = self._constraints.digital_sample_rate.min
                    max_val = self._constraints.digital_sample_rate.max
                    self.log.warning(
                        'Sample rate requested ({0:.3e}Hz) is out of bounds. Please choose '
                        'a value between {1:.3e}Hz and {2:.3e}Hz. Value will be clipped to '
                        'the closest boundary.'.format(sample_rate, min_val, max_val))
                sample_rate = max(min(max_val, sample_rate), min_val)
            self.__sample_rate = float(sample_rate)

        # Handle data type change
        if data_type is not None:
            if data_type != np.uint32 and data_type != np.float64:
                self.log.error('data_type must be a valid numpy dtype.')
                return self.all_settings
            if data_type == np.uint32 and self._analog_sources:
                self.log.error('Data type numpy.uint32 only allowed for pure digital counting. If '
                               'you are using analog input channels, you must set this to '
                               'numpy.float64.')
                return self.all_settings
            self.__data_type = data_type

        # Handle streaming mode change
        if streaming_mode is not None:
            if streaming_mode not in self._constraints.streaming_modes:
                self.log.error('Unknown streaming mode "{0}" encountered.\nValid modes are: {1}.'
                               ''.format(streaming_mode, self._constraints.streaming_modes))
                return self.all_settings

        # Handle total number of samples
        if total_number_of_samples is not None:
            if self.__streaming_mode != StreamingMode.FINITE:
                self.log.warning('total_number_of_samples only accepted for finite length '
                                 'streaming. Current streaming mode is "{0}". '
                                 'total_number_of_samples ignored.'.format(self.__streaming_mode))
            self.__total_number_of_samples = int(total_number_of_samples)

        # Handle buffer size
        if buffer_size is not None:
            if buffer_size > self._max_channel_samples_buffer:
                self.log.error('buffer_size to set ({0}) is larger than maximum allowed buffer '
                               'size of {1:d} samples per channel.'
                               ''.format(buffer_size, self._max_channel_samples_buffer))
                return self.all_settings
            elif buffer_size < 1:
                self.log.error('Buffer size smaller than 1 makes no sense. Tried to set {0} as '
                               'buffer size and failed.'.format(buffer_size))
                return self.all_settings
            self.__buffer_size = int(buffer_size)
            self._init_buffer()

        # Handle circular buffer flag
        if use_circular_buffer is not None:
            if use_circular_buffer and not self._constraints.allow_circular_buffer:
                self.log.error('Circular buffer not allowed for this hardware module.')
                return self.all_settings
            self.__use_circular_buffer = bool(use_circular_buffer)
        return self.all_settings

    def get_constraints(self):
        """
        Return the constraints on the settings for this data streamer.

        @return DataInStreamConstraints: Instance of DataInStreamConstraints containing constraints
        """
        return self._constraints

    def start_stream(self):
        """
        Start the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self.log.warning('Unable to start input stream. It is already running.')
            return 0

        if self._init_sample_clock() != 0 or self._init_digital_tasks() != 0 or self._init_analog_task() != 0:
            return -1

        self._init_buffer()

        try:
            self._clk_task_handle.start()
        except ni.DaqError:
            self.log.exception('Error while starting sample clock task.')
            self.terminate_all_tasks()
            return -1

        if self._ai_task_handle is not None:
            try:
                self._ai_task_handle.start()
            except ni.DaqError:
                self.log.exception('Error while starting analog input task.')
                self.terminate_all_tasks()
                return -1
        try:
            for task in self._di_task_handles:
                task.start()
        except ni.DaqError:
            self.log.exception('Error while starting digital counter tasks.')
            self.terminate_all_tasks()
            return -1
        return 0

    def stop_stream(self):
        """
        Stop the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self.terminate_all_tasks()
        return 0

    def read_data_into_buffer(self, buffer, number_of_samples=None):
        """
        Read data from the stream buffer into a 1D/2D numpy array given as parameter.
        In case of a single data channel the numpy array can be either 1D or 2D. In case of more
        channels the array must be 2D with the first index corresponding to the channel number and
        the second index serving as sample index:
            buffer.shape == (self.number_of_channels, number_of_samples)
        The numpy array must have the same data type as self.data_type.
        If number_of_samples is omitted it will be derived from buffer.shape[1]

        This method will not return until all requested samples have been read or a timeout occurs.

        @param numpy.ndarray buffer: The numpy array to write the samples to
        @param int number_of_samples: optional, number of samples to read per channel. If omitted,
                                      this number will be derived from buffer axis 1 size.

        @return int: Number of samples read into buffer; negative value indicates error
                     (e.g. read timeout)
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return -1

        if not isinstance(buffer, np.ndarray) or buffer.dtype != self.__data_type:
            self.log.error('buffer must be numpy.ndarray with dtype {0}. Read failed.'
                           ''.format(self.__data_type))
            return -1
        if number_of_samples is None:
            number_of_samples = buffer.shape[1]

        # Check for buffer overflow
        if self.available_samples > self.buffer_size:
            self._has_overflown = True

        try:
            # Read digital channels
            for i, reader in enumerate(self._di_readers):
                # read the counter value. This function is blocking.
                if self.__data_type == np.float64:
                    read_samples = reader.read_many_sample_double(
                        buffer[i],
                        number_of_samples_per_channel=number_of_samples,
                        timeout=self._rw_timeout)
                else:
                    read_samples = reader.read_many_sample_uint32(
                        buffer[i],
                        number_of_samples_per_channel=number_of_samples,
                        timeout=self._rw_timeout)
                if read_samples != number_of_samples:
                    return -1
            # Read analog channels
            if self._ai_reader is not None:
                read_samples = self._ai_reader.read_many_sample(
                    buffer[len(self._di_readers):],
                    number_of_samples_per_channel=number_of_samples,
                    timeout=self._rw_timeout)
            if read_samples != number_of_samples:
                return -1
        except ni.DaqError:
            self.log.exception('Getting samples from counter failed.')
            return -1
        return read_samples

    def read_available_data_into_buffer(self, buffer):
        """
        Read data from the stream buffer into a 1D/2D numpy array given as parameter.
        In case of a single data channel the numpy array can be either 1D or 2D. In case of more
        channels the array must be 2D with the first index corresponding to the channel number and
        the second index serving as sample index:
            buffer.shape == (self.number_of_channels, number_of_samples)
        The numpy array must have the same data type as self.data_type.

        This method will read all currently available samples into buffer. If number of available
        samples exceed buffer size, read only as many samples as fit into the buffer.

        @param numpy.ndarray buffer: The numpy array to write the samples to

        @return int: Number of samples read into buffer; negative value indicates error
                     (e.g. read timeout)
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return -1

        avail_samples = min(buffer.size // self.number_of_channels, self.available_samples)
        return self.read_data_into_buffer(buffer=buffer, number_of_samples=avail_samples)

    def read_data(self, number_of_samples=None):
        """
        Read data from the stream buffer into a 2D numpy array and return it.
        The arrays first index corresponds to the channel number and the second index serves as
        sample index:
            return_array.shape == (self.number_of_channels, number_of_samples)
        The numpy arrays data type is the one defined in self.data_type.
        If number_of_samples is omitted all currently available samples are read from buffer.

        This method will not return until all requested samples have been read or a timeout occurs.

        @param int number_of_samples: optional, number of samples to read per channel. If omitted,
                                      all available samples are read from buffer.

        @return numpy.ndarray: The read samples
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return -1

        if number_of_samples is None:
            if self._ai_task_handle is None:
                number_of_samples = self._di_task_handles[0].in_stream.total_samp_per_chan_acquired - self._di_task_handles[0].in_stream.curr_read_pos
            else:
                number_of_samples = self._ai_task_handle.in_stream.total_samp_per_chan_acquired - self._ai_task_handle.in_stream.curr_read_pos

        buffer = np.zeros((self.number_of_channels, number_of_samples), dtype=self.data_type)
        read_samples = self.read_data_into_buffer(buffer, number_of_samples=number_of_samples)
        if read_samples != number_of_samples:
            return np.empty((0, 0), dtype=self.data_type)
        return buffer

    def read_single_point(self):
        """
        This method will initiate a single sample read on each configured data channel.
        In general this sample may not be acquired simultaneous for all channels and timing in
        general can not be assured. Us this method if you want to have a non-timing-critical
        snapshot of your current data channel input.
        May not be available for all devices.
        The returned 1D numpy array will contain one sample for each channel.

        @return numpy.ndarray: 1D array containing one sample for each channel. Empty array
                               indicates error.
        """
        self.log.error('"read_single_point" not implemented yet.')
        return np.empty((0, 0), dtype=self.data_type)

    # =============================================================================================

    def _init_sample_clock(self):
        """
        If no external clock is given, configures a counter to provide the sample clock for all
        channels.

        @return int: error code (0: OK, -1: Error)
        """
        # Return if sample clock is externally supplied
        if self._external_sample_clock_source is not None:
            return 0

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
                    freq=self.__sample_rate,
                    idle_state=ni.constants.Level.LOW)
                task.timing.cfg_implicit_timing(
                    sample_mode=ni.constants.AcquisitionType.CONTINUOUS)
            except ni.DaqError:
                self.log.exception('Error while configuring sample clock task.')
                try:
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
        return 0

    def _init_digital_tasks(self):
        """
        Set up tasks for digital event counting.

        @return int: error code (0:OK, -1:error)
        """
        if not self._digital_sources:
            return 0
        if self._di_task_handles:
            self.log.error('Digital counting tasks have already been generated. '
                           'Setting up counter tasks has failed.')
            self.terminate_all_tasks()
            return -1

        if self._clk_task_handle is None and self._external_sample_clock_source is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create digital counting tasks.')
            self.terminate_all_tasks()
            return -1

        if self._external_sample_clock_source:
            clock_channel = '/{0}/{1}'.format(self._device_name, self._external_sample_clock_source)
            sample_freq = float(self._external_sample_clock_frequency)
        else:
            clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
            sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up digital counting tasks
        for i, chnl in enumerate(self._digital_sources):
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
                        sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                        samps_per_chan=self.__buffer_size)
                except ni.DaqError:
                    try:
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

    def _init_analog_task(self):
        """
        Set up task for analog voltage measurement.

        @return int: error code (0:OK, -1:error)
        """
        if not self._analog_sources:
            return 0
        if self._ai_task_handle:
            self.log.error(
                'Analog input task has already been generated. Unable to set up analog in task.')
            self.terminate_all_tasks()
            return -1
        if self._clk_task_handle is None and self._external_sample_clock_source is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create analog voltage measurement tasks.')
            self.terminate_all_tasks()
            return -1

        if self._external_sample_clock_source:
            clock_channel = '/{0}/{1}'.format(self._device_name, self._external_sample_clock_source)
            sample_freq = float(self._external_sample_clock_frequency)
        else:
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
            ai_ch_str = ','.join(
                ['/{0}/{1}'.format(self._device_name, chnl) for chnl in self._analog_sources])
            ai_task.ai_channels.add_ai_voltage_chan(ai_ch_str,
                                                    max_val=max(self._adc_voltage_range),
                                                    min_val=min(self._adc_voltage_range))
            ai_task.timing.cfg_samp_clk_timing(sample_freq,
                                               source=clock_channel,
                                               active_edge=ni.constants.Edge.RISING,
                                               sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                                               samps_per_chan=self.__buffer_size)
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
            # self._ai_reader.verify_array_shape = False
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

        for i in range(len(self._di_task_handles)):
            try:
                if not self._di_task_handles[i].is_task_done():
                    self._di_task_handles[i].stop()
                self._di_task_handles[i].close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate digital counter task.')
                err = -1
            finally:
                del self._di_task_handles[i]
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

    def _clk_frequency_valid(self, frequency):
        if self._analog_sources:
            max_rate = self._constraints.combined_sample_rate.max
            min_rate = self._constraints.combined_sample_rate.min
        else:
            max_rate = self._constraints.digital_sample_rate.max
            min_rate = self._constraints.digital_sample_rate.min
        return min_rate <= frequency <= max_rate

    def _init_buffer(self):
        if not self.is_running:
            self._data_buffer = np.zeros(
                (self.number_of_channels, self.buffer_size),
                dtype=self.data_type)
            self._has_overflown = False
        return
