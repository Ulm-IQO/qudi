# -*- coding: utf-8 -*-

"""
This file contains models for linear fitting routines for qudi based on the lmfit package.

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

__all__ = ('Linear',)

import numpy as np
from ._general import FitModelBase, estimator


class Linear(FitModelBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('slope', value=0, min=-np.inf, max=np.inf)

    @staticmethod
    def _model_function(x, offset, slope):
        return offset + slope * x

    @estimator('default')
    def estimate(self, data, x):
        data = np.asarray(data)
        x = np.asarray(x)
        # calculate the parameters using Least-squares estimation of linear regression
        x_mean = np.mean(x)
        data_mean = np.mean(data)
        a_1 = np.sum((x - x_mean) * (data - data_mean))
        a_2 = np.sum(np.power(x - x_mean, 2))

        slope = a_1 / a_2
        intercept = data_mean - slope * x_mean

        max_slope = (max(data) - min(data)) / abs(x[-1] - x[0])  # maximum slope possible

        estimate = self.make_params()
        estimate['offset'].set(value=intercept, min=-np.inf, max=np.inf)
        estimate['slope'].set(value=slope, min=-max_slope, max=max_slope)
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        estimate = self.estimate(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Constant')
    def estimate_no_offset(self, data, x):
        estimate = self.make_params()
        estimate['slope'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        estimate['offset'].set(value=np.mean(data), min=min(data), max=max(data))
        return estimate
