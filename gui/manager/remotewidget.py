# -*- coding: utf-8 -*-
"""
# FIXME

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

from qtpy import QtCore, QtGui, QtWidgets


class RemoteWidget(QtWidgets.QWidget):
    """

    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Create widgets
        self.host_label = QtWidgets.QLabel('host')
        self.port_label = QtWidgets.QLabel('port')
        self.shared_module_listview = QtWidgets.QListView()
        self.shared_module_listview.setUniformItemSizes(True)
        self.shared_module_listview.setAlternatingRowColors(True)
        self.remote_module_listview = QtWidgets.QListView()
        self.remote_module_listview.setUniformItemSizes(True)
        self.remote_module_listview.setAlternatingRowColors(True)

        # Group widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.host_label, 0, 0)
        layout.addWidget(self.shared_module_listview, 1, 0)
        layout.addWidget(self.port_label, 0, 1)
        layout.addWidget(self.remote_module_listview, 1, 1)
        self.setLayout(layout)
