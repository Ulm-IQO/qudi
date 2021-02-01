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
from scipy.ndimage import filters
from ._general import FitModelBase, estimator

__all__ = ('Gaussian', 'Gaussian2D')


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
        estimate = self.make_params()

        x_span = abs(x[-1] - x[0])
        x_step = abs(x[1] - x[0])
        data_smoothed = filters.gaussian_filter1d(data, sigma=2)
        y_span = max(data_smoothed) - min(data_smoothed)
        smooth_sum = np.sum(data_smoothed)
        smooth_mean = np.mean(data_smoothed)
        mom1 = np.sum(x * data_smoothed) / smooth_sum
        mom2 = np.sum(x ** 2 * data_smoothed) / smooth_sum

        estimate['offset'].set(value=smooth_mean,
                               min=min(data_smoothed) - 5 * y_span,
                               max=max(data_smoothed) + 5 * y_span)
        estimate['amplitude'].set(value=y_span, min=0, max=y_span * 5)
        estimate['center'].set(value=x[np.argmax(data_smoothed)],
                               min=min(x) - x_span,
                               max=max(x) + x_span)
        estimate['sigma'].set(value=np.sqrt(abs(mom2 - mom1 ** 2)),
                              min=x_step,
                              max=x_span)
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
        x_range = abs(xy[0].max() - xy[0].min())
        y_range = abs(xy[1].max() - xy[1].min())

        amplitude = np.max(data)
        center_x = x_range / 2 + xy[0].min()
        center_y = y_range / 2 + xy[1].min()
        sigma_x = x_range / 10
        sigma_y = y_range / 10
        theta = 0
        estimate = self.make_params(offset=np.mean(data),
                                    amplitude=amplitude,
                                    center_x=center_x,
                                    center_y=center_y,
                                    sigma_x=sigma_x,
                                    sigma_y=sigma_y,
                                    theta=theta)
        estimate['offset'].set(min=min(data), max=max(data))
        estimate['amplitude'].set(min=0, max=amplitude * 2)
        estimate['center_x'].set(min=np.min(xy[0]) - x_range / 2, max=np.max(xy[0]) + x_range / 2)
        estimate['center_y'].set(min=np.min(xy[1]) - x_range / 2, max=np.max(xy[1]) + x_range / 2)
        estimate['sigma_x'].set(min=x_range / (xy[0].shape[0] - 1), max=x_range)
        estimate['sigma_y'].set(min=y_range / (xy[0].shape[1] - 1), max=y_range)
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
