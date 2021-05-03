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

__all__ = ('ExponentialDecay', 'multiple_exponential_decay')

import numpy as np
import warnings
from scipy.ndimage import filters
from ._general import FitModelBase, estimator


def multiple_exponential_decay(x, amplitudes, decays, stretches):
    """ Mathematical definition of the sum of multiple stretched exponential decays without any
    bias.

    WARNING: iterable parameters "amplitudes", "decays" and "stretches" must have same length.

    @param float x: The independent variable to calculate f(x)
    @param iterable amplitudes: Iterable containing amplitudes for all exponentials
    @param iterable decays: Iterable containing decay constants for all exponentials
    @param iterable stretches: Iterable containing stretch constants for all exponentials

    @return float|numpy.ndarray: The result given x for f(x)
    """
    assert len(decays) == len(amplitudes) == len(stretches)
    return sum(amp * np.exp(-(x / decay) ** stretch) for amp, decay, stretch in
               zip(amplitudes, decays, stretches))


class ExponentialDecay(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=-np.inf, max=np.inf)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, decay, stretch):
        return offset + multiple_exponential_decay(x, (amplitude,), (decay,), (stretch,))

    @estimator('Decay')
    def estimate_decay(self, data, x):
        # Smooth very radically the provided data, so that noise fluctuations will not disturb the
        # parameter estimation.
        if len(data) <= 10:
            data_smoothed = data.copy()
        else:
            sigma = max(1, int(round(len(data) / 10)))
            data_smoothed = filters.gaussian_filter1d(data, sigma=sigma)

        # Calculate mean value of first and last 10% of data array. Take the latter as offset.
        mean_len = max(1, len(x) // 10)
        start_mean = np.mean(data_smoothed[mean_len:])
        offset = np.mean(data_smoothed[-mean_len:])

        # subtraction of the offset and normalization of the decay direction
        if start_mean < offset:
            data_smoothed = offset - data_smoothed
        else:
            data_smoothed = data_smoothed - offset

        # Make sure there are no negative values
        smooth_min = min(data_smoothed)
        if smooth_min <= 0:
            data_smoothed -= smooth_min

        # Take all values up to the standard deviation, the remaining values are
        # more disturbing the estimation then helping:
        tmp = np.argwhere(data_smoothed <= np.std(data_smoothed))
        stop_index = tmp[0, 0] if tmp else len(data_smoothed)

        # perform a linear fit on the logarithm of the remaining data
        try:
            poly_coef = np.polyfit(x[:stop_index], np.log(data_smoothed[:stop_index]), deg=1)
            decay = 1 / np.sqrt(abs(poly_coef[0]))
            amplitude = np.exp(poly_coef[1])
        except:
            warnings.warn('Estimation of decay constant and amplitude failed.')
            decay = abs(data[1] - data[0]) / abs(x[-1] - x[0]) / abs(data[-1] - data[0])
            amplitude = abs(start_mean - offset)

        estimate = self.make_params()
        if start_mean < offset:
            estimate['amplitude'].set(value=-amplitude, max=0)
        else:
            estimate['amplitude'].set(value=amplitude, min=0)
        estimate['offset'].set(value=offset)
        estimate['decay'].set(value=decay, min=2 * min(abs(np.ediff1d(x))))
        estimate['stretch'].set(value=1, vary=False)
        return estimate

    @estimator('Stretched Decay')
    def estimate_stretched_decay(self, data, x):
        estimate = self.estimate_decay(data, x)
        # ToDo: Estimate stretch factor. Currently just a random starting point.
        estimate['stretch'].set(value=2, min=0, max=np.inf, vary=True)
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


class DoubleExponentialDecay(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=1., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_2', value=1., min=-np.inf, max=np.inf)
        self.set_param_hint('decay_1', value=1., min=0., max=np.inf)
        self.set_param_hint('decay_2', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch_1', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch_2', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude_1, amplitude_2, decay_1, decay_2, stretch_1,
                        stretch_2):
        return offset + multiple_exponential_decay(x,
                                                   (amplitude_1, amplitude_2),
                                                   (decay_1, decay_2),
                                                   (stretch_1, stretch_2))
