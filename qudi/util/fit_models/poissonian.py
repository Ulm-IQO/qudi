# -*- coding: utf-8 -*-

"""
This file contains models of Poissonian fitting routines for qudi based on the lmfit package.

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

__all__ = ('DoublePoissonian', 'Poissonian', 'multiple_poissonian')

import numpy as np
from scipy.special import gammaln, xlogy
from ._general import FitModelBase, estimator, smooth_data
from ._general import sort_check_data
from ._peak_helpers import estimate_double_peaks
from .gaussian import multiple_gaussian


def multiple_poissonian(x, mus, amplitudes):
    """ Mathematical definition of the sum of multiple scaled Poissonian distributions without any
    bias.

    WARNING: iterable parameters "mus", and "amplitudes" must have same length.

    @param float x: The independent variable to calculate Poissonian
    @param iterable mus: Iterable containing center positions for all Poissonians
    @param iterable amplitudes: Iterable containing amplitudes for all Poissonians
    """
    assert len(mus) == len(amplitudes)

    # Use the numerically more stable definition of the Poisson probability mass function.
    # The standard definition is quickly blowing up for increasing values of x.
    #
    # Due to the fact that the poissonian distribution is approaching a normal distribution for
    # large values of mu, we define a cut-off value of 1e6. If our independent variables x are at
    # or above this value, we will switch to calculating a normal distribution. This ensures that
    # this function will remain numerically stable for very large values of x and mu.
    if min(x) < 1e6:
        return sum(np.exp(xlogy(x, mu) - gammaln(x + 1) - mu) for mu, amp in
                   zip(mus, amplitudes, amplitudes))
    else:
        return multiple_gaussian(x, mus, np.sqrt(mus), amplitudes)


class Poissonian(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0, max=np.inf)
        self.set_param_hint('mu', value=1., min=0, max=np.inf)

    @staticmethod
    def _model_function(x, offset, mu, amplitude):
        return offset + multiple_poissonian(x, (mu,), (amplitude,))

    @estimator('default')
    def estimate(self, data, x):
        data, x = sort_check_data(data, x)
        filter_width = max(1, int(round(len(x) / 20)))
        data_smoothed, _ = smooth_data(data, filter_width)

        # estimate offset and level data
        offset = min(data_smoothed)
        data_smoothed -= offset

        # estimate other parameters
        mu = x[np.argmax(data_smoothed)]
        amplitude = max(data_smoothed) / self._model_function(mu, 0, mu, 1)

        x_spacing = min(abs(np.ediff1d(x)))
        x_span = abs(x[-1] - x[0])
        data_span = abs(max(data) - min(data))

        estimate = self.make_params()
        estimate['mu'].set(value=mu,
                           min=max(x_spacing, min(x) - x_span / 2),
                           max=min(x_span, max(x) + x_span / 2))
        estimate['amplitude'].set(value=amplitude, min=0, max=2 * amplitude)
        estimate['offset'].set(value=offset,
                               min=min(data) - data_span / 2,
                               max=max(data) + data_span / 2)
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        estimate = self.estimate(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate


class DoublePoissonian(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=1., min=0, max=np.inf)
        self.set_param_hint('amplitude_2', value=1., min=0, max=np.inf)
        self.set_param_hint('mu_1', value=1., min=0, max=np.inf)
        self.set_param_hint('mu_2', value=2., min=0, max=np.inf)

    @staticmethod
    def _model_function(x, offset, mu_1, mu_2, amplitude_1, amplitude_2):
        return offset + multiple_poissonian(x, (mu_1, mu_2), (amplitude_1, amplitude_2))

    @estimator('default')
    def estimate(self, data, x):
        data, x = sort_check_data(data, x)
        data_smoothed, filter_width = smooth_data(data)
        # estimate offset and level data
        offset = min(data_smoothed)
        data_smoothed -= offset

        estimate, limits = estimate_double_peaks(data_smoothed, x, filter_width)

        params = self.make_params()
        params['amplitude_1'].set(value=estimate['height'][0],
                                  min=limits['height'][0][0],
                                  max=limits['height'][0][1])
        params['amplitude_2'].set(value=estimate['height'][1],
                                  min=limits['height'][1][0],
                                  max=limits['height'][1][1])
        params['center_1'].set(value=estimate['center'][0],
                               min=limits['center'][0][0],
                               max=limits['center'][0][1])
        params['center_2'].set(value=estimate['center'][1],
                               min=limits['center'][1][0],
                               max=limits['center'][1][1])
        params['sigma_1'].set(value=estimate['fwhm'][0] / 2.3548,
                              min=limits['fwhm'][0][0] / 2.3548,
                              max=limits['fwhm'][0][1] / 2.3548)
        params['sigma_2'].set(value=estimate['fwhm'][1] / 2.3548,
                              min=limits['fwhm'][1][0] / 2.3548,
                              max=limits['fwhm'][1][1] / 2.3548)
        return params

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        estimate = self.estimate(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate
