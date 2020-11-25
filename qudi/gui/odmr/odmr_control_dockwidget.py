# -*- coding: utf-8 -*-

"""
This file contains a custom QDockWidget subclass to be used in the ODMR GUI module.

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

from PySide2 import QtCore, QtWidgets, QtGui

from qudi.core.gui.qtwidgets.advanced_dockwidget import AdvancedDockWidget
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox

__all__ = ('OdmrCwControlDockWidget', 'OdmrScanControlDockWidget')

# Determine minimal spinbox width from current default metrics
_min_spinbox_width = QtGui.QFontMetrics(ScienDSpinBox().font()).width('   -000.000000 GHz   ')


class OdmrCwControlDockWidget(AdvancedDockWidget):
    """

    """
    sigCwParametersChanged = QtCore.Signal(float, float)

    def __init__(self, *args, power_range=None, frequency_range=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ODMR CW Control')

        # create central widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setStretch(1, 1)
        main_layout.setStretch(3, 1)
        main_widget.setLayout(main_layout)
        main_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setWidget(main_widget)

        # create CW parameter spinboxes
        label = QtWidgets.QLabel('CW Power:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        main_layout.addWidget(label)
        self.cw_power_spinbox = ScienDSpinBox()
        self.cw_power_spinbox.setMinimumWidth(_min_spinbox_width)
        self.cw_power_spinbox.setDecimals(6)
        self.cw_power_spinbox.setSuffix('dBm')
        self.cw_power_spinbox.valueChanged.connect(self._cw_parameters_changed_cb)
        if power_range is not None:
            self.cw_power_spinbox.setRange(*power_range)
        main_layout.addWidget(self.cw_power_spinbox)
        label = QtWidgets.QLabel('CW Frequency:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        main_layout.addWidget(label)
        self.cw_frequency_spinbox = ScienDSpinBox()
        self.cw_frequency_spinbox.setMinimumWidth(_min_spinbox_width)
        self.cw_frequency_spinbox.setDecimals(6)
        self.cw_frequency_spinbox.setSuffix('Hz')
        self.cw_frequency_spinbox.valueChanged.connect(self._cw_parameters_changed_cb)
        if frequency_range is None:
            self.cw_frequency_spinbox.setMinimum(0)
        else:
            self.cw_frequency_spinbox.setRange(*frequency_range)
        main_layout.addWidget(self.cw_frequency_spinbox)

    @property
    def cw_parameters(self):
        return self.cw_frequency_spinbox.value(), self.cw_power_spinbox.value()

    def set_cw_parameters(self, frequency=None, power=None):
        if power is not None:
            self.cw_power_spinbox.setValue(power)
        if frequency is not None:
            self.cw_frequency_spinbox.setValue(frequency)

    def parameters_set_enabled(self, enable):
        self.cw_power_spinbox.setEnabled(enable)
        self.cw_frequency_spinbox.setEnabled(enable)

    @QtCore.Slot()
    def _cw_parameters_changed_cb(self):
        self.sigCwParametersChanged.emit(*self.cw_parameters)


class OdmrScanControlDockWidget(AdvancedDockWidget):
    """
    """
    sigRangeCountChanged = QtCore.Signal(int)
    sigRangeChanged = QtCore.Signal(tuple, int)
    sigRuntimeChanged = QtCore.Signal(float)
    sigAveragedLinesChanged = QtCore.Signal(int)
    sigDataSelectionChanged = QtCore.Signal(str, int)

    def __init__(self, *args, power_range=None, frequency_range=None, data_channels=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ODMR Scan Control')
        self.setFeatures(self.DockWidgetFloatable | self.DockWidgetMovable)

        if frequency_range is None:
            self._frequency_range = None
        else:
            self._frequency_range = tuple(frequency_range)

        # create central widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # create scan parameters group box
        group_box = QtWidgets.QGroupBox('Scan Parameters')
        layout = QtWidgets.QVBoxLayout()
        group_box.setLayout(layout)
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)
        self.remove_frequency_range_button = QtWidgets.QPushButton('Remove Range')
        self.remove_frequency_range_button.setFixedSize(
            self.remove_frequency_range_button.sizeHint()
        )
        self.remove_frequency_range_button.clicked.connect(self.remove_frequency_range)
        self.add_frequency_range_button = QtWidgets.QPushButton('Add Range')
        self.add_frequency_range_button.setFixedSize(self.remove_frequency_range_button.sizeHint())
        self.add_frequency_range_button.clicked.connect(self.add_frequency_range)
        h_layout.addWidget(self.add_frequency_range_button)
        h_layout.addWidget(self.remove_frequency_range_button)
        label = QtWidgets.QLabel('Power:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        h_layout.addWidget(label)
        self.scan_power_spinbox = ScienDSpinBox()
        self.scan_power_spinbox.setMinimumWidth(_min_spinbox_width)
        self.scan_power_spinbox.setDecimals(6)
        self.scan_power_spinbox.setSuffix('dBm')
        self.scan_power_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                              QtWidgets.QSizePolicy.Fixed)
        if power_range is not None:
            self.scan_power_spinbox.setRange(*power_range)
        h_layout.addWidget(self.scan_power_spinbox)
        layout.addLayout(h_layout)
        frame = QtWidgets.QFrame()
        frame.setFrameShape(frame.HLine)
        layout.addWidget(frame)
        self._ranges_layout = QtWidgets.QGridLayout()
        self._ranges_layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel('Frequency')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._ranges_layout.addWidget(label, 0, 0, 1, 3)
        label = QtWidgets.QLabel('Start')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._ranges_layout.addWidget(label, 1, 0)
        label = QtWidgets.QLabel('Step')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._ranges_layout.addWidget(label, 1, 1)
        label = QtWidgets.QLabel('Stop')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._ranges_layout.addWidget(label, 1, 2)
        layout.addLayout(self._ranges_layout)
        layout.addStretch(1)
        main_layout.addWidget(group_box)

        # create runtime parameters group box
        group_box = QtWidgets.QGroupBox('Runtime Parameters')
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        group_box.setLayout(layout)
        label = QtWidgets.QLabel('Runtime:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 0)
        self.runtime_spinbox = ScienDSpinBox()
        self.runtime_spinbox.setMinimumWidth(_min_spinbox_width)
        self.runtime_spinbox.setMinimum(0)
        self.runtime_spinbox.setDecimals(1)
        self.runtime_spinbox.setSuffix('s')
        self.runtime_spinbox.valueChanged.connect(self._runtime_changed_cb)
        layout.addWidget(self.runtime_spinbox, 0, 1)
        label = QtWidgets.QLabel('Lines to Average:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 2)
        self.average_lines_spinbox = QtWidgets.QSpinBox()
        self.average_lines_spinbox.setMinimumWidth(_min_spinbox_width)
        self.average_lines_spinbox.setMinimum(0)
        self.average_lines_spinbox.valueChanged.connect(self.sigAveragedLinesChanged)
        layout.addWidget(self.average_lines_spinbox, 0, 3)
        layout.addWidget(self.runtime_spinbox, 0, 1)

        label = QtWidgets.QLabel('Data Channel:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 0)
        self._data_channel_combobox = QtWidgets.QComboBox()
        if data_channels is not None:
            self._data_channel_combobox.addItems(data_channels)
        self._data_channel_combobox.currentIndexChanged.connect(self._data_selection_changed_cb)
        layout.addWidget(self._data_channel_combobox, 1, 1)
        label = QtWidgets.QLabel('Range Index:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 2)
        self._range_index_spinbox = QtWidgets.QSpinBox()
        self._range_index_spinbox.setRange(0, 0)
        self._range_index_spinbox.valueChanged.connect(self._data_selection_changed_cb)
        layout.addWidget(self._range_index_spinbox, 1, 3)

        group_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        main_layout.addWidget(group_box)

        # Add single frequency scan
        self._range_widgets = list()
        self.add_frequency_range()

    @property
    def averaged_lines(self):
        return self.average_lines_spinbox.value()

    @property
    def runtime(self):
        return self.runtime_spinbox.value()

    @property
    def range_count(self):
        return len(self._range_widgets)

    @property
    def scan_power(self):
        return self.scan_power_spinbox.value()

    @property
    def frequency_ranges(self):
        return tuple(self.get_frequency_range(index) for index in range(len(self._range_widgets)))

    def get_frequency_range(self, index):
        try:
            return tuple(sb.value() for sb in self._range_widgets[index])
        except IndexError:
            return None

    @QtCore.Slot(tuple, int)
    def set_frequency_range(self, values, index):
        try:
            spinboxes = self._range_widgets[index]
        except IndexError:
            raise IndexError(f'Frequency range index "{index}" out of range.')
        try:
            for ii, sb in enumerate(spinboxes):
                sb.setValue(values[ii])
        except IndexError:
            raise IndexError(f'set_scan_range is expecting 3 float values (start, step, stop)')

    def scan_parameters_set_enabled(self, enable):
        self.add_frequency_range_button.setEnabled(enable)
        self.remove_frequency_range_button.setEnabled(enable)
        self.scan_power_spinbox.setEnabled(enable)
        for widget_tuple in self._range_widgets:
            for spinbox in widget_tuple:
                spinbox.setEnabled(enable)

    @QtCore.Slot(int)
    def set_averaged_lines(self, value):
        self.average_lines_spinbox.setValue(value)

    @QtCore.Slot(float)
    def set_runtime(self, value):
        self.runtime_spinbox.setValue(value)

    @QtCore.Slot(int)
    def set_range_count(self, count):
        assert count > 0, 'Frequency range count must be >= 1'
        self.blockSignals(True)
        while self.range_count > count:
            self.remove_frequency_range()
        while self.range_count < count:
            self.add_frequency_range()
        self.blockSignals(False)

    @QtCore.Slot()
    def add_frequency_range(self):
        index = self.range_count
        row = index + 2
        callback = self.__get_range_change_cb(index)
        start_spinbox = ScienDSpinBox()
        start_spinbox.setMinimumWidth(_min_spinbox_width)
        start_spinbox.setDecimals(6)
        start_spinbox.setSuffix('Hz')
        start_spinbox.valueChanged.connect(callback)
        step_spinbox = ScienDSpinBox()
        step_spinbox.setMinimumWidth(_min_spinbox_width)
        step_spinbox.setDecimals(6)
        step_spinbox.setSuffix('Hz')
        step_spinbox.valueChanged.connect(callback)
        stop_spinbox = ScienDSpinBox()
        stop_spinbox.setMinimumWidth(_min_spinbox_width)
        stop_spinbox.setDecimals(6)
        stop_spinbox.setSuffix('Hz')
        stop_spinbox.valueChanged.connect(callback)
        if self._frequency_range is None:
            start_spinbox.setMinimum(0)
            step_spinbox.setMinimum(0)
            stop_spinbox.setMinimum(0)
        else:
            start_spinbox.setRange(*self._frequency_range)
            step_spinbox.setRange(*self._frequency_range)
            stop_spinbox.setRange(*self._frequency_range)
        self._range_widgets.append((start_spinbox, step_spinbox, stop_spinbox))
        for col, widget in enumerate(self._range_widgets[-1]):
            self._ranges_layout.addWidget(widget, row, col)
        self._range_index_spinbox.setMaximum(len(self._range_widgets) - 1)
        self.sigRangeCountChanged.emit(len(self._range_widgets))

    @QtCore.Slot()
    def remove_frequency_range(self):
        if self.range_count > 1:
            for widget in self._range_widgets[-1]:
                self._ranges_layout.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
            del self._range_widgets[-1]
            self._range_index_spinbox.setMaximum(len(self._range_widgets) - 1)
            self.sigRangeCountChanged.emit(len(self._range_widgets))

    @QtCore.Slot()
    def _data_selection_changed_cb(self):
        channel = self._data_channel_combobox.currentText()
        range_index = self._range_index_spinbox.value()
        self.sigDataSelectionChanged.emit(channel, range_index)

    @QtCore.Slot()
    def _runtime_changed_cb(self):
        self.sigRuntimeChanged.emit(self.runtime_spinbox.value())

    def __get_range_change_cb(self, index):
        def range_changed_cb():
            self.sigRangeChanged.emit(tuple(w.value() for w in self._range_widgets[index]), index)
        return range_changed_cb
