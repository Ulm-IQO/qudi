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

import numpy as np
from . import FitModelBase, estimator

__all__ = ('Linear',)


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
        estimate = self.make_params()
        try:
            data = np.asarray(data)
            x = np.asarray(x)
            # calculate the parameters using Least-squares estimation of linear regression
            x_mean = np.mean(x)
            data_mean = np.mean(data)
            a_1 = np.sum((x - x_mean) * (data - data_mean))
            a_2 = np.sum(np.power(x - x_mean, 2))

            slope = a_1 / a_2
            intercept = data_mean - slope * x_mean
            estimate['offset'].value = intercept
            estimate['slope'].value = slope
        except:
            self.log.warning('The estimation for Linear fit model did not work.')
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        estimate = self.estimate()
        estimate['offset'].set(value=0, vary=False)
        return estimate
