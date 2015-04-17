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
        
    def set_list(self,frequency=None, power=None):
        """ Sets the microwave output to list.
        
        @return int: Returns the number of items of the list.
        """
        raise InterfaceImplementationError('MWInterface>set_list')
        return -1
        
    def reset_listpos(self):
        """
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>reset_listpos')
        return -1
                
    def list_on(self):
        """ Switches on the list mode. 
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>list_on')
        return -1
        
    def set_sweep(self,frequency_start=None,frequency_stop=None,frequency_delta=None):
        """
        """
        raise InterfaceImplementationError('MWInterface>set_sweep')
        return -1
        
    def sweep_pos(self,frequency=None):
        """
        """
        raise InterfaceImplementationError('MWInterface>sweep_pos')
        return -1
        
    def trigger(self,source,pol):
        """
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MWInterface>trigger')
        return -1
        
    def set_modulation(self,flag=None):
        """
        """
        raise InterfaceImplementationError('MWInterface>set_modulation')
        return -1
        
    def output(self):
        """
        """
        raise InterfaceImplementationError('MWInterface>output')
        return -1
        
    def am(self,depth=None):
        """
        
        @return float:
        """
        raise InterfaceImplementationError('MWInterface>am')
        return -1
        
    
        
    