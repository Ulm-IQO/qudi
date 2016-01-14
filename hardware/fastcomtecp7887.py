# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware file implementation for FastComtec p7887 .

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

#TODO: Missing: set binwidth, set length,

#TODO: start stop works but pause does not work, i guess gui/logic problem
#TODO: What does get status do or need as return?
#TODO: Is the method get frequency really needed
#TODO: Where is the conversion from bins to ns

#Not written modules:
#TODO: configure
#TODO: get_status
#TODO: get_binwidth
#TODO: is_trace_extractable


from core.base import Base
from hardware.fast_counter_interface import FastCounterInterface
import time
import os
import numpy as np
import ctypes

class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class FastComtec(Base, FastCounterInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    _modclass = 'fastcounterinterface'
    _modtype = 'hardware'
    # connectors
    _out = {'fastcounter': 'FastCounterInterface'}

    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
        self.gated = False
         
        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self.dll = ctypes.windll.LoadLibrary('dp7887.dll')

        return

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    def configure(self):
        """Configures the Fast Counter."""
        
        raise InterfaceImplementationError('FastCounterInterface>configure')
        return -1
        

    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as return value."""
        status = {'binwidth_ns': 1000./950.}
        status['is_gated'] = self.gated
        time.sleep(0.2)
        return status

#    TODO: What should the status be it asks for something with binwidth but in the interface there is only the status of
    #card if running or halt or stopped ...
    # def get_status(self):
    #     #TODO: Find out if it is possible to get the status for other modes
    #     """
    #     Receives the current status of the Fast Counter and outputs it as return value.
    #     0 = unconfigured
    #     1 = idle
    #     2 = running
    #     3 = paused
    #     -1 = error state
    #     """
    #     status = AcqStatus()
    #     self.dll.GetStatusData(ctypes.byref(status), 0)
    #     if status.started == 0:
    #         return 0
    #     if status.started == 1:
    #         return 2
    #     else:
    #         self.logMsg('There is an unknown status from FastComtec. The status message was %s'%(str(status.started)), msgType='error')
    #         return -1

    def get_binwidth(self):
        return 1000./950.
    
    def start_measure(self):
        self.dll.Start(0)
        return 0

    def pause_measure(self):
        self.dll.Halt(0)
        return 0
        
    def stop_measure(self):
        self.dll.Halt(0)
        return 0
    
    def continue_measure(self):
        self.dll.Continue(0)
        return 0

    def is_trace_extractable(self):
        
        raise InterfaceImplementationError('FastCounterInterface>is_trace_extractable')
        return -1

    def get_data_trace(self):
        """
        Polls the current timetrace data from the fast counter and returns it as a numpy array (dtype = int64).
        The binning specified by calling configure() must be taken care of in this hardware class.
        A possible overflow of the histogram bins must be caught here and taken care of.
        If the counter is UNgated it will return a 1D-numpy-array with returnarray[timebin_index]
        If the counter is gated it will return a 2D-numpy-array with returnarray[gate_index, timebin_index]
        """
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        N = setting.range
        data = np.empty((N,), dtype=np.uint32)
        self.dll.LVGetDat(data.ctypes.data, 0)
        return np.int64(data)

    def get_data_testfile(self):
        ''' Load data test file '''
        data = np.loadtxt(os.path.join(self.get_main_dir(), 'tools', 'FastComTec_demo_timetrace.asc'))
        time.sleep(0.5)
        return data
        
    def is_gated(self):
        return self.gated
        
    def get_frequency(self):
        freq = 950.
        time.sleep(0.5)
        return freq

        
#    def save_raw_trace(self,path):
#        """A fast way of saving the raw data directly."""
#        
#        raise InterfaceImplementationError('FastCounterInterface>save_raw_trace')
#        return -1
#        
#    def save_raw_laserpulses(self,path):
#        """A fast way of saving the raw data directly."""
#        
#        raise InterfaceImplementationError('FastCounterInterface>save_raw_laserpulses')
#        return -1


class AcqStatus(ctypes.Structure):
    """
    Retrieving the status data from Fastcomtec

    int started;                // aquisition status: 1 if running, 0 else
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