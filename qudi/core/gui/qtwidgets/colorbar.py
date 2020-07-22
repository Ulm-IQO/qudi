# -*- coding: utf-8 -*-

"""
This file contains a custom Colorbar Widget to be used with pyqtgraph.ImageItem or qudi
ScanImageItem.

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
from enum import Enum
from pyqtgraph import mkPen, mkBrush, GraphicsObject, PlotWidget, BarGraphItem, mkColor
from qtpy import QtCore, QtGui, QtWidgets
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.gui.colordefs import ColorScaleInferno

__all__ = ('ColorBarMode', 'ColorBarWidget')


class ColorBarMode(Enum):
    ABSOLUTE = 0
    PERCENTILE = 1


class ColorBarItem(BarGraphItem):
    def __init__(self, parent=None, limits=(0, 1), cmap=None, pen=None):
        limits = (float(min(limits)), float(max(limits)))
        cmap = ColorScaleInferno().colormap if cmap is None else cmap
        pen = mkPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen)) if pen is None else mkPen(pen)
        grad = QtGui.QLinearGradient(0, 0, 0, 1)
        grad.setCoordinateMode(QtGui.QGradient.ObjectMode)
        for stop, color in zip(*cmap.getStops('float')):
            grad.setColorAt(stop, QtGui.QColor(*color))
        brush = mkBrush(QtGui.QBrush(grad))
        height = abs(limits[1] - limits[0])
        super().__init__(parent=parent,
                         x=[0],
                         y=[limits[0] + height / 2],
                         height=[height],
                         width=1.5,
                         brush=brush,
                         pen=pen)

    def set_limits(self, min_val, max_val):
        if max_val < min_val:
            min_val, max_val = max_val, min_val
        height = abs(max_val - min_val)
        self.setOpts(y=[min_val + height / 2], height=[height])


class ColorBarWidget(QtWidgets.QWidget):
    """ A widget containing a controllable colorbar for color-coded plots.
    """

    sigLimitsChanged = QtCore.Signal(tuple)  # (min_val, max_val)
    sigPercentilesChanged = QtCore.Signal(tuple)  # (low_percentile, high_percentile)
    sigModeChanged = QtCore.Signal(object)

    def __init__(self, *args, unit=None, label=None, absolute_range=None, percentile_range=None,
                 mode=ColorBarMode.PERCENTILE, **kwargs):
        super().__init__(*args, **kwargs)

        self.min_spinbox = ScienDSpinBox()
        self.min_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Fixed)
        self.min_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.min_spinbox.setMinimumWidth(75)
        self.min_spinbox.setValue(0)
        self.max_spinbox = ScienDSpinBox()
        self.max_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Fixed)
        self.max_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.min_spinbox.setMinimumWidth(75)
        self.max_spinbox.setValue(1)
        self.low_percentile_spinbox = ScienDSpinBox()
        self.low_percentile_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                  QtWidgets.QSizePolicy.Fixed)
        self.low_percentile_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.low_percentile_spinbox.setMinimumWidth(75)
        self.low_percentile_spinbox.setSuffix('%')
        self.low_percentile_spinbox.setValue(0)
        self.high_percentile_spinbox = ScienDSpinBox()
        self.high_percentile_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                   QtWidgets.QSizePolicy.Fixed)
        self.high_percentile_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.high_percentile_spinbox.setMinimumWidth(75)
        self.high_percentile_spinbox.setSuffix('%')
        self.high_percentile_spinbox.setValue(100)
        if unit is not None:
            self.max_spinbox.setSuffix(unit)
            self.min_spinbox.setSuffix(unit)
        if absolute_range is not None:
            self.min_spinbox.setRange(*absolute_range)
            self.max_spinbox.setRange(*absolute_range)
        if percentile_range is not None:
            min_percentile = percentile_range[0] if 0 <= percentile_range[0] <= 100 else 0
            max_percentile = percentile_range[1] if 0 <= percentile_range[1] <= 100 else 0
            self.low_percentile_spinbox.setRange(min_percentile, max_percentile)
            self.high_percentile_spinbox.setRange(min_percentile, max_percentile)
        else:
            self.low_percentile_spinbox.setRange(0, 100)
            self.high_percentile_spinbox.setRange(0, 100)

        grad = QtGui.QLinearGradient(0, 0, 0, 1)
        grad.setCoordinateMode(QtGui.QGradient.ObjectMode)
        for stop, color in zip(*ColorScaleInferno().colormap.getStops('float')):
            grad.setColorAt(stop, QtGui.QColor(*color))
        self._cb_brush = mkBrush(QtGui.QBrush(grad))

        self.colorbar = ColorBarItem()
        self.cb_plot_widget = PlotWidget()
        self.cb_plot_widget.hideButtons()
        self.cb_plot_widget.setMinimumWidth(75)
        self.cb_plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.cb_plot_widget.addItem(self.colorbar)
        self.cb_plot_widget.hideAxis('bottom')
        self.cb_plot_widget.setLabel('left', text=label, units=unit)
        self.cb_plot_widget.setMouseEnabled(x=False, y=False)
        self.cb_plot_widget.disableAutoRange()
        self.cb_plot_widget.setYRange(0, 1)
        self.cb_plot_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.absolute_radioButton = QtWidgets.QRadioButton('Absolute')
        self.absolute_radioButton.setAutoExclusive(True)
        self.percentile_radioButton = QtWidgets.QRadioButton('Percentile')
        self.percentile_radioButton.setAutoExclusive(True)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.max_spinbox)
        main_layout.addWidget(self.high_percentile_spinbox)
        main_layout.addWidget(self.cb_plot_widget)
        main_layout.addWidget(self.low_percentile_spinbox)
        main_layout.addWidget(self.min_spinbox)
        main_layout.addWidget(self.absolute_radioButton)
        main_layout.addWidget(self.percentile_radioButton)

        if mode is ColorBarMode.ABSOLUTE:
            self.absolute_radioButton.setChecked(True)
        else:
            self.percentile_radioButton.setChecked(True)

        # main_layout.setSpacing(0)
        main_layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(main_layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        # Connect signals
        self.min_spinbox.valueChanged.connect(self._absolute_value_changed)
        self.max_spinbox.valueChanged.connect(self._absolute_value_changed)
        self.low_percentile_spinbox.valueChanged.connect(self._percentile_value_changed)
        self.high_percentile_spinbox.valueChanged.connect(self._percentile_value_changed)
        self.percentile_radioButton.toggled.connect(self._mode_changed)
        self.absolute_radioButton.toggled.connect(self._mode_changed)
        return

    @property
    def mode(self):
        if self.absolute_radioButton.isChecked():
            return ColorBarMode.ABSOLUTE
        return ColorBarMode.PERCENTILE

    @property
    def limits(self):
        return self.min_spinbox.value(), self.max_spinbox.value()

    @property
    def percentiles(self):
        return self.low_percentile_spinbox.value(), self.high_percentile_spinbox.value()

    # FIXME: Remove?
    def sizeHint(self):
        return QtCore.QSize(90, 100)

    def set_label(self, text, unit=None):
        if unit is not None:
            self.max_spinbox.setSuffix(unit)
            self.min_spinbox.setSuffix(unit)
        return self.cb_plot_widget.setLabel('left', text=text, units=unit)

    def set_colormap(self, cmap=None):
        return self.colorbar.set_cmap(cmap=cmap)

    def set_pen(self, pen=None):
        return self.colorbar.set_pen(pen)

    @QtCore.Slot(float, float)
    @QtCore.Slot(float, float, float, float)
    def set_limits(self, min_value, max_value, low_percentile=None, high_percentile=None):
        # Check and set percentile values in spinboxes
        if (low_percentile is None) != (high_percentile is None):
            raise ValueError('If percentile ranges should be changed, you must specify both low '
                             'and high percentile values.')
        elif low_percentile is not None:
            self.low_percentile_spinbox.blockSignals(True)
            self.high_percentile_spinbox.blockSignals(True)
            self.low_percentile_spinbox.setValue(low_percentile)
            self.high_percentile_spinbox.setValue(high_percentile)
            self.low_percentile_spinbox.blockSignals(False)
            self.high_percentile_spinbox.blockSignals(False)

        # Set absolute values in spinboxes and update colorbar
        self.min_spinbox.blockSignals(True)
        self.max_spinbox.blockSignals(True)
        self.min_spinbox.setValue(min_value)
        self.max_spinbox.setValue(max_value)
        min_val = self.min_spinbox.value()
        max_val = self.max_spinbox.value()
        self.colorbar.set_limits(min_val, max_val)
        self.cb_plot_widget.setYRange(min_val, max_val)

        self.min_spinbox.blockSignals(False)
        self.max_spinbox.blockSignals(False)

    @QtCore.Slot(object)
    def set_mode(self, mode):
        if not isinstance(mode, ColorBarMode):
            raise TypeError('mode must be ColorBarMode enum.')
        if mode is ColorBarMode.ABSOLUTE:
            self.absolute_radioButton.setChecked(True)
        else:
            self.percentile_radioButton.setChecked(True)
        return

    @QtCore.Slot()
    def _absolute_value_changed(self):
        min_val = self.min_spinbox.value()
        max_val = self.max_spinbox.value()
        self.colorbar.set_limits(min_val, max_val)
        self.cb_plot_widget.setYRange(min_val, max_val)
        if not self.absolute_radioButton.isChecked():
            self.absolute_radioButton.setChecked(True)
            self.sigModeChanged.emit(ColorBarMode.ABSOLUTE)
        self.sigLimitsChanged.emit((min_val, max_val))
        return

    @QtCore.Slot()
    def _percentile_value_changed(self):
        if not self.percentile_radioButton.isChecked():
            self.percentile_radioButton.setChecked(True)
            self.sigModeChanged.emit(ColorBarMode.PERCENTILE)
        self.sigPercentilesChanged.emit((self.low_percentile_spinbox.value(),
                                         self.high_percentile_spinbox.value()))
        return

    @QtCore.Slot()
    def _mode_changed(self):
        if self.absolute_radioButton.isChecked():
            self.sigModeChanged.emit(ColorBarMode.ABSOLUTE)
        else:
            self.sigModeChanged.emit(ColorBarMode.PERCENTILE)
        return
