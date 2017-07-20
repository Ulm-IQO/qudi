# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file implementation for FastComtec p7887 .

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

#TODO: start stop works but pause does not work, i guess gui/logic problem
#TODO: What does get status do or need as return?
#TODO: Check if there are more modules which are missing, and more settings for FastComtec which need to be put, should we include voltage threshold?

from core.module import Base
from interface.fast_counter_interface import FastCounterInterface
import time
import os
import numpy as np
import ctypes


"""
Remark to the usage of ctypes:
All Python types except integers (int), strings (str), and bytes (byte) objects
have to be wrapped in their corresponding ctypes type, so that they can be
converted to the required C data type.

ctypes type     C type                  Python type
----------------------------------------------------------------
c_bool          _Bool                   bool (1)
c_char          char                    1-character bytes object
c_wchar         wchar_t                 1-character string
c_byte          char                    int
c_ubyte         unsigned char           int
c_short         short                   int
c_ushort        unsigned short          int
c_int           int                     int
c_uint          unsigned int            int
c_long          long                    int
c_ulong         unsigned long           int
c_longlong      __int64 or
                long long               int
c_ulonglong     unsigned __int64 or
                unsigned long long      int
c_size_t        size_t                  int
c_ssize_t       ssize_t or
                Py_ssize_t              int
c_float         float                   float
c_double        double                  float
c_longdouble    long double             float
c_char_p        char *
                (NUL terminated)        bytes object or None
c_wchar_p       wchar_t *
                (NUL terminated)        string or None
c_void_p        void *                  int or None

"""
# Reconstruct the proper structure of the variables, which can be extracted
# from the header file 'struct.h'.

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
    """ Create a structured Data type with ctypes where the dll can write into.

    This object handles and retrieves the acquisition settings of the Fastcomtec.
    """

    _fields_ = [('range',       ctypes.c_ulong),
                ('prena',       ctypes.c_long),
                ('cftfak',      ctypes.c_long),
                ('roimin',      ctypes.c_ulong),
                ('roimax',      ctypes.c_ulong),
                ('eventpreset', ctypes.c_double),
                ('timepreset',  ctypes.c_double),
                ('savedata',    ctypes.c_long),
                ('fmt',         ctypes.c_long),
                ('autoinc',     ctypes.c_long),
                ('cycles',      ctypes.c_long),
                ('sweepmode',   ctypes.c_long),
                ('syncout',     ctypes.c_long),
                ('bitshift',    ctypes.c_long),
                ('digval',      ctypes.c_long),
                ('digio',       ctypes.c_long),
                ('dac0',        ctypes.c_long),
                ('dac1',        ctypes.c_long),
                ('swpreset',    ctypes.c_double),
                ('nregions',    ctypes.c_long),
                ('caluse',      ctypes.c_long),
                ('fstchan',     ctypes.c_double),
                ('active',      ctypes.c_long),
                ('calpoints',   ctypes.c_long), ]

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

class FastComtec(Base, FastCounterInterface):
    """
    unstable: Jochen Scheuer

    Hardware Class for the FastComtec Card.
    """
    _modclass = 'FastComtec'
    _modtype = 'hardware'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

        self.GATED = False
        self.MINIMAL_BINWIDTH = 0.25e-9    # in seconds per bin
        #this variable has to be added because there is no difference
        #in the fastcomtec it can be on "stopped" or "halt"
        self.stopped_or_halt = "stopped"

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.dll = ctypes.windll.LoadLibrary('dp7887.dll')

        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
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
        constraints['hardware_binwidth_list'] = list(self.MINIMAL_BINWIDTH * (2 ** np.array(
                                                     np.linspace(0,24,25))))

        return constraints

    def configure(self, bin_width_s, record_length_s, number_of_gates = 0,sweep_reset=False, preset=None, cycles=None):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time trace
                                  histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single
                                      gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, gate_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual set gate length in seconds
                    number_of_gates: the number of gated, which are accepted
        """

        binwidth_s = self.set_binwidth(bin_width_s)
        no_of_bins = record_length_s / binwidth_s
        if sweep_reset:
            self.set_length(no_of_bins, preset=preset, cycles=cycles)
        else:
            self.set_length(no_of_bins)
        return (self.get_binwidth(), record_length_s, number_of_gates)

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)

        The red out bitshift will be converted to binwidth. The binwidth is
        defined as 2**bitshift*minimal_binwidth.
        """
        return self.MINIMAL_BINWIDTH*(2**int(self.get_bitshift()))

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
        self.dll.GetStatusData(ctypes.byref(status), 0)
        if status.started == 1:
            return 2
        elif status.started == 0:
            if self.stopped_or_halt == "stopped":
                return 1
            elif self.stopped_or_halt == "halt":
                return 3
            else:
                self.log.error('FastComTec neither stopped nor halt')

                return -1
        else:
            self.log.error(
                'There is an unknown status from FastComtec. The status message was %s' % (str(status.started)))
            return -1


    def start_measure(self):
        """Start the measurement. """
        status = self.dll.Start(0)
        while self.get_status() != 2:
            time.sleep(0.05)
        return status

    def pause_measure(self):
        """Make a pause in the measurement, which can be continued. """
        self.stopped_or_halt = "halt"
        status = self.dll.Halt(0)
        while self.get_status() != 3:
            time.sleep(0.05)
        return status

    def stop_measure(self):
        """Stop the measurement. """
        self.stopped_or_halt = "stopped"
        status = self.dll.Halt(0)
        while self.get_status() != 1:
            time.sleep(0.05)
        return status

    def continue_measure(self):
        """Continue a paused measurement. """
        status = self.dll.Continue(0)
        while self.get_status() != 2:
            time.sleep(0.05)
        return status

    def get_data_trace(self, sweep_reset=None):
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

        """ SSR is an optional variable to setup the fastcomtec and allow single-shot readout.
        If this variable is selected, the data is an array of size 'range'.'cycles'. I.e. each
        measurement of length 'range' is repeated 'cycles' number of times.
        """
        if sweep_reset:
            H = setting.cycles
            data = np.empty((H, N / H), dtype=np.uint32)
        else:
            data = np.empty((N,), dtype=np.uint32)

        self.dll.LVGetDat(data.ctypes.data, 0)
        return np.int64(data)


    def get_data_testfile(self):
        ''' Load data test file '''
        data = np.loadtxt(os.path.join(self.get_main_dir(), 'tools', 'FastComTec_demo_timetrace.asc'))
        time.sleep(0.5)
        return data

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return self.GATED

    # =========================================================================
    #                           Non Interface methods
    # =========================================================================

    def get_bitshift(self):
        """Get bitshift from Fastcomtec.

        @return int settings.bitshift: the red out bitshift
        """

        settings = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(settings), 0)
        return int(settings.bitshift)

    def set_bitshift(self, bitshift):
        """ Sets the bitshift properly for this card.

        @param int bitshift:

        @return int: asks the actual bitshift and returns the red out value
        """

        cmd = 'BITSHIFT={0}'.format(bitshift)
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))
        return self.get_bitshift()

    def set_binwidth(self, binwidth):
        """ Set defined binwidth in Card.

        @param float binwidth: the current binwidth in seconds

        @return float: Red out bitshift converted to binwidth

        The binwidth is converted into to an appropiate bitshift defined as
        2**bitshift*minimal_binwidth.
        """
        bitshift = int(np.log2(binwidth/self.MINIMAL_BINWIDTH))
        new_bitshift=self.set_bitshift(bitshift)

        return self.MINIMAL_BINWIDTH*(2**new_bitshift)

    def get_settings(self):
        """ get defined axis nanoseconds or bins
        @return float: settings class object

        """
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        return setting

    #TODO: Check such that only possible lengths are set.
    def set_length(self, N, preset=10000000, cycles=1):
        """ Sets the length of the length of the actual measurement.

        @param int N: Length of the measurement

        @return float: Red out length of measurement
        """

        cmd = 'RANGE={0}'.format(int(N))
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))
        cmd = 'roimax={0}'.format(int(N))
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))

        """ SSR is an optional variable to setup the fastcomtec and allow single-shot readout.
        With this variable selected the range is set as usual, but sweep-preset and cycles
        are also selected in the fastcomtec. A single measurement is repeated 'swpreset' number
        of times and all photons summed together before a new measurement is started on a new
        row of fastcomtec data. In total 'cycles' number of rows are measured.
        """
        cmd = 'swpreset={0}'.format(preset)
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))
        cmd = 'cycles={0}'.format(cycles)
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))

        return self.get_length()

    def get_length(self):
        """ Get the length of the current measurement.

          @return int: length of the current measurement
        """
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        return int(setting.range)

    # =========================================================================
    #   The following methods have to be carefully reviewed and integrated as
    #   internal methods/function, because they might be important one day.
    # =========================================================================

    def SetDelay(self, t):
        #~ setting = AcqSettings()
        #~ self.dll.GetSettingData(ctypes.byref(setting), 0)
        #~ setting.fstchan = t/6.4
        #~ self.dll.StoreSettingData(ctypes.byref(setting), 0)
        #~ self.dll.NewSetting(0)
        self.dll.RunCmd(0, 'DELAY={0:f}'.format(t))
        return self.GetDelay()

    def GetDelay(self):
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        return setting.fstchan * 6.4


    #former SaveData_fast
    def SaveData_locally(self, filename, laser_index):
        # os.chdir(r'D:\data\FastComTec')
        data = self.get_data()
        fil = open(filename + '.asc', 'w')
        for i in laser_index:
            for n in data[i:i+int(round(3000/(self.MINIMAL_BINWIDTH*2**self.GetBitshift())))
                    +int(round(1000/(self.MINIMAL_BINWIDTH*2**self.GetBitshift())))]:
                fil.write('{0!s}\n'.format(n))
        fil.close()

    def SetLevel(self, start, stop):
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        def FloatToWord(r):
            return int((r+2.048)/4.096*int('ffff',16))
        setting.dac0 = ( setting.dac0 & int('ffff0000',16) ) | FloatToWord(start)
        setting.dac1 = ( setting.dac1 & int('ffff0000',16) ) | FloatToWord(stop)
        self.dll.StoreSettingData(ctypes.byref(setting), 0)
        self.dll.NewSetting(0)
        return self.GetLevel()

    def GetLevel(self):
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        def WordToFloat(word):
            return (word & int('ffff',16)) * 4.096 / int('ffff',16) - 2.048
        return WordToFloat(setting.dac0), WordToFloat(setting.dac1)

    #used in one script for SSR
    #Todo: Remove
    def Running(self):
        s = self.GetStatus()
        return s.started

    def GetStatus(self):
        status = AcqStatus()
        self.dll.GetStatusData(ctypes.byref(status), 0)
        return status
