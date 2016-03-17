# -*- coding: utf-8 -*-

"""
This file contains a widget for fit parameters.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015-2016 Florian S. Frank florian.frank@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015-2016 Jan M. Binder jan.binder@uni-ulm.de
"""

from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

class FitSettingsWidget(QtGui.QWidget):

    def __init__(self, parameters):
        """ Definition, configuration and initialisation of the optimizer settings GUI. Adds a row with the
            value, min, max and vary for each variable in parameters.
        """
        super().__init__()

        self._Layout = QtGui.QGridLayout(self)  # Creation of the form Layout ( Maybe grid would be better )
        self.custom_params_checkbox = QtGui.QCheckBox('Use custom values')
        self._Layout.addWidget(self.custom_params_checkbox, 0, 0)
        self.valueLabel = QtGui.QLabel('Value')
        self.minimumLabel = QtGui.QLabel('Min')
        self.maximumLabel = QtGui.QLabel('Max')
        self.varyLabel = QtGui.QLabel('Vary')
        self._Layout.addWidget(self.valueLabel, 1, 1)
        self._Layout.addWidget(self.minimumLabel, 1, 2)
        self._Layout.addWidget(self.maximumLabel, 1, 3)
        self._Layout.addWidget(self.varyLabel, 1, 4)

        self.widgets = {}
        n = 2
        for name in parameters:
            self.widgets[name+"_label"] = parameterNameLabel = QtGui.QLabel(str(name))
            self.widgets[name+'_value'] = valueSpinbox =  QtGui.QDoubleSpinBox()
            self.widgets[name+'_min'] = minimumSpinbox = QtGui.QDoubleSpinBox()
            self.widgets[name+'_max'] = maximumSpinbox = QtGui.QDoubleSpinBox()
            self.widgets[name+'_vary'] = varyCheckbox = QtGui.QCheckBox()
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
            if not parameters[str(name)].value == None:
                valueSpinbox.setValue(parameters[str(name)].value)
                minimumSpinbox.setValue(parameters[str(name)].min)
                minimumSpinbox.setValue(parameters[str(name)].max)
                varyCheckbox.setChecked(parameters[str(name)].vary)
            
            self._Layout.addWidget(parameterNameLabel, n, 0)
            self._Layout.addWidget(valueSpinbox, n, 1)
            self._Layout.addWidget(minimumSpinbox, n, 2)
            self._Layout.addWidget(maximumSpinbox, n, 3)
            self._Layout.addWidget(varyCheckbox, n, 4)
            n += 1

    def updateFitSettings(self, parameters):
        """ Updates the fit parameters with the new values from the settings window
        """
        for name in parameters:
            parameters[name].value = self.widgets[name+'_value'].value()
            parameters[name].min = self.widgets[name+'_min'].value()
            parameters[name].max = self.widgets[name+'_max'].value()
            parameters[name].vary = self.widgets[name+'_vary'].checkState()
        return self.custom_params_checkbox.isChecked()

    def keepFitSettings(self, parameters, use_custom_parameters):
        """ Keeps the old fit settings
        """
        for name in parameters:
            if not parameters[name].value == None:
                self.widgets[name+'_value'].setValue(parameters[name].value)
                self.widgets[name+'_min'].setValue(parameters[name].min)
                self.widgets[name+'_max'].setValue(parameters[name].max)
                self.widgets[name+'_vary'].setChecked(parameters[name].vary)
        self.custom_params_checkbox.setChecked(use_custom_parameters)

