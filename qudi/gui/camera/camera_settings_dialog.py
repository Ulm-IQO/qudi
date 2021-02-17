# -*- coding: utf-8 -*-

"""
This module contains a custom QDialog subclass for the Camera GUI module.

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
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox

__all__ = ('CameraSettingsDialog',)


class CameraSettingsDialog(QtWidgets.QDialog):
    """ Create the camera settings dialog """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('qudi: Camera Settings')

        layout = QtWidgets.QGridLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)

        label = QtWidgets.QLabel('Exposure Time:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 0)
        self.exposure_spinbox = ScienDSpinBox()
        self.exposure_spinbox.setSuffix('s')
        self.exposure_spinbox.setMinimum(0)
        self.exposure_spinbox.setDecimals(3)
        self.exposure_spinbox.setMinimumWidth(100)
        layout.addWidget(self.exposure_spinbox, 0, 1)

        label = QtWidgets.QLabel('Gain:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 0)
        self.gain_spinbox = ScienDSpinBox()
        # ToDo: set proper unit for gain with self.gain_spinbox.setSuffix('s')
        self.gain_spinbox.setMinimum(0)
        self.gain_spinbox.setDecimals(3)
        self.gain_spinbox.setMinimumWidth(100)
        layout.addWidget(self.gain_spinbox, 1, 1)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                     QtWidgets.QDialogButtonBox.Cancel |
                                                     QtWidgets.QDialogButtonBox.Apply,
                                                     QtCore.Qt.Horizontal,
                                                     self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box, 2, 0, 1, 2)

        layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.setLayout(layout)
