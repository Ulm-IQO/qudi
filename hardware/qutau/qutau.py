import ctypes
import numpy as np
import time
from qtpy import QtCore
import ctypes

from core.module import Base
from core.configoption import ConfigOption
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from interface.simple_data_interface import SimpleDataInterface

from core.module import Base
from interface.fast_counter_interface import FastCounterInterface


# from core.interface import interface_method


class Qutau(Base, FastCounterInterface):
    """
    This is just a dummy hardware class to be used with SimpleDataReaderLogic.
    This is a dummy config file:
        fastcounter_qutau:
            module.Class: 'qutau.qutau.Qutau'
            deviceID: -1
            activeChannels: [1, 2]
            coincidenceWindow: 0
            fileformat: 'FORMAT_ASCII'
            filename: 'C:/Data/qutau/binary'
            minimal_binwidth: 0.081e-9
            gated: False
            aom_delay: 400e-9
    """
    _deviceId = ConfigOption('deviceID', 0, missing='warn')
    _activeChannels = ConfigOption('activeChannels', 0, missing='warn')
    _coincWin = ConfigOption('coincidenceWindow', 0, missing='warn')
    _fileformat = ConfigOption('fileformat', 0, missing='warn')
    _filename = ConfigOption('filename', 0, missing='warn')
    _bufferSize = 500
    minimal_binwidth = ConfigOption('minimal_binwidth', missing='warn')
    gated = ConfigOption('gated', False, missing='warn')
    aom_delay = ConfigOption('aom_delay', 400e-9, missing='warn')
    _trigger_channel = 1  # means channel 2
    _count_channel = 0  # means channel 1
    _number_of_bins = 100

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
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

    def Initialize(self, id=_deviceId):
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

    def setChannels(self, channels=None):
        """Enables the channels of the qutau. The qutau needs a bitfield, where
        a channel corresponds to each activation flag of a bit.
        example channel 1,3,6 should be activated:
        bit (channel)  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
        arising bit    | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
        so the corresponding bitfield number is 10100100 starting with 2^0.
        The number passed to qutau is then 1 * 2^(1-1) + 1 * 2^(3-1) + 1 * 2^(6-1) = 1 + 4 + 32 = 37"""
        if channels is None:
            channels = list(self._activeChannels)
        bitnumber = 0
        for channel in channels:
            bitnumber += 2 ** (channel - 1)

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
        print(filename)
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

    def setBufferSize(self, size):
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

    def on_activate(self):
        ans = self.Initialize()
        self.setChannels()
        self.setBufferSize(500)
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
        constraints['max_sweep_len'] = 6.8 # todo add correct max sweep length
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
        self._bufferSize = int(np.rint(record_length_s / bin_width_s))
        ans = self.setBufferSize(self._bufferSize)
        self.counts_bin_array = np.zeros(self._number_of_bins)
        self.start = 0
        # if ans != 0:
        #     print("Error in TDC_writeTimestamps: " + self.err_dict[ans])
        # return ans

        # record_length_qutau = record_length_s
        # if self.gated:
        #     # add time to account for AOM delay
        #     no_of_bins = int((record_length_qutau + self.aom_delay) / self.set_binwidth(bin_width_s))
        # else:
        #     # subtract time to make sure no sequence trigger is missed
        #     no_of_bins = int((record_length_qutau - self.trigger_safety) / self.set_binwidth(bin_width_s))
        #
        # self.set_length(no_of_bins, preset=1, cycles=number_of_gates)

        # if filename is not None:
        #     self._change_filename(filename)

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
            else:
                bin_number = timestamp[ii] - self.start
                if self._number_of_bins > bin_number > 0:
                    self.counts_bin_array[bin_number] += 1

        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': None}

        return self.counts_bin_array, info_dict
