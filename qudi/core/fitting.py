# -*- coding: utf-8 -*-

"""
This file contains data fitting routines based on the lmfit package for Qudi.

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
from scipy.ndimage import filters
from lmfit.models import LinearModel
# try:
#     from qudi.core.application import Qudi
#     _qudi_installed = True
# except ImportError:
#     _qudi_installed = False

__all__ = ('LinearModel', 'ExponentialDecay', 'StretchedExponentialDecay', 'Gaussian', 'Lorentzian')


class ExponentialDecay(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0., min=0., max=np.inf)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, decay):
        return offset + amplitude * np.exp(-x/decay)

    def guess(self, data, x):
        offset = data[-1]
        amplitude = data[0] - offset
        decay = (data[1] - data[0]) / (x[-1] - x[0]) / (data[-1] - data[0])
        estimate = self.make_params(offset=offset, amplitude=amplitude, decay=decay)
        estimate['decay'].set(min=abs(x[1]-x[0]))
        return estimate


class StretchedExponentialDecay(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0., max=np.inf)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)
        self.set_param_hint('stretch', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, decay, stretch):
        return offset + amplitude * np.exp(-(x / decay) ** stretch)

    def guess(self, data, x):
        # ToDo: Better estimator actually suited for a STRETCHED exponential
        offset = data[-1]
        amplitude = data[0] - offset
        decay = (data[1] - data[0]) / (x[-1] - x[0]) / (data[-1] - data[0])
        stretch = 2
        estimate = self.make_params(offset=offset,
                                    amplitude=amplitude,
                                    decay=decay,
                                    stretch=stretch)
        estimate['decay'].set(min=abs(x[1]-x[0]))
        return estimate


class Gaussian(lmfit.Model):
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
        return offset + amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))

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


class Sine(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency', value=0., min=0., max=np.inf)
        self.set_param_hint('phase', value=0., min=-np.pi, max=np.pi)

    @staticmethod
    def _model_function(x, offset, amplitude, frequency, phase):
        return offset + amplitude * np.sin(2 * np.pi * frequency * x + phase)

    def guess(self, data, x):
        estimate = self.make_params()
        return estimate


class DoubleSine(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
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

    def guess(self, data, x):
        estimate = self.make_params()
        return estimate


class ExponentialDecaySine(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency', value=0., min=0., max=np.inf)
        self.set_param_hint('phase', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude, frequency, phase, decay):
        return offset + amplitude * np.exp(-x / decay) * np.sin(2 * np.pi * frequency * x + phase)

    def guess(self, data, x):
        estimate = self.make_params()
        return estimate


class ExponentialDecayDoubleSine(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name, **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=1., min=0., max=np.inf)
        self.set_param_hint('amplitude_2', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency_1', value=0., min=0., max=np.inf)
        self.set_param_hint('frequency_2', value=0., min=0., max=np.inf)
        self.set_param_hint('phase_1', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('phase_2', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('decay', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
                        phase_2, decay):
        result = amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
        result += amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
        return np.exp(-x / decay) * result + offset

    def guess(self, data, x):
        estimate = self.make_params()
        return estimate


class DoubleExponentialDecayDoubleSine(lmfit.Model):
    """
    """
    def __init__(self, missing=None, prefix='', name=None, **kwargs):
        super().__init__(self._model_function, missing=missing, prefix=prefix, name=name,
                         **kwargs)
        self.set_param_hint('offset', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=1., min=0., max=np.inf)
        self.set_param_hint('amplitude_2', value=1., min=0., max=np.inf)
        self.set_param_hint('frequency_1', value=0., min=0., max=np.inf)
        self.set_param_hint('frequency_2', value=0., min=0., max=np.inf)
        self.set_param_hint('phase_1', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('phase_2', value=0., min=-np.pi, max=np.pi)
        self.set_param_hint('decay_1', value=1., min=0., max=np.inf)
        self.set_param_hint('decay_2', value=1., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
                        phase_2, decay_1, decay_2):
        result = np.exp(-x / decay_1) * amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
        result += np.exp(-x / decay_2) * amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
        return result + offset

    def guess(self, data, x):
        estimate = self.make_params()
        return estimate
