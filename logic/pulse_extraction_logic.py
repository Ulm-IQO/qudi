# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic for the extraction of laser pulses.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
from scipy import ndimage
from core.util.network import netobtain

class PulseExtractionLogic(GenericLogic):
    """unstable: Nikolas Tomek  """

    _modclass = 'PulseExtractionLogic'
    _modtype = 'logic'

    # declare connectors
    _in = {'fastcounter': 'FastCounterInterface'}
    _out = {'pulseextractionlogic': 'PulseExtractionLogic'}

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}

        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

        self.is_counter_gated = False
        self.conv_std_dev = 5
        self.old_raw_data = None    # This is used to pause and continue a measurement.
                                    # Is added to the new data.


    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._check_if_counter_gated()

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def _gated_extraction(self, count_data):
        """ Detects the rising flank in the gated timetrace data and extracts
            just the laser pulses.

        @param numpy.ndarray count_data: 2D array, the raw timetrace data from a
                                         gated fast counter, dimensions:
                                            0: gate number,
                                            1: time bin)

        @return numpy.ndarray: The extracted laser pulses of the timetrace
                               dimensions:
                                    0: laser number,
                                    1: time bin
        """
        # sum up all gated timetraces to ease flank detection
        timetrace_sum = np.sum(count_data, 0)

        # apply gaussian filter to remove noise and compute the gradient of the
        # timetrace sum
        #FIXME: That option should be stated in the config, or should be
        #       choosable by the GUI, since it is not always desired.
        #       It should also be possible to display the bare laserpulse,
        #       without cutting away something.

        conv_deriv = self._convolve_derive(timetrace_sum, self.conv_std_dev)
        # get indices of rising and falling flank

        rising_ind = conv_deriv.argmax()
        falling_ind = conv_deriv.argmin()
        # slice the data array to cut off anything but laser pulses
        laser_arr = count_data[:, rising_ind:falling_ind]
        return laser_arr


    def _ungated_extraction(self, count_data, num_of_lasers):
        """ Detects the laser pulses in the ungated timetrace data and extracts
            them.

        @param numpy.ndarray count_data: 1D array the raw timetrace data from an
                                         ungated fast counter
        @param int num_of_lasers: The total number of laser pulses inside the
                                  pulse sequence

        @return 2D numpy.ndarray: 2D array, the extracted laser pulses of the
                                  timetrace, dimensions:
                                        0: laser number,
                                        1: time bin
        """
        # apply gaussian filter to remove noise and compute the gradient of the
        # timetrace
        conv_deriv = self._convolve_derive(count_data, self.conv_std_dev)
        # initialize arrays to contain indices for all rising and falling
        # flanks, respectively
        rising_ind = np.empty([num_of_lasers],int)
        falling_ind = np.empty([num_of_lasers],int)
        # Find as many rising and falling flanks as there are laser pulses in
        # the timetrace
        for i in range(num_of_lasers):
            # save the index of the absolute maximum of the derived timetrace as
            #  rising flank position
            rising_ind[i] = np.argmax(conv_deriv)
            # set this position and the sourrounding of the saved flank to 0 to
            # avoid a second detection
            if rising_ind[i] < 2*self.conv_std_dev:
                del_ind_start = 0
            else:
                del_ind_start = rising_ind[i] - 2*self.conv_std_dev
            if (conv_deriv.size - rising_ind[i]) < 2*self.conv_std_dev:
                del_ind_stop = conv_deriv.size-1
            else:
                del_ind_stop = rising_ind[i] + 2*self.conv_std_dev
            conv_deriv[del_ind_start:del_ind_stop] = 0

            # save the index of the absolute minimum of the derived timetrace
            # as falling flank position
            falling_ind[i] = np.argmin(conv_deriv)
            # set this position and the sourrounding of the saved flank to 0 to
            #  avoid a second detection
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
        # slice the detected laser pulses of the timetrace and save them in the
        #  output array
        for i in range(num_of_lasers):
            if (rising_ind[i]+laser_length > count_data.size):
                lenarr = count_data[rising_ind[i]:].size
                laser_arr[i, 0:lenarr] = count_data[rising_ind[i]:]
            else:
                laser_arr[i] = count_data[rising_ind[i]:rising_ind[i]+laser_length]
        return laser_arr


    def _convolve_derive(self, data, std_dev):
        """ Smooth the input data by applying a gaussian filter.

        @param numpy.ndarray timetrace: 1D array, the raw data to be smoothed
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

        conv = ndimage.filters.gaussian_filter1d(data, std_dev)
        conv_deriv = np.gradient(conv)
        return conv_deriv


    def get_data_laserpulses(self, num_of_lasers):
        """ Capture the fast counter data and extracts the laser pulses.

        @param int num_of_lasers: The total number of laser pulses inside the
                                  pulse sequence
        @return tuple (numpy.ndarray, numpy.ndarray):
                    Explanation of the return value:

                    numpy.ndarray: 2D array, the extracted laser pulses of the
                                   timetrace, with the dimensions:
                                        0: laser number
                                        1: time bin
                    numpy.ndarray: 1D or 2D, the raw timetrace from the fast
                                   counter
        """
        # poll data from the fast counting device, netobtain is needed for
        # getting numpy array over network
        raw_data = netobtain(self._fast_counter_device.get_data_trace())
        if self.old_raw_data is not None:
            #if raw_data.shape == self.old_raw_data.shape:
            raw_data = np.add(raw_data, self.old_raw_data)

        # call appropriate laser extraction method depending on if the fast
        # counter is gated or not.
        if self.is_counter_gated:
            laser_data = self._gated_extraction(raw_data)
        else:
            laser_data = self._ungated_extraction(raw_data, num_of_lasers)
        return laser_data.astype(dtype=int), raw_data.astype(dtype=int)


    def _check_if_counter_gated(self):
        '''Check the fast counter if it is gated or not
        '''
        self.is_counter_gated = self._fast_counter_device.is_gated()
        return
