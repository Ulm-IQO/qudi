# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.ODMRCounterInterface import ODMRCounterInterface
from collections import OrderedDict
import random
import time

import numpy as np

class ODMRCounterInterfaceDummy(Base,ODMRCounterInterface):
    """This is the Dummy hardware class that simulates the controls for a simple ODMR.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'odmrcounterinterface'
        self._modtype = 'hardware'

        self.connector['out']['odmrcounter'] = OrderedDict()
        self.connector['out']['odmrcounter']['class'] = 'ODMRCounterInterfaceDummy'
        self.connector['in']['fitlogic'] = OrderedDict()
        self.connector['in']['fitlogic']['class'] = 'FitLogic'
        self.connector['in']['fitlogic']['object'] = None
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
    
        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured taking 100 Hz instead.', \
            msgType='warning')
            
        self._scanner_counter_daq_task = None
        self._odmr_length = None
        
        
        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        print('here you go')
        self._fit_logic = self.connector['in']['fitlogic']['object']
    
    
    def set_up_odmr_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)
            
        self.logMsg('ODMRCounterInterfaceDummy>set_up_odmr_clock', 
                    msgType='warning')
                    
        time.sleep(0.2)
        
        return 0
        
    
    def set_up_odmr(self, counter_channel = None, photon_source = None, clock_channel = None, odmr_trigger_channel = None):
        """ Configures the actual counter with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string odmr_trigger_channel: if defined, this specifies the trigger output for the microwave
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('ODMRCounterInterfaceDummy>set_up_odmr', 
                    msgType='warning')
                    
        if self.getState() == 'locked' or self._scanner_counter_daq_task != None:            
            self.logMsg('Another odmr is already running, close this one first.', \
            msgType='error')
            return -1
                            
        time.sleep(0.2)
                
        return 0
        
    def set_odmr_length(self,length = 100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave.
        
        @param int length: length of microwave sweep in pixel
        
        @return int: error code (0:OK, -1:error)
        """
        

        self._odmr_length = length
        
        self.logMsg('ODMRCounterInterfaceDummy>set_odmr_length', 
                    msgType='warning')
        
        return 0
        
    def count_odmr(self, length = 100):
        """ Sweeps the microwave and returns the counts on that sweep. 
        
        @param int length: length of microwave sweep in pixel
        
        @return float[]: the photon counts per second
        """
        
        if self.getState() == 'locked':
            self.logMsg('A scan_line is already running, close this one first.', \
            msgType='error')
            return -1
            
        self.lock()
        
        
        self._odmr_length = length
            
        count_data = np.empty((self._odmr_length,), dtype=np.uint32)
        
#        for i in range(self._odmr_length):
#            count_data[i] = random.uniform(0, 1e6)
        count_data = np.random.uniform(0,5e4,length)
            
        count_data += self._fit_logic.gaussian_function(x_data = np.arange(1,length+1,1),amplitude=-30000, x_zero=length/3, sigma=3, offset=50000)
        count_data += self._fit_logic.gaussian_function(x_data = np.arange(1,length+1,1),amplitude=-30000, x_zero=2*length/3, sigma=3, offset=50000)
            
        time.sleep(self._odmr_length*1./self._clock_frequency)
        
        self.logMsg('ODMRCounterInterfaceDummy>count_odmr: length {0:d}.'.format(self._odmr_length), 
                    msgType='warning')
                    
        self.unlock()
        
        return count_data
        

    def close_odmr(self):
        """ Closes the odmr and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('ODMRCounterInterfaceDummy>close_odmr', 
                    msgType='warning')
                    
        self._scanner_counter_daq_task = None
        
        return 0
        
    def close_odmr_clock(self):
        """ Closes the odmr and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """     
        
        self.logMsg('ODMRCounterInterfaceDummy>close_odmr_clock', 
                    msgType='warning')
                            
        return 0
