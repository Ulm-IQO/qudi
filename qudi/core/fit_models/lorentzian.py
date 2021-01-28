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
from . import FitModelBase, estimator

__all__ = ('Lorentzian',)


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
    def _model_function(x, offset, amplitude, center, sigma):
        return offset + amplitude * sigma ** 2 / ((x - center) ** 2 + sigma ** 2)

    @estimator('Peak')
    def estimate_peak(self, data, x):
        estimate = self.make_params()
        x_range = abs(x[-1] - x[0])

        offset = np.mean(data)
        amplitude = np.max(data) - np.min(data)
        center = x[np.argmax(data)]
        sigma = x_range / 10
        estimate['offset'].set(value=offset,
                               min=np.min(data) - amplitude / 2,
                               max=np.max(data) + amplitude / 2)
        estimate['amplitude'].set(value=amplitude, min=0, max=amplitude * 1.5)
        estimate['center'].set(value=center,
                               min=np.min(x) - x_range / 2,
                               max=np.max(x) + x_range / 2)
        estimate['sigma'].set(value=sigma, min=0, max=x_range)
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
