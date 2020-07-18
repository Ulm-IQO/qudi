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
from pyqtgraph import mkPen, mkBrush, GraphicsObject, PlotWidget
from qtpy import QtCore, QtGui, QtWidgets
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.gui.colordefs import ColorScaleInferno

__all__ = ['ColorBarWidget']


class ColorBarItem(GraphicsObject):
    def __init__(self, min_val=0, max_val=1, cmap=None, pen=None):
        """
        Graphics object to draw a colorbar inside a pyqtgraph PlotWidget
        """
        super().__init__()
        self._min_val = float(min_val)
        self._max_val = float(max_val)
        self._cmap = ColorScaleInferno().cmap_normed if cmap is None else cmap
        self._pen = mkPen('k') if pen is None else mkPen(pen)
        self._brush = None
        self._shape = None
        self._picture = None
        self._set_brush()
        self.update()
        self.informViewBoundsChanged()

    def _set_brush(self):
        grad = QtGui.QLinearGradient(0, self._min_val, 0, self._max_val)
        for stop, color in zip(*self._cmap.getStops('float')):
            grad.setColorAt(1.0 - stop, QtGui.QColor(*[255 * c for c in color]))
        self._brush = mkBrush(QtGui.QBrush(grad))
        return

    def set_range(self, min_val, max_val):
        self._min_val = float(min_val)
        self._max_val = float(max_val)
        self._set_brush()
        self.draw_picture()
        self.informViewBoundsChanged()

    def set_cmap(self, cmap=None):
        self._cmap = ColorScaleInferno().cmap_normed if cmap is None else cmap
        self._set_brush()
        self.draw_picture()
        return

    def set_pen(self, pen=None):
        self._pen = mkPen('k') if pen is None else mkPen(pen)
        self.draw_picture()
        return

    def draw_picture(self):
        self._picture = QtGui.QPicture()
        self._shape = QtGui.QPainterPath()
        p = QtGui.QPainter(self._picture)
        p.setPen(self._pen)
        p.setBrush(self._brush)
        rect = QtCore.QRectF(0, self._min_val, 1.0, self._max_val - self._min_val)
        p.drawRect(rect)
        self._shape.addRect(rect)
        p.end()
        self.prepareGeometryChange()
        return

    def paint(self, p, *args):
        if self._picture is None:
            self.draw_picture()
        self._picture.play(p)

    def boundingRect(self):
        if self._picture is None:
            self.draw_picture()
        return QtCore.QRectF(self._picture.boundingRect())

    def shape(self):
        if self._picture is None:
            self.draw_picture()
        return self._shape


class ColorBarWidget(QtWidgets.QWidget):
    """
    A widget containing a controllable colorbar which can be attached to an pyqtgraph ImageItem or
    qudi ScanImageItem to synchronize the colorscale.
    """

    sigRangeChanged = QtCore.Signal(float, float)  # min_val, max_val

    def __init__(self, parent=None, unit=None, label=None, image_item=None):
        super().__init__(parent)
        self._image_item = image_item
        self._image_data = None

        self.min_spinbox = ScienDSpinBox()
        self.min_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Fixed)
        self.min_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.min_spinbox.setMinimumWidth(75)
        self.min_spinbox.setMinimum(0)
        self.min_spinbox.setValue(0)
        self.max_spinbox = ScienDSpinBox()
        self.max_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Fixed)
        self.max_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.min_spinbox.setMinimumWidth(75)
        self.max_spinbox.setMinimum(0)
        self.max_spinbox.setValue(100)
        self.low_percentile_spinbox = ScienDSpinBox()
        self.low_percentile_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                  QtWidgets.QSizePolicy.Fixed)
        self.low_percentile_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.low_percentile_spinbox.setMinimumWidth(75)
        self.low_percentile_spinbox.setRange(0, 100)
        self.low_percentile_spinbox.setSuffix('%')
        self.low_percentile_spinbox.setValue(0)
        self.high_percentile_spinbox = ScienDSpinBox()
        self.high_percentile_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                   QtWidgets.QSizePolicy.Fixed)
        self.high_percentile_spinbox.setAlignment(QtCore.Qt.AlignRight)
        self.high_percentile_spinbox.setMinimumWidth(75)
        self.high_percentile_spinbox.setRange(0, 100)
        self.high_percentile_spinbox.setSuffix('%')
        self.high_percentile_spinbox.setValue(100)
        if unit is not None:
            self.max_spinbox.setSuffix(unit)
            self.min_spinbox.setSuffix(unit)

        self.colorbar = ColorBarItem()
        self.cb_plot_widget = PlotWidget()
        self.cb_plot_widget.setMinimumWidth(75)
        self.cb_plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.cb_plot_widget.addItem(self.colorbar)
        self.cb_plot_widget.hideAxis('bottom')
        self.cb_plot_widget.setLabel('left', text=label, units=unit)
        self.cb_plot_widget.setMouseEnabled(x=False, y=False)

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
        self.percentile_radioButton.toggled.connect(self.refresh_colorscale)
        self.absolute_radioButton.toggled.connect(self.refresh_colorscale)
        if self._image_item is not None:
            try:
                self._image_item.sigImageDataChanged.connect(self.image_data_changed)
            except AttributeError:
                pass
        return

    def sizeHint(self):
        return QtCore.QSize(90, 100)

    def set_label(self, text, unit=None):
        self.cb_plot_widget.setLabel('left', text=text, units=unit)
        if unit is not None:
            self.max_spinbox.setSuffix(unit)
            self.min_spinbox.setSuffix(unit)
        return

    def assign_image_item(self, item=None):
        if self._image_item is not None:
            try:
                self._image_item.sigImageChanged.disconnect()
            except (AttributeError, TypeError):
                pass
        self._image_item = item
        if self._image_item is not None:
            try:
                self._image_item.sigImageDataChanged.connect(self.image_data_changed)
            except AttributeError:
                pass
        return

    def set_colormap(self, cmap=None):
        self.colorbar.set_cmap(cmap=cmap)
        return

    def set_pen(self, pen=None):
        self.colorbar.set_pen(pen)
        return

    def image_data_changed(self, image):
        self._image_data = image
        self.refresh_colorscale()
        return

    @QtCore.Slot()
    @QtCore.Slot(bool)
    def refresh_colorscale(self, update=True, image=None):
        if image is not None:
            self._image_data = image
        if not update:
            return
        # Get absolute data ranges for the colorbar
        if self.percentile_radioButton.isChecked():
            if self._image_data is None:
                return
            data = self._image_data[np.nonzero(self._image_data)]
            if data.size == 0:
                return
            low_centile = self.low_percentile_spinbox.value()
            high_centile = self.high_percentile_spinbox.value()
            cb_min = np.percentile(data, low_centile)
            cb_max = np.percentile(data, high_centile)
        else:
            cb_min = self.min_spinbox.value()
            cb_max = self.max_spinbox.value()

        # Adjust colorbar
        self.colorbar.set_range(cb_min, cb_max)
        # Adjust image color
        if self._image_item is not None:
            self._image_item.setLevels((cb_min, cb_max))
        self.sigRangeChanged.emit(cb_min, cb_max)
        return

    @QtCore.Slot()
    def _absolute_value_changed(self):
        if self.absolute_radioButton.isChecked():
            self.refresh_colorscale()
        else:
            self.absolute_radioButton.setChecked(True)
        return

    @QtCore.Slot()
    def _percentile_value_changed(self):
        if self.percentile_radioButton.isChecked():
            self.refresh_colorscale()
        else:
            self.percentile_radioButton.setChecked(True)
        return
