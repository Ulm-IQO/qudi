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

        self.hlayout = QtWidgets.QHBoxLayout()

        self.choosefitLabel = QtWidgets.QLabel('Choose fit: ')
        self.chooseestimLabel = QtWidgets.QLabel('Choose estimator: ')

        self.hlayout.addWidget(self.choosefitLabel)
        self.hlayout.addWidget(self.chooseestimLabel)

        self.fit_action_layout = QtWidgets.QVBoxLayout(self)

        self.fit_function = QtWidgets.QComboBox()
        self.estimator = QtWidgets.QComboBox()

        self.fit_action_layout.addWidget(self.fit_function)
        self.fit_action_layout.addWidget(self.estimator)

        self.fit_action_layout.addLayout(self.hlayout)

        self.param_grid_layout = QtWidgets.QGridLayout()  # Creation of the grid Layout

        self.useLabel = QtWidgets.QLabel('Edit?')
        self.valueLabel = QtWidgets.QLabel('Value')
        self.minimumLabel = QtWidgets.QLabel('Minimum')
        self.maximumLabel = QtWidgets.QLabel('Maximum')
        self.exprLabel = QtWidgets.QLabel('Expression')
        self.varyLabel = QtWidgets.QLabel('Vary?')

        self.param_grid_layout.addWidget(self.useLabel, 1, 0)
        self.param_grid_layout.addWidget(self.valueLabel, 1, 2)
        self.param_grid_layout.addWidget(self.minimumLabel, 1, 3)
        self.param_grid_layout.addWidget(self.maximumLabel, 1, 4)
        self.param_grid_layout.addWidget(self.exprLabel, 1, 5)
        self.param_grid_layout.addWidget(self.varyLabel, 1, 6)

        self.widgets = {}
        self.paramUseSettings = {}
        n = 2
        for name, param in parameters.items():
            self.paramUseSettings[name] = False
            self.widgets[name + '_use'] = useCheckbox = QtWidgets.QCheckBox(parent=self)
            self.widgets[name + '_label'] = parameterNameLabel = QtWidgets.QLabel(str(name), parent=self)
            self.widgets[name + '_value'] = valueSpinbox = SpinBox(parent=self)
            self.widgets[name + '_min'] = minimumSpinbox = SpinBox(parent=self)
            self.widgets[name + '_max'] = maximumSpinbox = SpinBox(parent=self)
            self.widgets[name + '_expr'] = expressionLineEdit = QtWidgets.QLineEdit(parent=self)
            self.widgets[name + '_vary'] = varyCheckbox = QtWidgets.QCheckBox(parent=self)
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
                useCheckbox.setChecked(self.paramUseSettings[name])
                valueSpinbox.setValue(param.value)
                minimumSpinbox.setValue(param.min)
                minimumSpinbox.setValue(param.max)
                expressionLineEdit.setText(param.expr)
                varyCheckbox.setChecked(param.vary)

            self.param_grid_layout.addWidget(useCheckbox, n, 0)
            self.param_grid_layout.addWidget(parameterNameLabel, n, 1)
            self.param_grid_layout.addWidget(valueSpinbox, n, 2)
            self.param_grid_layout.addWidget(minimumSpinbox, n, 3)
            self.param_grid_layout.addWidget(maximumSpinbox, n, 4)
            self.param_grid_layout.addWidget(expressionLineEdit, n, 5)
            self.param_grid_layout.addWidget(varyCheckbox, n, 6)
            n += 1

        #self.fit_action_layout.addWidget(self.param_grid_layout)

    def updateFitSettings(self, parameters):
        """ Updates the fit parameters with the new values from the settings window
        """
        for name, param in parameters.items():
            self.paramUseSettings[name] = self.widgets[name + '_use'].checkState()
            param.use = self.paramUseSettings[name]
            param.value = self.widgets[name + '_value'].value()
            param.min = self.widgets[name + '_min'].value()
            param.max = self.widgets[name + '_max'].value()
            param.expr = str(self.widgets[name + '_expr'].displayText())
            param.vary = self.widgets[name + '_vary'].checkState()
        return self.paramUseSettings

    def keepFitSettings(self, parameters, paramUse):
        """ Keeps the old fit settings
        """
        for name, param in parameters.items():
            if parameters[name].value is not None and not math.isnan(param.value):
                self.paramUseSettings[name] = paramUse[name]
                self.widgets[name + '_use'].setChecked(paramUse[name])
                self.widgets[name + '_value'].setValue(param.value)
                self.widgets[name + '_min'].setValue(param.min)
                self.widgets[name + '_max'].setValue(param.max)
                self.widgets[name + '_expr'].setText(param.expr)
                self.widgets[name + '_vary'].setChecked(param.vary)
        return self.paramUseSettings
