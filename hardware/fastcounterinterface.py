# -*- coding: utf-8 -*-

#####################################################
#                                                   #
#HARDWARE INTERFACE CURRENTLY NOT WORKING - ALEX S. #
#                                                   #
#####################################################


from core.util.customexceptions import InterfaceImplementationError

class FastCounterInterface():
    """ UNSTABLE: Alex Stark 
     Interface class to define the controls for fast counting devices. """
    
    
    def configure(self):
        """ Initialize and open the connection to the Fast Counter and configure it."""
        
        raise InterfaceImplementationError('FastCounterInterface>configure')
        return -1
        
    
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as return value."""
        
        raise InterfaceImplementationError('FastCounterInterface>get_status')
        return -1
    
    def start_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>start')
        return -1
        
    def stop_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>stop')
        return -1
    
    def pause_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>pause_measure')
        return -1
    
    def continue_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>continue_measure')
        return -1

    def is_gated(self):
        
        raise InterfaceImplementationError('FastCounterInterface>is_gated')
        return -1
   
    def get_data_trace(self):
        
        raise InterfaceImplementationError('FastCounterInterface>get_data_trace')
        return -1
      
#    def get_data_laserpulses(self):
#        """ To extract the laser pulses, a general routine should be written."""
#        
#        raise InterfaceImplementationError('FastCounterInterface>get_data_laserpulses')
#        return -1
        
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