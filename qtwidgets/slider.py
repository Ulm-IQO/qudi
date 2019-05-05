# -*- coding: utf-8 -*-

"""
This file contains a wrapper to display the SpinBox in scientific way

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
"""

from qtpy import QtCore, QtWidgets
import numpy as np

__all__ = ['DoubleSlider']


class DoubleSlider(QtWidgets.QSlider):
    """

    """
    valueChanged = QtCore.Signal(float)
    sliderMoved = QtCore.Signal(float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scale_factor = 1
