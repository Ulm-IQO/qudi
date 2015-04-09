# -*- coding: utf-8 -*-

class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class SlowCounterInterface():
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def set_up_clock(self):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """ 
        raise InterfaceImplementationError('SlowCounterInterface>set_up_clock')
        return -1
    
    def set_up_counter(self):
        """ Configures the actual counter with a given clock. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('SlowCounterInterface>set_up_counter')
        return -1
        
    def get_counter(self):
        """ Returns the current counts per second of the counter. 
        <blank line>
        @return float: the photon counts per second
        """
        # This is not a good way to implement it!
        raise InterfaceImplementationError('SlowCounterInterface>get_counter')
        return 0.0
    
    def close_counter(self):
        """ Closes the counter and cleans up afterwards. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('SlowCounterInterface>close_counter')
        return -1
        
    def close_clock(self,power=0):
        """ Closes the clock and cleans up afterwards. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('SlowCounterInterface>close_clock')
        return -1