# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class ODMRLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for ODMR.
    """
    
    signal_next_line = QtCore.Signal()
    signal_ODMR_plot_updated = QtCore.Signal()
    signal_ODMR_matrix_updated = QtCore.Signal()
    signal_ODMR_finished = QtCore.Signal()

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
        
        self._odmrscan_counter = 0
        self._clock_frequency = 200
        
        self.MW_frequency = 2870.    #in MHz
        self.MW_power = -20.         #in dBm
        self.MW_start = 2700.        #in MHz
        self.MW_stop = 3000.         #in MHz
        self.MW_step = 5.            #in MHz
        
        #number of lines in the matrix plot
        self.NumberofLines = 50 
        
        self.threadlock = Mutex()
        
        self.stopRequested = False
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._MW_device = self.connector['in']['microwave1']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._ODMR_counter = self.connector['in']['odmrcounter']['object']
       
        self.signal_next_line.connect(self._scan_ODMR_line, QtCore.Qt.QueuedConnection)
        
        # Initalize the ODMR plot and matrix image
        self._MW_frequency_list = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step)
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()        
        
        #setting to low power and turning off the input during activation
        self.set_frequency(frequency = -20.)
        self.MW_off()

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock
        
        @param int clock_frequency: desired frequency of the clock 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._clock_frequency = int(clock_frequency)
        #checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            return 0                 
        
    def start_ODMR(self):
        self.lock()
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()
        
        self._ODMR_counter.set_up_odmr_clock(clock_frequency = self._clock_frequency)
        self._ODMR_counter.set_up_odmr()
        
    def kill_ODMR(self):  
        self._ODMR_counter.close_odmr()
        self._ODMR_counter.close_odmr_clock()
        return 0          
    
    def start_ODMR_scan(self):
        self.odmrscan_counter = 0
        
        self._MW_frequency_list = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step)
        self._ODMR_counter.set_odmr_length(len(self._MW_frequency_list))
        
        self._MW_device.set_list(self._MW_frequency_list,self.MW_power)
        self._MW_device.list_on()
        
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()
        
        self.signal_next_line.emit()
        
        
    def stop_ODMR_scan(self):
        """Stop the ODMR scan
        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True            
        return 0        
    
    
    def _initialize_ODMR_plot(self):
        '''Initializing the ODMR line plot.
        '''
        print('initialize odmr xy plot')
        self.ODMR_plot_x = self._MW_frequency_list
        self.ODMR_plot_y = np.zeros(self._MW_frequency_list.shape)
    
    def _initialize_ODMR_matrix(self):
        '''Initializing the ODMR matrix plot.
        '''
        self.ODMR_plot_xy = np.zeros( (self.NumberofLines, len(self._MW_frequency_list)) )
    
    
    def _scan_ODMR_line(self):
        '''Scans one line in ODMR.
        (from MW_start to MW_stop in steps of MW_step)
        '''        
        if self.stopRequested:
            with self.threadlock:
                self.MW_off()
                self.kill_ODMR()
                self.stopRequested = False
                self.unlock()
                self.signal_ODMR_plot_updated.emit() 
                self.signal_ODMR_matrix_updated.emit() 
                return
                
        self._MW_device.reset_listpos()        
        new_counts = self._ODMR_counter.count_odmr(length=len(self._MW_frequency_list))
        
        
        self.ODMR_plot_y = ( self.odmrscan_counter * self.ODMR_plot_y + new_counts ) / (self.odmrscan_counter + 1)
        self.ODMR_plot_xy = np.vstack( (new_counts, self.ODMR_plot_xy[:-1, :]) )
        
        self._odmrscan_counter += 1
        
        self.signal_ODMR_plot_updated.emit() 
        self.signal_ODMR_matrix_updated.emit() 
        self.signal_next_line.emit()


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