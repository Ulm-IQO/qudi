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
from gui.guiutils import ColorBar


class CameraWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_camera.ui')

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

    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()
    sigImageStop = QtCore.Signal()

    _image = []

    _logic = None
    _mw = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._logic = self.camera_logic()

        # Windows
        self._mw = CameraWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self._mw.start_video_Action.setEnabled(True)
        self._mw.start_video_Action.setChecked(self._logic.enabled)
        self._mw.start_video_Action.triggered.connect(self.start_video_clicked)

        self._mw.start_image_Action.setEnabled(True)
        self._mw.start_image_Action.setChecked(self._logic.enabled)
        self._mw.start_image_Action.triggered.connect(self.start_image_clicked)

        self._logic.sigUpdateDisplay.connect(self.update_data)
        self._logic.sigAcquisitionFinished.connect(self.acquisition_finished)
        self._logic.sigVideoFinished.connect(self.enable_start_image_action)

        # starting the physical measurement
        self.sigVideoStart.connect(self._logic.start_loop)
        self.sigVideoStop.connect(self._logic.stop_loop)
        self.sigImageStart.connect(self._logic.start_single_acquistion)

        raw_data_image = self._logic.get_last_image()
        self._image = pg.ImageItem(image=raw_data_image, axisOrder='row-major')
        self._mw.image_PlotWidget.addItem(self._image)
        self._mw.image_PlotWidget.setAspectLocked(True)
        # self.xy_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        # self.depth_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        # self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)

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

    def start_image_clicked(self):
        self.sigImageStart.emit()
        self._mw.start_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)

    def acquisition_finished(self):
        self._mw.start_image_Action.setChecked(False)
        self._mw.start_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)

    def start_video_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        self._mw.start_image_Action.setDisabled(True)
        if self._logic.enabled:
            self._mw.start_video_Action.setText('Start Video')
            self.sigVideoStop.emit()
        else:
            self._mw.start_video_Action.setText('Stop Video')
            self.sigVideoStart.emit()

    def enable_start_image_action(self):
        self._mw.start_image_Action.setEnabled(True)

    def update_data(self):
        """
        Get the image data from the logic and print it on the window
        """
        raw_data_image = self._logic.get_last_image()
        levels = (0., 1.)
        self._image.setImage(image=raw_data_image)
        # self._image.setImage(image=raw_data_image, levels=levels)

    def updateView(self):
        """
        Update the view when the model change
        """
        pass

