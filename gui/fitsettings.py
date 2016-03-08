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

Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015-2016 Jan M. Binder jan.binder@uni-ulm.de
"""

from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

class FitSettingsWidget(QtGui.QWidget):

    def __init__(self, parameters):
        """ Definition, configuration and initialisation of the optimizer settings GUI.
        """
        super().__init__()

        self.form_Layout = QtGui.QFormLayout(self)
        self.custom_params_checkbox = QtGui.QCheckBox(self)
        self.form_Layout.addRow('use custom', self.custom_params_checkbox)

        self.widgets = {}
        for name in parameters:
            self.widgets[name] = widget = {}
            widget['spinbox'] = spinbox = QtGui.QDoubleSpinBox()
            spinbox.setDecimals(3)
            spinbox.setSingleStep(0.01)
            spinbox.setMaximum(np.inf)
            spinbox.setMinimum(-np.inf)
            if not parameters[str(name)].value == None:
                spinbox.setValue(parameters[str(name)].value)
            self.form_Layout.addRow(name, spinbox)

    def updateFitSettings(self, parameters):
        for name in parameters:
            parameters[str(name)].value = self.widgets[name]['spinbox'].value()
        return self.custom_params_checkbox.isChecked()

    def keepFitSettings(self, parameters, use_custom_parameters):
        for name in parameters:
            if not parameters[str(name)].value == None:
                self.widgets[name]['spinbox'].setValue(parameters[str(name)].value)
        self.custom_params_checkbox.setChecked(use_custom_parameters)

