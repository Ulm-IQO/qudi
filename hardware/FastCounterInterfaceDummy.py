from core.Base import Base
from hardware.fastcounterinterface import FastCounterInterface
from collections import OrderedDict
import time

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
        
        raise InterfaceImplementationError('FastCounterInterface>get_status')
        return -1
    
    def start(self):
        time.sleep(1)
        return
    
    def halt(self):
        time.sleep(1)
        return
    
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
        data = np.random.randint(900, 1101, size=(100,3800))
        time.sleep(1)
        return data
        
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