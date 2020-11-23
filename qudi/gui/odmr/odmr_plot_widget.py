# -*- coding: utf-8 -*-

"""
This file contains a custom QWidget subclass to be used in the ODMR GUI module.

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

import pyqtgraph as pg
from PySide2 import QtCore, QtWidgets

from qudi.core.gui.qtwidgets.scan_2d_widget import ScanImageItem
from qudi.core.gui.qtwidgets.colorbar import ColorBarWidget, ColorBarMode
from qudi.core.gui.colordefs import QudiPalettePale as palette

__all__ = ('OdmrPlotWidget',)


class OdmrPlotWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, data_channel_units, **kwargs):
        super().__init__(*args, **kwargs)

        main_layout = QtWidgets.QGridLayout()
        main_layout.setColumnStretch(0, 1)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # Create data channel and range index selectors
        layout = QtWidgets.QHBoxLayout()
        layout.addStretch(1)
        label = QtWidgets.QLabel('Data Channel:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        self._data_channel_combobox = QtWidgets.QComboBox()
        self._data_channel_combobox.addItems(tuple(data_channel_units))
        self._data_channel_combobox.currentIndexChanged.connect(self._channel_changed)
        layout.addWidget(self._data_channel_combobox)
        label = QtWidgets.QLabel('Range Index:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        self._range_index_spinbox = QtWidgets.QSpinBox()
        self._range_index_spinbox.setRange(0, 0)
        self._range_index_spinbox.valueChanged.connect(self._range_changed)
        main_layout.addLayout(layout, 0, 0)

        # Create data plot
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.getPlotItem().setContentsMargins(0, 1, 5, 2)
        self._data_item = pg.PlotDataItem(pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)
        self._fit_data_item = pg.PlotDataItem(pen=pg.mkPen(palette.c2))
        self._plot_widget.addItem(self._data_item)
        self._plot_widget.setMinimumWidth(100)
        self._plot_widget.setMinimumHeight(100)
        self._plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Expanding)
        self._plot_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._plot_widget.setLabel('bottom', text='Frequency', units='Hz')
        self._plot_widget.setLabel('left', text='Signal')
        self._plot_widget.showGrid(x=True, y=True)
        main_layout.addWidget(self._plot_widget, 1, 0)

        # Create matrix plot
        self._image_widget = pg.PlotWidget()
        self._image_widget.getPlotItem().setContentsMargins(0, 1, 5, 2)
        self._image_item = ScanImageItem()
        self._image_widget.addItem(self._image_item)
        self._image_widget.setMinimumWidth(100)
        self._image_widget.setMinimumHeight(100)
        self._image_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Expanding)
        self._image_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        # self._image_widget.setAspectLocked(lock=True, ratio=1.0)
        self._image_widget.setLabel('bottom', text='Frequency', units='Hz')
        self._image_widget.setLabel('left', text='Scan Line')
        main_layout.addWidget(self._image_widget, 2, 0)

        # Create colorbar
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._range_index_spinbox)
        self._colorbar = ColorBarWidget()
        self._colorbar.set_label(text='Signal', unit='P')
        self._colorbar.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        if self._colorbar.mode is ColorBarMode.PERCENTILE:
            self._image_item.percentiles = self._colorbar.percentiles
        else:
            self._image_item.percentiles = None
        self._colorbar.sigModeChanged.connect(self._colorbar_mode_changed)
        self._colorbar.sigLimitsChanged.connect(self._colorbar_limits_changed)
        self._colorbar.sigPercentilesChanged.connect(self._colorbar_percentiles_changed)
        layout.addWidget(self._colorbar)
        main_layout.addLayout(layout, 0, 1, 3, 1)

        # Remember channel units
        self._channel_units = data_channel_units.copy()
        # Data buffers for plot data
        self._plot_data = None
        self._fit_data = None
        self._image_data = None
        self._frequency_data = None

    def set_data(self, image=None, signal=None, fit=None):
        channel = self._data_channel_combobox.currentText()
        range_index = self._range_index_spinbox.value()
        if image is not None:
            self._image_data = image.copy()
            self._update_image_data(channel, range_index)
        if signal is not None:
            self._plot_data = signal.copy()
            self._update_plot_data(channel, range_index)
        if fit is not None:
            self._fit_data = fit.copy()
            self._update_fit_data(channel, range_index)

    def set_frequency_data(self, data):
        self._frequency_data = None if data is None else data.copy()
        # Clear all old data
        self._plot_data = None
        self._fit_data = None
        self._image_data = None
        # Adjust index spinbox range
        self._range_index_spinbox.setMaximum(0 if data is None else len(data))

    def _update_signal_label(self, channel):
        unit = self._channel_units.get(channel, '')
        self._plot_widget.setLabel('left', text=channel, units=unit)
        self._colorbar.set_label(text=channel, unit=unit)

    def _update_image_data(self, channel, range_index):
        if self._image_data is None:
            return
        image_list = self._image_data.get(channel, None)
        if image_list is None:
            self._image_item.clear()
        else:
            image = image_list[range_index]
            if self._colorbar.mode is ColorBarMode.PERCENTILE:
                self._image_item.set_image(image=image, autoLevels=False)
                levels = self._image_item.levels
                if levels is not None:
                    self._colorbar.set_limits(*levels)
            else:
                self._image_item.set_image(image=image,
                                           autoLevels=False,
                                           levels=self._colorbar.limits)
            frequencies = self._frequency_data[range_index]
            self._image_item.set_image_extent(((frequencies[0], frequencies[-1]), (0, 1)))

    def _update_plot_data(self, channel, range_index):
        if self._plot_data is None:
            return
        data_list = self._plot_data.get(channel, None)
        if data_list is None:
            self._data_item.clear()
        else:
            self._data_item.setData(y=data_list[range_index])

    def _update_fit_data(self, channel, range_index):
        if self._fit_data is None:
            return
        fit_list = self._fit_data.get(channel, None)
        if fit_list is None:
            self._fit_data_item.clear()
        else:
            self._fit_data_item.setData(y=fit_list[range_index])

    @QtCore.Slot()
    def _channel_changed(self):
        channel = self._data_channel_combobox.currentText()
        range_index = self._range_index_spinbox.value()
        self._update_signal_label(channel)
        self._update_image_data(channel, range_index)
        self._update_plot_data(channel, range_index)
        self._update_fit_data(channel, range_index)

    @QtCore.Slot()
    def _range_changed(self):
        channel = self._data_channel_combobox.currentText()
        range_index = self._range_index_spinbox.value()
        self._update_image_data(channel, range_index)
        self._update_plot_data(channel, range_index)
        self._update_fit_data(channel, range_index)

    @QtCore.Slot(object)
    def _colorbar_mode_changed(self, mode):
        if mode is ColorBarMode.PERCENTILE:
            self._colorbar_percentiles_changed(self._colorbar.percentiles)
        else:
            self._colorbar_limits_changed(self._colorbar.limits)

    @QtCore.Slot(tuple)
    def _colorbar_limits_changed(self, limits):
        self._image_item.percentiles = None
        self._image_item.setLevels(limits)

    @QtCore.Slot(tuple)
    def _colorbar_percentiles_changed(self, percentiles):
        self._image_item.percentiles = percentiles
        levels = self._image_item.levels
        if levels is not None:
            self._colorbar.set_limits(*levels)
