from core.base import Base
from hardware.fastcounterinterface import FastCounterInterface
from collections import OrderedDict
import time
from scipy import signal

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
    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'fastcounterinterface'
        self._modtype = 'hardware'

        self.connector['out']['fastcounter'] = OrderedDict()
        self.connector['out']['fastcounter']['class'] = 'FastCounterInterfaceDummy'
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
         
        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        return
    
    def configure(self):
        """Configures the Fast Counter."""
        
        raise InterfaceImplementationError('FastCounterInterface>configure')
        return -1
        
    
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as return value."""
        status = {'binwidth_ns': 1000./950.}
        time.sleep(1)
        return status
    
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
        
        raise InterfaceImplementationError('FastCounterInterface>get_data_trace')
        return -1
      
    def get_data(self):
        rising_edge = np.arctan(np.linspace(-10,10))
        rising_edge = rising_edge - rising_edge.min()
        falling_edge = np.flipud(rising_edge)
        low_count = np.full([200], rising_edge.min())
        high_count = np.full([3000], rising_edge.max())
        
        data = np.array([], int)
        for i in range(100):
            gauss=signal.gaussian(500,120)/(1+np.random.random()*3)
            gauss=np.append(gauss, np.zeros([2500]))
            trace = 100000*np.concatenate((low_count, rising_edge, high_count+gauss, falling_edge, low_count))
            trace = np.array(np.rint(trace),int)
            trace = trace + np.random.randint(0,10000,trace.size)
            data = np.append(data, trace)
#        data = np.empty([100,trace.size],int)
#        for i in range(data.shape[0]):
#            data[i] = trace
        time.sleep(1)
        return data
        
    def is_gated(self):
#        return True
        return False
        
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