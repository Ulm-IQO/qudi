# -*- coding: utf-8 -*-

#####################################################
#                                                   #
#   HARDWARE CLASS CURRENTLY NOT WORKING - ALEX S.  #
#                                                   #
#####################################################
from core.base import Base
from hardware.fastcounterinterface import FastCounterInterface

import ctypes 
import os
import numpy, numpy.fft
import time

from collections import OrderedDict

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


class ACQSETTING(ctypes.Structure):
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
    _fields_ = [('s0', ctypes.POINTER(ctypes.c_ulong)),
                ('region', ctypes.POINTER(ctypes.c_ulong)),
                ('comment', ctypes.c_char_p),
                ('cnt', ctypes.POINTER(ctypes.c_double)),
                ('hs0', ctypes.c_int),
                ('hrg', ctypes.c_int),
                ('hcm', ctypes.c_int),
                ('hct', ctypes.c_int), ]

class ACQSTATUS(ctypes.Structure):
    _fields_ = [('started', ctypes.c_int),
                ('runtime', ctypes.c_double),
                ('totalsum', ctypes.c_double),
                ('roisum', ctypes.c_double),
                ('roirate', ctypes.c_double),
                ('ofls', ctypes.c_double),
                ('sweeps', ctypes.c_double),
                ('stevents', ctypes.c_double),
                ('maxval', ctypes.c_ulong), ]



class FastComtecP7887(Base,FastCounterInterface):
    """UNSTABLE: Alex Stark
    
    Hardware Class for the FastComtec Card communicating via the p7887 server.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        Base.__init__(self, manager, name, configuation=config)
        self._modclass = 'fastcomtecp7887'
        self._modtype = 'hardware'


        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'FastCounterInterface'

        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
    
    
        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured taking 100 Hz instead.',
                        msgType='warning')


        self._BINWIDTH = 0.25
        self._dll_name = 'dp7887.dll'
        self._dll_filepath = 'FILEPATH-TO-FIX' + self._dll_name
        self._dll = ctypes.windll.LoadLibrary(self._dll_filepath)

        self._zero = ctypes.c_int(0) 

    def configure(self, duration, bitshift):
        """Configures the Fast Counter.
        
          @param int duration: Duration of the expected measurement
          @param int bitshift: 
        """
        
        self._set_bitshift(int(bitshift))
        
        N = int(duration/(self.BINWIDTH*2**bitshift))
        
        self._set_length(N)

    def _set_bitshift(self, bitshift):
        """ Sets the bitshift properly for this card.
        
          @param int bitshift
          
          @return int: asks the actual bitshift and returns the red out value
          """
        
        self._dll.RunCmd(0, 'BITSHIFT={0}'.format(int(bitshift)))
        return self._get_bitshift()

    def _get_bitshift(self):
        """ Get the current bitshift from the program.                
        
          @param list settings: the values in the list are defined in ACQSETTING.
        """
        
        setting = ACQSETTING()
        self._dll.GetSettingData(ctypes.byref(setting), 0)
        return int(setting.bitshift)

    def _set_length(self, N):
        """Sets the length of the length of the actual measurement.
        
          @param int N: Length of the measurement      
        """
        self._dll.RunCmd(0, 'RANGE={0}'.format(int(N)))
        self._dll.RunCmd(0, 'roimax={0}'.format(int(N)))
        return self._get_length()

    def _get_length(self):
        """ Get the length of the current measurement.
        
          @return int: length of the current measurement
        """
        setting = ACQSETTING()
        self._dll.GetSettingData(ctypes.byref(setting), self._zero)
        
        return int(setting.range)


#    def _get_range(self):
#        """Get the range of the current measurement.
#        
#          @return list(length,bytelength): length is the current length of the
#                                           measurement and bytelength is the
#                                           length in byte.
#        """
#        return self._get_length(), self.BINWIDTH * 2**self.GetBitshift()

    
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
        return value.
        
          @return list status: the values in the list are defined in ACQSTATUS.
        """

        status = ACQSTATUS()
        self._dll.GetStatusData(ctypes.byref(status), self._zero)
        
        return status.runtime, status.sweeps
    
    def start(self):
        """Start the Fast Comtec counter and resets the counting bins."""
        
        self._dll.Start(self._zero)
        status = ACQSTATUS()
        status.started = self._zero
        
        while not status.started:
            time.sleep(0.1)
            self._dll.GetStatusData(ctypes.byref(status), self._zero)
        
    
    def halt(self):
        """Make a pause in the measurement, which can be continued. """
        self._dll.Halt(self._zero)
    
    def continue_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>continue_measure')
        return -1

    def is_trace_extractable(self):
        
        raise InterfaceImplementationError('FastCounterInterface>is_trace_extractable')
        return -1
   
    def get_data_trace(self):
        
        raise InterfaceImplementationError('FastCounterInterface>get_data_trace')
        return -1
      
    def get_data_laserpulses(self):
        """ To extract the laser pulses, a general routine should be written."""
        
        raise InterfaceImplementationError('FastCounterInterface>get_data_laserpulses')
        return -1
        
        
        
        
        
    BINWIDTH=0.25

 


    def SetSoftwareStart(self,b):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        if b:
            setting.sweepmode = setting.sweepmode |  int('10000',2)
            setting.sweepmode = setting.sweepmode &~ int('10000000',2)
        else:
            setting.sweepmode = setting.sweepmode &~ int('10000',2)
            setting.sweepmode = setting.sweepmode |  int('10000000',2)
        dll.StoreSettingData(ctypes.byref(setting), 0)
        dll.NewSetting(0)

    def SetDelay(self, t):
        #~ setting = ACQSETTING()
        #~ dll.GetSettingData(ctypes.byref(setting), 0)
        #~ setting.fstchan = t/6.4
        #~ dll.StoreSettingData(ctypes.byref(setting), 0)
        #~ dll.NewSetting(0)
        dll.RunCmd(0, 'DELAY=%f' % t)
        return self.GetDelay()

    def GetDelay(self):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        return setting.fstchan * 6.4

    def Start(self):
        dll.Start(0)
        status = ACQSTATUS()
        status.started = 0
        while not status.started:
            time.sleep(0.1)
            dll.GetStatusData(ctypes.byref(status), 0)


    def Erase(self):
        dll.Erase(0)

    def Continue(self):
        return dll.Continue(0)

    def GetData(self):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        N = setting.range
        data = numpy.empty((N,), dtype=numpy.uint32 )
        dll.LVGetDat(data.ctypes.data, 0)
        return data

    def GetData2(self, bins, length):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        N = setting.range
        data = numpy.empty((N,), dtype=numpy.uint32 )
        dll.LVGetDat(data.ctypes.data, 0)
        data2 = []
        for bin in bins:
            data2.append(data[bin:bin+length])
        return numpy.array(data2)

    def SaveData_fast(self, filename, laser_index):
        os.chdir(r'D:\data\FastComTec')
        data = self.GetData()
        fil = open(filename + '.asc', 'w')
        for i in laser_index:
            for n in data[i:i+int(round(3000/(0.25*2**self.GetBitshift())))+int(round(1000/(0.25*2**self.GetBitshift())))]:
                fil.write('%s\n'%n)
        fil.close()

    def SaveData(self, filename):
        os.chdir(r'D:\data\FastComTec')
        data = self.GetData()
        fil = open(filename + '.asc', 'w')
        for n in data:
            fil.write('%s\n'%n)
        fil.close()

    def GetState(self):
        status = ACQSTATUS()
        dll.GetStatusData(ctypes.byref(status), 0)
        return status.runtime, status.sweeps

    def Running(self):
        s = self.GetStatus()
        return s.started

    def SetLevel(self, start, stop):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        def FloatToWord(r):
            return int((r+2.048)/4.096*int('ffff',16))
        setting.dac0 = ( setting.dac0 & int('ffff0000',16) ) | FloatToWord(start)
        setting.dac1 = ( setting.dac1 & int('ffff0000',16) ) | FloatToWord(stop)
        dll.StoreSettingData(ctypes.byref(setting), 0)
        dll.NewSetting(0)
        return self.GetLevel()

    def GetLevel(self):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        def WordToFloat(word):
            return (word & int('ffff',16)) * 4.096 / int('ffff',16) - 2.048
        return WordToFloat(setting.dac0), WordToFloat(setting.dac1)

    def ReadSetting(self):
        setting = ACQSETTING()
        dll.GetSettingData(ctypes.byref(setting), 0)
        return setting

    def WriteSetting(self, setting):
        dll.StoreSettingData(ctypes.byref(setting), 0)
        dll.NewSetting(0)

    def GetStatus(self):
        status = ACQSTATUS()
        dll.GetStatusData(ctypes.byref(status), 0)
        return status        
        