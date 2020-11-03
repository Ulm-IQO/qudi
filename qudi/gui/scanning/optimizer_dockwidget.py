# -*- coding: utf-8 -*-

"""
This file contains a QDockWidget subclass to display the scanner optimizer results.

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
from PySide2 import QtCore, QtGui, QtWidgets
from pyqtgraph import PlotDataItem, mkPen
from qudi.core.gui.qtwidgets.scan_2d_widget import Scan2DPlotWidget, ScanImageItem
from qudi.core.gui.qtwidgets.scan_1d_widget import Scan1DPlotWidget
from qudi.core.gui.colordefs import QudiPalette

__all__ = ('OptimizerDockWidget',)


class OptimizerDockWidget(QtWidgets.QDockWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Optimizer')
        self.setObjectName('optimizer_dockWidget')

        self.image_item = ScanImageItem()
        self.plot2d_widget = Scan2DPlotWidget()
        self.plot2d_widget.addItem(self.image_item)
        self.plot2d_widget.toggle_zoom_by_selection(False)
        self.plot2d_widget.toggle_selection(False)
        self.plot2d_widget.add_crosshair(movable=False, pen={'color': '#00ff00', 'width': 2})
        self.plot2d_widget.setAspectLocked(lock=True, ratio=1.0)
        self.plot2d_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.plot_item = PlotDataItem(pen=mkPen(QudiPalette.c1, style=QtCore.Qt.DotLine),
                                      symbol='o',
                                      symbolPen=QudiPalette.c1,
                                      symbolBrush=QudiPalette.c1,
                                      symbolSize=7)
        self.fit_plot_item = PlotDataItem(pen=mkPen(QudiPalette.c2))
        self.plot1d_widget = Scan1DPlotWidget()
        self.plot1d_widget.addItem(self.plot_item)
        self.plot1d_widget.add_marker(movable=False, pen={'color': '#00ff00', 'width': 2})
        self.plot1d_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        label = QtWidgets.QLabel('(x, y, z):')
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.result_label = QtWidgets.QLabel('(?, ?, ?)')
        self.result_label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(label)
        label_layout.addWidget(self.result_label)
        label_layout.setStretch(1, 1)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.plot2d_widget, 0, 0)
        layout.addWidget(self.plot1d_widget, 0, 1)
        layout.addLayout(label_layout, 1, 0, 1, 2)
        layout.setRowStretch(0, 1)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

    @property
    def crosshair(self):
        return self.plot2d_widget.crosshairs[-1]

    @property
    def marker(self):
        return self.plot1d_widget.markers[-1]

    def set_2d_position(self, pos):
        self.crosshair.set_position(pos)

    def set_1d_position(self, pos):
        self.marker.set_position(pos)

    def set_image(self, image, extent=None):
        self.image_item.set_image(image=image)
        if extent is not None:
            self.image_item.set_image_extent(extent)

    def set_plot_data(self, x=None, y=None):
        if x is None and y is None:
            self.plot_item.clear()
            return
        elif x is None:
            x = self.plot_item.xData
            if x is None or len(x) != len(y):
                x = np.arange(len(y))
        elif y is None:
            y = self.plot_item.yData
            if y is None or len(x) != len(y):
                y = np.zeros(len(x))

        nan_mask = np.isnan(y)
        if nan_mask.all():
            self.plot_item.clear()
        else:
            self.plot_item.setData(x=x[~nan_mask], y=y[~nan_mask])
        return

    def set_fit_data(self, x=None, y=None):
        if x is None and y is None:
            self.fit_plot_item.clear()
            return
        elif x is None:
            x = self.fit_plot_item.xData
            if x is None or len(x) != len(y):
                x = np.arange(len(y))
        elif y is None:
            y = self.fit_plot_item.yData
            if y is None or len(x) != len(y):
                y = np.zeros(len(x))

        self.fit_plot_item.setData(x=x, y=y)
        return

    def set_image_label(self, axis, text=None, units=None):
        self.plot2d_widget.setLabel(axis=axis, text=text, units=units)

    def set_plot_label(self, axis, text=None, units=None):
        self.plot1d_widget.setLabel(axis=axis, text=text, units=units)


