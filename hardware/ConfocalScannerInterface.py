# -*- coding: utf-8 -*-

class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ConfocalScannerInterface():
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        raise InterfaceImplementationError('ConfocalScannerInterface>set_up_scanner_clock')
        return -1
    
    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None):
        """ Configures the actual scanner with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ConfocalScannerInterface>set_up_scanner')
        return -1
        
    def scanner_set_pos(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        
        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ConfocalScannerInterface>scanner_set_pos')
        return -1
        
    def scan_line(self, voltages = None):
        """ Scans a line and returns the counts on that line. 
        
        @param float[][4] voltages: array of 4-part tuples defining the voltage points
        
        @return float[]: the photon counts per second
        """
        
        raise InterfaceImplementationError('ConfocalScannerInterface>scan_line')
        return [0.0]
        
    def scanner_position_to_volt(self, positions = None):
        """ Converts a set of position pixels to acutal voltages.
        
        @param float[][4] positions: array of 4-part tuples defining the pixels
        
        @return float[][4]: array of 4-part tuples of corresponing voltages
        """
    
    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ConfocalScannerInterface>close_scanner')
        return -1
        
    def close_scanner_clock(self,power=0):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        raise InterfaceImplementationError('ConfocalScannerInterface>close_scanner_clock')
        return -1