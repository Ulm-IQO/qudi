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
from . import FitModelBase

__all__ = ('Sine', 'DoubleSine', 'ExponentialDecaySine', 'ExponentialDecayDoubleSine',
           'DoubleExponentialDecayDoubleSine')


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

    def guess(self, data, x):
        estimate = self.make_params()
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

    def guess(self, data, x):
        estimate = self.make_params()
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

    @staticmethod
    def _model_function(x, offset, amplitude, frequency, phase, decay):
        return offset + amplitude * np.exp(-x / decay) * np.sin(2 * np.pi * frequency * x + phase)

    def guess(self, data, x):
        estimate = self.make_params()
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

    @staticmethod
    def _model_function(x, offset, amplitude_1, amplitude_2, frequency_1, frequency_2, phase_1,
                        phase_2, decay):
        result = amplitude_1 * np.sin(2 * np.pi * frequency_1 * x + phase_1)
        result += amplitude_2 * np.sin(2 * np.pi * frequency_2 * x + phase_2)
        return np.exp(-x / decay) * result + offset

    def guess(self, data, x):
        estimate = self.make_params()
        return estimate


class DoubleExponentialDecayDoubleSine(FitModelBase):
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
