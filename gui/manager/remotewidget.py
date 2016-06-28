# -*- coding: utf-8 -*-
"""
This file contains the QuDi remote widget class.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
from pyqtgraph.Qt import QtGui, QtCore, uic
import os

class RemoteWidget(QtGui.QWidget):

    def __init__(self):
        super().__init__()
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_remotewidget.ui')

        # Load it
        uic.loadUi(ui_file, self)


