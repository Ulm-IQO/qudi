# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 11:43:51 2015

@author: s_ntomek
"""
# unstable: Nikolas Tomek

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime

class PulsedMeasurementLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the control of pulsed measurements.
    """    
    _modclass = 'pulsedmeasurementlogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'fastcounter': 'FastCounterInterface',
            #'pulsegenerator': 'PulserInterfaceDummy',
            'pulseanalysislogic': 'PulseAnalysisLogic',
            'savelogic': 'SaveLogic',
            'mykrowave': 'mykrowave'
            }
    _out = {'pulsedmeasurementlogic': 'PulsedMeasurementLogic'}

    signal_time_updated = QtCore.Signal()
    signal_laser_plot_updated = QtCore.Signal()
    signal_signal_plot_updated = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

        # mykrowave parameters
        self.mykrowave_power = -30. # dbm
        self.mykrowave_freq = 2870. # MHz
        # dictionary containing the fast counter status parameters
        self.fast_counter_status = {}
        # dictionary containing the parameters of the currently running sequence
        self.running_sequence_parameters = {}
        self.running_sequence_parameters['tau_vector'] = np.array(range(50))
        self.running_sequence_parameters['number_of_lasers'] = 50
        # index of the laser pulse to be displayed in the GUI (starting from 1).
        # A value of 0 corresponds to the sum of all laser pulses
        self.display_pulse_no = 0
        
        # timer for data analysis
        self.timer = None
        self.odmrtimer = None
        self.odmrtimer_interval = 0.5 # in seconds
        self.timer_interval = 5 # in seconds
        self.start_time = 0
        self.elapsed_time = 0
        self.elapsed_time_str = '00:00:00:00'
        self.elapsed_sweeps = 0
        
        # analyze windows for laser pulses
        self.signal_start_bin = None
        self.signal_width_bin = None
        self.norm_start_bin = None
        self.norm_width_bin = None
        
        self.fit_result = ([])
        
        # threading
        self.threadlock = Mutex()
        self.stopRequested = False
        
        # plot data
        self.signal_plot_x = None
        self.signal_plot_y = None
        self.laser_plot_x = None
        self.laser_plot_y = None
        
        # raw data
        self.laser_data = None
        self.raw_data = None
        
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        #self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
        self._mycrowave_source_device = self.connector['in']['mykrowave']['object']
        self.update_fast_counter_status()
        self._initialize_signal_plot()
        self._initialize_laser_plot()


    def deactivation(self, e):
        with self.threadlock:
            if self.getState() != 'idle' and self.getState() != 'deactivated':
                self.stop_pulsed_measurement()   
    
    
    def update_fast_counter_status(self):
        ''' This method captures the fast counter status and updates the corresponding class variable
        '''
        self.fast_counter_status = self._fast_counter_device.get_status()
        return
    
    
    def start_pulsed_measurement(self):
        '''Start the analysis thread.
        '''  
        with self.threadlock:
            if self.getState() == 'idle':
                self.update_fast_counter_status()
                # initialize plots
                self._initialize_signal_plot()
                self._initialize_laser_plot()
                # start mykrowave generator
                self.mykrowave_on()
                # start fast counter
                self.fast_counter_on()
                # start pulse generator
                self.pulse_generator_on()
                # set timer
                self.timer = QtCore.QTimer()
                self.timer.setSingleShot(False)
                self.timer.setInterval(int(1000. * self.timer_interval))
                self.timer.timeout.connect(self._pulsed_analysis_loop)
                # start analysis loop and set lock to indicate a running measurement
                self.lock()
                self.start_time = time.time()
                self.timer.start()
        return
        
        
    def _pulsed_analysis_loop(self):
        '''Acquires laser pulses from fast counter, calculates fluorescence signal and creates plots.
        '''
        with self.threadlock:
            # calculate analysis windows
            sig_start = self.signal_start_bin
            sig_end = self.signal_start_bin + self.signal_width_bin
            norm_start = self.norm_start_bin
            norm_end = self.norm_start_bin + self.norm_width_bin
            # analyze pulses and get data points for signal plot
            self.signal_plot_y, self.laser_data, self.raw_data = self._pulse_analysis_logic._analyze_data(sig_start, sig_end, norm_start, norm_end, self.running_sequence_parameters['number_of_lasers'])
            # set x-axis of signal plot
            self.signal_plot_x = self.running_sequence_parameters['tau_vector']
            # set laser plot
            if self.display_pulse_no > 0:
                self.laser_plot_y = self.laser_data[self.display_pulse_no-1]
            else:
                self.laser_plot_y = np.sum(self.laser_data,0)
            self.laser_plot_x = self.fast_counter_status['binwidth_ns'] * np.arange(1, self.laser_data.shape[1]+1)
            # recalculate time
            self.elapsed_time = time.time() - self.start_time
            self.elapsed_time_str = ''
            self.elapsed_time_str += str(int(self.elapsed_time)//86400).zfill(2) + ':' # days
            self.elapsed_time_str += str(int(self.elapsed_time)//3600).zfill(2) + ':' # hours
            self.elapsed_time_str += str(int(self.elapsed_time)//60).zfill(2) + ':' # minutes
            self.elapsed_time_str += str(int(self.elapsed_time) % 60).zfill(2) # seconds
            self.elapsed_sweeps = self.elapsed_time/3
            # emit signals
            self.signal_signal_plot_updated.emit() 
            self.signal_laser_plot_updated.emit() 
            self.signal_time_updated.emit()
            
    
    def stop_pulsed_measurement(self):
        """ Stop the measurement
          @return int: error code (0:OK, -1:error)
        """
        print ("test")
        with self.threadlock:
            if self.getState() == 'locked':
                self.timer.stop()
                self.timer.timeout.disconnect()
                self.timer = None
                self.fast_counter_off()
                self.mykrowave_off()
                self.pulse_generator_off()
                self.signal_signal_plot_updated.emit() 
                self.signal_laser_plot_updated.emit()
                self.unlock()
        return 0  
        
            
    def change_timer_interval(self, interval):
        with self.threadlock:
            self.timer_interval = interval
            if self.timer != None:
                self.timer.setInterval(int(1000. * self.timer_interval))
        return
        
    
    def change_odmrtimer_interval(self, interval):
        with self.threadlock:
            self.odmrtimer_interval = interval
            if self.odmrtimer != None:
                self.odmrtimer.setInterval(1000. * self.timer_interval)
        return
    

    def manually_pull_data(self):
        if self.getState() == 'locked':
            self._pulsed_analysis_loop()

        
     
    def do_fit(self):
        return
     
    
    def _initialize_signal_plot(self):
        '''Initializing the signal line plot.
        '''
        self.signal_plot_x = self.running_sequence_parameters['tau_vector']
        self.signal_plot_y = np.zeros(self.running_sequence_parameters['number_of_lasers'], dtype=float)
    
    
    def _initialize_laser_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        self.laser_plot_x = self.fast_counter_status['binwidth_ns'] * np.arange(1, 3001, dtype=int)
        self.laser_plot_y = np.zeros(3000, dtype=int)


    def _save_data(self):
        #####################################################################
        ####                Save extracted laser pulses                  ####         
        #####################################################################
        filepath = self._save_logic.get_path_for_module(module_name='PulsedMeasurement')
        filelabel = 'laser_pulses'
        timestamp = datetime.datetime.now()
        
        # prepare the data in a dict or in an OrderedDict:
        temp_arr = np.empty([self.laser_data.shape[1], self.laser_data.shape[0]+1])
        temp_arr[:,1:] = self.laser_data.transpose()
        temp_arr[:,0] = self.laser_plot_x
        data = OrderedDict()
        data = {'Time (ns), Signal (counts)': temp_arr}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (ns)'] = self.fast_counter_status['binwidth_ns']
        parameters['laser length (ns)'] = self.fast_counter_status['binwidth_ns'] * self.laser_plot_x.size

        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)
        
        #####################################################################
        ####                Save measurement data                        ####         
        #####################################################################
        filelabel = 'pulsed_measurement'
        
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Tau (ns), Signal (normalized)':np.array([self.signal_plot_x, self.signal_plot_y]).transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (ns)'] = self.fast_counter_status['binwidth_ns']
        parameters['Number of laser pulses'] = self.running_sequence_parameters['number_of_lasers']
        parameters['Signal start (bin)'] = self.signal_start_bin
        parameters['Signal width (bins)'] = self.signal_width_bin
        parameters['Normalization start (bin)'] = self.norm_start_bin
        parameters['Normalization width (bins)'] = self.norm_width_bin


        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)
        
        #####################################################################
        ####                Save raw data timetrace                      ####         
        #####################################################################
        filelabel = 'raw_timetrace'
        
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Signal (counts)': self.raw_data.transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Is counter gated?'] = self.fast_counter_status['is_gated']
        parameters['Bin size (ns)'] = self.fast_counter_status['binwidth_ns']
        parameters['Number of laser pulses'] = self.running_sequence_parameters['number_of_lasers']
        parameters['laser length (ns)'] = self.fast_counter_status['binwidth_ns'] * self.laser_plot_x.size
        parameters['Tau start'] = self.running_sequence_parameters['tau_vector'][0]
        parameters['Tau increment'] = self.running_sequence_parameters['tau_vector'][1] - self.running_sequence_parameters['tau_vector'][0]


        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':')#, as_xml=False, precision=None, delimiter=None)
        return
        
#    def get_tau_list(self):
#        """Get the list containing all tau values in ns for the current measurement.
#        
#        @return numpy array: tau_vector_ns
#        """
#        return self._tau_vector_ns
#
#        
#    def get_number_of_laser_pulses(self):
#        """Get the number of laser pulses for the current measurement.
#        
#        @return int: number_of_laser_pulses
#        """
#        return self._number_of_laser_pulses
#        
#        
#    def get_laser_length(self):
#        """Get the laser pulse length in ns for the current measurement.
#        
#        @return float: laser_length_ns
#        """
#        laser_length_ns = self._laser_length_bins * self._binwidth_ns
#        return laser_length_ns
#        
#        
#    def get_binwidth(self):
#        """Get the binwidth of the fast counter in ns for the current measurement.
#        
#        @return float: binwidth_ns
#        """
#        return self._binwidth_ns
    
        
    def pulse_generator_on(self):
        """Switching on the pulse generator.
        """
        time.sleep(0.1)
        return 0
    
    
    def pulse_generator_off(self):
        """Switching off the pulse generator.
        """
        time.sleep(0.1)
        return 0
        
        
    def fast_counter_on(self):
        """Switching on the fast counter
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.start_measure()
        return error_code

        
    def fast_counter_off(self):
        """Switching off the fast counter
        
        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.stop_measure()
        return error_code
        
    def mykrowave_on(self):
        self._mycrowave_source_device.set_cw(freq=self.mykrowave_freq, power=self.mykrowave_power)
        self._mycrowave_source_device.on()
        return
        
    def mykrowave_off(self):
        self._mycrowave_source_device.off()
        return
#    def do_fit(self, fit_function = None):
#        '''Performs the chosen fit on the measured data.
#        
#        @param string fit_function: name of the chosen fit function
#        '''
#        if fit_function == None:
#            self.ODMR_fit_y = np.zeros(self._MW_frequency_list.shape)
#            self.signal_ODMR_plot_updated.emit()  #ist das hier nötig?
        
        ####Signal to Noise calculation
        """The signal-to-noiuse ratio is defined as the ratio between 
        singal amplitude and its standard deviation"""
        
    def calculate_signal_to_noise_ratio(xdata,ydata):
        pass
    
    def calculate_standard_deviation(xdata,ydata):
        pass
        
#        standard_deviation[i]= np.sqrt()
#        return np.sqrt()
        
        
            
