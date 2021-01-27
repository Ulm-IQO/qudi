# -*- coding: utf-8 -*-

"""
This file contains models of linear fitting routines for qudi based on the lmfit package.

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
from . import FitModelBase

__all__ = ('Constant', 'Linear')


class Constant(FitModelBase):
    """
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)

    @staticmethod
    def _model_function(x, offset):
        return np.full(len(x), offset)

    def guess(self, data, x):
        estimate = self.make_params(offset=np.median(data))
        estimate['offset'].set(min=min(data), max=max(data))
        return estimate


class Linear(FitModelBase):
    """
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('intersect', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('slope', value=0., min=-np.inf, max=np.inf)

    @staticmethod
    def _model_function(x, intersect, slope):
        return intersect + slope * x

    def guess(self, data, x):
        y_span = data[-1] - data[0]
        x_span = x[-1] - x[0]
        slope = y_span / x_span
        intersect = data[0] - x[0] * slope
        estimate = self.make_params(intersect=intersect, slope=slope)
        estimate['intersect'].set(min=-np.inf, max=np.inf)
        estimate['slope'].set(min=-np.inf, max=np.inf)
        return estimate
