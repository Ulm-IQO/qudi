import ctypes as ct
import numpy as np
import time
from qtpy import QtCore
import os

from core.module import Base
from core.configoption import ConfigOption
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from interface.fast_counter_interface import FastCounterInterface


class Multiharp150(Base, FastCounterInterface):
    # From mhdefin.h
    _device_num = ConfigOption('deviceID', 0, missing='warn')
    syncChannelOffset = ConfigOption('syncChannelOffset', 0,
                                     missing='warn')  # you can change this (in ps, like a cable delay)
    inputChannelOffset = ConfigOption('inputChannelOffset', 0,
                                      missing='warn')  # you can change this (in ps, like a cable delay)
    LIB_VERSION = "2.0"
    MAXDEVNUM = 8
    MODE_HIST = 0
    MAXLENCODE = 6
    MAXINPCHAN = 16
    MAXHISTLEN = 65536
    FLAG_OVERFLOW = 0x0001

    # Measurement parameters, these are hardcoded since this is just a demo
    binning = 0  # you can change this
    offset = 0
    tacq = 360000000  # Measurement time in millisec, you can change this
    syncDivider = 1  # you can change this
    syncEdgeTrg = -50  # you can change this (in mV)
    inputEdgeTrg = -50  # you can change this (in mV)
    cmd = 0
    data = np.zeros([MAXINPCHAN, MAXHISTLEN], dtype=np.int32)
    dev = []
    libVersion = ct.create_string_buffer(b"", 8)
    hwSerial = ct.create_string_buffer(b"", 8)
    hwPartno = ct.create_string_buffer(b"", 8)
    hwVersion = ct.create_string_buffer(b"", 8)
    hwModel = ct.create_string_buffer(b"", 24)
    errorString = ct.create_string_buffer(b"", 40)
    numChannels = ct.c_int()
    histLen = ct.c_int()
    resolution = ct.c_double()
    syncRate = ct.c_int()
    countRate = ct.c_int()
    flags = ct.c_int()
    warnings = ct.c_int()
    warningstext = ct.create_string_buffer(b"", 16384)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        if os.name == "nt":
            self._dll = ct.WinDLL("mhlib64.dll")
        else:
            self._dll = ct.CDLL("libmh150.so")

    def error_code(self, retcode, funcName):
        if retcode < 0:
            self._dll.MH_GetErrorString(self.errorString, ct.c_int(retcode))
            print("MH_%s error %d (%s). Aborted." % (funcName, retcode,
                                                     self.errorString.value.decode("utf-8")))

    def on_activate(self):
        self.error_code(self._dll.MH_OpenDevice(ct.c_int(self._device_num), self.hwSerial), "OpenDevice")
        self.error_code(self._dll.MH_Initialize(ct.c_int(self._device_num), ct.c_int(self.MODE_HIST), ct.c_int(0)),
                        "Initialize")
        self.error_code(self._dll.MH_GetNumOfInputChannels(ct.c_int(self._device_num), ct.byref(self.numChannels)),
                        "GetNumOfInputChannels")

    def on_deactivate(self):
        self.error_code(self._dll.MH_CloseDevice(self._device_num), "CloseDevice")

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
        constraints['hardware_binwidth_list'] = list(0.080e-9 * (2 ** np.array(
            np.linspace(0, 23, 24))))
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

                    self.binning is set in base resolution
                    0 = 1 x base resolution
                    1 = 2 x base resolution
                    2 = 3 x base resolution
                    ...
        """
        self.binning = int(bin_width_s / 80e-12) - 1

        self.error_code(self._dll.MH_SetSyncDiv(ct.c_int(self._device_num), ct.c_int(self.syncDivider)), "SetSyncDiv")
        self.error_code(self._dll.MH_SetSyncEdgeTrg(ct.c_int(self._device_num), ct.c_int(self.syncEdgeTrg),
                                                    ct.c_int(1)), "SetSyncEdgeTrg")
        self.error_code(self._dll.MH_SetSyncChannelOffset(ct.c_int(self._device_num), ct.c_int(self.syncChannelOffset)),
                        "SetSyncChannelOffset")
        for i in range(0, self.numChannels.value):
            self.error_code(
                self._dll.MH_SetInputEdgeTrg(ct.c_int(self._device_num), ct.c_int(i), ct.c_int(self.inputEdgeTrg),
                                             ct.c_int(1)),
                "SetInputEdgeTrg"
            )

            self.error_code(
                self._dll.MH_SetInputChannelOffset(ct.c_int(self._device_num), ct.c_int(i),
                                                   ct.c_int(self.inputChannelOffset)),
                "SetInputChannelOffset"
            )

        self.error_code(
            self._dll.MH_SetHistoLen(ct.c_int(self._device_num), ct.c_int(self.MAXLENCODE), ct.byref(self.histLen)),
            "SetHistoLen")
        print("Histogram length is %d" % self.histLen.value)

        self.error_code(self._dll.MH_SetBinning(ct.c_int(self._device_num), ct.c_int(self.binning)), "SetBinning")
        self.error_code(self._dll.MH_SetOffset(ct.c_int(self._device_num), ct.c_int(self.offset)), "SetOffset")
        self.error_code(self._dll.MH_GetResolution(ct.c_int(self._device_num), ct.byref(self.resolution)),
                        "GetResolution")
        print("Resolution is %1.1lfps" % self.resolution.value)

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
        ctcstatus = ct.c_int()
        self.error_code(self._dll.MH_CTCStatus(ct.c_int(self._device_num), ct.byref(ctcstatus)), "CTCStatus")
        try:
            status = ctcstatus.value
            if status == 0:
                return 2
            elif status == 1:
                return 1
        except:
            return -1

    def start_measure(self):
        """ Start the fast counter. """
        self.error_code(self._dll.MH_ClearHistMem(ct.c_int(self._device_num)), "ClearHistMem")
        self.error_code(self._dll.MH_StartMeas(ct.c_int(self._device_num), ct.c_int(self.tacq)), "StartMeas")

    def stop_measure(self):
        """ Stop the fast counter. """
        self.error_code(self._dll.MH_StopMeas(ct.c_int(self._device_num)), "StopMeas")

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        self.error_code(self._dll.MH_StopMeas(ct.c_int(self._device_num)), "StopMeas")

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        self.error_code(self._dll.MH_StartMeas(ct.c_int(self._device_num), ct.c_int(self.tacq)), "StartMeas")

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        pass

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        pass

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
        self.error_code(self._dll.MH_GetAllHistograms(ct.c_int(self._device_num),
                                                      self.data.ctypes.data_as(ct.POINTER(ct.c_uint))), "GetHistogram")

        return self.data[0]
