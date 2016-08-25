# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic for analysis of laser pulses.

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
import numpy as np

class PulseAnalysisLogic(GenericLogic):
    """unstable: Nikolas Tomek  """

    _modclass = 'PulseAnalysisLogic'
    _modtype = 'logic'

    # declare connectors
    _in = { 'pulseextractionlogic': 'PulseExtractionLogic',
            'fitlogic': 'FitLogic'
            }
    _out = {'pulseanalysislogic': 'PulseAnalysisLogic'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))


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
        self._pulse_extraction_logic = self.connector['in']['pulseextractionlogic']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        return


    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def set_old_raw_data(self, raw_data):
        """
        This method will set the old raw data inside the pulse extraction logic to be added to the
        new data set.
        @param raw_data: numpy ndarray, the raw count data from the fast counter. Must be same
                        dimension as the new data to be recorded.
        """
        self._pulse_extraction_logic.old_raw_data = raw_data
        return


    def _analyze_data(self, norm_start_bin, norm_end_bin, signal_start_bin,
                      signal_end_bin, num_of_lasers,conv_std_dev):

        """ Analysis the laser,pulses and computes the measuring error given by photon shot noise

        @param int norm_start_bin: Bin where the data for reference starts
        @param int norm_end_bin: Bin where the data for reference ends
        @param int signal_start_bin: Bin where the signal starts
        @param int signal_end_bin: Bin where the signal stops
        @param int number_of_lasers: Number of laser pulses
        @param int conv_std_dev: Standard deviation of gaussian convolution

        @return: float array signal_data: Array with the computed signal
        @return: float array laser_data: Array with the laser data
        @return: float array raw_data: Array with the raw data
        """

        # acquire data from the pulse extraction logic
        laser_data, raw_data = self._pulse_extraction_logic.get_data_laserpulses(num_of_lasers, conv_std_dev)

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

        # Compute the measuring error
        for jj in range(num_of_lasers):
            signal_area[jj] = laser_data[jj][signal_start_bin:signal_end_bin].sum()
            reference_area[jj] = laser_data[jj][norm_start_bin:norm_end_bin].sum()

            measuring_error[jj] = self.calculate_measuring_error(signal_area[jj], reference_area[jj],signal_data[jj])

        return signal_data, laser_data, raw_data, measuring_error



    def calculate_measuring_error(self, signal_area, reference_area, signal_data):
        """ Computes the measuring error given by photon shot noise.

        @param float signal_area: Numerical integral over the photon count in the signal area
        @param float reference_area: Numerical integral over the photon count in the reference area

        @return: float measuring_error: Computed error
        """
        if reference_area == 0.:
            measuring_error = 0.
        elif signal_area == 0.:
            measuring_error = 0.
        else:
            #with respect to gaußian error 'evolution'
            measuring_error=signal_data*np.sqrt(1/signal_area+1/reference_area)

        return measuring_error

#    def get_measurement_ticks_list(self):
#        """Get the list containing all tau values in ns for the current measurement.
#
#        @return numpy array: tau_vector_ns
#        """
#        return self._measurement_ticks_list
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


