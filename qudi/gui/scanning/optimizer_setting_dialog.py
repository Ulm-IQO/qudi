# -*- coding: utf-8 -*-

"""
This file contains a custom QWidget class to provide optimizer settings for each scanner axis.

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

__all__ = ('OptimizerSettingDialog', 'OptimizerSettingWidget', 'OptimizerAxesWidget')

from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox


class OptimizerSettingDialog(QtWidgets.QDialog):
    """ User configurable settings for the scanner optimizer logic
    """

    def __init__(self, scanner_axes, scanner_channels):
        super().__init__()
        self.setObjectName('optimizer_settings_dialog')
        self.setWindowTitle('Optimizer Settings')

        self.settings_widget = OptimizerSettingWidget(scanner_axes=scanner_axes,
                                                      scanner_channels=scanner_channels)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                     QtWidgets.QDialogButtonBox.Cancel |
                                                     QtWidgets.QDialogButtonBox.Apply,
                                                     QtCore.Qt.Horizontal,
                                                     self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.button_box)
        layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.setLayout(layout)

    @property
    def settings(self):
        return self.settings_widget.settings

    def change_settings(self, settings):
        return self.settings_widget.change_settings(settings)


class OptimizerSettingWidget(QtWidgets.QWidget):
    """ User configurable settings for the scanner optimizer logic
    """

    def __init__(self, scanner_axes, scanner_channels):
        super().__init__()
        self.setObjectName('optimizer_settings_widget')

        font = QtGui.QFont()
        font.setBold(True)

        self.data_channel_combobox = QtWidgets.QComboBox()
        self.data_channel_combobox.addItems(tuple(ch.name for ch in scanner_channels))

        label = QtWidgets.QLabel('Data channel:')
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        label.setFont(font)
        misc_settings_groupbox = QtWidgets.QGroupBox('General settings')
        misc_settings_groupbox.setFont(font)
        misc_settings_groupbox.setLayout(QtWidgets.QGridLayout())
        misc_settings_groupbox.layout().addWidget(label, 0, 0)
        misc_settings_groupbox.layout().addWidget(self.data_channel_combobox, 0, 1)
        misc_settings_groupbox.layout().setColumnStretch(1, 1)

        self.axes_widget = OptimizerAxesWidget(scanner_axes=scanner_axes)
        self.axes_widget.setObjectName('optimizer_axes_widget')
        scan_settings_groupbox = QtWidgets.QGroupBox('Scan settings')
        scan_settings_groupbox.setFont(font)
        scan_settings_groupbox.setLayout(QtWidgets.QVBoxLayout())
        scan_settings_groupbox.layout().addWidget(self.axes_widget)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(misc_settings_groupbox)
        layout.addWidget(scan_settings_groupbox)
        self.setLayout(layout)

    @property
    def settings(self):
        return {'data_channel': self.data_channel_combobox.currentText(),
                'scan_sequence': (('x', 'y'), ('z',)),
                'scan_resolution': self.axes_widget.resolution,
                'scan_range': self.axes_widget.range,
                'scan_frequency': self.axes_widget.frequency}

    def change_settings(self, settings):
        # FIXME: sequence needs to be properly implemented
        if 'data_channel' in settings:
            self.data_channel_combobox.blockSignals(True)
            self.data_channel_combobox.setCurrentText(settings['data_channel'])
            self.data_channel_combobox.blockSignals(False)
        if 'scan_range' in settings:
            self.axes_widget.set_range(settings['scan_range'])
        if 'scan_resolution' in settings:
            self.axes_widget.set_resolution(settings['scan_resolution'])
        if 'scan_frequency' in settings:
            self.axes_widget.set_frequency(settings['scan_frequency'])


class OptimizerAxesWidget(QtWidgets.QWidget):
    """ Widget to set optimizer parameters for each scanner axes
    """

    def __init__(self, *args, scanner_axes, **kwargs):
        super().__init__(*args, **kwargs)

        self.axes_widgets = dict()

        font = QtGui.QFont()
        font.setBold(True)
        layout = QtWidgets.QGridLayout()

        label = QtWidgets.QLabel('Range')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, 1)

        label = QtWidgets.QLabel('Resolution')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, 2)

        label = QtWidgets.QLabel('Frequency')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, 3)

        for index, axis in enumerate(scanner_axes, 1):
            ax_name = axis.name
            label = QtWidgets.QLabel('{0}-Axis:'.format(ax_name.title()))
            label.setObjectName('{0}_axis_label'.format(ax_name))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            max_range = abs(axis.max_value - axis.min_value)
            range_spinbox = ScienDSpinBox()
            range_spinbox.setObjectName('{0}_range_scienDSpinBox'.format(ax_name))
            range_spinbox.setRange(0, max_range)
            range_spinbox.setValue(max_range / 100)
            range_spinbox.setSuffix(axis.unit)
            range_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            range_spinbox.setMinimumSize(75, 0)
            range_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                        QtWidgets.QSizePolicy.Preferred)

            res_spinbox = QtWidgets.QSpinBox()
            res_spinbox.setObjectName('{0}_resolution_spinBox'.format(ax_name))
            res_spinbox.setRange(axis.min_resolution, min(2 ** 31 - 1, axis.max_resolution))
            res_spinbox.setValue(axis.min_resolution)
            res_spinbox.setSuffix(' px')
            res_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            res_spinbox.setMinimumSize(50, 0)
            res_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            freq_spinbox = ScienDSpinBox()
            freq_spinbox.setObjectName('{0}_frequency_scienDSpinBox'.format(ax_name))
            freq_spinbox.setRange(*axis.frequency_range)
            freq_spinbox.setValue(max(axis.min_frequency, axis.max_frequency / 100))
            freq_spinbox.setSuffix('Hz')
            freq_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            freq_spinbox.setMinimumSize(75, 0)
            freq_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Preferred)

            # Add to layout
            layout.addWidget(label, index, 0)
            layout.addWidget(range_spinbox, index, 1)
            layout.addWidget(res_spinbox, index, 2)
            layout.addWidget(freq_spinbox, index, 3)

            # Remember widgets references for later access
            self.axes_widgets[ax_name] = dict()
            self.axes_widgets[ax_name]['label'] = label
            self.axes_widgets[ax_name]['res_spinbox'] = res_spinbox
            self.axes_widgets[ax_name]['range_spinbox'] = range_spinbox
            self.axes_widgets[ax_name]['freq_spinbox'] = freq_spinbox

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        self.setLayout(layout)
        self.setMaximumHeight(self.sizeHint().height())

    @property
    def axes(self):
        return tuple(self.axes_widgets)

    @property
    def resolution(self):
        return {ax: widgets['res_spinbox'].value() for ax, widgets in self.axes_widgets.items()}

    @property
    def range(self):
        return {ax: widgets['range_spinbox'].value() for ax, widgets in self.axes_widgets.items()}

    @property
    def frequency(self):
        return {ax: widgets['freq_spinbox'].value() for ax, widgets in self.axes_widgets.items()}

    def get_resolution(self, axis):
        return self.axes_widgets[axis]['res_spinbox'].value()

    @QtCore.Slot(dict)
    @QtCore.Slot(int, str)
    def set_resolution(self, value, axis=None):
        if axis is None or isinstance(value, dict):
            for ax, val in value.items():
                spinbox = self.axes_widgets[ax]['res_spinbox']
                spinbox.blockSignals(True)
                spinbox.setValue(val)
                spinbox.blockSignals(False)
        else:
            spinbox = self.axes_widgets[axis]['res_spinbox']
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def get_range(self, axis):
        return self.axes_widgets[axis]['range_spinbox'].value()

    @QtCore.Slot(dict)
    @QtCore.Slot(object, str)
    def set_range(self, value, axis=None):
        if axis is None or isinstance(value, dict):
            for ax, val in value.items():
                spinbox = self.axes_widgets[ax]['range_spinbox']
                spinbox.blockSignals(True)
                spinbox.setValue(val)
                spinbox.blockSignals(False)
        else:
            spinbox = self.axes_widgets[axis]['range_spinbox']
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def get_frequency(self, axis):
        return self.axes_widgets[axis]['freq_spinbox'].value()

    @QtCore.Slot(dict)
    @QtCore.Slot(float, str)
    def set_frequency(self, value, axis=None):
        if axis is None or isinstance(value, dict):
            for ax, val in value.items():
                spinbox = self.axes_widgets[ax]['freq_spinbox']
                spinbox.blockSignals(True)
                spinbox.setValue(val)
                spinbox.blockSignals(False)
        else:
            spinbox = self.axes_widgets[axis]['freq_spinbox']
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def set_assumed_unit_prefix(self, prefix):
        for widgets in self.axes_widgets.values():
            widgets['range_spinbox'].assumed_unit_prefix = prefix
