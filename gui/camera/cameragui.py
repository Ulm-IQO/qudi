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

from core.module import Connector, ConfigOption, StatusVar
from gui.colordefs import QudiPalettePale as palette
import numpy as np


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

    _pixel_size_x = ConfigOption('pixel_size_x', 1)
    _pixel_size_y = ConfigOption('pixel_size_y', 1)

    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()
    _image = []
    _logic = None
    _mw = None

    _exposure = None
    _gain = None
    _mask = None

    _raw_data_image = None
    _image_size = None

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

        self._mw.start_control_Action.setEnabled(True)
        self._mw.start_control_Action.setChecked(self._logic.enabled)
        self._mw.start_control_Action.triggered.connect(self.start_clicked)
        self._mw.image_meter_control_dockwidget.hide()  # The meter control is initially turned off

        self._logic.sigUpdateDisplay.connect(self.update_data)

        self.sigStart.connect(self._logic.startLoop)
        self.sigStop.connect(self._logic.stopLoop)

        self._mw.expos_current_InputWidget.editingFinished.connect(self.update_from_input_exposure)
        self._mw.gain_current_InputWidget.editingFinished.connect(self.update_from_input_gain)

        # Show the image measured
        self._image = pg.ImageItem(image=self._raw_data_image, axisOrder='row-major')
        self._mw.image_PlotWidget.addItem(self._image)
        self._mw.image_PlotWidget.setAspectLocked(True)

        self.update_view()
        self.update_units()

    def update_input_exposure(self, exposure):
        """ Updates the displayed exposure.

        @param float exposure: the current value of the exposure
        """
        self._mw.expos_current_InputWidget.setValue(exposure)

    def update_from_input_exposure(self):
        """ If the user changes the exposition time in the box, adjusts the corresponding hardware parameter
        """
        self._logic.set_exposure(self._mw.expos_current_InputWidget.value())

    def update_input_gain(self, gain):
        """ Updates the displayed gain.

         @param float gain: the current value of the gain
         """
        self._mw.gain_current_InputWidget.setValue(gain)

    def update_from_input_gain(self):
        """ If the user changes the gain in the box, adjusts the corresponding hardware parameter
        """
        self._logic.set_gain(self._mw.gain_current_InputWidget.value())

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

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """

        if self._logic.enabled:
            self._mw.start_control_Action.setText('Start')
            self.sigStop.emit()
        else:
            self._mw.start_control_Action.setText('Stop')
            self.sigStart.emit()

    def update_data(self):
        """ Get the image data from the logic and print it on the window
        """

        self._raw_data_image = self._logic.get_last_image()
        self._image.setImage(image=self._raw_data_image)
        #self._image.setImage(image=self._raw_data_image, levels=levels)

    def update_view(self):
        """ Update the view when the model change
        """
        self._mw.expos_current_InputWidget.setValue(self._logic.get_exposure())
        self._mw.gain_current_InputWidget.setValue(self._logic.get_gain())

    def update_units(self):
        """ Update the units on the graph

         Update the units on the graph and the view of the meter control windows, depending of the activation
         of the meter mode.
        """
        if self._mw.actionPhysical_position.isChecked():
            x_text, x_unit, x_size = ('X position', "Meter", self._pixel_size_x)
            y_text, y_unit, y_size = ('Y position', "Meter", self._pixel_size_y)
            self._mw.image_meter_control_dockwidget.show()
        else:
            x_text, x_unit, x_size = ('X position', "Pixel", 1)
            y_text, y_unit, y_size = ('Y position', "Pixel", 1)
            self._mw.image_meter_control_dockwidget.hide()

        x_axis = self._mw.image_PlotWidget.getAxis('bottom')
        x_axis.setLabel(x_text, units=x_unit)
        x_axis.setScale(x_size)

        y_axis = self._mw.image_PlotWidget.getAxis('left')
        y_axis.setLabel(y_text, units=y_unit)
        y_axis.setScale(y_size)
