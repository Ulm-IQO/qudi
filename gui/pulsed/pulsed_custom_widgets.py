# -*- coding: utf-8 -*-

"""
This file contains custom item widgets for the pulse editor QTableViews.

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

from qtpy import QtCore, QtGui
from collections import OrderedDict
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox


class DigitalChannelsWidget(QtGui.QWidget):
    """
    """
    stateChanged = QtCore.Signal()

    def __init__(self, parent=None, digital_channels=None):
        super().__init__(parent)

        if digital_channels is None:
            self._digital_channels = list()
        else:
            self._digital_channels = digital_channels

        self._dch_checkboxes = OrderedDict()
        self._width_hint = 30 * len(self._digital_channels)

        main_layout = QtGui.QHBoxLayout()
        for chnl in self._digital_channels:
            # Create QLabel and QCheckBox for each digital channel
            label = QtGui.QLabel(chnl.rsplit('ch')[1])
            label.setFixedWidth(30)
            label.setAlignment(QtCore.Qt.AlignCenter)
            widget = QtGui.QCheckBox()
            widget.setFixedWidth(19)
            widget.setChecked(False)
            self._dch_checkboxes[chnl] = {'label': label, 'widget': widget}

            # Forward editingFinished signal of child widget
            widget.stateChanged.connect(self.stateChanged)

            # Arrange CheckBoxes and Labels in a layout
            v_layout = QtGui.QVBoxLayout()
            v_layout.addWidget(label)
            v_layout.addWidget(widget)
            v_layout.setAlignment(label, QtCore.Qt.AlignHCenter)
            v_layout.setAlignment(widget, QtCore.Qt.AlignHCenter)
            main_layout.addLayout(v_layout)
        main_layout.addStretch(1)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def data(self):
        digital_states = OrderedDict()
        for chnl in self._digital_channels:
            digital_states[chnl] = self._dch_checkboxes[chnl]['widget'].isChecked()
        return digital_states

    def setData(self, data):
        for chnl in data:
            self._dch_checkboxes[chnl]['widget'].setChecked(data[chnl])
        self.stateChanged.emit()
        return

    def sizeHint(self):
        return QtCore.QSize(self._width_hint, 50)


class AnalogParametersWidget(QtGui.QWidget):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent=None, parameters_dict=None):
        super().__init__(parent)
        if parameters_dict is None:
            self._parameters = OrderedDict()
        else:
            self._parameters = parameters_dict

        self._width_hint = 90 * len(self._parameters)
        self._ach_widgets = OrderedDict()

        main_layout = QtGui.QHBoxLayout()
        for param in self._parameters:
            label = QtGui.QLabel(param)
            label.setAlignment(QtCore.Qt.AlignCenter)
            if self._parameters[param]['type'] == float:
                widget = ScienDSpinBox()
                widget.setMinimum(self._parameters[param]['min'])
                widget.setMaximum(self._parameters[param]['max'])
                widget.setDecimals(6, False)
                widget.setValue(self._parameters[param]['init'])
                widget.setSuffix(self._parameters[param]['unit'])
                # Set size constraints
                widget.setFixedWidth(90)
                # Forward editingFinished signal of child widget
                widget.editingFinished.connect(self.editingFinished)
            elif self._parameters[param]['type'] == int:
                widget = ScienSpinBox()
                widget.setValue(self._parameters[param]['init'])
                widget.setMinimum(self._parameters[param]['min'])
                widget.setMaximum(self._parameters[param]['max'])
                widget.setSuffix(self._parameters[param]['unit'])
                # Set size constraints
                widget.setFixedWidth(90)
                # Forward editingFinished signal of child widget
                widget.editingFinished.connect(self.editingFinished)
            elif self._parameters[param]['type'] == str:
                widget = QtGui.QLineEdit()
                widget.setText(self._parameters[param]['init'])
                # Set size constraints
                widget.setFixedWidth(90)
                # Forward editingFinished signal of child widget
                widget.editingFinished.connect(self.editingFinished)
            elif self._parameters[param]['type'] == bool:
                widget = QtGui.QCheckBox()
                widget.setChecked(self._parameters[param]['init'])
                # Set size constraints
                widget.setFixedWidth(90)
                # Forward editingFinished signal of child widget
                widget.stateChanged.connect(self.editingFinished)

            self._ach_widgets[param] = {'label': label, 'widget': widget}

            v_layout = QtGui.QVBoxLayout()
            v_layout.addWidget(label)
            v_layout.addWidget(widget)
            v_layout.setAlignment(label, QtCore.Qt.AlignHCenter)
            v_layout.setAlignment(widget, QtCore.Qt.AlignHCenter)
            main_layout.addLayout(v_layout)

        main_layout.addStretch(1)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def setData(self, data):
        # Set analog parameter widget values
        for param in self._ach_widgets:
            widget = self._ach_widgets[param]['widget']
            if self._parameters[param]['type'] in [int, float]:
                widget.setValue(data[param])
            elif self._parameters[param]['type'] == str:
                widget.setText(data[param])
            elif self._parameters[param]['type'] == bool:
                widget.setChecked(data[param])

        self.editingFinished.emit()
        return

    def data(self):
        # Get all analog parameters from widgets
        analog_params = OrderedDict()
        for param in self._parameters:
            widget = self._ach_widgets[param]['widget']
            if self._parameters[param]['type'] in [int, float]:
                analog_params[param] = widget.value()
            elif self._parameters[param]['type'] == str:
                analog_params[param] = widget.text()
            elif self._parameters[param]['type'] == bool:
                analog_params[param] = widget.isChecked()
        return analog_params

    def sizeHint(self):
        return QtCore.QSize(self._width_hint, 50)

    # def selectNumber(self):
    #     """
    #     """
    #     for param in self._parameters:
    #         widget = self._ach_widgets[param]['widget']
    #         if self._parameters[param]['type'] in [int, float]:
    #             widget.selectNumber()  # that is specific for the ScientificSpinBox
