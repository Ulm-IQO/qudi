# -*- coding: utf-8 -*-


import ctypes
import numpy as np
import logging


# =============================================================================
# Wrapper around the PHLib.DLL. The current file is based on the header files
# 'phdefin.h', 'phlib.h' and 'errorcodes.h'. The 'phdefin.h' contains all the
# constants and 'phlib.h' contains all the functions exported within the dll
# file. 'errorcodes.h' contains the possible error messages of the device.
#
# The wrappered commands are based on the PHLib Version 3.0. For further
# information read the manual
#       'PHLib - Programming Library for Custom Software Development'
# which can be downloaded from the PicoQuant homepage.
# =============================================================================
"""
The PicoHarp programming library PHLib.DLL is written in C and its data types
correspond to standard C/C++ data types as follows:

    char                    8 bit, byte (or characters in ASCII)
    short int               16 bit signed integer
    unsigned short int      16 bit unsigned integer
    int                     32 bit signed integer
    long int                32 bit signed integer
    unsigned int            32 bit unsigned integer
    unsigned long int       32 bit unsigned integer
    float                   32 bit floating point number
    double                  64 bit floating point number
"""




# Bitmask in hex.
# the comments behind each bitmask contain the integer value for the bitmask.
# You can check that by typing 'int(0x0001)' into the console to get the int.

#FEATURE_DLL     = 0x0001    #
#FEATURE_TTTR    = 0x0002    # 2
#FEATURE_MARKERS = 0x0004    # 4
#FEATURE_LOWRES  = 0x0008    # 8
#FEATURE_TRIGOUT = 0x0010    # 16
#
#FLAG_FIFOFULL   = 0x0003  # T-modes             # 3
#FLAG_OVERFLOW   = 0x0040  # Histomode           # 64
#FLAG_SYSERROR   = 0x0100  # Hardware problem    # 256

# The following are bitmasks for return values from GetWarnings()
#WARNING_INP0_RATE_ZERO          = 0x0001    #
#WARNING_INP0_RATE_TOO_LOW	    = 0x0002    #
#WARNING_INP0_RATE_TOO_HIGH      = 0x0004    #
#
#WARNING_INP1_RATE_ZERO		    = 0x0010    #
#WARNING_INP1_RATE_TOO_HIGH		= 0x0040    #
#
#WARNING_INP_RATE_RATIO			= 0x0100    #
#WARNING_DIVIDER_GREATER_ONE		= 0x0200    #
#WARNING_TIME_SPAN_TOO_SMALL     = 0x0400    #
#WARNING_OFFSET_UNNECESSARY      = 0x0800    #


class PicoHarp300():
    """Hardware class to control the Picoharp 300 from PicoQuant.

    This class is written according to the Programming Library Version 3.0
    """

    def __init__(self, deviceID, mode=0):

        self.errorcode = self._create_errorcode()

        # the library can communicate with 8 devices:
        self._connected_to_device = False
        self._deviceID = deviceID


        # Load the phlib64.dll from the folder <Windows>/System32/
        self.phlib = ctypes.windll.LoadLibrary('phlib64')

        try:
            self.open()
            self.initialize(mode)
        except:
            logging.error('Error loading Picoharp. In use? Check USB connection?')




    def activate(self):
        pass

    def _create_errorcode(self):
        """ Create a dictionary with the errorcode for the device.

        @return dict: errorcode in a dictionary

        The errorcode is extracted of PHLib  Ver. 3.0, December 2013. The
        errorcode can be also extracted by calling the get_error_string method
        with the appropriate integer value.
        """

        filename = 'errorcodes.h'
        try:
            with open(filename) as f:
                content = f.readlines()
        except:
            self.logMsg('No file "errorcodes.h" could be found in the '
                        'PicoHarp hardware directory!', msgType='error')

        errorcode = {}
        for line in content:
            if '#define ERROR' in line:
                errorstring, errorvalue = line.split()[-2:]
                errorcode[int(errorvalue)] = errorstring

        return errorcode

    def _set_constants(self):
        """Set the constants (max and min values) for the Picoharp300 device.
        These setting are taken from phdefin.h"""

        self.MODE_HIST = 0
        self.MODE_T2 = 2
        self.MODE_T3 = 3

        # in mV:
        self.ZCMIN = 0
        self.ZCMAX = 20
        self.DISCRMIN = 0
        self.DISCRMAX = 800
        self.PHR800LVMIN = -1600
        self.PHR800LVMAX = 2400

        # in ps:
        self.OFFSETMIN = 0
        self.OFFSETMAX = 1000000000
        self.SYNCOFFSMIN = -99999
        self.SYNCOFFSMAX	= 99999

        # in ms:
        self.ACQTMIN = 1
        self.ACQTMAX = 10*60*60*1000

        # in ns:
        self.HOLDOFFMAX = 210480

        self.BINSTEPSMAX = 8
        self.HISTCHAN = 65536    # number of histogram channels
        self.TTREADMAX = 131072  # 128K event records

    def check(self, func_val):
        """ Check routine for the received error codes.

        @param func int: return error code of the called function.

        @return int: pass the error code further so that other functions have
                     the possibility to use it."""

        if not func_val == 0:
            self.logMsg('Error in PicoHarp300 with errorcode {0}:\n'
                        '{1}'.format(func_val, self.errorcode[func_val]),
                        msgType='error')
        return func_val

    # =========================================================================
    # These two function below can be accessed without connection to device.
    # =========================================================================

    def get_version(self):
        """ Get the software/library version of the device.

        @return byte: string representation in byte (32bit-integers) of the
                      Version number of the current library."""
        buf = ctypes.create_string_buffer(16)
        self.check(self.phlib.PH_GetLibraryVersion(buf))
        return buf.value

    def get_error_string(self, errcode):
        """ Get the string error code from the Picoharp Device.

        @param int errcode: errorcode from 0 and below.

        @return byte: byte representation of the string error code.

        The stringcode for the error is the same as it is extracted from the
        errorcodes.h header file. Note that errcode should have the value 0
        or lower, since interger bigger 0 are not defined as error.
        """

        buf = ctypes.create_string_buffer(64)
        self.check(self.phlib.PH_GetErrorString(buf, errcode))
        return buf.value

    # =========================================================================
    # Establish the connection and initialize the device or disconnect it.
    # =========================================================================

    def open_connection(self):
        """ Open a connection to this device. """

        # The string buffer must be at least 8 chars.
        buf = ctypes.create_string_buffer(16)
        ret = self.check(self.phlib.PH_OpenDevice(self._deviceID, buf))
        self._serial = buf.value
        if ret >= 0:
            self._connected_to_device = True
            self.logMsg('Connection to the Picoharp 300 established',
                        msgType='status')

    def initialize(self, mode):
        """ Initialize the device with one of the three possible modes.

        @param int deviceID: a divice index from 0 to 7.
        @param int mode:    0: histogramming
                            2: T2
                            3: T3
        """
        if (mode != self.MODE_HIST) or (mode != self.MODE_T2) or \
           (mode != self.MODE_T3):
            self.logMsg('Picoharp: Mode for the device could not be set. It '
                        'must be {0}=Histogram-Mode, {1}=T2-Mode or '
                        '{2}=T3-Mode, but the mode {3} was '
                        'passed.'.format(self.MODE_HIST, self.MODE_T2,
                                         self.MODE_T3, mode),
                        msgType='error')
        else:
            self.check(self.phlib.PH_Initialize(self._deviceID, mode))

    def close_connection(self):
        """Close the connection to the device.

        @param int deviceID: a divice index from 0 to 7.
        """
        self._connected_to_device = False
        self.check(self.phlib.PH_CloseDevice(self._deviceID))
        self.logMsg('Connection to the Picoharp 300 closed.', msgType='status')

#    def __del__(self):
#        """ Delete the object PicoHarp300."""
#        self.close()

    # =========================================================================
    # All functions below can be used if the device was successfully called.
    # =========================================================================

    def get_hardware_version(self):
        """ Retrieve the device hardware information.

        @return tuple(3): (Model, Partnum, Version)
        """

        model = ctypes.create_string_buffer(32)     # at least 16 chars
        version = ctypes.create_string_buffer(16)   # at least 8 chars
        partnum = ctypes.create_string_buffer(16)   # at least 8 chars
        version = ctypes.create_string_buffer(16)   # at least 8 chars
        self.check(self.phlib.PH_GetHardwareVersion(self._deviceID, model,
                                                    partnum, version))

        return (model.value, partnum.value, version.value)

    def get_serial_number(self):
        """ Retrieve the serial number of the device.

        @return string: serial number of the device
        """

        serialnum = ctypes.create_string_buffer(16)   # at least 8 chars
        self.check(self.phlib.PH_GetSerialNumber(self._deviceID, serialnum))
        return serialnum.value

    def get_base_resolution(self):
        """ Retrieve the base resolution of the device.

        @return double: the base resolution of the device
        """
        res = ctypes.c_double()
        self.check(self.phlib.PH_GetBaseResolution(self._deviceID, res))
        return res.value

    def calibrate(self):
        """ Calibrate the device."""
        self.check(self.phlib.PH_Calibrate(self._deviceID))

    def get_features(self):
        """ Retrieve the possible features of the device.

        @return int: a bit pattern indicating the feature.
        """
        features = ctypes.c_int32()
        self.check(self.phlib.PH_GetFeatures(self._deviceID, features))
        return features.value

    def set_input_CFD(self, channel, level, zerocross):
        """
        @param int channel: number (0 or 1) of the input channel
        @param int level: CFD discriminator level in millivolts
        @param int zerocross: CFD zero cross in millivolts
        """
        channel = int(channel)
        level = int(level)
        zerocross = int(zerocross)
        if (channel != 0) and (channel != 1):
            self.logMsg('PicoHarp: Channal does not exist.\nChannel has to be '
                        '0 or 1 but {0} was passed.'.format(channel),
                        msgType='error')
            return
        if (level < self.DISCRMIN) or (self.DISCRMAX < level):
            self.logMsg('PicoHarp: Invalid CFD level.\nValue must be '
                        'within the range [{0},{1}] millivolts but a value of '
                        '{2} has been '
                        'passed.'.format(self.DISCRMIN, self.DISCRMAX, level),
                         msgType='error')
            return
        if (zerocross < self.ZCMIN) or (self.ZCMAX < zerocross):
            self.logMsg('PicoHarp: Invalid CFD zero cross.\nValue must be '
                        'within the range [{0},{1}] millivolts but a value of '
                        '{2} has been '
                        'passed.'.format(self.ZCMIN, self.ZCMAX, zerocross),
                         msgType='error')
            return

        self.check(self.phlib.PH_SetInputCFD(self._deviceID, channel,
                                             level, zerocross))


    def set_sync_div(self, div):
        """ Synchronize the devider of the device.

        @param int div: input rate devider applied at channel 0 (1,2,3, or 8)

        The sync devider must be used to keep the  effective sync rate at
        values <= 10MHz. It should only be used with sync sources of stable
        period. The readins obtained with PH_GetCountRate are corrected for the
        devider settin and deliver the external (undivided) rate.
        """
        self.check(self.phlib.PH_SetSyncDiv(self._deviceID, div))

    def set_sync_offset(self, offset):
        """ Set the offset of the synchronization.

        @param int offset: offset (time shift) in ps for that channel. That
                           value must lie within the range of SYNCOFFSMIN and
                           SYNCOFFSMAX.
        """
        offset = int(offset)
        if (offset < self.SYNCOFFSMIN) or (self.SYNCOFFSMAX < offset):
            self.logMsg('PicoHarp: Invalid Synchronization offset.\nValue must'
                        ' be within the range [{0},{1}] ps but a value of {2} '
                        'has been passed.'.format(self.SYNCOFFSMIN, self.SYNCOFFSMAX, offset),
                         msgType='error')
        else:
            self.check(self.phlib.PH_SetSyncOffset(self._deviceID, offset))


    def set_stop_overflow(self, stop_ovfl, stopcount):
        """ Stop the measurement if maximal amount of counts is reached.

        @param int stop_ovfl:  0 = do not stop,
                               1 = do stop on overflow
        @param int stopcount: count level at which should be stopped
                              (maximal 65535).

        This setting determines if a measurement run will stop if any channel
        reaches the maximum set by stopcount. If stop_ofl is 0 the measurement
        will continue but counts above 65535 in any bin will be clipped.
        """
        self.check(self.phlib.PH_SetStopOverflow(self._deviceID, stop_ovfl,
                                                 stopcount))

    def set_binning(self, binning):
        """ Set the base resolution of the measurement.

        @param int binning: binning code
                                minimum = 0 (smallest, i.e. base resolution)
                                maximum = (BINSTEPSMAX-1) (largest)

        The binning code corresponds to a power of 2, i.e.
            0 = base resolution,
            1 = 2x base resolution,
            2 = 4x base resolution,
            3 = 8x base resolution and so on.
        """
        if (binning < 0) or (self.BINSTEPSMAX-1 < binning):
            self.logMsg('PicoHarp: Invalid binning.\nValue must be within the '
                        'range [{0},{1}] bins, but a value of {2} has been '
                        'passed.'.format(0, self.BINSTEPSMAX, binning),
                         msgType='error')
        else:
            self.check(self.phlib.PH_SetRange(self._deviceID, binning))

    def set_multistop_enable(self, enable=True):
        """ Set whether multistops are possible within a measurement.

        @param bool enable: optional, Enable or disable the mutlistops.

        This is only for special applications where the multistop feature of
        the Picoharp is causing complications in statistical analysis. Usually
        it is not required to call this function. By default, multistop is
        enabled after PH_Initialize.
        """
        if enable:
            self.check(self.phlib.PH_SetMultistopEnable(self._deviceID, 1))
        else:
            self.check(self.phlib.PH_SetMultistopEnable(self._deviceID, 0))

    def set_offset(self, offset):
        """ Set an offset time.

        @param int offset: offset in ps (only possible for histogramming and T3
                           mode!). Value must be within [OFFSETMIN,OFFSETMAX].

        The true offset is an approximation fo the desired offset by the
        nearest multiple of the base resolution. This offset only acts on the
        difference between ch1 and ch0 in hitogramming and T3 mode. Do not
        confuse it with the input offsets!
        """
        if (offset <self.OFFSETMIN) or (self.OFFSETMAX < offset):
            self.logMsg('PicoHarp: Invalid offset.\nValue must be within the '
                        'range [{0},{1}] ps, but a value of {2} has been '
                        'passed.'.format(self.OFFSETMIN, self.OFFSETMAX, offset),
                         msgType='error')
        else:
            self.check(self.phlib.PH_SetOffset(self._deviceID, offset))

    def clear_hist_memory(self, block=0):
        """ Clear the histogram memory.

        @param int block: set which block number to clear.
        """
        self.check(self.phlib.PH_ClearHistMem(self._deviceID, block))

    def start(self, acq_time):
        """ Start acquisition for 'acq_time' ms.

        @param int acq_time: acquisition time in miliseconds. The value must be
                             be within the range [ACQTMIN,ACQTMAX].
        """
        if (acq_time < self.ACQTMIN) or (self.ACQTMAX < acq_time):
            self.logMsg('PicoHarp: No measurement could be started.\nThe '
                        'acquisition time must be within the range [{0},{1}] '
                        'ms, but a value of {2} has been passed.'.format(self.ACQTMIN, self.ACQTMAX, acq_time),
                         msgType='error')
        else:
            self.check(self.phlib.PH_StartMeas(self._deviceID, acq_time))

    def stop(self):
        """ Stop the measurement."""
        self.check(self.phlib.PH_StopMeas(self._deviceID))

    def get_status(self):
        """ Check the status of the device.

        @return int:  = 0: acquisition time still running
                      > 0: acquisition time has ended, measurement finished.
        """
        ctcstatus = ctypes.c_int32()
        self.check(self.phlib.PH_CTCStatus(self._deviceID, ctcstatus))
        return ctcstatus.value

    def get_histogram(self, block=0, xdata=True):
        """ Retrieve the measured histogram.

        @param int block: the block number to fetch (block >0 is only
                          meaningful with routing)
        @param bool xdata: if true, the x values in ns corresponding to the
                           read array will be returned.

        @return numpy.array[65536] or  numpy.array[65536], numpy.array[65536]:
                        depending if xdata = True, also the xdata are passed in
                        ns.

        """
        buf = np.zeros((self.HISTCHAN,), dtype=np.uint32)
        # buf.ctypes.data is the reference to the array in the memory.
        self.check(self.phlib.PH_GetBlock(self._deviceID, buf.ctypes.data, block))
        if xdata:
            xbuf = np.arange(self.HISTCHAN) * self.get_resolution() / 1000
            return xbuf, buf
        return buf

    def get_resolution(self):
        """ Retrieve the current resolution of the picohard.

        @return double: resolution at current binning.
        """

        resolution = ctypes.c_double()
        self.check(self.phlib.PH_GetResolution(self._deviceID, resolution))
        return resolution.value

    def get_count_rate(self, channel):
        """ Get the current count rate for the

        @param int channel: which input channel to read (0 or 1):

        @return int: count rate in ps.

        The hardware rate meters emply a gate time of 100ms. You must allow at
        least 100ms after PH_Initialize or PH_SetDyncDivider to get a valid
        rate meter reading. Similarly, wait at least 100ms to get a new
        reading. The readings are corrected for the snyc devider setting and
        deliver the external (undivided) rate. The gate time cannot be changed.
        The readings may therefore be inaccurate of fluctuating when the rate
        are very low. If accurate rates are needed you must perform a full
        blown measurement and sum up the recorded events.
        """
        if (channel !=0) or (channel != 1):
            self.logMsg('PicoHarp: Count Rate could not be read out, Channal '
                        'does not exist.\nChannel has to be 0 or 1 but {0} was '
                        'passed.'.format(channel),
                        msgType='error')
            return -1
        else:
            rate = ctypes.c_int32()
            self.check(self.phlib.PH_GetCountRate(self._deviceID, channel, rate))
            return rate.value

    def get_flags(self):
        """ Get the current status flag as a bit pattern.

        @return int: the current status flags (a bit pattern)

        Use the predefined bit mask values in phdefin.h (e.g. FLAG_OVERFLOW) to
        extract indiviual bits though a bitwise AND. It is also recommended to
        check for FLAG_SYSERROR to detect possible hardware failures. In that
        case you may want to call PH_GetHardwareDebugInfo and submit the
        results to support.
        """

        flags = ctypes.c_int32()
        self.check(self.phlib.PH_GetFlags(self._deviceID, flags))
        return flags.value

    def get_elepased_meas_time(self):
        """ Retrieve the elapsed measurement time in ms.

        @return double: the elapsed measurement time in ms.
        """
        elapsed = ctypes.c_double()
        self.check(self.phlib.PH_GetElapsedMeasTime(self._deviceID, elapsed))
        return elapsed.value

    def get_warnings(self):
        """Retrieve any warnings about the device or the current measurement.

        @return int: a bitmask for the warnings, as defined in phdefin.h

        NOTE: you have to call PH_GetCountRates for all channels prior to this
              call!
        """
        warnings = ctypes.c_int32()
        self.check(self.phlib.PH_GetWarnings(self._deviceID, warnings))
        return warnings.value

    def get_warnings_text(self, warning_num):
        """Retrieve the warningtext for the corresponding warning bitmask.

        @param int warning_num: the number for which you want to have the
                                warning text.
        @return char[32568]: the actual text of the warning.

        """
        text = ctypes.create_string_buffer(32568) # buffer at least 16284
        self.check(self.phlib.PH_GetWarningsText(self._deviceID, warning_num, text))
        return text.value

    def get_hardware_debug_info(self):
        """ Retrieve the debug information for the current hardware.

        @return char[32568]: the information for debugging.
        """
        debuginfo = ctypes.create_string_buffer(32568) # buffer at least 16284
        self.check(self.phlib.PH_GetHardwareDebugInfo(self._deviceID, debuginfo))
        return debuginfo.value

    # =========================================================================
    #  Special functions for Time-Tagged Time Resolved mode
    # =========================================================================
    # To check whether you can use the TTTR mode (must be purchased in
    # addition) you can call PH_GetFeatures to check.

    def tttr_read_fifo(self, num_counts):
        """ Read out the buffer of the FIFO.

        @param int num_counts: number of TTTR records to be fetched. Maximal
                               TTREADMAX

        @return tuple (counts, actual_num_counts):
                    counts = data array where the TTTR data are stored.
                    actual_num_counts = how many numbers of TTTR could be
                                        actually be read out. THIS NUMBER IS
                                        NOT CHECKED FOR PERFORMANCE REASONS, SO
                                        BE  CAREFUL!

        Must not be called with count larger than buffer size permits. CPU time
        during wait for completion will be yielded to other processes/threads.
        Function will return after a timeout period of 80 ms even if not all
        data could be fetched. Return value indicates how many records were
        fetched. Buffer must not be accessed until the function returns!
        """
        counts = np.zeros(num_counts, dtype=np.uint32)
        actual_num_counts = ctypes.c_int32()
        # counts.ctypes.data is the reference to the array in the memory.
        self.check(self.phlib.PH_TTReadData(self._deviceID, counts.ctypes.data,
                                            num_counts, actual_num_counts))

        return (counts, actual_num_counts)

    def tttr_set_marker_edges(self, me0, me1, me2, me3):
        """ Set the marker edges

        @param int me<n>:   active edge of marker signal <n>,
                                0 = falling
                                1 = rising

        PicoHarp devices prior to hardware version 2.0 support only the first
        three markers. Default after Initialize is all rising, i.e. set to 1.
        """

        if (me0 != 0) or (me0 != 1) or (me1 != 0) or (me1 != 1) or \
           (me2 != 0) or (me2 != 1) or (me3 != 0) or (me3 != 1):

            self.logMsg('PicoHarp: All the marker edges must be either 0 or '
                        '1, but the current marker settings were passed:\n'
                        'me0={0}, me1={1}, '
                        'me2={2}, me3={3},'.format(me0, me1, me2, me3),
                         msgType='error')
            return
        else:
            self.check(self.phlib.PH_TTSetMarkerEdges(self._deviceID, me0, me1,
                                                      me2, me3))

    def tttr_set_marker_enable(self, me0, me1, me2, me3):
        """ Set the marker enable or not.

        @param int me<n>:   enabling of marker signal <n>,
                                0 = disabled
                                1 = enabled

        PicoHarp devices prior to hardware version 2.0 support only the first
        three markers. Default after Initialize is all rising, i.e. set to 1.
        """

        if (me0 != 0) or (me0 != 1) or (me1 != 0) or (me1 != 1) or \
           (me2 != 0) or (me2 != 1) or (me3 != 0) or (me3 != 1):

            self.logMsg('PicoHarp: Could not set marker enable.\n'
                        'All the marker options must be either 0 or 1, but '
                        'the current marker settings were passed:\n'
                        'me0={0}, me1={1}, '
                        'me2={2}, me3={3},'.format(me0, me1, me2, me3),
                         msgType='error')
            return
        else:
            self.check(self.phlib.PH_TTSetMarkerEnable(self._deviceID, me0,
                                                       me1, me2, me3))

    def tttr_set_marker_holdofftime(self, holfofftime):
        """ Set the holdofftime for the markers.

        @param int holdofftime: holdofftime in ns. Maximal value is HOLDOFFMAX.

        This setting can be used to clean up gliches on the marker signals.
        When set to X ns then after detecting a first marker edge the next
        marker will not be accepted before x ns. Observe that the internal
        granularity of this time is only about 50ns. The holdoff time is set
        equally for all marker inputs but the holdoff logic acts on each
        marker independently.
        """

        if (holfofftime < 0) or (self.HOLDOFFMAX < holfofftime):
            self.logMsg('PicoHarp: Holdofftime could not be set.\n'
                        'Value of holdofftime must be within the range '
                        '[0,{0}], but a value of {1} '
                        'was passed.'.format(self.HOLDOFFMAX, holfofftime),
                        msgType='error')
        else:
            self.check(self.phlib.PH_SetMarkerHoldofftime(self._deviceID,
                                                          holfofftime))





    # FIXME: routing functions not yet wrapped, but will be wrapped if it will
    # be necessary to use them.
