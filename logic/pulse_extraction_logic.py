# -*- coding: utf-8 -*-
"""
Created on Thu May 28 12:24:25 2015

@author: quantenoptik
"""


from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
from scipy import ndimage

class PulseExtractionLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the extraction of laser pulses.
    """    
    _modclass = 'pulseextractionlogic'
    _modtype = 'logic'
    ## declare connectors
    _in = {'fastcounter': 'FastCounterInterface'}
    _out ={'pulseextractionlogic': 'PulseExtractionLogic'}

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        self.sequence_parameters = {}
        self.sequence_parameters['number_of_lasers'] = 100
        
        self.is_counter_gated = False
        self.conv_std_dev = 5
                      
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._check_if_counter_gated()


    def _gated_extraction(self, count_data):
        """ This method detects the rising flank in the gated timetrace data and extracts just the laser pulses
        """
        # sum up all gated timetraces to ease flank detection
        timetrace_sum = np.sum(count_data, 0)
        # compute the gradient of the timetrace sum
        conv_deriv, conv = self.convolve_derive(timetrace_sum, self.conv_std_dev)
        # get indices of rising and falling flank
        rising_ind = conv_deriv.argmax()
        falling_ind = conv_deriv.argmin()
        # slice the data array to cut off anything but laser pulses
        laser_arr = count_data[:, rising_ind:falling_ind]
        return laser_arr

    
    def _ungated_extraction(self, count_data):
        ''' This method detects the laser pulses in the ungated timetrace data and extracts them
        '''
        conv_deriv = self.convolve_derive(count_data, self.conv_std_dev)
        rising_ind = np.empty([self.sequence_parameters['number_of_lasers']],int)
        falling_ind = np.empty([self.sequence_parameters['number_of_lasers']],int)
        
        for i in range(self.sequence_parameters['number_of_lasers']):
            rising_ind[i] = np.argmax(conv_deriv)
            if rising_ind[i] < 2*self.conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = rising_ind[i] - 2*self.conv_std_dev
            if (conv_deriv.size - rising_ind[i]) < 2*self.conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = rising_ind[i] + 2*self.conv_std_dev
            conv_deriv[del_ind_start:del_ind_stop] = 0
            
            falling_ind[i] = np.argmin(conv_deriv)
            if falling_ind[i] < 2*self.conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = falling_ind[i] - 2*self.conv_std_dev
            if (conv_deriv.size - falling_ind[i]) < 2*self.conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = falling_ind[i] + 2*self.conv_std_dev
            conv_deriv[del_ind_start:del_ind_stop] = 0
            
        rising_ind.sort()
        falling_ind.sort()
        laser_length = np.max(falling_ind-rising_ind)
        np.savetxt('risedata.txt', rising_ind)
        np.savetxt('falldata.txt', falling_ind)
        laser_arr = np.zeros([self.sequence_parameters['number_of_lasers'],laser_length],int)
        for i in range(self.sequence_parameters['number_of_lasers']):
            laser_arr[i] = count_data[rising_ind[i]:rising_ind[i]+laser_length]
        return laser_arr
        
    
    def convolve_derive(self, timetrace, std_dev):    
        conv = ndimage.filters.gaussian_filter1d(timetrace, std_dev)
        conv_deriv = np.gradient(conv)
        return conv_deriv

    
    def get_data_laserpulses(self):
        """ This method captures the fast counter data and extracts the laser pulses.
        """
        raw_data = self._fast_counter_device.get_data()
        if self.is_counter_gated:
            laser_data = self._gated_extraction(raw_data)
        else:
            laser_data = self._ungated_extraction(raw_data)
        return laser_data
    
    
    def _check_if_counter_gated(self):
        '''Check the fast counter if it is gated or not
        '''
        self.is_counter_gated = self._fast_counter_device.is_gated()
        return
