# -*- coding: utf-8 -*-

"""
This file contains models of Lorentzian fitting routines for qudi based on the lmfit package.

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
from scipy.ndimage.filters import gaussian_filter1d as _gaussian_filter
from ._general import FitModelBase, estimator, correct_offset_histogram, find_highest_peaks

__all__ = ('DoubleLorentzian', 'Lorentzian',)


def _multiple_lorentzian_1d(x, centers, sigmas, amplitudes):
    """ Mathematical definition of the sum of multiple (physical) Lorentzian functions without any
    bias.

    WARNING: iterable parameters "centers", "sigmas" and "amplitudes" must have same length.

    @param float x: The independent variable to calculate lorentz(x)
    @param iterable centers: Iterable containing center positions for all lorentzians
    @param iterable sigmas: Iterable containing sigmas for all lorentzians
    @param iterable amplitudes: Iterable containing amplitudes for all lorentzians
    """
    assert len(centers) == len(sigmas) == len(amplitudes)
    return sum(amp * sig ** 2 / ((x - c) ** 2 + sig ** 2) for c, sig, amp in
               zip(centers, sigmas, amplitudes))


class Lorentzian(FitModelBase):
    """
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0., min=0., max=np.inf)
        self.set_param_hint('center', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center, sigma, amplitude):
        return offset + _multiple_lorentzian_1d(x, (center,), (sigma,), (amplitude,))

    @estimator('Peak')
    def estimate_peak(self, data, x):
        # check if input x-axis is ordered and increasing
        if not np.all(val > 0 for val in np.ediff1d(x)):
            x = x[np.argsort(x)]
            data = data[np.argsort(x)]

        # Smooth data
        if len(x) <= 10:
            filter_width = 1
        else:
            filter_width = min(10, int(round(len(x) / 10)))
        data_smoothed = _gaussian_filter(data, sigma=filter_width)

        # determine peak position
        center = x[np.argmax(data_smoothed)]

        # determine offset from histogram
        data_smoothed, offset = correct_offset_histogram(data_smoothed, bin_width=filter_width)

        # calculate amplitude
        amplitude = abs(max(data) - offset)

        # according to the derived formula, calculate sigma. The crucial part is here that the
        # offset was estimated correctly, then the area under the curve is calculated correctly:
        numerical_integral = np.trapz(data_smoothed, x)
        sigma = abs(numerical_integral / (np.pi * amplitude))

        x_spacing = min(abs(np.ediff1d(x)))
        x_span = abs(x[-1] - x[0])
        data_span = abs(max(data) - min(data))

        estimate = self.make_params()
        estimate['amplitude'].set(value=amplitude, min=0, max=2 * amplitude)
        estimate['sigma'].set(value=sigma, min=x_spacing, max=x_span)
        estimate['center'].set(value=center, min=min(x) - x_span / 2, max=max(x) + x_span / 2)
        estimate['offset'].set(
            value=offset, min=min(data) - data_span / 2, max=max(data) + data_span / 2
        )
        return estimate

    @estimator('Dip')
    def estimate_dip(self, data, x):
        estimate = self.estimate_peak(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude'].set(value=-estimate['amplitude'].value,
                                  min=-estimate['amplitude'].max,
                                  max=-estimate['amplitude'].min)
        return estimate

    @estimator('Peak (no offset)')
    def estimate_peak_no_offset(self, data, x):
        estimate = self.estimate_peak(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Dip (no offset)')
    def estimate_dip_no_offset(self, data, x):
        estimate = self.estimate_dip(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate


class DoubleLorentzian(FitModelBase):
    """ ToDo: Document
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_2', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center_1', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_2', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_1', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_2', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center_1, center_2, sigma_1, sigma_2, amplitude_1, amplitude_2):
        return offset + _multiple_lorentzian_1d(x,
                                                (center_1, center_2),
                                                (sigma_1, sigma_2),
                                                (amplitude_1, amplitude_2))

    @estimator('Peaks')
    def estimate_peaks(self, data, x):
        # check if input x-axis is ordered and increasing
        if not np.all(val > 0 for val in np.ediff1d(x)):
            x = x[np.argsort(x)]
            data = data[np.argsort(x)]

        # Smooth data
        filter_width = min(1, int(round(len(x) / 100)))
        data_smoothed = _gaussian_filter(data, sigma=filter_width)

        # determine offset from histogram
        data_smoothed, offset = correct_offset_histogram(data_smoothed, bin_width=filter_width)

        # Find peaks along with width and amplitude estimation
        peak_indices, peak_heights, peak_widths = find_highest_peaks(
            data_smoothed,
            peak_count=2,
            width=filter_width,
            height=0.05 * max(data_smoothed)
        )

        x_spacing = min(abs(np.ediff1d(x)))
        x_span = abs(x[-1] - x[0])
        data_span = abs(max(data) - min(data))

        # Replace missing peaks with sensible default value
        if len(peak_indices) == 1:
            # If just one peak was found, assume it is two peaks overlapping and split it into two
            left_peak_index = max(0, int(round(peak_indices[0] - peak_widths[0] / 2)))
            right_peak_index = min(len(x) - 1, int(round(peak_indices[0] + peak_widths[0] / 2)))
            peak_indices = (left_peak_index, right_peak_index)
            peak_heights = (peak_heights[0] / 2, peak_heights[0] / 2)
            peak_widths = (peak_widths[0] / 2, peak_widths[0] / 2)
        elif len(peak_indices) == 0:
            # If no peaks have been found, just make a wild guess
            peak_indices = (len(x) // 4, 3 * len(x) // 4)
            peak_heights = (data_span, data_span)
            peak_widths = (x_spacing * 10, x_spacing * 10)

        estimate = self.make_params()
        estimate['amplitude_1'].set(value=peak_heights[0], min=0, max=2 * data_span)
        estimate['amplitude_2'].set(value=peak_heights[1], min=0, max=2 * data_span)
        estimate['sigma_1'].set(value=peak_widths[0] * x_spacing / 2.3548,
                                min=x_spacing,
                                max=x_span)
        estimate['sigma_2'].set(value=peak_widths[1] * x_spacing / 2.3548,
                                min=x_spacing,
                                max=x_span)
        estimate['center_1'].set(value=x[peak_indices[0]],
                                 min=min(x) - x_span / 2,
                                 max=max(x) + x_span / 2)
        estimate['center_2'].set(value=x[peak_indices[1]],
                                 min=min(x) - x_span / 2,
                                 max=max(x) + x_span / 2)
        estimate['offset'].set(value=offset,
                               min=min(data) - data_span / 2,
                               max=max(data) + data_span / 2)
        return estimate

    @estimator('Dips')
    def estimate_dips(self, data, x):
        estimate = self.estimate_peaks(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude_1'].set(value=-estimate['amplitude_1'].value,
                                    min=-estimate['amplitude_1'].max,
                                    max=-estimate['amplitude_1'].min)
        estimate['amplitude_2'].set(value=-estimate['amplitude_2'].value,
                                    min=-estimate['amplitude_2'].max,
                                    max=-estimate['amplitude_2'].min)
        return estimate
