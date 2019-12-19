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

class AcqStatus(ctypes.Structure):
    """ Create a structured Data type with ctypes where the dll can write into.

    This object handles and retrieves the acquisition status data from the
    Fastcomtec.

    int started;                // acquisition status: 1 if running, 0 else
    double runtime;             // running time in seconds
    double totalsum;            // total events
    double roisum;              // events within ROI
    double roirate;             // acquired ROI-events per second
    double nettosum;            // ROI sum with background subtracted
    double sweeps;              // Number of sweeps
    double stevents;            // Start Events
    unsigned long maxval;       // Maximum value in spectrum
    """
    _fields_ = [('started', ctypes.c_int),
                ('runtime', ctypes.c_double),
                ('totalsum', ctypes.c_double),
                ('roisum', ctypes.c_double),
                ('roirate', ctypes.c_double),
                ('ofls', ctypes.c_double),
                ('sweeps', ctypes.c_double),
                ('stevents', ctypes.c_double),
                ('maxval', ctypes.c_ulong), ]


class AcqSettings(ctypes.Structure):
    _fields_ = [('range',       ctypes.c_long),
                ('cftfak',      ctypes.c_long),
                ('roimin',      ctypes.c_long),
                ('roimax',      ctypes.c_long),
                ('nregions',    ctypes.c_long),
                ('caluse',      ctypes.c_long),
                ('calpoints',   ctypes.c_long),
                ('param',       ctypes.c_long),
                ('offset',      ctypes.c_long),
                ('xdim',        ctypes.c_long),
                ('bitshift',    ctypes.c_ulong),
                ('active',      ctypes.c_long),
                ('eventpreset', ctypes.c_double),
                ('dummy1',      ctypes.c_double),
                ('dummy2',      ctypes.c_double),
                ('dummy3',      ctypes.c_double), ]

class ACQDATA(ctypes.Structure):
    """ Create a structured Data type with ctypes where the dll can write into.

    This object handles and retrieves the acquisition data of the Fastcomtec.
    """
    _fields_ = [('s0', ctypes.POINTER(ctypes.c_ulong)),
                ('region', ctypes.POINTER(ctypes.c_ulong)),
                ('comment', ctypes.c_char_p),
                ('cnt', ctypes.POINTER(ctypes.c_double)),
                ('hs0', ctypes.c_int),
                ('hrg', ctypes.c_int),
                ('hcm', ctypes.c_int),
                ('hct', ctypes.c_int), ]

class BOARDSETTING(ctypes.Structure):
    _fields_ = [('sweepmode',   ctypes.c_long),
                ('prena',       ctypes.c_long),
                ('cycles',      ctypes.c_long),
                ('sequences',   ctypes.c_long),
                ('syncout',     ctypes.c_long),
                ('digio',       ctypes.c_long),
                ('digval',      ctypes.c_long),
                ('dac0',        ctypes.c_long),
                ('dac1',        ctypes.c_long),
                ('dac2',        ctypes.c_long),
                ('dac3',        ctypes.c_long),
                ('dac4',        ctypes.c_long),
                ('dac5',        ctypes.c_long),
                ('fdac',        ctypes.c_int),
                ('tagbits',     ctypes.c_int),
                ('extclk',      ctypes.c_int),
                ('maxchan',     ctypes.c_long),
                ('serno',       ctypes.c_long),
                ('ddruse',      ctypes.c_long),
                ('active',      ctypes.c_long),
                ('holdafter',   ctypes.c_double),
                ('swpreset',    ctypes.c_double),
                ('fstchan',     ctypes.c_double),
                ('timepreset',  ctypes.c_double), ]

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
        op = self.dll.HH_OpenDevice(ctypes.c_int(self._deviceID), ctypes.c_int(self._mode), ctypes.c_int(self._refsource))
        if op == 0:
            ini = self.dll.HH_Initialize(ctypes.c_int(self._deviceID), ctypes.c_int(self._mode), ctypes.c_int(self._refsource))
        else:
            # search available Pico Quant device
            # unplug or replug of PQ device, could change the device ID
            for i in range(0,8):
                op = self.dll.HH_OpenDevice(ctypes.c_int(i), serial)
                if op == 0:
                    dev.append(i)
            # Use the first Pico Quant device as fastcounter
            self._deviceID = dev[0]
            ini = self.dll.HH_Initialize(ctypes.c_int(self._deviceID), ctypes.c_int(self._mode), ctypes.c_int(self._refsource))
        if self.gated:
            self.change_sweep_mode(gated=True)
        else:
            self.change_sweep_mode(gated=False)
        if ini == 0:
            return
        else:
            self.log.error('Could not find any Pico Quant device.')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.dll.HH_CloseDevice(ctypes.c_int(self._deviceID))
        return

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
        #FIXME confirm the values later with HHarp 400 manual
        constraints['hardware_binwidth_list'] = list(self.minimal_binwidth * (2 ** np.array(
                                                     np.linspace(0,24,25))))
        constraints['max_sweep_len'] = 6.8
        constraints['max_bins'] = 6.8 /0.2e-9
        return constraints

    def configure(self, bin_width_s, record_length_s, number_of_gates=1):
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
        record_length_FastComTech_s = record_length_s
        self.set_binwidth(bin_width_s)

        if self.gated:
            # add time to account for AOM delay
            no_of_bins = int((record_length_FastComTech_s + self.aom_delay) / bin_width_s)
        else:
            # subtract time to make sure no sequence trigger is missed
            no_of_bins = int((record_length_FastComTech_s - self.trigger_safety) / bin_width_s)

        self.set_length(no_of_bins)
        self.set_cycles(number_of_gates)

        return self.get_binwidth(), self.get_length() * self.get_binwidth(), number_of_gates

    def get_status(self):
        """
        Receives the current status of the Fast Counter and outputs it as return value.
        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        status = AcqStatus()
        #FIXME need to find the corresponding fucntion in manual
        self.dll.GetStatusData(ctypes.byref(status), 0)
        # status.started = 3 measn that fct is about to stop
        while status.started == 3:
            time.sleep(0.1)
            self.dll.GetStatusData(ctypes.byref(status), 0)
        if status.started == 1:
            return 2
        elif status.started == 0:
            if self.stopped_or_halt == "stopped":
                return 1
            elif self.stopped_or_halt == "halt":
                return 3
            else:
                self.log.error('There is an unknown status from FastComtec. The status message was %s' % (str(status.started)))
                return -1
        else:
            self.log.error(
                'There is an unknown status from FastComtec. The status message was %s' % (str(status.started)))
            return -1


    def start_measure(self):
        """Start the measurement. """
        status = self.dll.HH_StartMeas(0, t) # t is aquisition time, can set ACQTMAX as default
        return status

    def stop_measure(self):
        """Stop the measurement. """
        self.stopped_or_halt = "stopped"
        status = self.dll.HH_StopMeas(0)
     #   if self.gated:
      #      self.timetrace_tmp = []
        return status

    def pause_measure(self):
        """Make a pause in the measurement, which can be continued. """
        self.log.warn('HydraHarp400 has no functionality of PAUSE!')
        return -1

    def continue_measure(self):
        """Continue a paused measurement. """
        self.log.warn('HydraHarp400 has no functionality of PAUSE!')
        return -1

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return self.gated

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)

        The red out bitshift will be converted to binwidth. The binwidth is
        defined as 2**bitshift*minimal_binwidth.
        """
        return 1e12*self.dll.HH_GetResolution(0, double* resolution)#FIXME {1} in proper format

    def get_data_trace(self):
        """
        Polls the current timetrace data from the fast counter and returns it as a numpy array (dtype = int64).
        The binning specified by calling configure() must be taken care of in this hardware class.
        A possible overflow of the histogram bins must be caught here and taken care of.
        If the counter is UNgated it will return a 1D-numpy-array with returnarray[timebin_index]
        If the counter is gated it will return a 2D-numpy-array with returnarray[gate_index, timebin_index]

          @return arrray: Time trace.
        """
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        N = setting.range

        if self.is_gated():
            bsetting=BOARDSETTING()
            self.dll.GetMCSSetting(ctypes.byref(bsetting), 0)
            H = bsetting.cycles
            if H==0:
                H=1
            data = np.empty((H, int(N / H)), dtype=np.uint32)

        else:
            data = np.empty((N,), dtype=np.uint32)

        p_type_ulong = ctypes.POINTER(ctypes.c_uint32)
        ptr = data.ctypes.data_as(p_type_ulong)
        self.dll.LVGetDat(ptr, 0)
        time_trace = np.int64(data)

        if self.gated and self.timetrace_tmp != []:
            time_trace = time_trace + self.timetrace_tmp

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
        buf = ctypes.create_string_buffer(16)   # at least 8 byte
        self.check(self._dll.HH_GetLibraryVersion(ctypes.byref(buf)))
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
        self.check(self._dll.HH_GetErrorString(ctypes.byref(buf), errcode))
        return buf.value.decode() # .decode() converts byte to string

    # =========================================================================
    # Establish the connection and initialize the device or disconnect it.
    # =========================================================================

    def open_connection(self):
        """ Open a connection to this device. """

        buf = ctypes.create_string_buffer(16)  # at least 8 byte
        ret = self.check(self._dll.HH_OpenDevice(self._deviceID, ctypes.byref(buf)))
        self._serial = buf.value.decode()   # .decode() converts byte to string
        if ret >= 0:
            self.connected_to_device = True
            self.log.info('Connection to the HydraHarp400 established')

    def initialize(self, mode, refsource):
        """ Initialize the device with one of the three possible modes.

        @param int mode:    0: histogramming
                            2: T2
                            3: T3
                            8: CONT
        @param int mode:    0: internal
                            1: external
        """
        mode = int(mode)    # for safety reasons, convert to integer
        self._mode = mode

        refsource = int(refsource)
        self._refsource = refsource

        if not ((mode != self.MODE_HIST) or (mode != self.MODE_T2) or (mode != self.MODE_T3) or (mode != self.MODE_CONT)):
            self.log.error('Hydraharp: Mode for the device could not be set. '
                           'It must be {0}=Histogram-Mode, {1}=T2-Mode or '
                           '{2}=T3-Mode, {3}=CONT-Mode but a parameter {4} was '
                           'passed.'.format(self.MODE_HIST,
                                            self.MODE_T2,
                                            self.MODE_T3,
                                            self.MODE_CONT,
                                            mode)
                           )
        else:
            self.check(self._dll.HH_Initialize(self._deviceID, mode, refsource))

    def close_connection(self):
        """Close the connection to the device.

        @param int deviceID: a device index from 0 to 7.
        """
        self.connected_to_device = False
        self.check(self._dll.HH_CloseDevice(self._deviceID))
        self.log.info('Connection to the HydraHarp400 closed.')

    #    def __del__(self):
    #        """ Delete the object PicoHarp300."""
    #        self.close()

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
        self.check(self._dll.HH_GetHardwareInfo(self._deviceID, ctypes.byref(model),
                                                ctypes.byref(partnum), ctypes.byref(version)))

        # the .decode() function converts byte objects to string objects
        return model.value.decode(), partnum.value.decode(), version.value.decode()

    def get_serial_number(self):
        """ Retrieve the serial number of the device.

        @return string: serial number of the device
        """

        serialnum = ctypes.create_string_buffer(16)   # at least 8 byte
        self.check(self._dll.HH_GetSerialNumber(self._deviceID, ctypes.byref(serialnum)))
        return serialnum.value.decode() # .decode() converts byte to string

    def get_base_resolution(self):
        """ Retrieve the base resolution of the device.

        @return double: the base resolution of the device
        """

        res = ctypes.c_double()
        self.check(self._dll.HH_GetBaseResolution(self._deviceID, ctypes.byref(res)))
        return res.value

    def calibrate(self):
        """ Calibrate the device."""
        self.check(self._dll.HH_Calibrate(self._deviceID))

    def get_features(self):
        """ Retrieve the possible features of the device.

        @return int: a bit pattern indicating the feature.
        """
        features = ctypes.c_int32()
        self.check(self._dll.HH_GetFeatures(self._deviceID, ctypes.byref(features)))
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

        self.check(self._dll.HH_SetInputCFD(self._deviceID, channel, level, zerocross))

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
            self.check(self._dll.HH_SetSyncDiv(self._deviceID, div))

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
            self.check(self._dll.HH_SetSyncOffset(self._deviceID, offset))

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

        return self.check(self._dll.HH_SetStopOverflow(self._deviceID, stop_ovfl, stopcount))

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
            self.check(self._dll.HH_SetBinning(self._deviceID, binning))


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
            self.check(self._dll.HH_SetOffset(self._deviceID, offset))

    def clear_hist_memory(self, block=0):
        """ Clear the histogram memory.

        @param int block: set which block number to clear.
        """
        self.check(self._dll.HH_ClearHistMem(self._deviceID, block))

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
            self.check(self._dll.HH_StartMeas(self._deviceID, int(acq_time)))

    def stop_device(self):
        """ Stop the measurement."""
        self.check(self._dll.HH_StopMeas(self._deviceID))
        self.meas_run = False

    def _get_status(self):
        """ Check the status of the device.

        @return int:  = 0: acquisition time still running
                      > 0: acquisition time has ended, measurement finished.
        """
        ctcstatus = ctypes.c_int32()
        self.check(self._dll.HH_CTCStatus(self._deviceID, ctypes.byref(ctcstatus)))
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
        self.check(self._dll.HH_GetHistogram(self._deviceID, chcount.ctypes.data, block))
        if xdata:
            xbuf = np.arange(self.HISTCHAN) * self.get_resolution() / 1000
            return xbuf, chcount
        return chcount

    def get_resolution(self):
        """ Retrieve the current resolution of the picohard.

        @return double: resolution at current binning.
        """

        resolution = ctypes.c_double()
        self.check(self._dll.HH_GetResolution(self._deviceID, ctypes.byref(resolution)))
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
            self.check(self._dll.HH_GetCountRate(self._deviceID, channel, ctypes.byref(rate)))
            return rate.value

    def get_flags(self):
        """ Get the current status flag as a bit pattern.

        @return int: the current status flags (a bit pattern)

        Use the predefined bit mask values in phdefin.h (e.g. FLAG_OVERFLOW) to
        extract indiviual bits though a bitwise AND. It is also recommended to
        check for FLAG_SYSERROR to detect possible hardware failures. In that
        case you may want to call HH_GetHardwareDebugInfo and submit the
        results to support.
        """

        flags = ctypes.c_int32()
        self.check(self._dll.HH_GetFlags(self._deviceID, ctypes.byref(flags)))
        return flags.value

    def get_elepased_meas_time(self):
        """ Retrieve the elapsed measurement time in ms.

        @return double: the elapsed measurement time in ms.
        """
        elapsed = ctypes.c_double()
        self.check(self._dll.HH_GetElapsedMeasTime(self._deviceID, ctypes.byref(elapsed)))
        return elapsed.value

    def get_warnings(self):
        """Retrieve any warnings about the device or the current measurement.

        @return int: a bitmask for the warnings, as defined in phdefin.h

        NOTE: you have to call HH_GetCountRates for all channels prior to this
              call!
        """
        warnings = ctypes.c_int32()
        self.check(self._dll.HH_GetWarnings(self._deviceID, ctypes.byref(warnings)))
        return warnings.value

    def get_warnings_text(self, warning_num):
        """Retrieve the warningtext for the corresponding warning bitmask.

        @param int warning_num: the number for which you want to have the
                                warning text.
        @return char[32568]: the actual text of the warning.

        """
        text = ctypes.create_string_buffer(32568) # buffer at least 16284 byte
        self.check(self._dll.HH_GetWarningsText(self._deviceID, warning_num, text))
        return text.value

    def get_hardware_debug_info(self):
        """ Retrieve the debug information for the current hardware.

        @return char[32568]: the information for debugging.
        """
        debuginfo = ctypes.create_string_buffer(32568) # buffer at least 16284 byte
        self.check(self._dll.HH_GetHardwareDebugInfo(self._deviceID, debuginfo))
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

        self.check(self._dll.HH_ReadFiFo(self._deviceID, buffer.ctypes.data,
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
            self.check(self._dll.HH_SetMarkerEdges(self._deviceID, me0, me1,
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
        self.check(self._dll.HH_SetMarkerEnable(self._deviceID, me0,
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
            self.check(self._dll.HH_SetMarkerHoldofftime(self._deviceID, holfofftime))


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

    def set_up_counter(self, counter_channels=1, sources=None,
                       clock_channel = None):
        """ Ensure Interface compatibility. The counter allows no set up.

        @param string counter_channel: Set the actual channel which you want to
                                       read out. Default it is 0. It can
                                       also be 1.
        @param string photon_source: is not needed, arg will be omitted.
        @param string clock_channel: is not needed, arg will be omitted.

        @return int: error code (0:OK, -1:error)
        """
        self._count_channel = counter_channels
        self.log.info('Hydraharp: The counter allows no set up!\n'
                      'The implementation of this command ensures Interface '
                      'compatibility.')

        #FIXME: make the counter channel chooseable in config
        #FIXME: add second photon source either to config or in a better way to file
        return 0

    def get_counter_channels(self):
        """ Return one counter channel. """
        return ['Ctr0']

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 1
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return float: the photon counts per second
        """
        time.sleep(0.05)
        return [self.get_count_rate(self._count_channel)]

    def close_counter(self):
        """ Closes the counter and cleans up afterwards. Actually, you do not
        have to do anything with the picoharp. Therefore this command will do
        nothing and is only here for SlowCounterInterface compatibility.

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def close_clock(self):
        """Closes the clock and cleans up afterwards.. Actually, you do not
        have to do anything with the picoharp. Therefore this command will do
        nothing and is only here for SlowCounterInterface compatibility.

        @return int: error code (0:OK, -1:error)
        """
        return 0

    # =========================================================================
    #  Functions for the FastCounter Interface
    # =========================================================================

    #FIXME: The interface connection to the fast counter must be established!

    def configure(self, bin_width_ns, record_length_ns, number_of_gates = 0):
        """
        Configuration of the fast counter.
        bin_width_ns: Length of a single time bin in the time trace histogram
                      in nanoseconds.
        record_length_ns: Total length of the timetrace/each single gate in
                          nanoseconds.
        number_of_gates: Number of gates in the pulse sequence. Ignore for
                         ungated counter.
        """
        #        self.initialize(mode=3)
        self._bin_width_ns = bin_width_ns
        self._record_length_ns = record_length_ns
        self._number_of_gates = number_of_gates

        #FIXME: actualle only an unsigned array will be needed. Change that later.
        #        self.data_trace = np.zeros(number_of_gates, dtype=np.int64 )
        self.data_trace = [0]*number_of_gates
        self.count = 0

        self.result = []
        self.initialize(2)
        return

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
        """
        returns the width of a single timebin in the timetrace in seconds
        """
        #FIXME: Must be implemented
        return 2e-9

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
        """

        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': None}  # TODO : implement that according to hardware capabilities
        return self.data_trace, info_dict

    # =========================================================================
    #  Test routine for continuous readout
    # =========================================================================

    def start_measure(self):
        """
        Starts the fast counter.
        """
        self.lock()

        self.meas_run = True

        # start the device:
        self.start(int(self._record_length_ns/1e6))

        self.sigReadoutHydraharp.emit()

    def stop_measure(self):
        """ By setting the Flag, the measurement should stop.  """
        self.meas_run = False

    def get_fresh_data_loop(self):
        """ This method will be run infinitely until the measurement stops. """

        # for testing one can also take another array:
        buffer, actual_counts = self.tttr_read_fifo()
        #        buffer, actual_counts = [1,2,3,4,5,6,7,8,9], 9

        # This analysis signel should be analyzed in a queued thread:
        self.sigAnalyzeData.emit(buffer[0:actual_counts-1], actual_counts)

        if not self.meas_run:
            with self.threadlock:
                self.unlock()
                self.stop_device()
                return

        print('get new data.')
        # get the next data:
        self.sigReadoutHydraharp.emit()

    def analyze_received_data(self, arr_data, actual_counts):
        """ Analyze the actual data obtained from the TTTR mode of the device.

        @param arr_data: numpy uint32 array with length 'actual_counts'.
        @param actual_counts: int, number of read out events from the buffer.

        Write the obtained arr_data to the predefined array data_trace,
        initialized in the configure method.

        The received array contains 32bit words. The bit assignment starts from
        the MSB (most significant bit), which is here displayed as the most
        left bit.

        For T2 (initialized device with mode=2):
        ----------------------------------------

        [ 4 bit for channel-number |28 bit for time-tag] = [32 bit word]

        channel-number: 4 marker, which serve for the different channels.
                            0001 = marker 1
                            0010 = marker 2
                            0011 = marker 3
                            0100 = marker 4

                        The channel code 15 (all bits ones, 1111) marks a
                        special record. Special records can be overflows or
                        external markers. To differentiate this, the lower 4
                        bits of timetag must be checked:
                            - If they are all zero, the record marks an
                              overflow.
                            - If they are >=1 the individual bits are external
                              markers.

                        Overflow period: 210698240

                        the first bit is the overflow bit. It will be set if
                        the time-tag reached 2^28:

                            0000 = overflow

                        Afterwards both overflow marker and time-tag
                        will be reseted. This overflow should be detected and
                        the time axis should be adjusted accordingly.

        time-tag: The resolution is fixed to 4ps. Within the time of
                  4ps*2^28 = 1.073741824 ms
                  another photon event should occur so that the time axis can
                  be computed properly.

        For T3 (initialized device with mode=3):
        ----------------------------------------

        [ 4 bit for channel-number | 12 bit for start-stop-time | 16 bit for sync counter] = [32 bit word]

        channel-number: 4 marker, which serve for the different channels.
                            0001 = marker 1
                            0010 = marker 2
                            0011 = marker 3
                            0100 = marker 4

                        the first bit is the overflow bit. It will be set if
                        the sync-counter reached 65536 events:

                            1000 = overflow

                        Afterwards both, overflow marker and sync-counter
                        will be reseted. This overflow should be detected and
                        the time axis should be adjusted accordingly.

        start-stop-time: time between to consecutive sync pulses. Maximal time
                         between two sync pulses is therefore limited to
                             2^12 * Res
                         where Res is the Resolution
                             Res = {4,8,16,32,54,128,256,512} (in ps)
                         For largest Resolution of 512ps you have 2097.152 ns.
        sync-counter: can hold up to 2^16 = 65536 events. It that number is
                      reached overflow will be set. That means all 4 bits in
                      the channel-number are set to high (i.e. 1).
        """

        # at first just a simple test
        time.sleep(0.2)

        self.data_trace[self.count] = actual_counts
        self.count += 1

        if self.count > self._number_of_gates-1:
            self.count = 0

        if actual_counts == self.TTREADMAX:
            self.log.warning('Overflow!')

        print('Data analyzed.')

#        self.result = []
#        for entry in arr_data[0:actual_counts-1]:
#
#            # apply three bitmasks to extract the relavent numbers:
#            overflow = entry & (2**(32-1) )
#            marker_ch = entry & (2**(32-2)  + 2**(32-3) + 2**(32-4))
#            time_tag = entry & (2**32 -1 - 2**(32-1) + 2**(32-2) + 2**(32-3) + 2**(32-4))












