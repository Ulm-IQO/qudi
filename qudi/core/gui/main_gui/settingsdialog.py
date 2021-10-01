# -*- coding: utf-8 -*-
"""
This file contains a settings dialog for the qudi main GUI.

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

from PySide2 import QtCore, QtWidgets


class SettingsDialog(QtWidgets.QDialog):
    """
    Custom QDialog widget for configuration of the qudi main GUI
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setWindowTitle('Qudi: Main GUI settings')

        # Create main layout
        # Add widgets to layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.setRowStretch(1, 1)
        self.setLayout(layout)

        # Create widgets and add them to the layout
        self.font_size_spinbox = QtWidgets.QSpinBox()
        self.font_size_spinbox.setObjectName('fontSizeSpinBox')
        self.font_size_spinbox.setMinimum(5)
        self.font_size_spinbox.setValue(10)
        label = QtWidgets.QLabel('Console font size:')
        label.setObjectName('fontSizeLabel')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.font_size_spinbox, 0, 1)

        self.color_theme_combobox = QtWidgets.QComboBox()
        self.color_theme_combobox.setObjectName('colorThemeComboBox')
        self.color_theme_combobox.addItems(['linux', 'lightBG'])
        label = QtWidgets.QLabel('Console color theme:')
        label.setObjectName('colorThemeLabel')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.color_theme_combobox, 1, 1)

        self.show_error_popups_checkbox = QtWidgets.QCheckBox()
        self.show_error_popups_checkbox.setObjectName('showErrorPopupsCheckbox')
        self.show_error_popups_checkbox.setChecked(True)
        label = QtWidgets.QLabel('Show error popups:')
        label.setObjectName('showErrorPopupsLabel')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.show_error_popups_checkbox, 2, 1)

        buttonbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok
                                               | QtWidgets.QDialogButtonBox.Cancel
                                               | QtWidgets.QDialogButtonBox.Apply)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        layout.addWidget(buttonbox, 3, 0, 1, 2)

        # Add internal signals
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        buttonbox.button(buttonbox.Apply).clicked.connect(self.accepted)
