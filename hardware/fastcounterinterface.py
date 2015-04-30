# -*- coding: utf-8 -*-

#####################################################
#                                                   #
#HARDWARE INTERFACE CURRENTLY NOT WORKING - ALEX S. #
#                                                   #
#####################################################




class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class FastCounterInterface():
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    
    def configure(self):
        """Configures the Fast Counter."""
        
        raise InterfaceImplementationError('FastCounterInterface>configure')
        return -1
        
    
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as return value."""
        
        raise InterfaceImplementationError('FastCounterInterface>get_status')
        return -1
    
    def start(self):
        
        raise InterfaceImplementationError('FastCounterInterface>start')
        return -1
    
    def halt(self):
        
        raise InterfaceImplementationError('FastCounterInterface>halt')
        return -1
    
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