# -*- coding: utf-8 -*-
"""
This file contains a console settings dialog for the Qudi manager GUI.

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

import os
from qtpy import QtCore, QtGui, QtWidgets


class ConsoleSettingsDialog(QtWidgets.QDialog):
    """
    Custom QDialog widget for console configuration of the Qudi manager GUI
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Create widgets
        self.font_size_spinbox = QtWidgets.QSpinBox()
        self.font_size_spinbox.setObjectName('fontSizeSpinBox')
        self.font_size_spinbox.setMinimum(5)
        self.font_size_spinbox.setValue(10)
        label = QtWidgets.QLabel('Font size:')
        label.setObjectName('fontSizeLabel')
        buttonbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok
                                               | QtWidgets.QDialogButtonBox.Cancel
                                               | QtWidgets.QDialogButtonBox.Apply)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)

        # Add widgets to layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.font_size_spinbox, 0, 1)
        layout.setRowStretch(1, 1)
        layout.addWidget(buttonbox, 2, 0, 1, 2)
        self.setLayout(layout)

        # Add internal signals
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        buttonbox.button(buttonbox.Apply).clicked.connect(self.accepted)
