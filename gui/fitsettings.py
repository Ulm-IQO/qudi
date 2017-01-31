# -*- coding: utf-8 -*-

"""
This file contains a widget for fit parameters.

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

from qtpy import QtWidgets
from pyqtgraph import SpinBox
import numpy as np
import math

class FitSettingsWidget(QtWidgets.QWidget):

    def __init__(self, parameters):
        """ Definition, configuration and initialisation of the optimizer settings GUI. Adds a row
            with the value, min, max and vary for each variable in parameters.
        """
        super().__init__()

        self._Layout = QtWidgets.QGridLayout(self)  # Creation of the grid Layout
        self.custom_params_checkbox = QtWidgets.QCheckBox('Use custom values')
        self._Layout.addWidget(self.custom_params_checkbox, 0, 0)
        self.valueLabel = QtWidgets.QLabel('Value')
        self.minimumLabel = QtWidgets.QLabel('Min')
        self.maximumLabel = QtWidgets.QLabel('Max')
        self.varyLabel = QtWidgets.QLabel('Vary')
        self.exprLabel = QtWidgets.QLabel('Expr')
        self._Layout.addWidget(self.valueLabel, 1, 1)
        self._Layout.addWidget(self.minimumLabel, 1, 2)
        self._Layout.addWidget(self.maximumLabel, 1, 3)
        self._Layout.addWidget(self.varyLabel, 1, 5)
        self._Layout.addWidget(self.exprLabel, 1, 4)

        self.widgets = {}
        n = 2
        for name, param in parameters.items():
            self.widgets[name+"_label"] = parameterNameLabel = QtWidgets.QLabel(str(name),parent=self)
            self.widgets[name+'_value'] = valueSpinbox =  SpinBox(parent=self)
            self.widgets[name+'_min'] = minimumSpinbox = SpinBox(parent=self)
            self.widgets[name+'_max'] = maximumSpinbox = SpinBox(parent=self)
            self.widgets[name+'_expr'] = expressionLineEdit = QtWidgets.QLineEdit(parent=self)
            self.widgets[name+'_vary'] = varyCheckbox = QtWidgets.QCheckBox(parent=self)
            valueSpinbox.setDecimals(3)
            valueSpinbox.setSingleStep(0.01)
            valueSpinbox.setMaximum(np.inf)
            valueSpinbox.setMinimum(-np.inf)
            minimumSpinbox.setDecimals(3)
            minimumSpinbox.setSingleStep(0.01)
            minimumSpinbox.setMaximum(np.inf)
            minimumSpinbox.setMinimum(-np.inf)
            maximumSpinbox.setDecimals(3)
            maximumSpinbox.setSingleStep(0.01)
            maximumSpinbox.setMaximum(np.inf)
            maximumSpinbox.setMinimum(-np.inf)
            if param.value is not None and not math.isnan(param.value):
                valueSpinbox.setValue(param.value)
                minimumSpinbox.setValue(param.min)
                minimumSpinbox.setValue(param.max)
                expressionLineEdit.setText(param.expr)
                varyCheckbox.setChecked(param.vary)

            self._Layout.addWidget(parameterNameLabel, n, 0)
            self._Layout.addWidget(valueSpinbox, n, 1)
            self._Layout.addWidget(minimumSpinbox, n, 2)
            self._Layout.addWidget(maximumSpinbox, n, 3)
            self._Layout.addWidget(expressionLineEdit, n, 4)
            self._Layout.addWidget(varyCheckbox, n, 5)
            n += 1

    def updateFitSettings(self, parameters):
        """ Updates the fit parameters with the new values from the settings window
        """
        for name, param in parameters.items():
            param.value = self.widgets[name+'_value'].value()
            param.min = self.widgets[name+'_min'].value()
            param.max = self.widgets[name+'_max'].value()
            param.expr = str(self.widgets[name+'_expr'].displayText())
            param.vary = self.widgets[name+'_vary'].checkState()
        return self.custom_params_checkbox.isChecked()

    def keepFitSettings(self, parameters, use_custom_parameters):
        """ Keeps the old fit settings
        """
        for name, param in parameters.items():
            if parameters[name].value is not None and not math.isnan(param.value):
                self.widgets[name+'_value'].setValue(param.value)
                self.widgets[name+'_min'].setValue(param.min)
                self.widgets[name+'_max'].setValue(param.max)
                self.widgets[name+'_expr'].setText(param.expr)
                self.widgets[name+'_vary'].setChecked(param.vary)
        self.custom_params_checkbox.setChecked(use_custom_parameters)

