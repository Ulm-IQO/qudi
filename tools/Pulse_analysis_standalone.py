# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 16:35:51 2015
This file contains a class for standalone analysis of fast counter data.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
"""

import numpy as np
from scipy import ndimage
from matplotlib.pyplot import plot

class PulseAnalysis():
    
    def __init__(self):
        self.is_counter_gated = False
        # std. deviation of the gaussian filter. 
        #Too small and the filtered data is too noisy to analyze; too big and the pulse edges are filtered out...
        self.conv_std_dev = 5
        # set windows for signal and normalization of the laser pulses
        self.signal_start_bin = 5
        self.signal_width_bins = 200
        self.norm_start_bin = 500
        self.norm_width_bins = 200
        # total number of laser pulses in the sequence
        self.number_of_lasers = 50
        # data arrays
        self.tau_vector = np.array(range(50))   # tau values (x-axis)
        self.signal_vector = np.zeros(self.number_of_lasers, dtype=float) # data points (y-axis)
        self.laser_data = None # extracted laser pulses


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

    
    def analyze_data(self, raw_data):
        """ This method captures the fast counter data and extracts the laser pulses.
          @param int num_of_lasers: The total number of laser pulses inside the pulse sequence
          @return 2D numpy.ndarray: The extracted laser pulses of the timetrace (dimensions 0: laser number, 1: time bin)
          @return 1D/2D numpy.ndarray: The raw timetrace from the fast counter
        """
        # call appropriate laser extraction method depending on if the fast counter is gated or not.
        if self.is_counter_gated:
            self.laser_data = self._gated_extraction(raw_data)
        else:
            self.laser_data = self._ungated_extraction(raw_data, self.number_of_lasers)
        
        #analyze data
        norm_mean = np.zeros(self.number_of_lasers, dtype=float)
        signal_mean = np.zeros(self.number_of_lasers, dtype=float)
        # set start and stop indices for the analysis
        norm_start = self.norm_start_bin
        norm_end = self.norm_start_bin + self.norm_width_bins
        signal_start = self.signal_start_bin
        signal_end = self.signal_start_bin + self.signal_width_bins
        # loop over all laser pulses and analyze them
        for i in range(self.number_of_lasers):
            # calculate the mean of the data in the normalization window
            norm_mean[i] = self.laser_data[i][norm_start:norm_end].mean()
            # calculate the mean of the data in the signal window
            signal_mean[i] = (self.laser_data[i][signal_start:signal_end] - norm_mean[i]).mean()
            # update the signal plot y-data
            self.signal_vector[i] = 1. + (signal_mean[i]/norm_mean[i])
        return

if __name__ == "__main__":  
    tool = PulseAnalysis()
    data = np.loadtxt('FastComTec_demo_timetrace.asc')
    tool.analyze_data(data)
    plot(tool.tau_vector, tool.signal_vector)