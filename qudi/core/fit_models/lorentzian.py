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
from scipy.ndimage.filters import gaussian_filter1d as _gaussian_filter
from ._general import FitModelBase, estimator, correct_offset_histogram
from ._peak_helpers import estimate_double_peaks, estimate_double_dips
from ._peak_helpers import estimate_triple_peaks, estimate_triple_dips

__all__ = ('DoubleLorentzian', 'Lorentzian', 'TripleLorentzian')


def _multiple_lorentzian_1d(x, centers, sigmas, amplitudes):
    """ Mathematical definition of the sum of multiple (physical) Lorentzian functions without any
    bias.

    WARNING: iterable parameters "centers", "sigmas" and "amplitudes" must have same length.

    @param float x: The independent variable to calculate lorentz(x)
    @param iterable centers: Iterable containing center positions for all lorentzians
    @param iterable sigmas: Iterable containing sigmas for all lorentzians
    @param iterable amplitudes: Iterable containing amplitudes for all lorentzians
    """
    assert len(centers) == len(sigmas) == len(amplitudes)
    return sum(amp * sig ** 2 / ((x - c) ** 2 + sig ** 2) for c, sig, amp in
               zip(centers, sigmas, amplitudes))


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
    def _model_function(x, offset, center, sigma, amplitude):
        return offset + _multiple_lorentzian_1d(x, (center,), (sigma,), (amplitude,))

    @estimator('Peak')
    def estimate_peak(self, data, x):
        # check if input x-axis is ordered and increasing
        if not np.all(val > 0 for val in np.ediff1d(x)):
            x = x[np.argsort(x)]
            data = data[np.argsort(x)]

        # Smooth data
        filter_width = max(1, int(round(len(x) / 100)))
        data_smoothed = _gaussian_filter(data, sigma=filter_width)

        # determine peak position
        center = x[np.argmax(data_smoothed)]

        # determine offset from histogram
        data_smoothed, offset = correct_offset_histogram(data_smoothed, bin_width=filter_width)

        # calculate amplitude
        amplitude = abs(max(data) - offset)

        # according to the derived formula, calculate sigma. The crucial part is here that the
        # offset was estimated correctly, then the area under the curve is calculated correctly:
        numerical_integral = np.trapz(data_smoothed, x)
        sigma = abs(numerical_integral / (np.pi * amplitude))

        x_spacing = min(abs(np.ediff1d(x)))
        x_span = abs(x[-1] - x[0])
        data_span = abs(max(data) - min(data))

        estimate = self.make_params()
        estimate['amplitude'].set(value=amplitude, min=0, max=2 * amplitude)
        estimate['sigma'].set(value=sigma, min=x_spacing, max=x_span)
        estimate['center'].set(value=center, min=min(x) - x_span / 2, max=max(x) + x_span / 2)
        estimate['offset'].set(
            value=offset, min=min(data) - data_span / 2, max=max(data) + data_span / 2
        )
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


class DoubleLorentzian(FitModelBase):
    """ ToDo: Document
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_2', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center_1', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_2', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_1', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_2', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center_1, center_2, sigma_1, sigma_2, amplitude_1, amplitude_2):
        return offset + _multiple_lorentzian_1d(x,
                                                (center_1, center_2),
                                                (sigma_1, sigma_2),
                                                (amplitude_1, amplitude_2))

    @estimator('Peaks')
    def estimate_peaks(self, data, x):
        return estimate_double_peaks(self.make_params(), data, x)

    @estimator('Dips')
    def estimate_dips(self, data, x):
        return estimate_double_dips(self.make_params(), data, x)


class TripleLorentzian(FitModelBase):
    """ ToDo: Document
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_2', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_3', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center_1', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_2', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_3', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_1', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_2', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_3', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center_1, center_2, center_3, sigma_1, sigma_2, sigma_3,
                        amplitude_1, amplitude_2, amplitude_3):
        return offset + _multiple_lorentzian_1d(x,
                                                (center_1, center_2, center_3),
                                                (sigma_1, sigma_2, sigma_3),
                                                (amplitude_1, amplitude_2, amplitude_3))

    @estimator('Peaks')
    def estimate_peaks(self, data, x):
        return estimate_triple_peaks(self.make_params(), data, x)

    @estimator('Dips')
    def estimate_dips(self, data, x):
        return estimate_triple_dips(self.make_params(), data, x)
