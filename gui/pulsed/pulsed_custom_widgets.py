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
from enum import Enum


class MultipleCheckboxWidget(QtGui.QWidget):
    """
    """
    stateChanged = QtCore.Signal()

    def __init__(self, parent=None, checkbox_labels=None):
        super().__init__(parent)

        checkbox_labels = list() if checkbox_labels is None else list(checkbox_labels)

        self._checkboxes = OrderedDict()
        self._checkbox_width = 30
        self._width_hint = self._checkbox_width * len(checkbox_labels)

        main_layout = QtGui.QHBoxLayout()
        for box_label in checkbox_labels:
            # Create QLabel and QCheckBox for each checkbox label given in init
            label = QtGui.QLabel(box_label)
            label.setFixedWidth(self._checkbox_width)
            label.setAlignment(QtCore.Qt.AlignCenter)
            widget = QtGui.QCheckBox()
            widget.setFixedWidth(19)
            widget.setChecked(False)
            self._checkboxes[box_label] = {'label': label, 'widget': widget}

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
        checkbox_states = OrderedDict()
        for box_label, box_dict in self._checkboxes.items():
            checkbox_states[box_label] = box_dict['widget'].isChecked()
        return checkbox_states

    def setData(self, data):
        for label, state in data.items():
            self._checkboxes[label]['widget'].setChecked(state)
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
            elif issubclass(self._parameters[param]['type'], Enum):
                widget = QtGui.QComboBox()
                for option in self._parameters[param]['type']:
                    widget.addItem(option.name, option)
                widget.setCurrentText(self._parameters[param]['init'].name)
                # Set size constraints
                widget.setFixedWidth(90)
                # Forward editingFinished signal of child widget
                widget.currentIndexChanged.connect(self.editingFinished)

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
            elif issubclass(self._parameters[param]['type'], Enum):
                widget.setCurrentText(data[param].name)

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
            elif issubclass(self._parameters[param]['type'], Enum):
                analog_params[param] = widget.itemData(widget.currentIndex())
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
