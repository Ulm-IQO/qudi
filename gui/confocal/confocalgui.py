# -*- coding: utf-8 -*-

"""
This file contains the Qudi GUI for general Confocal control.

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

import numpy as np
import os
import pyqtgraph as pg
import time

from core.module import Connector, ConfigOption, StatusVar
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitParametersWidget
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

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

    def setSize(self,size, update=True,finish=True):
        """
        Sets the size of the ROI
        @param bool update: whether to update the display for this call of setPos
        @param bool finish: whether to emit sigRegionChangeFinished
        """
        super().setSize(size,update=update,finish=finish)

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


class ConfocalMainWindow(QtWidgets.QMainWindow):

    """ Create the Mainwindow based on the corresponding *.ui file. """

    sigPressKeyBoard = QtCore.Signal(QtCore.QEvent)
    sigDoubleClick = QtCore.Signal()

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_confocalgui.ui')
        self._doubleclicked = False

        # Load it
        super(ConfocalMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

    def keyPressEvent(self, event):
        """Pass the keyboard press event from the main window further. """
        self.sigPressKeyBoard.emit(event)

    def mouseDoubleClickEvent(self, event):
        self._doubleclicked = True
        self.sigDoubleClick.emit()


class ConfocalSettingDialog(QtWidgets.QDialog):

    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_cf_settings.ui')

        # Load it
        super(ConfocalSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class OptimizerSettingDialog(QtWidgets.QDialog):
    """ User configurable settings for the optimizer embedded in cofocal gui"""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_optim_settings.ui')

        # Load it
        super(OptimizerSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class ConfocalGui(GUIBase):

    """ Main Confocal Class for xy and depth scans.
    """
    _modclass = 'ConfocalGui'
    _modtype = 'gui'

    # declare connectors
    confocallogic1 = Connector(interface='ConfocalLogic')
    savelogic = Connector(interface='SaveLogic')
    optimizerlogic1 = Connector(interface='OptimizerLogic')

    # config options for gui
    fixed_aspect_ratio_xy = ConfigOption('fixed_aspect_ratio_xy', True)
    fixed_aspect_ratio_depth = ConfigOption('fixed_aspect_ratio_depth', True)
    image_x_padding = ConfigOption('image_x_padding', 0.02)
    image_y_padding = ConfigOption('image_y_padding', 0.02)
    image_z_padding = ConfigOption('image_z_padding', 0.02)

    # status var
    adjust_cursor_roi = StatusVar(default=True)
    slider_small_step = StatusVar(default=10e-9)    # initial value in meter
    slider_big_step = StatusVar(default=100e-9)     # initial value in meter

    # signals
    sigStartOptimizer = QtCore.Signal(list, str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """

        # Getting an access to all connectors:
        self._scanning_logic = self.get_connector('confocallogic1')
        self._save_logic = self.get_connector('savelogic')
        self._optimizer_logic = self.get_connector('optimizerlogic1')

        self._hardware_state = True

        self.initMainUI()      # initialize the main GUI
        self.initSettingsUI()  # initialize the settings GUI
        self.initOptimizerSettingsUI()  # initialize the optimizer settings GUI

    def initMainUI(self):
        """ Definition, configuration and initialisation of the confocal GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        self._mw = ConfocalMainWindow()

        ###################################################################
        #               Configuring the dock widgets                      #
        ###################################################################
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # always use first channel on startup, can be changed afterwards
        self.xy_channel = 0
        self.depth_channel = 0
        self.opt_channel = 0

        # Get the image for the display from the logic
        raw_data_xy = self._scanning_logic.xy_image[:, :, 3 + self.xy_channel]
        raw_data_depth = self._scanning_logic.depth_image[:, :, 3 + self.depth_channel]

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(raw_data_xy) / 2
        ini_pos_y_crosshair = len(raw_data_xy) / 2
        ini_pos_z_crosshair = len(raw_data_depth) / 2


        # Load the images for xy and depth in the display:
        self.xy_image = pg.ImageItem(image=raw_data_xy, axisOrder='row-major')
        self.depth_image = pg.ImageItem(image=raw_data_depth, axisOrder='row-major')

        # Hide tilt correction window
        self._mw.tilt_correction_dockWidget.hide()

        # Hide scan line display
        self._mw.scanLineDockWidget.hide()

        # set up scan line plot
        sc = self._scanning_logic._scan_counter
        sc = sc - 1 if sc >= 1 else sc
        if self._scanning_logic._zscan:
            data = self._scanning_logic.depth_image[sc, :, 0:4:3]
        else:
            data = self._scanning_logic.xy_image[sc, :, 0:4:3]

        self.scan_line_plot = pg.PlotDataItem(data, pen=pg.mkPen(palette.c1))
        self._mw.scanLineGraphicsView.addItem(self.scan_line_plot)

        ###################################################################
        #               Configuration of the optimizer tab                #
        ###################################################################
        # Load the image for the optimizer tab
        self.xy_refocus_image = pg.ImageItem(
            image=self._optimizer_logic.xy_refocus_image[:, :, 3 + self.opt_channel],
            axisOrder='row-major')
        self.xy_refocus_image.setRect(
            QtCore.QRectF(
                self._optimizer_logic._initial_pos_x - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic._initial_pos_y - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size
            )
        )
        self.depth_refocus_image = pg.PlotDataItem(
            x=self._optimizer_logic._zimage_Z_values,
            y=self._optimizer_logic.z_refocus_line[:, self._optimizer_logic.opt_channel],
            pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
            symbol='o',
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=7
        )
        self.depth_refocus_fit_image = pg.PlotDataItem(
            x=self._optimizer_logic._fit_zimage_Z_values,
            y=self._optimizer_logic.z_fit_data,
            pen=pg.mkPen(palette.c2)
        )

        # Add the display item to the xy and depth VieWidget, which was defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget_2.addItem(self.xy_refocus_image)
        self._mw.depth_refocus_ViewWidget_2.addItem(self.depth_refocus_image)

        # Labelling axes
        self._mw.xy_refocus_ViewWidget_2.setLabel('bottom', 'X position', units='m')
        self._mw.xy_refocus_ViewWidget_2.setLabel('left', 'Y position', units='m')

        self._mw.depth_refocus_ViewWidget_2.addItem(self.depth_refocus_fit_image)

        self._mw.depth_refocus_ViewWidget_2.setLabel('bottom', 'Z position', units='m')
        self._mw.depth_refocus_ViewWidget_2.setLabel('left', 'Fluorescence', units='c/s')

        # Add crosshair to the xy refocus scan
        self.vLine = pg.InfiniteLine(
            pen=QtGui.QPen(
                palette.green,
                self._optimizer_logic.refocus_XY_size / 50),
            pos=50,
            angle=90,
            movable=False)
        self.hLine = pg.InfiniteLine(
            pen=QtGui.QPen(
                palette.green,
                self._optimizer_logic.refocus_XY_size / 50),
            pos=50,
            angle=0,
            movable=False)
        self._mw.xy_refocus_ViewWidget_2.addItem(self.vLine, ignoreBounds=True)
        self._mw.xy_refocus_ViewWidget_2.addItem(self.hLine, ignoreBounds=True)

        # Set the state button as ready button as default setting.
        self._mw.action_stop_scanning.setEnabled(False)
        self._mw.action_scan_xy_resume.setEnabled(False)
        self._mw.action_scan_depth_resume.setEnabled(False)

        # Add the display item to the xy and depth ViewWidget, which was defined
        # in the UI file:
        self._mw.xy_ViewWidget.addItem(self.xy_image)
        self._mw.depth_ViewWidget.addItem(self.depth_image)

        # Label the axes:
        self._mw.xy_ViewWidget.setLabel('bottom', 'X position', units='m')
        self._mw.xy_ViewWidget.setLabel('left', 'Y position', units='m')
        self._mw.depth_ViewWidget.setLabel('bottom', 'X position', units='m')
        self._mw.depth_ViewWidget.setLabel('left', 'Z position', units='m')

        # Create Region of Interest for xy image and add to xy Image Widget:
        self.roi_xy = CrossROI(
            [
                ini_pos_x_crosshair - self._optimizer_logic.refocus_XY_size / 2,
                ini_pos_y_crosshair - self._optimizer_logic.refocus_XY_size / 2
            ],
            [self._optimizer_logic.refocus_XY_size, self._optimizer_logic.refocus_XY_size],
            pen={'color': "F0F", 'width': 1},
            removable=True
        )

        self._mw.xy_ViewWidget.addItem(self.roi_xy)

        # create horizontal and vertical line as a crosshair in xy image:
        self.hline_xy = CrossLine(pos=self.roi_xy.pos() + self.roi_xy.size() * 0.5,
                                  angle=0, pen={'color': palette.green, 'width': 1})
        self.vline_xy = CrossLine(pos=self.roi_xy.pos() + self.roi_xy.size() * 0.5,
                                  angle=90, pen={'color': palette.green, 'width': 1})

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_xy.sigRegionChanged.connect(self.hline_xy.adjust)
        self.roi_xy.sigRegionChanged.connect(self.vline_xy.adjust)
        self.roi_xy.sigUserRegionUpdate.connect(self.update_from_roi_xy)
        self.roi_xy.sigRegionChangeFinished.connect(self.roi_xy_bounds_check)

        # add the configured crosshair to the xy Widget
        self._mw.xy_ViewWidget.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.addItem(self.vline_xy)

        # Set up and connect xy channel combobox
        scan_channels = self._scanning_logic.get_scanner_count_channels()
        for n, ch in enumerate(scan_channels):
            self._mw.xy_channel_ComboBox.addItem(str(ch), n)

        self._mw.xy_channel_ComboBox.activated.connect(self.update_xy_channel)

        # Create Region of Interest for depth image and add to xy Image Widget:
        self.roi_depth = CrossROI(
            [
                ini_pos_x_crosshair - self._optimizer_logic.refocus_XY_size/2,
                ini_pos_z_crosshair - self._optimizer_logic.refocus_Z_size/2
            ],
            [self._optimizer_logic.refocus_XY_size,self._optimizer_logic.refocus_Z_size],
            pen={'color': "F0F", 'width': 1},
            removable=True
        )
        self._mw.depth_ViewWidget.addItem(self.roi_depth)

        # create horizontal and vertical line as a crosshair in depth image:
        self.hline_depth = CrossLine(
            pos=self.roi_depth.pos() + self.roi_depth.size() * 0.5,
            angle=0,
            pen={'color': palette.green, 'width': 1}
        )
        self.vline_depth = CrossLine(
            pos=self.roi_depth.pos() + self.roi_depth.size() * 0.5,
            angle=90,
            pen={'color': palette.green, 'width': 1}
        )
        # connect the change of a region with the adjustment of the crosshair:
        self.roi_depth.sigRegionChanged.connect(self.hline_depth.adjust)
        self.roi_depth.sigRegionChanged.connect(self.vline_depth.adjust)
        self.roi_depth.sigUserRegionUpdate.connect(self.update_from_roi_depth)
        self.roi_depth.sigRegionChangeFinished.connect(self.roi_depth_bounds_check)

        # add the configured crosshair to the depth Widget:
        self._mw.depth_ViewWidget.addItem(self.hline_depth)
        self._mw.depth_ViewWidget.addItem(self.vline_depth)

        # Set up and connect depth channel combobox
        scan_channels = self._scanning_logic.get_scanner_count_channels()
        for n, ch in enumerate(scan_channels):
            self._mw.depth_channel_ComboBox.addItem(str(ch), n)

        self._mw.depth_channel_ComboBox.activated.connect(self.update_depth_channel)

        # Setup the Sliders:
        # Calculate the needed Range for the sliders. The image ranges comming
        # from the Logic module must be in meters.
        # 1 nanometer resolution per one change, units are meters
        self.slider_res = 1e-9

        # How many points are needed for that kind of resolution:
        num_of_points_x = (self._scanning_logic.x_range[1] - self._scanning_logic.x_range[0]) / self.slider_res
        num_of_points_y = (self._scanning_logic.y_range[1] - self._scanning_logic.y_range[0]) / self.slider_res
        num_of_points_z = (self._scanning_logic.z_range[1] - self._scanning_logic.z_range[0]) / self.slider_res

        # Set a Range for the sliders:
        self._mw.x_SliderWidget.setRange(0, num_of_points_x)
        self._mw.y_SliderWidget.setRange(0, num_of_points_y)
        self._mw.z_SliderWidget.setRange(0, num_of_points_z)

        # Just to be sure, set also the possible maximal values for the spin
        # boxes of the current values:
        self._mw.x_current_InputWidget.setRange(self._scanning_logic.x_range[0],
                                                self._scanning_logic.x_range[1])
        self._mw.y_current_InputWidget.setRange(self._scanning_logic.y_range[0],
                                                self._scanning_logic.y_range[1])
        self._mw.z_current_InputWidget.setRange(self._scanning_logic.z_range[0],
                                                self._scanning_logic.z_range[1])

        # set the maximal ranges for the imagerange from the logic:
        self._mw.x_min_InputWidget.setRange(self._scanning_logic.x_range[0],
                                            self._scanning_logic.x_range[1])
        self._mw.x_max_InputWidget.setRange(self._scanning_logic.x_range[0],
                                            self._scanning_logic.x_range[1])
        self._mw.y_min_InputWidget.setRange(self._scanning_logic.y_range[0],
                                            self._scanning_logic.y_range[1])
        self._mw.y_max_InputWidget.setRange(self._scanning_logic.y_range[0],
                                            self._scanning_logic.y_range[1])
        self._mw.z_min_InputWidget.setRange(self._scanning_logic.z_range[0],
                                            self._scanning_logic.z_range[1])
        self._mw.z_max_InputWidget.setRange(self._scanning_logic.z_range[0],
                                            self._scanning_logic.z_range[1])

        # Predefine the maximal and minimal image range as the default values
        # for the display of the range:
        self._mw.x_min_InputWidget.setValue(self._scanning_logic.get_image_axis_range('x')[0])
        self._mw.x_max_InputWidget.setValue(self._scanning_logic.get_image_axis_range('x')[1])
        self._mw.y_min_InputWidget.setValue(self._scanning_logic.get_image_axis_range('y')[0])
        self._mw.y_max_InputWidget.setValue(self._scanning_logic.get_image_axis_range('y')[1])
        self._mw.z_min_InputWidget.setValue(self._scanning_logic.get_image_axis_range('z')[0])
        self._mw.z_max_InputWidget.setValue(self._scanning_logic.get_image_axis_range('z')[1])

        # Handle slider movements by user:
        self._mw.x_SliderWidget.sliderMoved.connect(self.update_from_slider_x)
        self._mw.y_SliderWidget.sliderMoved.connect(self.update_from_slider_y)
        self._mw.z_SliderWidget.sliderMoved.connect(self.update_from_slider_z)

        # Take the default values from logic:
        self._mw.xy_res_InputWidget.setValue(self._scanning_logic.xy_resolution)
        self._mw.z_res_InputWidget.setValue(self._scanning_logic.z_resolution)

        # Update the inputed/displayed numbers if the cursor has left the field:
        self._mw.x_current_InputWidget.editingFinished.connect(self.update_from_input_x)
        self._mw.y_current_InputWidget.editingFinished.connect(self.update_from_input_y)
        self._mw.z_current_InputWidget.editingFinished.connect(self.update_from_input_z)

        self._mw.xy_res_InputWidget.editingFinished.connect(self.change_xy_resolution)
        self._mw.z_res_InputWidget.editingFinished.connect(self.change_z_resolution)

        self._mw.x_min_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.editingFinished.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.editingFinished.connect(self.change_z_image_range)

        # Connect the change of the viewed area to an adjustment of the ROI:
        self.adjust_cursor_roi = True
        self.xy_image.getViewBox().sigRangeChanged.connect(self.update_roi_xy_size)
        self.depth_image.getViewBox().sigRangeChanged.connect(self.update_roi_depth_size)

        #################################################################
        #                           Actions                             #
        #################################################################
        # Connect the scan actions to the events if they are clicked. Connect
        # also the adjustment of the displayed windows.
        self._mw.action_stop_scanning.triggered.connect(self.ready_clicked)

        self._scan_xy_start_proxy = pg.SignalProxy(
            self._mw.action_scan_xy_start.triggered,
            delay=0.1,
            slot=self.xy_scan_clicked
            )
        self._scan_xy_resume_proxy =  pg.SignalProxy(
            self._mw.action_scan_xy_resume.triggered,
            delay=0.1,
            slot=self.continue_xy_scan_clicked
            )
        self._scan_depth_start_proxy = pg.SignalProxy(
            self._mw.action_scan_depth_start.triggered,
            delay=0.1,
            slot=self.depth_scan_clicked
            )
        self._scan_depth_resume_proxy = pg.SignalProxy(
            self._mw.action_scan_depth_resume.triggered,
            delay=0.1,
            slot=self.continue_depth_scan_clicked
            )
        self._optimize_position_proxy = pg.SignalProxy(
            self._mw.action_optimize_position.triggered,
            delay=0.1,
            slot=self.refocus_clicked
            )

        # history actions
        self._mw.actionForward.triggered.connect(self._scanning_logic.history_forward)
        self._mw.actionBack.triggered.connect(self._scanning_logic.history_back)
        self._scanning_logic.signal_history_event.connect(lambda: self.set_history_actions(True))
        self._scanning_logic.signal_history_event.connect(self.update_xy_cb_range)
        self._scanning_logic.signal_history_event.connect(self.update_depth_cb_range)
        self._scanning_logic.signal_history_event.connect(self._mw.xy_ViewWidget.autoRange)
        self._scanning_logic.signal_history_event.connect(self._mw.depth_ViewWidget.autoRange)
        self._scanning_logic.signal_history_event.connect(self.reset_xy_imagerange)
        self._scanning_logic.signal_history_event.connect(self.reset_depth_imagerange)

        # Get initial tilt correction values
        self._mw.action_TiltCorrection.setChecked(
            self._scanning_logic._scanning_device.tiltcorrection)

        self._mw.tilt_01_x_pos_doubleSpinBox.setValue(self._scanning_logic.point1[0])
        self._mw.tilt_01_y_pos_doubleSpinBox.setValue(self._scanning_logic.point1[1])
        self._mw.tilt_01_z_pos_doubleSpinBox.setValue(self._scanning_logic.point1[2])

        self._mw.tilt_02_x_pos_doubleSpinBox.setValue(self._scanning_logic.point2[0])
        self._mw.tilt_02_y_pos_doubleSpinBox.setValue(self._scanning_logic.point2[1])
        self._mw.tilt_02_z_pos_doubleSpinBox.setValue(self._scanning_logic.point2[2])

        self._mw.tilt_03_x_pos_doubleSpinBox.setValue(self._scanning_logic.point3[0])
        self._mw.tilt_03_y_pos_doubleSpinBox.setValue(self._scanning_logic.point3[1])
        self._mw.tilt_03_z_pos_doubleSpinBox.setValue(self._scanning_logic.point3[2])

        # Connect tilt correction buttons
        self._mw.action_TiltCorrection.triggered.connect(self._scanning_logic.set_tilt_correction)
        self._mw.tilt_set_01_pushButton.clicked.connect(self._scanning_logic.set_tilt_point1)
        self._mw.tilt_set_02_pushButton.clicked.connect(self._scanning_logic.set_tilt_point2)
        self._mw.tilt_set_03_pushButton.clicked.connect(self._scanning_logic.set_tilt_point3)
        self._mw.calc_tilt_pushButton.clicked.connect(self._scanning_logic.calc_tilt_correction)
        self._scanning_logic.signal_tilt_correction_update.connect(self.update_tilt_correction)
        self._scanning_logic.signal_tilt_correction_active.connect(
            self._mw.action_TiltCorrection.setChecked)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)
        self._mw.optimizer_only_view_Action.triggered.connect(self.small_optimizer_view)
        self._mw.actionAutoRange_xy.triggered.connect(self._mw.xy_ViewWidget.autoRange)
        self._mw.actionAutoRange_z.triggered.connect(self._mw.depth_ViewWidget.autoRange)
        # Connect the buttons and inputs for the xy colorbar
        self._mw.xy_cb_manual_RadioButton.clicked.connect(self.update_xy_cb_range)
        self._mw.xy_cb_centiles_RadioButton.clicked.connect(self.update_xy_cb_range)

        self._mw.xy_cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)
        self._mw.xy_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)

        # Connect the buttons and inputs for the depth colorbars
        # RadioButtons in Main tab
        self._mw.depth_cb_manual_RadioButton.clicked.connect(self.update_depth_cb_range)
        self._mw.depth_cb_centiles_RadioButton.clicked.connect(self.update_depth_cb_range)

        # input edits in Main tab
        self._mw.depth_cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_depth_cb_manual)
        self._mw.depth_cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_depth_cb_manual)
        self._mw.depth_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_depth_cb_centiles)
        self._mw.depth_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_depth_cb_centiles)

        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture:
        self._scanning_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._scanning_logic.signal_xy_image_updated.connect(self.refresh_scan_line)
        self._scanning_logic.signal_depth_image_updated.connect(self.refresh_scan_line)
        self._scanning_logic.signal_depth_image_updated.connect(self.refresh_depth_image)
        self._optimizer_logic.sigImageUpdated.connect(self.refresh_refocus_image)
        self._scanning_logic.sigImageXYInitialized.connect(self.adjust_xy_window)
        self._scanning_logic.sigImageDepthInitialized.connect(self.adjust_depth_window)

        # Connect the signal from the logic with an update of the cursor position
        self._scanning_logic.signal_change_position.connect(self.update_crosshair_position_from_logic)

        # Connect other signals from the logic with an update of the gui

        self._scanning_logic.signal_start_scanning.connect(self.logic_started_scanning)
        self._scanning_logic.signal_continue_scanning.connect(self.logic_continued_scanning)
        self._optimizer_logic.sigRefocusStarted.connect(self.logic_started_refocus)
        # self._scanning_logic.signal_stop_scanning.connect()

        self._scanning_logic.image_ranges_changed_Signal.connect(self.logic_updated_scan_range)
        self._scanning_logic.scan_resolution_changed_Signal.connect(self.logic_updated_resolution)

        # Connect the tracker
        self.sigStartOptimizer.connect(self._optimizer_logic.start_refocus)
        self._optimizer_logic.sigRefocusFinished.connect(self._refocus_finished_wrapper)
        self._optimizer_logic.sigRefocusXySizeChanged.connect(self.update_roi_xy_size)
        self._optimizer_logic.sigRefocusZSizeChanged.connect(self.update_roi_depth_size)

        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._mw.action_optimizer_settings.triggered.connect(self.menu_optimizer_settings)
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan_data)
        self._mw.actionSave_Depth_Scan.triggered.connect(self.save_depth_scan_data)

        # Configure and connect the zoom actions with the desired buttons and
        # functions if
        self._mw.action_full_range_xy.triggered.connect(self.set_full_scan_range_xy)
        self._mw.action_full_range_z.triggered.connect(self.set_full_scan_range_z)

        self._mw.action_zoom.toggled.connect(self.zoom_clicked)
        self._mw.sigDoubleClick.connect(self.activate_zoom_double_click)
        self._mw.xy_ViewWidget.sigMouseClick.connect(self.xy_scan_start_zoom_point)
        self._mw.xy_ViewWidget.sigMouseReleased.connect(self.xy_scan_end_zoom_point)
        self._mw.depth_ViewWidget.sigMouseClick.connect(self.depth_scan_start_zoom_point)
        self._mw.depth_ViewWidget.sigMouseReleased.connect(self.depth_scan_end_zoom_point)



        ###################################################################
        #               Icons for the scan actions                        #
        ###################################################################

        self._scan_xy_single_icon = QtGui.QIcon()
        self._scan_xy_single_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_depth_single_icon = QtGui.QIcon()
        self._scan_depth_single_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-depth-start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_xy_loop_icon = QtGui.QIcon()
        self._scan_xy_loop_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-loop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_depth_loop_icon = QtGui.QIcon()
        self._scan_depth_loop_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-depth-loop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        #################################################################
        #           Connect the colorbar and their actions              #
        #################################################################
        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleInferno()

        self.xy_image.setLookupTable(self.my_colors.lut)
        self.depth_image.setLookupTable(self.my_colors.lut)
        self.xy_refocus_image.setLookupTable(self.my_colors.lut)

        # Create colorbars and add them at the desired place in the GUI. Add
        # also units to the colorbar.

        self.xy_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self.depth_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xy_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.xy_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        self._mw.depth_cb_ViewWidget.addItem(self.depth_cb)
        self._mw.depth_cb_ViewWidget.hideAxis('bottom')
        self._mw.depth_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.depth_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        self._mw.sigPressKeyBoard.connect(self.keyPressEvent)

        # Now that the ROI for xy and depth is connected to events, update the
        # default position and initialize the position of the crosshair and
        # all other components:
        self.enable_scan_actions()
        self.update_crosshair_position_from_logic('init')
        self.adjust_xy_window()
        self.adjust_depth_window()

        self.show()

    def initSettingsUI(self):
        """ Definition, configuration and initialisation of the settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._sd = ConfocalSettingDialog()
        # Connect the action of the settings window with the code:
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self._sd.hardware_switch.clicked.connect(self.switch_hardware)

        # write the configuration to the settings window of the GUI.
        self.keep_former_settings()

    def initOptimizerSettingsUI(self):
        """ Definition, configuration and initialisation of the optimizer settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._osd = OptimizerSettingDialog()
        # Connect the action of the settings window with the code:
        self._osd.accepted.connect(self.update_optimizer_settings)
        self._osd.rejected.connect(self.keep_former_optimizer_settings)
        self._osd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_optimizer_settings)

        # Set up and connect xy channel combobox
        scan_channels = self._optimizer_logic.get_scanner_count_channels()
        for n, ch in enumerate(scan_channels):
            self._osd.opt_channel_ComboBox.addItem(str(ch), n)

        # Generation of the fit params tab ##################
        self._osd.fit_tab = FitParametersWidget(self._optimizer_logic.z_params)
        self._osd.settings_tabWidget.addTab(self._osd.fit_tab, "Fit Params")

        # write the configuration to the settings window of the GUI.
        self.keep_former_optimizer_settings()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def show(self):
        """Make main window visible and put it above all other windows. """
        # Show the Main Confocal GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def keyPressEvent(self, event):
        """ Handles the passed keyboard events from the main window.

        @param object event: qtpy.QtCore.QEvent object.
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        position = self._scanning_logic.get_position()   # in meters
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

    def get_xy_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.xy_cb_manual_RadioButton.isChecked() or np.max(self.xy_image.image) == 0.0:
            cb_min = self._mw.xy_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.xy_cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            xy_image_nonzero = self.xy_image.image[np.nonzero(self.xy_image.image)]

            # Read centile range
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(xy_image_nonzero, low_centile)
            cb_max = np.percentile(xy_image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def get_depth_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.depth_cb_manual_RadioButton.isChecked() or np.max(self.depth_image.image) == 0.0:
            cb_min = self._mw.depth_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.depth_cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            depth_image_nonzero = self.depth_image.image[np.nonzero(self.depth_image.image)]

            # Read centile range
            low_centile = self._mw.depth_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.depth_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(depth_image_nonzero, low_centile)
            cb_max = np.percentile(depth_image_nonzero, high_centile)

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

    def refresh_depth_colorbar(self):
        """ Adjust the depth colorbar.

        Calls the refresh method from colorbar, which takes either the lowest
        and higherst value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """
        cb_range = self.get_depth_cb_range()
        self.depth_cb.refresh_colorbar(cb_range[0], cb_range[1])

    def disable_scan_actions(self):
        """ Disables the buttons for scanning.
        """
        # Enable the stop scanning button
        self._mw.action_stop_scanning.setEnabled(True)

        # Disable the start scan buttons
        self._mw.action_scan_xy_start.setEnabled(False)
        self._mw.action_scan_depth_start.setEnabled(False)

        self._mw.action_scan_xy_resume.setEnabled(False)
        self._mw.action_scan_depth_resume.setEnabled(False)

        self._mw.action_optimize_position.setEnabled(False)

        self._mw.x_min_InputWidget.setEnabled(False)
        self._mw.x_max_InputWidget.setEnabled(False)
        self._mw.y_min_InputWidget.setEnabled(False)
        self._mw.y_max_InputWidget.setEnabled(False)
        self._mw.z_min_InputWidget.setEnabled(False)
        self._mw.z_max_InputWidget.setEnabled(False)

        self._mw.xy_res_InputWidget.setEnabled(False)
        self._mw.z_res_InputWidget.setEnabled(False)

        # Set the zoom button if it was pressed to unpressed and disable it
        self._mw.action_zoom.setChecked(False)
        self._mw.action_zoom.setEnabled(False)

        self.set_history_actions(False)

    def enable_scan_actions(self):
        """ Reset the scan action buttons to the default active
        state when the system is idle.
        """
        # Disable the stop scanning button
        self._mw.action_stop_scanning.setEnabled(False)

        # Enable the scan buttons
        self._mw.action_scan_xy_start.setEnabled(True)
        self._mw.action_scan_depth_start.setEnabled(True)
#        self._mw.actionRotated_depth_scan.setEnabled(True)

        self._mw.action_optimize_position.setEnabled(True)

        self._mw.x_min_InputWidget.setEnabled(True)
        self._mw.x_max_InputWidget.setEnabled(True)
        self._mw.y_min_InputWidget.setEnabled(True)
        self._mw.y_max_InputWidget.setEnabled(True)
        self._mw.z_min_InputWidget.setEnabled(True)
        self._mw.z_max_InputWidget.setEnabled(True)

        self._mw.xy_res_InputWidget.setEnabled(True)
        self._mw.z_res_InputWidget.setEnabled(True)

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

    def _refocus_finished_wrapper(self, caller_tag, optimal_pos):
        """ Re-enable the scan buttons in the GUI.
          @param str caller_tag: tag showing the origin of the action
          @param array optimal_pos: optimal focus position determined by optimizer

        Also, if the refocus was initiated here in confocalgui then we need to handle the
        "returned" optimal position.
        """
        if caller_tag == 'confocalgui':
            self._scanning_logic.set_position(
                'optimizer',
                x=optimal_pos[0],
                y=optimal_pos[1],
                z=optimal_pos[2],
                a=0.0
            )
        self.enable_scan_actions()

    def set_history_actions(self, enable):
        """ Enable or disable history arrows taking history state into account. """
        if enable and self._scanning_logic.history_index < len(self._scanning_logic.history) - 1:
            self._mw.actionForward.setEnabled(True)
        else:
            self._mw.actionForward.setEnabled(False)
        if enable and self._scanning_logic.history_index > 0:
            self._mw.actionBack.setEnabled(True)
        else:
            self._mw.actionBack.setEnabled(False)

    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

    def update_settings(self):
        """ Write new settings from the gui to the file. """
        self._scanning_logic.set_clock_frequency(self._sd.clock_frequency_InputWidget.value())
        self._scanning_logic.return_slowness = self._sd.return_slowness_InputWidget.value()
        self._scanning_logic.permanent_scan = self._sd.loop_scan_CheckBox.isChecked()
        self._scanning_logic.depth_scan_dir_is_xz = self._sd.depth_dir_x_radioButton.isChecked()
        self.fixed_aspect_ratio_xy = self._sd.fixed_aspect_xy_checkBox.isChecked()
        self.fixed_aspect_ratio_depth = self._sd.fixed_aspect_depth_checkBox.isChecked()
        self.slider_small_step = self._sd.slider_small_step_DoubleSpinBox.value()
        self.slider_big_step = self._sd.slider_big_step_DoubleSpinBox.value()
        self.adjust_cursor_roi = self._sd.adjust_cursor_to_optimizer_checkBox.isChecked()

        # Update GUI icons to new loop-scan state
        self._set_scan_icons()
        # update cursor
        self.update_roi_xy_size()
        self.update_roi_depth_size()

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._sd.clock_frequency_InputWidget.setValue(int(self._scanning_logic._clock_frequency))
        self._sd.return_slowness_InputWidget.setValue(int(self._scanning_logic.return_slowness))
        self._sd.loop_scan_CheckBox.setChecked(self._scanning_logic.permanent_scan)
        if self._scanning_logic.depth_scan_dir_is_xz:
            self._sd.depth_dir_x_radioButton.setChecked(True)
        else:
            self._sd.depth_dir_y_radioButton.setChecked(True)

        self._sd.adjust_cursor_to_optimizer_checkBox.setChecked(self.adjust_cursor_roi)
        self._sd.fixed_aspect_xy_checkBox.setChecked(self.fixed_aspect_ratio_xy)
        self._sd.fixed_aspect_depth_checkBox.setChecked(self.fixed_aspect_ratio_depth)
        self._sd.slider_small_step_DoubleSpinBox.setValue(float(self.slider_small_step))
        self._sd.slider_big_step_DoubleSpinBox.setValue(float(self.slider_big_step))

    def menu_optimizer_settings(self):
        """ This method opens the settings menu. """
        self.keep_former_optimizer_settings()
        self._osd.exec_()

    def update_optimizer_settings(self):
        """ Write new settings from the gui to the file. """
        self._optimizer_logic.refocus_XY_size = self._osd.xy_optimizer_range_DoubleSpinBox.value()
        self._optimizer_logic.optimizer_XY_res = self._osd.xy_optimizer_resolution_SpinBox.value()
        self._optimizer_logic.refocus_Z_size = self._osd.z_optimizer_range_DoubleSpinBox.value()
        self._optimizer_logic.optimizer_Z_res = self._osd.z_optimizer_resolution_SpinBox.value()
        self._optimizer_logic.set_clock_frequency(self._osd.count_freq_SpinBox.value())
        self._optimizer_logic.return_slowness = self._osd.return_slow_SpinBox.value()
        self._optimizer_logic.hw_settle_time = self._osd.hw_settle_time_SpinBox.value() / 1000
        self._optimizer_logic.do_surface_subtraction = self._osd.do_surface_subtraction_CheckBox.isChecked()
        index = self._osd.opt_channel_ComboBox.currentIndex()
        self._optimizer_logic.opt_channel = int(self._osd.opt_channel_ComboBox.itemData(index, QtCore.Qt.UserRole))


        self._optimizer_logic.optimization_sequence = str(
            self._osd.optimization_sequence_lineEdit.text()
            ).upper().replace(" ", "").split(',')
        self._optimizer_logic.check_optimization_sequence()
        # z fit parameters
        self._optimizer_logic.use_custom_params = self._osd.fit_tab.paramUseSettings
        self.update_roi_xy_size()
        self.update_roi_depth_size()

    def keep_former_optimizer_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._osd.xy_optimizer_range_DoubleSpinBox.setValue(self._optimizer_logic.refocus_XY_size)
        self._osd.xy_optimizer_resolution_SpinBox.setValue(self._optimizer_logic.optimizer_XY_res)
        self._osd.z_optimizer_range_DoubleSpinBox.setValue(self._optimizer_logic.refocus_Z_size)
        self._osd.z_optimizer_resolution_SpinBox.setValue(self._optimizer_logic.optimizer_Z_res)
        self._osd.count_freq_SpinBox.setValue(self._optimizer_logic._clock_frequency)
        self._osd.return_slow_SpinBox.setValue(self._optimizer_logic.return_slowness)
        self._osd.hw_settle_time_SpinBox.setValue(self._optimizer_logic.hw_settle_time * 1000)
        self._osd.do_surface_subtraction_CheckBox.setChecked(self._optimizer_logic.do_surface_subtraction)

        old_ch = self._optimizer_logic.opt_channel
        index = self._osd.opt_channel_ComboBox.findData(old_ch)
        self._osd.opt_channel_ComboBox.setCurrentIndex(index)

        self._osd.optimization_sequence_lineEdit.setText(', '.join(self._optimizer_logic.optimization_sequence))

        # fit parameters
        self._osd.fit_tab.resetFitParameters()
        self.update_roi_xy_size()
        self.update_roi_depth_size()

    def ready_clicked(self):
        """ Stopp the scan if the state has switched to ready. """
        if self._scanning_logic.module_state() == 'locked':
            self._scanning_logic.permanent_scan = False
            self._scanning_logic.stop_scanning()
        if self._optimizer_logic.module_state() == 'locked':
            self._optimizer_logic.stop_refocus()

        self.enable_scan_actions()

    def xy_scan_clicked(self):
        """ Manages what happens if the xy scan is started. """
        self.disable_scan_actions()
        self._scanning_logic.start_scanning(zscan=False,tag='gui')

    def continue_xy_scan_clicked(self):
        """ Continue xy scan. """
        self.disable_scan_actions()
        self._scanning_logic.continue_scanning(zscan=False,tag='gui')

    def continue_depth_scan_clicked(self):
        """ Continue depth scan. """
        self.disable_scan_actions()
        self._scanning_logic.continue_scanning(zscan=True,tag='gui')

    def depth_scan_clicked(self,tag='gui'):
        """ Start depth scan. """
        self.disable_scan_actions()
        self._scanning_logic.start_scanning(zscan=True)

    def refocus_clicked(self):
        """ Start optimize position. """
        self.disable_scan_actions()
        # Get the current crosshair position to send to optimizer
        crosshair_pos = self._scanning_logic.get_position()
        self.sigStartOptimizer.emit(crosshair_pos, 'confocalgui')

    def update_crosshair_position_from_logic(self, tag):
        """ Update the GUI position of the crosshair from the logic.

        @param str tag: tag indicating the source of the update

        Ignore the update when it is tagged with one of the tags that the
        confocal gui emits, as the GUI elements were already adjusted.
        """
        if 'roi' not in tag and 'slider' not in tag and 'key' not in tag and 'input' not in tag:
            position = self._scanning_logic.get_position()
            x_pos = position[0]
            y_pos = position[1]
            z_pos = position[2]

            # XY image
            roi_h_view = x_pos - self.roi_xy.size()[0] * 0.5
            roi_v_view = y_pos - self.roi_xy.size()[1] * 0.5
            self.roi_xy.setPos([roi_h_view, roi_v_view])

            # depth image
            if self._scanning_logic.depth_img_is_xz:
                roi_h_view = x_pos - self.roi_depth.size()[0] * 0.5
            else:
                roi_h_view = y_pos - self.roi_depth.size()[1] * 0.5
            roi_v_view = z_pos - self.roi_depth.size()[1] * 0.5
            self.roi_depth.setPos([roi_h_view, roi_v_view])

            self.update_slider_x(x_pos)
            self.update_slider_y(y_pos)
            self.update_slider_z(z_pos)

            self.update_input_x(x_pos)
            self.update_input_y(y_pos)
            self.update_input_z(z_pos)

    def roi_xy_bounds_check(self, roi):
        """ Check if the focus cursor is outside the allowed range after drag
            and set its position to the limit
        """
        h_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        v_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        new_h_pos = np.clip(h_pos, *self._scanning_logic.x_range)
        new_v_pos = np.clip(v_pos, *self._scanning_logic.y_range)

        if h_pos != new_h_pos or v_pos != new_v_pos:
            self.update_roi_xy(new_h_pos, new_v_pos)

    def roi_depth_bounds_check(self, roi):
        """ Check if the focus cursor is oputside the allowed range after drag
            and set its position to the limit """
        h_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        v_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        if self._scanning_logic.depth_img_is_xz:
            h_range = self._scanning_logic.x_range
        else:
            h_range = self._scanning_logic.y_range

        new_h_pos = np.clip(h_pos, *h_range)
        new_v_pos = np.clip(v_pos, *self._scanning_logic.z_range)

        if h_pos != new_h_pos or v_pos != new_v_pos:
            self.update_roi_depth(new_h_pos, new_v_pos)

    def update_roi_xy(self, h=None, v=None):
        """ Adjust the xy ROI position if the value has changed.

        @param float x: real value of the current x position
        @param float y: real value of the current y position

        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not
        the actual position!
        """
        roi_h_view = self.roi_xy.pos()[0]
        roi_v_view = self.roi_xy.pos()[1]

        if h is not None:
            roi_h_view = h - self.roi_xy.size()[0] * 0.5
        if v is not None:
            roi_v_view = v - self.roi_xy.size()[1] * 0.5

        self.roi_xy.setPos([roi_h_view, roi_v_view])

    def update_roi_xy_size(self):
        """ Update the cursor size showing the optimizer scan area for the XY image.
        """
        hpos = self.roi_xy.pos()[0]
        vpos = self.roi_xy.pos()[1]
        hsize = self.roi_xy.size()[0]
        vsize = self.roi_xy.size()[1]
        hcenter = hpos + 0.5 * hsize
        vcenter = vpos + 0.5 * vsize
        if self.adjust_cursor_roi:
            newsize = self._optimizer_logic.refocus_XY_size
        else:
            viewrange = self.xy_image.getViewBox().viewRange()
            newsize = np.sqrt(np.sum(np.ptp(viewrange, axis=1)**2)) / 20
        self.roi_xy.setSize([newsize, newsize])
        self.roi_xy.setPos([hcenter - newsize / 2, vcenter - newsize / 2])

    def update_roi_depth_size(self):
        """ Update the cursor size showing the optimizer scan area for the X-depth image.
        """
        hpos = self.roi_depth.pos()[0]
        vpos = self.roi_depth.pos()[1]
        hsize = self.roi_depth.size()[0]
        vsize = self.roi_depth.size()[1]
        hcenter = hpos + 0.5 * hsize
        vcenter = vpos + 0.5 * vsize

        if self.adjust_cursor_roi:
            newsize_h = self._optimizer_logic.refocus_XY_size
            newsize_v = self._optimizer_logic.refocus_Z_size
        else:
            viewrange = self.depth_image.getViewBox().viewRange()
            newsize = np.sqrt(np.sum(np.ptp(viewrange, axis=1)**2)) / 20
            newsize_h = newsize
            newsize_v = newsize

        self.roi_depth.setSize([newsize_h, newsize_v])
        self.roi_depth.setPos([hcenter - newsize_h / 2, vcenter - newsize_v / 2])

    def update_roi_depth(self, h=None, v=None):
        """ Adjust the depth ROI position if the value has changed.

        @param float h: real value of the current horizontal position
        @param float v: real value of the current vertical position

        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not
        the actual position!
        """
        roi_h_view = self.roi_depth.pos()[0]
        roi_v_view = self.roi_depth.pos()[1]

        if h is not None:
            roi_h_view = h - self.roi_depth.size()[0] * 0.5
        if v is not None:
            roi_v_view = v - self.roi_depth.size()[1] * 0.5

        self.roi_depth.setPos([roi_h_view, roi_v_view])

    def update_from_roi_xy(self, roi):
        """The user manually moved the XY ROI, adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        h_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        v_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        h_pos = np.clip(h_pos, *self._scanning_logic.x_range)
        v_pos = np.clip(v_pos, *self._scanning_logic.y_range)

        if self._scanning_logic.depth_img_is_xz:
            self.update_roi_depth(h=h_pos)
        else:
            self.update_roi_depth(h=v_pos)

        self.update_slider_x(h_pos)
        self.update_slider_y(v_pos)

        self.update_input_x(h_pos)
        self.update_input_y(v_pos)

        self._scanning_logic.set_position('roixy', x=h_pos, y=v_pos)
        self._optimizer_logic.set_position('roixy', x=h_pos, y=v_pos)

    def update_from_roi_depth(self, roi):
        """The user manually moved the Z ROI, adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        if self._scanning_logic.depth_img_is_xz:
            h_range = self._scanning_logic.x_range
        else:
            h_range = self._scanning_logic.y_range

        h_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        v_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        h_pos = np.clip(h_pos, *h_range)
        v_pos = np.clip(v_pos, *self._scanning_logic.z_range)

        self.update_slider_z(v_pos)
        self.update_input_z(v_pos)

        if self._scanning_logic.depth_img_is_xz:
            self.update_roi_xy(h=h_pos)
            self.update_slider_x(h_pos)
            self.update_input_x(h_pos)
            self._scanning_logic.set_position('roidepth', x=h_pos, z=v_pos)
            self._optimizer_logic.set_position('roidepth', x=h_pos, z=-v_pos)
        else:
            self.update_roi_xy(v=h_pos)
            self.update_slider_y(h_pos)
            self.update_input_y(h_pos)
            self._scanning_logic.set_position('roidepth', y=h_pos, z=v_pos)
            self._optimizer_logic.set_position('roidepth', y=h_pos, z=-v_pos)

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

    def update_from_input_x(self):
        """ The user changed the number in the x position spin box, adjust all
            other GUI elements."""
        x_pos = self._mw.x_current_InputWidget.value()
        self.update_roi_xy(h=x_pos)
        if self._scanning_logic.depth_img_is_xz:
            self.update_roi_depth(h=x_pos)
        self.update_slider_x(x_pos)
        self._scanning_logic.set_position('xinput', x=x_pos)
        self._optimizer_logic.set_position('xinput', x=x_pos)

    def update_from_input_y(self):
        """ The user changed the number in the y position spin box, adjust all
            other GUI elements."""
        y_pos = self._mw.y_current_InputWidget.value()
        self.update_roi_xy(v=y_pos)
        if not self._scanning_logic.depth_img_is_xz:
            self.update_roi_depth(h=y_pos)
        self.update_slider_y(y_pos)
        self._scanning_logic.set_position('yinput', y=y_pos)
        self._optimizer_logic.set_position('yinput', y=y_pos)

    def update_from_input_z(self):
        """ The user changed the number in the z position spin box, adjust all
           other GUI elements."""
        z_pos = self._mw.z_current_InputWidget.value()
        self.update_roi_depth(v=z_pos)
        self.update_slider_z(z_pos)
        self._scanning_logic.set_position('zinput', z=z_pos)
        self._optimizer_logic.set_position('zinput', z=z_pos)

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
        """The user moved the x position slider, adjust the other GUI elements.

        @params int sliderValue: slider postion, a quantized whole number
        """
        x_pos = self._scanning_logic.x_range[0] + sliderValue * self.slider_res
        self.update_roi_xy(h=x_pos)
        if self._scanning_logic.depth_img_is_xz:
            self.update_roi_depth(h=x_pos)
        self.update_input_x(x_pos)
        self._scanning_logic.set_position('xslider', x=x_pos)
        self._optimizer_logic.set_position('xslider', x=x_pos)

    def update_from_slider_y(self, sliderValue):
        """The user moved the y position slider, adjust the other GUI elements.

        @params int sliderValue: slider postion, a quantized whole number
        """
        y_pos = self._scanning_logic.y_range[0] + sliderValue * self.slider_res
        self.update_roi_xy(v=y_pos)
        if not self._scanning_logic.depth_img_is_xz:
            self.update_roi_depth(h=y_pos)
        self.update_input_y(y_pos)
        self._scanning_logic.set_position('yslider', y=y_pos)
        self._optimizer_logic.set_position('yslider', y=y_pos)

    def update_from_slider_z(self, sliderValue):
        """The user moved the z position slider, adjust the other GUI elements.

        @params int sliderValue: slider postion, a quantized whole number
        """
        z_pos = self._scanning_logic.z_range[0] + sliderValue * self.slider_res
        self.update_roi_depth(v=z_pos)
        self.update_input_z(z_pos)
        self._scanning_logic.set_position('zslider', z=z_pos)
        self._optimizer_logic.set_position('zslider', z=z_pos)

    def update_slider_x(self, x_pos):
        """ Update the x slider when a change happens.

        @param float x_pos: x position in m
        """
        self._mw.x_SliderWidget.setValue((x_pos - self._scanning_logic.x_range[0]) / self.slider_res)

    def update_slider_y(self, y_pos):
        """ Update the y slider when a change happens.

        @param float y_pos: x yosition in m
        """
        self._mw.y_SliderWidget.setValue((y_pos - self._scanning_logic.y_range[0]) / self.slider_res)

    def update_slider_z(self, z_pos):
        """ Update the z slider when a change happens.

        @param float z_pos: z position in m
        """
        self._mw.z_SliderWidget.setValue((z_pos - self._scanning_logic.z_range[0]) / self.slider_res)

    def change_xy_resolution(self):
        """ Update the xy resolution in the logic according to the GUI.
        """
        self._scanning_logic.xy_resolution = self._mw.xy_res_InputWidget.value()

    def change_z_resolution(self):
        """ Update the z resolution in the logic according to the GUI.
        """
        self._scanning_logic.z_resolution = self._mw.z_res_InputWidget.value()

    def change_x_image_range(self):
        """ Adjust the image range for x in the logic. """
        self._scanning_logic.set_image_axis_range(
            'x',
            self._mw.x_min_InputWidget.value(),
            self._mw.x_max_InputWidget.value()
        )

    def change_y_image_range(self):
        """ Adjust the image range for y in the logic.
        """
        self._scanning_logic.set_image_axis_range(
            'y',
            self._mw.y_min_InputWidget.value(),
            self._mw.y_max_InputWidget.value()
        )

    def change_z_image_range(self):
        """ Adjust the image range for z in the logic. """
        self._scanning_logic.set_image_axis_range(
            'z',
            self._mw.z_min_InputWidget.value(),
            self._mw.z_max_InputWidget.value()
        )

    def update_tilt_correction(self):
        """ Update all tilt points from the scanner logic. """
        self._mw.tilt_01_x_pos_doubleSpinBox.setValue(self._scanning_logic.point1[0])
        self._mw.tilt_01_y_pos_doubleSpinBox.setValue(self._scanning_logic.point1[1])
        self._mw.tilt_01_z_pos_doubleSpinBox.setValue(self._scanning_logic.point1[2])

        self._mw.tilt_02_x_pos_doubleSpinBox.setValue(self._scanning_logic.point2[0])
        self._mw.tilt_02_y_pos_doubleSpinBox.setValue(self._scanning_logic.point2[1])
        self._mw.tilt_02_z_pos_doubleSpinBox.setValue(self._scanning_logic.point2[2])

        self._mw.tilt_03_x_pos_doubleSpinBox.setValue(self._scanning_logic.point3[0])
        self._mw.tilt_03_y_pos_doubleSpinBox.setValue(self._scanning_logic.point3[1])
        self._mw.tilt_03_z_pos_doubleSpinBox.setValue(self._scanning_logic.point3[2])

    def update_xy_channel(self, index):
        """ The displayed channel for the XY image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.xy_channel = int(self._mw.xy_channel_ComboBox.itemData(index, QtCore.Qt.UserRole))
        self.refresh_xy_image()

    def update_depth_channel(self, index):
        """ The displayed channel for the X-depth image was changed, refresh the displayed image.

            @param index int: index of selected channel item in combo box
        """
        self.depth_channel = int(self._mw.depth_channel_ComboBox.itemData(index, QtCore.Qt.UserRole))
        self.refresh_depth_image()

    def shortcut_to_xy_cb_manual(self):
        """Someone edited the absolute counts range for the xy colour bar, better update."""
        self._mw.xy_cb_manual_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def shortcut_to_xy_cb_centiles(self):
        """Someone edited the centiles range for the xy colour bar, better update."""
        self._mw.xy_cb_centiles_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def shortcut_to_depth_cb_manual(self):
        """Someone edited the absolute counts range for the z colour bar, better update."""
        # Change cb mode
        self._mw.depth_cb_manual_RadioButton.setChecked(True)
        self.update_depth_cb_range()

    def shortcut_to_depth_cb_centiles(self):
        """Someone edited the centiles range for the z colour bar, better update."""
        # Change cb mode
        self._mw.depth_cb_centiles_RadioButton.setChecked(True)
        self.update_depth_cb_range()

    def update_xy_cb_range(self):
        """Redraw xy colour bar and scan image."""
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

    def update_depth_cb_range(self):
        """Redraw z colour bar and scan image."""
        self.refresh_depth_colorbar()
        self.refresh_depth_image()

    def refresh_xy_image(self):
        """ Update the current XY image from the logic.

        Everytime the scanner is scanning a line in xy the
        image is rebuild and updated in the GUI.
        """
        self.xy_image.getViewBox().updateAutoRange()

        xy_image_data = self._scanning_logic.xy_image[:, :, 3 + self.xy_channel]

        cb_range = self.get_xy_cb_range()

        # Now update image with new color scale, and update colorbar
        self.xy_image.setImage(image=xy_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_xy_colorbar()

        # Unlock state widget if scan is finished
        if self._scanning_logic.module_state() != 'locked':
            self.enable_scan_actions()

    def refresh_depth_image(self):
        """ Update the current Depth image from the logic.

        Everytime the scanner is scanning a line in depth the
        image is rebuild and updated in the GUI.
        """

        self.depth_image.getViewBox().enableAutoRange()

        depth_image_data = self._scanning_logic.depth_image[:, :, 3 + self.depth_channel]
        cb_range = self.get_depth_cb_range()

        # Now update image with new color scale, and update colorbar
        self.depth_image.setImage(image=depth_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_depth_colorbar()

        # Unlock state widget if scan is finished
        if self._scanning_logic.module_state() != 'locked':
            self.enable_scan_actions()

    def refresh_refocus_image(self):
        """Refreshes the xy image, the crosshair and the colorbar. """
        ##########
        # Updating the xy optimizer image with color scaling based only on nonzero data
        xy_optimizer_image = self._optimizer_logic.xy_refocus_image[:, :, 3 + self._optimizer_logic.opt_channel]

        # If the Z scan is done first, then the XY image has only zeros and there is nothing to draw.
        if np.max(xy_optimizer_image) != 0:
            colorscale_min = np.min(xy_optimizer_image[np.nonzero(xy_optimizer_image)])
            colorscale_max = np.max(xy_optimizer_image[np.nonzero(xy_optimizer_image)])

            self.xy_refocus_image.setImage(image=xy_optimizer_image, levels=(colorscale_min, colorscale_max))
        ##########
        # TODO: does this need to be reset every time this refresh function is called?
        # Is there a better way?
        self.xy_refocus_image.setRect(
            QtCore.QRectF(
                self._optimizer_logic._initial_pos_x - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic._initial_pos_y - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size
            )
        )
        ##########
        # Crosshair in optimizer
        self.vLine.setValue(self._optimizer_logic.optim_pos_x)
        self.hLine.setValue(self._optimizer_logic.optim_pos_y)
        ##########
        # The depth optimization
        # data from chosen channel
        self.depth_refocus_image.setData(
            self._optimizer_logic._zimage_Z_values,
            self._optimizer_logic.z_refocus_line[:, self._optimizer_logic.opt_channel])
        # fit made from the data
        self.depth_refocus_fit_image.setData(
            self._optimizer_logic._fit_zimage_Z_values,
            self._optimizer_logic.z_fit_data)
        ##########
        # Set the optimized position label
        self._mw.refocus_position_label.setText(
            'µ = ({0:.3f}, {1:.3f}, {2:.3f}) µm   '
            'σ = ({3:.3f}, {4:.3f}, {5:.3f}) µm '
            ''.format(
                self._optimizer_logic.optim_pos_x * 1e6,
                self._optimizer_logic.optim_pos_y * 1e6,
                self._optimizer_logic.optim_pos_z * 1e6,
                self._optimizer_logic.optim_sigma_x * 1e6,
                self._optimizer_logic.optim_sigma_y * 1e6,
                self._optimizer_logic.optim_sigma_z * 1e6
            )
        )

    def refresh_scan_line(self):
        """ Get the previously scanned image line and display it in the scan line plot. """
        sc = self._scanning_logic._scan_counter
        sc = sc - 1 if sc >= 1 else sc
        if self._scanning_logic._zscan:
            self.scan_line_plot.setData(self._scanning_logic.depth_image[sc, :, 0:4:3])
        else:
            self.scan_line_plot.setData(self._scanning_logic.xy_image[sc, :, 0:4:3])

    def adjust_xy_window(self):
        """ Fit the visible window in the xy scan to full view.

        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and y. Make sure that in the process of the depth scan
        no method is calling adjust_depth_window, otherwise it will adjust for you
        a window which does not correspond to the scan!
        """
        # It is extremly crucial that before adjusting the window view and
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_xy_image()
        xy_viewbox = self.xy_image.getViewBox()

        xMin, xMax = self._scanning_logic.get_image_axis_range('x')
        yMin, yMax = self._scanning_logic.get_image_axis_range('y')

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
            xy_viewbox.setLimits(xMin=xMin - (xMax - xMin) * self.image_x_padding,
                                 xMax=xMax + (xMax - xMin) * self.image_x_padding,
                                 yMin=yMin - (yMax - yMin) * self.image_y_padding,
                                 yMax=yMax + (yMax - yMin) * self.image_y_padding)

        self.xy_image.setRect(QtCore.QRectF(xMin, yMin, xMax - xMin, yMax - yMin))

        self.put_cursor_in_xy_scan()

        xy_viewbox.updateAutoRange()
        xy_viewbox.updateViewRange()
        self.update_roi_xy()

    def adjust_depth_window(self):
        """ Fit the visible window in the depth scan to full view.

        Be careful in using that method, since it uses the input values for
        the ranges to adjust x and z. Make sure that in the process of the depth scan
        no method is calling adjust_xy_window, otherwise it will adjust for you
        a window which does not correspond to the scan!
        """
        # It is extremly crutial that before adjusting the window view and
        # limits, to make an update of the current image. Otherwise the
        # adjustment will just be made for the previous image.
        self.refresh_depth_image()

        depth_viewbox = self.depth_image.getViewBox()

        if self._scanning_logic.depth_img_is_xz:
            self._mw.depth_ViewWidget.setLabel('bottom', 'X position', units='m')
            xMin, xMax = self._scanning_logic.get_image_axis_range('x')
        else:
            self._mw.depth_ViewWidget.setLabel('bottom', 'Y position', units='m')
            xMin, xMax = self._scanning_logic.get_image_axis_range('y')  # Note 'y'

        zMin, zMax = self._scanning_logic.get_image_axis_range('z')

        if self.fixed_aspect_ratio_depth:
            # Reset the limit settings so that the method 'setAspectLocked'
            # works properly. It has to be done in a manual way since no method
            # exists yet to reset the set limits:
            depth_viewbox.state['limits']['xLimits'] = [None, None]
            depth_viewbox.state['limits']['yLimits'] = [None, None]
            depth_viewbox.state['limits']['xRange'] = [None, None]
            depth_viewbox.state['limits']['yRange'] = [None, None]

            depth_viewbox.setAspectLocked(lock=True, ratio=1.0)
            depth_viewbox.updateViewRange()
        else:
            depth_viewbox.setLimits(
                xMin=xMin - xMin * self.image_x_padding,
                xMax=xMax + xMax * self.image_x_padding,
                yMin=zMin - zMin * self.image_z_padding,
                yMax=zMax + zMax * self.image_z_padding
            )

        self.depth_image.setRect(QtCore.QRectF(xMin, zMin, xMax - xMin, zMax - zMin))

        self.put_cursor_in_depth_scan()

        depth_viewbox.updateAutoRange()
        depth_viewbox.updateViewRange()
        self.update_roi_depth()

    def put_cursor_in_xy_scan(self):
        """Put the xy crosshair back if it is outside of the visible range. """
        view_x_min, view_x_max = self._scanning_logic.get_image_axis_range('x')
        view_y_min, view_y_max = self._scanning_logic.get_image_axis_range('y')

        x_value = self.roi_xy.pos()[0]
        y_value = self.roi_xy.pos()[1]
        cross_pos = self.roi_xy.pos() + self.roi_xy.size() * 0.5

        if (view_x_min > cross_pos[0]):
            x_value = view_x_min + self.roi_xy.size()[0]

        if (view_x_max < cross_pos[0]):
            x_value = view_x_max - self.roi_xy.size()[0]

        if (view_y_min > cross_pos[1]):
            y_value = view_y_min + self.roi_xy.size()[1]

        if (view_y_max < cross_pos[1]):
            y_value = view_y_max - self.roi_xy.size()[1]

        self.roi_xy.setPos([x_value, y_value], update=True)


    def put_cursor_in_depth_scan(self):
        """Put the depth crosshair back if it is outside of the visible range. """
        view_x_min, view_x_max = self._scanning_logic.get_image_axis_range('x')
        view_z_min, view_z_max = self._scanning_logic.get_image_axis_range('z')

        x_value = self.roi_depth.pos()[0]
        z_value = self.roi_depth.pos()[1]
        cross_pos = self.roi_depth.pos() + self.roi_depth.size()*0.5

        if (view_x_min > cross_pos[0]):
            x_value = view_x_min + self.roi_depth.size()[0]

        if (view_x_max < cross_pos[0]):
            x_value = view_x_max - self.roi_depth.size()[0]

        if (view_z_min > cross_pos[1]):
            z_value = view_z_min + self.roi_depth.size()[1]

        if (view_z_max < cross_pos[1]):
            z_value = view_z_max - self.roi_depth.size()[1]

        self.roi_depth.setPos([x_value, z_value], update=True)

    def save_xy_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal data."""
        cb_range = self.get_xy_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.xy_cb_manual_RadioButton.isChecked():
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._scanning_logic.save_xy_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        filepath = self._save_logic.get_path_for_module(module_name='Confocal')
        filename = filepath + os.sep + time.strftime('%Y%m%d-%H%M-%S_confocal_xy_scan_raw_pixel_image')
        if self._sd.save_purePNG_checkBox.isChecked():
            self.xy_image.save(filename + '_raw.png')

    def save_xy_scan_image(self):
        """ Save the image and according to that the data.

        Here only the path to the module is taken from the save logic, but the
        picture save algorithm is situated here in confocal, since it is a very
        specific task to save the used PlotObject.
        """
        self.log.warning('Deprecated, use normal save method instead!')

    def save_depth_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal pic."""
        cb_range = self.get_depth_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.depth_cb_manual_RadioButton.isChecked():
            low_centile = self._mw.depth_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.depth_cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._scanning_logic.save_depth_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        filepath = self._save_logic.get_path_for_module(module_name='Confocal')
        filename = filepath + os.sep + time.strftime('%Y%m%d-%H%M-%S_confocal_depth_scan_raw_pixel_image')
        if self._sd.save_purePNG_checkBox.isChecked():
            self.depth_image.save(filename + '_raw.png')

    def save_depth_scan_image(self):
        """ Save the image and according to that the data.

        Here only the path to the module is taken from the save logic, but the
        picture save algorithm is situated here in confocal, since it is a very
        specific task to save the used PlotObject.
        """
        self.log.warning('Deprecated, use normal save method instead!')

    def switch_hardware(self):
        """ Switches the hardware state. """
        self._scanning_logic.switch_hardware(to_on=False)

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.xy_scan_dockWidget.show()
        self._mw.scan_control_dockWidget.show()
        self._mw.depth_scan_dockWidget.show()
        self._mw.optimizer_dockWidget.show()
        self._mw.tilt_correction_dockWidget.hide()
        self._mw.scanLineDockWidget.hide()

        # re-dock any floating dock widgets
        self._mw.xy_scan_dockWidget.setFloating(False)
        self._mw.scan_control_dockWidget.setFloating(False)
        self._mw.depth_scan_dockWidget.setFloating(False)
        self._mw.optimizer_dockWidget.setFloating(False)
        self._mw.tilt_correction_dockWidget.setFloating(False)
        self._mw.scanLineDockWidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.xy_scan_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.scan_control_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.depth_scan_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.optimizer_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.tilt_correction_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.scanLineDockWidget)

        # Resize window to default size
        self._mw.resize(1255, 939)

    def small_optimizer_view(self):
        """ Rearrange the DockWidgets to produce a small optimizer interface
        """
        # Hide the other dock widgets
        self._mw.xy_scan_dockWidget.hide()
        self._mw.scan_control_dockWidget.hide()
        self._mw.depth_scan_dockWidget.hide()

        # Show the optimizer dock widget, and re-dock
        self._mw.optimizer_dockWidget.show()
        self._mw.optimizer_dockWidget.setFloating(False)

        # Resize the window to small dimensions
        self._mw.resize(1000, 360)

    #####################################################################
    #        Methods for the zoom functionality of confocal GUI         #
    #####################################################################

# FIXME: These methods can be combined to one, because the procedure for the xy
#       and the depth scan is the same. A nice way has to be figured our here.
# FIXME: For the depth scan both possibilities have to be implemented, either
#       for a xz of a yz scan. The image ranges have to be adjusted properly.

    def zoom_clicked(self, is_checked):
        """ Activates the zoom mode in the xy and depth Windows.

        @param bool is_checked: pass the state of the zoom button if checked
                                or not.

        Depending on the state of the zoom button the DragMode in the
        ViewWidgets are changed.  There are 3 possible modes and each of them
        corresponds to a int value:
            - 0: NoDrag
            - 1: ScrollHandDrag
            - 2: RubberBandDrag

        Pyqtgraph implements every action for the NoDrag mode. That means the
        other two modes are not used at the moment. Therefore we are using the
        RubberBandDrag mode to simulate a zooming procedure. The selection
        window in the RubberBandDrag is only used to show the user which region
        will be selected. But the zooming idea is based on catched
        mousePressEvent and mouseReleaseEvent, which will be used if the
        RubberBandDrag mode is activated.

        For more information see the qt doc:
        http://doc.qt.io/qt-4.8/qgraphicsview.html#DragMode-enum
        """

        # You could also set the DragMode by its integer number, but in terms
        # of readability it is better to use the direct attributes from the
        # ViewWidgets and pass them to setDragMode.
        if is_checked:
            self.xy_image.getViewBox().setLeftButtonAction('rect')
            self.depth_image.getViewBox().setLeftButtonAction('rect')
        else:
            self.xy_image.getViewBox().setLeftButtonAction('pan')
            self.depth_image.getViewBox().setLeftButtonAction('pan')

    def xy_scan_start_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was pressed.

        @param QMouseEvent event: Mouse Event object which contains all the
                                  information at the time the event was emitted
        """
        if self._mw._doubleclicked:
            event.ignore()
            return

        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        pos = self.xy_image.getViewBox().mapSceneToView(event.localPos())

        # store the initial mouse position in a class variable
        self._current_xy_zoom_start = [pos.x(), pos.y()]
        event.accept()

    def xy_scan_end_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was released.

        @param QEvent event:
        """
        if self._mw._doubleclicked:
            self._mw._doubleclicked = False
            event.ignore()
            return

        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        # get the ViewBox which is also responsible for the xy_image
        viewbox = self.xy_image.getViewBox()

        # Map the mouse position in the whole ViewWidget to the coordinate
        # system of the ViewBox, which also includes the 2D graph:
        pos = viewbox.mapSceneToView(event.localPos())
        endpos = [pos.x(), pos.y()]

        initpos = self._current_xy_zoom_start



        # get the right corners from the zoom window:
        if initpos[0] > endpos[0]:
            xMin = endpos[0]
            xMax = initpos[0]
        else:
            xMin = initpos[0]
            xMax = endpos[0]

        if initpos[1] > endpos[1]:
            yMin = endpos[1]
            yMax = initpos[1]
        else:
            yMin = initpos[1]
            yMax = endpos[1]

        # set the values to the InputWidgets and update them
        self._mw.x_min_InputWidget.setValue(xMin)
        self._mw.x_max_InputWidget.setValue(xMax)
        self.change_x_image_range()

        self._mw.y_min_InputWidget.setValue(yMin)
        self._mw.y_max_InputWidget.setValue(yMax)
        self.change_y_image_range()

        # Finally change the visible area of the ViewBox:
        event.accept()
        viewbox.setRange(xRange=(xMin, xMax), yRange=(yMin, yMax), update=True)
        # second time is really needed, otherwisa zooming will not work for the first time
        viewbox.setRange(xRange=(xMin, xMax), yRange=(yMin, yMax), update=True)
        self.update_roi_xy()
        self._mw.action_zoom.setChecked(False)

    def reset_xy_imagerange(self):
        """ Reset the imagerange if autorange was pressed.

        Take the image range values directly from the scanned image and set
        them as the current image ranges.
        """
        # extract the range directly from the image:
        xMin = self._scanning_logic.xy_image[0, 0, 0]
        yMin = self._scanning_logic.xy_image[0, 0, 1]
        xMax = self._scanning_logic.xy_image[-1, -1, 0]
        yMax = self._scanning_logic.xy_image[-1, -1, 1]

        self._mw.x_min_InputWidget.setValue(xMin)
        self._mw.x_max_InputWidget.setValue(xMax)
        self.change_x_image_range()

        self._mw.y_min_InputWidget.setValue(yMin)
        self._mw.y_max_InputWidget.setValue(yMax)
        self.change_y_image_range()

    def set_full_scan_range_xy(self):
        xMin = self._scanning_logic.x_range[0]
        xMax = self._scanning_logic.x_range[1]
        self._mw.x_min_InputWidget.setValue(xMin)
        self._mw.x_max_InputWidget.setValue(xMax)
        self.change_x_image_range()

        yMin = self._scanning_logic.y_range[0]
        yMax = self._scanning_logic.y_range[1]
        self._mw.y_min_InputWidget.setValue(yMin)
        self._mw.y_max_InputWidget.setValue(yMax)
        self.change_y_image_range()

        for i in range(2):
            self.xy_image.getViewBox().setRange(xRange=(xMin, xMax), yRange=(yMin, yMax),
                update=True)

    def activate_zoom_double_click(self):
        if self._mw.action_zoom.isChecked():
            self._mw.action_zoom.setChecked(False)
        else:
            self._mw.action_zoom.setChecked(True)

    def depth_scan_start_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was pressed.

        @param QMouseEvent event: Mouse Event object which contains all the
                                  information at the time the event was emitted
        """
        if self._mw._doubleclicked:
            event.ignore()
            return
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        pos = self.depth_image.getViewBox().mapSceneToView(event.localPos())
        self._current_depth_zoom_start = [pos.x(), pos.y()]

        # store the initial mouse position in a class variable
        event.accept()

    def depth_scan_end_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was released.

        @param QEvent event:
        """
        if self._mw._doubleclicked:
            self._mw._doubleclicked = False
            event.ignore()
            return

        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        # get the ViewBox which is also responsible for the depth_image
        viewbox = self.depth_image.getViewBox()

        # Map the mouse position in the whole ViewWidget to the coordinate
        # system of the ViewBox, which also includes the 2D graph:
        pos = viewbox.mapSceneToView(event.localPos())
        endpos = [pos.x(), pos.y()]
        initpos = self._current_depth_zoom_start

        # get the right corners from the zoom window:
        if initpos[0] > endpos[0]:
            xMin = endpos[0]
            xMax = initpos[0]
        else:
            xMin = initpos[0]
            xMax = endpos[0]

        if initpos[1] > endpos[1]:
            zMin = endpos[1]
            zMax = initpos[1]
        else:
            zMin = initpos[1]
            zMax = endpos[1]

        # set the values to the InputWidgets and update them
        self._mw.x_min_InputWidget.setValue(xMin)
        self._mw.x_max_InputWidget.setValue(xMax)
        self.change_x_image_range()

        self._mw.z_min_InputWidget.setValue(zMin)
        self._mw.z_max_InputWidget.setValue(zMax)
        self.change_z_image_range()

        event.accept()
        # Finally change the visible area of the ViewBox:
        viewbox.setRange(xRange=(xMin, xMax), yRange=(zMin, zMax))
        # second time is really needed, otherwisa zooming will not work for the first time
        viewbox.setRange(xRange=(xMin, xMax), yRange=(zMin, zMax))
        self.update_roi_depth()

        self._mw.action_zoom.setChecked(False)


    def reset_depth_imagerange(self):
        """ Reset the imagerange if autorange was pressed.

        Take the image range values directly from the scanned image and set
        them as the current image ranges.
        """
        # extract the range directly from the image:
        xMin = self._scanning_logic.depth_image[0, 0, 0]
        zMin = self._scanning_logic.depth_image[0, 0, 2]
        xMax = self._scanning_logic.depth_image[-1, -1, 0]
        zMax = self._scanning_logic.depth_image[-1, -1, 2]

        self._mw.x_min_InputWidget.setValue(xMin)
        self._mw.x_max_InputWidget.setValue(xMax)
        self.change_x_image_range()

        self._mw.z_min_InputWidget.setValue(zMin)
        self._mw.z_max_InputWidget.setValue(zMax)
        self.change_z_image_range()

    def set_full_scan_range_z(self):

        if self._scanning_logic.depth_img_is_xz:
            hMin = self._scanning_logic.x_range[0]
            hMax = self._scanning_logic.x_range[1]
            self._mw.x_min_InputWidget.setValue(hMin)
            self._mw.x_max_InputWidget.setValue(hMax)
            self.change_x_image_range()
        else:
            hMin = self._scanning_logic.y_range[0]
            hMax = self._scanning_logic.y_range[1]
            self._mw.y_min_InputWidget.setValue(hMin)
            self._mw.y_max_InputWidget.setValue(hMax)
            self.change_y_image_range()

        vMin = self._scanning_logic.z_range[0]
        vMax = self._scanning_logic.z_range[1]
        self._mw.z_min_InputWidget.setValue(vMin)
        self._mw.z_max_InputWidget.setValue(vMax)
        self.change_z_image_range()

        for i in range(2):
            self.depth_image.getViewBox().setRange(xRange=(hMin, hMax), yRange=(vMin, vMax), update=True)

        self.update_roi_depth()

    def _set_scan_icons(self):
        """ Set the scan icons depending on whether loop-scan is active or not
        """

        if self._scanning_logic.permanent_scan:
            self._mw.action_scan_xy_start.setIcon(self._scan_xy_loop_icon)
            self._mw.action_scan_depth_start.setIcon(self._scan_depth_loop_icon)
        else:
            self._mw.action_scan_xy_start.setIcon(self._scan_xy_single_icon)
            self._mw.action_scan_depth_start.setIcon(self._scan_depth_single_icon)

    def logic_started_scanning(self, tag):
        """ Disable icons if a scan was started.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_scan_actions()

    def logic_continued_scanning(self, tag):
        """ Disable icons if a scan was continued.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_scan_actions()

    def logic_started_refocus(self, tag):
        """ Disable icons if a refocus was started.

            @param tag str: tag indicating command source
        """
        if tag == 'logic':
            self.disable_scan_actions()

    def logic_updated_scan_range(self):
        """ Update displayed scan range if the logic had it changed somewhere else.
        """
        self._mw.x_min_InputWidget.setValue(
            self._scanning_logic.get_image_axis_range('x')[0]
        )
        self._mw.x_max_InputWidget.setValue(
            self._scanning_logic.get_image_axis_range('x')[1]
        )

        self._mw.y_min_InputWidget.setValue(
            self._scanning_logic.get_image_axis_range('y')[0]
        )
        self._mw.y_max_InputWidget.setValue(
            self._scanning_logic.get_image_axis_range('y')[1]
        )

        self._mw.z_min_InputWidget.setValue(
            self._scanning_logic.get_image_axis_range('z')[0]
        )
        self._mw.z_max_InputWidget.setValue(
            self._scanning_logic.get_image_axis_range('z')[1]
        )

    def logic_updated_resolution(self):
        """ Update displayed resolution if the logic had it changed somewhere else.
        """
        self._mw.xy_res_InputWidget.setValue(
            self._scanning_logic.get_xy_resolution()
        )

        self._mw.z_res_InputWidget.setValue(
            self._scanning_logic.get_z_resolution()
        )