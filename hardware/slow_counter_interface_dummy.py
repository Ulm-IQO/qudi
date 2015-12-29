# -*- coding: utf-8 -*-

from core.base import Base
from hardware.slow_counter_interface import SlowCounterInterface
from collections import OrderedDict
import random
import time

import numpy as np

class SlowCounterInterfaceDummy(Base,SlowCounterInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    _modclass = 'slowcounterinterface'
    _modtype = 'hardware'
    # connectors
    _out = {'counter': 'SlowCounterInterface'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuration=config, callbacks = c_dict)
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
    
    def activation(self, e):
        config = self.getConfiguration()
        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured taking 100 Hz instead.', \
            msgType='warning')
            
        if 'samples_number' in config.keys():
            self._samples_number=config['samples_number']
        else:
            self._samples_number=10
            self.logMsg('No samples_number configured taking 10 instead.', \
            msgType='warning')

        if 'photon_source2' in config.keys():
            self._photon_source2 = 1
        else:
            self._photon_source2 = None

    def deactivation(self, e):
        pass
    
    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)
            
        self.logMsg('slowcounterinterfacedummy>set_up_clock', 
                    msgType='warning')
                    
        time.sleep(0.1)
        
        return 0
    
    
    def set_up_counter(self, counter_channel = None, photon_source = None, clock_channel = None):
        """ Configures the actual counter with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('slowcounterinterfacedummy>set_up_counter', 
                    msgType='warning')
                    
        time.sleep(0.1)
        
        return 0
        
        
    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter. 
        
        @param int samples: if defined, number of samples to read in one go
        
        @return float: the photon counts per second
        """
        
#        self.logMsg('slowcounterinterfacedummy>get_counter', 
#                    msgType='warning')
                    
        if samples == None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)
        
        count_data = np.empty([2,samples], dtype=np.uint32) # count data will be written here in the NumPy array
        
        for i in range(samples):
            count_data[0][i] = random.uniform(0, 1e6)
        
        if self._photon_source2 is not None:
            for i in range(samples):
                count_data[1][i] = random.uniform(0, 1e5)
            
        time.sleep(1./self._clock_frequency*samples)
        
        return count_data
    
    def close_counter(self):
        """ Closes the counter and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('slowcounterinterfacedummy>close_counter', 
                    msgType='warning')
        return 0
        
    def close_clock(self,power=0):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('slowcounterinterfacedummy>close_clock', 
                    msgType='warning')
        return 0
