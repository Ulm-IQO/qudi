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
        self.lable00 = QtGui.QLabel('Value')
        self.lable01 = QtGui.QLabel('Min')
        self.lable02 = QtGui.QLabel('Max')
        self.lable03 = QtGui.QLabel('Vary')
        self._Layout.addWidget(self.lable00, 1, 0)
        self._Layout.addWidget(self.lable01, 1, 1)
        self._Layout.addWidget(self.lable02, 1, 2)
        self._Layout.addWidget(self.lable03, 1, 3)

        self.widgets = {}
        n = 2
        for name in parameters:
            self.widgets[name] = widget = {}
            self.widgets[name+'min'] = widget2 = {}
            self.widgets[name+'max'] = widget3 = {}
            self.widgets[name+'vary'] = widget4 = {}
            widget['spinbox'] = spinbox = QtGui.QDoubleSpinBox()
            widget2['spinbox'] = spinbox2 = QtGui.QDoubleSpinBox()
            widget3['spinbox'] = spinbox3 = QtGui.QDoubleSpinBox()
            widget4['checkbox'] = checkbox = QtGui.QCheckBox()
            spinbox.setDecimals(3)
            spinbox.setSingleStep(0.01)
            spinbox.setMaximum(np.inf)
            spinbox.setMinimum(-np.inf)
            spinbox2.setDecimals(3)
            spinbox2.setSingleStep(0.01)
            spinbox2.setMaximum(np.inf)
            spinbox2.setMinimum(-np.inf)
            spinbox3.setDecimals(3)
            spinbox3.setSingleStep(0.01)
            spinbox3.setMaximum(np.inf)
            spinbox3.setMinimum(-np.inf)
            if not parameters[str(name)].value == None:
                spinbox.setValue(parameters[str(name)].value)
                spinbox2.setValue(parameters[str(name)].min)
                spinbox2.setValue(parameters[str(name)].max)
                checkbox.setChecked(parameters[str(name)].vary)
            
            self._Layout.addWidget(spinbox, n, 0)
            self._Layout.addWidget(spinbox2, n, 1)
            self._Layout.addWidget(spinbox3, n, 2)
            self._Layout.addWidget(checkbox, n, 3)
            n += 1

    def updateFitSettings(self, parameters):
        """ Updates the fit parameters with the new values from the settings window
        """
        for name in parameters:
            parameters[str(name)].value = self.widgets[name]['spinbox'].value()
            parameters[str(name)].min = self.widgets[name+'min']['spinbox'].value()
            parameters[str(name)].max = self.widgets[name+'max']['spinbox'].value()
            parameters[str(name)].vary = self.widgets[name+'vary']['checkbox'].checkState()
        return self.custom_params_checkbox.isChecked()

    def keepFitSettings(self, parameters, use_custom_parameters):
        """ Keeps the old fit settings
        """
        for name in parameters:
            if not parameters[str(name)].value == None:
                self.widgets[name]['spinbox'].setValue(parameters[str(name)].value)
                self.widgets[name+'min']['spinbox'].setValue(parameters[str(name)].min)
                self.widgets[name+'max']['spinbox'].setValue(parameters[str(name)].max)
                self.widgets[name+'vary']['checkbox'].setChecked(parameters[str(name)].vary)
        self.custom_params_checkbox.setChecked(use_custom_parameters)

