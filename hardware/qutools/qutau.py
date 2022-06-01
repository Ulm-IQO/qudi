import ctypes
import numpy as np
import time
from qtpy import QtCore
import ctypes
import threading

from core.module import Base
from core.configoption import ConfigOption
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from interface.simple_data_interface import SimpleDataInterface

from core.module import Base
from interface.fast_counter_interface import FastCounterInterface
# from interface.slow_counter_interface import SlowCounterInterface, SlowCounterConstraints, CountingMode


# from core.interface import interface_method


class Qutau(Base, FastCounterInterface):
    """
    This is a hardware file to be used with qutau from qutools.
    This is a dummy config file for qutau:
        fastcounter_qutau:
            module.Class: 'qutools.qutau.Qutau'
            deviceID: -1
            activeChannels: [1, 2]
            count_channel: 0
            trigger_channel: 1
            coincidenceWindow: 0
            fileformat: 'FORMAT_ASCII'
            filename: 'C:/Data/qutau/binary'
            minimal_binwidth: 0.081e-9
            gated: False

    Count channel 0 means channel 1 and trigger channel 1 means channel 2 and so on...
    Load the Qutau library file tdcbase.dll. Can be found on the server or in the directory of the qutau software
    in programs files folder and should be placed in <Windows>/System32/
    Or simply install the software gui from qutau.
    """
    _deviceId = ConfigOption('deviceID', 0, missing='warn')
    _activeChannels = ConfigOption('activeChannels', 0, missing='warn')
    _coincWin = ConfigOption('coincidenceWindow', 0, missing='warn')
    _fileformat = ConfigOption('fileformat', 0, missing='warn')
    _filename = ConfigOption('filename', 0, missing='warn')
    _bufferSize = 500
    minimal_binwidth = ConfigOption('minimal_binwidth', missing='warn')
    gated = ConfigOption('gated', False, missing='warn')
    _trigger_channel = ConfigOption('trigger_channel', missing='warn')
    _count_channel = ConfigOption('count_channel', missing='warn')
    _number_of_bins = 100
    _clock_frequency = ConfigOption('clock_frequency', missing='warn')
    _samples_number = ConfigOption('samples_number', missing='warn')
    _counter_channels = ConfigOption('counter_channels', missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.hardware_thread = QtCore.QThread()
        self._start_measure = False
        self._threadlock = Mutex()
        self._dll = ctypes.windll.LoadLibrary('tdcbase')
        self._number_of_gates = 0
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

    def initialize(self, id=_deviceId):
        """Initialize QuTau '-1' enables all detected QuTau devices"""
        ans = self._dll.TDC_init(-1)

        if ans is not 0:
            print("Error in TDC_init: " + self.err_dict[ans])
        return ans

    def de_initialize(self):
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
                channels = list(self._activeChannels)
        except TypeError:
            channels = [1]  # only activate first channel
        bitnumber = 0
        for channel in channels:
            bitnumber += 2 ** (channel - 1)

        ans = self._dll.TDC_enableChannels(bitnumber)
        if ans is not 0:
            print('Error in TDC_enableChannels' + self.err_dict[ans])

    def set_coincidence_window(self, coincWin=None):
        """Set Coincidence Window.
            Sets the coincidence time window for the integrated coincidence counting. """
        if coincWin is None:
            coincWin = int(self._coincWin)
        ans = self._dll.TDC_setCoincidenceWindow(coincWin)
        if ans != 0:
            print("Error in TDC_setCoincidenceWindows: " + self.err_dict[ans])
        return 0

    def get_device_params(self):
        """Read Back Device Parameters.
        Reads the device parameters back from the device.
        All Parameters are output parameters but may be NULL-Pointers if the result is not required. """
        channels = ctypes.c_int32()
        coinc_window = ctypes.c_int32()
        exp_time = ctypes.c_int32()

        answer = self._dll.TDC_getDeviceParams(ctypes.byref(channels), ctypes.byref(coinc_window),
                                               ctypes.byref(exp_time))

        return answer, channels.value, coinc_window.value, exp_time.value

    def write_timestamps(self, filename=None, fileformat=None):
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
        print(filename)
        ans = self._dll.TDC_writeTimestamps(filename, 1)
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans

    def stop_writing_timestamps(self):
        ans = self._dll.TDC_writeTimestamps('', 4)
        return ans

    def get_buffer_size(self):
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
        # print(size)
        ans = self._dll.TDC_setTimestampBufferSize(size)
        if ans != 0:
            print("Error in TDC_setTimestampBufferSize: " + self.err_dict[ans])
        return ans

    def get_last_timestamps(self, reset=True):
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
            timestamps = np.zeros(int(self._bufferSize),
                                  dtype=np.int64)  # np.concatenate(np.zeros((self._number_of_gates, int(self._bufferSize)), dtype=np.int64))
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

        return timestamps.value, channels.value, valid.value

    def set_exposure_time(self, expTime):
        """Set exposure time in units of ms between 0...65635 """
        ans = self._dll.TDC_setExposureTime(int(expTime))
        if ans != 0:
            print("Error in TDC_setExposureTime: " + self.err_dict[ans])
        return ans

    def get_coinc_counters(self):
        data = np.zeros(int(19), dtype=np.int32)
        update = ctypes.c_int32()
        ans = self._dll.TDC_getCoincCounters(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                                             ctypes.byref(update))
        if update.value == 1:
            return np.array(data)
        else:
            while update.value != 1:
                ans = self._dll.TDC_getCoincCounters(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                                                     ctypes.byref(update))
            return np.array(data)
        # return np.array([np.random.randint(1, 30)])

    def set_signal_conditioning(self, channel, conditioning, edge, term, threshold):
        if edge:
            edge_value = 1  # True: Rising
        else:
            edge_value = 0  # False: Falling
        # conditioning
        # self.SCOND_TTL= 1
        # self. SCOND_LVTTL = 2
        # self. SCOND_NIM = 3
        # self. SCOND_MISC = 4
        # scond_none = 5
        ans = self._dll.TDC_configureSignalConditioning(channel, conditioning, edge_value, term, threshold)
        if ans != 0:
            print("Error in TDC_configureSignalConditioning: " + self.err_dict[ans])
        return ans

    def enable_start_stop(self, enable):
        """Enable Start Stop Histograms.

        Enables the calculation of start stop histograms. When enabled, all incoming events contribute to the
        histograms. When disabled, all corresponding functions are unavailable. Disabling saves a relevant amount of
        memory and CPU load. The function implicitly clears the histograms. Use TDC_freezeBuffers to interrupt the
        accumulation of events without clearing the functions and TDC_clearAllHistograms to clear without interrupt. """
        if enable:
            ena_value = 1
        else:
            ena_value = 0
        ans = self._dll.TDC_enableStartStop(ena_value)
        if ans != 0:
            print("Error in TDC_enableStartStop: " + self.err_dict[ans])
        return ans

    def set_histogram_params(self, binWidth, binCount):
        """Set Start Stop Histogram Parameters.

        Sets parameters for the internally generated start stop histograms. If the function is not called,
        default values are in place. When the function is called, all collected histogram data are cleared. """
        self._StartStopBinCount = binCount
        ans = self._dll.TDC_setHistogramParams(binWidth, binCount)
        if ans != 0:
            print("Error in TDC_setHistogramParams: " + self.err_dict[ans])
        return ans

    def get_histogram_params(self):
        """Read back Start Stop Histogram Parameters.

        Reads back the parameters that have been set with TDC_setHistogramParams. All output parameters may be NULL
        to ignore the value. """
        binWidth = ctypes.c_int32()
        binCount = ctypes.c_int32()
        ans = self._dll.TDC_getHistogramParams(ctypes.byref(binWidth), ctypes.byref(binCount))
        if ans != 0:
            print("Error in TDC_getHistogramParams: " + self.err_dict[ans])
        return (binWidth.value, binCount.value)

    def clear_all_histograms(self):
        ans = self._dll.TDC_clearAllHistograms()
        if ans != 0:
            print("Error in TDC_clearAllHistograms: " + self.err_dict[ans])
        return ans

    def get_histogram(self, chanA, chanB, reset):
        """Clear Start Stop Histograms.

        Clears all internally generated start stop histograms, i.e. all bins are set to 0. """
        if reset:
            reset_value = 1
        else:
            reset_value = 0
        data = np.zeros(self._StartStopBinCount, dtype=np.int32)
        count = ctypes.c_int32()
        tooSmall = ctypes.c_int32()
        tooLarge = ctypes.c_int32()
        starts = ctypes.c_int32()
        stops = ctypes.c_int32()
        expTime = ctypes.c_int64()
        ans = self._dll.TDC_getHistogram(chanA, chanB, reset_value,
                                         data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                                         ctypes.byref(count), ctypes.byref(tooSmall), ctypes.byref(tooLarge),
                                         ctypes.byref(starts), ctypes.byref(stops), ctypes.byref(expTime))
        if ans != 0:
            print("Error in TDC_getHistogram: " + self.err_dict[ans])

        return data, count.value, tooSmall.value, tooLarge.value, starts.value, stops.value, expTime.value

    def freeze_buffers(self, freeze):
        """Freeze internal Buffers.

        The function can be used to freeze the internal buffers, allowing to retrieve multiple histograms with the
        same integration time. When frozen, no more events are added to the built-in histograms and timestamp buffer.
        The coincidence counters are not affected. Initially, the buffers are not frozen. All types of histograms
        calculated by software are affected. """
        if freeze:
            freeze_value = 1
        else:
            freeze_value = 0
        ans = self._dll.TDC_freezeBuffers(freeze_value)
        if ans != 0:
            print("Error in TDC_freezeBuffers: " + self.err_dict[ans])

        return ans

    def on_activate(self):
        ans = self.initialize()
        # self.set_signal_conditioning(0, 2, 1, 1, 2)
        # self.set_signal_conditioning(1, 2, 1, 1, 2)
        # self.set_signal_conditioning(2, 3, False, 1)
        self.set_channels()
        self.set_buffer_size(500)
        if ans != 0:
            print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        return ans

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
        constraints = dict()

        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seconds use the get_binwidth method.
        constraints['hardware_binwidth_list'] = list(0.081e-9 * (2 ** np.array(
            np.linspace(0, 24, 25))))
        constraints['max_sweep_len'] = 6.8  # todo add correct max sweep length
        return constraints

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time
                                  trace histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each
                                      single gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, record_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual record length in seconds
                    number_of_gates: the number of gated, which are accepted, None if not-gated

        """
        self._number_of_gates = number_of_gates
        self._number_of_bins = int(np.rint(record_length_s / bin_width_s))
        # print(int(np.rint(record_length_s / bin_width_s)))
        self._bufferSize = int(np.rint(record_length_s / bin_width_s)) # calculate the lenght of the histogram array
        # in multiples of bin
        self._bin_size = int(bin_width_s / 81e-12)  # calculate the binning size in multiples of smallest bin size
        self.enable_start_stop(1)  # enable the start stop measurement
        self.set_histogram_params(self._bin_size, self._bufferSize)  # set the bin size and buffer size

        return bin_width_s, record_length_s, number_of_gates

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
        self.enable_start_stop(1)  # enable start stop histogram of qutau
        self.set_histogram_params(self._bin_size, self._bufferSize)  # set the histo params as above in config
        self.freeze_buffers(0)  # release buffers to start histogram exposure

    def stop_measure(self):
        """ Stop the fast counter. """
        self.freeze_buffers(1)  # freezes all buffers
        self.enable_start_stop(0)  # stops all histogramms and clears the histo-buffer

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        self.freeze_buffers(1)  # freeze buffers

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        self.freeze_buffers(0)  # release buffers

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
        #return self.minimal_binwidth  # todo: maybe not correct

        return self._bin_size * 81e-12

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
        data, count, tooSmall, tooLarge, starts, stops, expTime = self.get_histogram(self._trigger_channel,
                                                                                     self._count_channel, 0)
        self.counts_bin_array = data
        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': None}

        return self.counts_bin_array, info_dict

    # Slow Counter methods:
    #
    # def get_constraints(self): # todo two get_constraints functions
    #     """ Retrieve the hardware constrains from the counter device.
    #
    #     @return SlowCounterConstraints: object with constraints for the counter
    #     """
    #     constraints = SlowCounterConstraints() #todo in init
    #     constraints.max_detectors = 8
    #     constraints.min_count_frequency = 0.01526
    #     constraints.max_count_frequency = 1000
    #     constraints.counting_mode = [CountingMode.CONTINUOUS]  # todo not sure
    #
    #     return constraints

    # def set_up_clock(self, clock_frequency=None, clock_channel=None):
    #     """ Configures the hardware clock of the NiDAQ card to give the timing.
    #
    #     @param float clock_frequency: if defined, this sets the frequency of the clock
    #     @param string clock_channel: if defined, this is the physical channel of the clock
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     self._clock_frequency = clock_frequency
    #     self._exp_time = int(1 / clock_frequency * 1000)  # calculate the inverse clock_frequency in ms
    #     self.set_exposure_time(self._exp_time)
    #
    #     return 0

    # def set_up_counter(self,
    #                    counter_channels=None,
    #                    sources=None,
    #                    clock_channel=None,
    #                    counter_buffer=None):
    #     """ Configures the actual counter with a given clock.
    #
    #     @param list(str) counter_channels: optional, physical channel of the counter
    #     @param list(str) sources: optional, physical channel where the photons
    #                                photons are to count from
    #     @param str clock_channel: optional, specifies the clock channel for the
    #                               counter
    #     @param int counter_buffer: optional, a buffer of specified integer
    #                                length, where in each bin the count numbers
    #                                are saved.
    #
    #     @return int: error code (0:OK, -1:error)
    #
    #     There need to be exactly the same number sof sources and counter channels and
    #     they need to be given in the same order.
    #     All counter channels share the same clock.
    #     """
    #     if counter_channels is None:
    #         counter_channels = self._counter_channels
    #     else:
    #         self._counter_channels = counter_channels
    #     self.setChannels(counter_channels)
    #
    #     channels = self.get_counter_channels()
    #
    #     return 0

    # def get_counter(self, samples=None):
    #     """ Returns the current counts per second of the counter.
    #
    #     @param int samples: if defined, number of samples to read in one go
    #
    #     @return numpy.array((n, uint32)): the photon counts per second for n channels
    #     """
    #     data = self.get_coinc_counters()
    #     counter_data = np.array([[data[0]]]) / self._exp_time * 1000
    #
    #     return counter_data

    # def get_counter_channels(self):
    #     """ Returns the list of counter channel names.
    #
    #     @return list(str): channel names
    #
    #     Most methods calling this might just care about the number of channels, though.
    #     """
    #
    #     channel_array = []
    #     _, channels, _, _ = self.getDeviceParams()
    #     channels_string = '{0:b}'.format(channels)
    #     for ii, channel in enumerate(channels_string):
    #         if int(channel):
    #             channel_array.append(ii)
    #
    #     return channel_array

    # def close_counter(self):
    #     """ Closes the counter and cleans up afterwards.
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     return 0
    #
    # def close_clock(self):
    #     """ Closes the clock and cleans up afterwards.
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     return 0
