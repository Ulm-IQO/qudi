# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
from lmfit import Parameters
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
                        
        self.MW_trigger_source = 'EXT'
        self.MW_trigger_pol = 'POS'
        
        self._odmrscan_counter = 0
        self._clock_frequency = 200
        self.fit_function = 'No Fit'
        
        self.MW_frequency = 2870.    #in MHz
        self.MW_power = -30.         #in dBm
        self.MW_start = 2800.        #in MHz
        self.MW_stop = 2950.         #in MHz
        self.MW_step = 2.            #in MHz
        
        self.RunTime = 10
        self.ElapsedTime = 0
        
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
        self.ODMR_fit_x = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step/10.)
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()        
        
        #setting to low power and turning off the input during activation
        self.set_frequency(frequency = self.MW_frequency)
        self.set_power(power = self.MW_power)
        self.MW_off()
        self._MW_device.trigger(source = self.MW_trigger_source, pol = self.MW_trigger_pol)


    def deactivation(self, e):
        '''Tasks that are required to be performed during deactivation of the module.
        '''
        #deconnecting from the MW-source
        pass


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
        '''Starting the ODMR counter.
        '''
        self.lock()        
        self._ODMR_counter.set_up_odmr_clock(clock_frequency = self._clock_frequency)
        self._ODMR_counter.set_up_odmr()
        
        
    def kill_ODMR(self):
        '''Stopping the ODMR counter.
        '''  
        self._ODMR_counter.close_odmr()
        self._ODMR_counter.close_odmr_clock()
        return 0          
    
    
    def start_ODMR_scan(self):
        '''Starting an ODMR scan.
        '''
        self._odmrscan_counter = 0
        self._StartTime = time.time()
        self.ElapsedTime = 0
        
        self._MW_frequency_list = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step)
        self.ODMR_fit_x = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step/10.)
#        self._ODMR_counter.set_odmr_length(len(self._MW_frequency_list))
        
        self.start_ODMR()
        
        self._MW_device.set_list(self._MW_frequency_list*1e6, self.MW_power)  #times 1e6 to have freq in Hz
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
        self.ODMR_plot_x = self._MW_frequency_list
        self.ODMR_plot_y = np.zeros(self._MW_frequency_list.shape)
        self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)
    
    
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
                self._MW_device.set_cw(f=self.MW_frequency,power=self.MW_power)
                self.kill_ODMR()
                self.stopRequested = False
                self.unlock()
                self.signal_ODMR_plot_updated.emit() 
                self.signal_ODMR_matrix_updated.emit() 
                return
                
        self._MW_device.reset_listpos()        
        new_counts = self._ODMR_counter.count_odmr(length=len(self._MW_frequency_list))
        
        
        self.ODMR_plot_y = ( self._odmrscan_counter * self.ODMR_plot_y + new_counts ) / (self._odmrscan_counter + 1)
        self.ODMR_plot_xy = np.vstack( (new_counts, self.ODMR_plot_xy[:-1, :]) )
        
        self._odmrscan_counter += 1
        
        self.ElapsedTime = time.time() - self._StartTime
        if self.ElapsedTime >= self.RunTime:
            self.do_fit(fit_function = 'Double Lorentzian')
            self.stopRequested = True
        
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
        
        if isinstance(frequency,(int, float)):
            self.MW_frequency = frequency
        else:
            return -1
        
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._MW_device.set_frequency(frequency*1e6) #times 1e6 to have freq in Hz
            return error_code
    
    
    def get_frequency(self):
        """Getting the current frequency from the MW source.
        
        @return float: current frequency off the MW source
        """
        frequency = self._MW_device.get_frequency()/1e6 #divided by 1e6 to get freq in MHz
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
        
        
    def do_fit(self, fit_function = None):
        '''Performs the chosen fit on the measured data.
        
        @param string fit_function: name of the chosen fit function
        '''
        self.fit_function = fit_function
        
        if self.fit_function == 'No Fit':
            self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)
            self.signal_ODMR_plot_updated.emit()#ist das hier nötig?
            
        elif self.fit_function == 'Lorentzian':
            result = self._fit_logic.make_lorentzian_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            lorentzian,params=self._fit_logic.make_lorentzian_model()
            self.ODMR_fit_y = lorentzian.eval(x=self.ODMR_fit_x, params=result.params)
            
            
        elif self.fit_function =='Double Lorentzian':
            result = self._fit_logic.make_double_lorentzian_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            double_lorentzian,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = double_lorentzian.eval(x=self.ODMR_fit_x, params=result.params)

        elif self.fit_function =='Double Lorentzian with fixed splitting':
            p=Parameters()
#            TODO: insert this in gui config of ODMR
            splitting_from_gui_config=3.03 #in MHz
            p.add('lorentz1_center',expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))
            result = self._fit_logic.make_double_lorentzian_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=p)
            double_lorentzian,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = double_lorentzian.eval(x=self.ODMR_fit_x, params=result.params)
            
        elif self.fit_function =='N14':
            result = self._fit_logic.make_N14_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            fitted_funciton,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=3)
            self.ODMR_fit_y = fitted_funciton.eval(x=self.ODMR_fit_x, params=result.params)
            
        elif self.fit_function =='N15':
            result = self._fit_logic.make_N15_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            fitted_funciton,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = fitted_funciton.eval(x=self.ODMR_fit_x, params=result.params)