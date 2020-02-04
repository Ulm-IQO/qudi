import ctypes
import numpy as np
import time
from qtpy import QtCore
import ctypes

from core.module import Base
from core.configoption import ConfigOption
from core.util.helpers import natural_sort
from core.util.helpers import natural_sort
from interface.data_instream_interface import DataInStreamInterface, DataInStreamConstraints
from interface.data_instream_interface import StreamingMode, StreamChannelType, StreamChannel


# from core.interface import interface_method


class Qutau(Base, DataInStreamInterface):
    """
    This is just a dummy hardware class to be used with SimpleDataReaderLogic.
    This is a dummy config file:
        qutau_slow:
            module.Class: 'data_instream_dummy.InStreamDummy'
            digital_channels:  # optional, must provide at least one digital or analog channel
                - '1'
                - '2'
            digital_event_rates:  # optional, must have as many entries as digital_channels or just one
                - 1000

    Count channel 0 means channel 1 and trigger channel 1 means channel 2 and so on...
    Load the Qutau library file tdcbase.dll. Can be found on the server or in the directory of the qutau software
    in programs files folder and should be placed in <Windows>/System32/
    """
    _digital_channels = ConfigOption(name='digital_channels', missing='warn')
    _digital_event_rates = ConfigOption(name='digital_event_rates', default=100000, missing='nothing')
    _analog_channels = ConfigOption(name='analog_channels', default=tuple(), missing='nothing')

    # _deviceId = ConfigOption('deviceID', 0, missing='warn')
    # _coincWin = ConfigOption('coincidenceWindow', 0, missing='warn')
    # _fileformat = ConfigOption('fileformat', 0, missing='warn')
    # _filename = ConfigOption('filename', 0, missing='warn')
    # _bufferSize = 500
    # minimal_binwidth = ConfigOption('minimal_binwidth', missing='warn')
    # gated = ConfigOption('gated', False, missing='warn')
    # _trigger_channel = ConfigOption('trigger_channel', missing='warn')
    # _count_channel = ConfigOption('count_channel', missing='warn')
    # _number_of_bins = 100
    # _clock_frequency = ConfigOption('clock_frequency', missing='warn')
    # _samples_number = ConfigOption('samples_number', missing='warn')
    # _counter_channels = ConfigOption('counter_channels', missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._dll = ctypes.windll.LoadLibrary('tdcbase')
        self.__sample_rate = -1.0
        self.__data_type = np.float64
        self.__stream_length = -1
        self.__buffer_size = 1
        self.__use_circular_buffer = False
        self.__streaming_mode = None
        self.__active_channels = [1, 2]

        # Data buffer
        self._data_buffer = np.empty(0, dtype=self.__data_type)
        self._has_overflown = False
        self._is_running = False
        self._last_read = None
        self._start_time = None
        # Stored hardware constraints
        self._constraints = DataInStreamConstraints()
        self._constraints.digital_channels = tuple(
            StreamChannel(name=ch, type=StreamChannelType.DIGITAL, unit='counts') for ch in
            self._digital_channels)
        self._constraints.digital_sample_rate.min = 0.01526
        self._constraints.digital_sample_rate.max = 1000
        self._constraints.digital_sample_rate.step = 1
        self._constraints.digital_sample_rate.unit = 'Hz'

        self._constraints.read_block_size.min = 31
        self._constraints.read_block_size.max = 1000000
        self._constraints.read_block_size.step = 1
        # TODO: Implement FINITE streaming mode
        self._constraints.streaming_modes = (StreamingMode.CONTINUOUS,)  # , StreamingMode.FINITE)
        self._constraints.data_type = self.__data_type
        self._constraints.allow_circular_buffer = True

        self.err_dict = {-1: 'unspecified error',
                         0: 'No error',
                         1: 'Receive timed out',
                         2: 'No connection was established',
                         3: 'Error accessing the USB driver',
                         4: 'Unknown Error',
                         5: 'Unknown Error',
                         6: 'Unknown Error',
                         7: 'Can''t connect device because already in use',
                         8: 'Unknown error',
                         9: 'Invalid device number used in call',
                         10: 'Parameter in fct. call is out of range',
                         11: 'Failed to open specified file',
                         12: 'Library has not been initialized',
                         13: 'Requested Feature is not enabled',
                         14: 'Requested Feature is not available'}

    def on_activate(self):
        """
        Starts up the qutau and performs sanity checks.
        """
        # Sanity check ConfigOptions
        if not self._digital_channels and not self._analog_channels:
            raise Exception('Not a single analog or digital channel provided in ConfigOptions.')
        self._digital_channels = natural_sort(str(chnl) for chnl in self._digital_channels)
        self._analog_channels = natural_sort(str(chnl) for chnl in self._analog_channels)

        if self._digital_channels:
            try:
                if len(self._digital_channels) != len(self._digital_event_rates):
                    if len(self._digital_event_rates) == 1:
                        tmp = self._digital_event_rates[0]
                        self._digital_event_rates = [i * tmp for i, _ in
                                                     enumerate(self._digital_channels, 1)]
                    else:
                        raise Exception('ConfigOption "digital_event_rates" must have same length '
                                        'as "digital_channels" or just be a single value.')
            except TypeError:
                self._digital_event_rates = [i * self._digital_event_rates for i, _ in
                                             enumerate(self._digital_channels, 1)]

        self.__sample_rate = self._constraints.combined_sample_rate.min
        self.__data_type = np.float64
        self.__stream_length = 0
        # self.__buffer_size = 20
        self.__use_circular_buffer = False
        self.__streaming_mode = StreamingMode.CONTINUOUS
        self.__active_channels = [1, 2]

        # Reset data buffer
        self._data_buffer = np.empty(0, dtype=self.__data_type)
        self._has_overflown = False
        self._is_running = False
        self._last_read = None
        self._start_time = None

        # initialize qutau
        ans = self.initialize()
        # activate digital channels
        self.set_channels(self.__active_channels)
        self.set_buffer_size(self.__buffer_size)
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self._has_overflown = False
        self._is_running = False
        self._last_read = None
        # Free memory if possible while module is inactive
        self._data_buffer = np.empty(0, dtype=self.__data_type)

        ans = self._dll.TDC_deInit()
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans
        return

    @property
    def sample_rate(self):
        """
        Read-only property to return the currently set sample rate

        @return float: current sample rate in Hz
        """
        return self.__sample_rate

    @sample_rate.setter
    def sample_rate(self, rate):
        if self._check_settings_change():
            if not self._clk_frequency_valid(rate):
                if self._analog_channels:
                    min_val = self._constraints.combined_sample_rate.min
                    max_val = self._constraints.combined_sample_rate.max
                else:
                    min_val = self._constraints.digital_sample_rate.min
                    max_val = self._constraints.digital_sample_rate.max
                self.log.warning(
                    'Sample rate requested ({0:.3e}Hz) is out of bounds. Please choose '
                    'a value between {1:.3e}Hz and {2:.3e}Hz. Value will be clipped to '
                    'the closest boundary.'.format(rate, min_val, max_val))
                rate = max(min(max_val, rate), min_val)
            self.__sample_rate = float(rate)
        return

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

    @buffer_size.setter
    def buffer_size(self, size):
        if self._check_settings_change():
            size = int(size)
            if size < 1:
                self.log.error('Buffer size smaller than 1 makes no sense. Tried to set {0} as '
                               'buffer size and failed.'.format(size))
                return
            self.__buffer_size = int(size)
            self._init_buffer()
        return

    @property
    def use_circular_buffer(self):
        """
        Read-only property to return a flag indicating if circular sample buffering is being used
        or not.

        @return bool: indicate if circular sample buffering is used (True) or not (False)
        """
        return self.__use_circular_buffer

    @use_circular_buffer.setter
    def use_circular_buffer(self, flag):
        if self._check_settings_change():
            if flag and not self._constraints.allow_circular_buffer:
                self.log.error('Circular buffer not allowed for this hardware module.')
                return
            self.__use_circular_buffer = bool(flag)
        return

    @property
    def streaming_mode(self):
        """
        Read-only property to return the currently configured streaming mode Enum.

        @return StreamingMode: Finite (StreamingMode.FINITE) or continuous
                               (StreamingMode.CONTINUOUS) data acquisition
        """
        return self.__streaming_mode

    @streaming_mode.setter
    def streaming_mode(self, mode):
        if self._check_settings_change():
            mode = StreamingMode(mode)
            if mode not in self._constraints.streaming_modes:
                self.log.error('Unknown streaming mode "{0}" encountered.\nValid modes are: {1}.'
                               ''.format(mode, self._constraints.streaming_modes))
                return
            self.__streaming_mode = mode
        return

    @property
    def number_of_channels(self):
        """
        Read-only property to return the currently configured number of data channels.

        @return int: the currently set number of channels
        """
        return len(self.__active_channels)

    @property
    def active_channels(self):
        """
        The currently configured data channel properties.
        Returns a dict with channel names as keys and corresponding StreamChannel instances as
        values.

        @return dict: currently active data channel properties with keys being the channel names
                      and values being the corresponding StreamChannel instances.
        """
        constr = self._constraints
        return (*(ch.copy() for ch in constr.digital_channels if ch.name in self.__active_channels),
                *(ch.copy() for ch in constr.analog_channels if ch.name in self.__active_channels))

    @active_channels.setter
    def active_channels(self, channels):
        if self._check_settings_change():
            channels = tuple(channels)
            avail_chnl_names = tuple(ch.name for ch in self.available_channels)
            if any(ch not in avail_chnl_names for ch in channels):
                self.log.error('Invalid channel to stream from encountered: {0}.\nValid channels '
                               'are: {1}'
                               ''.format(channels, avail_chnl_names))
                return
            self.__active_channels = channels
        return

    @property
    def available_channels(self):
        """
        Read-only property to return the currently used data channel properties.
        Returns a dict with channel names as keys and corresponding StreamChannel instances as
        values.

        @return tuple: data channel properties for all available channels with keys being the
                       channel names and values being the corresponding StreamChannel instances.
        """
        return (*(ch.copy() for ch in self._constraints.digital_channels),
                *(ch.copy() for ch in self._constraints.analog_channels))

    @property
    def available_samples(self):
        """
        Read-only property to return the currently available number of samples per channel ready
        to read from buffer.

        @return int: Number of available samples per channel
        """
        if not self.is_running:
            return 0
        return int((time.perf_counter() - self._last_read) * self.__sample_rate)

    @property
    def stream_length(self):
        """
        Property holding the total number of samples per channel to be acquired by this stream.
        This number is only relevant if the streaming mode is set to StreamingMode.FINITE.

        @return int: The number of samples to acquire per channel. Ignored for continuous streaming.
        """
        return self.__stream_length

    @stream_length.setter
    def stream_length(self, length):
        if self._check_settings_change():
            length = int(length)
            if length < 1:
                self.log.error('Stream_length must be a positive integer >= 1.')
                return
            self.__stream_length = length
        return

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        return self._is_running

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
                'streaming_mode': self.__streaming_mode,
                'active_channels': self.active_channels,
                'stream_length': self.__stream_length,
                'buffer_size': self.__buffer_size,
                'use_circular_buffer': self.__use_circular_buffer}

    def configure(self, sample_rate=None, streaming_mode=None, active_channels=None,
                  stream_length=None, buffer_size=None, use_circular_buffer=None):
        """
        Method to configure all possible settings of the data input stream.

        @param float sample_rate: The sample rate in Hz at which data points are acquired
        @param StreamingMode streaming_mode: The streaming mode to use (finite or continuous)
        @param iterable active_channels: Iterable of channel names (str) to be read from.
        @param int stream_length: In case of a finite data stream, the total number of
                                            samples to read per channel
        @param int buffer_size: The size of the data buffer to pre-allocate in samples per channel
        @param bool use_circular_buffer: Use circular buffering (True) or stop upon buffer overflow
                                         (False)

        @return dict: All current settings in a dict. Keywords are the same as kwarg names.
        """
        if self._check_settings_change():
            # Handle sample rate change
            if sample_rate is not None:
                self.sample_rate = sample_rate

            # Handle streaming mode change
            if streaming_mode is not None:
                self.streaming_mode = streaming_mode

            # Handle active channels
            if active_channels is not None:
                self.active_channels = active_channels

            # Handle total number of samples
            if stream_length is not None:
                self.stream_length = stream_length

            # Handle buffer size
            if buffer_size is not None:
                self.buffer_size = buffer_size

            # Handle circular buffer flag
            if use_circular_buffer is not None:
                self.use_circular_buffer = use_circular_buffer

        self._exp_time = int(1 / sample_rate * 1000)  # calculate the inverse clock_frequency in ms
        self.set_exposure_time(self._exp_time)

        return self.all_settings

    def get_constraints(self):
        """
        Return the constraints on the settings for this data streamer.

        @return DataInStreamConstraints: Instance of DataInStreamConstraints containing constraints
        """
        # print(self._constraints)
        return self._constraints.copy()

    def start_stream(self):
        """
        Start the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self.log.warning('Unable to start input stream. It is already running.')
            return 0

        self._init_buffer()
        self._is_running = True
        self._start_time = time.perf_counter()
        self._last_read = self._start_time
        return 0

    def stop_stream(self):
        """
        Stop the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self._is_running = False
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

        if buffer.ndim == 2:
            if buffer.shape[0] != self.number_of_channels:
                self.log.error('Configured number of channels ({0:d}) does not match first '
                               'dimension of 2D buffer array ({1:d}).'
                               ''.format(self.number_of_channels, buffer.shape[0]))
                return -1
            number_of_samples = buffer.shape[1] if number_of_samples is None else number_of_samples
            buffer = buffer.flatten()
        elif buffer.ndim == 1:
            number_of_samples = (
                    buffer.size // self.number_of_channels) if number_of_samples is None else number_of_samples
        else:
            self.log.error('Buffer must be a 1D or 2D numpy.ndarray.')
            return -1

        if number_of_samples < 1:
            return 0
        while self.available_samples < number_of_samples:
            time.sleep(0.001)
        # Check for buffer overflow
        avail_samples = self.available_samples
        if avail_samples > self.buffer_size:
            self._has_overflown = True

        offset = 0
        analog_x = np.arange(number_of_samples, dtype=self.__data_type) / self.__sample_rate
        analog_x *= 2 * np.pi
        analog_x += 2 * np.pi * (self._last_read - self._start_time)
        self._last_read = time.perf_counter()
        data = self.get_coinc_counters(number_of_samples)
        # for i, chnl in enumerate(self.__active_channels):
        #     if chnl in self._digital_channels:
        #         ch_index = self._digital_channels.index(chnl)
        #         events_per_bin = self._digital_event_rates[ch_index] / self.__sample_rate
        #         try:
        #             buffer = data # buffer[offset:(offset + number_of_samples)] = data[i]
        #             print(data.shape, buffer.shape)
        #         except ValueError:
        #             print(data.shape, buffer.shape, number_of_samples)
        #     else:
        #         ch_index = self._analog_channels.index(chnl)
        #         ch_index = self._analog_channels.index(chnl)
        #         amplitude = self._analog_amplitudes[ch_index]
        #         np.sin(analog_x, out=buffer[offset:(offset + number_of_samples)])
        #         buffer[offset:(offset + number_of_samples)] *= amplitude
        #         noise_level = 0.1 * amplitude
        #         buffer[offset:(offset + number_of_samples)] += data[i]
        #     offset += number_of_samples
        self._data_buffer = data
        return number_of_samples

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
            return np.empty((0, 0), dtype=self.data_type)

        if number_of_samples is None:
            read_samples = self.read_available_data_into_buffer(self._data_buffer)
            if read_samples < 0:
                return np.empty((0, 0), dtype=self.data_type)
        else:
            read_samples = self.read_data_into_buffer(self._data_buffer,
                                                      number_of_samples=number_of_samples)
            if read_samples != number_of_samples:
                return np.empty((0, 0), dtype=self.data_type)

        total_samples = self.number_of_channels * read_samples
        return self._data_buffer[:total_samples].reshape((self.number_of_channels,
                                                          number_of_samples))
        # data = self.get_coinc_counters()
        # counter_data = np.array([[data[0]]]) / self._exp_time * 1000
        # return counter_data

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
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return np.empty(0, dtype=self.__data_type)

        data = np.empty(self.number_of_channels, dtype=self.__data_type)
        analog_x = 2 * np.pi * (self._last_read - self._start_time)
        self._last_read = time.perf_counter()
        for i, chnl in enumerate(self.__active_channels):
            if chnl in self._digital_channels:
                ch_index = self._digital_channels.index(chnl)
                events_per_bin = self._digital_event_rates[ch_index] / self.__sample_rate
                data[i] = np.random.poisson(events_per_bin)
            else:
                ch_index = self._analog_channels.index(chnl)
                amplitude = self._analog_amplitudes[ch_index]
                noise_level = 0.05 * amplitude
                noise = noise_level - 2 * noise_level * np.random.rand()
                data[i] = amplitude * np.sin(analog_x) + noise
        return data

    # =============================================================================================
    def _clk_frequency_valid(self, frequency):
        if self._analog_channels:
            max_rate = self._constraints.combined_sample_rate.max
            min_rate = self._constraints.combined_sample_rate.min
        else:
            max_rate = self._constraints.digital_sample_rate.max
            min_rate = self._constraints.digital_sample_rate.min
        return min_rate <= frequency <= max_rate

    def _init_buffer(self):
        if not self.is_running:
            self._data_buffer = np.zeros(
                [self.number_of_channels, self.buffer_size],
                dtype=self.data_type)
            self._has_overflown = False
        return

    def _check_settings_change(self):
        """
        Helper method to check if streamer settings can be changed, i.e. if the streamer is idle.
        Throw a warning if the streamer is running.

        @return bool: Flag indicating if settings can be changed (True) or not (False)
        """
        if self.is_running:
            self.log.warning('Unable to change streamer settings while streamer is running. '
                             'New settings ignored.')
            return False
        return True

    def initialize(self):
        """Initialize QuTau '-1' enables all detected QuTau devices"""
        ans = self._dll.TDC_init(-1)

        if ans is not 0:
            print("Error in TDC_init: " + self.err_dict[ans])
        return ans

    def deInitialize(self):
        """Disconnect QuTau"""
        ans = self._dll.TDC_deInit()

        if ans is not 0:  # from the documentation: "never fails"
            print("Error in TDC_deInit: " + self.err_dict[ans])
        return ans

    def set_channels(self, channels=None):
        """Enables the channels of the qutau. The qutau needs a bitfield, where
        a channel corresponds to each activation flag of a bit.
        example channel 1,3,6 should be activated:
        bit (channel)  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
        arising bit    | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
        so the corresponding bitfield number is 10100100 starting with 2^0.
        The number passed to qutau is then 1 * 2^(1-1) + 1 * 2^(3-1) + 1 * 2^(6-1) = 1 + 4 + 32 = 37"""
        try:
            if channels is None:
                channels = self.__active_channels
        except TypeError:
            channels = [1]  # only activate first channel
        bitnumber = 0
        for channel in channels:
            bitnumber += 2 ** (channel - 1)
        print(bitnumber)
        error = self._dll.TDC_enableChannels(bitnumber)
        if error is not 0:
            print('Error in TDC_enableChannels' + self.err_dict[error])

    def setCoincidenceWindow(self, coincWin=None):
        """Set Coincidence Window.
            Sets the coincidence time window for the integrated coincidence counting. """
        if coincWin is None:
            coincWin = int(self._coincWin)
        ans = self._dll.TDC_setCoincidenceWindow(coincWin)
        if ans != 0:
            print("Error in TDC_setCoincidenceWindows: " + self.err_dict[ans])
        return 0

    def getDeviceParams(self):
        """Read Back Device Parameters.
        Reads the device parameters back from the device.
        All Parameters are output parameters but may be NULL-Pointers if the result is not required. """
        channels = ctypes.c_int32()
        coinc_window = ctypes.c_int32()
        exp_time = ctypes.c_int32()

        answer = self._dll.TDC_getDeviceParams(ctypes.byref(channels), ctypes.byref(coinc_window),
                                               ctypes.byref(exp_time))

        return answer, channels.value, coinc_window.value, exp_time.value

    def writeTimestamps(self, filename=None, fileformat=None):
        """
        At this stage the folder in which the qutau should write needs to be created before.
        fileformat:
        FILEFORMAT_ASCII = 0
        FILEFORMAT_BINARY = 1
        FILEFORMAT_COMPRESSED = 2
        FILEFORMAT_RAW = 3
        FILEFORMAT_NONE = 4 (to stop writing)"""
        if fileformat is None:
            fileformat = str(self._fileformat)
        if filename is None:
            filename = r'{}/test.bin'.format(str(self._filename))  # str(self._filename) + "/" + time.asctime() + ".bin"
        # filename = r'test.bin'
        filename = filename.encode('utf-8')
        # print(filename)
        ans = self._dll.TDC_writeTimestamps(filename, 1)
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans

    def stopwritingTimestamps(self):
        ans = self._dll.TDC_writeTimestamps('', 4)
        return ans

    def getBufferSize(self):
        """Read back Timestamp Buffer Size.
        Reads back the buffer size as set by TDC_setTimestampBufferSize. """
        sz = ctypes.c_int32()
        ans = self._dll.TDC_getTimestampBufferSize(ctypes.byref(sz))
        if ans != 0:
            print("Error in TDC_getTimestampBufferSize: " + self.err_dict[ans])
        return sz.value

    def set_buffer_size(self, size):
        """Set Timestamp Buffer Size.
        Sets the size of a ring buffer that stores the timestamps of the last detected events. The buffer's
        contents can be retrieved with TDC_getLastTimestamps. By default, the buffersize is 0. When the function
        is called, the buffer is cleared. """
        ans = self._dll.TDC_setTimestampBufferSize(size)
        if ans != 0:
            print("Error in TDC_setTimestampBufferSize: " + self.err_dict[ans])
        return ans

    def getLastTimestamps(self, reset=True):
        """
        Retrieve Last Timestamp Values.

        Retrieves the timestamp values of the last n detected events on all TDC channels. The buffer size must have
        been set with TDC_setTimestampBufferSize , otherwise 0 data will be returned.

        Parameters:

        reset	    If the data should be cleared after retrieving.

        timestamps	Output: Timestamps of the last events in base units, see TDC_getTimebase. The array must have at
                    least size elements, see TDC_setTimestampBufferSize . A NULL pointer is allowed to ignore the data.

        channels	Output: Numbers of the channels where the events have been detected. Every array element belongs
                    to the timestamp with the same index. Range is 0...7 for channels 1...8. The array must have at
                    least size elements, see TDC_setTimestampBufferSize . A NULL pointer is allowed to ignore the data.

        valid	    Output: Number of valid entries in the above arrays. May be less than the buffer size if the buffer
                    has been cleared.

        Returns
            TDC_Ok (never fails)

        """
        if self._number_of_gates:
            timestamps = np.zeros((self._number_of_gates, int(self._bufferSize)), dtype=np.int64)
            channels = np.zeros(int(self._bufferSize), dtype=np.int8)
            valid = ctypes.c_int32()

        else:
            timestamps = np.zeros(int(self._bufferSize), dtype=np.int64)
            channels = np.zeros(int(self._bufferSize), dtype=np.int8)
            valid = ctypes.c_int32()

        ans = self._dll.TDC_getLastTimestamps(reset, timestamps.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
                                              channels.ctypes.data_as(ctypes.POINTER(ctypes.c_int8)),
                                              ctypes.byref(valid))

        if ans != 0:  # "never fails"
            print("Error in TDC_getLastTimestamps: " + self.err_dict[ans])

        return timestamps, channels, valid.value

    def set_exposure_time(self, exp_time):
        """Set exposure time in units of ms between 0...65635 """
        ans = self._dll.TDC_setExposureTime(int(exp_time))
        if ans != 0:
            print("Error in TDC_setExposureTime: " + self.err_dict[ans])
        return ans

    def get_coinc_counters(self, number_of_samples):
        available_samples = number_of_samples
        if available_samples is not 0:
            self.set_exposure_time(1)
            counter = 0
            data_array = np.array([])
            while counter < self._exp_time * available_samples:
                data = np.zeros(int(19), dtype=np.int32)
                update = ctypes.c_int32()
                ans = self._dll.TDC_getCoincCounters(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                                                     ctypes.byref(update))
                if update.value == 1:
                    counter += update.value
                    data_array = np.append(data_array, data[0:len(self.available_channels)])
                elif update.value == 0:
                    counter += update.value
                else:
                    counter += 1
                    data_array = np.append(data_array, data[0:len(self.available_channels)])

            # print(counter, available_samples, self._exp_time)
            raw_data = data_array.reshape(self._exp_time * available_samples, len(self.available_channels)).transpose()
            return_data = np.empty((available_samples, len(self.available_channels)))
            increment = int(self._exp_time)
            try:
                for i in range(available_samples): #range(len(raw_data[0])//self._exp_time):
                    return_data[i] = np.sum(raw_data[:, increment * i:(i+1) * increment], axis=1)
            except ValueError:
                print(raw_data, available_samples, len(raw_data[0]//self._exp_time))

            return return_data.transpose()
        else:
            return np.empty((len(self.available_channels), 1))

        # return data_array.reshape(self._exp_time * available_samples, self.available_channels)

        # available_samples = self.available_samples()
        # if available_samples == 1:
        #     data = np.zeros(int(19), dtype=np.int32)
        #     update = ctypes.c_int32()
        #     ans = self._dll.TDC_getCoincCounters(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        #                                          ctypes.byref(update))
        #     return np.array(data)
        # else:
        #     self.set_exposure_time(self._exp_time * available_samples)
        #     data = np.zeros(int(19), dtype=np.int32)
        #     update = ctypes.c_int32()
        #     ans = self._dll.TDC_getCoincCounters(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        #                                          ctypes.byref(update))
        #     return np.array(data)
        # if update.value == 1:
        #     return np.array(data)
        # else:
        #     while update.value != 1:
        #         ans = self._dll.TDC_getCoincCounters(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        #                                              ctypes.byref(update))
        #     return np.array(data)
        # return np.array([np.random.randint(1, 30)])

    def on_deactivate(self):
        ans = self._dll.TDC_deInit()
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.

        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.

         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
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

        # Example for configuration with default values:

        constraints = dict()

        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seonds use the get_binwidth method.
        constraints['hardware_binwidth_list'] = []

        """
        constraints = self._constraints

        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seconds use the get_binwidth method.
        return constraints

    # def configure(self, bin_width_s, record_length_s, number_of_gates=0):
    #     """ Configuration of the fast counter.
    #
    #     @param float bin_width_s: Length of a single time bin in the time
    #                               trace histogram in seconds.
    #     @param float record_length_s: Total length of the timetrace/each
    #                                   single gate in seconds.
    #     @param int number_of_gates: optional, number of gates in the pulse
    #                                 sequence. Ignore for not gated counter.
    #
    #     @return tuple(binwidth_s, record_length_s, number_of_gates):
    #                 binwidth_s: float the actual set binwidth in seconds
    #                 gate_length_s: the actual record length in seconds
    #                 number_of_gates: the number of gated, which are accepted, None if not-gated
    #
    #     """
    #     self._number_of_gates = number_of_gates
    #     self._number_of_bins = int(np.rint(record_length_s / bin_width_s))
    #     # print(int(np.rint(record_length_s / bin_width_s)))
    #     self._bufferSize = int(np.rint(record_length_s / bin_width_s))
    #     ans = self.setBufferSize(self._bufferSize)
    #     self.counts_bin_array = np.zeros(self._number_of_bins)
    #     self.start = 0
    #     # if ans != 0:
    #     #     print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
    #     # return ans
    #
    #     # record_length_qutau = record_length_s
    #     # if self.gated:
    #     #     # add time to account for AOM delay
    #     #     no_of_bins = int((record_length_qutau + self.aom_delay) / self.set_binwidth(bin_width_s))
    #     # else:
    #     #     # subtract time to make sure no sequence trigger is missed
    #     #     no_of_bins = int((record_length_qutau - self.trigger_safety) / self.set_binwidth(bin_width_s))
    #     #
    #     # self.set_length(no_of_bins, preset=1, cycles=number_of_gates)
    #
    #     # if filename is not None:
    #     #     self._change_filename(filename)
    #
    #     return bin_width_s, record_length_s, number_of_gates

    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
      -1 = error state
        """
        return 1

    def start_measure(self):
        """ Start the fast counter. """
        # ans = self.writeTimestamps()
        ans = self.setBufferSize(self._bufferSize)
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans

    def stop_measure(self):
        """ Stop the fast counter. """
        # ans = self.stopwritingTimestamps()
        # if ans != 0:
        #     print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        # return ans
        pass

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        pass

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        pass

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return self.gated

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        return self.minimal_binwidth  # todo: maybe not correct

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        Return value is a numpy array (dtype = int64).
        The binning, specified by calling configure() in forehand, must be
        taken care of in this hardware class. A possible overflow of the
        histogram bins must be caught here and taken care of.
        If the counter is NOT GATED it will return a tuple (1D-numpy-array, info_dict) with
            returnarray[timebin_index]
        If the counter is GATED it will return a tuple (2D-numpy-array, info_dict) with
            returnarray[gate_index, timebin_index]

        info_dict is a dictionary with keys :
            - 'elapsed_sweeps' : the elapsed number of sweeps
            - 'elapsed_time' : the elapsed time in seconds

        If the hardware does not support these features, the values should be None
        """
        timestamp, channel_array, _ = self.getLastTimestamps()
        index_trigger = np.where(channel_array == self._trigger_channel)
        timestamp_trigger = timestamp[index_trigger]
        # trigger length in units of bin (0.081)
        trigger_length = np.diff(timestamp_trigger)
        # average_sequence_length = np.average(trigger_length)
        index_count = np.where(channel_array == self._count_channel)
        # calculate for each count event after a trigger event the time difference
        for ii, ch in enumerate(channel_array):
            if ch == self._trigger_channel:
                self.start = timestamp[ii]
            elif ch == self._count_channel:
                bin_number = timestamp[ii] - self.start
                if self._number_of_bins > bin_number > 0:
                    self.counts_bin_array[bin_number] += 1

        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': None}

        return self.counts_bin_array, info_dict

    # Slow Counter methods:

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = clock_frequency
        self._exp_time = int(1 / clock_frequency * 1000)  # calculate the inverse clock_frequency in ms
        self.setExposureTime(self._exp_time)

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
        if counter_channels is None:
            counter_channels = self._counter_channels
        else:
            self._counter_channels = counter_channels
        self.set_channels(counter_channels)

        channels = self.get_counter_channels()

        return 0

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array((n, uint32)): the photon counts per second for n channels
        """
        data = self.getCoincCounters()
        counter_data = np.array([[data[0]]]) / self._exp_time * 1000
        # time.sleep(1/self._clock_frequency)
        return counter_data

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """

        channel_array = []
        _, channels, _, _ = self.getDeviceParams()
        channels_string = '{0:b}'.format(channels)
        for ii, channel in enumerate(channels_string):
            if int(channel):
                channel_array.append(ii)
        return channel_array

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
