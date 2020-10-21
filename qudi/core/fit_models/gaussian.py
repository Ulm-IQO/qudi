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

import lmfit
import numpy as np

__all__ = ('Gaussian', 'Gaussian2D')


class Gaussian(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0., min=0., max=np.inf)
        self.set_param_hint('center', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, center, sigma):
        return offset + amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))

    def guess(self, data, x):
        x_range = abs(x[-1] - x[0])

        offset = np.median(data)
        amplitude = np.max(data) - np.min(data)
        center = x[np.argmax(data)]
        sigma = x_range / 10
        estimate = self.make_params(offset=offset,
                                    amplitude=amplitude,
                                    center=center,
                                    sigma=sigma)
        estimate['offset'].set(min=np.min(data) - amplitude / 2, max=np.max(data) + amplitude / 2)
        estimate['amplitude'].set(min=0, max=amplitude * 1.5)
        estimate['center'].set(min=np.min(x) - x_range / 2, max=np.max(x) + x_range / 2)
        estimate['sigma'].set(min=0, max=x_range)
        return estimate


class Gaussian2D(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0., min=0., max=np.inf)
        self.set_param_hint('center_x', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_y', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_x', value=1., min=0, max=np.inf)
        self.set_param_hint('sigma_y', value=1., min=0, max=np.inf)
        self.set_param_hint('theta', value=0., min=0, max=np.pi)

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

    def guess(self, data, xy):
        x_range = xy[0].max() - xy[0].min()
        y_range = xy[1].max() - xy[1].min()

        offset = (data[:, 0].mean() + data[:, -1].mean() + data[0, :].mean() + data[-1, :].mean())/4
        amplitude = np.max(data) - offset
        center_x = x_range / 2 + xy[0].min()
        center_y = y_range / 2 + xy[1].min()
        sigma_x = x_range / 10
        sigma_y = y_range / 10
        theta = 0
        estimate = self.make_params(offset=offset,
                                    amplitude=amplitude,
                                    center_x=center_x,
                                    center_y=center_y,
                                    sigma_x=sigma_x,
                                    sigma_y=sigma_y,
                                    theta=theta)
        estimate['offset'].set(min=np.min(data) - amplitude / 2, max=np.max(data) + amplitude / 2)
        estimate['amplitude'].set(min=0, max=amplitude * 1.5)
        estimate['center_x'].set(min=np.min(xy[0]) - x_range / 2, max=np.max(xy[0]) + x_range / 2)
        estimate['center_y'].set(min=np.min(xy[1]) - x_range / 2, max=np.max(xy[1]) + x_range / 2)
        estimate['sigma_x'].set(min=x_range / (xy[0].shape[0] - 1), max=x_range)
        estimate['sigma_y'].set(min=y_range / (xy[0].shape[1] - 1), max=y_range)
        estimate['theta'].set(min=0, max=x_range)
        return estimate
