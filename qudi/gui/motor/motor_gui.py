# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for Motor control.

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
from qudi.core.connector import Connector
from qudi.core.util import units
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtWidgets, QtGui
from qudi.core.util.paths import get_artwork_dir
from qudi.core.gui.uic import loadUi


class MotorMainWindow(QtWidgets.QMainWindow):
    """ The main window for the Motor GUI
        """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'motor.ui')

        # Load it
        super().__init__(**kwargs)
        loadUi(ui_file, self)

        # self.setTabPosition(QtCore.Qt.TopDockWidgetArea, QtWidgets.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtWidgets.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setWindowTitle('qudi: Motor')

        # # Create QActions
        # icon_path = os.path.join(get_artwork_dir(), 'icons')
        #
        # icon = QtGui.QIcon(os.path.join(icon_path, 'qudiTheme', '22x22', 'start-counter.png'))
        # icon.addFile(os.path.join(icon_path, 'qudiTheme', '22x22', 'stop-counter.png'),
        #              state=QtGui.QIcon.On)


class MotorGui(GuiBase):
    """
    This is the GUI Class for Motor operations
    """

    # declare connectors
    _motor_logic = Connector(name='motor_logic', interface='MotorLogic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self._mw = MotorMainWindow()
        self._mw.setDockNestingEnabled(True)
        self.constraints = self.motor_logic().constraints
        self._mw.motor_x_move_negative.connect()

    def show(self):
        """
        Make window visible and put it above all other windows.
        """
        self._mw.show()
        self._mw.raise_()
        self._mw.activateWindow()
        return

    def on_deactivate(self):
        self._mw.motor_x_move_negative.disconnect()

    def motor_x_move_negative(self):
        print(self._mw.lineEdit_x.text)

