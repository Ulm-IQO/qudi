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

import logging
logger = logging.getLogger(__name__)


class FitSettingsDialog(QtWidgets.QDialog):

    sigFitsUpdated = QtCore.Signal(dict)
    sigParametersUpdated = QtCore.Signal()

    def __init__(self, all_functions, my_functions, title='Fit Settings'):
        """ """
        super().__init__()
        self.setModal(False)
        self.setWindowTitle(title)
        self.title = title
        self.all_functions = all_functions
        self.tabs = {}
        self.parameters = {}
        self.parameter_use = {}
        self.user_fits = OrderedDict()
        self.fitWidgets = OrderedDict()

        self._dialogLayout = QtWidgets.QVBoxLayout()
        self._tabWidget = QtWidgets.QTabWidget()
        self._firstPage = QtWidgets.QWidget()
        self._firstPageLayout = QtWidgets.QVBoxLayout()
        self._scrollArea = QtWidgets.QScrollArea()
        self._scrollWidget = QtWidgets.QWidget()
        self._scrLayout = QtWidgets.QVBoxLayout()
        self._dbox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal
        )
        self._addFitButton = QtWidgets.QPushButton('Add fit')

        self._scrollWidget.setLayout(self._scrLayout)
        self._scrollArea.setWidget(self._scrollWidget)
        self._scrollArea.setWidgetResizable(True)
        self._firstPageLayout.addWidget(self._addFitButton)
        self._firstPageLayout.addWidget(self._scrollArea)
        self._firstPage.setLayout(self._firstPageLayout)
        self._tabWidget.addTab(self._firstPage, 'Fit functions')
        self._dialogLayout.addWidget(self._addFitButton)
        self._dialogLayout.addWidget(self._tabWidget)
        self._dialogLayout.addWidget(self._dbox)
        self.setLayout(self._dialogLayout)

        self._dbox.accepted.connect(self.accept)
        self._dbox.rejected.connect(self.reject)
        self._dbox.clicked.connect(self.buttonClicked)
        self.accepted.connect(self.updateSettings)
        self.rejected.connect(self.restoreSettings)
        self._addFitButton.clicked.connect(self.addFitButtonClicked)

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def buttonClicked(self, button):
        if self._dbox.buttonRole(button) ==  QtWidgets.QDialogButtonBox.ApplyRole:
            self.updateSettings()

    @QtCore.Slot()
    def addFitButtonClicked(self):
        res = QtWidgets.QInputDialog.getText(
            self,
            'New fit',
            'Enter a name for this fit:',
            )
        print(res)
        if res[1]:
            self.addFit(res[0])

    def loadFits(self, user_fits):
        """ """
        for name, fit in self.all_functions.items():
            self._scrLayout.addWidget(self.checkboxes[name])

    def addFit(self, name):
        if len(name) < 1:
            return
        if name in self.fitWidgets:
            logging.error('{0}: Fit {1} already exists.'.format(self.title, name))
            return

        fcw = FitConfigWidget(name, self.all_functions)
        self.fitWidgets[name] = fcw
        self._scrLayout.addWidget(fcw)
        fcw.show()

    def removeFit(self, name):
        pass

    def getFits(self):
        """ """
        return
    
    def restoreSettings(self):
        """ """
        pass

    def updateSettings(self):
        """ """
        pass

    def getParameters(self, fit_name):
        """ """
        return self.parameters[fit_]

    def setParameters(self, fit_name, parameters):
        """ """
        self.sigParametersUpdated.emit()


class FitSettingsComboBox(QtWidgets.QComboBox):
   
    sigFitUpdated = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)
        self.fit_functions = OrderedDict()
        self.fit_functions['No Fit'] = None
        self.addItem('No Fit')
        self.setCurrentIndex(self.findText('No Fit'))

    def setFitFunctions(self, user_fits):
        """ """
        current = self.getCurrentFit()
        self.clear()
        self.fit_functions = OrderedDict()
        self.fit_functions['No Fit'] = None
        self.addItem('No Fit')

        for name, fit in user_fits.items():
            self.fit_functions[name] = fit
            self.addItem(name)

        if current[0] in self.fit_functions:
            self.setCurrentIndex(self.findText(current[0]))
        else:
            self.setCurrentIndex(self.findText('No Fit'))
        self.sigFitUpdated.emit()

    def getFitFunctions(self):
        return self.fit_functions

    def getCurrentFit(self):
        """ """
        name = self.currentText()
        return (name, self.fit_functions[name])

class FitConfigWidget(QtWidgets.QWidget):

    sigRemoveFit = QtCore.Signal(str)

    def __init__(self, name, all_fits):
        super().__init__()
        self.name = name
        self.all_fits = all_fits

        self.nameLabel = QtWidgets.QLabel(name)
        self.fitComboBox = QtWidgets.QComboBox()
        self.estComboBox = QtWidgets.QComboBox()
        self.delButton = QtWidgets.QToolButton()

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self.nameLabel)
        self._layout.addWidget(self.fitComboBox)
        self._layout.addWidget(self.estComboBox)
        self._layout.addWidget(self.delButton)

        self.setLayout(self._layout)

        for name, fit in self.all_fits.items():
            if 'make_fit' in fit and 'make_model' in fit:
                self.fitComboBox.addItem(name)

        self.fitComboBox.activated.connect(self.fitChanged)
        self.estComboBox.activated.connect(self.estimatorChanged)
        self.delButton.clicked.connect(self.removeWidget)
        print('Fit widget {0} online!'.format(self.name))

    @QtCore.Slot(int)
    def fitChanged(self, index):
        name = self.fitComboBox.itemText(index)
        self.estComboBox.clear()
        for estimator in self.all_fits[name]:
            if not estimator.startswith('make_'):
                self.estComboBox.addItem(estimator)
        print(name)

    @QtCore.Slot(int)
    def estimatorChanged(self, index):
        name = self.estComboBox.itemText(index)
        print(name)

    def updateSettings(self):
        self.fit = self.fitComboBox.currentText()
        self.estimator = self.estComboBox.currentText()

    def resetSettings(self):
        self.fitComboBox.setIndex(self.fitComboBox.findText(self.fit))
        self.fitChanged(self.fit)
        self.estComboBox.setIndex(self.estComboBox.findText(self.estimator))
        self.estimatorChanged(self.estimator)

    def removeWidget(self):
        self.hide()
        self.sigRemoveFit.emit(self.name)

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

