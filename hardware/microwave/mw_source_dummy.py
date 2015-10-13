# -*- coding: utf-8 -*-

from core.base import Base
from hardware.microwave.mwsourceinterface import MWInterface
import random
from collections import OrderedDict



class mwsourcedummy(Base,MWInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    _modclass = 'MWInterface'
    _modtype = 'mwsource'
    
    ## declare connectors
    _out = {'mwsourcedummy': 'MWInterface'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)
        
        self.logMsg("The following configuration was found.", msgType='status')
        
        # checking for the right configuration
        for key in config.keys():
            self.logMsg("{}: {}".format(key,config[key]), msgType='status')
        
        # trying to load the visa connection
        try: 
            import visa
        except:
            self.logMsg("No visa connection installed. Please install pyvisa.", msgType='error')

    def activation(self, e):
        pass
            
    def deactivation(self, e):
        pass

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
        self.logMsg("mwsourcedummy>set_power, power: {0:f}".format(power), msgType='warning')
        return 0
        
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
        
        @return float: the power set at the device
        """
        self.logMsg("mwsourcedummy>get_frequency", msgType='warning')
        return random.uniform(0, 1e6)
        
    def set_frequency(self, frequency=None):
        """ Sets the frequency of the microwave output. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        self.logMsg("mwsourcedummy>set_frequency, frequency: {0:f}".format(frequency), msgType='warning')
        return 0

    def set_cw(self, freq=None, power=None):
        """ Sets the MW mode to cw and additionally frequency and power
        
        @param float freq: frequency to set
        @param float power: power to set
        
        @return int: error code (0:OK, -1:error)
        """
        self.logMsg("mwsourcedummy>set_cw, frequency: {0:f}, power{0:f}:".format(freq, power), msgType='warning')
        return 0
        
    def set_list(self, freq=None, power=None):
        """Sets the MW mode to list mode 
        @param list f: list of frequencies
        @param float power: MW power
         
        @return int: error code (0:OK, -1:error)
        """
        #FIXME: the following line raises an error
        #self.logMsg("mwsourcedummy>set_list, frequency: {0:f}".format(freq), 
        #            msgType='warning')
        return 0
        
    def reset_listpos(self):#
        """Reset of MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        self.logMsg("mwsourcedummy>reset_listpos", msgType='warning')
        return 0
        
    def list_on(self):
        """Activates MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        self.logMsg("mwsourcedummy>list_on", msgType='warning')
        return 0
        
        
    def trigger(self,source,pol):
        pass
        

