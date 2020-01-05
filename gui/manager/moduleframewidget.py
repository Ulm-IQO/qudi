# -*- coding: utf-8 -*-
"""
This file contains a custom module widget for the Qudi manager GUI.

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
from qtpy import QtGui, QtWidgets


class ModuleFrameWidget(QtWidgets.QFrame):
    """
    Custom module QFrame widget for the Qudi manager GUI
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Create QToolButtons
        self.cleanup_button = QtWidgets.QToolButton()
        self.cleanup_button.setObjectName('cleanupButton')
        self.deactivate_button = QtWidgets.QToolButton()
        self.deactivate_button.setObjectName('deactivateButton')
        self.reload_button = QtWidgets.QToolButton()
        self.reload_button.setObjectName('reloadButton')

        # Set icons for QToolButtons
        icon_path = os.path.join(os.getcwd(), 'artwork', 'icons', 'oxygen', '22x22')
        self.cleanup_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-clear.png')))
        self.deactivate_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-delete.png')))
        self.reload_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'view-refresh.png')))

        # Create activation pushbutton
        self.load_button = QtWidgets.QPushButton('load/activate <module_name>')
        self.load_button.setObjectName('loadButton')
        self.load_button.setCheckable(True)
        self.load_button.setMinimumWidth(200)
        self.load_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.Fixed)

        # Create status label
        self.status_label = QtWidgets.QLabel('Module status goes here...')
        self.status_label.setObjectName('statusLabel')

        # Set tooltips
        self.cleanup_button.setToolTip('Clean up module status file')
        self.deactivate_button.setToolTip('Deactivate module')
        self.reload_button.setToolTip('Reload module')
        self.load_button.setToolTip('Load this module and all its dependencies')
        self.status_label.setToolTip('Displays module status information')

        # Combine all widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.load_button, 0, 0)
        layout.addWidget(self.reload_button, 0, 1)
        layout.addWidget(self.deactivate_button, 0, 2)
        layout.addWidget(self.cleanup_button, 0, 3)
        layout.addWidget(self.status_label, 1, 0, 1, 4)
        self.setLayout(layout)
