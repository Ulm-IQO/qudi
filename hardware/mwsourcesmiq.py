# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.mwsourceinterface import MWInterface
import visa


class mwsourcesmiq(Base,MWInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config = {}, **kwargs):
        Base.__init__(self, manager, name, 
                      configuation=config, callback_dict = {})
        self._modclass = 'mwsourcedummy'
        self._modtype = 'mwsource'
                      
        # checking for the right configuration
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.logMsg("This is MWSMIQ: did not find >>gpib_address<< in \
            configration.", 
                        messageType='error')
        
        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.logMsg("This is MWSMIQ: did not find >>gpib_timeout<< in \
            configration. I will set it to 10 seconds.", 
                        messageType='error')
        
        # trying to load the visa connection to the module
        rm = visa.ResourceManager()
        try: 
            self._gpib_connetion = rm.open_resource(self._gpib_address, 
                                              timeout=self._gpib_timeout)
        except:
            self.logMsg("This is MWSMIQ: could not connect to the GPIB \
            address >>{}<<.".format(self._gpib_address), 
                        messageType='error')
            raise
            
        self.logMsg("MWSMIQ initialised and connected to hardware.", 
                    messageType='status')
        
    def on(self):
        """ Switches on any preconfigured microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        self._gpib_connetion.write(':OUTP ON')
        self._gpib_connetion.write('*WAI')
        
        return 0
    
    def off(self):
        """ Switches off any microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._gpib_connetion.ask(':FREQ:MODE?') == 'LIST':
            self._gpib_connetion.write(':FREQ:MODE CW')
        self._gpib_connetion.write(':OUTP OFF')
        self._gpib_connetion.write('*WAI')
        
        return 0
        
    def power(self,power=None):
        """ Sets and gets the microwave output power. 
        
        @param float power: if defined, this power is set at the device
        
        @return float: the power set at the device
        """
        # This is not a good way to implement it!
        self.logMsg("This is MWSMIQ>power: Bad implementation, \
        use get and set.", 
                    messageType='error')
        return 0.0
    
    def get_power(self):
        """ Gets the microwave output power. 
        
        @return float: the power set at the device
        """
        
        return float(self._gpib_connetion.ask(':POW?'))
        
    def set_power(self,power=None):
        """ Sets the microwave output power. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connetion.write(':POW {:f}'.format(power))
        return 0
        
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
        
        @return float: the power set at the device
        """
        
        return float(self._gpib_connetion.ask(':FREQ?'))
        
    def set_frequency(self,frequency=0):
        """ Sets the frequency of the microwave output. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connetion.write(':FREQ {:e}'.format(frequency))
        return 0