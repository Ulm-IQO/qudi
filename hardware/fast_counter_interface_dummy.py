# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware dummy for fast counting devices.

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
"""

from core.base import Base
from hardware.fast_counter_interface import FastCounterInterface
import time
import os
import numpy as np


class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class FastCounterInterfaceDummy(Base, FastCounterInterface):
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

    def get_binwidth(self):
        return 1000./950.
    
    def start_measure(self):
        time.sleep(1)
        return 0
    
    def pause_measure(self):
        time.sleep(1)
        return 0
        
    def stop_measure(self):
        time.sleep(1)
        return 0
    
    def continue_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>continue_measure')
        return -1

    def is_trace_extractable(self):
        
        raise InterfaceImplementationError('FastCounterInterface>is_trace_extractable')
        return -1
      
    def get_data_trace(self):
        ''' params '''
#        num_of_lasers = 100
#        polarized_count = 200
#        ground_noise = 50
#        laser_length = 3000
#        rise_length = 30
#        tail_length = 1000
#        
#        rising_edge = np.arctan(np.linspace(-10, 10, rise_length))
#        rising_edge = rising_edge - rising_edge.min()
#        falling_edge = np.flipud(rising_edge)
#        low_count = np.full([tail_length], rising_edge.min())
#        high_count = np.full([laser_length], rising_edge.max())
#    
#        gate_length = laser_length + 2*(rise_length + tail_length)
#        trace_length = num_of_lasers * gate_length
#    
#        if self.gated:
#            data = np.empty([num_of_lasers, gate_length], int)
#        else:
#            data = np.empty([trace_length], int)
#    
#        for i in range(num_of_lasers):
#            gauss = signal.gaussian(500,120) / (1 + 3*np.random.random())
#            gauss = np.append(gauss, np.zeros([laser_length-500]))
#            trace = np.concatenate((low_count, rising_edge, high_count+gauss, falling_edge, low_count))
#            trace = polarized_count * (trace / rising_edge.max())
#            trace = np.array(np.rint(trace), int)
#            trace = trace + np.random.randint(-ground_noise, ground_noise, trace.size)
#            for j in range(trace.size):
#                if trace[j] <= 0:
#                    trace[j] = 0
#                else:
#                    trace[j] = trace[j] + np.random.randint(-np.sqrt(trace[j]), np.sqrt(trace[j]))
#                    if trace[j] < 0:
#                        trace[j] = 0 
#            if self.gated:
#                data[i] = trace
#            else:
#                data[i*gate_length:(i+1)*gate_length] = trace
#        data = np.loadtxt('141222_Rabi_old_NV_-11.04dbm_01.asc')
#        data = np.loadtxt('20150701_binning4.asc')
        data = np.loadtxt(os.path.join(self.get_main_dir(), 'tools', 'FastComTec_demo_timetrace.asc'))
        time.sleep(0.5)
        return data
        
    def is_gated(self):
#        return True
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
