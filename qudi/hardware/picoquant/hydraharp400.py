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
import numpy as np
import ctypes

# =============================================================================
# Wrapper around the HHLib64.DLL. The current file is based on the header files
# 'hhdefin.h', 'hhlib.h' and 'errorcodes.h'. The 'hhdefin.h' contains all the
# constants and 'hhlib.h' contains all the functions exported within the dll
# file. 'errorcodes.h' contains the possible error messages of the device.
#
# The wrappered commands are based on the hHLib Version 3.0.0.2 For further
# information read the manual
#       'HHLib - Programming Library for Custom Software Development'
# which can be downloaded from the PicoQuant homepage.
# TODO GATED mode
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

class HydraHarp400(Base, FastCounterInterface):
    """ Hardware class to control the HydraHarp 400 from PicoQuant.

    This class is written according to the Programming Library Version 3.0.0.2

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
    trigger_safety = ConfigOption('trigger_safety', 400e-9, missing='warn')
    aom_delay = ConfigOption('aom_delay', 390e-9, missing='warn')
    minimal_binwidth = ConfigOption('minimal_binwidth', 1e-12, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._set_constants()
        self.connected_to_device = False

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        self.stopped_or_halt = "stopped"
        self.bins_num = 0

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
            self.log.warn('Fastcounter: Cannot find configured HydraHarp400. \nSearching available HydraHarp400...')
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
                self.log.warn('Fastcounter: Calibration of HydraHarp400 failed.')
        else:
            self.log.error('Fastcounter: Could not find any Pico Quant device.')

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
            self.log.error('Fastcounter: Error in HydraHarp400 with errorcode {0}:\n'
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
        constraints['max_sweep_len'] = 2.199 # Page 51 in user manual
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

            return self.get_binwidth(), self.get_length() * self.get_binwidth(), number_of_gates

    def start_measure(self):
        """Start the measurement. """
        self.dll.HH_ClearHistMem(self._deviceID)
        status = self.dll.HH_StartMeas(self._deviceID, 360000) # t is aquisition time, can set ACQTMAX as default
        return status

    def stop_measure(self):
        """Stop the measurement. """
        self.stopped_or_halt = "stopped"
        status = self.dll.HH_StopMeas(self._deviceID)
        return status

    def pause_measure(self):
        """Make a pause in the measurement, which can be continued. """
        self.stopped_or_halt = "halt"
        status = self.dll.HH_StopMeas(self._deviceID)
        return status

    def continue_measure(self):
        """Continue a paused measurement. """
        status = self.dll.HH_StartMeas(self._deviceID, 360000)
        return status

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
        if self.bins_num == 0:
            self.log.warn('Fastcounter: bin number has not been set. Returning 0.')
        return self.bins_num

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
        py_counts = np.empty((self.bins_num,), dtype=np.uint32)
        pointer = ctypes.POINTER(ctypes.c_uint32)
        c_counts = py_counts.ctypes.data_as(pointer)

        if self.is_gated():
            pass
            # TODO implement
        else:
            self.tryfunc(self.dll.HH_GetHistogram(self._deviceID, c_counts, 1, 0), "GetHistogram")

        time_trace = np.int64(py_counts)

        meas_t = int(self.get_measurement_time())
        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': meas_t}
        return time_trace, info_dict

    def get_measurement_time(self):
        t = ctypes.c_double()  # in ms unit
        self.dll.HH_GetElapsedMeasTime(self._deviceID, ctypes.byref(t))
        return t.value/1000 # return in second

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

    def _get_status(self):
        """ Check the status of the device.

        @return int:  = 0: acquisition time still running
                      > 0: acquisition time has ended, measurement finished.
        """
        ctcstatus = ctypes.c_int32()
        self.check(self.dll.HH_CTCStatus(self._deviceID, ctypes.byref(ctcstatus)))
        return ctcstatus.value

    def get_resolution(self):
        """ Retrieve the current resolution of the picohard.

        @return double: resolution at current binning.
        """

        resolution = ctypes.c_double()
        self.check(self.dll.HH_GetResolution(self._deviceID, ctypes.byref(resolution)))
        return resolution.value

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
            # bin numbers for Hydraharp, bin_num=1024*2^lencode, where lencode is integral, ranging 0~16.
            # Therefore, it has a very large bin increments. Bin numbers can be [1024,2048, 4096, ...].
            lencode = int(np.log2(length_bins/1024)+1)
            actualength = ctypes.c_int()
            length_set = self.dll.HH_SetHistoLen(self._deviceID, lencode, ctypes.byref(actualength))
            if length_set == 0:
                self.log.info('Bin lencode is {0}, Actual histogram bins are {1}.'.format(lencode, actualength.value))
                self.bins_num = actualength.value
                extra_length = (self.bins_num - length_bins) * self.get_binwidth()*1e3
                self.log.warn('Fastcounter: Extra length of the sweep is {0} ms.'.format(extra_length))
            else:
                self.log.error('Fastcounter: Counting length set failed, errocode: {0}. check errorcodes.h for solution.'.format(length_set))
            time.sleep(0.5)
            return actualength.value
        else:
            self.log.error('Fastcounter: Dimensions {0} are too large for fast counter!'.format(length_bins * cycles))
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
            self.log.error("Fastcounter: HH_%s error %d (%s). Aborted." % (funcName, retcode,\
                  errorString.value.decode("utf-8")))
        return retcode
