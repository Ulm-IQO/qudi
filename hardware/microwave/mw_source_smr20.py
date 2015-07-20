# -*- coding: utf-8 -*-

from core.base import Base
from hardware.microwave.mwsourceinterface import MWInterface
import visa
import numpy as np
from collections import OrderedDict

class MWSourceSMR20(Base,MWInterface):
    """ The hardware control for the device Rohde and Schwarz SMR 20. 
    
    For additional information concerning the commands to communicate via the 
    GPIB connection through visa, please have a look at:
    
    http://cdn.rohde-schwarz.com/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/s/smr_1/smr_20-40.pdf    
    """
    _modclass = 'MWInterface'
    _modtype = 'hardware'
    ## declare connectors
    _out = {'MWSourceSMR20': 'MWInterface'}

    def __init__(self, manager, name, config = {}, **kwargs):
        cb = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb)

    def activation(self, e):
        # checking for the right configuration
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.logMsg('MWSourceSMR20: did not find >>gpib_address<< in configration.', msgType='error')
        
        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.logMsg('MWSourceSMR20: did not find >>gpib_timeout<< in configration. I will set it to 10 seconds.', msgType='error')
        
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try: 
            self._gpib_connection = rm.open_resource(self._gpib_address, timeout=self._gpib_timeout)
            self.logMsg('MWSourceSMR20: initialised and connected to hardware.', msgType='status')
        except:
            self.logMsg('MWSourceSMR20: could not connect to the GPIB address >>{0}<<.'.format(self._gpib_address), msgType='error')

    def deactivation(self, e):
        self._gpib_connection.close()
        self.rm.close()
        
    def on(self):
        """ Switches on any preconfigured microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        self._gpib_connection.write(':OUTP ON')
        #self._gpib_connection.write('*WAI')
        
        return 0
        
    def off(self):
        """ Switches off any microwave output. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._gpib_connection.ask(':FREQ:MODE?') == 'LIST':
            self._gpib_connection.write(':FREQ:MODE CW')
        self._gpib_connection.write(':OUTP OFF')
        #self._gpib_connection.write('*WAI')
        
        return 0
        
    def get_power(self):
        """ Gets the microwave output power. 
        
        @return float: the power set at the device in dBm
        """
        
        return float(self._gpib_connection.ask(':POW?'))
        
    def set_power(self,power):
        """ Sets the microwave output power. 
        
        @param float power: the power (in dBm) set for this device
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connection.write(':POW {:f}'.format(power))
        return 0
        
    def get_frequency(self):
        """ Gets the frequency of the microwave output. 
        
        @return float: frequency (in Hz), which is currently set for this device
        """
        
        return float(self._gpib_connection.ask(':FREQ?'))
        
    def set_frequency(self,freq):
        """ Sets the frequency of the microwave output. 
        
        @param float freq: the frequency (in Hz) set for this device
        
        @return int: error code (0:OK, -1:error)
        """
        
        
        self._gpib_connection.write(':FREQ {:e}'.format(freq))
        # {:e} meens a representation in float with exponential style
        return 0
        
    def set_cw(self,freq=None, power=None):
        """ Sets the MW mode to cw and additionally frequency and power
        
        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        
        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':FREQ:MODE CW')
        
        if freq != None:
            self.set_frequency(freq)
        if power != None:
            self.set_power(power)
        
        self.on()
        
        return 0
        
    def set_list(self,freq=None, power=None):
        """Sets the MW mode to list mode 
        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm
         
        @return int: error code (0:OK, -1:error)
        """
        error = 0
        
        if self.set_cw(freq[0],power) != 0:
            self.logMsg('The frequency list has an invalide first frequency '
                        'and power, which cannot be set.', msgType='error')
            error = -1
            
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:DEL:ALL')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(":LIST:SEL 'ODMR'")
        FreqString = ''
        
        for f in freq[:-1]:
            FreqString += ' {:f},'.format(f)
        FreqString += ' {:f},'.format(freq[-1])
      
        self._gpib_connection.write(':LIST:FREQ' + FreqString)
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:POW' + (' {:f},'.format(power * len(freq))[:-1]))
       
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':TRIG1:LIST:SOUR EXT')
        self._gpib_connection.write(':TRIG1:SLOP NEG')
        self._gpib_connection.write(':LIST:MODE STEP')
        self._gpib_connection.write('*WAI')
        
        N = int(np.round(float(self._gpib_connection.ask(':LIST:FREQ:POIN?'))))
        
        if N != len(freq):
            error = -1
            self.logMsg('The input Frequency list does not corresponds to the '
                        'generated List from the SMR20.', msgType='error')
        return error
        
    def reset_listpos(self):
        """Reset of MW List Mode
         
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connection.write(':FREQ:MODE CW; :FREQ:MODE LIST')
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
    
    def turn_AM_on(self,depth):
        """ Turn on the Amplitude Modulation mode. 
        
        @param float depth: modulation depth in percent (from 0 to 100%). 
        
        @return int: error code (0:OK, -1:error)
        
        Set the Amplitude modulation based on an external DC signal source and
        switch on the device after configuration.
        """

        self._gpib_connection.write('AM:SOUR EXT')
        self._gpib_connection.write('AM:EXT:COUP DC')
        self._gpib_connection.write('AM {:f}'.format(float(depth)))
        self._gpib_connection.write('AM:STAT ON')
        self._gpib_connection.write('*WAI')
        
        return 0
        
    def turn_AM_off(self):
        """ Turn off the Amlitude Modulation Mode.
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._gpib_connection.write(':AM:STAT OFF')
        self._gpib_connection.write('*WAI')
        
        return 0
        
