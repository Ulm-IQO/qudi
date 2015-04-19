# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.mwsourceinterface import MWInterface
import random

class mwsourcedummy(Base,MWInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        Base.__init__(self, manager, name, configuation=config)
        self._modclass = 'mwsourcedummy'
        self._modtype = 'mwsource'
        
        self.logMsg("The following configuration was found.", 
                    msgType='status')
        
        # checking for the right configuration
        for key in config.keys():
            self.logMsg("{}: {}".format(key,config[key]), 
                        msgType='status')
        
        # trying to load the visa connection
        try: 
            import visa
        except:
            self.logMsg("No visa connection installed. Please install pyvisa.", 
                        msgType='error')
            
        
    def on(self):
        """ Switches on any preconfigured microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        self.logMsg("mwsourcedummy>on", msgType='warning')
        
        return 0
    
    def off(self):
        """ Switches off any microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg("mwsourcedummy>off", msgType='warning')
        
        return 0
    
    def get_power(self):
        """ Gets the microwave output power. 
        
        @return float: the power set at the device
        """
        
        self.logMsg("mwsourcedummy>get_power", msgType='warning')
                    
        return random.uniform(-10, 10)
        
    def set_power(self,power=None):
        """ Sets the microwave output power. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg("mwsourcedummy>set_power, power: {f}".format(power), 
                    msgType='warning')
                    
        return 0
        
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
        
        @return float: the power set at the device
        """
        
        self.logMsg("mwsourcedummy>get_frequency", msgType='warning')
                    
        return random.uniform(0, 1e6)
        
    def set_frequency(self,frequency=0):
        """ Sets the frequency of the microwave output. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg("mwsourcedummy>set_frequency, frequency: {f}".format(power), 
                    msgType='warning')
                    
        return 0
