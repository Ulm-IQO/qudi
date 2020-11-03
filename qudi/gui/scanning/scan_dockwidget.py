# -*- coding: utf-8 -*-

"""
This file contains a QDockWidget subclass to display a scanning measurement for given axes.

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

import os
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.gui.qtwidgets.scan_2d_widget import Scan2DWidget
from qudi.core.util.paths import get_artwork_dir

__all__ = ('Scan2DDockWidget',)


class Scan2DDockWidget(QtWidgets.QDockWidget):
    """
    """

    __transparent_crosshair_attrs = frozenset(
        {'sigPositionChanged', 'sigPositionDragged', 'sigDragStarted', 'sigDragFinished'}
    )
    __transparent_widget_attrs = frozenset(
        {'sigMouseClicked', 'sigMouseAreaSelected', 'sigScanToggled', 'use_blink_correction',
         'toggle_blink_correction', 'selection_enabled', 'zoom_by_selection_enabled',
         'toggle_selection', 'toggle_zoom_by_selection', 'set_image_extent', 'toggle_scan',
         'toggle_enabled', 'set_scan_data'}
    )

    def __init__(self, *args, scan_axes, channels, **kwargs):
        x_axis, y_axis = scan_axes

        super().__init__(*args, **kwargs)

        self._axes = (x_axis.name, y_axis.name)

        self.setWindowTitle('{0}-{1} Scan'.format(x_axis.name.title(), y_axis.name.title()))
        self.setObjectName('{0}_{1}_scan_dockWidget'.format(x_axis.name, y_axis.name))

        icon_path = os.path.join(get_artwork_dir(), 'icons', 'qudiTheme', '22x22')
        start_icon_path = os.path.join(icon_path, 'scan-xy-start.png')
        stop_icon_path = os.path.join(icon_path, 'stop-scan.png')
        icon = QtGui.QIcon(start_icon_path)
        icon.addPixmap(QtGui.QPixmap(stop_icon_path), mode=QtGui.QIcon.Normal, state=QtGui.QIcon.On)
        self.scan_widget = Scan2DWidget(channel_units={ch.name: ch.unit for ch in channels},
                                        scan_icon=icon)
        self.scan_widget.set_axis_label('bottom', label=x_axis.name.title(), unit=x_axis.unit)
        self.scan_widget.set_axis_label('left', label=y_axis.name.title(), unit=y_axis.unit)
        self.scan_widget.set_data_channels({ch.name: ch.unit for ch in channels})
        self.scan_widget.add_crosshair(movable=True, min_size_factor=0.02)
        self.scan_widget.crosshairs[-1].set_allowed_range((x_axis.value_range, y_axis.value_range))
        self.scan_widget.toggle_zoom_by_selection(True)

        self.setWidget(self.scan_widget)

    def __getattr__(self, item):
        if item in self.__transparent_crosshair_attrs:
            return getattr(self.scan_widget.crosshairs[-1], item)
        if item in self.__transparent_widget_attrs:
            return getattr(self.scan_widget, item)
        raise AttributeError('Scan2DDockWidget has no attribute "{0}"'.format(item))

    @property
    def axes(self):
        return self._axes

    @property
    def crosshair(self):
        return self.scan_widget.crosshairs[-1]

    def toggle_crosshair(self, enabled):
        if enabled:
            return self.scan_widget.show_crosshair(-1)
        return self.scan_widget.hide_crosshair(-1)
