# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines for exponential decay models.

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

import unittest
import numpy as np

from qudi.core.fitting import StretchedExponentialDecay


class TestExpDecayMethods(unittest.TestCase):
    _fit_param_tolerance = 0.05  # 5% tolerance for each fit parameter

    @staticmethod
    def stretched_exp_decay(x, offset, amplitude, decay, stretch):
        return offset + amplitude * np.exp(-(x / decay) ** stretch)

    def setUp(self):
        self.offset = (np.random.rand() - 0.5) * 2e6
        self.amplitude = np.random.rand() * 100
        window = max(1e-9, np.random.rand() * 1e9)
        left = (np.random.rand() - 0.5) * 2e9
        points = np.random.randint(10, 1001)
        self.x_values = np.linspace(left, left + window, points)
        min_decay = 1.5 * (self.x_values[1] - self.x_values[0])
        self.decay = min_decay + np.random.rand() * ((window / 2) - min_decay)
        self.stretch = 0.1 + np.random.rand() * 3.9
        self.noise_amp = max(self.amplitude / 10, np.random.rand() * self.amplitude)
        self.noise = (np.random.rand(points) - 0.5) * self.noise_amp

    def test_exp_decay(self):
        # Test for exponential decay (stretch == 1)
        y_values = self.noise + self.stretched_exp_decay(self.x_values,
                                                         self.offset,
                                                         self.amplitude,
                                                         self.decay,
                                                         1)

        fit_model = StretchedExponentialDecay()
        guess = fit_model.guess(y_values, self.x_values)
        guess['stretch'].set(vary=False, value=1)
        fit_result = fit_model.fit(data=y_values, x=self.x_values, **guess)

        params_ideal = {'offset': self.offset,
                        'amplitude': self.amplitude,
                        'decay': self.decay}
        for name, ideal_val in params_ideal.items():
            diff = abs(fit_result.best_values[name] - ideal_val)
            tolerance = abs(ideal_val * self._fit_param_tolerance)
            msg = 'Exp. decay fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)

    def test_stretched_exp_decay(self):
        # Test for stretched exponential decay
        y_values = self.noise + self.stretched_exp_decay(self.x_values,
                                                         self.offset,
                                                         self.amplitude,
                                                         self.decay,
                                                         self.stretch)

        fit_model = StretchedExponentialDecay()
        fit_result = fit_model.fit(data=y_values,
                                   x=self.x_values,
                                   **fit_model.guess(y_values, self.x_values))

        params_ideal = {'offset': self.offset,
                        'amplitude': self.amplitude,
                        'decay': self.decay,
                        'stretch': self.stretch}
        for name, ideal_val in params_ideal.items():
            diff = abs(fit_result.best_values[name] - ideal_val)
            tolerance = abs(ideal_val * self._fit_param_tolerance)
            msg = 'Stretched exp. decay fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)


if __name__ == '__main__':
    unittest.main()
