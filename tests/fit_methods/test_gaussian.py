# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines for Gaussian peak/dip models.

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

from qudi.util.fit_models.gaussian import Gaussian


class TestGaussianMethods(unittest.TestCase):
    _fit_param_tolerance = 0.05  # 5% tolerance for each fit parameter

    @staticmethod
    def gaussian(x, offset, amplitude, center, sigma):
        return offset + amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))

    def setUp(self):
        self.offset = (np.random.rand() - 0.5) * 2e6
        self.amplitude = np.random.rand() * 100
        window = max(1e-9, np.random.rand() * 1e9)
        left = (np.random.rand() - 0.5) * 2e9
        points = np.random.randint(10, 1001)
        self.x_values = np.linspace(left, left + window, points)
        min_sigma = 1.5 * (self.x_values[1] - self.x_values[0])
        self.sigma = min_sigma + np.random.rand() * ((window / 2) - min_sigma)
        self.center = left + np.random.rand() * window
        self.noise_amp = max(self.amplitude / 10, np.random.rand() * self.amplitude)
        self.noise = (np.random.rand(points) - 0.5) * self.noise_amp

    def test_gaussian(self):
        # Test for gaussian peak
        y_values = self.noise + self.gaussian(self.x_values,
                                              self.offset,
                                              self.amplitude,
                                              self.center,
                                              self.sigma)
        y_values += (np.random.rand(len(y_values)) - 0.5) * self.noise_amp

        fit_model = Gaussian()
        fit_result = fit_model.fit(data=y_values,
                                   x=self.x_values,
                                   **fit_model.guess(y_values, self.x_values))

        params_ideal = {'offset': self.offset,
                        'amplitude': self.amplitude,
                        'center': self.center,
                        'sigma': self.sigma}
        for name, fit_param in fit_result.best_values.items():
            diff = abs(fit_param - params_ideal[name])
            tolerance = abs(params_ideal[name] * self._fit_param_tolerance)
            msg = 'Gaussian peak fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)

        # Test for gaussian dip
        y_values = self.noise + self.gaussian(self.x_values,
                                              self.offset,
                                              -self.amplitude,
                                              self.center,
                                              self.sigma)

        fit_model = Gaussian()
        fit_result = fit_model.fit(data=y_values,
                                   x=self.x_values,
                                   **fit_model.guess(y_values, self.x_values))

        params_ideal['amplitude'] = -self.amplitude
        for name, fit_param in fit_result.best_values.items():
            diff = abs(fit_param - params_ideal[name])
            tolerance = abs(params_ideal[name] * self._fit_param_tolerance)
            msg = 'Gaussian dip fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)


if __name__ == '__main__':
    unittest.main()
