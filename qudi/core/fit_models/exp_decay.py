# -*- coding: utf-8 -*-

"""
This file contains models of exponential decay fitting routines for qudi based on the lmfit package.

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

__all__ = ('StretchedExponentialDecay',)


class ExponentialDecay(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0., max=np.inf)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, decay, stretch):
        return offset + amplitude * np.exp(-(x / decay) ** stretch)

    @estimator('Decay')
    def estimate_decay(self, data, x):
        estimate = self.make_params()
        offset = data[-1]
        amplitude = data[0] - offset
        decay = (data[1] - data[0]) / (x[-1] - x[0]) / (data[-1] - data[0])
        estimate['offset'].set(value=offset, max=max(data))
        estimate['amplitude'].set(value=amplitude)
        estimate['decay'].set(value=decay, min=abs(x[1] - x[0]))
        estimate['stretch'].set(value=1, vary=False)
        return estimate

    @estimator('Stretched Decay')
    def estimate_stretched_decay(self, data, x):
        # ToDo: Better estimator actually suited for a STRETCHED exponential
        estimate = self.estimate_decay(data, x)
        estimate['stretch'].set(value=2, min=abs(x[1]-x[0]))
        return estimate

    @estimator('Decay (no offset)')
    def estimate_decay_no_offset(self, data, x):
        estimate = self.estimate_decay(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Stretched Decay (no offset)')
    def estimate_stretched_decay_no_offset(self, data, x):
        estimate = self.estimate_stretched_decay(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate
