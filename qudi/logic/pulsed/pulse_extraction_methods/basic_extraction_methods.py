# -*- coding: utf-8 -*-
"""
This file contains basic pulse extraction methods for Qudi.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
from scipy import ndimage

from logic.pulsed.pulse_extractor import PulseExtractorBase


class BasicPulseExtractor(PulseExtractorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def gated_conv_deriv(self, count_data, conv_std_dev=20.0, flank_width=0):
        """
        Detects the rising flank in the gated timetrace data and extracts just the laser pulses.
        The flank detection is based on an image edge detection technique performed in 1D.
        There is no information about the data needed.
        Only the gaussian filter width to reduce shot noise can be given as parameter.

        @param 2D numpy.ndarray count_data: the raw timetrace data from a gated fast counter
                                            dim 0: gate number; dim 1: time bin
        @param float conv_std_dev: The standard deviation of the gaussian filter used for smoothing
        @param int flank_width: The width of the flank in pixel to include/exclude additionally from the found position

        @return dict: The extracted laser pulses of the timetrace as well as the indices for rising
                      and falling flanks.
        """
        # Create return dictionary
        return_dict = {'laser_counts_arr': np.zeros(0, dtype='int64'),
                       'laser_indices_rising': -1,
                       'laser_indices_falling': -1}

        # sum up all gated timetraces to ease flank detection
        timetrace_sum = np.sum(count_data, 0)

        # apply gaussian filter to remove noise and compute the gradient of the timetrace sum
        try:
            conv = ndimage.filters.gaussian_filter1d(timetrace_sum.astype(float), conv_std_dev)
        except:
            conv = np.zeros(timetrace_sum.size)
        try:
            conv_deriv = np.gradient(conv)
        except:
            conv_deriv = np.zeros(conv.size)

        # get indices of rising and falling flank
        rising_ind, falling_ind = sorted([int(np.clip(conv_deriv.argmax() - flank_width, 0, len(timetrace_sum))),
                                          int(np.clip(conv_deriv.argmin() + flank_width, 0, len(timetrace_sum)))
                                          ])

        # If gaussian smoothing or derivative failed, the returned array only contains zeros.
        # Check for that and return also only zeros to indicate a failed pulse extraction.
        if len(conv_deriv.nonzero()[0]) == 0:
            laser_arr = np.zeros(count_data.shape, dtype='int64')
        else:
            # slice the data array to cut off anything but laser pulses
            laser_arr = count_data[:, rising_ind:falling_ind]

        return_dict['laser_counts_arr'] = laser_arr.astype('int64')
        return_dict['laser_indices_rising'] = rising_ind
        return_dict['laser_indices_falling'] = falling_ind

        return return_dict

    def ungated_conv_deriv(self, count_data, conv_std_dev=20.0):
        """ Detects the laser pulses in the ungated timetrace data and extracts
            them.

        @param numpy.ndarray count_data: The raw timetrace data (1D) from an ungated fast counter
        @param float conv_std_dev: The standard deviation of the gaussian used for smoothing

        @return 2D numpy.ndarray:   2D array, the extracted laser pulses of the timetrace.
                                    dimensions: 0: laser number, 1: time bin

        Procedure:
            Edge Detection:
            ---------------

            The count_data array with the laser pulses is smoothed with a
            gaussian filter (convolution), which used a defined standard
            deviation of 10 entries (bins). Then the derivation of the convolved
            time trace is taken to obtain the maxima and minima, which
            corresponds to the rising and falling edge of the pulses.

            The convolution with a gaussian removes nasty peaks due to count
            fluctuation within a laser pulse and at the same time ensures a
            clear distinction of the maxima and minima in the derived convolved
            trace.

            The maxima and minima are not found sequentially, pulse by pulse,
            but are rather globally obtained. I.e. the convolved and derived
            array is searched iteratively for a maximum and a minimum, and after
            finding those the array entries within the 4 times
            self.conv_std_dev (2*self.conv_std_dev to the left and
            2*self.conv_std_dev) are set to zero.

            The crucial part is the knowledge of the number of laser pulses and
            the choice of the appropriate std_dev for the gauss filter.

            To ensure a good performance of the edge detection, you have to
            ensure a steep rising and falling edge of the laser pulse! Be also
            careful in choosing a large conv_std_dev value and using a small
            laser pulse (rule of thumb: conv_std_dev < laser_length/10).
        """
        # Create return dictionary
        return_dict = {'laser_counts_arr': np.empty(0, dtype='int64'),
                       'laser_indices_rising': np.empty(0, dtype='int64'),
                       'laser_indices_falling': np.empty(0, dtype='int64')}

        number_of_lasers = self.measurement_settings.get('number_of_lasers')
        if not isinstance(number_of_lasers, int):
            return return_dict

        # apply gaussian filter to remove noise and compute the gradient of the timetrace sum
        try:
            conv = ndimage.filters.gaussian_filter1d(count_data.astype(float), conv_std_dev)
        except:
            conv = np.zeros(count_data.size)
        try:
            conv_deriv = np.gradient(conv)
        except:
            conv_deriv = np.zeros(conv.size)

        # if gaussian smoothing or derivative failed, the returned array only contains zeros.
        # Check for that and return also only zeros to indicate a failed pulse extraction.
        if len(conv_deriv.nonzero()[0]) == 0:
            return_dict['laser_counts_arr'] = np.zeros((number_of_lasers, 10), dtype='int64')
            return return_dict

        # use a reference for array, because the exact position of the peaks or dips
        # (i.e. maxima or minima, which are the inflection points in the pulse) are distorted by
        # a large conv_std_dev value.
        try:
            conv = ndimage.filters.gaussian_filter1d(count_data.astype(float), 10)
        except:
            conv = np.zeros(count_data.size)
        try:
            conv_deriv_ref = np.gradient(conv)
        except:
            conv_deriv_ref = np.zeros(conv.size)

        # initialize arrays to contain indices for all rising and falling
        # flanks, respectively
        rising_ind = np.empty(number_of_lasers, dtype='int64')
        falling_ind = np.empty(number_of_lasers, dtype='int64')

        # Find as many rising and falling flanks as there are laser pulses in
        # the trace:
        for i in range(number_of_lasers):
            # save the index of the absolute maximum of the derived time trace
            # as rising edge position
            rising_ind[i] = np.argmax(conv_deriv)

            # refine the rising edge detection, by using a small and fixed
            # conv_std_dev parameter to find the inflection point more precise
            start_ind = int(rising_ind[i] - conv_std_dev)
            if start_ind < 0:
                start_ind = 0

            stop_ind = int(rising_ind[i] + conv_std_dev)
            if stop_ind > len(conv_deriv):
                stop_ind = len(conv_deriv)

            if start_ind == stop_ind:
                stop_ind = start_ind + 1

            rising_ind[i] = start_ind + np.argmax(conv_deriv_ref[start_ind:stop_ind])

            # set this position and the surrounding of the saved edge to 0 to
            # avoid a second detection
            if rising_ind[i] < 2 * conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = rising_ind[i] - int(2 * conv_std_dev)
            if (conv_deriv.size - rising_ind[i]) < 2 * conv_std_dev:
                del_ind_stop = conv_deriv.size - 1
            else:
                del_ind_stop = rising_ind[i] + int(2 * conv_std_dev)
                conv_deriv[del_ind_start:del_ind_stop] = 0

            # save the index of the absolute minimum of the derived time trace
            # as falling edge position
            falling_ind[i] = np.argmin(conv_deriv)

            # refine the falling edge detection, by using a small and fixed
            # conv_std_dev parameter to find the inflection point more precise
            start_ind = int(falling_ind[i] - conv_std_dev)
            if start_ind < 0:
                start_ind = 0

            stop_ind = int(falling_ind[i] + conv_std_dev)
            if stop_ind > len(conv_deriv):
                stop_ind = len(conv_deriv)

            if start_ind == stop_ind:
                stop_ind = start_ind + 1

            falling_ind[i] = start_ind + np.argmin(conv_deriv_ref[start_ind:stop_ind])

            # set this position and the sourrounding of the saved flank to 0 to
            #  avoid a second detection
            if falling_ind[i] < 2 * conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = falling_ind[i] - int(2 * conv_std_dev)
            if (conv_deriv.size - falling_ind[i]) < 2 * conv_std_dev:
                del_ind_stop = conv_deriv.size - 1
            else:
                del_ind_stop = falling_ind[i] + int(2 * conv_std_dev)
            conv_deriv[del_ind_start:del_ind_stop] = 0

        # sort all indices of rising and falling flanks
        rising_ind.sort()
        falling_ind.sort()

        # find the maximum laser length to use as size for the laser array
        laser_length = np.max(falling_ind - rising_ind)

        # initialize the empty output array
        laser_arr = np.zeros((number_of_lasers, laser_length), dtype='int64')
        # slice the detected laser pulses of the timetrace and save them in the
        # output array according to the found rising edge
        for i in range(number_of_lasers):
            if rising_ind[i] + laser_length > count_data.size:
                lenarr = count_data[rising_ind[i]:].size
                laser_arr[i, 0:lenarr] = count_data[rising_ind[i]:]
            else:
                laser_arr[i] = count_data[rising_ind[i]:rising_ind[i] + laser_length]

        return_dict['laser_counts_arr'] = laser_arr.astype('int64')
        return_dict['laser_indices_rising'] = rising_ind
        return_dict['laser_indices_falling'] = falling_ind
        return return_dict

    def ungated_threshold(self, count_data, count_threshold=10, min_laser_length=200e-9,
                          threshold_tolerance=20e-9):
        """
        Detects the laser pulses in the ungated timetrace data and extracts them.
    
        @param numpy.ndarray count_data: The raw timetrace data (1D) from an ungated fast counter
        @param count_threshold: 
        @param min_laser_length: 
        @param threshold_tolerance: 
        
        @return 2D numpy.ndarray:   2D array, the extracted laser pulses of the timetrace.
                                    dimensions: 0: laser number, 1: time bin
    
        Procedure:
            Threshold detection:
            ---------------
    
            All count data from the time trace is compared to a threshold value.
            Values above the threshold are considered to belong to a laser pulse.
            If the length of a pulse would be below the minimum length the pulse is discarded.
            If a number of bins which are below the threshold is smaller than the number of bins 
            making the threshold_tolerance then they are still considered to belong to a laser 
            pulse.
        """
        return_dict = dict()

        number_of_lasers = self.measurement_settings.get('number_of_lasers')
        counter_bin_width = self.fast_counter_settings.get('bin_width')

        if not isinstance(number_of_lasers, int):
            return_dict['laser_indices_rising'] = np.zeros(1, dtype='int64')
            return_dict['laser_indices_falling'] = np.zeros(1, dtype='int64')
            return_dict['laser_counts_arr'] = np.zeros((1, 3000), dtype='int64')
            return return_dict
        else:
            return_dict['laser_indices_rising'] = np.zeros(number_of_lasers, dtype='int64')
            return_dict['laser_indices_falling'] = np.zeros(number_of_lasers, dtype='int64')
            return_dict['laser_counts_arr'] = np.zeros((number_of_lasers, 3000), dtype='int64')

        # Convert length in seconds into length in time bins
        threshold_tolerance = round(threshold_tolerance / counter_bin_width)
        min_laser_length = round(min_laser_length / counter_bin_width)

        # get all bin indices with counts > threshold value
        bigger_indices = np.where(count_data >= count_threshold)[0]

        # get all indices with consecutive numbering (bin chains not interrupted by
        # values < threshold
        index_list = np.split(bigger_indices,
                              np.where(np.diff(bigger_indices) >= threshold_tolerance)[0] + 1)
        for i, index_group in enumerate(index_list):
            if index_group.size > 0:
                start, end = index_list[i][0], index_list[i][-1]
                index_list[i] = np.arange(start, end + 1)
        consecutive_indices_unfiltered = index_list

        # sort out all groups shorter than minimum laser length
        consecutive_indices = [item for item in consecutive_indices_unfiltered if
                               len(item) > min_laser_length]

        # Check if the number of lasers matches the number of remaining index groups
        if number_of_lasers != len(consecutive_indices):
            return return_dict

        # determine max length of laser pulse and initialize laser array
        max_laser_length = max([index_array.size for index_array in consecutive_indices])
        return_dict['laser_counts_arr'] = np.zeros((number_of_lasers, max_laser_length),
                                                   dtype='int64')

        # fill laser array with slices of raw data array. Also populate the rising/falling index
        # arrays
        for i, index_group in enumerate(consecutive_indices):
            return_dict['laser_indices_rising'][i] = index_group[0]
            return_dict['laser_indices_falling'][i] = index_group[-1]
            return_dict['laser_counts_arr'][i, :index_group.size] = count_data[index_group]

        return return_dict

    def ungated_gated_conv_deriv(self, count_data, conv_std_dev=20.0, delay=5e-7, safety=2e-7):
        """
        Extracts the laser pulses in the ungated timetrace data using laser_start_indices and
        laser_length.
        Procedure:
            Finds the laser pulses from the ungated timetrace using that their positions are
            known. The laser pulses are then extracted using gated_conv_deriv.

        @param numpy.ndarray count_data: 1D array the raw timetrace data from an ungated fast
                                         counter
        @param float conv_std_dev: The standard deviation of the gaussian filter used for smoothing
        @param float delay:
        @param float safety:

        @return 2D numpy.ndarray: 2D array, the extracted laser pulses of the timetrace.
                                  dimensions: 0: laser number, 1: time bin
        """
        # get the generation sampling rate
        sample_rate = self.sampling_information['pulse_generator_settings']['sample_rate']
        # get the fastcounter binwidth
        fc_binwidth = self.fast_counter_settings['bin_width']
        # get laser rising and falling bins
        laser_rising_bins = self.sampling_information['laser_rising_bins']
        laser_falling_bins = self.sampling_information['laser_falling_bins']

        # Sort out trailing or leading incomplete laser pulse
        while len(laser_rising_bins) != len(laser_falling_bins):
            if len(laser_rising_bins) > len(laser_falling_bins):
                if laser_rising_bins[-1] >= laser_falling_bins[-1]:
                    laser_rising_bins = laser_rising_bins[:-1]
                else:
                    laser_rising_bins = laser_rising_bins[1:]
            else:
                if laser_rising_bins[0] >= laser_falling_bins[0]:
                    laser_falling_bins = laser_falling_bins[1:]
                else:
                    laser_falling_bins = laser_falling_bins[:-1]

        # convert to bins of fastcounter
        laser_rising_bins = np.rint(laser_rising_bins / sample_rate / fc_binwidth).astype('int64')
        laser_falling_bins = np.rint(laser_falling_bins / sample_rate / fc_binwidth).astype('int64')
        # convert to fastcounter bins
        safety_bins = round(safety / fc_binwidth)
        delay_bins = round(delay / fc_binwidth)
        # dimensions of laser pulse array
        num_rows = len(laser_rising_bins)
        max_laser_length = max(laser_falling_bins - laser_rising_bins)
        num_col = max_laser_length + 2 * safety_bins
        # compute from laser_start_indices and laser length the respective position of the laser
        # pulses
        laser_pulses = np.empty((num_rows, num_col))
        for ii in range(num_rows):
            laser_pulses[ii][:] = count_data[
                np.arange(laser_rising_bins[ii] + delay_bins - safety_bins,
                          laser_rising_bins[ii] + delay_bins + safety_bins + max_laser_length)]
        # use the gated extraction method
        return_dict = self.gated_conv_deriv(laser_pulses, conv_std_dev)
        return return_dict

    def ungated_pass_through(self, count_data):
        """
        This method does not actually extract anything. It takes the 1D array from the hardware and reshapes it
        into a 2D array, where the length of the second dimension is 1. The data itself is handed through.
        This function is useful, if the extraction and analysis are performed in hardware.

        @param numpy.ndarray count_data: 1D array the raw timetrace data from an ungated fast
                                         counter

        @return dict: The extracted laser pulses of the timetrace as well as the indices for rising
                      and falling flanks.
        """
        # Create return dictionary
        return_dict = {'laser_counts_arr': np.reshape(count_data, (-1, 1)),
                       'laser_indices_rising': np.arange(len(count_data)),
                       'laser_indices_falling': np.arange(len(count_data))}

        return return_dict

    def gated_pass_through(self, count_data):
        """
        This method does not actually extract anything. It just passes through the data from the hardware.
        This function is useful, if the extraction is performed in hardware.

        @param 2D numpy.ndarray count_data: the raw timetrace data from a gated fast counter
                                            dim 0: gate number; dim 1: time bin

        @return dict: The extracted laser pulses of the timetrace as well as the indices for rising
                      and falling flanks.
        """
        # Create return dictionary
        return_dict = {'laser_counts_arr': np.array(count_data),
                       'laser_indices_rising': np.arange(len(count_data)),
                       'laser_indices_falling': np.arange(len(count_data))}

        return return_dict