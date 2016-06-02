# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI for general Confocal control.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
Copyright (C) 2015-2016 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015-2016 Jan M. Binder jan.binder@uni-ulm.de
Copyright (C) 2015-2016 Lachlan J. Rogers lachlan.j.rogers@quantum.diamonds
"""

from pyqtgraph.Qt import QtCore, QtGui, uic
import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
import time
import os

from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colormaps import ColorScaleRainbow
from gui.fitsettings import FitSettingsWidget

# This _fromUtf8 bit was copied from the gui code produced using PyQt4 UI code generator
# It is used when specifying the paths to icons for the scanning actions.
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


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


class ConfocalMainWindow(QtGui.QMainWindow):

    """ Create the Mainwindow based on the corresponding *.ui file. """

    sigPressKeyBoard = QtCore.Signal(QtCore.QEvent)

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_confocalgui.ui')

        # Load it
        super(ConfocalMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

    def keyPressEvent(self, event):
        """Pass the keyboard press event from the main window further. """
        self.sigPressKeyBoard.emit(event)


class ConfocalSettingDialog(QtGui.QDialog):

    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_cf_settings.ui')

        # Load it
        super(ConfocalSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class OptimizerSettingDialog(QtGui.QDialog):

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
    _in = {'confocallogic1': 'ConfocalLogic',
           'savelogic': 'SaveLogic',
           'optimizerlogic1': 'OptimizerLogic'
           }

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        c_dict = {'onactivate': self.initUI,
                  'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key, config[key]),
                        msgType='status')

        self.fixed_aspect_ratio_xy = config['fixed_aspect_ratio_xy']
        self.fixed_aspect_ratio_depth = config['fixed_aspect_ratio_depth']
#        self.slider_stepsize = config['slider_stepsize']
        self.image_x_padding = config['image_x_padding']
        self.image_y_padding = config['image_y_padding']
        self.image_z_padding = config['image_z_padding']

        self.slider_small_step = 10         # initial value in nanometer
        self.slider_big_step = 100          # initial value in nanometer

        # the 4 possible orientations, where the first entry of the array
        # tells you the actual position. The number tells you how often a 90
        # degree trun is applied.
        self.xy_image_orientation = np.array([0, 1, 2, -1], int)
        self.depth_image_orientation = np.array([0, 1, 2, -1], int)

    def initUI(self, e=None):
        """ Initializes all needed UI files and establishes the connectors.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """

        # Getting an access to all connectors:
        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._optimizer_logic = self.connector['in']['optimizerlogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self._hardware_state = True

        self.initMainUI(e)      # initialize the main GUI
        self.initSettingsUI(e)  # initialize the settings GUI
        self.initOptimizerSettingsUI(e)  # initialize the optimizer settings GUI

    def initMainUI(self, e=None):
        """ Definition, configuration and initialisation of the confocal GUI.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

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

        # Get the image for the display from the logic. Transpose the received
        # matrix to get the proper scan. The graphig widget displays vector-
        # wise the lines and the lines are normally columns, but in our
        # measurement we scan rows per row. That's why it has to be transposed.
        arr01 = self._scanning_logic.xy_image[:, :, 3].transpose()
        arr02 = self._scanning_logic.depth_image[:, :, 3].transpose()

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(arr01) / 2
        ini_pos_y_crosshair = len(arr01) / 2
        ini_pos_z_crosshair = len(arr02) / 2

        # Load the images for xy and depth in the display:
        self.xy_image = pg.ImageItem(arr01)
        self.depth_image = pg.ImageItem(arr02)

        # Hide Tiltcorrection window
        self._mw.tilt_correction_dockWidget.hide()

        ###################################################################
        #               Configuration of the optimizer tab                #
        ###################################################################
        # Load the image for the optimizer tab
        self.xy_refocus_image = pg.ImageItem(self._optimizer_logic.xy_refocus_image[:, :, 3].transpose())
        self.xy_refocus_image.setRect(
            QtCore.QRectF(
                self._optimizer_logic._initial_pos_x - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic._initial_pos_y - 0.5 * self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size,
                self._optimizer_logic.refocus_XY_size
            )
        )
        self.depth_refocus_image = pg.ScatterPlotItem(
            x=self._optimizer_logic._zimage_Z_values,
            y=self._optimizer_logic.z_refocus_line,
            symbol='o'
        )
        self.depth_refocus_fit_image = pg.PlotDataItem(
            x=self._optimizer_logic._fit_zimage_Z_values,
            y=self._optimizer_logic.z_fit_data,
            pen=QtGui.QPen(QtGui.QColor(255, 0, 255, 255))
        )

        # Add the display item to the xy and depth VieWidget, which was defined in
        # the UI file.
        self._mw.xy_refocus_ViewWidget_2.addItem(self.xy_refocus_image)
        self._mw.depth_refocus_ViewWidget_2.addItem(self.depth_refocus_image)

        # Labelling axes
        self._mw.xy_refocus_ViewWidget_2.setLabel('bottom', 'X position', units='µm')
        self._mw.xy_refocus_ViewWidget_2.setLabel('left', 'Y position', units='µm')

        self._mw.depth_refocus_ViewWidget_2.addItem(self.depth_refocus_fit_image)

        self._mw.depth_refocus_ViewWidget_2.setLabel('bottom', 'Z position', units='µm')
        self._mw.depth_refocus_ViewWidget_2.setLabel('left', 'Fluorescence', units='c/s')

        # Add crosshair to the xy refocus scan
        self.vLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255, 0, 255, 255), 0.02), pos=50, angle=90, movable=False)
        self.hLine = pg.InfiniteLine(pen=QtGui.QPen(QtGui.QColor(255, 0, 255, 255), 0.02), pos=50, angle=0, movable=False)
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
        self._mw.xy_ViewWidget.setLabel('bottom', 'X position', units='µm')
        self._mw.xy_ViewWidget.setLabel('left', 'Y position', units='µm')
        self._mw.depth_ViewWidget.setLabel('bottom', 'X position', units='µm')
        self._mw.depth_ViewWidget.setLabel('left', 'Z position', units='µm')

        # Create Region of Interest for xy image and add to xy Image Widget:
        self.roi_xy = CrossROI(
            [
                ini_pos_x_crosshair - len(arr01) / 40,
                ini_pos_y_crosshair - len(arr01) / 40
            ],
            [len(arr01) / 20, len(arr01) / 20],
            pen={'color': "F0F", 'width': 1},
            removable=True
        )
        self._mw.xy_ViewWidget.addItem(self.roi_xy)

        # create horizontal and vertical line as a crosshair in xy image:
        self.hline_xy = CrossLine(pos=self.roi_xy.pos() + self.roi_xy.size() * 0.5,
                                  angle=0, pen={'color': "F0F", 'width': 1})
        self.vline_xy = CrossLine(pos=self.roi_xy.pos() + self.roi_xy.size() * 0.5,
                                  angle=90, pen={'color': "F0F", 'width': 1})

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_xy.sigRegionChanged.connect(self.hline_xy.adjust)
        self.roi_xy.sigRegionChanged.connect(self.vline_xy.adjust)
        self.roi_xy.sigUserRegionUpdate.connect(self.update_from_roi_xy)
        self.roi_xy.sigRegionChangeFinished.connect(self.roi_xy_bounds_check)

        # add the configured crosshair to the xy Widget
        self._mw.xy_ViewWidget.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.addItem(self.vline_xy)

        # Create Region of Interest for depth image and add to xy Image Widget:
        self.roi_depth = CrossROI(
            [
                ini_pos_x_crosshair - len(arr02) / 20,
                ini_pos_z_crosshair - len(arr02) / 20
            ],
            [len(arr02) / 20, len(arr02) / 20],
            pen={'color': "F0F", 'width': 1},
            removable=True
        )
        self._mw.depth_ViewWidget.addItem(self.roi_depth)

        # create horizontal and vertical line as a crosshair in depth image:
        self.hline_depth = CrossLine(
            pos=self.roi_depth.pos() + self.roi_depth.size() * 0.5,
            angle=0,
            pen={'color': "F0F", 'width': 1}
        )
        self.vline_depth = CrossLine(
            pos=self.roi_depth.pos() + self.roi_depth.size() * 0.5,
            angle=90,
            pen={'color': "F0F", 'width': 1}
        )
        # connect the change of a region with the adjustment of the crosshair:
        self.roi_depth.sigRegionChanged.connect(self.hline_depth.adjust)
        self.roi_depth.sigRegionChanged.connect(self.vline_depth.adjust)
        self.roi_depth.sigUserRegionUpdate.connect(self.update_from_roi_depth)
        self.roi_depth.sigRegionChangeFinished.connect(self.roi_depth_bounds_check)

        # add the configured crosshair to the depth Widget:
        self._mw.depth_ViewWidget.addItem(self.hline_depth)
        self._mw.depth_ViewWidget.addItem(self.vline_depth)

        # Setup the Sliders:
        # Calculate the needed Range for the sliders. The image ranges comming
        # from the Logic module must be in micrometer.
        self.slider_res = 0.001  # 1 nanometer resolution per one change, units
                                 # are micrometer

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
        self._mw.x_current_InputWidget.setRange(self._scanning_logic.x_range[0], self._scanning_logic.x_range[1])
        self._mw.y_current_InputWidget.setRange(self._scanning_logic.y_range[0], self._scanning_logic.y_range[1])
        self._mw.z_current_InputWidget.setRange(self._scanning_logic.z_range[0], self._scanning_logic.z_range[1])

        # Predefine the maximal and minimal image range as the default values
        # for the display of the range:
        self._mw.x_min_InputWidget.setValue(self._scanning_logic.image_x_range[0])
        self._mw.x_max_InputWidget.setValue(self._scanning_logic.image_x_range[1])
        self._mw.y_min_InputWidget.setValue(self._scanning_logic.image_y_range[0])
        self._mw.y_max_InputWidget.setValue(self._scanning_logic.image_y_range[1])
        self._mw.z_min_InputWidget.setValue(self._scanning_logic.image_z_range[0])
        self._mw.z_max_InputWidget.setValue(self._scanning_logic.image_z_range[1])

        # set the maximal ranges for the imagerange from the logic:
        self._mw.x_min_InputWidget.setRange(self._scanning_logic.x_range[0], self._scanning_logic.x_range[1])
        self._mw.x_max_InputWidget.setRange(self._scanning_logic.x_range[0], self._scanning_logic.x_range[1])
        self._mw.y_min_InputWidget.setRange(self._scanning_logic.y_range[0], self._scanning_logic.y_range[1])
        self._mw.y_max_InputWidget.setRange(self._scanning_logic.y_range[0], self._scanning_logic.y_range[1])
        self._mw.z_min_InputWidget.setRange(self._scanning_logic.z_range[0], self._scanning_logic.z_range[1])
        self._mw.z_max_InputWidget.setRange(self._scanning_logic.z_range[0], self._scanning_logic.z_range[1])

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

        self._mw.xy_res_InputWidget.editingFinished.connect(self.change_xy_resolution, QtCore.Qt.QueuedConnection)
        self._mw.z_res_InputWidget.editingFinished.connect(self.change_z_resolution)

        self._mw.x_min_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.x_max_InputWidget.editingFinished.connect(self.change_x_image_range)
        self._mw.y_min_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.y_max_InputWidget.editingFinished.connect(self.change_y_image_range)
        self._mw.z_min_InputWidget.editingFinished.connect(self.change_z_image_range)
        self._mw.z_max_InputWidget.editingFinished.connect(self.change_z_image_range)

        # Connect the change of the viewed area to an adjustment of the ROI:
        self.xy_image.getViewBox().sigRangeChanged.connect(self.adjust_aspect_roi_xy)
        self.depth_image.getViewBox().sigRangeChanged.connect(self.adjust_aspect_roi_depth)

        #################################################################
        #                           Actions                             #
        #################################################################
        # Connect the scan actions to the events if they are clicked. Connect
        # also the adjustment of the displayed windows.
        self._mw.action_stop_scanning.triggered.connect(self.ready_clicked)

        self._mw.action_scan_xy_start.triggered.connect(self.xy_scan_clicked, type=QtCore.Qt.QueuedConnection)
        self._mw.action_scan_xy_resume.triggered.connect(self.continue_xy_scan_clicked)
        self._mw.action_scan_depth_start.triggered.connect(self.depth_scan_clicked)
        self._mw.action_scan_depth_resume.triggered.connect(self.continue_depth_scan_clicked)
        #self._mw.actionRotated_depth_scan.triggered.connect(self.rotate_depth_scan_clicked)

        self._mw.action_optimize_position.triggered.connect(self.refocus_clicked)

        # history actions
        self._mw.actionForward.triggered.connect(self._scanning_logic.history_forward)
        self._mw.actionBack.triggered.connect(self._scanning_logic.history_back)
        self._scanning_logic.signal_history_event.connect(lambda: self.set_history_actions(True))
        self._scanning_logic.signal_history_event.connect(self.update_xy_cb_range)
        self._scanning_logic.signal_history_event.connect(self.update_depth_cb_range)

        # Get initial tilt correction values
        self._mw.action_Tiltcorrection.setChecked(self._scanning_logic.TiltCorrection)

        self._mw.tilt_01_x_pos_doubleSpinBox.setValue(self._scanning_logic.point1[0])
        self._mw.tilt_01_y_pos_doubleSpinBox.setValue(self._scanning_logic.point1[1])
        self._mw.tilt_01_z_pos_doubleSpinBox.setValue(self._scanning_logic.point1[2])

        self._mw.tilt_02_x_pos_doubleSpinBox.setValue(self._scanning_logic.point2[0])
        self._mw.tilt_02_y_pos_doubleSpinBox.setValue(self._scanning_logic.point2[1])
        self._mw.tilt_02_z_pos_doubleSpinBox.setValue(self._scanning_logic.point2[2])

        self._mw.tilt_03_x_pos_doubleSpinBox.setValue(self._scanning_logic.point3[0])
        self._mw.tilt_03_y_pos_doubleSpinBox.setValue(self._scanning_logic.point3[1])
        self._mw.tilt_03_z_pos_doubleSpinBox.setValue(self._scanning_logic.point3[2])

        # Connect tiltcorrection stuff
        self._mw.action_Tiltcorrection.triggered.connect(self.use_tiltcorrection_clicked)
        self._mw.tilt_set_01_pushButton.clicked.connect(self.set_tiltpoint_01_clicked)
        self._mw.tilt_set_02_pushButton.clicked.connect(self.set_tiltpoint_02_clicked)
        self._mw.tilt_set_03_pushButton.clicked.connect(self.set_tiltpoint_03_clicked)
        self._mw.calc_tilt_pushButton.clicked.connect(self.calculate_tiltcorrection_clicked)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)
        self._mw.optimizer_only_view_Action.triggered.connect(self.small_optimizer_view)

        # Connect the buttons and inputs for the xy colorbar
        self._mw.xy_cb_manual_RadioButton.clicked.connect(self.update_xy_cb_range)
        self._mw.xy_cb_centiles_RadioButton.clicked.connect(self.update_xy_cb_range)

        self._mw.xy_cb_min_InputWidget.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_max_InputWidget.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_low_centile_InputWidget.valueChanged.connect(self.shortcut_to_xy_cb_centiles)
        self._mw.xy_cb_high_centile_InputWidget.valueChanged.connect(self.shortcut_to_xy_cb_centiles)

        # Connect the buttons and inputs for the depth colorbars
        # RadioButtons in Main tab
        self._mw.depth_cb_manual_RadioButton.clicked.connect(self.update_depth_cb_range)
        self._mw.depth_cb_centiles_RadioButton.clicked.connect(self.update_depth_cb_range)

        # input edits in Main tab
        self._mw.depth_cb_min_InputWidget.valueChanged.connect(self.shortcut_to_depth_cb_manual)
        self._mw.depth_cb_max_InputWidget.valueChanged.connect(self.shortcut_to_depth_cb_manual)
        self._mw.depth_cb_low_centile_InputWidget.valueChanged.connect(self.shortcut_to_depth_cb_centiles)
        self._mw.depth_cb_high_centile_InputWidget.valueChanged.connect(self.shortcut_to_depth_cb_centiles)

        # Connect the emitted signal of an image change from the logic with
        # a refresh of the GUI picture:
        self._scanning_logic.signal_xy_image_updated.connect(self.refresh_xy_image)
        self._scanning_logic.signal_depth_image_updated.connect(self.refresh_depth_image)
        self._optimizer_logic.signal_image_updated.connect(self.refresh_refocus_image)
        self._scanning_logic.sigImageXYInitialized.connect(self.adjust_xy_window)
        self._scanning_logic.sigImageDepthInitialized.connect(self.adjust_depth_window)

        # Connect the signal from the logic with an update of the cursor position
        self._scanning_logic.signal_change_position.connect(self.update_crosshair_position_from_logic)

        # Connect the tracker
        self._optimizer_logic.signal_refocus_finished.connect(self._refocus_finished_wrapper)
        self._optimizer_logic.signal_refocus_started.connect(self.disable_scan_actions)

        # Connect the 'File' Menu dialog and the Settings window in confocal
        # with the methods:
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._mw.action_optimizer_settings.triggered.connect(self.menu_optimizer_settings)
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan_data)
        self._mw.actionSave_Depth_Scan.triggered.connect(self.save_depth_scan_data)
        self._mw.actionSave_XY_Image_Data.triggered.connect(self.save_xy_scan_image)
        self._mw.actionSave_Depth_Image_Data.triggered.connect(self.save_depth_scan_image)

        # Connect the image rotation buttons with the GUI:
        self._mw.xy_rotate_anticlockwise_PushButton.clicked.connect(self.rotate_xy_image_anticlockwise)
        self._mw.xy_rotate_clockwise_PushButton.clicked.connect(self.rotate_xy_image_clockwise)
        self._mw.depth_rotate_anticlockwise_PushButton.clicked.connect(self.rotate_depth_image_anticlockwise)
        self._mw.depth_rotate_clockwise_PushButton.clicked.connect(self.rotate_depth_image_clockwise)

        # Configure and connect the zoom actions with the desired buttons and
        # functions if
        self._mw.action_zoom.toggled.connect(self.zoom_clicked)
        self._mw.xy_ViewWidget.sigMouseClick.connect(self.xy_scan_start_zoom_point)
        self._mw.xy_ViewWidget.sigMouseReleased.connect(self.xy_scan_end_zoom_point)

        self._mw.depth_ViewWidget.sigMouseClick.connect(self.depth_scan_start_zoom_point)
        self._mw.depth_ViewWidget.sigMouseReleased.connect(self.depth_scan_end_zoom_point)

        # Check whenever a state of the ViewBox was changed inside of a
        # PlotWidget, which creates a xy_ViewWidget or a depth_Viewwidget:
        #self._mw.xy_ViewWidget.getViewBox().sigRangeChanged.connect(self.reset_xy_imagerange)

        ###################################################################
        #               Icons for the scan actions                        #
        ###################################################################

        self._scan_xy_single_icon = QtGui.QIcon()
        self._scan_xy_single_icon.addPixmap(QtGui.QPixmap(_fromUtf8("artwork/icons/qudiTheme/22x22/scan-xy-start.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self._scan_depth_single_icon = QtGui.QIcon()
        self._scan_depth_single_icon.addPixmap(QtGui.QPixmap(_fromUtf8("artwork/icons/qudiTheme/22x22/scan-depth-start.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self._scan_xy_loop_icon = QtGui.QIcon()
        self._scan_xy_loop_icon.addPixmap(QtGui.QPixmap(_fromUtf8("artwork/icons/qudiTheme/22x22/scan-xy-loop.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self._scan_depth_loop_icon = QtGui.QIcon()
        self._scan_depth_loop_icon.addPixmap(QtGui.QPixmap(_fromUtf8("artwork/icons/qudiTheme/22x22/scan-depth-loop.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        #################################################################
        #           Connect the colorbar and their actions              #
        #################################################################
        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleRainbow()

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
        self.adjust_aspect_roi_xy()
        self.adjust_aspect_roi_depth()
        self.enable_scan_actions()
        self.update_crosshair_position_from_logic('init')
        self.adjust_xy_window()
        self.adjust_depth_window()

        self.show()

    def initSettingsUI(self, e=None):
        """ Definition, configuration and initialisation of the settings GUI.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._sd = ConfocalSettingDialog()
        # Connect the action of the settings window with the code:
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self._sd.hardware_switch.clicked.connect(self.switch_hardware)

        # write the configuration to the settings window of the GUI.
        self.keep_former_settings()

    def initOptimizerSettingsUI(self, e=None):
        """ Definition, configuration and initialisation of the optimizer settings GUI.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._osd = OptimizerSettingDialog()
        # Connect the action of the settings window with the code:
        self._osd.accepted.connect(self.update_optimizer_settings)
        self._osd.rejected.connect(self.keep_former_optimizer_settings)
        self._osd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_optimizer_settings)

        # Generation of the fit params tab ##################
        self._osd.fit_tab = FitSettingsWidget(self._optimizer_logic.z_params)
        self._osd.settings_tabWidget.addTab(self._osd.fit_tab, "Fit Params")

        # write the configuration to the settings window of the GUI.
        self.keep_former_optimizer_settings()

    def deactivation(self, e):
        """ Reverse steps of activation

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

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

        @param object event: PyQt4.QtCore.QEvent object.
        """
        modifiers = QtGui.QApplication.keyboardModifiers()

        x_pos, y_pos, z_pos = self._scanning_logic.get_position()   # in micrometers

        if modifiers == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_Right:
                self.update_from_key(x=float(round(x_pos + self.slider_big_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_Left:
                self.update_from_key(x=float(round(x_pos - self.slider_big_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_Up:
                self.update_from_key(y=float(round(y_pos + self.slider_big_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_Down:
                self.update_from_key(y=float(round(y_pos - self.slider_big_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_PageUp:
                self.update_from_key(z=float(round(z_pos + self.slider_big_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_PageDown:
                self.update_from_key(z=float(round(z_pos - self.slider_big_step * 0.001, 4)))
            else:
                event.ignore()
        else:
            if event.key() == QtCore.Qt.Key_Right:
                self.update_from_key(x=float(round(x_pos + self.slider_small_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_Left:
                self.update_from_key(x=float(round(x_pos - self.slider_small_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_Up:
                self.update_from_key(y=float(round(y_pos + self.slider_small_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_Down:
                self.update_from_key(y=float(round(y_pos - self.slider_small_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_PageUp:
                self.update_from_key(z=float(round(z_pos + self.slider_small_step * 0.001, 4)))
            elif event.key() == QtCore.Qt.Key_PageDown:
                self.update_from_key(z=float(round(z_pos - self.slider_small_step * 0.001, 4)))
            else:
                event.ignore()

    def get_xy_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.xy_cb_manual_RadioButton.isChecked() or np.max(self.xy_image.image) == 0.0:
            cb_min = self._mw.xy_cb_min_InputWidget.value()
            cb_max = self._mw.xy_cb_max_InputWidget.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            xy_image_nonzero = self.xy_image.image[np.nonzero(self.xy_image.image)]

            # Read centile range
            low_centile = self._mw.xy_cb_low_centile_InputWidget.value()
            high_centile = self._mw.xy_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(xy_image_nonzero, low_centile)
            cb_max = np.percentile(xy_image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def get_depth_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.depth_cb_manual_RadioButton.isChecked() or np.max(self.depth_image.image) == 0.0:
            cb_min = self._mw.depth_cb_min_InputWidget.value()
            cb_max = self._mw.depth_cb_max_InputWidget.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            depth_image_nonzero = self.depth_image.image[np.nonzero(self.depth_image.image)]

            # Read centile range
            low_centile = self._mw.depth_cb_low_centile_InputWidget.value()
            high_centile = self._mw.depth_cb_high_centile_InputWidget.value()

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
        # Ensable the stop scanning button
        self._mw.action_stop_scanning.setEnabled(True)

        # Disable the start scan buttons
        self._mw.action_scan_xy_start.setEnabled(False)
        self._mw.action_scan_depth_start.setEnabled(False)
#        self._mw.actionRotated_depth_scan.setEnabled(False)

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

        self.enable_scan_actions()

        if caller_tag == 'confocalgui':
            self._scanning_logic.set_position(
                'optimizer',
                x=optimal_pos[0],
                y=optimal_pos[1],
                z=optimal_pos[2],
                a=0.0
            )

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
        self.fixed_aspect_ratio_xy = self._sd.fixed_aspect_xy_checkBox.isChecked()
        self.fixed_aspect_ratio_depth = self._sd.fixed_aspect_depth_checkBox.isChecked()
        self.slider_small_step = self._sd.slider_small_step_SpinBox.value()
        self.slider_big_step = self._sd.slider_big_step_SpinBox.value()

        # Update GUI icons to new loop-scan state
        self._set_scan_icons()

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._sd.clock_frequency_InputWidget.setValue(int(self._scanning_logic._clock_frequency))
        self._sd.return_slowness_InputWidget.setValue(int(self._scanning_logic.return_slowness))
        self._sd.loop_scan_CheckBox.setChecked(self._scanning_logic.permanent_scan)
        self._sd.fixed_aspect_xy_checkBox.setChecked(self.fixed_aspect_ratio_xy)
        self._sd.fixed_aspect_depth_checkBox.setChecked(self.fixed_aspect_ratio_depth)
        self._sd.slider_small_step_SpinBox.setValue(int(self.slider_small_step))
        self._sd.slider_big_step_SpinBox.setValue(int(self.slider_big_step))

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

        self._optimizer_logic.optimization_sequence = str(self._osd.optimization_sequence_lineEdit.text()).upper().replace(" ", "").split(',')

        self._optimizer_logic.check_optimization_sequence()
        # z fit parameters
        self._optimizer_logic.use_custom_params = self._osd.fit_tab.updateFitSettings(self._optimizer_logic.z_params)

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

        self._osd.optimization_sequence_lineEdit.setText(', '.join(self._optimizer_logic.optimization_sequence))

        # fit parameters
        self._osd.fit_tab.keepFitSettings(self._optimizer_logic.z_params, self._optimizer_logic.use_custom_params)

    def ready_clicked(self):
        """ Stopp the scan if the state has switched to ready. """
        if self._scanning_logic.getState() == 'locked':
            self._scanning_logic.permanent_scan = False
            self._scanning_logic.stop_scanning()
        if self._optimizer_logic.getState() == 'locked':
            self._optimizer_logic.stop_refocus()

        self.enable_scan_actions()

    def xy_scan_clicked(self):
        """ Manages what happens if the xy scan is started. """
        self._scanning_logic.start_scanning()
        self.disable_scan_actions()

    def continue_xy_scan_clicked(self):
        """ Manages what happens if the xy scan is continued.

        @param bool enabled: continue scan if that is possible
        """
        self._scanning_logic.continue_scanning(zscan=False)
        self.disable_scan_actions()

    def continue_depth_scan_clicked(self):
        """ Manages what happens if the xy scan is continued.

        @param bool enabled: continue scan if that is possible
        """
        self._scanning_logic.continue_scanning(zscan=True)
        self.disable_scan_actions()

    def depth_scan_clicked(self):
        """ Manages what happens if the depth scan is started.

        @param bool enabled: start scan if that is possible
        """
        self._scanning_logic.start_scanning(zscan=True)
        self.disable_scan_actions()

    def rotate_depth_scan_clicked(self):
        self._scanning_logic.yz_instead_of_xz_scan = not self._scanning_logic.yz_instead_of_xz_scan

    def refocus_clicked(self):
        """ Manages what happens if the optimizer is started.

        @param bool enabled: start optimizer if that is possible
        """
        self._scanning_logic.stop_scanning()  # CHECK: is this necessary?

        # Get the current crosshair position to send to optimizer
        crosshair_pos = self._scanning_logic.get_position()

        self._optimizer_logic.start_refocus(initial_pos=crosshair_pos, caller_tag='confocalgui')

        self.disable_scan_actions()

    def update_crosshair_position_from_logic(self, tag):
        """ Update the GUI position of the crosshair from the logic.

        @param str tag: tag indicating the source of the update

        Ignore the update when it is tagged with one of the tags that the confocal gui emits, as the
        GUI elements were already adjusted.
        """
        if not 'roi' in tag and not 'slider' in tag and not 'key' in tag and not 'input' in tag:
            x_pos, y_pos, z_pos = self._scanning_logic.get_position()

            roi_x_view = x_pos - self.roi_xy.size()[0] * 0.5
            roi_y_view = y_pos - self.roi_xy.size()[1] * 0.5
            self.roi_xy.setPos([roi_x_view, roi_y_view])

            roi_x_view = x_pos - self.roi_depth.size()[0] * 0.5
            roi_y_view = z_pos - self.roi_depth.size()[1] * 0.5
            self.roi_depth.setPos([roi_x_view, roi_y_view])

            self.update_slider_x(x_pos)
            self.update_slider_y(y_pos)
            self.update_slider_z(z_pos)

            self.update_input_x(x_pos)
            self.update_input_y(y_pos)
            self.update_input_z(z_pos)

    def roi_xy_bounds_check(self, roi):
        """Check if the focus cursor is oputside the allowed range after drag and set its position to the limit """
        x_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        y_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        needs_reset = False

        if x_pos < self._scanning_logic.x_range[0]:
            x_pos = self._scanning_logic.x_range[0]
            needs_reset = True
        elif x_pos > self._scanning_logic.x_range[1]:
            x_pos = self._scanning_logic.x_range[1]
            needs_reset = True

        if y_pos < self._scanning_logic.y_range[0]:
            y_pos = self._scanning_logic.y_range[0]
            needs_reset = True
        elif y_pos > self._scanning_logic.y_range[1]:
            y_pos = self._scanning_logic.y_range[1]
            needs_reset = True

        if needs_reset:
            self.update_roi_xy(x_pos, y_pos)

    def roi_depth_bounds_check(self, roi):
        """Check if the focus cursor is oputside the allowed range after drag and set its position to the limit """
        x_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        z_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        needs_reset = False

        if x_pos < self._scanning_logic.x_range[0]:
            x_pos = self._scanning_logic.x_range[0]
            needs_reset = True
        elif x_pos > self._scanning_logic.x_range[1]:
            x_pos = self._scanning_logic.x_range[1]
            needs_reset = True

        if z_pos < self._scanning_logic.z_range[0]:
            z_pos = self._scanning_logic.z_range[0]
            needs_reset = True
        elif z_pos > self._scanning_logic.z_range[1]:
            z_pos = self._scanning_logic.z_range[1]
            needs_reset = True

        if needs_reset:
            self.update_roi_depth(x_pos, z_pos)

    def update_roi_xy(self, x=None, y=None):
        """ Adjust the xy ROI position if the value has changed.

        @param float x: real value of the current x position
        @param float y: real value of the current y position

        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not
        the actual position!
        """
        roi_x_view = self.roi_xy.pos()[0]
        roi_y_view = self.roi_xy.pos()[1]

        if x is not None:
            roi_x_view = x - self.roi_xy.size()[0] * 0.5
        if y is not None:
            roi_y_view = y - self.roi_xy.size()[1] * 0.5

        self.roi_xy.setPos([roi_x_view, roi_y_view])

    def update_roi_depth(self, x=None, z=None):
        """ Adjust the depth ROI position if the value has changed.

        @param float x: real value of the current x value
        @param float z: real value of the current z value

        Since the origin of the region of interest (ROI) is not the crosshair
        point but the lowest left point of the square, you have to shift the
        origin according to that. Therefore the position of the ROI is not
        the actual position!
        """
        roi_x_view = self.roi_depth.pos()[0]
        roi_y_view = self.roi_depth.pos()[1]

        if x is not None:
            roi_x_view = x - self.roi_depth.size()[0] * 0.5
        if z is not None:
            roi_y_view = z - self.roi_depth.size()[1] * 0.5

        self.roi_depth.setPos([roi_x_view, roi_y_view])

    def update_from_roi_xy(self, roi):
        """The user manually moved the XY ROI, adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        x_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        y_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        if x_pos < self._scanning_logic.x_range[0]:
            x_pos = self._scanning_logic.x_range[0]
        elif x_pos > self._scanning_logic.x_range[1]:
            x_pos = self._scanning_logic.x_range[1]

        if y_pos < self._scanning_logic.y_range[0]:
            y_pos = self._scanning_logic.y_range[0]
        elif y_pos > self._scanning_logic.y_range[1]:
            y_pos = self._scanning_logic.y_range[1]

        self.update_roi_depth(x=x_pos)

        self.update_slider_x(x_pos)
        self.update_slider_y(y_pos)

        self.update_input_x(x_pos)
        self.update_input_y(y_pos)

        self._scanning_logic.set_position('roixy', x=x_pos, y=y_pos)

    def update_from_roi_depth(self, roi):
        """The user manually moved the Z ROI, adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        x_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        z_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        if x_pos < self._scanning_logic.x_range[0]:
            x_pos = self._scanning_logic.x_range[0]
        elif x_pos > self._scanning_logic.x_range[1]:
            x_pos = self._scanning_logic.x_range[1]

        if z_pos < self._scanning_logic.z_range[0]:
            z_pos = self._scanning_logic.z_range[0]
        elif z_pos > self._scanning_logic.z_range[1]:
            z_pos = self._scanning_logic.z_range[1]

        self.update_roi_xy(x=x_pos)
        self.update_slider_x(x_pos)
        self.update_slider_z(z_pos)
        self.update_input_x(x_pos)
        self.update_input_z(z_pos)

        self._scanning_logic.set_position('roidepth', x=x_pos, z=z_pos)

    def update_from_key(self, x=None, y=None, z=None):
        """The user pressed a key to move the crosshair, adjust all GUI elements.

        @param float x: new x position in µm
        @param float y: new y position in µm
        @param float z: new z position in µm
        """
        if x is not None:
            self.update_roi_xy(x=x)
            self.update_roi_depth(x=x)
            self.update_slider_x(x)
            self.update_input_x(x)
        if y is not None:
            self.update_roi_xy(y=y)
            self.update_slider_y(y)
            self.update_input_y(y)
        if z is not None:
            self.update_roi_depth(z=z)
            self.update_slider_z(z)
            self.update_input_z(z)

    def update_from_input_x(self):
        """The user changed the number in the x position spin box, adjust all other GUI elements."""
        x_pos = self._mw.x_current_InputWidget.value()
        self.update_roi_xy(x=x_pos)
        self.update_roi_depth(x=x_pos)
        self.update_slider_x(x_pos)
        self._scanning_logic.set_position('xinput', x=x_pos)

    def update_from_input_y(self):
        """The user changed the number in the y position spin box, adjust all other GUI elements."""
        y_pos = self._mw.y_current_InputWidget.value()
        self.update_roi_xy(y=y_pos)
        self.update_slider_y(y_pos)
        self._scanning_logic.set_position('yinput', y=y_pos)

    def update_from_input_z(self):
        """The user changed the number in the z position spin box, adjust all other GUI elements."""
        z_pos = self._mw.z_current_InputWidget.value()
        self.update_roi_depth(z=z_pos)
        self.update_slider_z(z_pos)
        self._scanning_logic.set_position('zinput', z=z_pos)

    def update_input_x(self, x_pos):
        """ Update the displayed x-value.

        @param float x_pos: the current value of the x position in µm
        """
        # Convert x_pos to number of points for the slider:
        self._mw.x_current_InputWidget.setValue(x_pos)

    def update_input_y(self, y_pos):
        """ Update the displayed y-value.

        @param float y_pos: the current value of the y position in µm
        """
        # Convert x_pos to number of points for the slider:
        self._mw.y_current_InputWidget.setValue(y_pos)

    def update_input_z(self, z_pos):
        """ Update the displayed z-value.

        @param float z_pos: the current value of the z position in µm
        """
        # Convert x_pos to number of points for the slider:
        self._mw.z_current_InputWidget.setValue(z_pos)

    def update_from_slider_x(self, sliderValue):
        """The user moved the x position slider, adjust the other GUI elements.

        @params int sliderValue: slider postion, a quantized whole number
        """
        x_pos = self._scanning_logic.x_range[0] + sliderValue * self.slider_res
        self.update_roi_xy(x=x_pos)
        self.update_roi_depth(x=x_pos)
        self.update_input_x(x_pos)
        self._scanning_logic.set_position('xslider', x=x_pos)

    def update_from_slider_y(self, sliderValue):
        """The user moved the y position slider, adjust the other GUI elements.

        @params int sliderValue: slider postion, a quantized whole number
        """
        y_pos = self._scanning_logic.y_range[0] + sliderValue * self.slider_res
        self.update_roi_xy(y=y_pos)
        self.update_input_y(y_pos)
        self._scanning_logic.set_position('yslider', y=y_pos)

    def update_from_slider_z(self, sliderValue):
        """The user moved the z position slider, adjust the other GUI elements.

        @params int sliderValue: slider postion, a quantized whole number
        """
        z_pos = self._scanning_logic.z_range[0] + sliderValue * self.slider_res
        self.update_roi_depth(z=z_pos)
        self.update_input_z(z_pos)
        self._scanning_logic.set_position('zslider', z=z_pos)

    def update_slider_x(self, x_pos):
        """ Update the x slider when a change happens.

        @param float x_pos: x position in µm
        """
        self._mw.x_SliderWidget.setValue((x_pos - self._scanning_logic.x_range[0]) / self.slider_res)

    def update_slider_y(self, y_pos):
        """ Update the y slider when a change happens.

        @param float y_pos: x yosition in µm
        """
        self._mw.y_SliderWidget.setValue((y_pos - self._scanning_logic.y_range[0]) / self.slider_res)

    def update_slider_z(self, z_pos):
        """ Update the z slider when a change happens.

        @param float z_pos: z position in µm
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
        self._scanning_logic.image_x_range = [self._mw.x_min_InputWidget.value(), self._mw.x_max_InputWidget.value()]

    def change_y_image_range(self):
        """ Adjust the image range for y in the logic.
        """
        self._scanning_logic.image_y_range = [self._mw.y_min_InputWidget.value(), self._mw.y_max_InputWidget.value()]

    def change_z_image_range(self):
        """ Adjust the image range for z in the logic. """
        self._scanning_logic.image_z_range = [self._mw.z_min_InputWidget.value(), self._mw.z_max_InputWidget.value()]

    def use_tiltcorrection_clicked(self, e):
        """ """
        self._scanning_logic.TiltCorrection = e
        self._scanning_logic.clicked_TiltCorrection(e)

    def calculate_tiltcorrection_clicked(self):
        """ """
        self._scanning_logic.calc_tilt_correction()

    def set_tiltpoint_01_clicked(self):
        """Set the crosshair position as the first reference point for tilt correction calculation."""
        self._scanning_logic.set_tilt_point1()
        self._mw.tilt_01_x_pos_doubleSpinBox.setValue(self._scanning_logic.point1[0])
        self._mw.tilt_01_y_pos_doubleSpinBox.setValue(self._scanning_logic.point1[1])
        self._mw.tilt_01_z_pos_doubleSpinBox.setValue(self._scanning_logic.point1[2])

    def set_tiltpoint_02_clicked(self):
        """Set the crosshair position as the second reference point for tilt correction calculation."""
        self._scanning_logic.set_tilt_point2()
        self._mw.tilt_02_x_pos_doubleSpinBox.setValue(self._scanning_logic.point2[0])
        self._mw.tilt_02_y_pos_doubleSpinBox.setValue(self._scanning_logic.point2[1])
        self._mw.tilt_02_z_pos_doubleSpinBox.setValue(self._scanning_logic.point2[2])

    def set_tiltpoint_03_clicked(self):
        """Set the crosshair position as the third reference point for tilt correction calculation."""
        self._scanning_logic.set_tilt_point3()
        self._mw.tilt_03_x_pos_doubleSpinBox.setValue(self._scanning_logic.point3[0])
        self._mw.tilt_03_y_pos_doubleSpinBox.setValue(self._scanning_logic.point3[1])
        self._mw.tilt_03_z_pos_doubleSpinBox.setValue(self._scanning_logic.point3[2])

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

    def rotate_xy_image_clockwise(self):
        """Rotate the xy image clockwise.

        Actually you just roll the orienation array and that changes the
        leading number of it and that will cause another rotation in the
        refresh_xy_image method.
        """
        self.xy_image_orientation = np.roll(self.xy_image_orientation, 1)
        self.refresh_xy_image()

    def rotate_xy_image_anticlockwise(self):
        """Rotate the xy image anti-clockwise.

        Actually you just roll the orienation array and that changes the
        leading number of it and that will cause another rotation in the
        refresh_xy_image method.
        """
        self.xy_image_orientation = np.roll(self.xy_image_orientation, -1)
        self.refresh_xy_image()

    def rotate_depth_image_clockwise(self):
        """Rotate the depth image clockwise.

        Actually you just roll the orienation array and that changes the
        leading number of it and that will cause another rotation in the
        refresh_depth_image method.
        """
        self.depth_image_orientation = np.roll(self.depth_image_orientation, 1)
        self.refresh_depth_image()

    def rotate_depth_image_anticlockwise(self):
        """Rotate the depth image anti-clockwise.

        Actually you just roll the orienation array and that changes the
        leading number of it and that will cause another rotation in the
        refresh_depth_image method.
        """
        self.depth_image_orientation = np.roll(self.depth_image_orientation, -1)
        self.refresh_depth_image()

    def refresh_xy_image(self):
        """ Update the current XY image from the logic.

        Everytime the scanner is scanning a line in xy the
        image is rebuild and updated in the GUI.
        """
        self.xy_image.getViewBox().updateAutoRange()
        self.adjust_aspect_roi_xy()

        xy_image_data = np.rot90(self._scanning_logic.xy_image[:, :, 3].transpose(), self.xy_image_orientation[0])

        cb_range = self.get_xy_cb_range()

        # Now update image with new color scale, and update colorbar
        self.xy_image.setImage(image=xy_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_xy_colorbar()

        # Unlock state widget if scan is finished
        if self._scanning_logic.getState() != 'locked':
            self.enable_scan_actions()

    def refresh_depth_image(self):
        """ Update the current Depth image from the logic.

        Everytime the scanner is scanning a line in depth the
        image is rebuild and updated in the GUI.
        """

        self.depth_image.getViewBox().enableAutoRange()
        self.adjust_aspect_roi_depth()

        depth_image_data = np.rot90(self._scanning_logic.depth_image[:, :, 3].transpose(), self.depth_image_orientation[0])
        cb_range = self.get_depth_cb_range()

        # Now update image with new color scale, and update colorbar
        self.depth_image.setImage(image=depth_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_depth_colorbar()

        # Unlock state widget if scan is finished
        if self._scanning_logic.getState() != 'locked':
            self.enable_scan_actions()

    def refresh_refocus_image(self):
        """Refreshes the xy image, the crosshair and the colorbar. """
        ##########
        # Updating the xy optimizer image with color scaling based only on nonzero data
        xy_optimizer_image = self._optimizer_logic.xy_refocus_image[:, :, 3].transpose()

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
        self.depth_refocus_image.setData(self._optimizer_logic._zimage_Z_values, self._optimizer_logic.z_refocus_line)
        self.depth_refocus_fit_image.setData(self._optimizer_logic._fit_zimage_Z_values, self._optimizer_logic.z_fit_data)
        ##########
        # Set the optimized position label
        self._mw.refocus_position_label.setText(
            '({0:.3f}, {1:.3f}, {2:.3f})'.format(
                self._optimizer_logic.optim_pos_x,
                self._optimizer_logic.optim_pos_y,
                self._optimizer_logic.optim_pos_z
            )
        )

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

        xMin = self._scanning_logic.image_x_range[0]
        xMax = self._scanning_logic.image_x_range[1]
        yMin = self._scanning_logic.image_y_range[0]
        yMax = self._scanning_logic.image_y_range[1]

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
        self.adjust_aspect_roi_xy()

        xy_viewbox.updateAutoRange()
        xy_viewbox.updateViewRange()

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

        xMin = self._scanning_logic.image_x_range[0]
        xMax = self._scanning_logic.image_x_range[1]
        zMin = self._scanning_logic.image_z_range[0]
        zMax = self._scanning_logic.image_z_range[1]

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
        self.adjust_aspect_roi_depth()

        depth_viewbox.updateAutoRange()
        depth_viewbox.updateViewRange()

    def put_cursor_in_xy_scan(self):
        """Put the xy crosshair back if it is outside of the visible range. """
        view_x_min = self._scanning_logic.image_x_range[0]
        view_x_max = self._scanning_logic.image_x_range[1]
        view_y_min = self._scanning_logic.image_y_range[0]
        view_y_max = self._scanning_logic.image_y_range[1]

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
        view_x_min = self._scanning_logic.image_x_range[0]
        view_x_max = self._scanning_logic.image_x_range[1]
        view_z_min = self._scanning_logic.image_z_range[0]
        view_z_max = self._scanning_logic.image_z_range[1]

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

    def adjust_aspect_roi_xy(self):
        """ Keep the aspect ratio of the ROI also during the zoom the same.

        @param object viewbox: pyqtgraph.ViewBox object, which contains the
                               view information about the display.
        """
        viewbox = self.xy_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_y_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]

        new_size_x_roi = current_x_view_range / 20
        new_size_y_roi = current_y_view_range / 20

        old_size_x_roi = self.roi_xy.size()[0]
        old_size_y_roi = self.roi_xy.size()[1]

        diff_size_x_roi = (old_size_x_roi - new_size_x_roi) * 0.5
        diff_size_y_roi = (old_size_y_roi - new_size_y_roi) * 0.5

        # Here it is really necessary not to update, otherwise you will
        # calculate the position of the roi in a wrong way.
        self.roi_xy.setSize([new_size_x_roi, new_size_y_roi], update=False)
        pos = self.roi_xy.pos()
        self.roi_xy.setPos([pos[0] + diff_size_x_roi, pos[1] + diff_size_y_roi], update=True)

    def adjust_aspect_roi_depth(self, viewbox=None):
        """ Keep the aspect ratio of the ROI also during the zoom the same.

        @param object viewbox: pyqtgraph.ViewBox object, which contains the
                               view information about the display.

        """
        viewbox = self.depth_image.getViewBox()
        current_x_view_range = viewbox.viewRange()[0][1] - viewbox.viewRange()[0][0]
        current_z_view_range = viewbox.viewRange()[1][1] - viewbox.viewRange()[1][0]

        new_size_x_roi = current_x_view_range / 20
        new_size_z_roi = current_z_view_range / 20

        if self.fixed_aspect_ratio_depth:
            if new_size_x_roi > new_size_z_roi:
                new_size_z_roi = new_size_x_roi
            else:
                new_size_x_roi = new_size_z_roi

        old_size_x_roi = self.roi_depth.size()[0]
        old_size_z_roi = self.roi_depth.size()[1]

        diff_size_x_roi = (old_size_x_roi - new_size_x_roi) * 0.5
        diff_size_z_roi = (old_size_z_roi - new_size_z_roi) * 0.5

        # Here it is really necessary not to update, otherwise you will
        # calculate the position of the roi in a wrong way.
        self.roi_depth.setSize([new_size_x_roi, new_size_z_roi], update=False)
        pos = self.roi_depth.pos()
        self.roi_depth.setPos([pos[0] + diff_size_x_roi, pos[1] + diff_size_z_roi], update=True)

    def save_xy_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal pic."""
        self._scanning_logic.save_xy_data()

    def save_xy_scan_image(self):
        """ Save the image and according to that the data.

        Here only the path to the module is taken from the save logic, but the
        picture save algorithm is situated here in confocal, since it is a very
        specific task to save the used PlotObject.
        """

        filepath = self._save_logic.get_path_for_module(module_name='Confocal')
        filename = filepath + os.sep + time.strftime('%Y%m%d-%H%M-%S_confocal_xy_scan_image')

        self._mw.xy_ViewWidget.plotItem.removeItem(self.roi_xy)
        self._mw.xy_ViewWidget.plotItem.removeItem(self.hline_xy)
        self._mw.xy_ViewWidget.plotItem.removeItem(self.vline_xy)

        exporter = pg.exporters.SVGExporter(self._mw.xy_ViewWidget.plotItem)
        exporter.export(filename + '.svg')

        if self._sd.savePNG_checkBox.isChecked():
            exporter = pg.exporters.ImageExporter(self._mw.xy_ViewWidget.plotItem)
            exporter.export(filename + '.png')

        if self._sd.save_purePNG_checkBox.isChecked():
            self.xy_image.save(filename + '_raw.png')

        self._mw.xy_ViewWidget.plotItem.addItem(self.roi_xy)
        self._mw.xy_ViewWidget.plotItem.addItem(self.hline_xy)
        self._mw.xy_ViewWidget.plotItem.addItem(self.vline_xy)

        self.save_xy_scan_data()

    def save_depth_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal pic."""
        self._scanning_logic.save_depth_data()

    def save_depth_scan_image(self):
        """ Save the image and according to that the data.

        Here only the path to the module is taken from the save logic, but the
        picture save algorithm is situated here in confocal, since it is a very
        specific task to save the used PlotObject.
        """

        filepath = self._save_logic.get_path_for_module(module_name='Confocal')
        filename = filepath + os.sep + time.strftime('%Y%m%d-%H%M-%S_confocal_depth_scan_image')

        self._mw.depth_ViewWidget.plotItem.removeItem(self.roi_depth)
        self._mw.depth_ViewWidget.plotItem.removeItem(self.hline_depth)
        self._mw.depth_ViewWidget.plotItem.removeItem(self.vline_depth)

        exporter = pg.exporters.SVGExporter(self._mw.depth_ViewWidget.plotItem)
        exporter.export(filename + '.svg')

        if self._sd.savePNG_checkBox.isChecked():
            exporter = pg.exporters.ImageExporter(self._mw.depth_ViewWidget.plotItem)
            exporter.export(filename + '.png')

        if self._sd.save_purePNG_checkBox.isChecked():
            self.depth_image.save(filename + '_raw.png')

        self._mw.depth_ViewWidget.plotItem.addItem(self.roi_depth)
        self._mw.depth_ViewWidget.plotItem.addItem(self.hline_depth)
        self._mw.depth_ViewWidget.plotItem.addItem(self.vline_depth)

        self.save_depth_scan_data()

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

        # re-dock any floating dock widgets
        self._mw.xy_scan_dockWidget.setFloating(False)
        self._mw.scan_control_dockWidget.setFloating(False)
        self._mw.depth_scan_dockWidget.setFloating(False)
        self._mw.optimizer_dockWidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.xy_scan_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.scan_control_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.depth_scan_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.optimizer_dockWidget)

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
            self._mw.xy_ViewWidget.setDragMode(self._mw.xy_ViewWidget.RubberBandDrag)
            self._mw.depth_ViewWidget.setDragMode(self._mw.xy_ViewWidget.RubberBandDrag)
        else:
            self._mw.xy_ViewWidget.setDragMode(self._mw.xy_ViewWidget.NoDrag)
            self._mw.depth_ViewWidget.setDragMode(self._mw.xy_ViewWidget.NoDrag)

    def xy_scan_start_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was pressed.

        @param QMouseEvent event: Mouse Event object which contains all the
                                  information at the time the event was emitted
        """
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        pos = self.xy_image.getViewBox().mapSceneToView(event.posF())

        # store the initial mouse position in a class variable
        self._current_xy_zoom_start = [pos.x(), pos.y()]
        event.accept()

    def xy_scan_end_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was released.

        @param QEvent event:
        """
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        # get the ViewBox which is also responsible for the xy_image
        viewbox = self.xy_image.getViewBox()

        # Map the mouse position in the whole ViewWidget to the coordinate
        # system of the ViewBox, which also includes the 2D graph:
        pos = viewbox.mapSceneToView(event.posF())
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

    def reset_xy_imagerange(self, viewbox):
        """ Reset the imagerange if autorange was pressed.

        Take the image range values directly from the scanned image and set
        them as the current image ranges. This method is only applied if the
        zoom button is pressed.
        """
        if (viewbox.state['autoRange'][0] is True) and (self._mw.action_zoom.isChecked()):
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

    def depth_scan_start_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was pressed.

        @param QMouseEvent event: Mouse Event object which contains all the
                                  information at the time the event was emitted
        """
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        pos = self.depth_image.getViewBox().mapSceneToView(event.posF())

        # store the initial mouse position in a class variable
        self._current_depth_zoom_start = [pos.x(), pos.y()]
        event.accept()

    def depth_scan_end_zoom_point(self, event):
        """ Get the mouse coordinates if the mouse button was released.

        @param QEvent event:
        """
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_zoom.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        # get the ViewBox which is also responsible for the depth_image
        viewbox = self.depth_image.getViewBox()

        # Map the mouse position in the whole ViewWidget to the coordinate
        # system of the ViewBox, which also includes the 2D graph:
        pos = viewbox.mapSceneToView(event.posF())
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

    def reset_depth_imagerange(self, viewbox):
        """ Reset the imagerange if autorange was pressed.

        Take the image range values directly from the scanned image and set
        them as the current image ranges. This method is only applied if the
        zoom button is pressed.
        """
        if (viewbox.state['autoRange'][0] is True) and (self._mw.action_zoom.isChecked()):
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

    def _set_scan_icons(self):
        """ Set the scan icons depending on whether loop-scan is active or not
        """

        if self._scanning_logic.permanent_scan:
            self._mw.action_scan_xy_start.setIcon(self._scan_xy_loop_icon)
            self._mw.action_scan_depth_start.setIcon(self._scan_depth_loop_icon)
        else:
            self._mw.action_scan_xy_start.setIcon(self._scan_xy_single_icon)
            self._mw.action_scan_depth_start.setIcon(self._scan_depth_single_icon)
