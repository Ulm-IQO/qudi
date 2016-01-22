# -*- coding: utf-8 -*-
# unstable: Nikolas Tomek

from logic.generic_logic import GenericLogic
import numpy as np

class PulseAnalysisLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the analysis of laser pulses.
    """    
    _modclass = 'pulseanalysislogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'pulseextractionlogic': 'PulseExtractionLogic',
            'fitlogic': 'FitLogic'
            }
    _out = {'pulseanalysislogic': 'PulseAnalysisLogic'}

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
        
        self.fit_result = ([])
        
                      
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._pulse_extraction_logic = self.connector['in']['pulseextractionlogic']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        return


    def deactivation(self, e):
        pass  
            
       
    def _analyze_data(self, norm_start_bin, norm_end_bin, signal_start_bin, signal_end_bin, num_of_lasers):
        # acquire data from the pulse extraction logic 
        laser_data, raw_data = self._pulse_extraction_logic.get_data_laserpulses(num_of_lasers)
        # Initialize the signal and normalization mean data arrays
        reference_mean = np.zeros(num_of_lasers, dtype=float)
        signal_mean = np.zeros(num_of_lasers, dtype=float)
        signal_area = np.zeros(num_of_lasers, dtype=float)
        reference_area = np.zeros(num_of_lasers, dtype=float)
        measuring_error = np.zeros(num_of_lasers, dtype=float)
        # initialize data arrays
        signal_data = np.empty(num_of_lasers, dtype=float)
        # loop over all laser pulses and analyze them
        for ii in range(num_of_lasers):
            # calculate the mean of the data in the normalization window
            reference_mean[ii] = laser_data[ii][norm_start_bin:norm_end_bin].mean()
            # calculate the mean of the data in the signal window
            signal_mean[ii] = (laser_data[ii][signal_start_bin:signal_end_bin] - reference_mean[ii]).mean()
            # update the signal plot y-data
            signal_data[ii] = 1. + (signal_mean[ii]/reference_mean[ii])

            
        for jj in range(num_of_lasers):
            signal_area[jj] = laser_data[jj][signal_start_bin:signal_end_bin].sum()
            reference_area[jj] = laser_data[jj][norm_start_bin:norm_end_bin].sum()
            
            measuring_error[jj] = self.calculate_measuring_error(signal_area[jj], reference_area[jj])
            #print(measuring_error[jj])
            
        #return data
        #print (measuring_error)
        return signal_data, laser_data, raw_data, measuring_error
        
     
    def do_fit(self):
        return

    def calculate_measuring_error(self,signal_area,reference_area):

        #with respect to gaußian error 'evolution'
        measuring_error=signal_area/reference_area*np.sqrt(1/signal_area+1/reference_area)
        
        return measuring_error     
        
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
#        
#        
#    def do_fit(self, fit_function = None):
#        '''Performs the chosen fit on the measured data.
#        
#        @param string fit_function: name of the chosen fit function
#        '''
#        if fit_function == None:
#            self.ODMR_fit_y = np.zeros(self._MW_frequency_list.shape)
#            self.signal_ODMR_plot_updated.emit()  #ist das hier nötig?
            
