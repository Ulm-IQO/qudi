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

import lmfit
import numpy as np

__all__ = ('Lorentzian',)


class Lorentzian(lmfit.Model):
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
        return offset + amplitude * sigma ** 2 / ((x - center) ** 2 + sigma ** 2)

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
