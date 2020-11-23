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

__all__ = ('OdmrControlDockWidget',)


class OdmrControlDockWidget(AdvancedDockWidget):
    """
    """
    sigRangeCountChanged = QtCore.Signal(int)
    sigRangeChanged = QtCore.Signal(tuple, int)
    sigCwParametersChanged = QtCore.Signal(float, float)
    sigRuntimeChanged = QtCore.Signal(float)
    sigAveragedLinesChanged = QtCore.Signal(int)

    def __init__(self, *args, scan_frequency_limits=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ODMR Control')

        font_metrics = QtGui.QFontMetrics(ScienDSpinBox().font())
        self._min_spinbox_width = font_metrics.width(f'   -000.000000 GHz   ')

        if scan_frequency_limits is None:
            self._scan_frequency_limits = None
        else:
            self._scan_frequency_limits = tuple(scan_frequency_limits)

        # create central widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout()
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # create CW parameter group box
        group_box = QtWidgets.QGroupBox('CW Parameters')
        layout = QtWidgets.QHBoxLayout()
        group_box.setLayout(layout)
        label = QtWidgets.QLabel('CW Frequency:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        self.cw_frequency_spinbox = ScienDSpinBox()
        self.cw_frequency_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.cw_frequency_spinbox.setMinimum(0)
        self.cw_frequency_spinbox.setDecimals(6)
        self.cw_frequency_spinbox.setSuffix('Hz')
        layout.addWidget(self.cw_frequency_spinbox)
        label = QtWidgets.QLabel('CW Power:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        self.cw_power_spinbox = ScienDSpinBox()
        self.cw_power_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.cw_power_spinbox.setDecimals(6)
        self.cw_power_spinbox.setSuffix('dBm')
        layout.addWidget(self.cw_power_spinbox)
        layout.setStretch(1, 1)
        layout.setStretch(3, 1)
        group_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
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
        self.runtime_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.runtime_spinbox.setMinimum(0)
        self.runtime_spinbox.setDecimals(1)
        self.runtime_spinbox.setSuffix('s')
        layout.addWidget(self.runtime_spinbox, 0, 1)
        label = QtWidgets.QLabel('Lines to Average:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 2)
        self.average_lines_spinbox = QtWidgets.QSpinBox()
        self.average_lines_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.average_lines_spinbox.setMinimum(0)
        layout.addWidget(self.average_lines_spinbox, 0, 3)
        layout.addWidget(self.runtime_spinbox, 0, 1)
        label = QtWidgets.QLabel('Elapsed Time:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 0)
        self.elapsed_time_lineedit = QtWidgets.QLineEdit('00:00:00')
        self.elapsed_time_lineedit.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.elapsed_time_lineedit.setReadOnly(True)
        layout.addWidget(self.elapsed_time_lineedit, 1, 1)
        label = QtWidgets.QLabel('Elapsed Sweeps:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 2)
        self.elapsed_sweeps_spinbox = QtWidgets.QSpinBox()
        self.elapsed_sweeps_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.elapsed_sweeps_spinbox.setMinimum(-1)
        self.elapsed_sweeps_spinbox.setSpecialValueText('NaN')
        self.elapsed_sweeps_spinbox.setValue(-1)
        self.elapsed_sweeps_spinbox.setReadOnly(True)
        self.elapsed_sweeps_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        layout.addWidget(self.elapsed_sweeps_spinbox, 1, 3)
        group_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        main_layout.addWidget(group_box)

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
        self.scan_power_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.scan_power_spinbox.setDecimals(6)
        self.scan_power_spinbox.setSuffix('dBm')
        self.scan_power_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                              QtWidgets.QSizePolicy.Fixed)
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
    def cw_parameters(self):
        return self.cw_power_spinbox.value(), self.cw_frequency_spinbox.value()

    @property
    def range_count(self):
        return len(self._range_widgets)

    @QtCore.Slot(int)
    def set_averaged_lines(self, value):
        self.average_lines_spinbox.setValue(value)

    @QtCore.Slot(float)
    def set_runtime(self, value):
        self.runtime_spinbox.setValue(value)

    @QtCore.Slot(float, float)
    def set_cw_parameters(self, power, frequency):
        self.cw_power_spinbox.setValue(power)
        self.cw_frequency_spinbox.setValue(frequency)

    @QtCore.Slot(int)
    def set_range_count(self, count):
        assert count > 0, 'Frequency range count must be >= 1'
        while self.range_count > count:
            self.remove_frequency_range()
        while self.range_count < count:
            self.add_frequency_range()

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
            raise IndexError(f'set_frequency_range is expecting 3 float values (start, step, stop)')

    @QtCore.Slot()
    def add_frequency_range(self):
        row = self.range_count + 2
        start_spinbox = ScienDSpinBox()
        start_spinbox.setMinimumWidth(self._min_spinbox_width)
        start_spinbox.setDecimals(6)
        start_spinbox.setSuffix('Hz')
        step_spinbox = ScienDSpinBox()
        step_spinbox.setMinimumWidth(self._min_spinbox_width)
        step_spinbox.setDecimals(6)
        step_spinbox.setSuffix('Hz')
        stop_spinbox = ScienDSpinBox()
        stop_spinbox.setMinimumWidth(self._min_spinbox_width)
        stop_spinbox.setDecimals(6)
        stop_spinbox.setSuffix('Hz')
        if self._scan_frequency_limits is None:
            start_spinbox.setMinimum(0)
            step_spinbox.setMinimum(0)
            stop_spinbox.setMinimum(0)
        else:
            start_spinbox.setRange(*self._scan_frequency_limits)
            step_spinbox.setRange(*self._scan_frequency_limits)
            stop_spinbox.setRange(*self._scan_frequency_limits)
        self._range_widgets.append((start_spinbox, step_spinbox, stop_spinbox))
        for col, widget in enumerate(self._range_widgets[-1]):
            self._ranges_layout.addWidget(widget, row, col)

    @QtCore.Slot()
    def remove_frequency_range(self):
        if self.range_count > 1:
            for widget in self._range_widgets[-1]:
                self._ranges_layout.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
            del self._range_widgets[-1]
