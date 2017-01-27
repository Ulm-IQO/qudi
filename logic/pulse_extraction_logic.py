# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic for the extraction of laser pulses.

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
from logic.generic_logic import GenericLogic


class PulseExtractionLogic(GenericLogic):
    """unstable: Nikolas Tomek  """

    _modclass = 'PulseExtractionLogic'
    _modtype = 'logic'

    # declare connectors
    _out = {'pulseextractionlogic': 'PulseExtractionLogic'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        self.extraction_method = None

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        # FIXME: Implement alternative extraction methods
        self.extraction_method = None   # will later on be used to switch between different methods
        return

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def gated_extraction(self, count_data, conv_std_dev):
        """ Detects the rising flank in the gated timetrace data and extracts
            just the laser pulses.

        @param numpy.ndarray count_data: 2D array, the raw timetrace data from a
                                         gated fast counter, dimensions:
                                            0: gate number,
                                            1: time bin)
        @param float conv_std_dev: standard deviation of the gaussian filter to be
                              applied for smoothing

        @return numpy.ndarray: The extracted laser pulses of the timetrace
                               dimensions:
                                    0: laser number,
                                    1: time bin
        """
        # sum up all gated timetraces to ease flank detection
        timetrace_sum = np.sum(count_data, 0)

        # apply gaussian filter to remove noise and compute the gradient of the timetrace sum
        conv_deriv = self._convolve_derive(timetrace_sum.astype(float), conv_std_dev)

        # if gaussian smoothing or derivative failed, the returned array only contains zeros.
        # Check for that and return also only zeros to indicate a failed pulse extraction.
        if len(conv_deriv.nonzero()[0]) == 0:
            laser_arr = np.zeros(count_data.shape, dtype=int)
            return laser_arr

        # get indices of rising and falling flank
        rising_ind = conv_deriv.argmax()
        falling_ind = conv_deriv.argmin()
        # slice the data array to cut off anything but laser pulses
        laser_arr = count_data[:, rising_ind:falling_ind]
        return laser_arr.astype(int)

    def ungated_extraction(self, count_data, conv_std_dev, num_of_lasers):
        """ Detects the laser pulses in the ungated timetrace data and extracts
            them.

        @param numpy.ndarray count_data: 1D array the raw timetrace data from an
                                         ungated fast counter
        @param int num_of_lasers: The total number of laser pulses inside the
                                  pulse sequence
        @param float conv_std_dev: standard deviation of the gaussian filter to be
                              applied for smoothing

        @return 2D numpy.ndarray: 2D array, the extracted laser pulses of the
                                  timetrace, dimensions:
                                        0: laser number,
                                        1: time bin

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

        # apply gaussian filter to remove noise and compute the gradient of the timetrace
        conv_deriv = self._convolve_derive(count_data.astype(float), conv_std_dev)

        # if gaussian smoothing or derivative failed, the returned array only contains zeros.
        # Check for that and return also only zeros to indicate a failed pulse extraction.
        if len(conv_deriv.nonzero()[0]) == 0:
            laser_arr = np.zeros([num_of_lasers, 10], dtype=int)
            return laser_arr

        # use a reference for array, because the exact position of the peaks or dips
        # (i.e. maxima or minima, which are the inflection points in the pulse) are distorted by
        # a large conv_std_dev value.
        conv_deriv_ref = self._convolve_derive(count_data, 10)

        # initialize arrays to contain indices for all rising and falling
        # flanks, respectively
        rising_ind = np.empty([num_of_lasers], int)
        falling_ind = np.empty([num_of_lasers], int)

        # Find as many rising and falling flanks as there are laser pulses in
        # the trace:
        for i in range(num_of_lasers):
            # save the index of the absolute maximum of the derived time trace
            # as rising edge position
            rising_ind[i] = np.argmax(conv_deriv)

            # refine the rising edge detection, by using a small and fixed
            # conv_std_dev parameter to find the inflection point more precise
            start_ind = int(rising_ind[i]-conv_std_dev)
            if start_ind < 0:
                start_ind = 0

            stop_ind = int(rising_ind[i]+conv_std_dev)
            if stop_ind > len(conv_deriv):
                stop_ind = len(conv_deriv)

            if start_ind == stop_ind:
                stop_ind = start_ind+1

            rising_ind[i] = start_ind + np.argmax(conv_deriv_ref[start_ind:stop_ind])

            # set this position and the surrounding of the saved edge to 0 to
            # avoid a second detection
            if rising_ind[i] < 2*conv_std_dev:                del_ind_start = 0
            else:
                del_ind_start = rising_ind[i] - 2*conv_std_dev
            if (conv_deriv.size - rising_ind[i]) < 2*conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = rising_ind[i] + 2*conv_std_dev
                conv_deriv[del_ind_start:del_ind_stop] = 0

            # save the index of the absolute minimum of the derived time trace
            # as falling edge position
            falling_ind[i] = np.argmin(conv_deriv)

            # refine the falling edge detection, by using a small and fixed
            # conv_std_dev parameter to find the inflection point more precise
            start_ind = int(falling_ind[i]-conv_std_dev)
            if start_ind < 0:
                start_ind = 0

            stop_ind = int(falling_ind[i]+conv_std_dev)
            if stop_ind > len(conv_deriv):
                stop_ind = len(conv_deriv)

            if start_ind == stop_ind:
                stop_ind = start_ind+1

            falling_ind[i] = start_ind + np.argmin(conv_deriv_ref[start_ind:stop_ind])

            # set this position and the sourrounding of the saved flank to 0 to
            #  avoid a second detection
            if falling_ind[i] < 2*conv_std_dev:                del_ind_start = 0
            else:
                del_ind_start = falling_ind[i] - 2*conv_std_dev
            if (conv_deriv.size - falling_ind[i]) < 2*conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = falling_ind[i] + 2*conv_std_dev
            conv_deriv[del_ind_start:del_ind_stop] = 0

        # sort all indices of rising and falling flanks
        rising_ind.sort()
        falling_ind.sort()

        # find the maximum laser length to use as size for the laser array
        laser_length = np.max(falling_ind-rising_ind)

        #Todo: Find better method, here the idea is to take a histogram to find
        # length of pulses
        #diff = (falling_ind-rising_ind)[np.where( falling_ind-rising_ind > 0)]
        #self.histo = np.histogram(diff)
        #laser_length = int(self.histo[1][self.histo[0].argmax()])

        # initialize the empty output array
        laser_arr = np.zeros([num_of_lasers, laser_length], dtype=int)
        # slice the detected laser pulses of the timetrace and save them in the
        # output array according to the found rising edge
        for i in range(num_of_lasers):
            if (rising_ind[i]+laser_length > count_data.size):
                lenarr = count_data[rising_ind[i]:].size
                laser_arr[i, 0:lenarr] = count_data[rising_ind[i]:]
            else:
                laser_arr[i] = count_data[rising_ind[i]:rising_ind[i]+laser_length]
        return laser_arr.astype(int)

    def _convolve_derive(self, data, std_dev):
        """ Smooth the input data by applying a gaussian filter.

        @param numpy.ndarray data: 1D array, the raw data to be smoothed
                                        and derived
        @param float std_dev: standard deviation of the gaussian filter to be
                              applied for smoothing

        @return numpy.ndarray: 1D array, the smoothed and derived data

        The convolution is applied with specified standard deviation. The
        derivative of the smoothed data is computed afterwards and returned. If
        the input data is some kind of rectangular signal containing high
        frequency noise, the output data will show sharp peaks corresponding to
        the rising and falling flanks of the input signal.
        """
        try:
            conv = ndimage.filters.gaussian_filter1d(data, std_dev)
        except:
            self.log.debug('Convolution of fast counter timetrace failed.\n'
                           'Probably NaN encountered in data array.')
            conv = np.zeros(data.size)
        try:
            conv_deriv = np.gradient(conv)
        except:
            self.log.debug('Derivative of convolution of fast counter timetrace failed.\n'
                           'Probably NaN encountered in data array.')
            conv_deriv = np.zeros(conv.size)
        return conv_deriv


    def extract_laser_pulses(self,data,count_treshold,min_len_laser,
                           exception):

        """ Detects the laser pulses in the ungated timetrace data and extracts
            them.

        @param numpy.ndarray data: 1D array the raw timetrace data from an
                                         ungated fast counter
        @param int count_treshold: The treshold to seperate between laser and noise
        @param int min_len_laser:  Minimum length of laser pulse
        @param int exception:      how many bin may be under treshold but still count
                                   for the laser


        @return 2D numpy.ndarray: 2D array, the extracted laser pulses of the
                                  timetrace, dimensions:
                                        0: laser number,
                                        1: time bin

        @return 2D numpy.ndarray: 2D array, the extracted laser pulses of the
                                  timetrace, dimensions:
                                        0: laser number,
                                        1: counts time bin

        Procedure:
            Treshold detection:
            ---------------

            All count data from the time trace is compared to a trehold value.
            Values above the trehold are considered to belong to a laser pulse.
            If the length of a pulse would be below the minium length the pulse is discarded
        """

        # initialize
        x_data = []
        y_data = []
        laser_x = []
        laser_y = []
        excep=0

        for ii in range(len(data)):

                if data[ii] >= count_treshold:

                    x_data.append(ii)
                    y_data.append(data[ii])

                else:
                    if excep < exception:
                        x_data.append(ii)
                        y_data.append(data[ii])
                        excep=excep+1

                    elif len(x_data)>min_len_laser:
                        laser_x.append(np.array(x_data))
                        laser_y.append(np.array(y_data))
                        x_data=[]
                        y_data=[]
                        excep=0
                    else:
                        x_data=[]
                        y_data=[]
                        excep=0

        # find the longest laser pulse
        length=np.zeros(len(laser_y))
        for jj in range(len(laser_y)):
            length[jj]=len(laser_y[jj])
        longest = np.max(length)

        #symmetrize all pulses so that they have the same length
        for jj in range(len(laser_y)):
            while len(laser_y[jj])<longest:
                laser_x[jj]=np.append(laser_x[jj],laser_x[jj][-1]+1)
                laser_y[jj]=np.append(laser_y[jj],laser_y[jj][-1])

        #FIXME: It should be possible to return laser_x aswell but therefor
        #FIXME: the functions above also would have to be changed

        laser_arr=np.asarray(laser_y)

        return laser_arr.astype(int)

    def excise_laser_pulses(self,count_data,num_lasers,laser_length,initial_offset,initial_length,increment):


        laser_x = []
        laser_y = []

        x_data = np.linspace(initial_offset,initial_offset+laser_length,laser_length+1)
        y_data = count_data[initial_offset:initial_offset+laser_length]
        laser_x.append(x_data)
        laser_y.append(y_data)

        time = initial_length + initial_offset

        for laser in range(int(num_lasers)-1):

            x_data = np.linspace(time,time+laser_length,laser_length+1)
            y_data = count_data[time:(time+laser_length)]
            laser_x.append(np.array(x_data))
            laser_y.append(np.array(y_data))


            time = time + initial_length + (laser+1)*increment




        laser_arr=np.asarray(laser_y)

        self.log.debug(laser_y)

        return laser_arr.astype(int)

