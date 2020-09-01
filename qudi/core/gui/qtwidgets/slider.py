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

from PySide2 import QtCore, QtWidgets
import numpy as np

__all__ = ['DoubleSlider']


class DoubleSlider(QtWidgets.QSlider):
    """

    """
    doubleValueChanged = QtCore.Signal(float)
    doubleSliderMoved = QtCore.Signal(float)
    doubleRangeChanged = QtCore.Signal(float, float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._step_number = 1000
        self._minimum_value = 0
        self._maximum_value = 1
        super().setRange(0, self._step_number)
        self.valueChanged.connect(self.__translate_value_changed)
        self.sliderMoved.connect(self.__translate_slider_moved)
        self.rangeChanged.connect(self.__translate_range_changed)
        return

    def setMinimum(self, min_val):
        self._minimum_value = float(min_val)
        return

    def setMaximum(self, max_val):
        self._maximum_value = float(max_val)
        return

    def setRange(self, min_val, max_val):
        self._minimum_value = float(min_val)
        self._maximum_value = float(max_val)
        return

    def minimum(self):
        return self._minimum_value

    def maximum(self):
        return self._maximum_value

    def value(self):
        int_val = super().value()
        return self.minimum() + (self.maximum() - self.minimum()) * (int_val / self._step_number)

    def setValue(self, val):
        int_val = round((val - self.minimum()) * self._step_number / (self.maximum() - self.minimum()))
        super().setValue(int_val)
        return

    def set_granularity(self, number_of_steps):
        """
        Set the granularity of the slider, i.e. the number of discrete steps within the value range.

        @param int number_of_steps: The number of discrete positions the slider has
        """
        number_of_steps = int(number_of_steps)
        if number_of_steps < 1:
            raise ValueError('Number of steps must be larger than 0.')
        self._step_number = number_of_steps - 1  # Include 0 as position
        super().setRange(0, self._step_number)
        return

    @QtCore.Slot(int)
    def __translate_value_changed(self, int_val):
        self.doubleValueChanged.emit(
            self.minimum() + (self.maximum() - self.minimum()) * (int_val / self._step_number))
        return

    @QtCore.Slot(int)
    def __translate_slider_moved(self, int_val):
        self.doubleSliderMoved.emit(
            self.minimum() + (self.maximum() - self.minimum()) * (int_val / self._step_number))
        return

    @QtCore.Slot()
    def __translate_range_changed(self):
        self.doubleRangeChanged.emit(self.minimum(), self.maximum())
        return
