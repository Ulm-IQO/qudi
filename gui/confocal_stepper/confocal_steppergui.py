# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for ODMR control.

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

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg
import numpy as np
import os
import time

from core.module import Connector, ConfigOption, StatusVar
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from core.util import units


class ConfocalStepperMainWindow(QtWidgets.QMainWindow):
    """ The main window for the ODMR measurement GUI.
    """

    sigPressKeyBoard = QtCore.Signal(QtCore.QEvent)

    def __init__(self):
        # Get the path to the *.ui filezorry
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_confocal_stepper_gui.ui')

        # Load it
        super(ConfocalStepperMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

        def keyPressEvent(self, event):
            """Pass the keyboard press event from the main window further. """
            self.sigPressKeyBoard.emit(event)


class ConfocalStepperSettingDialog(QtWidgets.QDialog):
    """ The settings dialog for ODMR measurements.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_cfs_settings.ui')

        # Load it
        super(ConfocalStepperSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class ConfocalStepperGui(GUIBase):
    """
    This is the GUI Class for Confocal measurements
    """

    _modclass = 'ConfocalStepperGui'
    _modtype = 'gui'

    # declare connectors
    confocallogic1 = Connector(interface='ConfocalLogic')
    savelogic = Connector(interface='SaveLogic')
    stepperlogic1 = Connector(interface='ConfocalStepperLogic')

    sigStartSteppingScan = QtCore.Signal()
    sigStopSteppingScan = QtCore.Signal()
    sigContinueSteppingScan = QtCore.Signal()
    sigClearData = QtCore.Signal()
    sigSaveMeasurement = QtCore.Signal(str, list, list)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        #self.log.info('The following configuration was found.')

        # checking for the right configuration
        #for key in config.keys():
        #    self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition, configuration and initialisation of the Confocal Stepper GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._stepper_logic = self.get_connector('stepperlogic1')
        self._scanning_logic = self.get_connector('confocallogic1')

        self.initMainUI()

        ########################################################################
        #                       Connect signals                                #
        ########################################################################


        # Show the Main SteppingConfocal GUI:
        self._show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        pass

    def initMainUI(self):
        """ Definition, configuration and initialisation of the confocal stepper GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        # Use the inherited class 'Ui_StepperGuiUI' to create now the GUI element:
        self._mw = ConfocalStepperMainWindow()
        self._sd = ConfocalStepperSettingDialog()

        ###################################################################
        #               Configuring the dock widgets                      #
        ###################################################################
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        #self._mw.scanLineDockWidget.hide()

        self.init_plot_step_UI()
        self.init_hardware_UI()
        self.init_step_parameters_UI()
        self.init_tilt_correction_UI()

        # Set the state button as ready button as default setting.
        self._mw.action_step_stop.setEnabled(False)
        self._mw.action_step_resume.setEnabled(False)

        # Connect other signals from the logic with an update of the gui

        self._stepper_logic.signal_start_stepping.connect(self.logic_started_stepping)
        self._stepper_logic.signal_continue_stepping.connect(self.logic_continued_stepping)
        # self._scanning_logic.signal_stop_scanning.connect()

        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._mw.actionSave_Step_Scan.triggered.connect(self.save_step_scan_data)

        #################################################################
        #                           Actions                             #
        #################################################################
        # Connect the scan actions to the events if they are clicked. Connect
        # also the adjustment of the displayed windows.
        self._mw.action_step_stop.triggered.connect(self.ready_clicked)

        self._step_start_proxy = pg.SignalProxy(
            self._mw.action_step_start.triggered,
            delay=0.1,
            slot=self.step_start_clicked
        )
        self._step_resume_proxy = pg.SignalProxy(
            self._mw.action_step_resume.triggered,
            delay=0.1,
            slot=self.step_continued_clicked
        )

        ###################################################################
        #               Icons for the scan actions                        #
        ###################################################################

        self._step_single_icon = QtGui.QIcon()
        self._step_single_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._step_loop_icon = QtGui.QIcon()
        self._step_loop_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-loop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

    def initSettingsUI(self):
        """ Definition, configuration and initialisation of the settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        # Todo: Fix
        self._sd = "a"
        # Connect the action of the settings window with the code:
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.update_settings)
        self._sd.hardware_switch.clicked.connect(self.switch_hardware)

        # write the configuration to the settings window of the GUI.
        self.keep_former_settings()

    def init_plot_step_UI(self):
        # Get the image for the display from the logic. Transpose the received
        # matrix to get the proper scan. The graphic widget displays vector-
        # wise the lines and the lines are normally columns, but in our
        # measurement we scan rows per row. That's why it has to be transposed.
        self.step_image = pg.ImageItem(self._stepper_logic.stepping_raw_data.transpose())

        # set up scan line plot
        sc = self._stepper_logic._step_counter
        sc = sc - 1 if sc >= 1 else sc
        data = self._stepper_logic.image[sc, :, 0:3:2]

        self.step_line_plot = pg.PlotDataItem(data, pen=pg.mkPen(palette.c1))
        #self._mw.scanLineGraphicsView.addItem(self.step_line_plot)

        # Add the display item  ViewWidget, which was defined in the UI file:
        self._mw.ViewWidget.addItem(self.step_image)

        # Label the axes:
        # Todo: Think about axes labels
        self._mw.ViewWidget.setLabel('bottom', units='Steps')
        self._mw.ViewWidget.setLabel('left', units='Steps')

        # Set up and connect xy channel combobox
        scan_channels = self._stepper_logic.get_counter_count_channels()
        for n, ch in enumerate(scan_channels):
            self._mw.count_channel_ComboBox.addItem(str(ch), n)
        self._mw.count_channel_ComboBox.activated.connect(self.update_count_channel)

        self._mw.count_direction_ComboBox.addItem("Forward", True)
        self._mw.count_direction_ComboBox.addItem("Backward", False)
        self._mw.count_direction_ComboBox.activated.connect(self.update_count_direction)

        #################################################################
        #           Connect the colorbar and their actions              #
        #################################################################
        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleInferno()

        self.step_image.setLookupTable(self.my_colors.lut)

        # Create colorbars and add them at the desired place in the GUI. Add
        # also units to the colorbar.

        self.cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self._mw.cb_ViewWidget.addItem(self.cb)
        self._mw.cb_ViewWidget.hideAxis('bottom')
        self._mw.cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.cb_ViewWidget.setMouseEnabled(x=False, y=False)

        self._mw.sigPressKeyBoard.connect(self.keyPressEvent)
        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture:
        self._stepper_logic.signal_image_updated.connect(self.refresh_image)
        self._stepper_logic.signal_image_updated.connect(self.refresh_scan_line)
        #self._stepper_logic.sigImageInitialized.connect(self.adjust_window)

    def init_hardware_UI(self):
        # Set the range for the spin boxes of the voltage and frequency values:
        amplitude_range = self._stepper_logic.axis_class["x"].get_amplitude_range()
        self._mw.x_amplitude_doubleSpinBox.setRange(amplitude_range[0], amplitude_range[1])
        amplitude_range = self._stepper_logic.axis_class["y"].get_amplitude_range()
        self._mw.y_amplitude_doubleSpinBox.setRange(amplitude_range[0], amplitude_range[1])
        amplitude_range = self._stepper_logic.axis_class["z"].get_amplitude_range()
        self._mw.z_amplitude_doubleSpinBox.setRange(amplitude_range[0], amplitude_range[1])

        frequency_range = self._stepper_logic.axis_class["x"].get_freq_range()
        self._mw.x_frequency_spinBox.setRange(frequency_range[0], frequency_range[1])
        frequency_range = self._stepper_logic.axis_class["y"].get_freq_range()
        self._mw.y_frequency_spinBox.setRange(frequency_range[0], frequency_range[1])
        frequency_range = self._stepper_logic.axis_class["z"].get_freq_range()
        self._mw.z_frequency_spinBox.setRange(frequency_range[0], frequency_range[1])

        # set minimal steps for the current value
        self._mw.x_amplitude_doubleSpinBox.setOpts(minStep=0.1)
        self._mw.y_amplitude_doubleSpinBox.setOpts(minStep=0.1)
        self._mw.z_amplitude_doubleSpinBox.setOpts(minStep=0.1)

    def init_step_parameters_UI(self):

        # These connect to confocal logic such that the piezos are moved
        # Setup the Sliders:
        # Calculate the needed Range for the sliders. The image ranges comming
        # from the Logic module must be in meters.
        # 1 nanometer resolution per one change, units are meters
        self.slider_res = 1e-9

        # How many points are needed for that kind of resolution:
        num_of_points_x = (self._scanning_logic.x_range[1] - self._scanning_logic.x_range[
            0]) / self.slider_res
        num_of_points_y = (self._scanning_logic.y_range[1] - self._scanning_logic.y_range[
            0]) / self.slider_res
        num_of_points_z = (self._scanning_logic.z_range[1] - self._scanning_logic.z_range[
            0]) / self.slider_res

        # Set a Range for the sliders:
        self._mw.x_piezo_SliderWidget.setRange(0, num_of_points_x)
        self._mw.y_piezo_SliderWidget.setRange(0, num_of_points_y)
        self._mw.z_piezo_SliderWidget.setRange(0, num_of_points_z)

        # Just to be sure, set also the possible maximal values for the spin
        # boxes of the current values:
        self._mw.x_piezo_InputWidget.setRange(self._scanning_logic.x_range[0],
                                              self._scanning_logic.x_range[1])
        self._mw.y_piezo_InputWidget.setRange(self._scanning_logic.y_range[0],
                                              self._scanning_logic.y_range[1])
        self._mw.z_piezo_InputWidget.setRange(self._scanning_logic.z_range[0],
                                              self._scanning_logic.z_range[1])

        # set minimal steps for the current value
        self._mw.x_piezo_InputWidget.setOpts(minStep=1e-6)
        self._mw.y_piezo_InputWidget.setOpts(minStep=1e-6)
        self._mw.z_piezo_InputWidget.setOpts(minStep=1e-6)

        # Predefine the maximal and minimal image range as the default values
        # for the display of the range:
        self._mw.x_piezo_min_InputWidget.setValue(self._scanning_logic.image_x_range[0])
        self._mw.x_piezo_max_InputWidget.setValue(self._scanning_logic.image_x_range[1])
        self._mw.y_piezo_min_InputWidget.setValue(self._scanning_logic.image_y_range[0])
        self._mw.y_piezo_max_InputWidget.setValue(self._scanning_logic.image_y_range[1])
        self._mw.z_piezo_min_InputWidget.setValue(self._scanning_logic.image_z_range[0])
        self._mw.z_piezo_max_InputWidget.setValue(self._scanning_logic.image_z_range[1])

        # set the maximal ranges for the image range from the logic:
        self._mw.x_piezo_min_InputWidget.setRange(self._scanning_logic.x_range[0],
                                                  self._scanning_logic.x_range[1])
        self._mw.x_piezo_max_InputWidget.setRange(self._scanning_logic.x_range[0],
                                                  self._scanning_logic.x_range[1])
        self._mw.y_piezo_min_InputWidget.setRange(self._scanning_logic.y_range[0],
                                                  self._scanning_logic.y_range[1])
        self._mw.y_piezo_max_InputWidget.setRange(self._scanning_logic.y_range[0],
                                                  self._scanning_logic.y_range[1])
        self._mw.z_piezo_min_InputWidget.setRange(self._scanning_logic.z_range[0],
                                                  self._scanning_logic.z_range[1])
        self._mw.z_piezo_max_InputWidget.setRange(self._scanning_logic.z_range[0],
                                                  self._scanning_logic.z_range[1])

        # set the minimal step size
        self._mw.x_piezo_min_InputWidget.setOpts(minStep=1e-6)
        self._mw.x_piezo_max_InputWidget.setOpts(minStep=1e-6)
        self._mw.y_piezo_min_InputWidget.setOpts(minStep=1e-6)
        self._mw.y_piezo_max_InputWidget.setOpts(minStep=1e-6)
        self._mw.z_piezo_min_InputWidget.setOpts(minStep=1e-6)
        self._mw.z_piezo_max_InputWidget.setOpts(minStep=1e-6)

        # Handle slider movements by user:
        self._mw.x_piezo_SliderWidget.sliderMoved.connect(self.update_from_piezo_slider_x)
        self._mw.y_piezo_SliderWidget.sliderMoved.connect(self.update_from_piezo_slider_y)
        self._mw.z_piezo_SliderWidget.sliderMoved.connect(self.update_from_piezo_slider_z)

        # Add Step Directions
        self._mw.step_direction_comboBox.addItem("XY", "xy")
        self._mw.step_direction_comboBox.addItem("XZ", "xz")
        self._mw.step_direction_comboBox.addItem("YZ", "yz")
        self._mw.step_direction_comboBox.activated.connect(self.update_step_direction)

    def init_tilt_correction_UI(self):
        # Hide tilt correction window
        self._mw.tilt_correction_dockWidget.hide()

    def _show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def keyPressEvent(self, event):
        """ Handles the passed keyboard events from the main window.

        @param object event: qtpy.QtCore.QEvent object.
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        position = self._scanning_logic.get_position()  # in meters
        x_pos = position[0]
        y_pos = position[1]
        z_pos = position[2]

        if modifiers == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_Right:
                self.update_from_key(x=float(round(x_pos + self.slider_big_step, 10)))
            elif event.key() == QtCore.Qt.Key_Left:
                self.update_from_key(x=float(round(x_pos - self.slider_big_step, 10)))
            elif event.key() == QtCore.Qt.Key_Up:
                self.update_from_key(y=float(round(y_pos + self.slider_big_step, 10)))
            elif event.key() == QtCore.Qt.Key_Down:
                self.update_from_key(y=float(round(y_pos - self.slider_big_step, 10)))
            elif event.key() == QtCore.Qt.Key_PageUp:
                self.update_from_key(z=float(round(z_pos + self.slider_big_step, 10)))
            elif event.key() == QtCore.Qt.Key_PageDown:
                self.update_from_key(z=float(round(z_pos - self.slider_big_step, 10)))
            else:
                event.ignore()
        else:
            if event.key() == QtCore.Qt.Key_Right:
                self.update_from_key(x=float(round(x_pos + self.slider_small_step, 10)))
            elif event.key() == QtCore.Qt.Key_Left:
                self.update_from_key(x=float(round(x_pos - self.slider_small_step, 10)))
            elif event.key() == QtCore.Qt.Key_Up:
                self.update_from_key(y=float(round(y_pos + self.slider_small_step, 10)))
            elif event.key() == QtCore.Qt.Key_Down:
                self.update_from_key(y=float(round(y_pos - self.slider_small_step, 10)))
            elif event.key() == QtCore.Qt.Key_PageUp:
                self.update_from_key(z=float(round(z_pos + self.slider_small_step, 10)))
            elif event.key() == QtCore.Qt.Key_PageDown:
                self.update_from_key(z=float(round(z_pos - self.slider_small_step, 10)))
            else:
                event.ignore()

    ################## Step Scan ##################
    def get_cb_range(self):
        """ Determines the cb_min and cb_max values for the image
        """
        # If "Manual" is checked, or the image data is empty (all zeros),
        # then take manual cb range.
        if self._mw.cb_manual_RadioButton.isChecked() or np.max(
                self.step_image.image) == 0.0:
            cb_min = self._mw.cb_min_DoubleSpinBox.value()
            cb_max = self._mw.cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            image_nonzero = self.step_image.image[np.nonzero(self.step_image.image)]

            # Read centile range
            low_centile = self._mw.cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(image_nonzero, low_centile)
            cb_max = np.percentile(image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def refresh_colorbar(self):
        """ Adjust the image colorbar.

        Calls the refresh method from colorbar, which takes either the lowest
        and highest value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """
        cb_range = self.get_cb_range()
        self.cb.refresh_colorbar(cb_range[0], cb_range[1])

    ################## Hardware Scan ##################

    ################## Tool bar ##################
    def disable_step_actions(self):
        """ Disables the buttons for scanning.
        """
        # Enable the stop scanning button
        self._mw.action_step_stop.setEnabled(True)

        # Disable the start scan buttons
        self._mw.action_step_start.setEnabled(False)

        self._mw.action_step_resume.setEnabled(False)

        self._mw.x_piezo_min_InputWidget.setEnabled(False)
        self._mw.x_piezo_max_InputWidget.setEnabled(False)
        self._mw.y_piezo_min_InputWidget.setEnabled(False)
        self._mw.y_piezo_max_InputWidget.setEnabled(False)
        self._mw.z_piezo_min_InputWidget.setEnabled(False)
        self._mw.z_piezo_max_InputWidget.setEnabled(False)

        self._mw.x_step_InputWidget.setEnabled(False)
        self._mw.y_step_InputWidget.setEnabled(False)
        self._mw.z_step_InputWidget.setEnabled(False)

        # Set the zoom button if it was pressed to unpressed and disable it
        self._mw.action_zoom.setChecked(False)
        self._mw.action_zoom.setEnabled(False)

        self.set_history_actions(False)

    def enable_step_actions(self):
        """ Reset the scan action buttons to the default active
        state when the system is idle.
        """
        # Disable the stop scanning button
        self._mw.action_step_stop.setEnabled(False)

        # Enable the scan buttons
        self._mw.action_step_start.setEnabled(True)
        #        self._mw.actionRotated_depth_scan.setEnabled(True)

        self._mw.action_optimize_position.setEnabled(True)

        self._mw.x_piezo_min_InputWidget.setEnabled(True)
        self._mw.x_piezo_max_InputWidget.setEnabled(True)
        self._mw.y_piezo_min_InputWidget.setEnabled(True)
        self._mw.y_piezo_max_InputWidget.setEnabled(True)
        self._mw.z_piezo_min_InputWidget.setEnabled(True)
        self._mw.z_piezo_max_InputWidget.setEnabled(True)

        self._mw.x_step_InputWidget.setEnabled(True)
        self._mw.y_step_InputWidget.setEnabled(True)
        self._mw.z_step_InputWidget.setEnabled(True)

        self._mw.action_zoom.setEnabled(True)

        self.set_history_actions(True)

        # Enable the resume scan buttons if scans were unfinished
        # TODO: this needs to be implemented properly.
        # For now they will just be enabled by default

        if self._scanning_logic._zscan_continuable is True:
            self._mw.action_scan_depth_resume.setEnabled(True)
        else:
            self._mw.action_scan_depth_resume.setEnabled(False)

        if self._scanning_logic._xyscan_continuable is True:
            self._mw.action_scan_xy_resume.setEnabled(True)
        else:
            self._mw.action_scan_xy_resume.setEnabled(False)

    def set_history_actions(self, enable):
        """ Enable or disable history arrows taking history state into account. """
        if enable and self._stepper_logic.history_index < len(
                self._stepper_logic.history) - 1:
            self._mw.actionForward.setEnabled(True)
        else:
            self._mw.actionForward.setEnabled(False)
        if enable and self._scanning_logic.history_index > 0:
            self._mw.actionBack.setEnabled(True)
        else:
            self._mw.actionBack.setEnabled(False)

    def ready_clicked(self):
        """ Stop the scan if the state has switched to ready. """
        if self._stepper_logic.getState() == 'locked':
            # Todo: Needs to be implemented when option in logic exists
            # self._stepper_logic.permanent_scan = False
            self._stepper_logic.stop_stepper()

        self.enable_step_actions()

    def step_start_clicked(self):
        """ Manages what happens if the step scan is started. """
        self.disable_step_actions()
        self._stepper_logic.start_stepper()  # tag='gui')

    def step_continued_clicked(self):
        """ Continue step scan. """
        self.disable_step_actions()
        self._stepper_logic.continue_stepper()  # tag='gui')

    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

    def update_settings(self):
        """ Write new settings from the gui to the file. """
        # Todo: Needs to be implemented when option in logic exists
        # self._stepper_logic.permanent_scan = self._sd.loop_scan_CheckBox.isChecked()
        self.fixed_aspect_ratio = self._sd.fixed_aspect_checkBox.isChecked()
        self.slider_small_step = self._sd.slider_small_step_DoubleSpinBox.value()
        self.slider_big_step = self._sd.slider_big_step_DoubleSpinBox.value()

        # Update GUI icons to new loop-scan state
        self._set_scan_icons()

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        # Todo: Needs to be implemented when option in logic exists
        self._sd.loop_scan_CheckBox.setChecked(self._stepper_logic.permanent_scan)
        direction = self._stepper_logic._scan_axes

        self._sd.fixed_aspect_checkBox.setChecked(self.fixed_aspect_ratio)
        self._sd.slider_small_step_DoubleSpinBox.setValue(float(self.slider_small_step))
        self._sd.slider_big_step_DoubleSpinBox.setValue(float(self.slider_big_step))

    ############################################################################
    #                           Change Methods                                 #
    ############################################################################


    ################## File Menu ##################
    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_tag_LineEdit.text()
        cb_range = self.get_matrix_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if self._mw.odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.odmr_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.odmr_cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self.sigSaveMeasurement.emit(filetag, cb_range, pcile_range)
        return

    # Todo: anpassen
    ################## Step Scan ##################
    def update_count_channel(self, index):
        """ The displayed channel for the image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.count_channel = int(self._mw.count_channel_ComboBox.itemData(index,
                                                                          QtCore.Qt.UserRole))
        self.refresh_image()

    def update_count_direction(self, index):
        """ The displayed direction for the image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.count_direction = bool(self._mw.count_direction_ComboBox.itemData(index,
                                                                               QtCore.Qt.UserRole))
        self.refresh_image()

    def shortcut_to_cb_manual(self):
        """The absolute counts range for the colour bar was edited, update."""
        self._mw.cb_manual_RadioButton.setChecked(True)
        self.update_cb_range()

    def shortcut_to_cb_centiles(self):
        """The centiles range for the colour bar was edited, update."""
        self._mw.cb_centiles_RadioButton.setChecked(True)
        self.update_cb_range()

    def update_cb_range(self):
        """Redraw colour bar and scan image."""
        self.refresh_colorbar()
        self.refresh_image()

    def refresh_image(self):
        """ Update the current image from the logic.

        Every time the stepper is stepping a line the image is rebuild and updated in the GUI.
        """
        self.step_image.getViewBox().updateAutoRange()
        # Todo: this needs to have a check for the stepping direction and the correct data has to
        #  be chosen
        if self.count_direction:
            step_image_data = self._stepper_logic.stepping_raw_data.transpose()
        else:
            step_image_data = self._stepper_logic.stepping_raw_data_back
        cb_range = self.get_cb_range()

        # Now update image with new color scale, and update colorbar
        self.step_image.setImage(image=step_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_colorbar()

        # Unlock state widget if scan is finished
        if self._stepper_logic.getState() != 'locked':
            self.enable_step_actions()

    ################## Step Parameters ##################
    # Todo:
    def update_step_direction(self, index):
        """ The user changed the step scan direction, adjust all
            other GUI elements."""
        self.scan_axes = str(self._mw.count_direction_ComboBox.itemData(index,
                                                                        QtCore.Qt.UserRole))

        self.set_scan_axes(self.scan_axes)
        pass

    def update_from_input_x_piezo(self):
        """ The user changed the number in the x piezo position spin box, adjust all
            other GUI elements."""
        x_pos = self._mw.x_piezo_InputWidget.value()
        self.update_slider_piezo_x(x_pos)
        self._scanning_logic.set_position('xinput', x=x_pos)

    def update_from_input_y_piezo(self):
        """ The user changed the number in the y piezo position spin box, adjust all
            other GUI elements."""
        y_pos = self._mw.y_piezo_InputWidget.value()
        self.update_piezo_slider_y(y_pos)
        self._scanning_logic.set_position('yinput', y=y_pos)

    def update_from_input_z_piezo(self):
        """ The user changed the number in the z piezo position spin box, adjust all
           other GUI elements."""
        z_pos = self._mw.z_current_InputWidget.value()
        self.update_slider_piezo_z(z_pos)
        self._scanning_logic.set_position('zinput', z=z_pos)

    def update_input_x_piezo(self, x_pos):
        """ Update the displayed x-value.

        @param float x_pos: the current value of the x position in m
        """
        # Convert x_pos to number of points for the slider:
        self._mw.x_piezo_InputWidget.setValue(x_pos)

    def update_input_y_piezo(self, y_pos):
        """ Update the displayed y-value.

        @param float y_pos: the current value of the y position in m
        """
        # Convert x_pos to number of points for the slider:
        self._mw.y_piezo_InputWidget.setValue(y_pos)

    def update_input_z_piezo(self, z_pos):
        """ Update the displayed z-value.

        @param float z_pos: the current value of the z position in m
        """
        # Convert x_pos to number of points for the slider:
        self._mw.z_piezo_InputWidget.setValue(z_pos)

    def update_from_piezo_slider_x(self, sliderValue):
        """The user moved the x piezo slider slider, adjust the other GUI elements.

        @params int sliderValue: slider piezo position, a quantized whole number
        """
        x_pos = self._scanning_logic.x_range[0] + sliderValue * self.slider_res
        self.update_input_x(x_pos)
        self._scanning_logic.set_position('xslider', x=x_pos)

    def update_from_piezo_slider_y(self, sliderValue):
        """The user moved the y piezo slider, adjust the other GUI elements.

        @params int sliderValue: slider piezo position, a quantized whole number
        """
        y_pos = self._scanning_logic.y_range[0] + sliderValue * self.slider_res
        self.update_input_y_piezo(y_pos)
        self._scanning_logic.set_position('yslider', y=y_pos)

    def update_from_piezo_slider_z(self, sliderValue):
        """The user moved the z piezo slider, adjust the other GUI elements.

        @params int sliderValue: slider piezo position, a quantized whole number
        """
        z_pos = self._scanning_logic.z_range[0] + sliderValue * self.slider_res
        self.update_input_z_piezo(z_pos)
        self._scanning_logic.set_position('zslider', z=z_pos)

    def update_piezo_slider_x(self, x_pos):
        """ Update the x piezo slider when a change happens.

        @param float x_pos: x position in m
        """
        self._mw.x_piezo_SliderWidget.setValue(
            (x_pos - self._scanning_logic.x_range[0]) / self.slider_res)

    def update_piezo_slider_y(self, y_pos):
        """ Update the y piezo slider when a change happens.

        @param float y_pos: y position in m
        """
        self._mw.y_piezo_SliderWidget.setValue(
            (y_pos - self._scanning_logic.y_range[0]) / self.slider_res)

    def update_piezo_slider_z(self, z_pos):
        """ Update the z piezo slider when a change happens.

        @param float z_pos: z position in m
        """
        self._mw.z_piezo_SliderWidget.setValue(
            (z_pos - self._scanning_logic.z_range[0]) / self.slider_res)

    def change_x_steps_range(self):
        """ Update the x steps range in the logic according to the GUI.
        """
        self._stepper_logic.steps_direction['x'] = self._mw.x_steps_InputWidget.value()

    def change_z_resolution(self):
        """ Update the y steps range in the logic according to the GUI.
        """
        self._stepper_logic.steps_direction['y'] = self._mw.y_steps_InputWidget.value()

    def change_z_resolution(self):
        """ Update the z steps range in the logic according to the GUI.
        """
        self._stepper_logic.steps_direction['z'] = self._mw.z_steps_InputWidget.value()

    # Todo: did not do this yet
    def change_x_image_range(self):
        """ Adjust the image range for x in the logic. """
        self._scanning_logic.image_x_range = [
            self._mw.x_min_InputWidget.value(),
            self._mw.x_max_InputWidget.value()]

    def change_x_piezo_range(self):
        """ Adjust the piezo range for x in the logic. """
        self._scanning_logic.image_x_range = [
            self._mw.x_min_InputWidget.value(),
            self._mw.x_max_InputWidget.value()]

    def change_y_piezo_range(self):
        """ Adjust the piezo range for y in the logic.
        """
        self._scanning_logic.image_y_range = [
            self._mw.y_piezo_min_InputWidget.value(),
            self._mw.y_piezo_max_InputWidget.value()]

    def change_z_piezo_range(self):
        """ Adjust the piezo range for z in the logic. """
        self._scanning_logic.image_z_range = [
            self._mw.z_piezo_min_InputWidget.value(),
            self._mw.z_piezo_max_InputWidget.value()]

    ################## Scan Line ##################
    def refresh_scan_line(self):
        """ Get the previously scanned image line and display it in the step line plot. """
        sc = self._stepper_logic.get_step_counter()
        sc = sc - 1 if sc >= 1 else sc
        self.step_line_plot.setData(self._stepper_logic.stepping_raw_data[sc])

    def adjust_window(self):
        """ Fit the visible window in the step scan to full view.

        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and y.
        """
        # It is extremely crucial that before adjusting the window view and
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_image()
        xy_viewbox = self.step_image.getViewBox()

        Min_first_axis = 0
        Max_first_axis = self._scanning_logic.image_x_range[1]
        Min_second_axis = 0
        Max_second_axis = self._scanning_logic.image_y_range[1]

        if self.fixed_aspect_ratio_xy:
            # Reset the limit settings so that the method 'setAspectLocked'
            # works properly. It has to be done in a manual way since no method
            # exists yet to reset the set limits:
            xy_viewbox.state['limits']['xLimits'] = [None, None]
            xy_viewbox.state['limits']['yLimits'] = [None, None]
            xy_viewbox.state['limits']['xRange'] = [None, None]
            xy_viewbox.state['limits']['yRange'] = [None, None]

            xy_viewbox.setAspectLocked(lock=True, ratio=1.0)
            xy_viewbox.updateViewRange()
        else:
            xy_viewbox.setLimits(
                xMin=Min_first_axis - (Max_first_axis - Min_first_axis) * self.image_x_padding,
                xMax=Max_first_axis + (Max_first_axis - Min_first_axis) * self.image_x_padding,
                yMin=Min_second_axis - (Max_second_axis - Min_second_axis) * self.image_y_padding,
                yMax=Max_second_axis + (Max_second_axis - Min_second_axis) * self.image_y_padding)

        self.step_image.setRect(
            QtCore.QRectF(Min_first_axis, Min_second_axis, Max_first_axis - Min_first_axis,
                          Max_second_axis - Min_second_axis))

        xy_viewbox.updateAutoRange()
        xy_viewbox.updateViewRange()

    def save_step_scan_data(self):
        """ Run the save routine from the logic to save the confocal stepper data."""
        cb_range = self.get_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.cb_manual_RadioButton.isChecked():
            low_centile = self._mw.cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._scanning_logic.save_xy_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        # if self._mw.count
        filepath = self._save_logic.get_path_for_module(module_name='ConfocalStepper')
        filename = filepath + os.sep + time.strftime(
            '%Y%m%d-%H%M-%S_confocal_step_scan_raw_pixel_image')
        if self._sd.save_purePNG_checkBox.isChecked():
            self.step_image.save(filename + '_raw.png')

    ################## Settings ##################
    def switch_hardware(self):
        """ Switches the hardware state. """
        self._stepper_logic.switch_hardware(to_on=False)

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.step_dockWidget.show()
        self._mw.scan_control_dockWidget.show()
        self._mw.hardware_dockWidget.show()
        self._mw.tilt_correction_dockWidget.hide()
        #self._mw.scanLineDockWidget.hide()

        # re-dock any floating dock widgets
        self._mw.step_dockWidget.setFloating(False)
        self._mw.scan_control_dockWidget.setFloating(False)
        self._mw.hardware_dockWidget.setFloating(False)
        self._mw.tilt_correction_dockWidget.setFloating(False)
        #self._mw.scanLineDockWidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.step_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.scan_control_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.tilt_correction_dockWidget)
        #self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.scanLineDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.hardware_dockWidget)

        # Resize window to default size
        self._mw.resize(1255, 939)

    def logic_started_stepping(self, tag):
        """ Disable icons if a scan was started.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_step_actions()

    def logic_continued_stepping(self, tag):
        """ Disable icons if a scan was continued.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_step_actions()
