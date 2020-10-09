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

from core.module import Connector, ConfigOption
from gui.confocal_stepper.lab_book_gui import ConfocalStepperLabBookWindow
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from core.util import units
from qtwidgets.scan_plotwidget import ScanImageItem


class CrossROI(pg.ROI):
    """ Create a Region of interest, which is a zoomable rectangular.

    @param float pos: optional parameter to set the position
    @param float size: optional parameter to set the size of the roi

    Have a look at:
    http://www.pyqtgraph.org/documentation/graphicsItems/roi.html
    """
    sigUserRegionUpdate = QtCore.Signal(object)
    sigMachineRegionUpdate = QtCore.Signal(object)

    def __init__(self, pos, size, **args):
        """Create a ROI with a central handle."""
        self.userDrag = False
        pg.ROI.__init__(self, pos, size, **args)
        # That is a relative position of the small box inside the region of
        # interest, where 0 is the lowest value and 1 is the higherst:
        center = [0.5, 0.5]
        # Translate the center to the intersection point of the crosshair.
        self.addTranslateHandle(center)

        self.sigRegionChangeStarted.connect(self.startUserDrag)
        self.sigRegionChangeFinished.connect(self.stopUserDrag)
        self.sigRegionChanged.connect(self.regionUpdateInfo)

    def setPos(self, pos, update=True, finish=False):
        """Sets the position of the ROI.

        @param bool update: whether to update the display for this call of setPos
        @param bool finish: whether to emit sigRegionChangeFinished

        Changed finish from parent class implementation to not disrupt user dragging detection.
        """
        super().setPos(pos, update=update, finish=finish)

    def setSize(self, size, update=True, finish=True):
        """
        Sets the size of the ROI
        @param bool update: whether to update the display for this call of setPos
        @param bool finish: whether to emit sigRegionChangeFinished
        """
        super().setSize(size, update=update, finish=finish)

    def handleMoveStarted(self):
        """ Handles should always be moved by user."""
        super().handleMoveStarted()
        self.userDrag = True

    def startUserDrag(self, roi):
        """ROI has started being dragged by user."""
        self.userDrag = True

    def stopUserDrag(self, roi):
        """ROI has stopped being dragged by user"""
        self.userDrag = False

    def regionUpdateInfo(self, roi):
        """When the region is being dragged by the user, emit the corresponding signal."""
        # Todo: Check
        if self.userDrag:
            self.sigUserRegionUpdate.emit(roi)
        else:
            self.sigMachineRegionUpdate.emit(roi)


class CrossLine(pg.InfiniteLine):
    """ Construct one line for the Crosshair in the plot.

    @param float pos: optional parameter to set the position
    @param float angle: optional parameter to set the angle of the line
    @param dict pen: Configure the pen.

    For additional options consider the documentation of pyqtgraph.InfiniteLine
    """

    def __init__(self, **args):
        pg.InfiniteLine.__init__(self, **args)

    #        self.setPen(QtGui.QPen(QtGui.QColor(255, 0, 255),0.5))

    def adjust(self, extroi):
        """
        Run this function to adjust the position of the Crosshair-Line

        @param object extroi: external roi object from pyqtgraph
        """
        if self.angle == 0:
            self.setValue(extroi.pos()[1] + extroi.size()[1] * 0.5)
        if self.angle == 90:
            self.setValue(extroi.pos()[0] + extroi.size()[0] * 0.5)


class ConfocalStepperMainWindow(QtWidgets.QMainWindow):
    """ The main window for the confocal stepper measurement GUI.
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
    This is the GUI Class for Confocal Stepper measurements
    """

    _modclass = 'ConfocalStepperGui'
    _modtype = 'gui'

    # declare connectors
    confocallogic1 = Connector(interface='ConfocalLogic')
    savelogic = Connector(interface='SaveLogic')
    stepperlogic1 = Connector(interface='ConfocalStepperLogic')

    default_meter_prefix = ConfigOption('default_meter_prefix', None)  # assume the unit prefix of position spinbox

    # signals
    sigStartSteppingScan = QtCore.Signal()
    sigStopSteppingScan = QtCore.Signal()
    sigContinueSteppingScan = QtCore.Signal()
    sigClearData = QtCore.Signal()
    sigSaveMeasurement = QtCore.Signal(str, list, list)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # self.log.info('The following configuration was found.')

        # checking for the right configuration
        # for key in config.keys():
        #    self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition, configuration and initialisation of the Confocal Stepper GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._stepper_logic = self.stepperlogic1()
        self._scanning_logic = self.confocallogic1()
        self._save_logic = self.savelogic()

        self.initMainUI()

        ########################################################################
        #                       Connect signals                                #
        ########################################################################

        # Show the Main SteppingConfocal GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def initMainUI(self):
        """ Definition, configuration and initialisation of the confocal stepper GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        # Use the inherited class 'Ui_StepperGuiUI' to create now the GUI element:
        self._mw = ConfocalStepperMainWindow()
        self._sd = ConfocalStepperSettingDialog()
        self._lab= ConfocalStepperLabBookWindow(self._stepper_logic)
        self._mw.action_show_labbook.triggered.connect(self.show_labbook)


        ###################################################################
        #               Configuring the dock widgets                      #
        ###################################################################
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self.init_plot_step_UI()
        self.init_hardware_UI()
        self.init_position_feedback_UI()
        self.init_step_parameters_UI()
        self.init_3D_step_scan_parameters()
        self.init_tilt_correction_UI()

        # Set the state button as ready button as default setting.
        self._mw.action_step_stop.setEnabled(False)
        self._mw.action_step_resume.setEnabled(False)
        self._mw.action_scan_3D_start.setEnabled(True)
        self._mw.action_scan_3D_resume.setEnabled(False)
        self._mw.action_scan_Finesse_start.setEnabled(True)


        # Connect other signals from the logic with an update of the gui

        self._stepper_logic.signal_start_stepping.connect(self.logic_started_stepping)
        self._stepper_logic.signal_continue_stepping.connect(self.logic_continued_stepping)
        self._stepper_logic.signal_start_3D_stepping.connect(self.logic_started_3D_stepping)
        self._stepper_logic.signal_start_Finesse_stepping.connect(self.logic_started_3D_stepping)

        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._mw.actionSave_Step_Scan.triggered.connect(self.save_step_scan_data)
        self._mw.action_load_data.triggered.connect(self.load_data)

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
        self._step_start_3D_proxy = pg.SignalProxy(
            self._mw.action_scan_3D_start.triggered,
            delay=0.1,
            slot=self.step_start_3D_clicked
        )
        self._step_resume_3D_proxy = pg.SignalProxy(
            self._mw.action_scan_3D_resume.triggered,
            delay=0.1,
            slot=self.step_continued_clicked
        )
        self.action_scan_Finesse_start = pg.SignalProxy(
            self._mw.action_scan_Finesse_start.triggered,
            delay=0.1,
            slot=self.step_start_Finesse_clicked
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

        self._get_former_parameters()

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
        self._currently_stepping = False
        # Get the image for the display from the logic.
        self.step_image = pg.ImageItem(image=self._stepper_logic.image_raw[:, :, 2], axisOrder='row-major')
        self.step_image_2 = pg.ImageItem(image=self._stepper_logic.image_raw[:, :, 2], axisOrder='row-major')
        # Todo: Add option to see data from other counter later

        # set up scan line plot
        sc = self._stepper_logic._step_counter
        sc = sc - 1 if sc >= 1 else sc
        data = self._stepper_logic.image_raw[sc, :, 0:3:2]

        self.step_line_plot = pg.PlotDataItem(data, pen=pg.mkPen(palette.c1))
        # self._mw.scanLineGraphicsView.addItem(self.step_line_plot)

        # Add the display item  step_scan_ViewWidget(s), which was defined in the UI file:
        self._mw.step_scan_ViewWidget.addItem(self.step_image)
        self._mw.step_scan_ViewWidget_2.addItem(self.step_image_2)

        # Label the axes:
        self._mw.step_scan_ViewWidget.setLabel('bottom', units='Steps')
        self._mw.step_scan_ViewWidget.setLabel('left', units='Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('bottom', units='Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('left', units='Steps')

        # Create Region of Interest for xy image and add to Image Widget:
        # Get the image for the display from the logic
        step_image_data = self._stepper_logic.image_raw[:, :, 2]
        ini_pos_x_crosshair = len(step_image_data) / 2
        ini_pos_y_crosshair = len(step_image_data) / 2
        self.roi = CrossROI(
            [
                ini_pos_x_crosshair - ini_pos_x_crosshair * 0.1,
                ini_pos_y_crosshair - ini_pos_y_crosshair * 0.1,
            ],
            [ini_pos_y_crosshair * 0.05
                , ini_pos_y_crosshair * 0.05],
            pen={'color': "F0F", 'width': 1},
            removable=True
        )

        self._mw.step_scan_ViewWidget.addItem(self.roi)
        self._mw.step_scan_ViewWidget_2.addItem(self.roi)

        # create horizontal and vertical line as a crosshair in image:
        self.hline = CrossLine(pos=self.roi.pos() + self.roi.size() * 0.5,
                               angle=0, pen={'color': palette.green, 'width': 1})
        self.vline = CrossLine(pos=self.roi.pos() + self.roi.size() * 0.5,
                               angle=90, pen={'color': palette.green, 'width': 1})

        # connect the change of a region with the adjustment of the crosshair:
        self.roi.sigRegionChanged.connect(self.hline.adjust)
        self.roi.sigRegionChanged.connect(self.vline.adjust)
        self.roi.sigUserRegionUpdate.connect(self.update_from_roi)
        # self.roi.sigRegionChangeFinished.connect(self.roi_bounds_check)

        # add the configured crosshair to the Widget
        self._mw.step_scan_ViewWidget.addItem(self.hline)
        self._mw.step_scan_ViewWidget.addItem(self.vline)
        self._mw.step_scan_ViewWidget_2.addItem(self.hline)
        self._mw.step_scan_ViewWidget_2.addItem(self.vline)

        # Set up and connect count channel combobox
        scan_channels = self._stepper_logic.get_counter_count_channels()
        for n, ch in enumerate(scan_channels):
            self._mw.count_channel_ComboBox.addItem(str(ch), n)
            self._mw.count_channel_ComboBox_2.addItem(str(ch), n)

        self._mw.count_channel_ComboBox.activated.connect(self.update_count_channel)
        self.count_channel = int(self._mw.count_channel_ComboBox.currentData())
        self._mw.count_channel_ComboBox_2.activated.connect(self.update_count_channel_2)
        self.count_channel_2 = int(self._mw.count_channel_ComboBox_2.currentData())

        self._mw.count_direction_ComboBox.addItem("Forward", True)
        self._mw.count_direction_ComboBox.addItem("Backward", False)
        self._mw.count_direction_ComboBox.activated.connect(self.update_count_direction)
        self.count_direction = bool(self._mw.count_direction_ComboBox.currentIndex())
        self._mw.count_direction_ComboBox_2.addItem("Forward", True)
        self._mw.count_direction_ComboBox_2.addItem("Backward", False)
        self._mw.count_direction_ComboBox_2.activated.connect(self.update_count_direction_2)
        self.count_direction_2 = bool(self._mw.count_direction_ComboBox_2.currentIndex())

        self._mw.data_display_type_ComboBox.activated.connect(self.update_data_display_type)
        self._mw.data_display_type_ComboBox.addItem("Average", True)
        self._mw.data_display_type_ComboBox.addItem("Extremum", False)
        self._mw.data_display_type_ComboBox.addItem("Median Extremum Difference",False)
        self._mw.data_display_type_ComboBox.addItem("Laser Corrected", False)
        self._mw.data_display_type_ComboBox_2.activated.connect(self.update_data_display_type_2)
        self._mw.data_display_type_ComboBox_2.addItem("Average", True)
        self._mw.data_display_type_ComboBox_2.addItem("Extremum", False)
        self._mw.data_display_type_ComboBox_2.addItem("Median Extremum Difference",False)
        self._mw.data_display_type_ComboBox_2.addItem("Laser Corrected", False)

        #################################################################
        #           Connect the colorbar and their actions              #
        #################################################################

        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleInferno()

        self.step_image.setLookupTable(self.my_colors.lut)
        self.step_image_2.setLookupTable(self.my_colors.lut)


        # Create colorbars and add them at the desired place in the GUI. Add
        # also units to the colorbar.

        self.cb = ColorBar(self.my_colors.cmap_normed, width=50, cb_min=0, cb_max=100)
        self._mw.step_scan_cb_ViewWidget.addItem(self.cb)
        self._mw.step_scan_cb_ViewWidget.hideAxis('bottom')
        self._mw.step_scan_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.step_scan_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        self.cb_2 = ColorBar(self.my_colors.cmap_normed, width=50, cb_min=0, cb_max=100)
        self._mw.step_scan_cb_ViewWidget_2.addItem(self.cb_2)
        self._mw.step_scan_cb_ViewWidget_2.hideAxis('bottom')
        self._mw.step_scan_cb_ViewWidget_2.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.step_scan_cb_ViewWidget_2.setMouseEnabled(x=False, y=False)

        self._mw.sigPressKeyBoard.connect(self.keyPressEvent)
        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture:
        self._stepper_logic.signal_image_updated.connect(self.refresh_image)
        self._stepper_logic.signal_image_updated.connect(self.refresh_scan_line)

        #TODO: Test this, implement this

        # self._stepper_logic.sigImageInitialized.connect(self.adjust_window)

        # Connect the buttons and inputs for the xy colorbar
        self._mw.cb_manual_RadioButton.clicked.connect(self.update_cb_range)
        self._mw.cb_centiles_RadioButton.clicked.connect(self.update_cb_range)
        self._mw.cb_manual_RadioButton_2.clicked.connect(self.update_cb_range)
        self._mw.cb_centiles_RadioButton_2.clicked.connect(self.update_cb_range)

        self._mw.cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_manual)
        self._mw.cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_manual)
        self._mw.cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_centiles)
        self._mw.cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_centiles)
        self._mw.cb_min_DoubleSpinBox_2.valueChanged.connect(self.shortcut_to_cb_manual_2)
        self._mw.cb_max_DoubleSpinBox_2.valueChanged.connect(self.shortcut_to_cb_manual_2)
        self._mw.cb_low_percentile_DoubleSpinBox_2.valueChanged.connect(self.shortcut_to_cb_centiles_2)
        self._mw.cb_high_percentile_DoubleSpinBox_2.valueChanged.connect(self.shortcut_to_cb_centiles_2)

    def init_position_feedback_UI(self):
        """
        Initialises all values for the position feedback of the confocal stepper
        Depending on the steppers used some ooptions will not be available
        """
        #### Initialize the position feedback LCD labels ####

        #  Check which axes have position feedback option
        self._x_closed_loop = self._stepper_logic.axis_class["x"].closed_loop
        self._y_closed_loop = self._stepper_logic.axis_class["y"].closed_loop
        self._z_closed_loop = self._stepper_logic.axis_class["z"].closed_loop
        self._feedback_axis = {}
        # X Axis
        if self._x_closed_loop:
            self._mw.x_accuracy_doubleSpinBox.setValue(
                self._stepper_logic.axis_class["x"].feedback_precision_position * 1e-3)
            self._mw.x_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["x"].absolute_position * 1e-3)
            pos_range = self._stepper_logic.axis_class["x"].get_position_range_stepper()
            self._mw.x_new_position_doubleSpinBox.setRange(pos_range[0] * 1e-3, pos_range[1] * 1e-3)
            self._feedback_axis["x"] = self._mw.x_new_position_doubleSpinBox
        else:
            self._mw.x_accuracy_doubleSpinBox.setValue(-1)
            self._mw.x_accuracy_doubleSpinBox.setValue(-1)
            self._mw.set_x_position_pushButton.setEnabled(False)
            self._mw.x_new_position_doubleSpinBox.setEnabled(False)

        # Y Axis
        if self._y_closed_loop:
            self._mw.y_accuracy_doubleSpinBox.setValue(
                self._stepper_logic.axis_class["y"].feedback_precision_position * 1e-3)
            self._mw.y_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["y"].absolute_position * 1e-3)
            pos_range = self._stepper_logic.axis_class["y"].get_position_range_stepper()
            self._mw.y_new_position_doubleSpinBox.setRange(pos_range[0] * 1e-3, pos_range[1] * 1e-3)
            self._feedback_axis["y"] = self._mw.y_new_position_doubleSpinBox
        else:
            self._mw.y_accuracy_doubleSpinBox.setValue(-1)
            self._mw.y_position_doubleSpinBox.setValue(-1)
            self._mw.set_y_position_pushButton.setEnabled(False)
            self._mw.y_new_position_doubleSpinBox.setEnabled(False)

        # Z Axis
        if self._z_closed_loop:
            self._mw.z_accuracy_doubleSpinBox.setValue(
                self._stepper_logic.axis_class["z"].feedback_precision_position * 1e-3)
            self._mw.z_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["z"].absolute_position * 1e-3)
            pos_range = self._stepper_logic.axis_class["z"].get_position_range_stepper()
            self._mw.z_new_position_doubleSpinBox.setRange(pos_range[0] * 1e-3, pos_range[1] * 1e-3)
            self._feedback_axis["z"] = self._mw.z_new_position_doubleSpinBox
        else:
            self._mw.z_accuracy_doubleSpinBox.setValue(-1)
            self._mw.z_position_doubleSpinBox.setValue(-1)
            self._mw.set_z_position_pushButton.setEnabled(False)
            self._mw.z_new_position_doubleSpinBox.setEnabled(False)

        self._mw.move_all_axis_pushButton.setEnabled(self._x_closed_loop + self._y_closed_loop + self._z_closed_loop)

        # connect actions
        self._mw.get_all_positions_pushButton.clicked.connect(self.get_position_steppers)
        self._mw.set_x_position_pushButton.clicked.connect(self.step_to_x_position)
        self._mw.set_y_position_pushButton.clicked.connect(self.step_to_y_position)
        self._mw.set_z_position_pushButton.clicked.connect(self.step_to_z_position)
        self._mw.move_all_axis_pushButton.clicked.connect(self.move_all_axis_to_position)

        self._mw.start_position_bool_checkBox.clicked.connect(self.update_move_to_start)
        self._mw.save_pos_feedback_checkBox.clicked.connect(self.update_save_position)

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
        self._mw.x_amplitude_doubleSpinBox.setSingleStep(0.1)
        self._mw.y_amplitude_doubleSpinBox.setSingleStep(0.1)
        self._mw.z_amplitude_doubleSpinBox.setSingleStep(0.1)
        # set unit in spin box
        self._mw.x_amplitude_doubleSpinBox.setSuffix(" V")
        self._mw.y_amplitude_doubleSpinBox.setSuffix(" V")
        self._mw.z_amplitude_doubleSpinBox.setSuffix(" V")

        # connect actions
        self._mw.read_hardware_pushButton.clicked.connect(self.measure_stepper_hardware_values)
        self._mw.update_hardware_pushButton.clicked.connect(self.update_stepper_hardware_values)

        # get current step values
        self.measure_stepper_hardware_values()

    def init_step_parameters_UI(self):

        self._mw.x_steps_InputWidget.setValue(self._stepper_logic.axis_class["x"].steps_direction)
        self._mw.y_steps_InputWidget.setValue(self._stepper_logic.axis_class["y"].steps_direction)
        self._mw.z_steps_InputWidget.setValue(self._stepper_logic.axis_class["z"].steps_direction)

        self._mw.x_steps_InputWidget.valueChanged.connect(self.change_x_steps_range)
        self._mw.y_steps_InputWidget.valueChanged.connect(self.change_y_steps_range)
        self._mw.z_steps_InputWidget.valueChanged.connect(self.change_z_steps_range)

        # These connect to confocal logic such that the piezos are moved
        # Setup the Sliders:
        # Calculate the needed Range for the sliders. The image ranges coming
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

        if self.default_meter_prefix:
            self._mw.x_piezo_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.y_piezo_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.z_piezo_InputWidget.assumed_unit_prefix = self.default_meter_prefix

            self._mw.x_piezo_min_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.x_piezo_max_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.y_piezo_min_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.y_piezo_max_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.z_piezo_min_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.z_piezo_max_InputWidget.assumed_unit_prefix = self.default_meter_prefix

        # Handle slider movements by user:
        self._mw.x_piezo_SliderWidget.sliderMoved.connect(self.update_from_piezo_slider_x)
        self._mw.y_piezo_SliderWidget.sliderMoved.connect(self.update_from_piezo_slider_y)
        self._mw.z_piezo_SliderWidget.sliderMoved.connect(self.update_from_piezo_slider_z)

        # Add Step Directions
        self._mw.step_direction_comboBox.addItem("XY", "xy")
        self._mw.step_direction_comboBox.addItem("XZ", "xz")
        self._mw.step_direction_comboBox.addItem("YZ", "yz")
        self._inverted_axes = {"xy": "yx", "xz": "zx", "yz": "zy", "yx": "xy", "zx": "xz", "zy": "yz"}
        self._mw.step_direction_comboBox.activated.connect(self.update_step_direction)
        self._mw.inverted_direction_checkBox.clicked.connect(self.update_step_direction)
        self._mw._fast_scan_checkBox.clicked.connect(self.update_fast_scan_option)
        self.update_fast_scan_option()

        self._stepper_logic.signal_step_scan_stopped.connect(self.enable_step_actions)

    def init_3D_step_scan_parameters(self):

        # setting default parameters
        voltage_range_3D = self._stepper_logic.get_analogue_voltage_range()
        self._mw.startV_3D_spinBox.setRange(voltage_range_3D[0], voltage_range_3D[1])
        self._mw.startV_3D_spinBox.setValue(self._stepper_logic.start_voltage_3D)
        self._mw.startV_3D_spinBox.editingFinished.connect(self.start_value_3D_changed, QtCore.Qt.QueuedConnection)

        self._mw.stopV_3D_spinBox.setRange(voltage_range_3D[0], voltage_range_3D[1])
        self._mw.stopV_3D_spinBox.setValue(self._stepper_logic.end_voltage_3D)
        self._mw.stopV_3D_spinBox.editingFinished.connect(self.stop_value_3D_changed, QtCore.Qt.QueuedConnection)

        self._mw.scan_resolution_3D_spinBox.setValue(self._stepper_logic.scan_resolution_3D)

        self._mw.smoothing_steps_3D_spinBox.setRange(0, 500) # todo: this needs to be adjusted according to the steps used for
        # one scan it can not be higher than half the amount of steps for one scan ramp
        self._mw.smoothing_steps_3D_spinBox.setValue(self._stepper_logic._3D_smoothing_steps)
        self._mw.smoothing_steps_3D_spinBox.editingFinished.connect(self.smoothing_steps_3D_changed, QtCore.Qt.QueuedConnection)

        # setting up check box for the maximal scan resolution and cavity mode
        self._mw.max_scan_resolution_3D_checkBox.toggled.connect(self.toggle_scan_resolution_3D)

        # todo: here it should actually find out the bit resolution of the hardware
        self._mw.maximal_scan_resolution_3D_DisplayWidget.display(self._stepper_logic.calculate_resolution(
            16, [self._stepper_logic.start_voltage_3D,
                 self._stepper_logic.end_voltage_3D]))

        self._mw.scan_resolution_3D_spinBox.valueChanged.connect(self.scan_resolution_3D_changed)

        #Todo: is there a maximally possible scan freq?
        self._mw.finesse_scan_freq_doubleSpinBox.setValue(self._stepper_logic.finesse_scan_freq)
        self._mw.finesse_scan_freq_doubleSpinBox.editingFinished.connect(self.finesse_scan_freq_changed, QtCore.Qt.QueuedConnection)

        # setting GUI elements enabled
        self._mw.startV_3D_spinBox.setEnabled(True)
        self._mw.stopV_3D_spinBox.setEnabled(True)
        self._mw.scan_resolution_3D_spinBox.setEnabled(True)
        self._mw.smoothing_steps_3D_spinBox.setEnabled(True)

        # setting up check box for the maximal scan resolution and cavity mode
        self._mw.max_scan_resolution_3D_checkBox.toggled.connect(self.toggle_scan_resolution_3D)

        # setting up the LCD Displays for the scan speed (V/s) and the maximal scan resolution
        self._mw.scan_speed_3D_DisplayWidget.display(np.abs(self._stepper_logic.end_voltage_3D -
                                                            self._stepper_logic.start_voltage_3D) *
                                                     self._stepper_logic.axis_class[self._stepper_logic._first_scan_axis].step_freq)
        self._mw.maximal_scan_resolution_3D_DisplayWidget.display(self._stepper_logic.calculate_resolution(
            16, [self._stepper_logic.start_voltage_3D,
                 self._stepper_logic.end_voltage_3D]))
        self._mw.finesse_scan_freq_doubleSpinBox.setEnabled(True)
        # todo: connect smoothing parameter

    def init_tilt_correction_UI(self):
        # Hide tilt correction window
        self._mw.tilt_correction_dockWidget.hide()

        self._mw.thrid_axis_correction_checkBox.stateChanged.connect(self._correct_3rd_axis_changed)
        self._mw.move_3rd_axis_up_checkBox.stateChanged.connect(self._correction_direction_3rd_axis_changed)
        self._mw.correct_every_x_lines_tilt_spinBox.valueChanged.connect(self._correction_nth_line_3rd_axis_changed)

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def keyPressEvent(self, event):
        """ Handles the passed keyboard events from the main window.

        @param object event: qtpy.QtCore.QEvent object.
        """
        pass
        #todo: update from key needs to be adjusted for confocal stepper
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

    def _get_former_parameters(self):
        inv_axes = self._stepper_logic._inverted_scan
        self._mw.inverted_direction_checkBox.setCheckState(inv_axes)
        if inv_axes:
            current_axes = self._inverted_axes[self._stepper_logic._scan_axes]
        else:
            current_axes = self._stepper_logic._scan_axes
        axes = self._mw.step_direction_comboBox.findData(current_axes)
        if axes == -1:
            self.log.error("the axes given in the confocal stepper logic is not possible in the gui")
        else:
            self._mw.step_direction_comboBox.setCurrentIndex(axes)
        # Label the axes:
        self._mw.step_scan_ViewWidget.setLabel('bottom', units=current_axes[0] + ' Steps')
        self._mw.step_scan_ViewWidget.setLabel('left', units=current_axes[1] + ' Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('bottom', units=current_axes[0] + ' Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('left', units=current_axes[1] + ' Steps')

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

        #do the same for the color bar range of the second image
        if self._mw.cb_manual_RadioButton_2.isChecked() or np.max(
                self.step_image_2.image) == 0.0:
            cb_min_2 = self._mw.cb_min_DoubleSpinBox_2.value()
            cb_max_2 = self._mw.cb_max_DoubleSpinBox_2.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            image_nonzero = self.step_image_2.image[np.nonzero(self.step_image_2.image)]

            # Read centile range
            low_centile = self._mw.cb_low_percentile_DoubleSpinBox_2.value()
            high_centile = self._mw.cb_high_percentile_DoubleSpinBox_2.value()

            cb_min_2 = np.percentile(image_nonzero, low_centile)
            cb_max_2 = np.percentile(image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]
        cb_range_2 = [cb_min_2, cb_max_2]

        return cb_range, cb_range_2

    def refresh_colorbar(self):
        """ Adjust the image colorbar.

        Calls the refresh method from colorbar, which takes either the lowest
        and highest value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """
        cb_range, cb_range_2 = self.get_cb_range()
        self.cb.refresh_colorbar(cb_range[0], cb_range[1])
        self.cb_2.refresh_colorbar(cb_range_2[0], cb_range_2[1])


    ################## Hardware Parameters ##################
    def measure_stepper_hardware_values(self):
        self._mw.x_amplitude_doubleSpinBox.setValue(self._stepper_logic.axis_class["x"].get_stepper_amplitude())
        self._mw.y_amplitude_doubleSpinBox.setValue(self._stepper_logic.axis_class["y"].get_stepper_amplitude())
        self._mw.z_amplitude_doubleSpinBox.setValue(self._stepper_logic.axis_class["z"].get_stepper_amplitude())
        self._mw.x_frequency_spinBox.setValue(self._stepper_logic.axis_class["x"].get_stepper_frequency())
        self._mw.y_frequency_spinBox.setValue(self._stepper_logic.axis_class["y"].get_stepper_frequency())
        self._mw.z_frequency_spinBox.setValue(self._stepper_logic.axis_class["z"].get_stepper_frequency())
        mode = self._stepper_logic.axis_class["x"].get_stepper_mode()
        if mode == "Input" or "Stepping":
            self._mw.x_dcin_checkBox.setCheckState(self._stepper_logic.axis_class["x"].get_dc_mode())
        else:
            self._mw.x_dcin_checkBox.setCheckState(False)
        mode = self._stepper_logic.axis_class["y"].get_stepper_mode()
        if mode == "Input" or "Stepping":
            self._mw.y_dcin_checkBox.setCheckState(self._stepper_logic.axis_class["y"].get_dc_mode())
        else:
            self._mw.y_dcin_checkBox.setCheckState(False)
        mode = self._stepper_logic.axis_class["z"].get_stepper_mode()
        if mode == "Input" or "Stepping":
            self._mw.z_dcin_checkBox.setCheckState(self._stepper_logic.axis_class["z"].get_dc_mode())
        else:
            self._mw.z_dcin_checkBox.setCheckState(False)
        self._mw.scan_frequency_3D_lcdNumber.display(self._stepper_logic.axis_class[self._stepper_logic._first_scan_axis].step_freq)

    def update_stepper_hardware_values(self):
        self._stepper_logic.axis_class["x"].set_stepper_amplitude(self._mw.x_amplitude_doubleSpinBox.value())
        self._stepper_logic.axis_class["y"].set_stepper_amplitude(self._mw.y_amplitude_doubleSpinBox.value())
        self._stepper_logic.axis_class["z"].set_stepper_amplitude(self._mw.z_amplitude_doubleSpinBox.value())
        self._stepper_logic.axis_class["x"].set_stepper_frequency(self._mw.x_frequency_spinBox.value())
        self._stepper_logic.axis_class["y"].set_stepper_frequency(self._mw.y_frequency_spinBox.value())
        self._stepper_logic.axis_class["z"].set_stepper_frequency(self._mw.z_frequency_spinBox.value())

        self._stepper_logic.axis_class["x"].set_dc_mode(self._mw.x_dcin_checkBox.checkState())
        self._stepper_logic.axis_class["y"].set_dc_mode(self._mw.y_dcin_checkBox.checkState())
        self._stepper_logic.axis_class["z"].set_dc_mode(self._mw.z_dcin_checkBox.checkState())
        self._mw.scan_frequency_3D_lcdNumber.display(self._stepper_logic.axis_class[self._stepper_logic._first_scan_axis].step_freq)

    ################## Position Feedback ##################

    def get_position_steppers(self):
        """Measures the current positions of the stepper for the axis with position feedback"""
        result = self._stepper_logic.get_position([*self._feedback_axis])  # get position for keys of feedback axes
        if self._x_closed_loop:
            self._mw.x_position_doubleSpinBox.setValue(result[0] * 1e-3)
        if self._y_closed_loop:
            self._mw.y_position_doubleSpinBox.setValue(result[self._x_closed_loop] * 1e-3)
        if self._z_closed_loop:
            self._mw.z_position_doubleSpinBox.setValue(result[self._x_closed_loop + self._y_closed_loop] * 1e-3)

    def step_to_x_position(self):
        if self._x_closed_loop:
            # Get positions to move to
            pos = {"x": self._mw.x_new_position_doubleSpinBox.value() * 1e3}
            # Move steppers to desired position
            self._stepper_logic.move_to_position(pos)
            # Update positions displayed in GUI
            self._mw.x_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["x"].absolute_position * 1e-3)
        else:
            # If axis can not be moved disable button
            self._mw.set_x_position_pushButton.setEnabled(False)
            self._mw.x_new_position_doubleSpinBox.setEnabled(False)

    def step_to_y_position(self):
        if self._y_closed_loop:
            # Get positions to move to
            pos = {"y": self._mw.y_new_position_doubleSpinBox.value() * 1e3}
            # Move steppers to desired position
            self._stepper_logic.move_to_position(pos)
            # Update positions displayed in GUI
            self._mw.y_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["y"].absolute_position * 1e-3)
        else:
            # If axis can not be moved disable button
            self._mw.set_y_position_pushButton.setEnabled(False)
            self._mw.y_new_position_doubleSpinBox.setEnabled(False)
            self._mw.y_new_position_doubleSpinBox.setEnabled(False)

    def step_to_z_position(self):
        if self._z_closed_loop:
            # Get positions to move to
            pos = {"z": self._mw.z_new_position_doubleSpinBox.value() * 1e3}
            # Move steppers to desired position
            self._stepper_logic.move_to_position(pos)
            # Update positions displayed in GUI
            self._mw.z_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["z"].absolute_position * 1e-3)
        else:
            # If axis can not be moved disable button
            self._mw.set_z_position_pushButton.setEnabled(False)
            self._mw.z_new_position_doubleSpinBox.setEnabled(False)

    def move_all_axis_to_position(self):
        # Get positions to move to and corresponding axes
        pos = {}
        for key, item in self._feedback_axis.items():
            pos[key] = item.value() * 1e3

        # Move steppers to desired position
        if len(self._feedback_axis) > 0:
            self._stepper_logic.move_to_position(pos)
        else:
            # If no axis can be moved disable button
            self._mw.move_all_axis_pushButton.setEnabled(False)

        # Update positions displayed in GUI
        if self._x_closed_loop:
            self._mw.x_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["x"].absolute_position * 1e-3)
        if self._y_closed_loop:
            self._mw.y_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["y"].absolute_position * 1e-3)
        if self._z_closed_loop:
            self._mw.z_position_doubleSpinBox.setValue(self._stepper_logic.axis_class["z"].absolute_position * 1e-3)

    def update_move_to_start(self):
        pass

    def update_save_position(self):
        self._stepper_logic._save_positions = self._mw.save_pos_feedback_checkBox.isChecked()

    ################## Tool bar ##################
    def disable_step_actions(self):
        """ Disables the buttons for scanning.
        """
        # Enable the stop scanning button
        self._mw.action_step_stop.setEnabled(True)

        # Disable the start scan buttons
        self._mw.action_step_start.setEnabled(False)
        self._mw.action_step_resume.setEnabled(False)
        self._mw.action_scan_3D_start.setEnabled(False)
        self._mw.action_scan_3D_resume.setEnabled(False)
        self._mw.action_scan_Finesse_start.setEnabled(False)

        self._mw.x_piezo_min_InputWidget.setEnabled(False)
        self._mw.x_piezo_max_InputWidget.setEnabled(False)
        self._mw.y_piezo_min_InputWidget.setEnabled(False)
        self._mw.y_piezo_max_InputWidget.setEnabled(False)
        self._mw.z_piezo_min_InputWidget.setEnabled(False)
        self._mw.z_piezo_max_InputWidget.setEnabled(False)

        self._mw.x_steps_InputWidget.setEnabled(False)
        self._mw.y_steps_InputWidget.setEnabled(False)
        self._mw.z_steps_InputWidget.setEnabled(False)

        self._mw.inverted_direction_checkBox.setEnabled(False)
        self._mw.step_direction_comboBox.setEnabled(False)
        self._mw._fast_scan_checkBox.setEnabled(False)

        # Set the zoom button if it was pressed to unpressed and disable it
        # self._mw.action_zoom.setChecked(False)
        # self._mw.action_zoom.setEnabled(False)

        # self.set_history_actions(False)

        # Disable Position feedback buttons which can't be used during step scan
        self._mw.get_all_positions_pushButton.setEnabled(False)
        self._mw.set_x_position_pushButton.setEnabled(False)
        self._mw.set_y_position_pushButton.setEnabled(False)
        self._mw.set_z_position_pushButton.setEnabled(False)
        self._mw.move_all_axis_pushButton.setEnabled(False)
        self._mw.measure_pos_feedback_checkBox.setEnabled(False)

        self._currently_stepping = True

    def enable_step_actions(self):
        """ Reset the scan action buttons to the default active
        state when the system is idle.
        """
        # Disable the stop scanning button
        self._mw.action_step_stop.setEnabled(False)

        # Enable the scan buttons
        self._mw.action_step_start.setEnabled(True)
        self._mw.action_scan_3D_start.setEnabled(True)
        self._mw.action_scan_Finesse_start.setEnabled(True)
        #        self._mw.actionRotated_depth_scan.setEnabled(True)

        self._mw.action_optimize_position.setEnabled(True)

        self._mw.x_piezo_min_InputWidget.setEnabled(True)
        self._mw.x_piezo_max_InputWidget.setEnabled(True)
        self._mw.y_piezo_min_InputWidget.setEnabled(True)
        self._mw.y_piezo_max_InputWidget.setEnabled(True)
        self._mw.z_piezo_min_InputWidget.setEnabled(True)
        self._mw.z_piezo_max_InputWidget.setEnabled(True)

        self._mw.x_steps_InputWidget.setEnabled(True)
        self._mw.y_steps_InputWidget.setEnabled(True)
        self._mw.z_steps_InputWidget.setEnabled(True)

        self._mw.inverted_direction_checkBox.setEnabled(True)
        self._mw.step_direction_comboBox.setEnabled(True)
        self._mw._fast_scan_checkBox.setEnabled(True)

        # 3D step scan parameters:
        self._mw.startV_3D_spinBox.setEnabled(True)
        self._mw.stopV_3D_spinBox.setEnabled(True)
        self._mw.scan_resolution_3D_spinBox.setEnabled(True)
        self._mw.smoothing_steps_3D_spinBox.setEnabled(True)
        self._mw.max_scan_resolution_3D_checkBox.setEnabled(True)
        self._mw.finesse_scan_freq_doubleSpinBox.setEnabled(True)

        # self._mw.action_zoom.setEnabled(True)

        # self.set_history_actions(True)

        # Enable the resume scan buttons if scans were unfinished
        # TODO: this needs to be implemented properly.

        # if self._scanning_logic._scan_continuable is True:
        #    self._mw.action_scan_resume.setEnabled(True)
        # else:
        #    self._mw.action_scan_resume.setEnabled(False)

        # Disable Position feedback buttons which can't be used during step scan
        self._mw.get_all_positions_pushButton.setEnabled(True)
        self._mw.set_x_position_pushButton.setEnabled(True)
        self._mw.set_y_position_pushButton.setEnabled(True)
        self._mw.set_z_position_pushButton.setEnabled(True)
        self._mw.move_all_axis_pushButton.setEnabled(True)
        self._mw.measure_pos_feedback_checkBox.setEnabled(True)

        self._currently_stepping = False

    def disable_3D_parameters(self):

        # disable parameters inputs:
        self._mw.startV_3D_spinBox.setEnabled(False)
        self._mw.stopV_3D_spinBox.setEnabled(False)
        self._mw.scan_resolution_3D_spinBox.setEnabled(False)
        self._mw.smoothing_steps_3D_spinBox.setEnabled(False)
        self._mw.max_scan_resolution_3D_checkBox.setEnabled(False)
        self._mw.finesse_scan_freq_doubleSpinBox.setEnabled(False)

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
        if self._stepper_logic.module_state() == 'locked':
            # Todo: Needs to be implemented when option in logic exists
            # self._stepper_logic.permanent_scan = False
            self._stepper_logic.stop_stepper()

        #Todo: Step actions should only be enabled after the logic has signalled that it has actually stopped
        self.enable_step_actions()

    def step_start_clicked(self):
        """ Manages what happens if the step scan is started. """
        self._stepper_logic.map_scan_position = self._mw.measure_pos_feedback_checkBox.isChecked()
        # update axes (both for position feedback and plot display)
        self._h_axis = self._stepper_logic._scan_axes[0]
        self._v_axis = self._stepper_logic._scan_axes[1]
        self._mw.step_scan_ViewWidget.setLabel('bottom', units=self._h_axis + 'Steps')
        self._mw.step_scan_ViewWidget.setLabel('left', units=self._v_axis + 'Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('bottom', units=self._h_axis + 'Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('left', units=self._v_axis + 'Steps')

        self.disable_step_actions()
        self.update_stepper_hardware_values()
        self._stepper_logic.start_stepper()  # tag='gui')

    def step_continued_clicked(self):
        """ Continue step scan. """
        self.disable_step_actions()
        self.update_stepper_hardware_values()
        self._stepper_logic.continue_stepper()  # tag='gui')

    def step_start_3D_clicked(self):
        """ Manages what happens if the step scan is started. """
        self._stepper_logic.map_scan_position = self._mw.measure_pos_feedback_checkBox.isChecked()
        # update axes (both for position feedback and plot display)
        self._h_axis = self._stepper_logic._scan_axes[0]
        self._v_axis = self._stepper_logic._scan_axes[1]
        self._mw.step_scan_ViewWidget.setLabel('bottom', units=self._h_axis + 'Steps')
        self._mw.step_scan_ViewWidget.setLabel('left', units=self._v_axis + 'Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('bottom', units=self._h_axis + 'Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('left', units=self._v_axis + 'Steps')

        self.disable_step_actions()
        self.disable_3D_parameters()
        self.update_stepper_hardware_values()
        self._stepper_logic._start_3D_step_scan()  # tag='gui')

    def step_start_Finesse_clicked(self):
        """ Manages what happens if the Finesse scan is started. """
        self._stepper_logic.map_scan_position = self._mw.measure_pos_feedback_checkBox.isChecked()
        # update axes (both for position feedback and plot display)
        self._h_axis = self._stepper_logic._scan_axes[0]
        self._v_axis = self._stepper_logic._scan_axes[1]
        self._mw.step_scan_ViewWidget.setLabel('bottom', units=self._h_axis + 'Steps')
        self._mw.step_scan_ViewWidget.setLabel('left', units=self._v_axis + 'Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('bottom', units=self._h_axis + 'Steps')
        self._mw.step_scan_ViewWidget_2.setLabel('left', units=self._v_axis + 'Steps')

        # as the program can only do one scan direction for the Finesse scan set fast scan state
        self._mw._fast_scan_checkBox.setCheckState(True)
        self.update_fast_scan_option()

        self.disable_step_actions()
        self.disable_3D_parameters()
        self.update_stepper_hardware_values()
        self._stepper_logic.start_finesse_measurement()  # tag='gui')

    def show_labbook(self):
        self._lab.show()

    def load_data(self):
        """Method for when the File -> Load Data action is clicked"""
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open data folder', QtWidgets.QFileDialog.ShowDirsOnly)
        self.log.info("the directory chosen is: %s",fname)
        dir_paths = fname.split("\\")
        if dir_paths[-2]=="ConfocalStepper_3D":
            data_type = "3D"
        elif dir_paths[-2] ==  "ConfocalStepper_finesse":
            data_type = "Finesse"
        elif dir_paths[-2] == "ConfocalStepper":
            data_type= "2D"
        else:
            self.log.warning("The chosen dir path '%s' does not contain usable data", fname)
            return -1

        self._stepper_logic.signal_load_data(fname, data_type)


    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

    def update_settings(self):
        """ Write new settings from the gui to the file. """

        self.fixed_aspect_ratio = self._sd.fixed_aspect_checkBox.isChecked()
        self.slider_small_step = self._sd.slider_small_step_DoubleSpinBox.value()
        self.slider_big_step = self._sd.slider_big_step_DoubleSpinBox.value()

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """

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
        if self._mw.cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.cb_high_percentile_DoubleSpinBox.value()
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
        if self.count_channel == 1:
            self._mw.step_scan_cb_ViewWidget.setLabel('left', 'Volt', units='V')
        else:
            self._mw.step_scan_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')

        self.refresh_image()

    def update_count_channel_2(self, index):
        """ The displayed channel for the image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.count_channel_2 = int(self._mw.count_channel_ComboBox_2.itemData(index,
                                                                          QtCore.Qt.UserRole))
        if self.count_channel == 1:
            self._mw.step_scan_cb_ViewWidget_2.setLabel('left', 'Volt', units='V')
        else:
            self._mw.step_scan_cb_ViewWidget_2.setLabel('left', 'Fluorescence', units='c/s')

        self.refresh_image()

    def update_count_direction(self, index):
        """ The displayed direction for the image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.count_direction = bool(self._mw.count_direction_ComboBox.itemData(index,
                                                                               QtCore.Qt.UserRole))
        self.refresh_image()

    def update_count_direction_2(self, index):
        """ The displayed direction for the image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.count_direction_2 = bool(self._mw.count_direction_ComboBox_2.itemData(index,
                                                                               QtCore.Qt.UserRole))
        self.refresh_image()

    def update_data_display_type(self, index):
        display_type = int(self._mw.data_display_type_ComboBox.itemData(index, QtCore.Qt.UserRole))
        self.log.warning("This tool isnt implemented yet")
        pass

    def update_data_display_type_2(self, index):
        display_type = int(self._mw.data_display_type_ComboBox_2.itemData(index, QtCore.Qt.UserRole))
        self.log.warning("This tool isnt implemented yet")
        pass

    def shortcut_to_cb_manual(self):
        """The absolute counts range for the colour bar was edited, update."""
        self._mw.cb_manual_RadioButton.setChecked(True)
        self.update_cb_range()

    def shortcut_to_cb_manual_2(self):
        """The absolute counts range for the colour bar was edited, update."""
        self._mw.cb_manual_RadioButton_2.setChecked(True)
        self.update_cb_range()

    def shortcut_to_cb_centiles(self):
        """The centiles range for the colour bar was edited, update."""
        self._mw.cb_centiles_RadioButton.setChecked(True)
        self.update_cb_range()

    def shortcut_to_cb_centiles_2(self):
        """The centiles range for the colour bar was edited, update."""
        self._mw.cb_centiles_RadioButton_2.setChecked(True)
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
        self.step_image_2.getViewBox().updateAutoRange()
        # Todo: this needs to have a check for the stepping direction and the correct data has to
        #  be chosen

        if self.count_direction:
            step_image_data = self._stepper_logic.image_raw[:, :, 2 + self.count_channel]
        else:
            step_image_data = self._stepper_logic.image_raw_back[:, :, 2 + self.count_channel]

        if self.count_direction_2:
            step_image_data_2 = self._stepper_logic.image_raw[:, :, 2 + self.count_channel_2]
        else:
            step_image_data_2 = self._stepper_logic.image_raw_back[:, :, 2 + self.count_channel_2]

        cb_range, cb_range_2 = self.get_cb_range()

        # Now update image with new color scale, and update colorbar
        self.step_image.setImage(image=step_image_data, levels=(cb_range[0], cb_range[1]))
        cb_range, cb_range_2 = self.get_cb_range()
        self.step_image_2.setImage(image=step_image_data_2, levels=(cb_range_2[0], cb_range_2[1]))
        self.refresh_colorbar()

        # Unlock state widget if scan is finished
        if self._stepper_logic.module_state() != 'locked':
            self.enable_step_actions()

    ################## Step Parameters ##################
    def update_fast_scan_option(self):
        """ The user changed if he wants to acquire both directions or just the forward one.
         Adjust all other GUI elements accordingly."""
        fast_scan = self._mw._fast_scan_checkBox.isChecked()
        self._stepper_logic._fast_scan = fast_scan
        if fast_scan:
            self.update_count_direction(0)
        self._mw.count_direction_ComboBox.setDisabled(fast_scan)
        self._mw.count_direction_ComboBox_2.setDisabled(fast_scan)

    def update_from_key(self, x=None, y=None, z=None):
        """The user pressed a key to move the crosshair, adjust all GUI elements.

        @param float x: new x position in m
        @param float y: new y position in m
        @param float z: new z position in m
        """
        if x is not None:
            self.update_roi_xy(h=x)
            if self._scanning_logic.depth_img_is_xz:
                self.update_roi_depth(h=x)
            self.update_slider_x(x)
            self.update_input_x(x)
            self._scanning_logic.set_position('xinput', x=x)
        if y is not None:
            self.update_roi_xy(v=y)
            if not self._scanning_logic.depth_img_is_xz:
                self.update_roi_depth(h=y)
            self.update_slider_y(y)
            self.update_input_y(y)
            self._scanning_logic.set_position('yinput', y=y)
        if z is not None:
            self.update_roi_depth(v=z)
            self.update_slider_z(z)
            self.update_input_z(z)
            self._scanning_logic.set_position('zinput', z=z)

    def update_step_direction(self):
        """ The user changed the step scan direction, adjust all
            other GUI elements."""

        direction = self._mw.inverted_direction_checkBox.isChecked()
        new_axes = self._mw.step_direction_comboBox.currentData()
        if direction:
            new_axes = self._inverted_axes[new_axes]
        self._scanning_logic._inverted_scan = direction
        self._scanning_logic.set_scan_axes(new_axes)
        self._mw.scan_frequency_3D_lcdNumber.display(self._stepper_logic.axis_class[self._stepper_logic._first_scan_axis].step_freq)

    def update_from_input_x_piezo(self):
        """ The user changed the number in the x piezo position spin box, adjust all
            other GUI elements."""
        #todo: this is not connected to anything yet.
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
        """The user moved the x piezo slider, adjust the other GUI elements.

        @params int sliderValue: slider piezo position, a quantized whole number
        """
        x_pos = self._scanning_logic.x_range[0] + sliderValue * self.slider_res
        self.update_input_x_piezo(x_pos)
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
        self._stepper_logic.axis_class['x'].steps_direction = self._mw.x_steps_InputWidget.value()

    def change_y_steps_range(self):
        """ Update the y steps range in the logic according to the GUI.
        """
        self._stepper_logic.axis_class['y'].steps_direction = self._mw.y_steps_InputWidget.value()

    def change_z_steps_range(self):
        """ Update the z steps range in the logic according to the GUI.
        """
        self._stepper_logic.axis_class['z'].steps_direction = self._mw.z_steps_InputWidget.value()

    # Todo: did not do this yet
    def change_x_piezo_range(self):
        """ Adjust the piezo range for x in the logic. """
        self._scanning_logic.image_x_range = [
            self._mw.x_piezo_min_InputWidget.value(),
            self._mw.x_piezo_max_InputWidget.value()]

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
        cb_range, cb_range_2 = self.get_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.cb_manual_RadioButton.isChecked():
            low_centile = self._mw.cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._stepper_logic.save_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        # if self._mw.count
        filepath = self._save_logic.get_path_for_module(module_name='ConfocalStepper')
        filename = filepath + os.sep + time.strftime(
            '%Y%m%d-%H%M-%S_confocal_step_scan_raw_pixel_image')
        if self._sd.save_purePNG_checkBox.isChecked():
            self.step_image.save(filename + '_raw.png')

    ################## 3DStep Scan Parameters ##################
    def scan_resolution_3D_changed(self):
        resolution = self._mw.scan_resolution_3D_spinBox.value()
        minV = min(self._stepper_logic.start_voltage_3D, self._stepper_logic.end_voltage_3D)
        maxV = max(self._stepper_logic.start_voltage_3D, self._stepper_logic.end_voltage_3D)
        maximal_scan_resolution = self._stepper_logic.calculate_resolution(16, [minV, maxV])
        if resolution < maximal_scan_resolution:
            self.log.warn("Maximum scan resolution of scanning device exceeded! Set scan resolution to maximum value.")
            self._stepper_logic.scan_resolution_3D = maximal_scan_resolution
            self._mw.scan_resolution_3D_spinBox.setValue(maximal_scan_resolution)
        else:
            self._stepper_logic.scan_resolution_3D = resolution

    def start_value_3D_changed(self):
        start = self._mw.startV_3D_spinBox.value()
        self._stepper_logic.start_voltage_3D = start
        self.update_scan_speed_3D()
        self.update_maximal_scan_resolution_3D()

    def stop_value_3D_changed(self):
        stop = self._mw.stopV_3D_spinBox.value()
        self._stepper_logic.end_voltage_3D = stop
        self.update_scan_speed_3D()
        self.update_maximal_scan_resolution_3D()

    def toggle_scan_resolution_3D(self):
        if self._mw.max_scan_resolution_3D_checkBox.isChecked():
            self._stepper_logic._3D_use_maximal_resolution = True
            self._mw.scan_resolution_3D_spinBox.setEnabled(False)
        else:
            self._stepper_logic._3D_use_maximal_resolution = False
            self._mw.scan_resolution_3D_spinBox.setEnabled(True)
            self.scan_resolution_3D_changed()

    def smoothing_steps_3D_changed(self):
        smoothing_steps = self._mw.smoothing_steps_3D_spinBox.value()
        self._stepper_logic._3D_smoothing_steps = smoothing_steps

    def update_scan_speed_3D(self):
        scan_speed = np.abs(self._stepper_logic.end_voltage_3D -
                            self._stepper_logic.start_voltage_3D) * \
                     self._stepper_logic.axis_class[self._stepper_logic._first_scan_axis].step_freq
        self._mw.scan_speed_3D_DisplayWidget.display(scan_speed)
        return

    def update_maximal_scan_resolution_3D(self):
        minV = min(self._stepper_logic.start_voltage_3D, self._stepper_logic.end_voltage_3D)
        maxV = max(self._stepper_logic.start_voltage_3D, self._stepper_logic.end_voltage_3D)
        maximal_scan_resolution = self._stepper_logic.calculate_resolution(16, [minV, maxV])
        self._mw.maximal_scan_resolution_3D_DisplayWidget.display(maximal_scan_resolution)
        return

    def finesse_scan_freq_changed(self):
        freq = self._mw.finesse_scan_freq_doubleSpinBox.value()
        self._stepper_logic.finesse_scan_freq = freq

    ################## Tilt Correction ##################
    def _correct_3rd_axis_changed(self):
        """Change the state of the 3rd axis tilt correction.
        Sets logic variable true or false, depending on what the user has clicked.
        """
        self._stepper_logic.correct_third_axis_for_tilt = self._mw.thrid_axis_correction_checkBox.checkState()

    def _correction_direction_3rd_axis_changed(self):
        """Change the tilt correction direction of the 3rd axis.
        Sets logic variable true (move axis up) or false (move axis down), depending on what the user has clicked.
        """
        self._stepper_logic._3rd_direction_correction = self._mw.move_3rd_axis_up_checkBox.checkState()

    def _correction_nth_line_3rd_axis_changed(self):
        """Change the tilt correction direction of the 3rd axis.
        Sets logic variable true (move axis up) or false (move axis down), depending on what the user has clicked.
        """
        value = self._mw.correct_every_x_lines_tilt_spinBox.value()
        if value == 0:
            self._stepper_logic.correct_third_axis_for_tilt = False
            self._mw.correct_every_x_lines_tilt_spinBox.setValue(100)
            self._mw.thrid_axis_correction_checkBox.setChecked(False)
            self.log.info("correcting every 0th lines is not possible, so the correction was turned off and the "
                          "value set to a possible value")
        self._stepper_logic._lines_correct_3rd_axis = value

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
        # self._mw.scanLineDockWidget.hide()

        # re-dock any floating dock widgets
        self._mw.step_dockWidget.setFloating(False)
        self._mw.scan_control_dockWidget.setFloating(False)
        self._mw.hardware_dockWidget.setFloating(False)
        self._mw.tilt_correction_dockWidget.setFloating(False)
        # self._mw.scanLineDockWidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.step_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.scan_control_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.tilt_correction_dockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.scanLineDockWidget)
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

    def logic_started_3D_stepping(self, tag):
        """ Disable icons if a scan was started.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_step_actions()
            self.disable_3D_parameters()

    ################## ROI ######################
    def update_from_roi(self, roi):
        """The user manually moved the ROI (region of interest), adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        # Todo: Add option if backward picture is shown
        if self._stepper_logic.map_scan_position and not self._currently_stepping:
            # This is a safety precaution
            self._feedback_axis["x"].setValue(self._mw.x_position_doubleSpinBox.value())
            self._feedback_axis["y"].setValue(self._mw.y_position_doubleSpinBox.value())
            self._feedback_axis["z"].setValue(self._mw.z_position_doubleSpinBox.value())

            # Find position of ROI
            h_step_pos = int(roi.pos()[0])
            v_step_pos = int(roi.pos()[1])

            if h_step_pos < 0:
                h_step_pos = 0
            elif h_step_pos > self._stepper_logic._steps_scan_first_line - 1:
                h_step_pos = self._stepper_logic._steps_scan_first_line - 1

            if v_step_pos < 0:
                v_step_pos = 0
            elif v_step_pos > self._stepper_logic._steps_scan_second_line - 1:
                v_step_pos = self._stepper_logic._steps_scan_first_line - 1
            h_pos = self._stepper_logic.full_image_smoothed[v_step_pos, h_step_pos, 0]
            v_pos = self._stepper_logic.full_image_smoothed[v_step_pos, h_step_pos, 1]

            self._feedback_axis[self._stepper_logic._first_scan_axis].setValue(h_pos * 1e-3)
            self._feedback_axis[self._stepper_logic._second_scan_axis].setValue(v_pos * 1e-3)
