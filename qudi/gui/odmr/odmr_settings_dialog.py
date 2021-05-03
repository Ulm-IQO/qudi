# -*- coding: utf-8 -*-

"""
This file contains a QDialog subclass to edit less frequently used ODMR measurement parameters.

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

__all__ = ('OdmrSettingsDialog',)

import numpy as np
from PySide2 import QtCore, QtWidgets
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.util.units import ScaledFloat


class OdmrSettingsDialog(QtWidgets.QDialog):
    """ Dialog class for editing less frequently used ODMR measurement settings.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ODMR Settings')

        # Spinbox defining maximum scan matrix lines shown
        self.max_scans_shown_spinbox = QtWidgets.QSpinBox()
        self.max_scans_shown_spinbox.setRange(1, 2 ** 31 - 1)
        self.max_scans_shown_spinbox.setValue(50)
        # Spinbox defining data rate for scans (defining the spacing between shown data points)
        # This is NOT the hardware sample rate for the scan (would be oversampling * data_rate)
        self.data_rate_spinbox = ScienDSpinBox()
        self.data_rate_spinbox.setSuffix('Hz')
        self.data_rate_spinbox.setRange(0, np.inf)
        self.data_rate_spinbox.setValue(100)
        self.data_rate_spinbox.valueChanged.connect(self._sample_rate_changed)
        # Spinbox defining oversampling factor for scans.
        self.oversampling_spinbox = QtWidgets.QSpinBox()
        self.oversampling_spinbox.setRange(1, 2 ** 31 - 1)
        self.oversampling_spinbox.setValue(1)
        self.oversampling_spinbox.valueChanged.connect(self._sample_rate_changed)
        # label showing the resulting hardware sample rate (oversampling * data_rate)
        self.sample_rate_label = QtWidgets.QLabel('')
        self.sample_rate_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self._sample_rate_changed()

        # Buttonbox for this QDialog
        buttons = QtWidgets.QDialogButtonBox.Ok | \
                  QtWidgets.QDialogButtonBox.Apply | \
                  QtWidgets.QDialogButtonBox.Cancel
        self.button_box = QtWidgets.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # create main layout
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        label = QtWidgets.QLabel('Data Rate:')
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.data_rate_spinbox, 0, 1)
        label = QtWidgets.QLabel('Oversampling Factor:')
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.oversampling_spinbox, 1, 1)
        label = QtWidgets.QLabel('Resulting Sample Rate:')
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.sample_rate_label, 2, 1)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(hline, 3, 0, 1, 2)
        label = QtWidgets.QLabel('Max. Displayed Number of Scans:')
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        layout.addWidget(label, 4, 0)
        layout.addWidget(self.max_scans_shown_spinbox, 4, 1)
        layout.addWidget(self.button_box, 5, 0, 1, 2)
        layout.setColumnStretch(1, 1)

    @QtCore.Slot()
    def _sample_rate_changed(self):
        data_rate = self.data_rate_spinbox.value()
        oversampling = self.oversampling_spinbox.value()
        digits = self.data_rate_spinbox.decimals()
        self.sample_rate_label.setText('{rate:.{dig}r}Hz'.format(
            rate=ScaledFloat(oversampling * data_rate),
            dig=digits)
        )
