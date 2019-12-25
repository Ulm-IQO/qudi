# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware module for the HydraHarp400.

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

from core.module import Base
from core.configoption import ConfigOption
from core.util.modules import get_main_dir
from interface.fast_counter_interface import FastCounterInterface
import time
import os
import numpy as np
import ctypes

# =============================================================================
# Wrapper around the HHLib.DLL. The current file is based on the header files
# 'hhdefin.h', 'hhlib.h' and 'errorcodes.h'. The 'hhdefin.h' contains all the
# constants and 'hhlib.h' contains all the functions exported within the dll
# file. 'errorcodes.h' contains the possible error messages of the device.
#
# The wrappered commands are based on the hHLib Version 3.0.0.2 For further
# information read the manual
#       'HHLib - Programming Library for Custom Software Development'
# which can be downloaded from the PicoQuant homepage.
# TODO GATED mode, also pause by HH400 not possible
# =============================================================================
"""
The PicoHarp programming library HHLib.DLL is written in C and its data types
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

class HydraHarp400(Base, FastCounterInterface):
    """ Hardware class to control the HydraHarp 400 from PicoQuant.

    This class is written according to the Programming Library Version 3.0

    Example config for copy-paste:

    fastcounter_hydraharp400:
        module.Class: 'picoquant.hydraharp400.hydraharp400.HydraHarp400'
        deviceID: 0 # a device index from 0 to 7.
        mode: 0 # 0: histogram mode, 2: T2 mode, 3: T3 mode, 8: continuous mode
        
    """
    _modclass = 'HydraHarp400'
    _modtype = 'hardware'

    _deviceID = ConfigOption('deviceID', 0, missing='warn') # a device index from 0 to 7.
    _mode = ConfigOption('mode', 0, missing='warn')
    _refsource = ConfigOption('refsource', 0, missing='warn')

    gated = ConfigOption('gated', False, missing='warn')
    trigger_safety = ConfigOption('trigger_safety', 400e-9, missing='warn') #FIXME need check exact value
    aom_delay = ConfigOption('aom_delay', 390e-9, missing='warn')
    minimal_binwidth = ConfigOption('minimal_binwidth', 1e-12, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._set_constants()
        self.connected_to_device = False

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

        #this variable has to be added because there is no difference
        #in the fastcomtec it can be on "stopped" or "halt"
        self.stopped_or_halt = "stopped"
        self.timetrace_tmp = []


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self.dll = ctypes.windll.LoadLibrary('C:\Windows\System32\hhlib64.dll')
        serial = ctypes.create_string_buffer(8)
        dev=[]
        # Check the availability of the configured Pico Quant device
        op = self.dll.HH_OpenDevice(ctypes.c_int(self._deviceID), serial)
        if op == 0:
            ini = self.dll.HH_Initialize(ctypes.c_int(self._deviceID), ctypes.c_int(self._mode), ctypes.c_int(self._refsource))
        else:
            # search available Pico Quant device
            # unplug or replug of PQ device, could change the device ID
            self.log.warn('Cannot find configured HydraHarp400. \nSearching available HydraHarp400...')
            for i in range(0, 8):
                op = self.dll.HH_OpenDevice(ctypes.c_int(i), serial)
                if op == 0:
                    dev.append(i)
            # Use the first Pico Quant device as fastcounter
            self.log.info('Using the first Pico Quant device of the searching list as the fastcounter. \ndeviceID: {0}'.format(dev[0]))
            self._deviceID = dev[0]
            ini = self.dll.HH_Initialize(ctypes.c_int(self._deviceID), ctypes.c_int(self._mode), ctypes.c_int(self._refsource))
        if ini == 0:
            cal = self.dll.HH_Calibrate(self._deviceID)
            if cal == 0:
                self.connected_to_device = True
                self.log.info('Calibration of HydraHarp400 is finished.')
                return
            else:
                self.log.warn('Calibration of HydraHarp400 failed.')
        else:
            self.log.error('Could not find any Pico Quant device.')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.dll.HH_CloseDevice(ctypes.c_int(self._deviceID))
        self.log.info('HydraHarp400 closed.')
        return

    def check(self, func_val):
        """ Check routine for the received error codes.

        @param int func_val: return error code of the called function.

        @return int: pass the error code further so that other functions have
                     the possibility to use it.

        Each called function in the dll has an 32-bit return integer, which
        indicates, whether the function was called and finished successfully
        (then func_val = 0) or if any error has occured (func_val < 0). The
        errorcode, which corresponds to the return value can be looked up in
        the file 'errorcodes.h'.
        """

        if not func_val == 0:
            self.log.error('Error in HydraHarp400 with errorcode {0}:\n'
                           '{1}'.format(func_val, self.errorcode[func_val]))
        return func_val


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
        """

        constraints = dict()

        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seonds use the get_binwidth method.

        constraints['hardware_binwidth_list'] = list(self.minimal_binwidth * (2 ** np.array(
                                                     np.linspace(0, 25, 26))))
        constraints['max_sweep_len'] = 6
        constraints['max_bins'] = 65536
        return constraints


    def configure(self, bin_width_s, record_length_s, number_of_gates=None):
            """ Configuration of the fast counter.
            @param float bin_width_s: Length of a single time bin in the time trace
                                      histogram in seconds.
            @param float record_length_s: Total length of the timetrace/each single
                                          gate in seconds.
            @param int number_of_gates: optional, number of gates in the pulse
                                        sequence. Ignore for not gated counter.
            @return tuple(binwidth_s, record_length_s, number_of_gates):
                        binwidth_s: float the actual set binwidth in seconds
                        gate_length_s: the actual record length in seconds
                        number_of_gates: the number of gated, which are accepted,
                        None if not-gated
            """

            # when not gated, record length = total sequence length, when gated, record length = laser length.
            # subtract 200 ns to make sure no sequence trigger is missed
            self.set_binwidth(bin_width_s)
            record_length_HydraHarp_s = record_length_s

            if self.gated:
                # add time to account for AOM delay
                new_record_length_s = int((record_length_HydraHarp_s + self.aom_delay) / bin_width_s)
            else:
                # subtract time to make sure no sequence trigger is missed
                new_record_length_s = int((record_length_HydraHarp_s - self.trigger_safety) / bin_width_s)
            self.set_length(new_record_length_s)
            # self.set_cycles(number_of_gates)

            return self.get_binwidth(), new_record_length_s, number_of_gates

    def start_measure(self):
        """Start the measurement. """
        status = self.dll.HH_StartMeas(ctypes.c_int(self._deviceID), 360000) # t is aquisition time, can set ACQTMAX as default
        return status

    def stop_measure(self):
        """Stop the measurement. """
        self.stopped_or_halt = "stopped"
        status = self.dll.HH_StopMeas(ctypes.c_int(self._deviceID))
     #   if self.gated:
      #      self.timetrace_tmp = []
        return status

    def pause_measure(self):
        """Make a pause in the measurement, which can be continued. """
        self.log.warn('HydraHarp400 has no functionality of PAUSE!')
        return

    def continue_measure(self):
        """Continue a paused measurement. """
        self.log.warn('HydraHarp400 has no functionality of PAUSE!')
        return

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return self.gated

    def get_length(self):
        """ Get the length of the current measurement.

          @return int: length of the current measurement in bins
        """

        if self.is_gated():
            cycles = self.get_cycles()
            if cycles ==0:
                cycles = 1
        else:
            cycles = 1
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        length = int(setting.range / cycles)
        return length

    def get_data_trace(self):
        """
        Polls the current timetrace data from the fast counter and returns it
        as a numpy array (dtype = int64). The binning specified by calling
        configure() must be taken care of in this hardware class. A possible
        overflow of the histogram bins must be caught here and taken care of.
          - If the counter is NOT gated it will return a 1D-numpy-array with
            returnarray[timebin_index].
          - If the counter is gated it will return a 2D-numpy-array with
            returnarray[gate_index, timebin_index]
        @return arrray: Time trace.
        """
        flags = ctypes.c_int32()


        if self.is_gated():
            pass
            # TODO implement
        else:
            self.tryfunc(self.dll.HH_GetHistogram(self._deviceID, ctypes.byref(self.counts[0]), 0, 1), "GetHistogram")

        self.tryfunc(self.dll.HH_GetFlags(self._deviceID, ctypes.byref(flags)), "GetFlags")

        if flags.value & self.FLAG_OVERFLOW > 0:
            self.log.warn("Overflow.")

        time_trace = self.counts[0]

        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': None}  # TODO : implement that according to hardware capabilities
        return time_trace, info_dict

    def _set_constants(self):
        """ Set the constants (max and min values) for the Hydraharp400 device.
        These setting are taken from hhdefin.h """

        self.MODE_HIST = 0
        self.MODE_T2 = 2
        self.MODE_T3 = 3
        self.MODE_CONT = 8

        # in mV:
        self.ZCMIN = 0
        self.ZCMAX = 40
        self.DISCRMIN = 0
        self.DISCRMAX = 1000
     #   self.PHR800LVMIN = -1600
      #  self.PHR800LVMAX = 2400

        # in ps:
        self.OFFSETMIN = 0
        self.OFFSETMAX = 500000000
        self.SYNCOFFSMIN = -99999
        self.SYNCOFFSMAX = 99999

        # in ms:
        self.ACQTMIN = 1
        self.ACQTMAX = 100 * 60 * 60 * 1000
        self.TIMEOUT = 80  # the maximal device timeout for a readout request

        # in ns:
        self.HOLDOFFFMIN = 0
        self.HOLDOFFMAX = 524296

        self.BINSTEPSMAX = 26
        self.HISTCHAN = 65536  # number of histogram channels 2^16
        self.TTREADMAX = 131072  # 128K event records (2^17)


    def get_version(self):
        """ Get the software/library version of the device.

        @return string: string representation of the
                        Version number of the current library."""
        buf = ctypes.create_string_buffer(8)   # at least 8 byte
        self.check(self.dll.HH_GetLibraryVersion(ctypes.byref(buf)))
        return buf.value # .decode() converts byte to string

    def get_error_string(self, errcode):
        """ Get the string error code from the Hydraharp Device.

        @param int errcode: errorcode from 0 and below.

        @return byte: byte representation of the string error code.

        The stringcode for the error is the same as it is extracted from the
        errorcodes.h header file. Note that errcode should have the value 0
        or lower, since interger bigger 0 are not defined as error.
        """

        buf = ctypes.create_string_buffer(80)   # at least 40 byte
        self.check(self.dll.HH_GetErrorString(ctypes.byref(buf), errcode))
        return buf.value.decode() # .decode() converts byte to string

    # =========================================================================
    # Establish the connection and initialize the device or disconnect it.
    # =========================================================================

    def close_connection(self):
        """Close the connection to the device.

        @param int deviceID: a device index from 0 to 7.
        """
        self.connected_to_device = False
        self.check(self.dll.HH_CloseDevice(self._deviceID))
        self.log.info('Connection to the HydraHarp400 closed.')

    # =========================================================================
    # All functions below can be used if the device was successfully called.
    # =========================================================================

    def get_hardware_info(self):
        """ Retrieve the device hardware information.

        @return string tuple(3): (Model, Partnum, Version)
        """

        model = ctypes.create_string_buffer(32)     # at least 16 byte
        version = ctypes.create_string_buffer(16)   # at least 8 byte
        partnum = ctypes.create_string_buffer(16)   # at least 8 byte
        self.check(self.dll.HH_GetHardwareInfo(self._deviceID, ctypes.byref(model),
                                                ctypes.byref(partnum), ctypes.byref(version)))

        # the .decode() function converts byte objects to string objects
        return model.value.decode(), partnum.value.decode(), version.value.decode()

    def get_serial_number(self):
        """ Retrieve the serial number of the device.

        @return string: serial number of the device
        """

        serialnum = ctypes.create_string_buffer(16)   # at least 8 byte
        self.check(self.dll.HH_GetSerialNumber(self._deviceID, ctypes.byref(serialnum)))
        return serialnum.value.decode() # .decode() converts byte to string

    def get_base_resolution(self):
        """ Retrieve the base resolution of the device.

        @return double: the base resolution of the device
        """

        res = ctypes.c_double()
        self.check(self.dll.HH_GetBaseResolution(self._deviceID, ctypes.byref(res)))
        return res.value

    def calibrate(self):
        """ Calibrate the device."""
        self.check(self.dll.HH_Calibrate(self._deviceID))

    def get_features(self):
        """ Retrieve the possible features of the device.

        @return int: a bit pattern indicating the feature.
        """
        features = ctypes.c_int32()
        self.check(self.dll.HH_GetFeatures(self._deviceID, ctypes.byref(features)))
        return features.value

    def set_input_CFD(self, channel, level, zerocross):
        """ Set the Constant Fraction Discriminators for the HydraHarp400.

        @param int channel: number (0 or 1) of the input channel
        @param int level: CFD discriminator level in millivolts
        @param int zerocross: CFD zero cross in millivolts
        """
        channel = int(channel)
        level = int(level)
        zerocross = int(zerocross)
        if channel not in (0, 1):
            self.log.error('HydraHarp: Channal does not exist.\nChannel has '
                           'to be 0 or 1 but {0} was passed.'.format(channel))
            return
        if not(self.DISCRMIN <= level <= self.DISCRMAX):
            self.log.error('HydraHarp: Invalid CFD level.\nValue must be '
                           'within the range [{0},{1}] millivolts but a value of '
                           '{2} has been '
                           'passed.'.format(self.DISCRMIN, self.DISCRMAX, level))
            return
        if not(self.ZCMIN <= zerocross <= self.ZCMAX):
            self.log.error('HydraHarp: Invalid CFD zero cross.\nValue must be '
                           'within the range [{0},{1}] millivolts but a value of '
                           '{2} has been '
                           'passed.'.format(self.ZCMIN, self.ZCMAX, zerocross))
            return

        self.check(self.dll.HH_SetInputCFD(self._deviceID, channel, level, zerocross))

    def set_sync_div(self, div):
        """ Synchronize the devider of the device.

        @param int div: input rate devider applied at channel 0 (1,2,4, or 8)

        The sync devider must be used to keep the  effective sync rate at
        values <= 12.5 MHz. It should only be used with sync sources of stable
        period. The readins obtained with HH_GetCountRate are corrected for the
        devider settin and deliver the external (undivided) rate.
        """
        if not ((div != 1) or (div != 2) or (div != 4) or (div != 8)) or (div != 16):
            self.log.error('HydraHarp: Invalid sync devider.\n'
                           'Value must be 1, 2, 4, 8 or 16 but a value of {0} was '
                           'passed.'.format(div))
            return
        else:
            self.check(self.dll.HH_SetSyncDiv(self._deviceID, div))

    def set_sync_offset(self, offset):
        """ Set the offset of the synchronization.

        @param int offset: offset (time shift) in ps for that channel. That
                           value must lie within the range of SYNCOFFSMIN and
                           SYNCOFFSMAX.
        """
        offset = int(offset)
        if not(self.SYNCOFFSMIN <= offset <= self.SYNCOFFSMAX):
            self.log.error('HydraHarp: Invalid Synchronization offset.\nValue '
                           'must be within the range [{0},{1}] ps but a value of '
                           '{2} has been passed.'.format(
                self.SYNCOFFSMIN, self.SYNCOFFSMAX, offset))
        else:
            self.check(self.dll.HH_SetSyncOffset(self._deviceID, offset))

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
        if stop_ovfl not in (0, 1):
            self.log.error('HydraHarp: Invalid overflow parameter.\n'
                           'The overflow parameter must be either 0 or 1 but a '
                           'value of {0} was passed.'.format(stop_ovfl))
            return

        if not (0 <= stopcount <= self.HISTCHAN):
            self.log.error('HydraHarp: Invalid stopcount parameter.\n'
                           'stopcount must be within the range [0,{0}] but a '
                           'value of {1} was passed.'.format(self.HISTCHAN, stopcount))
            return

        return self.check(self.dll.HH_SetStopOverflow(self._deviceID, stop_ovfl, stopcount))

    def set_offset(self, offset):
        """ Set an offset time.

        @param int offset: offset in ps (only possible for histogramming and T3
                           mode!). Value must be within [OFFSETMIN,OFFSETMAX].

        The true offset is an approximation fo the desired offset by the
        nearest multiple of the base resolution. This offset only acts on the
        difference between ch1 and ch0 in hitogramming and T3 mode. Do not
        confuse it with the input offsets!
        """
        if not(self.OFFSETMIN <= offset <= self.OFFSETMAX):
            self.log.error('HydraHarp: Invalid offset.\nValue must be within '
                           'the range [{0},{1}] ps, but a value of {2} has been '
                           'passed.'.format(self.OFFSETMIN, self.OFFSETMAX, offset))
        else:
            self.check(self.dll.HH_SetOffset(self._deviceID, offset))

    def clear_hist_memory(self, block=0):
        """ Clear the histogram memory.

        @param int block: set which block number to clear.
        """
        self.check(self.dll.HH_ClearHistMem(self._deviceID, block))

    def start(self, acq_time):
        """ Start acquisition for 'acq_time' ms.

        @param int acq_time: acquisition time in miliseconds. The value must be
                             be within the range [ACQTMIN,ACQTMAX].
        """
        if not(self.ACQTMIN <= acq_time <= self.ACQTMAX):
            self.log.error('HydraHarp: No measurement could be started.\n'
                           'The acquisition time must be within the range [{0},{1}] '
                           'ms, but a value of {2} has been passed.'
                           ''.format(self.ACQTMIN, self.ACQTMAX, acq_time))
        else:
            self.check(self.dll.HH_StartMeas(self._deviceID, int(acq_time)))

    def stop_device(self):
        """ Stop the measurement."""
        self.check(self.dll.HH_StopMeas(self._deviceID))
        self.meas_run = False

    def _get_status(self):
        """ Check the status of the device.

        @return int:  = 0: acquisition time still running
                      > 0: acquisition time has ended, measurement finished.
        """
        ctcstatus = ctypes.c_int32()
        self.check(self.dll.HH_CTCStatus(self._deviceID, ctypes.byref(ctcstatus)))
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
        chcount = np.zeros((self.HISTCHAN,), dtype=np.uint32)
        # buf.ctypes.data is the reference to the array in the memory.
        self.check(self.dll.HH_GetHistogram(self._deviceID, chcount.ctypes.data, block))
        if xdata:
            xbuf = np.arange(self.HISTCHAN) * self.get_resolution() / 1000
            return xbuf, chcount
        return chcount

    def get_resolution(self):
        """ Retrieve the current resolution of the picohard.

        @return double: resolution at current binning.
        """

        resolution = ctypes.c_double()
        self.check(self.dll.HH_GetResolution(self._deviceID, ctypes.byref(resolution)))
        return resolution.value

    def get_count_rate(self, channel):
        """ Get the current count rate for the

        @param int channel: which input channel to read (0 or 1):

        @return int: count rate in ps.

        The hardware rate meters emply a gate time of 100ms. You must allow at
        least 100ms after HH_Initialize or HH_SetDyncDivider to get a valid
        rate meter reading. Similarly, wait at least 100ms to get a new
        reading. The readings are corrected for the snyc devider setting and
        deliver the external (undivided) rate. The gate time cannot be changed.
        The readings may therefore be inaccurate of fluctuating when the rate
        are very low. If accurate rates are needed you must perform a full
        blown measurement and sum up the recorded events.
        """
        if not ((channel !=0) or (channel != 1)):
            self.log.error('HydraHarp: Count Rate could not be read out, '
                           'Channel does not exist.\nChannel has to be 0 or 1 '
                           'but {0} was passed.'.format(channel))
            return -1
        else:
            rate = ctypes.c_int32()
            self.check(self.dll.HH_GetCountRate(self._deviceID, channel, ctypes.byref(rate)))
            return rate.value

    def get_elepased_meas_time(self):
        """ Retrieve the elapsed measurement time in ms.

        @return double: the elapsed measurement time in ms.
        """
        elapsed = ctypes.c_double()
        self.check(self.dll.HH_GetElapsedMeasTime(self._deviceID, ctypes.byref(elapsed)))
        return elapsed.value

    def get_warnings(self):
        """Retrieve any warnings about the device or the current measurement.

        @return int: a bitmask for the warnings, as defined in phdefin.h

        NOTE: you have to call HH_GetCountRates for all channels prior to this
              call!
        """
        warnings = ctypes.c_int32()
        self.check(self.dll.HH_GetWarnings(self._deviceID, ctypes.byref(warnings)))
        return warnings.value

    def get_warnings_text(self, warning_num):
        """Retrieve the warningtext for the corresponding warning bitmask.

        @param int warning_num: the number for which you want to have the
                                warning text.
        @return char[32568]: the actual text of the warning.

        """
        text = ctypes.create_string_buffer(32568) # buffer at least 16284 byte
        self.check(self.dll.HH_GetWarningsText(self._deviceID, warning_num, text))
        return text.value

    def get_hardware_debug_info(self):
        """ Retrieve the debug information for the current hardware.

        @return char[32568]: the information for debugging.
        """
        debuginfo = ctypes.create_string_buffer(32568) # buffer at least 16284 byte
        self.check(self.dll.HH_GetHardwareDebugInfo(self._deviceID, debuginfo))
        return debuginfo.value

    # =========================================================================
    #  Special functions for Time-Tagged Time Resolved mode
    # =========================================================================
    # To check whether you can use the TTTR mode (must be purchased in
    # addition) you can call HH_GetFeatures to check.

    def tttr_read_fifo(self):#, num_counts):
        """ Read out the buffer of the FIFO.

        @param int num_counts: number of TTTR records to be fetched. Maximal
                               TTREADMAX

        @return tuple (buffer, actual_num_counts):
                    buffer = data array where the TTTR data are stored.
                    actual_num_counts = how many numbers of TTTR could be
                                        actually be read out. THIS NUMBER IS
                                        NOT CHECKED FOR PERFORMANCE REASONS, SO
                                        BE  CAREFUL! Maximum is TTREADMAX.

        THIS FUNCTION SHOULD BE CALLED IN A SEPARATE THREAD!

        Must not be called with count larger than buffer size permits. CPU time
        during wait for completion will be yielded to other processes/threads.
        Function will return after a timeout period of 80 ms even if not all
        data could be fetched. Return value indicates how many records were
        fetched. Buffer must not be accessed until the function returns!
        """

        # if type(num_counts) is not int:
        #     num_counts = self.TTREADMAX
        # elif (num_counts<0) or (num_counts>self.TTREADMAX):
        #     self.log.error('PicoHarp: num_counts were expected to within the '
        #                 'interval [0,{0}], but a value of {1} was '
        #                 'passed'.format(self.TTREADMAX, num_counts))
        #     num_counts = self.TTREADMAX

        # PicoHarp T3 Format (for analysis and interpretation):
        # The bit allocation in the record for the 32bit event is, starting
        # from the MSB:
        #       channel:     4 bit
        #       dtime:      12 bit
        #       nsync:      16 bit
        # The channel code 15 (all bits ones) marks a special record.
        # Special records can be overflows or external markers. To
        # differentiate this, dtime must be checked:
        #
        #     If it is zero, the record marks an overflow.
        #     If it is >=1 the individual bits are external markers.

        num_counts = self.TTREADMAX

        buffer = np.zeros((num_counts,), dtype=np.uint32)

        actual_num_counts = ctypes.c_int32()

        self.check(self.dll.HH_ReadFiFo(self._deviceID, buffer.ctypes.data,
                                         num_counts, ctypes.byref(actual_num_counts)))

        return buffer, actual_num_counts.value

    def tttr_set_marker_edges(self, me0, me1, me2, me3):
        """ Set the marker edges

        @param int me<n>:   active edge of marker signal <n>,
                                0 = falling
                                1 = rising
        """

        if (me0 != 0) or (me0 != 1) or (me1 != 0) or (me1 != 1) or \
                (me2 != 0) or (me2 != 1) or (me3 != 0) or (me3 != 1):

            self.log.error('HydraHarp: All the marker edges must be either 0 '
                           'or 1, but the current marker settings were passed:\n'
                           'me0={0}, me1={1}, '
                           'me2={2}, me3={3},'.format(me0, me1, me2, me3))
            return
        else:
            self.check(self.dll.HH_SetMarkerEdges(self._deviceID, me0, me1,
                                                     me2, me3))

    def tttr_set_marker_enable(self, me0, me1, me2, me3):
        """ Set the marker enable or not.

        @param int me<n>:   enabling of marker signal <n>,
                                0 = disabled
                                1 = enabled
        """

        #        if ((me0 != 0) or (me0 != 1)) or ((me1 != 0) or (me1 != 1)) or \
        #           ((me2 != 0) or (me2 != 1)) or ((me3 != 0) or (me3 != 1)):
        #
        #            self.log.error('PicoHarp: Could not set marker enable.\n'
        #                        'All the marker options must be either 0 or 1, but '
        #                        'the current marker settings were passed:\n'
        #                        'me0={0}, me1={1}, '
        #                        'me2={2}, me3={3},'.format(me0, me1, me2, me3))
        #            return
        #        else:
        self.check(self.dll.HH_SetMarkerEnable(self._deviceID, me0,
                                                me1, me2, me3))

    def tttr_set_marker_holdofftime(self, holfofftime):
        """ Set the holdofftime for the markers.

        @param int holdofftime: holdofftime in ns. Maximal value is HOLDOFFMAX.

        This setting can be used to clean up glitches on the marker signals.
        When set to X ns then after detecting a first marker edge the next
        marker will not be accepted before x ns. Observe that the internal
        granularity of this time is only about 50ns. The holdoff time is set
        equally for all marker inputs but the holdoff logic acts on each
        marker independently.
        """

        if not(0 <= holdofftime <= self.HOLDOFFMAX):
            self.log.error('HydraHarp: Holdofftime could not be set.\n'
                           'Value of holdofftime must be within the range '
                           '[0,{0}], but a value of {1} was passed.'
                           ''.format(self.HOLDOFFMAX, holfofftime))
        else:
            self.check(self.dll.HH_SetMarkerHoldofftime(self._deviceID, holfofftime))


    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Set here which channel you want to access of the Hydraharp.

        @param float clock_frequency: Sets the frequency of the clock. That
                                      frequency will not be taken. It is not
                                      needed, and argument will be omitted.
        @param string clock_channel: This is the physical channel
                                     of the clock. It is not needed, and
                                     argument will be omitted.

        The Hardware clock for the Hydraharp is not programmable. It is a gated
        counter every 100ms. That you cannot change. You can retrieve from both
        channels simultaneously the count rates.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('Hydraharp: The Hardware clock for the Hydraharp is not '
                      'programmable!\n'
                      'It is a gated counter every 100ms. That you cannot change. '
                      'You can retrieve from both channels simultaneously the '
                      'count rates.')

        return 0

    def get_status(self):
        """
        Receives the current status of the Fast Counter and outputs it as
        return value.
        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        if not self.connected_to_device:
            return -1
        else:
            returnvalue = self._get_status()
            if returnvalue == 0:
                return 2
            else:
                return 1

    def pause_measure(self):
        """
        Pauses the current measurement if the fast counter is in running state.
        """

        self.stop_measure()
        self.meas_run = False

    def continue_measure(self):
        """
        Continues the current measurement if the fast counter is in pause state.
        """
        self.meas_run = True
        self.start(self._record_length_ns/1e6)

    def is_gated(self):
        """
        Boolean return value indicates if the fast counter is a gated counter
        (TRUE) or not (FALSE).
        """
        return False

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.
        @return float: current length of a single bin in seconds (seconds/bin)
        """
        resolution = ctypes.c_double()
        self.tryfunc(self.dll.HH_GetResolution(self._deviceID, ctypes.byref(resolution)), "GetResolution")

        return resolution.value * 1e-12



    def set_length(self, length_bins):
        """ Sets the length of the length of the actual measurement.

        @param int length_bins: Length of the measurement in bins

        @return float: Red out length of measurement
        """
        # First check if no constraint is
        constraints = self.get_constraints()
        if self.is_gated():
            pass
        else:
            cycles = 1
        if length_bins *  cycles < constraints['max_bins']:
            # Smallest increment is 64 bins. Since it is better if the range is too short than too long, round down
            length_bins = int(64 * int(length_bins / 64))
            actualen = ctypes.c_int()
            length_set = self.dll.HH_SetHistoLen(self._deviceID, length_bins, ctypes.byref(actualen))
            if length_bins == 0:
                self.log.info('Bin length is {0}, Actual histogram bins are {1}.'.format(length_bins, actualen.value))
            else:
                self.log.error('Counting length set failed, errocode: {0}. check errorcodes.h for solution.'.format(length_bins))
            time.sleep(0.5)
            return length_bins
        else:
            self.log.error('Dimensions {0} are too large for fast counter1!'.format(length_bins *  cycles))
            return -1

    def set_binning(self, binning):
        """ Set the base resolution of the measurement.
        @param int binning: binning code
                                minimum = 0 (smallest, i.e. base resolution)
                                maximum = (BINSTEPSMAX-1) (largest)
        The binning code corresponds to a power of 2, i.e.
            0 =      base resolution,     => 2^0 =    1ps
            1 =   2x base resolution,     => 2^1 =    2ps
            2 =   4x base resolution,     => 2^2 =   4ps
            3 =   8x base resolution      => 2^3 =   8ps
            4 =  16x base resolution      => 2^4 =   16ps
            5 =  32x base resolution      => 2^5 =  32ps
            6 =  64x base resolution      => 2^6 =  64ps
            7 = 128x base resolution      => 2^7 =  128ps
            ...
        In histogram mode the internal
        buffer can store 65535 points (each a 32bit word).
        """
        if not(0 <= binning < self.BINSTEPSMAX):
            self.log.error('HydraHarp: Invalid binning.\nValue must be within '
                           'the range [{0},{1}] bins, but a value of {2} has been '
                           'passed.'.format(0, self.BINSTEPSMAX, binning))
        else:
            self.check(self.dll.HH_SetBinning(self._deviceID, binning))

    def set_binwidth(self, binwidth):
        """ Set defined binwidth in Card.
        @param float binwidth: the current binwidth in seconds
        @return float: Red out bitshift converted to binwidth
        The binwidth is converted into to an appropiate bitshift defined as
        2**bitshift*minimal_binwidth.
        """
        bitshift = int(np.log2(binwidth/self.minimal_binwidth))
        resolution=self.set_bitshift(bitshift)
        return resolution

    def set_bitshift(self, bitshift):
        """ Sets the bitshift properly for this card.
        @param int bitshift:
        @return int: asks the actual bitshift and returns the red out value
        """

        self.set_binning(bitshift)
        resolution = ctypes.c_double()
        self.tryfunc(self.dll.HH_GetResolution(self._deviceID, ctypes.byref(resolution)), "GetResolution")
        return resolution.value * 1e-12

    def tryfunc(self, retcode, funcName, measRunning=False):
        errorString = ctypes.create_string_buffer(b"", 40)
        if retcode < 0:
            self.dll.HH_GetErrorString(errorString, ctypes.c_int(retcode))
            self.log.error("HH_%s error %d (%s). Aborted." % (funcName, retcode,\
                  errorString.value.decode("utf-8")))
        return retcode
