# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.confocalscannerinterface import ConfocalScannerInterface
from collections import OrderedDict
import random
import time

import numpy as np

class confocalscannerinterfacedummy(Base,ConfocalScannerInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        Base.__init__(self, manager, name, configuation=config)
        self._modclass = 'confocalscannerinterface'
        self._modtype = 'hardware'

        self.connector['out']['confocalscanner'] = OrderedDict()
        self.connector['out']['confocalscanner']['class'] = 'confocalscannerinterface'
        
        self.logMsg('The following configuration was found.', 
                    messageType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        messageType='status')
    
        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured taking 100 Hz instead.', \
            messageType='warning')
            
    
    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)
            
        self.logMsg('confocalscannerinterfacedummy>set_up_scanner_clock', 
                    messageType='warning')
                    
        time.sleep(0.5)
        
        return 0
    
    
    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None):
        """ Configures the actual scanner with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('confocalscannerinterfacedummy>set_up_scanner', 
                    messageType='warning')
                    
        time.sleep(0.5)
        
        return 0
        
        
    def scan_line(self, voltages = None):
        """ Scans a line and returns the counts on that line. 
        
        @param float[][4] voltages: array of 4-part tuples defining the voltage points
        
        @return float[]: the photon counts per second
        """
        
#        self.logMsg('slowcounterinterfacedummy>get_counter', 
#                    messageType='warning')
        length = 100
        count_data = np.empty((length,), dtype=np.uint32)
        
        for i in range(length):
            count_data[i] = random.uniform(0, 1e6)
            
        time.sleep(1./self._clock_frequency)
        
        return count_data
        
    def scanner_position_to_volt(self, positions = None):
        """ Converts a set of position pixels to acutal voltages.
        
        @param float[][4] positions: array of 4-part tuples defining the pixels
        
        @return float[][4]: array of 4-part tuples of corresponing voltages
        """
        
        return positions
    
    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('confocalscannerinterfacedummy>close_scanner', 
                    messageType='warning')
        return 0
        
    def close_scanner_clock(self,power=0):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('confocalscannerinterfacedummy>close_scanner_clock', 
                    messageType='warning')
        return 0
