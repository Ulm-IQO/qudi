# -*- coding: utf-8 -*-
"""
This file contains basic pulse analysis methods for Qudi.

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

from logic.pulsed.pulse_analyzer import PulseAnalyzerBase


class BasicPulseAnalyzer(PulseAnalyzerBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def analyse_mean_norm(self, laser_data, signal_start=0.0, signal_end=200e-9, norm_start=300e-9,
                          norm_end=500e-9):
        """

        @param laser_data:
        @param signal_start:
        @param signal_end:
        @param norm_start:
        @param norm_end:
        @return:
        """
        # Get number of lasers
        num_of_lasers = laser_data.shape[0]
        # Get counter bin width
        bin_width = self.fast_counter_settings.get('bin_width')

        if not isinstance(bin_width, float):
            return np.zeros(num_of_lasers), np.zeros(num_of_lasers)

        # Convert the times in seconds to bins (i.e. array indices)
        signal_start_bin = round(signal_start / bin_width)
        signal_end_bin = round(signal_end / bin_width)
        norm_start_bin = round(norm_start / bin_width)
        norm_end_bin = round(norm_end / bin_width)

        # initialize data arrays for signal and measurement error
        signal_data = np.empty(num_of_lasers, dtype=float)
        error_data = np.empty(num_of_lasers, dtype=float)

        # loop over all laser pulses and analyze them
        for ii, laser_arr in enumerate(laser_data):
            # calculate the sum and mean of the data in the normalization window
            tmp_data = laser_arr[norm_start_bin:norm_end_bin]
            reference_sum = np.sum(tmp_data)
            reference_mean = (reference_sum / len(tmp_data)) if len(tmp_data) != 0 else 0.0

            # calculate the sum and mean of the data in the signal window
            tmp_data = laser_arr[signal_start_bin:signal_end_bin]
            signal_sum = np.sum(tmp_data)
            signal_mean = (signal_sum / len(tmp_data)) if len(tmp_data) != 0 else 0.0

            # Calculate normalized signal while avoiding division by zero
            if reference_mean > 0 and signal_mean >= 0:
                signal_data[ii] = signal_mean / reference_mean
            else:
                signal_data[ii] = 0.0

            # Calculate measurement error while avoiding division by zero
            if reference_sum > 0 and signal_sum > 0:
                # calculate with respect to gaussian error 'evolution'
                error_data[ii] = signal_data[ii] * np.sqrt(1 / signal_sum + 1 / reference_sum)
            else:
                error_data[ii] = 0.0

        return signal_data, error_data

    def analyse_sum(self, laser_data, signal_start=0.0, signal_end=200e-9):
        """
        @param laser_data:
        @param signal_start:
        @param signal_end:
        @return:
        """
        # Get number of lasers
        num_of_lasers = laser_data.shape[0]
        # Get counter bin width
        bin_width = self.fast_counter_settings.get('bin_width')

        if not isinstance(bin_width, float):
            return np.zeros(num_of_lasers), np.zeros(num_of_lasers)

        # Convert the times in seconds to bins (i.e. array indices)
        signal_start_bin = round(signal_start / bin_width)
        signal_end_bin = round(signal_end / bin_width)

        # initialize data arrays for signal and measurement error
        signal_data = np.empty(num_of_lasers, dtype=float)
        error_data = np.empty(num_of_lasers, dtype=float)

        # loop over all laser pulses and analyze them
        for ii, laser_arr in enumerate(laser_data):
            # calculate the sum of the data in the signal window
            signal = laser_arr[signal_start_bin:signal_end_bin].sum()
            signal_error = np.sqrt(signal)

            # Avoid numpy C type variables overflow and NaN values
            if signal < 0 or signal != signal:
                signal_data[ii] = 0.0
                error_data[ii] = 0.0
            else:
                signal_data[ii] = signal
                error_data[ii] = signal_error

        return signal_data, error_data

    def analyse_mean(self, laser_data, signal_start=0.0, signal_end=200e-9):
        """

        @param laser_data:
        @param signal_start:
        @param signal_end:
        @return:
        """
        # Get number of lasers
        num_of_lasers = laser_data.shape[0]
        # Get counter bin width
        bin_width = self.fast_counter_settings.get('bin_width')

        if not isinstance(bin_width, float):
            return np.zeros(num_of_lasers), np.zeros(num_of_lasers)

        # Convert the times in seconds to bins (i.e. array indices)
        signal_start_bin = round(signal_start / bin_width)
        signal_end_bin = round(signal_end / bin_width)

        # initialize data arrays for signal and measurement error
        signal_data = np.empty(num_of_lasers, dtype=float)
        error_data = np.empty(num_of_lasers, dtype=float)

        # loop over all laser pulses and analyze them
        for ii, laser_arr in enumerate(laser_data):
            # calculate the mean of the data in the signal window
            signal = laser_arr[signal_start_bin:signal_end_bin].mean()
            signal_sum = laser_arr[signal_start_bin:signal_end_bin].sum()
            signal_error = np.sqrt(signal_sum) / (signal_end_bin - signal_start_bin)

            # Avoid numpy C type variables overflow and NaN values
            if signal < 0 or signal != signal:
                signal_data[ii] = 0.0
                error_data[ii] = 0.0
            else:
                signal_data[ii] = signal
                error_data[ii] = signal_error

        return signal_data, error_data

    def analyse_pass_through(self, laser_data):
        """
        This method does not actually analyze anything.
        For 1 D data the output is raveled: for 2 D data, the output is the mean along the second axis.

        @param 2D numpy.ndarray laser_data: the raw timetrace data from a gated fast counter
                                            dim 0: gate number; dim 1: time bin

        @return numpy.ndarray, numpy.ndarray: analyzed data per laser pulse, error per laser pulse
        """
        length = len(laser_data)
        if len(np.shape(laser_data)) > 1:
            data = np.mean(laser_data, axis=1)
        else:
            data = np.ravel(laser_data)
        return data, np.zeros_like(length)

    def analyse_mean_reference(self, laser_data, signal_start=0.0, signal_end=200e-9, norm_start=300e-9,
                          norm_end=500e-9):
        """
        This method takes the mean of the signal window.
        It then does not divide by the background window to normalize
        but rather substracts the background window to generate the output.

        @param 2D numpy.ndarray laser_data: the raw timetrace data from a gated fast counter
                                            dim 0: gate number; dim 1: time bin
        @param float signal_start: Beginning of the signal window in s
        @param float signal_end: End of the signal window in s
        @param float norm_start: Beginning of the background window in s
        @param float norm_end: End of the background window in s

        @return numpy.ndarray, numpy.ndarray: analyzed data per laser pulse, error per laser pulse
        """
        # Get number of lasers
        num_of_lasers = laser_data.shape[0]
        # Get counter bin width
        bin_width = self.fast_counter_settings.get('bin_width')

        if not isinstance(bin_width, float):
            return np.zeros(num_of_lasers), np.zeros(num_of_lasers)

        # Convert the times in seconds to bins (i.e. array indices)
        signal_start_bin = round(signal_start / bin_width)
        signal_end_bin = round(signal_end / bin_width)
        norm_start_bin = round(norm_start / bin_width)
        norm_end_bin = round(norm_end / bin_width)

        # initialize data arrays for signal and measurement error
        signal_data = np.empty(num_of_lasers, dtype=float)
        error_data = np.empty(num_of_lasers, dtype=float)

        # loop over all laser pulses and analyze them
        for ii, laser_arr in enumerate(laser_data):
            # calculate the sum and mean of the data in the normalization window
            tmp_data = laser_arr[norm_start_bin:norm_end_bin]
            reference_sum = np.sum(tmp_data)
            reference_mean = (reference_sum / len(tmp_data)) if len(tmp_data) != 0 else 0.0

            # calculate the sum and mean of the data in the signal window
            tmp_data = laser_arr[signal_start_bin:signal_end_bin]
            signal_sum = np.sum(tmp_data)
            signal_mean = (signal_sum / len(tmp_data)) if len(tmp_data) != 0 else 0.0

            signal_data[ii] = signal_mean - reference_mean

            # calculate with respect to gaussian error 'evolution'
            error_data[ii] = signal_data[ii] * np.sqrt(1 / abs(signal_sum) + 1 / abs(reference_sum))

        return signal_data, error_data
