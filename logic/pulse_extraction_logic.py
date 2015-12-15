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
    _out = {'pulseextractionlogic': 'PulseExtractionLogic'}

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
        
        self.is_counter_gated = False
        self.conv_std_dev = 5
                      
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._check_if_counter_gated()
        
    def deactivation(self, e):
        """ 
        """        
        return


    def _gated_extraction(self, count_data):
        """ This method detects the rising flank in the gated timetrace data and extracts just the laser pulses
          @param 2D numpy.ndarray count_data: the raw timetrace data from a gated fast counter (dimensions 0: gate number, 1: time bin)
          @return  2D numpy.ndarray: The extracted laser pulses of the timetrace (dimensions 0: laser number, 1: time bin) 
        """
        # sum up all gated timetraces to ease flank detection
        timetrace_sum = np.sum(count_data, 0)
        # apply gaussian filter to remove noise and compute the gradient of the timetrace sum
        conv_deriv = self._convolve_derive(timetrace_sum, self.conv_std_dev)
        # get indices of rising and falling flank
        rising_ind = conv_deriv.argmax()
        falling_ind = conv_deriv.argmin()
        # slice the data array to cut off anything but laser pulses
        laser_arr = count_data[:, rising_ind:falling_ind]
        return laser_arr

    
    def _ungated_extraction(self, count_data, num_of_lasers):
        """ This method detects the laser pulses in the ungated timetrace data and extracts them
          @param 1D numpy.ndarray count_data: the raw timetrace data from an ungated fast counter
          @param int num_of_lasers: The total number of laser pulses inside the pulse sequence
          @return 2D numpy.ndarray: The extracted laser pulses of the timetrace (dimensions 0: laser number, 1: time bin) 
        """
        # apply gaussian filter to remove noise and compute the gradient of the timetrace
        conv_deriv = self._convolve_derive(count_data, self.conv_std_dev)
        # initialize arrays to contain indices for all rising and falling flanks, respectively
        rising_ind = np.empty([num_of_lasers],int)
        falling_ind = np.empty([num_of_lasers],int)
        # Find as many rising and falling flanks as there are laser pulses in the timetrace
        for i in range(num_of_lasers):
            # save the index of the absolute maximum of the derived timetrace as rising flank position
            rising_ind[i] = np.argmax(conv_deriv)
            # set this position and the sourrounding of the saved flank to 0 to avoid a second detection 
            if rising_ind[i] < 2*self.conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = rising_ind[i] - 2*self.conv_std_dev
            if (conv_deriv.size - rising_ind[i]) < 2*self.conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = rising_ind[i] + 2*self.conv_std_dev
            conv_deriv[del_ind_start:del_ind_stop] = 0
            
            # save the index of the absolute minimum of the derived timetrace as falling flank position
            falling_ind[i] = np.argmin(conv_deriv)
            # set this position and the sourrounding of the saved flank to 0 to avoid a second detection
            if falling_ind[i] < 2*self.conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = falling_ind[i] - 2*self.conv_std_dev
            if (conv_deriv.size - falling_ind[i]) < 2*self.conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = falling_ind[i] + 2*self.conv_std_dev
            conv_deriv[del_ind_start:del_ind_stop] = 0
        # sort all indices of rising and falling flanks 
        rising_ind.sort()
        falling_ind.sort()
        # find the maximum laser length to use as size for the laser array
        laser_length = np.max(falling_ind-rising_ind)
        # initialize the empty output array
        laser_arr = np.zeros([num_of_lasers, laser_length],int)
        # slice the detected laser pulses of the timetrace and save them in the output array
        for i in range(num_of_lasers):
            if (rising_ind[i]+laser_length > count_data.size):
                lenarr = count_data[rising_ind[i]:].size
                laser_arr[i, 0:lenarr] = count_data[rising_ind[i]:]
            else:
                laser_arr[i] = count_data[rising_ind[i]:rising_ind[i]+laser_length]
        return laser_arr
        
    
    def _convolve_derive(self, data, std_dev):    
        """ This method smoothes the input data by applying a gaussian filter (convolution) with 
            specified standard deviation. The derivative of the smoothed data is computed afterwards and returned.
            If the input data is some kind of rectangular signal containing high frequency noise, 
            the output data will show sharp peaks corresponding to the rising and falling flanks of the input signal. 
          @param 1D numpy.ndarray timetrace: the raw data to be smoothed and derived
          @param float std_dev: standard deviation of the gaussian filter to be applied for smoothing
          @return 1D numpy.ndarray: The smoothed and derived data 
        """
        conv = ndimage.filters.gaussian_filter1d(data, std_dev)
        conv_deriv = np.gradient(conv)
        return conv_deriv

    
    def get_data_laserpulses(self, num_of_lasers):
        """ This method captures the fast counter data and extracts the laser pulses.
          @param int num_of_lasers: The total number of laser pulses inside the pulse sequence
          @return 2D numpy.ndarray: The extracted laser pulses of the timetrace (dimensions 0: laser number, 1: time bin)
          @return 1D/2D numpy.ndarray: The raw timetrace from the fast counter
        """
        # poll data from the fast countin device
        raw_data = self._fast_counter_device.get_data_trace()
        # call appropriate laser extraction method depending on if the fast counter is gated or not.
        if self.is_counter_gated:
            laser_data = self._gated_extraction(raw_data)
        else:
            laser_data = self._ungated_extraction(raw_data, num_of_lasers)
        return laser_data, raw_data
        
    
    def _check_if_counter_gated(self):
        '''Check the fast counter if it is gated or not
        '''
        self.is_counter_gated = self._fast_counter_device.is_gated()
        return
