# -*- coding: utf-8 -*-
"""
This file contains the interface for the sweep points extension for spectrum analyzers.

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

import abc


class SweepPointsExtensionInterface(metaclass=abc.ABCMeta):
    """
    Extension for spectrum analyzers supporting to specify the number of sweep points.
    """
    class sweep_coupling(metaclass=abc.ABCMeta):
        @property
        @abc.abstractmethod
        def sweep_points(self):
            """
            Specifies the number of measured points in each sweep.
            """
            pass

        @sweep_points.setter
        def sweep_points(self, value):
            pass