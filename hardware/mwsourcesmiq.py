# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.mwsourceinterface import MWInterface
import visa
import numpy as np

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
                        msgType='error')
        
        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.logMsg("This is MWSMIQ: did not find >>gpib_timeout<< in \
            configration. I will set it to 10 seconds.", 
                        msgType='error')
        
        # trying to load the visa connection to the module
        rm = visa.ResourceManager()
        try: 
            self._gpib_connetion = rm.open_resource(self._gpib_address, 
                                              timeout=self._gpib_timeout)
        except:
            self.logMsg("This is MWSMIQ: could not connect to the GPIB \
            address >>{}<<.".format(self._gpib_address), 
                        msgType='error')
            raise
            
        self.logMsg("MWSMIQ initialised and connected to hardware.", 
                    msgType='status')
        
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
        
    def set_cw(self,f=None, power=None):
        """ Sets the MW mode to cw and additionally frequency and power
        
        @param float f: frequency to set
        @param float power: power to set
        
        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connetion.write(':FREQ:MODE CW')
        
        if f != None:
            self.set_frequency(f)
        if power != None:
            self.set_power(power)
            
        return 0
        
    def set_list(self,freq=None, power=None):
        """Sets the MW mode to list mode 
        @param list f: list of frequencies
        @param float power: MW power
         
        @return int: error code (0:OK, -1:error)
        """
        error = 0
        
        if self.set_cw(freq[0],power) != 0:
            error = -1
            
        self._gpib_connetion.write('*WAI')
        self._gpib_connetion.write(':LIST:DEL:ALL')
        self._gpib_connetion.write('*WAI')
        self._gpib_connetion.write(":LIST:SEL 'ODMR'")
        FreqString = ''
        
        for f in freq[:-1]:
            FreqString += ' %f,' % f
        FreqString += ' %f' % freq[-1]
      
        self._gpib_connetion.write(':LIST:FREQ' + FreqString)
        self._gpib_connetion.write('*WAI')
        self._gpib_connetion.write(':LIST:POW'  +  (' %f,' % power * len(freq))[:-1])
       
        self._gpib_connetion.write('*WAI')
        self._gpib_connetion.write(':TRIG1:LIST:SOUR EXT')
        self._gpib_connetion.write(':TRIG1:SLOP NEG')
        self._gpib_connetion.write(':LIST:MODE STEP')
        self._gpib_connetion.write('*WAI')
        
        N = int(np.round(float(self._gpib_connetion.ask(':LIST:FREQ:POIN?'))))
        
        if N != len(freq):
            error = -1
            
        return error
        
    def reset_listpos(self):#
        """Reset of MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connetion.write(':FREQ:MODE CW; :FREQ:MODE LIST')
        self._gpib_connetion.write('*WAI')
        return 0
        
    def list_on(self):
        """Activates MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connetion.write(':OUTP ON')
        self._gpib_connetion.write('*WAI')
        self._gpib_connetion.write(':LIST:LEAR')
        self._gpib_connetion.write('*WAI')
        self._gpib_connetion.write(':FREQ:MODE LIST')
        
        return 0
        
    
        
        