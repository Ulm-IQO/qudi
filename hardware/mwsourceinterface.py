# -*- coding: utf-8 -*-

class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MWInterface():
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def on(self):
        """ Switches on any preconfigured microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        raise InterfaceImplementationError('MWInterface>on')
        return -1
    
    def off(self):
        """ Switches off any microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>off')
        return -1
        
    def get_power(self):
        """ Gets the microwave output power. 
        
        @return float: the power set at the device
        """
        raise InterfaceImplementationError('MWInterface>get_power')
        return 0.0
        
    def set_power(self,power=0.):
        """ Sets the microwave output power. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>set_power')
        return -1
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
    
        @return float: the power set at the device
        """
        raise InterfaceImplementationError('MWInterface>get_frequency')
        return 0.0
        
    def set_frequency(self,frequency=0):
        """ Sets the frequency of the microwave output. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>set_frequency')
        return -1
        
    def set_cw(self,frequency=None, power=None, useinterleave=None):
        """ Sets the microwave output to CW. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>set_cw')
        return -1