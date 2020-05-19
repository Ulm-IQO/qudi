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


class Scanner3DMainWindow(QtWidgets.QMainWindow):
    """ The main window for the 3D scan measurement GUI.
    """

    sigPressKeyBoard = QtCore.Signal(QtCore.QEvent)

    def __init__(self):
        # Get the path to the *.ui filezorry
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanner_3D_gui.ui')

        # Load it
        super(Scanner3DMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

        def keyPressEvent(self, event):
            """Pass the keyboard press event from the main window further. """
            self.sigPressKeyBoard.emit(event)


class Scanner3DSettingDialog(QtWidgets.QDialog):
    """ The settings dialog for 3D scan measurements.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanner_3D_settings.ui')

        # Load it
        super(Scanner3DSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class OptimizerSettingDialog(QtWidgets.QDialog):
    """ User configurable settings for the optimizer embedded in scanner 3D gui"""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_optim_settings.ui')

        # Load it
        super(OptimizerSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class Scanner3DGui(GUIBase):
    """
    This is the GUI Class for Confocal measurements
    """

    _modclass = 'Scanner3DGui'
    _modtype = 'gui'

    # declare connectors
    savelogic = Connector(interface='SaveLogic')
    scanner3Dlogic = Connector(interface='Scanner3DLogic')
    optimizerlogic1 = Connector(interface='OptimizerLogic')

    fixed_aspect_ratio = ConfigOption('fixed_aspect_ratio', True)
    image_x_padding = ConfigOption('image_x_padding', 0.02)
    image_y_padding = ConfigOption('image_y_padding', 0.02)
    image_z_padding = ConfigOption('image_z_padding', 0.02)

    default_meter_prefix = ConfigOption('default_meter_prefix', None)  # assume the unit prefix of position spinbox

    # status var
    adjust_cursor_roi = StatusVar(default=True)
    slider_small_step = StatusVar(default=10e-9)  # initial value in meter
    slider_big_step = StatusVar(default=100e-9)  # initial value in meter

    # signals
    sigSaveMeasurement = QtCore.Signal(str, list, list)
    sigStartOptimizer = QtCore.Signal(list, str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # self.log.info('The following configuration was found.')

        # checking for the right configuration
        # for key in config.keys():
        #    self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition, configuration and initialisation of the Scan 3D GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._scanner_logic = self.scanner3Dlogic()
        self._save_logic = self.savelogic()
        self._optimizer_logic = self.optimizerlogic1()

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
        # Disconnect signals
        pass

    def initMainUI(self):
        """ Definition, configuration and initialisation of the Scanner 3D GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        self._mw = Scanner3DMainWindow()
        self._sd = Scanner3DSettingDialog()

        ###################################################################
        #               Configuring the dock widgets                      #
        ###################################################################
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self.init_scan_parameters_UI()
        self.init_plot_scan_UI()
        self.init_position_feedback_UI()
        self.init_fast_axis_scan_parameters()

        # Set the state button as ready button as default setting.
        self._mw.action_scan_3D_start.setEnabled(True)
        self._mw.action_scan_3D_resume.setEnabled(False)

        # Connect other signals from the logic with an update of the gui
        self._scanner_logic.signal_start_scanning.connect(self.logic_started_scanning)
        self._scanner_logic.signal_continue_scanning.connect(self.logic_continued_scanning)

        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._mw.actionSave_Scan.triggered.connect(self.save_scan_data)

        #################################################################
        #                           Actions                             #
        #################################################################
        # Connect the scan actions to the events if they are clicked. Connect
        # also the adjustment of the displayed windows.
        self._mw.action_scan_3D_stop.triggered.connect(self.ready_clicked)

        self._scan_3D_start_proxy = pg.SignalProxy(
            self._mw.action_scan_3D_start.triggered,
            delay=0.1,
            slot=self.scan_start_clicked
        )
        self._scan_3D_resume_proxy = pg.SignalProxy(
            self._mw.action_scan_3D_resume.triggered,
            delay=0.1,
            slot=self.scan_continued_clicked
        )

        ###################################################################
        #               Icons for the scan actions                        #
        ###################################################################

        self._scan_single_icon = QtGui.QIcon()
        self._scan_single_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_loop_icon = QtGui.QIcon()
        self._scan_loop_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-loop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        # self._get_former_parameters()

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

    def init_plot_scan_UI(self):
        self._currently_scanning = False
        # Get the image for the display from the logic.
        # todo: image update!
        self.scan_image = pg.ImageItem(image=self._scanner_logic.image_2D[:, :, 3], axisOrder='row-major')
        # Todo: Add option to see data from other counter later

        # Add the display item  ViewWidget, which was defined in the UI file:
        self._mw.ViewWidget.addItem(self.scan_image)

        # Label the axes:
        self._mw.ViewWidget.setLabel('bottom', 'X position', units='m')
        self._mw.ViewWidget.setLabel('left', 'Y position', units='m')

        # Create Region of Interest for xy image and add to xy Image Widget:
        # Get the image for the display from the logic
        scan_image_data = self._scanner_logic.image_2D[:, :, 3]
        ini_pos_x_crosshair = len(scan_image_data) / 2
        ini_pos_y_crosshair = len(scan_image_data) / 2

        # Create crosshair for image:
        self._mw.ViewWidget.toggle_crosshair(True, movable=True)
        self._mw.ViewWidget.set_crosshair_min_size_factor(0.02)
        self._mw.ViewWidget.set_crosshair_pos((ini_pos_x_crosshair, ini_pos_y_crosshair))
        self._mw.ViewWidget.set_crosshair_size(
            (self._optimizer_logic.refocus_XY_size, self._optimizer_logic.refocus_XY_size))
        # connect the drag event of the crosshair with a change in scanner position:
        self._mw.ViewWidget.sigCrosshairDraggedPosChanged.connect(self.update_from_roi)

        # Connect the signal from the logic with an update of the cursor position
        self._scanner_logic.signal_change_position.connect(self.update_crosshair_position_from_logic)

        # Set up and connect count channel combobox
        scan_channels = self._scanner_logic._get_scanner_count_channels()
        self.digital_count_channels = len(scan_channels)
        scan_channels.append(self._scanner_logic._ai_counter)
        for n, ch in enumerate(scan_channels):
            self._mw.count_channel_ComboBox.addItem(str(ch), n)

        self._mw.count_channel_ComboBox.activated.connect(self.update_count_channel)
        self.count_channel = int(self._mw.count_channel_ComboBox.currentData())

        #################################################################
        #           Connect the colorbar and their actions              #
        #################################################################

        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleInferno()
        self.scan_image.setLookupTable(self.my_colors.lut)

        # Create colorbars and add them at the desired place in the GUI. Add
        # also units to the colorbar.

        self.cb = ColorBar(self.my_colors.cmap_normed, width=50, cb_min=0, cb_max=100)
        self._mw.cb_ViewWidget.addItem(self.cb)
        self._mw.cb_ViewWidget.hideAxis('bottom')
        self._mw.cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.cb_ViewWidget.setMouseEnabled(x=False, y=False)

        self._mw.sigPressKeyBoard.connect(self.keyPressEvent)
        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture:
        self._scanner_logic.signal_image_updated.connect(self.refresh_image)
        self._scanner_logic.sigImageInitialized.connect(self.adjust_window)

        # Connect the buttons and inputs for the colorbar
        self._mw.cb_manual_RadioButton.clicked.connect(self.update_cb_range)
        self._mw.cb_centiles_RadioButton.clicked.connect(self.update_cb_range)

        self._mw.cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_manual)
        self._mw.cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_manual)
        self._mw.cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_centiles)
        self._mw.cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_cb_centiles)

        # Connect the tracker
        self.sigStartOptimizer.connect(self._optimizer_logic.start_refocus)
        self._optimizer_logic.sigRefocusXySizeChanged.connect(self.update_roi_size)

        # Connect the change of the viewed area to an adjustment of the ROI:
        self.adjust_cursor_roi = True
        self.update_crosshair_position_from_logic('init')
        self.adjust_window()

    def init_position_feedback_UI(self):
        """
            Initialises all values for the position feedback of the 3D scanner
            Depending on the feedback of the scanner axis used some options will not be available
            """
        #### Initialize the position feedback LCD labels ####

        #  Check which axes have position feedback option
        self._feedback_axis = {}
        # Todo: check which position feedback axis exist
        self._x_closed_loop = True
        self._y_closed_loop = True
        self._z_closed_loop = True
        # Todo: The corresponding functions do not yet exist in the scanner 3D logic. Therefore it is set to false

        # X Axis
        if self._x_closed_loop:
            self._feedback_axis["x"] = self._mw.x_position_image_doubleSpinBox
        else:
            self._mw.x_accuracy_doubleSpinBox.setValue(-1)
            self._mw.x_accuracy_doubleSpinBox.setValue(-1)

        # Y Axis
        if self._y_closed_loop:
            self._feedback_axis["y"] = self._mw.y_position_image_doubleSpinBox
        else:
            self._mw.y_accuracy_doubleSpinBox.setValue(-1)
            self._mw.y_position_doubleSpinBox.setValue(-1)

        # Z Axis
        if self._z_closed_loop:
            self._feedback_axis["z"] = self._mw.z_position_image_doubleSpinBox
        else:
            self._mw.z_accuracy_doubleSpinBox.setValue(-1)
            self._mw.z_position_doubleSpinBox.setValue(-1)

        # connect actions
        self._mw.get_all_positions_pushButton.clicked.connect(self.get_scanner_position)

        self._mw.start_position_bool_checkBox.clicked.connect(self.update_move_to_start)
        self._mw.save_pos_feedback_checkBox.clicked.connect(self.update_save_position)

    # Todo: ROI things happening
    def init_scan_parameters_UI(self):
        self._mw.x_scan_resolution_InputWidget.setValue(self._scanner_logic.xy_resolution)
        self._mw.y_scan_resolution_InputWidget.setValue(self._scanner_logic.xy_resolution)
        # Todo: This is only correct while the z axis is always the fast axis
        self._mw.z_scan_resolution_InputWidget.setValue(self._scanner_logic.scan_resolution_fast_axis)

        self._mw.x_scan_resolution_InputWidget.valueChanged.connect(self.change_x_resolution)
        self._mw.y_scan_resolution_InputWidget.valueChanged.connect(self.change_y_resolution)
        self._mw.z_scan_resolution_InputWidget.valueChanged.connect(self.change_z_resolution)

        # These connect to confocal logic such that the piezos are moved
        # Setup the Sliders:
        # Calculate the needed Range for the sliders. The image ranges coming
        # from the Logic module must be in meters.
        # 1 nanometer resolution per one change, units are meters
        self.slider_res = 1e-9

        # How many points are needed for that kind of resolution:
        num_of_points_x = (self._scanner_logic._scanning_axes_ranges["x"][1] -
                           self._scanner_logic._scanning_axes_ranges["x"][0]) / self.slider_res
        num_of_points_y = (self._scanner_logic._scanning_axes_ranges["y"][1] -
                           self._scanner_logic._scanning_axes_ranges["y"][0]) / self.slider_res
        num_of_points_z = (self._scanner_logic._scanning_axes_ranges["z"][1] -
                           self._scanner_logic._scanning_axes_ranges["z"][0]) / self.slider_res

        # Set a Range for the sliders:
        self._mw.x_SliderWidget.setRange(0, num_of_points_x)
        self._mw.y_SliderWidget.setRange(0, num_of_points_y)
        self._mw.z_SliderWidget.setRange(0, num_of_points_z)

        # Just to be sure, set also the possible maximal values for the spin
        # boxes of the current values:
        self._mw.x_current_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["x"][0],
                                                self._scanner_logic._scanning_axes_ranges["x"][1])
        self._mw.y_current_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["y"][0],
                                                self._scanner_logic._scanning_axes_ranges["y"][1])
        self._mw.z_current_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["z"][0],
                                                self._scanner_logic._scanning_axes_ranges["z"][1])

        # Predefine the maximal and minimal image range as the default values
        # for the display of the range:
        self._mw.x_min_InputWidget.setValue(self._scanner_logic._scanning_axes_ranges["x"][0])
        self._mw.x_max_InputWidget.setValue(self._scanner_logic._scanning_axes_ranges["x"][1])
        self._mw.y_min_InputWidget.setValue(self._scanner_logic._scanning_axes_ranges["y"][0])
        self._mw.y_max_InputWidget.setValue(self._scanner_logic._scanning_axes_ranges["y"][1])
        self._mw.z_min_InputWidget.setValue(self._scanner_logic._scanning_axes_ranges["z"][0])
        self._mw.z_max_InputWidget.setValue(self._scanner_logic._scanning_axes_ranges["z"][1])

        # set the maximal ranges for the image range from the logic:
        self._mw.x_min_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["x"][0],
                                            self._scanner_logic._scanning_axes_ranges["x"][1])
        self._mw.x_max_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["x"][0],
                                            self._scanner_logic._scanning_axes_ranges["x"][1])
        self._mw.y_min_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["y"][0],
                                            self._scanner_logic._scanning_axes_ranges["y"][1])
        self._mw.y_max_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["y"][0],
                                            self._scanner_logic._scanning_axes_ranges["y"][1])
        self._mw.z_min_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["z"][0],
                                            self._scanner_logic._scanning_axes_ranges["z"][1])
        self._mw.z_max_InputWidget.setRange(self._scanner_logic._scanning_axes_ranges["z"][0],
                                            self._scanner_logic._scanning_axes_ranges["z"][1])

        if self.default_meter_prefix:
            self._mw.x_current_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.y_current_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.z_current_InputWidget.assumed_unit_prefix = self.default_meter_prefix

            self._mw.x_min_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.x_max_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.y_min_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.y_max_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.z_min_InputWidget.assumed_unit_prefix = self.default_meter_prefix
            self._mw.z_max_InputWidget.assumed_unit_prefix = self.default_meter_prefix

        # Handle slider movements by user:
        self._mw.x_SliderWidget.sliderMoved.connect(self.update_from_slider_x)
        self._mw.y_SliderWidget.sliderMoved.connect(self.update_from_slider_y)
        self._mw.z_SliderWidget.sliderMoved.connect(self.update_from_slider_z)

        # Update the inputed/displayed numbers if the cursor has left the field:
        self._mw.x_current_InputWidget.editingFinished.connect(self.update_from_input_x)
        self._mw.y_current_InputWidget.editingFinished.connect(self.update_from_input_y)
        self._mw.z_current_InputWidget.editingFinished.connect(self.update_from_input_z)

        self._mw.x_min_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.editingFinished.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.editingFinished.connect(self.change_z_image_range)

        # Add Scan Directions
        self._mw.scan_direction_comboBox.addItem("XYZ", "xyz")
        self._mw.scan_direction_comboBox.addItem("XZY", "xzy")
        self._mw.scan_direction_comboBox.addItem("YZX", "yzx")
        self._inverted_axes = {"xyz": "yxz", "xzy": "zxy", "yzx": "zyx", "yxz": "xyz", "zxy": "xzy", "zyx": "yzx"}
        self._mw.scan_direction_comboBox.activated.connect(self.update_scan_direction)
        self._mw.inverted_direction_checkBox.clicked.connect(self.update_scan_direction)

        self._scanner_logic.signal_stop_scanning.connect(self.enable_step_actions)

    def init_fast_axis_scan_parameters(self):
        # setting GUI elements enabled
        self._mw.scan_resolution_fast_axis_spinBox.setEnabled(True)
        self._mw.smoothing_steps_fast_axis_spinBox.setEnabled(True)
        self._mw.smooth_fast_axis_checkBox.setEnabled(True)

        # Todo: this needs to be done differently, as it is extremely error prone
        self._max_voltage_range_fast_axis = self._scanner_logic._scanning_device._ao_voltage_range["z"].copy()
        self._max_position_range_fast_axis = self._scanner_logic._scanning_axes_ranges["z"].copy()

        # scan speed
        # Todo: set maximally possible scan freq depending on hardware max clock freq.
        self._mw.scan_freq_fast_axis_doubleSpinBox.setValue(self._scanner_logic.scan_freq_fast_axis)
        self._mw.scan_freq_fast_axis_doubleSpinBox.editingFinished.connect(self.scan_freq_fast_axis_changed,
                                                                           QtCore.Qt.QueuedConnection)
        self._mw.scan_speed_m_fast_axis_doubleSpinBox.setValue(np.abs(self._scanner_logic.image_ranges["z"][1] -
                                                                      self._scanner_logic.image_ranges["z"][0]) *
                                                               self._mw.scan_freq_fast_axis_doubleSpinBox.value())
        self._mw.scan_speed_V_fast_axis_doubleSpinBox.setValue(np.abs(self._max_voltage_range_fast_axis[1] -
                                                                      self._max_voltage_range_fast_axis[0]) *
                                                               self._mw.scan_freq_fast_axis_doubleSpinBox.value())

        # scan resolution
        self._mw.scan_resolution_fast_axis_spinBox.setValue(self._scanner_logic.scan_resolution_fast_axis)
        self._mw.scan_resolution_fast_axis_V_doubleSpinBox.setValue(
            abs(self._max_voltage_range_fast_axis[1] - self._max_voltage_range_fast_axis[0]) / abs(
                self._max_position_range_fast_axis[1] - self._max_position_range_fast_axis[0]) *
            self._mw.scan_resolution_fast_axis_spinBox.value())

        # todo: here it should actually find out the bit resolution of the hardware
        self._mw.maximal_scan_resolution_fast_axis_doubleSpinBox.setValue(self._scanner_logic.calculate_resolution(
            16, [self._scanner_logic.image_ranges["z"][0], self._scanner_logic.image_ranges["z"][1]]))
        self._mw.max_scan_resolution_fast_axis_checkBox.toggled.connect(self.max_scan_resolution_fast_axis_clicked)
        self._mw.scan_resolution_fast_axis_spinBox.valueChanged.connect(self.scan_resolution_fast_axis_changed)

        # smoothing
        self._mw.smooth_fast_axis_checkBox.setCheckState(self._scanner_logic.smoothing)
        self._mw.smooth_fast_axis_checkBox.toggled.connect(self.smoothing_fast_axis_clicked)
        self._mw.smoothing_steps_fast_axis_spinBox.setValue(self._scanner_logic._fast_axis_smoothing_steps)
        self._mw.smoothing_steps_fast_axis_spinBox.setRange(0, 500)

        # todo: this needs to be adjusted according to the steps used for
        # one scan it can not be higher than half the amount of steps for one scan ramp
        self._mw.smoothing_steps_fast_axis_spinBox.editingFinished.connect(self.smoothing_steps_fast_axis_changed,
                                                                           QtCore.Qt.QueuedConnection)

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
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        position = self._scanner_logic._current_position.copy()  # in meters
        x_pos = position["x"]
        y_pos = position["y"]
        z_pos = position["z"]

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
        # inv_axes = self._scanner_logic._inverted_scan
        # self._mw.inverted_direction_checkBox.setCheckState(inv_axes)
        # if inv_axes:
        #    current_axes = self._inverted_axes[self._scanner_logic._scan_axes]
        # else:
        #    current_axes = self._scanner_logic._scan_axes
        # axes = self._mw.scan_direction_comboBox.findData(current_axes)
        # if axes == -1:
        #    self.log.error("the axes given in the scanner 3D logic is not possible in the gui")
        # else:
        #    self._mw.scan_direction_comboBox.setCurrentIndex(axes)
        # Label the axes:
        # self._mw.ViewWidget.setLabel('bottom', units=current_axes[0] + ' Steps')
        # self._mw.ViewWidget.setLabel('left', units=current_axes[1] + ' Steps')
        pass
        # todo: The actions programmed here do not yet exist in the logic

    ##################  Scan ##################
    def get_cb_range(self):
        """ Determines the cb_min and cb_max values for the image
        """
        # If "Manual" is checked, or the image data is empty (all zeros),
        # then take manual cb range.
        if self._mw.cb_manual_RadioButton.isChecked() or np.max(
                self.scan_image.image) == 0.0:
            cb_min = self._mw.cb_min_DoubleSpinBox.value()
            cb_max = self._mw.cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            image_nonzero = self.scan_image.image[np.nonzero(self.scan_image.image)]

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

    # Todo: write function
    def get_scanner_position(self):
        """Measures the current positions of the scanner for the axis with position feedback"""
        """Measures the current positions of the stepper for the axis with position feedback"""
        result = self._scanner_logic.get_position_from_feedback([*self._feedback_axis])  # get position for keys of feedback axes
        if self._x_closed_loop:
            self._mw.x_position_doubleSpinBox.setValue(result[0] * 1e-3)
        if self._y_closed_loop:
            self._mw.y_position_doubleSpinBox.setValue(result[self._x_closed_loop] * 1e-3)
        if self._z_closed_loop:
            self._mw.z_position_doubleSpinBox.setValue(result[self._x_closed_loop + self._y_closed_loop] * 1e-3)

    ################## Tool bar ##################
    def disable_step_actions(self):
        """ Disables the buttons for scanning.
        """
        # Enable the stop scanning button
        self._mw.action_scan_3D_stop.setEnabled(True)

        # Disable the start scan buttons
        self._mw.action_scan_3D_start.setEnabled(False)
        self._mw.action_scan_3D_resume.setEnabled(False)

        self._mw.x_min_InputWidget.setEnabled(False)
        self._mw.x_max_InputWidget.setEnabled(False)
        self._mw.y_min_InputWidget.setEnabled(False)
        self._mw.y_max_InputWidget.setEnabled(False)
        self._mw.z_min_InputWidget.setEnabled(False)
        self._mw.z_max_InputWidget.setEnabled(False)

        self._mw.x_scan_resolution_InputWidget.setEnabled(False)
        self._mw.y_scan_resolution_InputWidget.setEnabled(False)
        self._mw.z_scan_resolution_InputWidget.setEnabled(False)

        self._mw.inverted_direction_checkBox.setEnabled(False)
        self._mw.scan_direction_comboBox.setEnabled(False)

        # Todo: Do Zoom
        # Set the zoom button if it was pressed to unpressed and disable it
        # self._mw.action_zoom.setChecked(False)
        # self._mw.action_zoom.setEnabled(False)

        # no history exist for 3D scanner yet
        # self.set_history_actions(False)

        # Disable Position feedback buttons which can't be used during step scan
        self._mw.get_all_positions_pushButton.setEnabled(False)
        self._mw.measure_pos_feedback_checkBox.setEnabled(False)

        # Fast axis scan parameters:
        self._mw.scan_freq_fast_axis_doubleSpinBox.setEnabled(False)
        self._mw.scan_resolution_fast_axis_spinBox.setEnabled(False)
        self._mw.max_scan_resolution_fast_axis_checkBox.setEnabled(False)
        self._mw.smooth_fast_axis_checkBox.setEnabled(False)

        self._mw.smoothing_steps_fast_axis_spinBox.setEnabled(False)

        self._currently_scanning = True

    def enable_step_actions(self):
        """ Reset the scan action buttons to the default active
        state when the system is idle.
        """
        # Disable the stop scanning button
        self._mw.action_scan_3D_stop.setEnabled(False)

        # Enable the scan buttons
        self._mw.action_scan_3D_start.setEnabled(True)
        self._mw.action_scan_3D_start.setEnabled(True)
        self._mw.action_scan_Finesse_start.setEnabled(True)

        # self._mw.action_optimize_position.setEnabled(True)

        self._mw.x_min_InputWidget.setEnabled(True)
        self._mw.x_max_InputWidget.setEnabled(True)
        self._mw.y_min_InputWidget.setEnabled(True)
        self._mw.y_max_InputWidget.setEnabled(True)
        self._mw.z_min_InputWidget.setEnabled(True)
        self._mw.z_max_InputWidget.setEnabled(True)

        self._mw.x_scan_resolution_InputWidget.setEnabled(True)
        self._mw.y_scan_resolution_InputWidget.setEnabled(False)
        self._mw.z_scan_resolution_InputWidget.setEnabled(False)

        self._mw.inverted_direction_checkBox.setEnabled(False)
        self._mw.scan_direction_comboBox.setEnabled(False)

        # Fast axis scan parameters:
        self._mw.scan_freq_fast_axis_doubleSpinBox.setEnabled(True)
        self._mw.scan_resolution_fast_axis_spinBox.setEnabled(True)
        self._mw.max_scan_resolution_fast_axis_checkBox.setEnabled(True)
        self._mw.smooth_fast_axis_checkBox.setEnabled(True)
        if self._mw.smooth_fast_axis_checkBox.isChecked():
            self._mw.smoothing_steps_fast_axis_spinBox.setEnabled(True)

        # self._mw.action_zoom.setEnabled(True)

        # self.set_history_actions(True)

        # Enable the resume scan buttons if scans were unfinished
        # TODO: this needs to be implemented properly.
        # For now they will just be enabled by default

        if self._scanner_logic._scan_continuable is True:
            self._mw.action_scan_3D_resume.setEnabled(True)
        else:
            self._mw.action_scan_3D_resume.setEnabled(False)

        # Disable Position feedback buttons which can't be used during step scan
        self._mw.get_all_positions_pushButton.setEnabled(True)
        self._mw.measure_pos_feedback_checkBox.setEnabled(True)

        self._currently_scanning = False

    def set_history_actions(self, enable):
        """ Enable or disable history arrows taking history state into account. """
        pass
        # there is no history in the logic
        if enable and self._scanner_logic.history_index < len(
                self._scanner_logic.history) - 1:
            self._mw.actionForward.setEnabled(True)
        else:
            self._mw.actionForward.setEnabled(False)
        if enable and self._scanner_logic.history_index > 0:
            self._mw.actionBack.setEnabled(True)
        else:
            self._mw.actionBack.setEnabled(False)

    def ready_clicked(self):
        """ Stop the scan if the state has switched to ready. """
        if self._scanner_logic.module_state() == 'locked':
            # Todo: Needs to be implemented when option in logic exists
            # self._scanner_logic.permanent_scan = False
            self._scanner_logic.stop_3D_scan()

        self.enable_step_actions()

    def scan_start_clicked(self):
        """ Manages what happens if the scan is started. """
        self._scanner_logic.map_scan_positions = self._mw.measure_pos_feedback_checkBox.isChecked()

        # Todo: This is code that can be used, when scan axes are flexible in the future
        # update axes (both for position feedback and plot display)
        # self._h_axis = self._scanner_logic._scan_axes[0]
        # self._v_axis = self._scanner_logic._scan_axes[1]
        # self._mw.ViewWidget.setLabel('bottom', units=self._h_axis + 'm')
        # self._mw.ViewWidget.setLabel('left', units=self._v_axis + 'm')

        self.disable_step_actions()
        self._scanner_logic.start_3D_scan()  # tag='gui')

    def scan_continued_clicked(self):
        """ Continue 3D scan. """
        self.disable_step_actions()
        self._scanner_logic.continue_3D_scan()  # tag='gui')

    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

    def update_settings(self):
        """ Write new settings from the gui to the file. """
        # Todo: Needs to be implemented when option in logic exists
        # self._scanner_logic.permanent_scan = self._sd.loop_scan_CheckBox.isChecked()
        self.fixed_aspect_ratio = self._sd.fixed_aspect_checkBox.isChecked()
        self.slider_small_step = self._sd.slider_small_step_DoubleSpinBox.value()
        self.slider_big_step = self._sd.slider_big_step_DoubleSpinBox.value()

        # Update GUI icons to new loop-scan state
        self._set_scan_icons()

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        # Todo: Needs to be implemented when option in logic exists
        self._sd.loop_scan_CheckBox.setChecked(self._scanner_logic.permanent_scan)
        direction = self._scanner_logic._scan_axes

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
        # todo: check! signal
        return

    ################## Scan ##################
    def update_count_channel(self, index):
        """ The displayed channel for the image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.count_channel = int(self._mw.count_channel_ComboBox.itemData(index,
                                                                          QtCore.Qt.UserRole))
        if self.count_channel >= self.digital_count_channels:
            self._mw.cb_ViewWidget.setLabel('left', 'Volt', units='V')
        else:
            self._mw.cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')

        self.refresh_image()

    # Todo: anpassen

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
        self.scan_image.getViewBox().updateAutoRange()
        # Todo: this needs to have a check for the direction and the correct data has to
        #  be chosen
        # if self.count_direction:
        # Todo: add count_direction variable

        # Todo: getting the data like this only works if the first channel for analog are always counter in logic!
        image_data = self._scanner_logic.image_2D[:, :, 3 + self.count_channel]

        cb_range = self.get_cb_range()

        # Now update image with new color scale, and update colorbar
        self.scan_image.setImage(image=image_data, levels=(cb_range[0], cb_range[1]))
        cb_range = self.get_cb_range()
        self.scan_image.setImage(image=image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_colorbar()

        # Unlock state widget if scan is finished
        if self._scanner_logic.module_state() != 'locked':
            self.enable_step_actions()

    ################## Position Feedback ################
    def update_move_to_start(self):
        pass

    def update_save_position(self):
        self._scanner_logic._save_positions = self._mw.save_pos_feedback_checkBox.isChecked()

    ################## Scan Parameters ##################
    def update_scan_direction(self):
        """ The user changed the step scan direction, adjust all
            other GUI elements."""

        direction = self._mw.inverted_direction_checkBox.isChecked()
        new_axes = self._mw.scan_direction_comboBox.currentData()
        if direction:
            new_axes = self._inverted_axes[new_axes]
        self._scanner_logic._inverted_scan = direction

        # todo: this method does not exist yet
        self._scanner_logic.set_scan_axes(new_axes)

    def update_from_key(self, x=None, y=None, z=None):
        """The user pressed a key to move the crosshair, adjust all GUI elements.

        @param float x: new x position in m
        @param float y: new y position in m
        @param float z: new z position in m
        """
        pos = {}
        if x is not None:
            self.update_roi(h=x)
            self.update_slider_x(x)
            self.update_input_x(x)
            pos["x"] = x
        if y is not None:
            self.update_roi(v=y)
            self.update_slider_y(y)
            self.update_input_y(y)
            pos["y"] = y
        if z is not None:
            self.update_slider_z(z)
            self.update_input_z(z)
            pos["z"] = z
        if pos:
            self._scanner_logic.move_to_position(pos, 'key')

    def update_from_input_x(self):
        """ The user changed the number in the current x position spin box, adjust all
            other GUI elements."""
        x_pos = self._mw.x_current_InputWidget.value()
        self.update_slider_piezo_x(x_pos)
        self._scanner_logic.move_to_position({"x": x_pos}, "xinput")
        # todo: ROI

    def update_from_input_y(self):
        """ The user changed the number in the current y position spin box, adjust all
            other GUI elements."""
        y_pos = self._mw.y_current_InputWidget.value()
        self.update_slider_y(y_pos)
        self._scanner_logic.move_to_position({"y": y_pos}, "yinput")
        # todo: ROI

    def update_from_input_z(self):
        """ The user changed the number in the current z position spin box, adjust all
           other GUI elements."""
        z_pos = self._mw.z_current_InputWidget.value()
        self.update_slider_piezo_z(z_pos)
        self._scanner_logic.move_to_position({"z": z_pos}, "zinput")
        # todo: ROI

    def update_input_x(self, x_pos):
        """ Update the displayed x-value.

        @param float x_pos: the current value of the x position in m
        """
        # Convert x_pos to number of points for the slider:
        self._mw.x_current_InputWidget.setValue(x_pos)

    def update_input_y(self, y_pos):
        """ Update the displayed y-value.

        @param float y_pos: the current value of the y position in m
        """
        # Convert x_pos to number of points for the slider:
        self._mw.y_current_InputWidget.setValue(y_pos)

    def update_input_z(self, z_pos):
        """ Update the displayed z-value.

        @param float z_pos: the current value of the z position in m
        """
        # Convert x_pos to number of points for the slider:
        self._mw.z_current_InputWidget.setValue(z_pos)

    def update_from_slider_x(self, sliderValue):
        """The user moved the x slider , adjust the other GUI elements.

        @params int sliderValue: slider position, a quantized whole number
        """
        x_pos = self._scanner_logic._scanning_axes_ranges["x"][0] + sliderValue * self.slider_res
        self.update_roi(h=x_pos)
        self.update_input_x(x_pos)
        self._scanner_logic.move_to_position({"x": x_pos}, 'xslider')
        self._optimizer_logic.set_position('xslider', x=x_pos)

    def update_from_slider_y(self, sliderValue):
        """The user moved the y slider, adjust the other GUI elements.

        @params int sliderValue: slider position, a quantized whole number
        """
        y_pos = self._scanner_logic._scanning_axes_ranges["y"][0] + sliderValue * self.slider_res
        self.update_roi(h=y_pos)
        self.update_input_y(y_pos)
        self._scanner_logic.move_to_position({"y": y_pos}, 'yslider')
        self._optimizer_logic.set_position('yslider', x=y_pos)

    def update_from_slider_z(self, sliderValue):
        """The user moved the z slider, adjust the other GUI elements.

        @params int sliderValue: slider position, a quantized whole number
        """
        z_pos = self._scanner_logic._scanning_axes_ranges["z"][0] + sliderValue * self.slider_res
        # Todo: needs to be done, when possible to choose scan axes
        # self.update_roi(h=z_pos)
        self.update_input_z(z_pos)
        self._scanner_logic.move_to_position({"z": z_pos}, 'zslider')
        self._optimizer_logic.set_position('zslider', x=z_pos)

    def update_slider_x(self, x_pos):
        """ Update the x slider when a change happens.

        @param float x_pos: x position in m
        """
        self._mw.x_SliderWidget.setValue(
            (x_pos - self._scanner_logic._scanning_axes_ranges["x"][0]) / self.slider_res)

    def update_slider_y(self, y_pos):
        """ Update the y slider when a change happens.

        @param float y_pos: y position in m
        """
        self._mw.y_SliderWidget.setValue(
            (y_pos - self._scanner_logic._scanning_axes_ranges["y"][0]) / self.slider_res)

    def update_slider_z(self, z_pos):
        """ Update the z slider when a change happens.

        @param float z_pos: z position in m
        """
        self._mw.z_SliderWidget.setValue(
            (z_pos - self._scanner_logic._scanning_axes_ranges["z"][0]) / self.slider_res)

    def change_x_resolution(self):
        """ Update the x resolution in the logic according to the GUI.
        """
        self._scanner_logic.xy_resolution = self._mw.x_scan_resolution_InputWidget.value()
        # Todo: this needs to be updated when there is actually the option to choose x and y resolution independently
        self._mw.y_scan_resolution_InputWidget.setValue(self._mw.x_scan_resolution_InputWidget.value())

    def change_y_resolution(self):
        """ Update the y resolution in the logic according to the GUI.
        """
        # self._scanner_logic.y_resolution= self._mw.y_scan_resolution_InputWidget.value()
        pass

    def change_z_resolution(self):
        """ Update the z resolution in the logic according to the GUI.
        """
        pass
        # todo: this function will have to be updated once it is possible to do a scan where z is not the fast axis
        # self._scanner_logic.z_resolution = self._mw.z_scan_resolution_InputWidget.value()

    # Todo: did not do this yet
    def change_x_image_range(self):
        """ Adjust the image range for x in the logic. """
        self._scanner_logic.image_ranges["x"] = [
            self._mw.x_min_InputWidget.value(),
            self._mw.x_max_InputWidget.value()]
        self.update_scan_speed_fast_axis()
        self.update_maximal_scan_resolution_fast_axis()

    def change_y_image_range(self):
        """ Adjust the image range for y in the logic.
        """
        self._scanner_logic.image_ranges["y"] = [
            self._mw.y_min_InputWidget.value(),
            self._mw.y_max_InputWidget.value()]
        self.update_scan_speed_fast_axis()
        self.update_maximal_scan_resolution_fast_axis()

    def change_z_image_range(self):
        """ Adjust the image range for z in the logic. """
        self._scanner_logic.image_ranges["z"] = [
            self._mw.z_min_InputWidget.value(),
            self._mw.z_max_InputWidget.value()]
        self.update_scan_speed_fast_axis()
        self.update_maximal_scan_resolution_fast_axis()

    ################## Scan Line ##################
    def adjust_window(self):
        """ Fit the visible window in the scan to full view.

        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and y.
        """
        # It is extremely crucial that before adjusting the window view and
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_image()
        viewbox = self.scan_image.getViewBox()

        # Todo: this needs to be update when scanning axes can be changed
        Min_first_axis = self._scanner_logic.image_ranges["x"][0]
        Max_first_axis = self._scanner_logic.image_ranges["x"][1]
        Min_second_axis = self._scanner_logic.image_ranges["y"][0]
        Max_second_axis = self._scanner_logic.image_ranges["y"][1]

        if self.fixed_aspect_ratio:
            # Reset the limit settings so that the method 'setAspectLocked'
            # works properly. It has to be done in a manual way since no method
            # exists yet to reset the set limits:
            viewbox.state['limits']['xLimits'] = [None, None]
            viewbox.state['limits']['yLimits'] = [None, None]
            viewbox.state['limits']['xRange'] = [None, None]
            viewbox.state['limits']['yRange'] = [None, None]

            viewbox.setAspectLocked(lock=True, ratio=1.0)
            viewbox.updateViewRange()
        else:
            viewbox.setLimits(
                xMin=Min_first_axis - (Max_first_axis - Min_first_axis) * self.image_x_padding,
                xMax=Max_first_axis + (Max_first_axis - Min_first_axis) * self.image_x_padding,
                yMin=Min_second_axis - (Max_second_axis - Min_second_axis) * self.image_y_padding,
                yMax=Max_second_axis + (Max_second_axis - Min_second_axis) * self.image_y_padding)

        self.scan_image.setRect(
            QtCore.QRectF(Min_first_axis, Min_second_axis, Max_first_axis - Min_first_axis,
                          Max_second_axis - Min_second_axis))

        viewbox.updateAutoRange()
        viewbox.updateViewRange()

    def save_scan_data(self):
        """ Run the save routine from the logic to save the Scan 3D data"""
        cb_range = self.get_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.cb_manual_RadioButton.isChecked():
            low_centile = self._mw.cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._scanner_logic.save_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        # if self._mw.count
        filepath = self._save_logic.get_path_for_module(module_name='Piezo_scan_3D')
        filename = filepath + os.sep + time.strftime(
            '%Y%m%d-%H%M-%S_scan_3D_pixel_image')
        if self._sd.save_purePNG_checkBox.isChecked():
            self.scan_image.save(filename + '_raw.png')

    ################## Fast Axis Scan Parameters ##################
    def convert_pos_to_voltage(self, pos):
        """Converts a position value to a voltage value
        @return float: the calculated voltage
        """
        # todo: this only works for the fast axis
        v_range = self._max_voltage_range_fast_axis
        pos_range = self._max_position_range_fast_axis
        voltage = (v_range[1] - v_range[0]) / (pos_range[1] - pos_range[0]) * (
                pos - pos_range[0]) + v_range[0]

        return voltage

    def update_scan_speed_fast_axis(self):
        """ Updates the fast scan axis scan speed,
        eg. if the scan freq of the fast axis or the fast axis range was changed
        """
        # Todo: if axes are variable this needs to be update
        image_start_pos = self._scanner_logic.image_ranges["z"][0]
        image_end_pos = self._scanner_logic.image_ranges["z"][1]
        scan_speed_m = np.abs(image_end_pos - image_start_pos) * self._scanner_logic.scan_freq_fast_axis
        self._mw.scan_speed_m_fast_axis_doubleSpinBox.setValue(scan_speed_m)
        image_start_v = self.convert_pos_to_voltage(image_start_pos)
        image_end_v = self.convert_pos_to_voltage(image_end_pos)
        scan_speed_v = np.abs(image_end_v - image_start_v) * self._scanner_logic.scan_freq_fast_axis
        self._mw.scan_speed_V_fast_axis_doubleSpinBox.setValue(scan_speed_v)

        return

    def scan_freq_fast_axis_changed(self):
        """ Update the scan freq of the fast scan axis in the logic according to the GUI.
        """
        freq = self._mw.scan_freq_fast_axis_doubleSpinBox.value()
        self._scanner_logic.scan_freq_fast_axis = freq
        self.update_scan_speed_fast_axis()

    def scan_resolution_fast_axis_changed(self):
        """ Update the scan resolution of the fast axis in the logic according to the GUI.
        """
        resolution = self._mw.scan_resolution_fast_axis_spinBox.value()
        maximal_scan_resolution = self._mw.maximal_scan_resolution_fast_axis_doubleSpinBox.value()
        if resolution < maximal_scan_resolution:
            self.log.warn(
                "Set scan resolution %s exceeds maximum scan resolution %s of scanning device! "
                "Scan resolution was set to maximum value.",
                resolution, maximal_scan_resolution)
            self._scanner_logic.scan_resolution_fast_axis = maximal_scan_resolution
            self._mw.scan_resolution_fast_axis_spinBox.setValue(maximal_scan_resolution)
            self._mw.scan_resolution_fast_axis_V_doubleSpinBox.setValue(
                abs(self._max_voltage_range_fast_axis[1] - self._max_voltage_range_fast_axis[0]) /
                abs(self._max_position_range_fast_axis[1] - self._max_position_range_fast_axis[0])
                * maximal_scan_resolution)
        else:
            self._scanner_logic.scan_resolution_fast_axis = resolution
            self._mw.scan_resolution_fast_axis_V_doubleSpinBox.setValue(
                abs(self._max_voltage_range_fast_axis[1] - self._max_voltage_range_fast_axis[0]) /
                abs(self._max_position_range_fast_axis[1] - self._max_position_range_fast_axis[0]) * resolution)
        self._mw.z_scan_resolution_InputWidget.setValue(self._scanner_logic.scan_resolution_fast_axis)

    def update_maximal_scan_resolution_fast_axis(self):
        """ Update fast axis scan resolution to the maximally possible scan resolution
        """
        if self._mw.max_scan_resolution_fast_axis_checkBox.isChecked():
            self._scanner_logic._use_maximal_resolution()
            maximal_scan_resolution = self._scanner_logic.scan_resolution_fast_axis
            self._mw.maximal_scan_resolution_fast_axis_doubleSpinBox.setValue(maximal_scan_resolution)
        return

    def max_scan_resolution_fast_axis_clicked(self):
        if self._mw.max_scan_resolution_fast_axis_checkBox.isChecked():
            self._scanner_logic._use_maximal_resolution_fast_axis = True
            self.update_maximal_scan_resolution_fast_axis()
            self._mw.scan_resolution_fast_axis_spinBox.setEnabled(False)
        else:
            self._scanner_logic._use_maximal_resolution_fast_axis = False
            self._mw.scan_resolution_fast_axis_spinBox.setEnabled(True)
            self.scan_resolution_fast_axis_changed()

    def smoothing_steps_fast_axis_changed(self):
        smoothing_steps = self._mw.smoothing_steps_fast_axis_spinBox.value()
        self._scanner_logic._fast_axis_smoothing_steps = smoothing_steps

    def smoothing_fast_axis_clicked(self):
        """

        """
        if self._mw.smooth_fast_axis_checkBox.isChecked():
            self._scanner_logic.smoothing = True
            self._mw.smoothing_steps_fast_axis_spinBox.setEnabled(True)

        else:
            self._scanner_logic.smoothing = False
            self._mw.smoothing_steps_fast_axis_spinBox.setEnabled(False)

    ################## Settings ##################
    def switch_hardware(self):
        """ Switches the hardware state. """
        self._scanner_logic.switch_hardware(to_on=False)

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

    def logic_started_scanning(self, tag):
        """ Disable icons if a scan was started.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_step_actions()

    def logic_continued_scanning(self, tag):
        """ Disable icons if a scan was continued.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_step_actions()

    ################## ROI ######################
    def roi_bounds_check(self, pos):
        """ Check if the focus cursor is oputside the allowed range after drag
            and set its position to the limit
        """
        new_h_pos = np.clip(pos[0], *self._scanner_logic.image_ranges["x"])
        new_v_pos = np.clip(pos[1], *self._scanner_logic.image_ranges["y"])
        in_bounds = new_h_pos == pos[0] and new_v_pos == pos[1]
        return in_bounds, (new_h_pos, new_v_pos)

    def update_from_roi(self, pos):
        """The user manually moved the ROI (region of interest), adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        # Check if ROI in image range and update if not
        pos = (pos.x(), pos.y())
        in_range, pos = self.roi_bounds_check(pos)
        if not in_range:
            self._mw.ViewWidget.set_crosshair_pos(pos)

        # Find position of ROI
        h_step_pos, v_step_pos = pos

        # Todo: needs to be updated when scan axes are flexible
        # Update positions feedback position display
        if self._scanner_logic.map_scan_positions and not self._currently_scanning:
            other_channels = 3 + self._mw.count_channel_ComboBox.count()
            # Todo: The position needs to be translate to ann index via the image 2D positions of the scanner.
            # After this this function can be used
            # h_pos = self._scanner_logic.image_2D[
            #    v_step_pos, h_step_pos, other_channels + 0]
            # v_pos = self._scanner_logic.image_2D[
            #    v_step_pos, h_step_pos, other_channels + 1]
            # if self._x_closed_loop:
            #    # This is a safety precaution
            #    self._feedback_axis["x"].setValue(self._mw.x_position_doubleSpinBox.value())
            #    self._feedback_axis["x"].setValue(h_pos * 1e-3)

            # if self._y_closed_loop:
            #    self._feedback_axis["y"].setValue(self._mw.y_position_doubleSpinBox.value())
            #    self._feedback_axis["y"].setValue(v_pos * 1e-3)

        # Update Piezo positions
        self.update_slider_x(h_step_pos)
        self.update_slider_y(v_step_pos)

        self.update_input_x(h_step_pos)
        self.update_input_y(v_step_pos)

        self._scanner_logic.move_to_position({"x": h_step_pos, "y": v_step_pos}, 'roi')
        self._optimizer_logic.set_position('roixy', x=h_step_pos, y=v_step_pos)

    def update_roi(self, h=None, v=None):
        """ Adjust the ROI position if the value has changed.

        @param float h: real value of the current horizontal position
        @param float v: real value of the current vertical position
        """
        if h is None:
            h = self._mw.ViewWidget.crosshair_position[0]
        if v is None:
            v = self._mw.ViewWidget.crosshair_position[1]
        self._mw.ViewWidget.set_crosshair_pos((h, v))

    def update_roi_size(self):
        """ Update the cursor size showing the optimizer scan area for the image.
        """
        if self.adjust_cursor_roi:
            self._mw.ViewWidget.set_crosshair_min_size_factor(0.02)
        else:
            self._mw.ViewWidget.set_crosshair_min_size_factor(0.1)

        newsize = self._optimizer_logic.refocus_XY_size
        self._mw.ViewWidget.set_crosshair_size([newsize, newsize])
        return

    def update_crosshair_position_from_logic(self, tag):
        """ Update the GUI position of the crosshair from the logic.

        @param str tag: tag indicating the source of the update

        Ignore the update when it is tagged with one of the tags that the
        confocal gui emits, as the GUI elements were already adjusted.
        """
        if 'roi' not in tag and 'slider' not in tag and 'key' not in tag and 'input' not in tag:
            position = self._scanner_logic._current_position.copy()
            x_pos = position["x"]
            y_pos = position["y"]
            z_pos = position["z"]

            # image
            self._mw.ViewWidget.set_crosshair_pos([x_pos, y_pos])

            self.update_slider_x(x_pos)
            self.update_slider_y(y_pos)
            self.update_slider_z(z_pos)

            self.update_input_x(x_pos)
            self.update_input_y(y_pos)
            self.update_input_z(z_pos)
