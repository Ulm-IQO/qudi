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

__all__ = ('Sine', 'DoubleSine', 'ExponentialDecaySine', 'estimate_frequency_ft')

import numpy as np
from qudi.util.math import compute_ft
from ._general import FitModelBase, estimator, sort_check_data


def estimate_frequency_ft(data, x):
    # calculate PSD with zeropadding to obtain nicer interpolation between the appearing peaks.
    dft_x, dft_y = compute_ft(x, data, zeropad_num=1, psd=True)
    # Maximum PSD value corresponds to most likely frequency
    return abs(dft_x[dft_y.argmax()]), (dft_x, dft_y)


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
        data, x = sort_check_data(data, x)
        x_span = abs(max(x) - min(x))
        offset = np.mean(data)

        estimate = self.estimate_no_offset(data - offset, x)
        if 1/(2 * estimate['frequency'].value) > x_span:
            estimate['offset'].set(value=offset, min=-np.inf, max=np.inf, vary=True)
        else:
            estimate['offset'].set(value=offset, min=min(data), max=max(data), vary=True)
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        data, x = sort_check_data(data, x)
        x_step = min(abs(np.ediff1d(x)))
        data_span = abs(max(data) - min(data))
        amplitude = data_span / 2

        frequency, _ = estimate_frequency_ft(data, x)

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
        data, x = sort_check_data(data, x)
        x_step = min(abs(np.ediff1d(x)))
        x_span = abs(max(x) - min(x))
        data_span = abs(max(data) - min(data))

        amplitude = data_span / 2
        offset = np.mean(data)
        frequency, _ = estimate_frequency_ft(data - offset, x)

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
        x_span = abs(max(x) - min(x))
        offset = np.mean(data)

        estimate = self.estimate_no_offset(data - offset, x)
        if 1 / (2 * min(estimate['frequency_1'].value, estimate['frequency_2'].value)) > x_span:
            estimate['offset'].set(value=offset, min=-np.inf, max=np.inf, vary=True)
        else:
            estimate['offset'].set(value=offset, min=min(data), max=max(data), vary=True)
        return estimate

    @estimator('No Offset')
    def estimate_no_offset(self, data, x):
        data, x = sort_check_data(data, x)
        # Fit a single sine to the data
        single_sine_model = Sine()
        single_sine_result = single_sine_model.fit(data,
                                                   single_sine_model.estimate_no_offset(data, x),
                                                   x=x)
        # Subtract the fitted sine and estimate another single sine from the remaining data
        data_sub = data - single_sine_result.best_fit
        single_sine_estimate = single_sine_model.estimate_no_offset(data_sub, x)
        # Merge single sine fit result and single sine estimate

        single_fit_params = single_sine_result.params
        estimate = self.make_params()
        estimate['amplitude_1'].set(value=single_fit_params['amplitude'].value,
                                    min=single_fit_params['amplitude'].min,
                                    max=single_fit_params['amplitude'].max,
                                    vary=True)
        estimate['amplitude_2'].set(value=single_sine_estimate['amplitude'].value,
                                    min=single_sine_estimate['amplitude'].min,
                                    max=single_sine_estimate['amplitude'].max,
                                    vary=True)
        estimate['frequency_1'].set(value=single_fit_params['frequency'].value,
                                    min=single_fit_params['frequency'].min,
                                    max=single_fit_params['frequency'].max,
                                    vary=True)
        estimate['frequency_2'].set(value=single_sine_estimate['frequency'].value,
                                    min=single_sine_estimate['frequency'].min,
                                    max=single_sine_estimate['frequency'].max,
                                    vary=True)
        estimate['phase_1'].set(value=single_fit_params['phase'].value,
                                min=single_fit_params['phase'].min,
                                max=single_fit_params['phase'].max,
                                vary=True)
        estimate['phase_2'].set(value=single_sine_estimate['phase'].value,
                                min=single_sine_estimate['phase'].min,
                                max=single_sine_estimate['phase'].max,
                                vary=True)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
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
        x_span = abs(max(x) - min(x))
        offset = np.mean(data)

        estimate = self.estimate_decay_no_offset(data - offset, x)
        if 1 / (2 * estimate['frequency'].value) > x_span:
            estimate['offset'].set(value=offset, min=-np.inf, max=np.inf, vary=True)
        else:
            estimate['offset'].set(value=offset, min=min(data), max=max(data), vary=True)
        return estimate

    @estimator('Stretched Decay')
    def estimate_stretched_decay(self, data, x):
        # ToDo: Stretch estimation
        estimate = self.estimate_decay(data, x)
        estimate['stretch'].set(value=2, min=0, max=np.inf, vary=True)
        return estimate

    @estimator('Decay (no offset)')
    def estimate_decay_no_offset(self, data, x):
        data, x = sort_check_data(data, x)
        x_step = min(abs(np.ediff1d(x)))
        data_span = abs(max(data) - min(data))
        amplitude = data_span / 2

        frequency, (dft_x, dft_y) = estimate_frequency_ft(data, x)

        # remove noise for peak width and decay constant estimation
        dft_y[np.argwhere(dft_y <= np.std(dft_y))] = 0
        # calculating the width of the FT peak for the estimation of decay constant
        decay = 1 / (2 * np.trapz(dft_y, dft_x) / max(dft_y))
        # s = 0
        # for i in range(0, len(dft_x)):
        #     s += dft_y[i] * abs(dft_x[1] - dft_x[0]) / max(dft_y)
        # lifetime_val = 0.5 / s

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
        estimate['decay'].set(value=decay,
                              min=2 * x_step,
                              max=1/(abs(dft_x[1]-dft_x[0])*0.5),
                              vary=True)
        estimate['stretch'].set(value=1, min=0, max=np.inf, vary=False)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Stretched Decay (no offset)')
    def estimate_stretched_decay_no_offset(self, data, x):
        # ToDo: Stretch estimation
        estimate = self.estimate_decay_no_offset(data, x)
        estimate['stretch'].set(value=2, min=0, max=np.inf, vary=True)
        return estimate


class ExponentialDecayDoubleSine(FitModelBase):
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
        self.set_param_hint('decay', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
                        phase_2, decay, stretch):
        result = amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
        result += amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
        return np.exp(-(x / decay) ** stretch) * result + offset

    @estimator('Decay')
    def estimate_decay(self, data, x):
        x_span = abs(max(x) - min(x))
        offset = np.mean(data)

        estimate = self.estimate_decay_no_offset(data - offset, x)
        if 1 / (2 * min(estimate['frequency_1'].value, estimate['frequency_2'].value)) > x_span:
            estimate['offset'].set(value=offset, min=-np.inf, max=np.inf, vary=True)
        else:
            estimate['offset'].set(value=offset, min=min(data), max=max(data), vary=True)
        return estimate

    @estimator('Stretched Decay')
    def estimate_stretched_decay(self, data, x):
        # ToDo: Stretch estimation
        estimate = self.estimate_decay(data, x)
        estimate['stretch'].set(value=2, min=0, max=np.inf, vary=True)
        return estimate

    @estimator('Decay (no offset)')
    def estimate_decay_no_offset(self, data, x):
        data, x = sort_check_data(data, x)

        # Try to estimate fit from fitting single sine cases
        model = ExponentialDecaySine()
        first_sine_fit = model.fit(data, model.estimate_decay_no_offset(data, x), x=x)
        data_sub = data - first_sine_fit.best_fit
        model = Sine()
        second_sine_fit = model.fit(data_sub, model.estimate_no_offset(data_sub, x), x=x)

        # Merge fit results into estimated parameters
        first_params = first_sine_fit.params
        second_params = second_sine_fit.params
        estimate = self.make_params()
        estimate['frequency_1'].set(value=first_params['frequency'].value,
                                    min=first_params['frequency'].min,
                                    max=first_params['frequency'].max,
                                    vary=True)
        estimate['frequency_2'].set(value=second_params['frequency'].value,
                                    min=second_params['frequency'].min,
                                    max=second_params['frequency'].max,
                                    vary=True)
        estimate['amplitude_1'].set(value=first_params['amplitude'].value,
                                    min=first_params['amplitude'].min,
                                    max=first_params['amplitude'].max,
                                    vary=True)
        estimate['amplitude_2'].set(value=second_params['amplitude'].value,
                                    min=second_params['amplitude'].min,
                                    max=second_params['amplitude'].max,
                                    vary=True)
        estimate['phase_1'].set(value=first_params['phase'].value,
                                min=first_params['phase'].min,
                                max=first_params['phase'].max,
                                vary=True)
        estimate['phase_2'].set(value=second_params['phase'].value,
                                min=second_params['phase'].min,
                                max=second_params['phase'].max,
                                vary=True)
        estimate['decay'].set(value=first_params['decay'].value,
                              min=first_params['decay'].min,
                              max=first_params['decay'].max,
                              vary=True)
        estimate['stretch'].set(value=1, min=0, max=np.inf, vary=False)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Stretched Decay (no offset)')
    def estimate_stretched_decay_no_offset(self, data, x):
        # ToDo: Stretch estimation
        estimate = self.estimate_decay_no_offset(data, x)
        estimate['stretch'].set(value=2, min=0, max=np.inf, vary=True)
        return estimate


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
