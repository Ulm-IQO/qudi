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

from qtpy import QtCore, QtWidgets
from collections import OrderedDict
from qtwidgets.scientific_spinbox import ScienDSpinBox
import numpy as np
import math


class FitSettingsDialog(QtWidgets.QDialog):

    sigSelectionUpdated = QtCore.Signal()
    sigParametersUpdated = QtCore.Signal()

    def __init__(self, all_functions):
        """ """
        super().__init__()
        self.setModal(False)
        self.all_functions = all_functions
        self.checkboxes = OrderedDict()
        self.tabs = {}
        self.parameters = {}
        self.parameter_use = {}

        self._dialogLayout = QtWidgets.QVBoxLayout()
        self._tabWidget = QtWidgets.QTabWidget()
        self._scrollArea = QtWidgets.QScrollArea()
        self._scrollWidget = QtWidgets.QWidget()
        self._scrLayout = QtWidgets.QVBoxLayout()
        self._dbox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal
        )

        for name, fit in self.all_functions.items():
            self.checkboxes[name] = QtWidgets.QCheckBox(name)
            self._scrLayout.addWidget(self.checkboxes[name])

        self._scrollWidget.setLayout(self._scrLayout)
        self._scrollArea.setWidget(self._scrollWidget)
        self._tabWidget.addTab(self._scrollArea, 'Fit functions')
        self._dialogLayout.addWidget(self._tabWidget)
        self._dialogLayout.addWidget(self._dbox)
        self.setLayout(self._dialogLayout)

        self.fitSelection = {name: box.checkState() for name, box in self.checkboxes.items()}
        self._dbox.accepted.connect(self.accept)
        self._dbox.rejected.connect(self.reject)
        self._dbox.clicked.connect(self.buttonClicked)
        self.accepted.connect(self.updateSettings)
        self.rejected.connect(self.restoreSettings)

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def buttonClicked(self, button):
        if self._dbox.buttonRole(button) ==  QtWidgets.QDialogButtonBox.ApplyRole:
            self.updateSettings()

    def setFitSelection(self, selection):
        """ """
        for name, state in selection.items():
            if name in self.checkboxes:
                self.checkboxes[name].setCheckState(state)
                self.fitSelection[name] = state

        self._tabWidget.clear()
        self._tabWidget.addTab(self._scrollArea, 'Fit functions')

        for name, box in self.checkboxes.items():
            if box.checkState():
                self.tabs[name] = FitSettingsWidget(self.all_functions[name][1])
                self._tabWidget.addTab(self.tabs[name], name)

        self.sigSelectionUpdated.emit()

    def getFitSelection(self):
        """ """
        return self.fitSelection

    def restoreSettings(self):
        """ """
        self.setFitSelection(self.fitSelection)

    def updateSettings(self):
        """ """
        for name, box in self.checkboxes.items():
            self.fitSelection[name] = box.checkState()

        self.setFitSelection(self.fitSelection)

    def getParameters(self, fit_function):
        """ """
        return self.parameters[fit_function]

    def setParameters(self, fit_function, parameters):
        """ """
        self.sigParametersUpdated.emit()


class FitSettingsComboBox(QtWidgets.QComboBox):
    
    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)


class FitSettingsWidget(QtWidgets.QWidget):

    def __init__(self, parameters):
        """ Definition, configuration and initialisation of the optimizer settings GUI. Adds a row
            with the value, min, max and vary for each variable in parameters.
        """
        super().__init__()

        self._Layout = QtWidgets.QGridLayout(self)  # Creation of the grid Layout
        self.useLabel = QtWidgets.QLabel('Edit?')
        self.valueLabel = QtWidgets.QLabel('Value')
        self.minimumLabel = QtWidgets.QLabel('Minimum')
        self.maximumLabel = QtWidgets.QLabel('Maximum')
        self.exprLabel = QtWidgets.QLabel('Expression')
        self.varyLabel = QtWidgets.QLabel('Vary?')

        self._Layout.addWidget(self.useLabel, 0, 0)
        self._Layout.addWidget(self.valueLabel, 0, 2)
        self._Layout.addWidget(self.minimumLabel, 0, 3)
        self._Layout.addWidget(self.maximumLabel, 0, 4)
        self._Layout.addWidget(self.exprLabel, 0, 5)
        self._Layout.addWidget(self.varyLabel, 0, 6)

        self.widgets = {}
        self.paramUseSettings = {}
        n = 2
        for name, param in parameters.items():
            self.paramUseSettings[name] = False
            self.widgets[name + '_use'] = useCheckbox = QtWidgets.QCheckBox()
            self.widgets[name + '_label'] = parameterNameLabel = QtWidgets.QLabel(str(name))
            self.widgets[name + '_value'] = valueSpinbox =  ScienDSpinBox()
            self.widgets[name + '_min'] = minimumSpinbox = ScienDSpinBox()
            self.widgets[name + '_max'] = maximumSpinbox = ScienDSpinBox()
            self.widgets[name + '_expr'] = expressionLineEdit = QtWidgets.QLineEdit()
            self.widgets[name + '_vary'] = varyCheckbox = QtWidgets.QCheckBox()
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

            self._Layout.addWidget(useCheckbox, n, 0)
            self._Layout.addWidget(parameterNameLabel, n, 1)
            self._Layout.addWidget(valueSpinbox, n, 2)
            self._Layout.addWidget(minimumSpinbox, n, 3)
            self._Layout.addWidget(maximumSpinbox, n, 4)
            self._Layout.addWidget(expressionLineEdit, n, 5)
            self._Layout.addWidget(varyCheckbox, n, 6)
            n += 1

        # space at the bottom
        self._Layout.setRowStretch(n, 1)

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

