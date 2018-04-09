# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrometer camera logic module.

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
import pyqtgraph as pg

from core.module import Connector
from gui.colordefs import QudiPalettePale as Palette
from gui.guibase import GUIBase

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic


class CameraWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_spectro_camera.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class CameraGUI(GUIBase):
    """ Main spectrometer camera class.
    """
    _modclass = 'CameraGui'
    _modtype = 'gui'

    camera_logic = Connector(interface='CameraLogic')

    def __init__(self, config, **kwargs):
        self.camera_logic = None
        self.save_logic = None

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._camera_logic = self.camera_logic()

        # Windows
        self._mw = CameraWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self._mw.action_start.setEnabled(True)
        self._mw.action_abort.setEnabled(False)

        # Cooling dependent GUI
        self.constraints = self._camera_logic.get_constraints()

        if self.constraints.cooler is True:
            self._mw.cooling_on_checkbox.setValue(self._camera_logic.get_cooler_on_state())
        else:
            self._mw.temperatureControllerWidget.setEnabled(False)
            self._mw.temperatureCurvesWidget.setEnabled(False)



    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

