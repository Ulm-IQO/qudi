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

from qudi.core.fitting import Sine, DoubleSine


class TestSineMethods(unittest.TestCase):
    _fit_param_tolerance = 0.05  # 5% tolerance for each fit parameter

    @staticmethod
    def sine(x, offset, amplitude, frequency, phase):
        return offset + amplitude * np.sin(2 * np.pi * frequency * x + phase)

    def setUp(self):
        self.offset = (np.random.rand() - 0.5) * 2e6
        self.amplitudes = np.random.rand(3) * 100
        window = max(1e-9, np.random.rand() * 1e9)
        left = (np.random.rand() - 0.5) * 2e9
        points = np.random.randint(10, 1001)
        self.x_values = np.linspace(left, left + window, points)
        max_freq = 0.25 / (self.x_values[1] - self.x_values[0])
        min_freq = 0.5 / window
        self.frequencies = min_freq + np.random.rand(3) * (max_freq - min_freq)
        self.phases = (np.random.rand(3) - 0.5) * 2 * np.pi
        self.noise_amp = max(self.amplitudes.min() / 10, np.random.rand() * self.amplitudes.min())
        self.noise = (np.random.rand(points) - 0.5) * self.noise_amp

    def test_sine(self):
        # Test for sine fit
        y_values = self.noise + self.sine(self.x_values,
                                          self.offset,
                                          self.amplitudes[0],
                                          self.frequencies[0],
                                          self.phases[0])

        fit_model = Sine()
        fit_result = fit_model.fit(data=y_values,
                                   x=self.x_values,
                                   **fit_model.guess(y_values, self.x_values))

        params_ideal = {'offset': self.offset,
                        'amplitude': self.amplitudes[0],
                        'frequency': self.frequencies[0],
                        'phase': self.phases[0]}
        for name, ideal_val in params_ideal.items():
            diff = abs(fit_result.best_values[name] - ideal_val)
            tolerance = abs(ideal_val * self._fit_param_tolerance)
            msg = 'Sine fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)

    def test_double_sine(self):
        # Test for sine fit
        y_values = self.noise + self.sine(self.x_values,
                                          self.offset,
                                          self.amplitudes[0],
                                          self.frequencies[0],
                                          self.phases[0])
        y_values += self.sine(self.x_values,
                              self.offset,
                              self.amplitudes[1],
                              self.frequencies[1],
                              self.phases[1])

        fit_model = DoubleSine()
        fit_result = fit_model.fit(data=y_values,
                                   x=self.x_values,
                                   **fit_model.guess(y_values, self.x_values))

        params_ideal = {'offset': self.offset,
                        'amplitude_1': self.amplitudes[0],
                        'amplitude_2': self.amplitudes[1],
                        'frequency_1': self.frequencies[0],
                        'frequency_2': self.frequencies[0],
                        'phase_1': self.phases[0],
                        'phase_2': self.phases[1]}
        for name, ideal_val in params_ideal.items():
            diff = abs(fit_result.best_values[name] - ideal_val)
            tolerance = abs(ideal_val * self._fit_param_tolerance)
            msg = 'Double sine fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)


if __name__ == '__main__':
    unittest.main()
