# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.ConfocalScannerInterface import ConfocalScannerInterface
from collections import OrderedDict
import random
import time

import numpy as np

class ConfocalScannerInterfaceDummy(Base,ConfocalScannerInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        Base.__init__(self, manager, name, configuation=config)
        self._modclass = 'confocalscannerinterface'
        self._modtype = 'hardware'

        self.connector['out']['confocalscanner'] = OrderedDict()
        self.connector['out']['confocalscanner']['class'] = 'ConfocalScannerInterface'
        
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
            
        self._line_length = None
        self._voltage_range = [-10., 10.]
        
        self._position_range=[[-10., 10.], [-10., 10.], [-10., 10.], [-10., 10.]]
        
        self._current_position = [0., 0., 0., 0.]
    
    
    def get_position_range(self):
        """ Returns the physical range of the scanner.
        
        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """ 
        return self._position_range
        
    def set_position_range(self, myrange=[[0,1],[0,1],[0,1],[0,1]]):
        """ Sets the physical range of the scanner.
        
        @param float [4][2] myrange: array of 4 ranges with an array containing lower and upper limit
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if not isinstance( myrange, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given range is no array type.', \
            msgType='error')
            return -1
            
        if len(myrange) != 4:
            self.logMsg('Given range should have dimension 4, but has {0:d} instead.'.format(len(myrange)), \
            msgType='error')
            return -1
            
        for pos in myrange:
            if len(pos) != 2:
                self.logMsg('Given range limit {1:d} should have dimension 2, but has {0:d} instead.'.format(len(pos),pos), \
                msgType='error')
                return -1
            if pos[0]>pos[1]:
                self.logMsg('Given range limit {0:d} has the wrong order.'.format(pos), \
                msgType='error')
                return -1
                
        self._position_range = myrange    
            
        return 0
        
    def set_voltage_range(self, myrange=[-10.,10.]):
        """ Sets the voltage range of the NI Card.
        
        @param float [2] myrange: array containing lower and upper limit
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if not isinstance( myrange, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given range is no array type.', \
            msgType='error')
            return -1
            
        if len(myrange) != 2:
            self.logMsg('Given range should have dimension 2, but has {0:d} instead.'.format(len(myrange)), \
            msgType='error')
            return -1
            
        if myrange[0]>myrange[1]:
            self.logMsg('Given range limit {0:d} has the wrong order.'.format(myrange), \
            msgType='error')
            return -1
                
        self._voltage_range = myrange    
            
        return 0


    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)
            
        self.logMsg('ConfocalScannerInterfaceDummy>set_up_scanner_clock', 
                    msgType='warning')
                    
        time.sleep(0.5)
        
        return 0
    
    
    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None, scanner_ao_channels = None):
        """ Configures the actual scanner with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string scanner_ao_channels: if defined, this specifies the analoque output channels
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('ConfocalScannerInterfaceDummy>set_up_scanner', 
                    msgType='warning')
                    
        time.sleep(0.5)
        
        return 0
        
        
    def scanner_set_pos(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        
        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('ConfocalScannerInterfaceDummy>scanner_set_pos: [{0:f},{1:f},{2:f},{3:f}]'.format(x,y,z,a), 
                    msgType='warning')
                    
        time.sleep(0.01)
        
        return 0
        
    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.
        
        @param int length: length of the line in pixel
        
        @return int: error code (0:OK, -1:error)
        """

        self._line_length = length
        
        self.logMsg('ConfocalScannerInterfaceDummy>set_up_line', 
                    msgType='warning')
        
        return 0
        
        
    def scan_line(self, voltages = None):
        """ Scans a line and returns the counts on that line. 
        
        @param float[][4] voltages: array of 4-part tuples defining the voltage points
        
        @return float[]: the photon counts per second
        """
        
        if not isinstance( voltages, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given voltage list is no array type.', \
            msgType='error')
            return np.array([-1.])
        
        if np.shape(voltages)[1] != self._line_length:
            self.set_up_line(np.shape(voltages)[1])
            
        count_data = np.empty((self._line_length,), dtype=np.uint32)
        
        for i in range(self._line_length):
            count_data[i] = random.uniform(0, 1e6)
            
        time.sleep(self._line_length*1./self._clock_frequency)
        
        self.logMsg('ConfocalScannerInterfaceDummy>scan_line: length {0:d}.'.format(self._line_length), 
                    msgType='warning')
                    
        
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
        
        self.logMsg('ConfocalScannerInterfaceDummy>close_scanner', 
                    msgType='warning')
        return 0
        
    def close_scanner_clock(self,power=0):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self.logMsg('ConfocalScannerInterfaceDummy>close_scanner_clock', 
                    msgType='warning')
        return 0
