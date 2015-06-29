# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError


class ODMRCounterInterface():
    """This is the Interface class supplies the controls for a simple ODMR.
    """
        
    
    def set_up_odmr_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        raise InterfaceImplementationError('ODMRCounterInterface>set_up_odmr_clock')
        return -1
        
    
    def set_up_odmr(self, counter_channel = None, photon_source = None, clock_channel = None, odmr_trigger_channel = None):
        """ Configures the actual counter with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string odmr_trigger_channel: if defined, this specifies the trigger output for the microwave
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ODMRCounterInterface>set_up_odmr')
        return -1
        
        
    def set_odmr_length(self, length = 100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave.
        
        @param int length: length of microwave sweep in pixel
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ODMRCounterInterface>set_odmr_length')
        return -1
        
        
    def count_odmr(self, length = 100):
        """ Sweeps the microwave and returns the counts on that sweep. 
        
        @param int length: length of microwave sweep in pixel
        
        @return float[]: the photon counts per second
        """
        
        raise InterfaceImplementationError('ODMRCounterInterface>count_odmr')
        return [0.0]
        

    def close_odmr(self):
        """ Closes the odmr and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ODMRCounterInterface>close_odmr')
        return -1
        
        
    def close_odmr_clock(self):
        """ Closes the odmr and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """     
        
        raise InterfaceImplementationError('ODMRCounterInterface>close_odmr_clock')
        return -1
        