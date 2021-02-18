# -*- coding: utf-8 -*-

"""
This file contains models of Gaussian fitting routines for qudi based on the lmfit package.

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
from ._general import FitModelBase, estimator, correct_offset_histogram, find_peaks

__all__ = ('DoubleGaussian', 'Gaussian', 'Gaussian2D')


class Gaussian(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, center, sigma):
        return offset + amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))

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
        sigma = abs(numerical_integral / (np.sqrt(2 * np.pi) * amplitude))

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


class DoubleGaussian(FitModelBase):
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
    def _model_function(x, offset, amplitude_1, center_1, sigma_1, amplitude_2, center_2, sigma_2):
        gauss = amplitude_1 * np.exp(-((x - center_1) ** 2) / (2 * sigma_1 ** 2))
        gauss += amplitude_2 * np.exp(-((x - center_2) ** 2) / (2 * sigma_2 ** 2))
        gauss += offset
        return gauss

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
        peak_indices, peak_heights, peak_widths = find_peaks(data_smoothed,
                                                             peak_count=2,
                                                             width=filter_width)

        x_spacing = min(abs(np.ediff1d(x)))
        x_span = abs(x[-1] - x[0])
        data_span = abs(max(data) - min(data))

        # Replace missing peaks with sensible default value
        while len(peak_indices) < 2:
            peak_indices = np.append(peak_indices, [len(x) // 2])
            peak_heights = np.append(peak_heights, [data_span])
            peak_widths = np.append(peak_widths, [x_spacing * 10])

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


class Gaussian2D(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_x', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_y', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_x', value=0, min=0, max=np.inf)
        self.set_param_hint('sigma_y', value=0, min=0, max=np.inf)
        self.set_param_hint('theta', value=0., min=-np.pi, max=np.pi)

    @staticmethod
    def _model_function(xy, offset, amplitude, center_x, center_y, sigma_x, sigma_y, theta):
        try:
            a = np.cos(-theta) ** 2 / (2 * sigma_x ** 2) + np.sin(-theta) ** 2 / (2 * sigma_y ** 2)
            b = np.sin(2 * -theta) / (4 * sigma_y ** 2) - np.sin(2 * -theta) / (4 * sigma_x ** 2)
            c = np.sin(-theta) ** 2 / (2 * sigma_x ** 2) + np.cos(-theta) ** 2 / (2 * sigma_y ** 2)
        except ZeroDivisionError:
            return np.full(xy[0].shape, offset)
        x_prime = xy[0] - center_x
        y_prime = xy[1] - center_y
        gauss = offset + amplitude * np.exp(
            -(a * x_prime ** 2 + 2 * b * x_prime * y_prime + c * y_prime ** 2))
        return gauss.ravel()

    @estimator('Peak')
    def estimate_peak(self, data, xy):
        # ToDo: Not properly implemented, yet
        x_range = abs(max(xy[0]) - min(xy[0]))
        y_range = abs(max(xy[1]) - min(xy[1]))

        amplitude = max(data)
        center_x = x_range / 2 + min(xy[0])
        center_y = y_range / 2 + min(xy[1])
        sigma_x = x_range / 10
        sigma_y = y_range / 10
        theta = 0

        estimate = self.make_params()
        estimate['offset'].set(value=np.mean(data), min=-np.inf, max=max(data))
        estimate['amplitude'].set(value=amplitude, min=0, max=amplitude * 2)
        estimate['center_x'].set(value=center_x, min=np.min(xy[0]) - x_range / 2, max=np.max(xy[0]) + x_range / 2)
        estimate['center_y'].set(value=center_y, min=np.min(xy[1]) - x_range / 2, max=np.max(xy[1]) + x_range / 2)
        estimate['sigma_x'].set(value=sigma_x, min=x_range / (xy[0].shape[0] - 1), max=x_range)
        estimate['sigma_y'].set(value=sigma_y, min=y_range / (xy[0].shape[1] - 1), max=y_range)
        estimate['theta'].set(value=theta, min=-np.pi, max=np.pi)
        return estimate

    @estimator('Dip')
    def estimate_dip(self, data, xy):
        estimate = self.estimate_peak(-data, xy)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude'].set(value=-estimate['amplitude'].value,
                                  min=-estimate['amplitude'].max,
                                  max=-estimate['amplitude'].min)
        return estimate
