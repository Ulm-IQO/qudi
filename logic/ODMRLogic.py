# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
import numpy as np
import time

class ODMRLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for ODMR.
    """    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'odmrlogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['odmrcounter'] = OrderedDict()
        self.connector['in']['odmrcounter']['class'] = 'ODMRCounterInterface'
        self.connector['in']['odmrcounter']['object'] = None
        self.connector['in']['fitlogic'] = OrderedDict()
        self.connector['in']['fitlogic']['class'] = 'FitLogic'
        self.connector['in']['fitlogic']['object'] = None
        self.connector['in']['microwave1'] = OrderedDict()
        self.connector['in']['microwave1']['class'] = 'mwsourceinterface'
        self.connector['in']['microwave1']['object'] = None
        
        self.connector['out']['odmrlogic'] = OrderedDict()
        self.connector['out']['odmrlogic']['class'] = 'ODMRLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        self._scan_counter = 0
        self._clock_frequency = 200
        
        self.MW_frequency = 2870.    #in MHz
        self.MW_power = -40.         #in dBm
        self.MW_start = 2700.        #in MHz
        self.MW_stop = 3000.         #in MHz
        self.MW_step = 5.            #in MHz
                       
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._MW_device = self.connector['in']['microwave1']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._ODMR_counter = self.connector['in']['odmrcounter']['object']
            
    
    def start_ODMR(self):
        self._scan_counter = 0
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()
        
        
    def stop_ODMR(self):
        pass        
    
    def _initialize_ODMR_plot(self):
        pass
    
    def _initialize_ODMR_matrix(self):
        pass
    
    def _scan_ODMR_line(self):
        pass
    

    def set_power(self, power = None):
        """Forwarding the desired new power from the GUI to the MW source.
        
        @param float power: power set at the GUI
        
        @return int: error code (0:OK, -1:error)
        """
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._MW_device.set_power(power)
            return error_code
    
    
    def get_power(self):
        """Getting the current power from the MW source.
        
        @return float: current power off the MW source
        """
        power = self._MW_device.get_power()
        return power
    
    
    def set_frequency(self, frequency = None):
        """Forwarding the desired new frequency from the GUI to the MW source.
        
        @param float frequency: frequency set at the GUI
        
        @return int: error code (0:OK, -1:error)
        """
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._MW_device.set_frequency(frequency)
            return error_code
    
    
    def get_frequency(self):
        """Getting the current frequency from the MW source.
        
        @return float: current frequency off the MW source
        """
        frequency = self._MW_device.get_frequency()
        return frequency
        
        
    def MW_on(self):
        """Switching on the MW source.
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._MW_device.on()
        return error_code
    
    
    def MW_off(self):
        """Switching off the MW source.
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._MW_device.off()
        return error_code