# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic for analysis of laser pulses.

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
from logic.generic_logic import GenericLogic


class PulseAnalysisLogic(GenericLogic):
    """unstable: Nikolas Tomek  """

    _modclass = 'PulseAnalysisLogic'
    _modtype = 'logic'

    # declare connectors
    _out = {'pulseanalysislogic': 'PulseAnalysisLogic'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

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
        pass

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def analyze_data(self, laser_data, norm_start_bin, norm_end_bin, signal_start_bin,
                     signal_end_bin):
        """ Analysis the laser pulses and computes the measuring error given by photon shot noise

        @param numpy.ndarray (int) laser_data: 2D array containing the extracted laser countdata
        @param int norm_start_bin: Bin where the data for reference starts
        @param int norm_end_bin: Bin where the data for reference ends
        @param int signal_start_bin: Bin where the signal starts
        @param int signal_end_bin: Bin where the signal stops

        @return: float array signal_data: Array with the computed signal
        @return: float array laser_data: Array with the laser data
        @return: float array raw_data: Array with the raw data
        """
        num_of_lasers = laser_data.shape[0]

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
            norm_tmp_data = laser_data[ii][norm_start_bin:norm_end_bin]
            if np.sum(norm_tmp_data) < 1:
                reference_mean[ii] = 0.0
            else:
                reference_mean[ii] = norm_tmp_data.mean()
            # calculate the mean of the data in the signal window
            signal_tmp_data = laser_data[ii][signal_start_bin:signal_end_bin]
            if np.sum(signal_tmp_data) < 1:
                signal_mean[ii] = 0.0
            else:
                signal_mean[ii] = signal_tmp_data.mean() - reference_mean[ii]
            # update the signal plot y-data
            if reference_mean[ii] == 0.0:
                signal_data[ii] = 0.0
            else:
                signal_data[ii] = 1. + (signal_mean[ii]/reference_mean[ii])


        # Compute the measuring error
        for jj in range(num_of_lasers):
            signal_area[jj] = laser_data[jj][signal_start_bin:signal_end_bin].sum()
            reference_area[jj] = laser_data[jj][norm_start_bin:norm_end_bin].sum()

            measuring_error[jj] = self.calculate_measuring_error(signal_area[jj],
                                                                 reference_area[jj],
                                                                 signal_data[jj])
        return signal_data, measuring_error

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
            # with respect to gaußian error 'evolution'
            measuring_error = signal_data * np.sqrt(1 / signal_area + 1 / reference_area)
        return measuring_error
