# -*- coding: utf-8 -*-
# unstable: Nikolas Tomek

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class PulseAnalysisLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the analysis of laser pulses.
    """    
    signal_analysis_next = QtCore.Signal()
    signal_laser_plot_updated = QtCore.Signal()
    signal_signal_plot_updated = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'pulseanalysislogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['fastcounter'] = OrderedDict()
        self.connector['in']['fastcounter']['class'] = 'FastCounterInterface'
        self.connector['in']['fastcounter']['object'] = None
        
        self.connector['in']['sequencegenerator'] = OrderedDict()
        self.connector['in']['sequencegenerator']['class'] = 'SequenceGeneratorLogic'
        self.connector['in']['sequencegenerator']['object'] = None
        
        self.connector['out']['pulseanalysislogic'] = OrderedDict()
        self.connector['out']['pulseanalysislogic']['class'] = 'PulseAnalysisLogic'        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        self._sequence_names = None
        
#        self._binwidth_ns = 1.
#        self._laser_length_bins = 3800
#        self._number_of_laser_pulses = 100
        
        self.fluorescence_signal_start_bin = 0
        self.fluorescence_signal_width_bins = 200
        self.norm_start_bin = 2000
        self.norm_width_bins = 200
#        self._tau_vector_ns = np.array(range(100))
        
        self.threadlock = Mutex()
        
        self.stopRequested = False
                      
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._sequence_generator_logic = self.connector['in']['sequencegenerator']['object']
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._get_measurement_parameters()
        self._initialize_signal_plot()
        self._initialize_laser_plot()
        self.signal_analysis_next.connect(self._analyze_data, QtCore.Qt.QueuedConnection)


    def _get_measurement_parameters(self):
        """Gets the important parameters from the sequence generator module
        """
        self._sequence_names = self._sequence_generator_logic.get_sequence_names()
        self._binwidth_ns = 1000./self._fast_counter_device.get_frequency()
        self._number_of_laser_pulses = self._sequence_generator_logic.get_number_of_laser_pulses()
        self._tau_vector_ns = self._sequence_generator_logic.get_tau_vector()
        self._laser_length_bins = self._sequence_generator_logic.get_laser_length()
    
    
    def start_pulsed_measurement(self):
        '''Calculate the fluorescence contrast and create plots.
        '''
        # initialize plots
        self._initialize_signal_plot()
        self._initialize_laser_plot()
        
        # get parameters for the measurement
        self._get_measurement_parameters()
        
        # start pulse generator
        self.pulse_generator_on()
        
        # start fast counter
        self.fast_counter_on()
        
        # start analysis loop and set lock to indicate a running measurement
        self.lock()
        self.signal_analysis_next.emit()
        
        
    def stop_pulsed_measurement(self):
        """Stop the measurement
        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True            
        return 0        
    
    
    def _analyze_data(self):
        '''Acquires laser pulses from fast counter, calculates fluorescence signal and creates plots.
        '''        
        if self.stopRequested:
            with self.threadlock:
                self.fast_counter_off()
                self.pulse_generator_off()
                self.stopRequested = False
                self.unlock()
                self.signal_signal_plot_updated.emit() 
                self.signal_laser_plot_updated.emit() 
                return
        
        norm_mean = np.zeros(self._number_of_laser_pulses, dtype=np.float)
        signal_mean = np.zeros(self._number_of_laser_pulses, dtype=np.float)
        
        norm_start = self.norm_start_bin
        norm_end = self.norm_start_bin + self.norm_width_bins
        signal_start = self.fluorescence_signal_start_bin
        signal_end = self.fluorescence_signal_start_bin + self.fluorescence_signal_width_bins
        
        new_laser_data = self._fast_counter_device.get_data_laserpulses()   
        
        for i in range(self._number_of_laser_pulses):
            norm_mean[i] = new_laser_data[i][norm_start:norm_end].mean()
            signal_mean[i] = (new_laser_data[i][signal_start:signal_end] - norm_mean[i]).mean()
            self.signal_plot_y[i] = 1. + (signal_mean[i]/norm_mean[i])
            self.laser_plot_y += new_laser_data[i]
        
        self.signal_signal_plot_updated.emit() 
        self.signal_laser_plot_updated.emit() 
        self.signal_analysis_next.emit()
        
        
    def _initialize_signal_plot(self):
        '''Initializing the signal line plot.
        '''
        self.signal_plot_x = self._tau_vector_ns
        self.signal_plot_y = np.zeros(self._number_of_laser_pulses, dtype=np.float)
    
    
    def _initialize_laser_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        self.laser_plot_x = self._binwidth_ns * np.arange(1, self._laser_length_bins+1, dtype=np.int)
        self.laser_plot_y = np.zeros(self._laser_length_bins, dtype=np.int)

    
    def get_tau_list(self):
        """Get the list containing all tau values in ns for the current measurement.
        
        @return numpy array: tau_vector_ns
        """
        return self._tau_vector_ns

        
    def get_number_of_laser_pulses(self):
        """Get the number of laser pulses for the current measurement.
        
        @return int: number_of_laser_pulses
        """
        return self._number_of_laser_pulses
        
        
    def get_laser_length(self):
        """Get the laser pulse length in ns for the current measurement.
        
        @return float: laser_length_ns
        """
        laser_length_ns = self._laser_length_bins * self._binwidth_ns
        return laser_length_ns
        
        
    def get_binwidth(self):
        """Get the binwidth of the fast counter in ns for the current measurement.
        
        @return float: binwidth_ns
        """
        return self._binwidth_ns
    
        
    def pulse_generator_on(self):
        """Switching on the pulse generator.
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._sequence_generator_logic.pulse_generator_on()
        return error_code
    
    
    def pulse_generator_off(self):
        """Switching off the pulse generator.
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._sequence_generator_logic.pulse_generator_off()
        return error_code
        
        
    def fast_counter_on(self):
        """Switching on the fast counter
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.start()
        return error_code

        
    def fast_counter_off(self):
        """Switching off the fast counter
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.halt()
        return error_code
        
        
#    def do_fit(self, fit_function = None):
#        '''Performs the chosen fit on the measured data.
#        
#        @param string fit_function: name of the chosen fit function
#        '''
#        if fit_function == None:
#            self.ODMR_fit_y = np.zeros(self._MW_frequency_list.shape)
#            self.signal_ODMR_plot_updated.emit()  #ist das hier nötig?
            