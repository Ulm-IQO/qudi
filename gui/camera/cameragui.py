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

from core.connector import Connector
from gui.colordefs import QudiPalettePale as Palette
from gui.guibase import GUIBase
from gui.colordefs import ColorScaleInferno

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic
from gui.guiutils import ColorBar

import numpy as np

import time

class CameraSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_camera_settings.ui')

        # Load it
        super(CameraSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


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

    camera_logic = Connector(interface='CameraLogic')
    savelogic = Connector(interface='SaveLogic')

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
        self._save_logic = self.savelogic()

        # Windows
        self._mw = CameraWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.initSettingsUI()

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

        # connect Settings action under Options menu
        self._mw.actionSettings.triggered.connect(self.menu_settings)
        # connect save action to save function
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan_data)

        raw_data_image = self._logic.get_last_image()
        self._image = pg.ImageItem(image=raw_data_image, axisOrder='row-major')
        self._mw.image_PlotWidget.addItem(self._image)
        self._mw.image_PlotWidget.setAspectLocked(True)

        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleInferno()

        self._image.setLookupTable(self.my_colors.lut)

        # Connect the buttons and inputs for the colorbar
        self._mw.xy_cb_manual_RadioButton.clicked.connect(self.update_xy_cb_range)
        self._mw.xy_cb_centiles_RadioButton.clicked.connect(self.update_xy_cb_range)

        self._mw.xy_cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)
        self._mw.xy_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)

        # create color bar
        self.xy_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self.depth_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xy_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c')
        self._mw.xy_cb_ViewWidget.setMouseEnabled(x=False, y=False)

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

    def initSettingsUI(self):
        """ Definition, configuration and initialisation of the settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._sd = CameraSettingDialog()
        # Connect the action of the settings window with the code:
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_settings)

        # write the configuration to the settings window of the GUI.
        self.keep_former_settings()

    def update_settings(self):
        """ Write new settings from the gui to the file. """
        self._logic.set_exposure(self._sd.exposureDSpinBox.value())
        self._logic.set_gain(self._sd.gainSpinBox.value())

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._sd.exposureDSpinBox.setValue(self._logic._exposure)
        self._sd.gainSpinBox.setValue(self._logic._gain)

    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

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
        self.update_xy_cb_range()
        # self._image.setImage(image=raw_data_image, levels=levels)

    def updateView(self):
        """
        Update the view when the model change
        """
        pass

# color bar functions
    def get_xy_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.xy_cb_manual_RadioButton.isChecked() or np.max(self._image.image) == 0.0:
            cb_min = self._mw.xy_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.xy_cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # xy_image_nonzero = self._image.image[np.nonzero(self._image.image)]

            # Read centile range
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(self._image.image, low_centile)
            cb_max = np.percentile(self._image.image, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def refresh_xy_colorbar(self):
        """ Adjust the xy colorbar.

        Calls the refresh method from colorbar, which takes either the lowest
        and higherst value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """
        cb_range = self.get_xy_cb_range()
        self.xy_cb.refresh_colorbar(cb_range[0], cb_range[1])

    def refresh_xy_image(self):
        """ Update the current XY image from the logic.

        Everytime the scanner is scanning a line in xy the
        image is rebuild and updated in the GUI.
        """
        self._image.getViewBox().updateAutoRange()

        xy_image_data = self._logic._last_image

        cb_range = self.get_xy_cb_range()

        # Now update image with new color scale, and update colorbar
        self._image.setImage(image=xy_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_xy_colorbar()

    def shortcut_to_xy_cb_manual(self):
        """Someone edited the absolute counts range for the xy colour bar, better update."""
        self._mw.xy_cb_manual_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def shortcut_to_xy_cb_centiles(self):
        """Someone edited the centiles range for the xy colour bar, better update."""
        self._mw.xy_cb_centiles_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def update_xy_cb_range(self):
        """Redraw xy colour bar and scan image."""
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

# save functions

    def save_xy_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal data."""
        cb_range = self.get_xy_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.xy_cb_manual_RadioButton.isChecked():
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._logic.save_xy_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        filepath = self._save_logic.get_path_for_module(module_name='Confocal')
        filename = filepath + os.sep + time.strftime('%Y%m%d-%H%M-%S_confocal_xy_scan_raw_pixel_image')

        self._image.save(filename + '_raw.png')

