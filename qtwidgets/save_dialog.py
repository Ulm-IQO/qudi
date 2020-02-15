# -*- coding: utf-8 -*-

"""
Simple window-modal dialog for locking GUIs during save operations.

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
from qtpy.QtWidgets import QDialog
from qtpy import uic
from qtpy import QtCore

class SaveDialog(QDialog):
    """ Simple modal dialog to indicate saving in progress """
    def __init__(self, parent=None):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_save_dialog.ui')

        # Load it
        super(SaveDialog, self).__init__(parent=parent)
        uic.loadUi(ui_file, self)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)