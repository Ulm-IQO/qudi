# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class WavemeterInterface():
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    def start_acqusition(self):
        """ Method to start the wavemeter software. 
        
        @return int: error code (0:OK, -1:error)
        
        Also the actual threaded method for getting the current wavemeter reading is started.
        """
        
        raise InterfaceImplementationError('WavemeterInterface>start_acqusition')
        return -1
        
    def stop_acqusition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('WavemeterInterface>stop_acqusition')
        return -1
        
    def get_current_wavelength(self, kind="air"):
        """ This method returns the current wavelength.
        
        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.
        
        @return float: wavelength (or negative value for errors)
        """
        raise InterfaceImplementationError('WavemeterInterface>get_current_wavelength')
        return -1.
        
    def get_current_wavelength2(self, kind="air"):
        """ This method returns the current wavelength of the second input channel.
        
        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.
        
        @return float: wavelength (or negative value for errors)
        """
        raise InterfaceImplementationError('WavemeterInterface>get_current_wavelength2')
        return -1.
        
    def get_timing(self):
        """ Get the timing of the internal measurement thread.
        
        @return float: clock length in second
        """
        raise InterfaceImplementationError('WavemeterInterface>get_timing')
        return -1.
        
    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.
        
        @param float timing: clock length in second
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('WavemeterInterface>set_timing')
        return -1
        