# -*- coding: utf-8 -*-

"""
This file contains a custom QWidget class to provide controls for each scanner axis.

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

from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.gui.qtwidgets.slider import DoubleSlider

__all__ = ('AxesControlDockWidget', 'AxesControlWidget')


class AxesControlDockWidget(QtWidgets.QDockWidget):
    """ Scanner control QDockWidget based on the corresponding QWidget subclass
    """
    __wrapped_attributes = frozenset({'sigResolutionChanged', 'sigRangeChanged',
                                      'sigTargetChanged', 'sigSliderMoved', 'axes', 'resolution',
                                      'range', 'target', 'get_resolution', 'set_resolution',
                                      'get_range', 'set_range', 'get_target', 'set_target',
                                      'set_assumed_unit_prefix'})

    def __init__(self, scanner_axes):
        super().__init__('Axes Control')
        self.setObjectName('axes_control_dockWidget')
        widget = AxesControlWidget(scanner_axes=scanner_axes)
        widget.setObjectName('axes_control_widget')
        self.setWidget(widget)
        return

    def __getattr__(self, item):
        if item in self.__wrapped_attributes:
            return getattr(self.widget(), item)
        raise AttributeError('AxesControlDockWidget has not attribute "{0}"'.format(item))


class AxesControlWidget(QtWidgets.QWidget):
    """ Widget to control scan parameters and target position of scanner axes.
    """

    sigResolutionChanged = QtCore.Signal(str, int)
    sigRangeChanged = QtCore.Signal(str, tuple)
    sigTargetChanged = QtCore.Signal(str, float)
    sigSliderMoved = QtCore.Signal(str, float)

    def __init__(self, *args, scanner_axes, **kwargs):
        super().__init__(*args, **kwargs)

        self.axes_widgets = dict()

        font = QtGui.QFont()
        font.setBold(True)
        layout = QtWidgets.QGridLayout()

        label = QtWidgets.QLabel('Resolution')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, 1)

        vline = QtWidgets.QFrame()
        vline.setFrameShape(QtWidgets.QFrame.VLine)
        vline.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(vline, 0, 2, len(scanner_axes) + 1, 1)

        label = QtWidgets.QLabel('Scan Range')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, 3, 1, 2)

        vline = QtWidgets.QFrame()
        vline.setFrameShape(QtWidgets.QFrame.VLine)
        vline.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(vline, 0, 5, len(scanner_axes) + 1, 1)

        label = QtWidgets.QLabel('Current Target')
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, 7)

        for index, axis in enumerate(scanner_axes, 1):
            ax_name = axis.name
            label = QtWidgets.QLabel('{0}-Axis:'.format(ax_name.title()))
            label.setObjectName('{0}_axis_label'.format(ax_name))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            res_spinbox = QtWidgets.QSpinBox()
            res_spinbox.setObjectName('{0}_resolution_spinBox'.format(ax_name))
            res_spinbox.setRange(axis.min_resolution, min(2 ** 31 - 1, axis.max_resolution))
            res_spinbox.setValue(axis.min_resolution)
            res_spinbox.setSuffix(' px')
            res_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            res_spinbox.setMinimumSize(50, 0)
            res_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            min_spinbox = ScienDSpinBox()
            min_spinbox.setObjectName('{0}_min_range_scienDSpinBox'.format(ax_name))
            min_spinbox.setRange(*axis.value_range)
            min_spinbox.setValue(axis.min_value)
            min_spinbox.setSuffix(axis.unit)
            min_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            min_spinbox.setMinimumSize(75, 0)
            min_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            max_spinbox = ScienDSpinBox()
            max_spinbox.setObjectName('{0}_max_range_scienDSpinBox'.format(ax_name))
            max_spinbox.setRange(*axis.value_range)
            max_spinbox.setValue(axis.max_value)
            max_spinbox.setSuffix(axis.unit)
            max_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            max_spinbox.setMinimumSize(75, 0)
            max_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            init_pos = (axis.max_value - axis.min_value) / 2 + axis.min_value

            slider = DoubleSlider(QtCore.Qt.Horizontal)
            slider.setObjectName('{0}_position_doubleSlider'.format(ax_name))
            slider.setRange(*axis.value_range)
            if axis.min_step > 0:
                slider.set_granularity(round((axis.max_value - axis.min_value) / axis.min_step) + 1)
            else:
                slider.set_granularity(2**16-1)
            slider.setValue(init_pos)
            slider.setMinimumSize(150, 0)
            slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            pos_spinbox = ScienDSpinBox()
            pos_spinbox.setObjectName('{0}_position_scienDSpinBox'.format(ax_name))
            pos_spinbox.setRange(*axis.value_range)
            pos_spinbox.setValue(init_pos)
            pos_spinbox.setSuffix(axis.unit)
            pos_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            pos_spinbox.setMinimumSize(75, 0)
            pos_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            # Add to layout
            layout.addWidget(label, index, 0)
            layout.addWidget(res_spinbox, index, 1)
            layout.addWidget(min_spinbox, index, 3)
            layout.addWidget(max_spinbox, index, 4)
            layout.addWidget(slider, index, 6)
            layout.addWidget(pos_spinbox, index, 7)

            # Connect signals
            res_spinbox.editingFinished.connect(
                self.__get_axis_resolution_callback(ax_name, res_spinbox)
            )
            min_spinbox.editingFinished.connect(
                self.__get_axis_min_range_callback(ax_name, min_spinbox)
            )
            max_spinbox.editingFinished.connect(
                self.__get_axis_max_range_callback(ax_name, max_spinbox)
            )
            slider.doubleSliderMoved.connect(self.__get_axis_slider_moved_callback(ax_name))
            slider.sliderReleased.connect(self.__get_axis_slider_released_callback(ax_name, slider))
            pos_spinbox.editingFinished.connect(
                self.__get_axis_target_callback(ax_name, pos_spinbox)
            )

            # Remember widgets references for later access
            self.axes_widgets[ax_name] = dict()
            self.axes_widgets[ax_name]['label'] = label
            self.axes_widgets[ax_name]['res_spinbox'] = res_spinbox
            self.axes_widgets[ax_name]['min_spinbox'] = min_spinbox
            self.axes_widgets[ax_name]['max_spinbox'] = max_spinbox
            self.axes_widgets[ax_name]['slider'] = slider
            self.axes_widgets[ax_name]['pos_spinbox'] = pos_spinbox

        layout.setColumnStretch(5, 1)
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
        return {ax: (widgets['min_spinbox'].value(), widgets['max_spinbox'].value()) for ax, widgets
                in self.axes_widgets.items()}

    @property
    def target(self):
        return {ax: widgets['pos_spinbox'].value() for ax, widgets in self.axes_widgets.items()}

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
        widget_dict = self.axes_widgets[axis]
        return widget_dict['min_spinbox'].value(), widget_dict['max_spinbox'].value()

    @QtCore.Slot(dict)
    @QtCore.Slot(object, str)
    def set_range(self, value, axis=None):
        if axis is None or isinstance(value, dict):
            for ax, val in value.items():
                min_spinbox = self.axes_widgets[ax]['min_spinbox']
                max_spinbox = self.axes_widgets[ax]['max_spinbox']
                min_val, max_val = val
                min_spinbox.blockSignals(True)
                min_spinbox.setValue(min_val)
                min_spinbox.blockSignals(False)
                max_spinbox.blockSignals(True)
                max_spinbox.setValue(max_val)
                max_spinbox.blockSignals(False)
        else:
            min_spinbox = self.axes_widgets[axis]['min_spinbox']
            max_spinbox = self.axes_widgets[axis]['max_spinbox']
            min_val, max_val = value
            min_spinbox.blockSignals(True)
            min_spinbox.setValue(min_val)
            min_spinbox.blockSignals(False)
            max_spinbox.blockSignals(True)
            max_spinbox.setValue(max_val)
            max_spinbox.blockSignals(False)

    def get_target(self, axis):
        return self.axes_widgets[axis]['pos_spinbox'].value()

    @QtCore.Slot(dict)
    @QtCore.Slot(float, str)
    def set_target(self, value, axis=None):
        if axis is None or isinstance(value, dict):
            for ax, val in value.items():
                spinbox = self.axes_widgets[ax]['pos_spinbox']
                slider = self.axes_widgets[ax]['slider']
                slider.blockSignals(True)
                slider.setValue(val)
                slider.blockSignals(False)
                spinbox.blockSignals(True)
                spinbox.setValue(val)
                spinbox.blockSignals(False)
        else:
            spinbox = self.axes_widgets[axis]['pos_spinbox']
            slider = self.axes_widgets[axis]['slider']
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def set_assumed_unit_prefix(self, prefix):
        for widgets in self.axes_widgets.values():
            widgets['pos_spinbox'].assumed_unit_prefix = prefix
            widgets['min_spinbox'].assumed_unit_prefix = prefix
            widgets['max_spinbox'].assumed_unit_prefix = prefix

    def __get_axis_resolution_callback(self, axis, spinbox):
        def callback():
            self.sigResolutionChanged.emit(axis, spinbox.value())
        return callback

    def __get_axis_min_range_callback(self, axis, spinbox):
        def callback():
            max_spinbox = self.axes_widgets[axis]['max_spinbox']
            min_value = spinbox.value()
            max_value = max_spinbox.value()
            if min_value > max_value:
                max_spinbox.blockSignals(True)
                max_spinbox.setValue(min_value)
                max_spinbox.blockSignals(False)
                max_value = min_value
            self.sigRangeChanged.emit(axis, (min_value, max_value))
        return callback

    def __get_axis_max_range_callback(self, axis, spinbox):
        def callback():
            min_spinbox = self.axes_widgets[axis]['min_spinbox']
            min_value = min_spinbox.value()
            max_value = spinbox.value()
            if max_value < min_value:
                min_spinbox.blockSignals(True)
                min_spinbox.setValue(max_value)
                min_spinbox.blockSignals(False)
                min_value = max_value
            self.sigRangeChanged.emit(axis, (min_value, max_value))
        return callback

    def __get_axis_slider_moved_callback(self, axis):
        def callback(value):
            spinbox = self.axes_widgets[axis]['pos_spinbox']
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)
            self.sigSliderMoved.emit(axis, value)
        return callback

    def __get_axis_slider_released_callback(self, axis, slider):
        def callback():
            value = slider.value()
            spinbox = self.axes_widgets[axis]['pos_spinbox']
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)
            self.sigTargetChanged.emit(axis, value)
        return callback

    def __get_axis_target_callback(self, axis, spinbox):
        def callback():
            value = spinbox.value()
            slider = self.axes_widgets[axis]['slider']
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
            self.sigTargetChanged.emit(axis, value)
        return callback
