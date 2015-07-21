# -*- coding: utf-8 -*-

from core.base import Base
from hardware.microwave.mwsourceinterface import MWInterface
import visa
import numpy as np
from collections import OrderedDict

class Mwsourcesmiq(Base, MWInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    _modclass = 'MWInterface'
    _modtype = 'hardware'
    ## declare connectors
    _out = {'mwsourcesmiq': 'MWInterface'}
    
    def __init__(self, manager, name, config = {}, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)
                      
    def activation(self,e=None):
        # checking for the right configuration
        config = self.getConfiguration()
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.logMsg("This is MWSMIQ: did not find >>gpib_address<< in configration.", msgType='error')
        
        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.logMsg("This is MWSMIQ: did not find >>gpib_timeout<< in configration. I will set it to 10 seconds.", msgType='error')
 
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try: 
            self._gpib_connection = self.rm.open_resource(self._gpib_address, timeout=self._gpib_timeout)
        except:
            self.logMsg("This is MWSMIQ: could not connect to the GPIB address >>{}<<.".format(self._gpib_address), msgType='error')
            raise
            
        self.logMsg("MWSMIQ initialised and connected to hardware.", msgType='status')
    
    def deactivation(self,e=None):
        self._gpib_connection.close()
        self.rm.close()

    def on(self):
        """ Switches on any preconfigured microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        self._gpib_connection.write(':OUTP ON')
        self._gpib_connection.write('*WAI')
        
        return 0


    def off(self):
        """ Switches off any microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._gpib_connection.ask(':FREQ:MODE?') == 'LIST':
            self._gpib_connection.write(':FREQ:MODE CW')
        self._gpib_connection.write(':OUTP OFF')
        self._gpib_connection.write('*WAI')
        
        return 0


    def get_power(self):
        """ Gets the microwave output power. 
        
        @return float: the power set at the device
        """
        
        return float(self._gpib_connection.ask(':POW?'))


    def set_power(self, power = None):
        """ Sets the microwave output power. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        
        if power != None:
            self._gpib_connection.write(':POW {:f}'.format(power))
            return 0
        else:
            return -1
        
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
        
        @return float: the power set at the device
        """
        
        return float(self._gpib_connection.ask(':FREQ?'))


    def set_frequency(self, frequency = None):
        """ Sets the frequency of the microwave output. 
        
        @param float power: this power is set at the device
        
        @return int: error code (0:OK, -1:error)
        """
        if frequency != None:
            self._gpib_connection.write(':FREQ {:e}'.format(frequency))
            return 0
        else:
            return -1


    def set_cw(self, f = None, power = None):
        """ Sets the MW mode to cw and additionally frequency and power
        
        @param float f: frequency to set
        @param float power: power to set
        
        @return int: error code (0:OK, -1:error)
        """
        error = 0
        self._gpib_connection.write(':FREQ:MODE CW')
        
        if f != None:
            error = self.set_frequency(f)
        else:
            return -1
        if power != None:
            error = self.set_power(power)
        else:
            return -1
        
        return error


    def set_list(self,freq=None, power=None):
        """Sets the MW mode to list mode 
        @param list f: list of frequencies
        @param float power: MW power
         
        @return int: error code (0:OK, -1:error)
        """
        error = 0
        

#        if self.set_cw(freq[0],power) != 0:
#            error = -1
            
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:DEL:ALL')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(":LIST:SEL 'ODMR'")
        FreqString = ''
        
        for f in freq[:-1]:
            FreqString += ' {:f},'.format(f)
        FreqString += ' {:f}'.format(freq[-1])
        print(':LIST:FREQ' + FreqString)
        self.test = ':LIST:FREQ' + FreqString

        self._gpib_connection.write(':LIST:FREQ' + FreqString)
        self._gpib_connection.write('*WAI')
      #  print(':LIST:POW'  +  (' %f,' % power * len(freq))[:-1])
       # self._gpib_connection.write(':LIST:POW'  +  (' {:f},'.format( power * len(freq))[:-1]))
        self.test2 = ':LIST:POW '  + str(power)+  ('{0}'.format(( ', '+str(power)) * (len(freq[:-1]))))
       
        self._gpib_connection.write(':LIST:POW '  + str(power)+  ('{0}'.format(( ', '+str(power)) * (len(freq[:-1])))))
        
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':TRIG1:LIST:SOUR EXT')
        self._gpib_connection.write(':TRIG1:SLOP NEG')
        self._gpib_connection.write(':LIST:MODE STEP')
        self._gpib_connection.write('*WAI')
        
        N = int(np.round(float(self._gpib_connection.ask(':LIST:FREQ:POIN?'))))
        
        if N != len(freq):
            error = -1
            
        return error
        
    def reset_listpos(self):#
        """Reset of MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        
        #self._gpib_connection.write(':FREQ:MODE CW; :FREQ:MODE LIST')
        #due an unknown reason the old call above produces timeouts
        self._gpib_connection.write(':FREQ:MODE CW')
        self._gpib_connection.write(':FREQ:MODE LIST')
        self._gpib_connection.write('*WAI')
        return 0
        
    def list_on(self):
        """Activates MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':OUTP ON')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:LEAR')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':FREQ:MODE LIST')
        
        return 0
        
    def trigger(self,source,pol):
        return 0
        
    
        
        
