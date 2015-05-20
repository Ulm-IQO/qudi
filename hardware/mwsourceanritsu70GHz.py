# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.mwsourceinterface import MWInterface
import visa
import numpy as np
from collections import OrderedDict

class mwsourceanritsu70GHz(Base,MWInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config = {}, **kwargs):
        Base.__init__(self, manager, name, 
                      configuation=config, callback_dict = {})
        self._modclass = 'mwsourceanritsu70GHz'
        self._modtype = 'mwsource'
        
        ## declare connectors        
        self.connector['out']['mwsourceanritsu70GHz'] = OrderedDict()
        self.connector['out']['mwsourceanritsu70GHz']['class'] = 'MWSource' 
                      
        # checking for the right configuration
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.logMsg("This is MWanritsu70GHz: did not find >>gpib_address<< in \
            configration.", 
                        msgType='error')
        
        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.logMsg("This is MWanritsu70GHz: did not find >>gpib_timeout<< in \
            configration. I will set it to 10 seconds.", 
                        msgType='error')
        
        # trying to load the visa connection to the module
        rm = visa.ResourceManager()
        try: 
            self._gpib_connetion = rm.open_resource(self._gpib_address, 
                                              timeout=self._gpib_timeout)
        except:
            self.logMsg("This is MWanritsu70GHz: could not connect to the GPIB \
            address >>{}<<.".format(self._gpib_address), 
                        msgType='error')
            raise
            
        self.logMsg("MWanritsu70GHz initialised and connected to hardware.", 
                    msgType='status')
                    
                    
    def on(self):
        """ Switches on any preconfigured microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        self._gpib_connetion.write('RF1')
        
        return 0
        
    def off(self):
        """ Switches off any microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connetion.write('RF0')
        
        return 0
        
    def get_power(self):
        """ Gets the microwave output power. 
        
        @return float: the power set at the device
        """
        
        return float(self._gpib_connetion.ask('OL0'))
        
    def set_power(self,power=None):
        """ Sets the microwave output power. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        if power != None:
            self._gpib_connetion.write('RF0 L0 {:f} DM RF1'.format(power))
        
        return 0
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
        
        @return float: the power set at the device
        """
        
        return float(self._gpib_connetion.ask('OF0'))
        
    def set_frequency(self,frequency=None):
        """ Sets the frequency of the microwave output. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        if frequency != None:
            self._gpib_connetion.write('RF0 F0 {:f} HZ RF1'.format(frequency))
            
        return 0
        
    def set_cw(self,f=None, power=None):
        """ Sets the MW mode to cw and additionally frequency and power
        
        @param float f: frequency to set
        @param float power: power to set
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.set_frequency(f)
        self.set_power(power)
        
        self.on()
        
    def set_list(self,freq=None, power=None):
        """Sets the MW mode to list mode 
        @param list f: list of frequencies
        @param float power: MW power
         
        @return int: error code (0:OK, -1:error)
        """
        error = 0
        
        if self.set_cw(freq[0],power) != 0:
            error = -1
            
        f = ''
        p = ''
        
        for s in freq[:-1]:
            f += '{:i} HZ, '.format(s)
            p += '{:f} DM, '.format(power)
            
        f += '{:i} HZ'.format(freq[-1])
        p += '{:f} DM'.format(power)
        stop = '{:i}'.format(len(freq)-1)
        
        while len(stop) < 4:
            stop = '0' + stop
            
        self._gpib_connetion.write('RF0 LST ELN0 ELI0000 LF ' + f + ' LP ' + p + 'LIB0000 LIE{:s}'.format(stop) + 'RF1')
        
        return error
        
    def reset_listpos(self):#
        """Reset of MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connetion.write('ELI0')
        self._gpib_connetion.write('*WAI')
        
        return 0
        
    def list_on(self):
        """Activates MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        
        pass
    
    def trigger(self,source,pol):
        
        self._gpib_connetion.write(':TRIG:SOUR '+source)
        self._gpib_connetion.write(':TRIG:SLOP '+pol)
        self._gpib_connetion.write('*WAI')