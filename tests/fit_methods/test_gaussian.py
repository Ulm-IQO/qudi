# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines.

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

from qudi.core.fitting import Gaussian


class TestGaussianMethods(unittest.TestCase):
    @staticmethod
    def gaussian(x, offset, amplitude, center, sigma):
        return offset + amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))

    def setUp(self):
        self.offset = (np.random.rand() - 0.5) * 2e6
        self.amplitude = (np.random.rand() - 0.5) * 200
        window = max(1e-9, np.random.rand() * 1e9)
        left = (np.random.rand() - 0.5) * 2e9
        points = np.random.randint(10, 1001)
        self.x_values = np.linspace(left, left + window, points)
        min_sigma = 1.5 * (self.x_values[1] - self.x_values[0])
        self.sigma = min_sigma + np.random.rand() * ((window / 2) - min_sigma)
        self.center = left + np.random.rand() * window
        self.noise_amp = max(self.amplitude / 10, np.random.rand() * (2 * self.amplitude))

    def test_gaussian(self):
        y_values = self.gaussian(self.x_values,
                                 self.offset,
                                 self.amplitude,
                                 self.center,
                                 self.sigma)
        fit_result = Gaussian().fit(y_values, x=self.x_values)
        print(fit_result.fit_report())
        self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")

    def test_sum_tuple(self):
        self.assertEqual(sum((1, 2, 2)), 6, "Should be 6")


if __name__ == '__main__':
    unittest.main()