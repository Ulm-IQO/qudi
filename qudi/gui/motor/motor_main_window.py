# -*- coding: utf-8 -*-
"""
This file contains the qudi main window for the Motor GUI module.

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
import datetime
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.util.paths import get_artwork_dir

# __all__ = ('OdmrMainWindow',)


class MotorMainWindow(QtWidgets.QMainWindow):
    """ The main window for the Motor GUI
        """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('qudi: Motor')

        # Create QActions
        icon_path = os.path.join(get_artwork_dir(), 'icons')

        icon = QtGui.QIcon(os.path.join(icon_path, 'qudiTheme', '22x22', 'start-counter.png'))
        icon.addFile(os.path.join(icon_path, 'qudiTheme', '22x22', 'stop-counter.png'),
                     state=QtGui.QIcon.On)
