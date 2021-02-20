# -*- coding: utf-8 -*-

"""
This file contains models of Sine fitting routines for qudi based on the lmfit package.

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
from qudi.core.util.math import compute_ft
from ._general import FitModelBase, estimator

__all__ = ('Sine', 'DoubleSine', 'ExponentialDecaySine', 'estimate_frequency_ft')


def estimate_frequency_ft(data, x):
    # calculate PSD with zeropadding to obtain nicer interpolation between the appearing peaks.
    dft_x, dft_y = compute_ft(x, data, zeropad_num=1, psd=True)
    # Maximum PSD value corresponds to most likely frequency
    return abs(dft_x[dft_y.argmax()])


class Sine(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency', value=0., min=0., max=np.inf)
        self.set_param_hint('phase', value=0., min=-np.pi, max=np.pi)

    @staticmethod
    def _model_function(x, offset, amplitude, frequency, phase):
        return offset + amplitude * np.sin(2 * np.pi * frequency * x + phase)

    @estimator('default')
    def estimate(self, data, x):
        x_span = abs(max(data) - min(data))
        offset = np.mean(data)

        estimate = self.estimate_no_offset(data - offset, x)
        if 1/(2 * estimate['frequency'].value) > x_span:
            estimate['offset'].set(value=offset, min=-np.inf, max=np.inf, vary=True)
        else:
            estimate['offset'].set(value=offset, min=min(data), max=max(data), vary=True)
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        x_step = min(abs(np.ediff1d(x)))
        data_span = abs(max(data) - min(data))
        amplitude = data_span / 2

        frequency = estimate_frequency_ft(data, x)

        # Find an estimate for the phase
        # Procedure: Create sin waves with different phases and perform a summation.
        #            The sum shows how well the sine was fitting to the actual data.
        #            The best fitting sine should be a maximum of the summed time
        #            trace.
        iter_steps = max(1, int(round(1 / (frequency * x_step))))
        test_phases = 2 * np.pi * np.arange(iter_steps) / iter_steps
        sum_res = np.zeros(iter_steps)
        for ii, phase in enumerate(test_phases):
            sum_res[ii] = np.abs(data - amplitude * np.sin(2 * np.pi * frequency * x + phase)).sum()
        phase = test_phases[sum_res.argmax()] - np.pi  # Maximum sum value corresponds to worst fit

        estimate = self.make_params()
        estimate['frequency'].set(value=frequency, min=0, max=1 / (2 * x_step), vary=True)
        estimate['amplitude'].set(value=amplitude, min=0, max=2 * data_span, vary=True)
        estimate['phase'].set(value=phase, min=-np.pi, max=np.pi, vary=True)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Zero Phase')
    def estimate_zero_phase(self, data, x):
        x_step = min(abs(np.ediff1d(x)))
        x_span = abs(max(data) - min(data))
        data_span = abs(max(data) - min(data))

        amplitude = data_span / 2
        offset = np.mean(data)
        frequency = estimate_frequency_ft(data - offset, x)

        estimate = self.make_params()
        estimate['frequency'].set(value=frequency, min=0, max=1 / (2 * x_step), vary=True)
        estimate['amplitude'].set(value=amplitude, min=0, max=2 * data_span, vary=True)
        if 1/(2 * frequency) > x_span:
            estimate['offset'].set(value=offset, min=-np.inf, max=np.inf, vary=True)
        else:
            estimate['offset'].set(value=offset, min=min(data), max=max(data), vary=True)
        estimate['phase'].set(value=0, min=-np.pi, max=np.pi, vary=False)
        return estimate


class DoubleSine(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=1., min=0., max=np.inf)
        self.set_param_hint('amplitude_2', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency_1', value=0., min=0., max=np.inf)
        self.set_param_hint('frequency_2', value=0., min=0., max=np.inf)
        self.set_param_hint('phase_1', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('phase_2', value=0., min=-np.pi, max=np.pi)

    @staticmethod
    def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
                        phase_2):
        result = amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
        result += amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
        return result + offset

    @estimator('default')
    def estimate(self, data, x):
        estimate = self.make_params()
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        estimate = self.make_params()
        estimate['offset'].set(value=0, vary=False)
        return estimate


class ExponentialDecaySine(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency', value=0., min=0., max=np.inf)
        self.set_param_hint('phase', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, frequency, phase, decay, stretch):
        return offset + amplitude * np.exp(-(x / decay) ** stretch) * np.sin(
            2 * np.pi * frequency * x + phase)

    @estimator('Decay')
    def estimate_decay(self, data, x):
        estimate = self.make_params()
        estimate['stretch'].set(value=1, vary=False)
        return estimate

    @estimator('Stretched Decay')
    def estimate_stretched_decay(self, data, x):
        estimate = self.make_params()
        return estimate

    @estimator('Decay (no offset)')
    def estimate_no_offset(self, data, x):
        estimate = self.make_params()
        estimate['stretch'].set(value=1, vary=False)
        estimate['offset'].set(value=0, vary=False)
        return estimate

    @estimator('Stretched Decay (no offset)')
    def estimate_zero_phase(self, data, x):
        estimate = self.make_params()
        estimate['offset'].set(value=0, vary=False)
        return estimate


# class ExponentialDecayDoubleSine(FitModelBase):
#     """
#     """
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
#         self.set_param_hint('amplitude_1', value=1., min=0., max=np.inf)
#         self.set_param_hint('amplitude_2', value=1., min=0., max=np.inf)
#         self.set_param_hint('frequency_1', value=0., min=0., max=np.inf)
#         self.set_param_hint('frequency_2', value=0., min=0., max=np.inf)
#         self.set_param_hint('phase_1', value=0., min=-np.pi, max=np.pi)
#         self.set_param_hint('phase_2', value=0., min=-np.pi, max=np.pi)
#         self.set_param_hint('decay', value=1., min=0., max=np.inf)
#
#     @staticmethod
#     def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
#                         phase_2, decay):
#         result = amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
#         result += amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
#         return np.exp(-x / decay) * result + offset
#
#     def guess(self, data, x):
#         estimate = self.make_params()
#         return estimate
#
#
# class DoubleExponentialDecayDoubleSine(FitModelBase):
#     """
#     """
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
#         self.set_param_hint('amplitude_1', value=1., min=0., max=np.inf)
#         self.set_param_hint('amplitude_2', value=1., min=0., max=np.inf)
#         self.set_param_hint('frequency_1', value=0., min=0., max=np.inf)
#         self.set_param_hint('frequency_2', value=0., min=0., max=np.inf)
#         self.set_param_hint('phase_1', value=0., min=-np.pi, max=np.pi)
#         self.set_param_hint('phase_2', value=0., min=-np.pi, max=np.pi)
#         self.set_param_hint('decay_1', value=1., min=0., max=np.inf)
#         self.set_param_hint('decay_2', value=1., min=0., max=np.inf)
#
#     @staticmethod
#     def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
#                         phase_2, decay_1, decay_2):
#         result = np.exp(-x / decay_1) * amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
#         result += np.exp(-x / decay_2) * amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
#         return result + offset
#
#     def guess(self, data, x):
#         estimate = self.make_params()
#         return estimate
