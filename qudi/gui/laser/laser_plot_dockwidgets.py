# -*- coding: utf-8 -*-

"""
This file contains QDockWidget subclasses to display time series data in the laser GUI.

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

__all__ = ('LaserOutputDockWidget', 'LaserTemperatureDockWidget')

import time
import pyqtgraph as pg
from PySide2 import QtCore

from qudi.util.colordefs import QudiPalettePale as palette
from qudi.util.widgets.advanced_dockwidget import AdvancedDockWidget


class LaserOutputDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot_widget.setLabel('bottom', 'Time', units=None)
        self.plot_widget.setLabel('left', 'Power', units='W', color=palette.c1.name())
        self.plot_widget.setLabel('right', 'Current', color=palette.c3.name())
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMouseTracking(False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()
        self.plot_widget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.plot_widget.setMinimumSize(200, 200)
        # Create second ViewBox to plot with two independent y-axes
        self.view_box2 = pg.ViewBox()
        self.plot_widget.scene().addItem(self.view_box2)
        self.plot_widget.getAxis('right').linkToView(self.view_box2)
        self.view_box2.setXLink(self.plot_widget)
        self.view_box2.setMouseEnabled(x=False, y=False)
        self.view_box2.setMenuEnabled(False)
        # Sync resize events
        self.plot_widget.plotItem.vb.sigResized.connect(self.__update_viewbox_sync)
        # Create plot data items
        self.power_data_item = pg.PlotCurveItem(pen=pg.mkPen(palette.c1, cosmetic=True),
                                                antialias=True)
        self.current_data_item = pg.PlotCurveItem(pen=pg.mkPen(palette.c3, cosmetic=True),
                                                  antialias=True)
        self.setWidget(self.plot_widget)
        self.plot_widget.getPlotItem().setContentsMargins(0, 1, 5, 2)

    @QtCore.Slot()
    def __update_viewbox_sync(self):
        """ Helper method to sync plots for both y-axes.
        """
        self.view_box2.setGeometry(self.plot_widget.plotItem.vb.sceneBoundingRect())
        self.view_box2.linkedViewChanged(self.plot_widget.plotItem.vb, self.view_box2.XAxis)

    def set_power_data(self, y, x=None):
        if y is None:
            if self.power_data_item in self.plot_widget.items():
                self.plot_widget.removeItem(self.power_data_item)
        else:
            self.power_data_item.setData(y=y, x=x)
            if self.power_data_item not in self.plot_widget.items():
                self.plot_widget.addItem(self.power_data_item)

    def set_current_data(self, y, x=None):
        if y is None:
            if self.current_data_item in self.view_box2.addedItems:
                self.view_box2.removeItem(self.current_data_item)
        else:
            self.current_data_item.setData(y=y, x=x)
            if self.current_data_item not in self.view_box2.addedItems:
                self.view_box2.addItem(self.current_data_item)


class LaserTemperatureDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, curve_names, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot_widget.setLabel('bottom', 'Time', units=None)
        self.plot_widget.setLabel('left', 'Temperature', units='°C', color=palette.c1.name())
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMouseTracking(False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()
        self.plot_widget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.plot_widget.setMinimumSize(200, 200)
        self.temperature_data_items = dict()
        for ii, name in enumerate(curve_names):
            color = getattr(palette, 'c{0:d}'.format((ii % 6) + 1))
            self.temperature_data_items[name] = pg.PlotCurveItem(pen=pg.mkPen(color, cosmetic=True),
                                                                 antialias=True)
            self.plot_widget.addItem(self.temperature_data_items[name])
        self.setWidget(self.plot_widget)
        self.plot_widget.getPlotItem().setContentsMargins(0, 1, 5, 2)

    def set_temperature_data(self, temp_dict, x=None):
        for name, y_data in temp_dict.items():
            item = self.temperature_data_items[name]
            if y_data is None:
                if item in self.plot_widget.items():
                    self.plot_widget.removeItem(item)
            else:
                item.setData(y=y_data, x=x)
                if item not in self.plot_widget.items():
                    self.plot_widget.addItem(item)


class TimeAxisItem(pg.AxisItem):
    """ pyqtgraph AxisItem that shows a HH:MM:SS timestamp on ticks.
        X-Axis must be formatted as (floating point) Unix time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """ Hours:Minutes:Seconds string from float unix timestamp. """
        return [time.strftime("%H:%M:%S", time.localtime(value)) for value in values]
