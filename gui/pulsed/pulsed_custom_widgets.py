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

import re
import numpy as np
from qtpy import QtCore, QtGui
from collections import OrderedDict
from pyqtgraph import functions as fn


class FloatValidator(QtGui.QValidator):
    """
    This is a validator for float values represented as strings in scientific notation.
    (i.e. "1.35e-9", ".24E+8", "14e3" etc.)
    Also supports SI unit prefix like 'M', 'n' etc.
    """
    float_re = re.compile(
        r'(\s*([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*([YZEPTGMkmµnpfazy]?)\s*)')

    def validate(self, string, position):
        if self._is_valid_float_string(string):
            state = self.Acceptable
        elif string == '' or string[position-1] in 'e.-+ ':
            state = self.Intermediate
        else:
            state = self.Invalid
        return state, string, position

    def fixup(self, text):
        match = self.float_re.search(text)
        if match:
            return match.groups()[0].lstrip().rstrip()
        else:
            return ''

    def _is_valid_float_string(self, string):
        match = self.float_re.search(string)
        if match:
            return match.groups()[0] == string
        else:
            return False


class ScientificDoubleSpinBox(QtGui.QDoubleSpinBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimum(-np.inf)
        self.setMaximum(np.inf)
        self.validator = FloatValidator()
        self.setDecimals(1000)

    def validate(self, text, position):
        return self.validator.validate(text, position)

    def fixup(self, text):
        return self.validator.fixup(text)

    def valueFromText(self, text):
        return fn.siEval(text.lstrip())  # get rid of leading whitespaces in text

    def textFromValue(self, value):
        (scale_factor, suffix) = fn.siScale(value)
        scaled_val = value * scale_factor
        string = ''
        if scaled_val < 10:
            string = fn.siFormat(value, precision=4)
        elif scaled_val < 100:
            string = fn.siFormat(value, precision=5)
        elif scaled_val < 1000:
            string = fn.siFormat(value, precision=6)
        return string

    def stepBy(self, steps):
        text = self.cleanText()
        groups = self.validator.float_re.search(text).groups()
        decimal_num = float(groups[1])
        decimal_num += steps
        new_string = '{0:g}'.format(decimal_num) + ((' ' + groups[4]) if groups[4] else '')
        new_value = fn.siEval(new_string)
        if new_value < self.minimum():
            new_value = self.minimum()
        if new_value > self.maximum():
            new_value = self.maximum()
        new_string = self.textFromValue(new_value)
        self.lineEdit().setText(new_string)
        return


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
            label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            widget = QtGui.QCheckBox()
            widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
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
            label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            if self._parameters[param]['type'] == float:
                widget = ScientificDoubleSpinBox()
                widget.setMinimum(self._parameters[param]['min'])
                widget.setMaximum(self._parameters[param]['max'])
                widget.setValue(self._parameters[param]['init'])
                # widget.setSuffix(self._parameters[param]['unit'])
                # Set size constraints
                widget.setFixedWidth(90)
                # Forward editingFinished signal of child widget
                widget.editingFinished.connect(self.editingFinished)
            elif self._parameters[param]['type'] == int:
                widget = QtGui.QSpinBox()
                widget.setValue(self._parameters[param]['init'])
                widget.setMinimum(self._parameters[param]['min'])
                widget.setMaximum(self._parameters[param]['max'])
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
