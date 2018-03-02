# -*- coding: utf-8 -*-

"""
This file contains the GUI for magnet control.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import datetime
import numpy as np
import os
import pyqtgraph as pg
import pyqtgraph.exporters
from qtpy import uic

from core.module import Connector, StatusVar
from core.util.units import get_unit_prefix_dict
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from qtpy import QtCore
from qtpy import QtWidgets
from qtwidgets.scientific_spinbox import ScienDSpinBox


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
        # interest, where 0 is the lowest value and 1 is the highest:
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

class MagnetMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_magnet_gui.ui')

        # Load it
        super(MagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class MagnetSettingsWindow(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_magnet_settings.ui')

        # Load it
        super(MagnetSettingsWindow, self).__init__()

        uic.loadUi(ui_file, self)


class MagnetGui(GUIBase):
    """ Main GUI for the magnet. """

    _modclass = 'MagnetGui'
    _modtype = 'gui'

    ## declare connectors
    magnetlogic1 = Connector(interface='MagnetLogic')
    savelogic = Connector(interface='SaveLogic')

    # status var
    _alignment_2d_cb_label = StatusVar('alignment_2d_cb_GraphicsView_text', 'Fluorescence')
    _alignment_2d_cb_units = StatusVar('alignment_2d_cb_GraphicsView_units', 'counts/s')


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._continue_2d_fluorescence_alignment = False


    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._magnet_logic = self.get_connector('magnetlogic1')
        self._save_logic = self.get_connector('savelogic')

        self._mw = MagnetMainWindow()

        # create all the needed control elements. They will manage the
        # connection with each other themselves. Note some buttons are also
        # connected within these functions because they have to be placed at
        # first in the GUI Layout, otherwise the signals will not react.
        self._create_axis_pos_disp()
        self._create_move_rel_control()
        self._create_move_abs_control()

        self._create_meas_type_RadioButtons()

        # Configuring the dock widgets
        # Use the class 'MagnetMainWindow' to create the GUI window

        axis_list = list(self._magnet_logic.get_hardware_constraints())
        self._mw.align_2d_axis0_name_ComboBox.clear()
        self._mw.align_2d_axis0_name_ComboBox.addItems(axis_list)

        self._mw.align_2d_axis1_name_ComboBox.clear()
        self._mw.align_2d_axis1_name_ComboBox.addItems(axis_list)

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
       # self._mw.tabifyDockWidget(self._mw.curr_pos_DockWidget, self._mw.move_rel_DockWidget)
       # self._mw.tabifyDockWidget(self._mw.curr_pos_DockWidget, self._mw.move_abs_DockWidget)
       # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.curr_pos_DockWidget)
       # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.move_rel_DockWidget)
       # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(3), self._mw.move_abs_DockWidget)
        self.set_default_view_main_window()
        raw_data_2d = self._magnet_logic.get_2d_data_matrix()

        # Set initial position for the crosshair, default is the middle of the
        # screen:
        ini_pos_x_crosshair = len(raw_data_2d) / 2
        ini_pos_y_crosshair = len(raw_data_2d) / 2

        # After a movement command, the device should not block the program, at
        # least on the hardware level. That meant that the dll (or whatever
        # protocol is used to access the hardware) can receive a command during
        # an ongoing action. That is of course controller specific, but in
        # general should it should be possible (unless the controller was
        # written by someone who has no clue what he is doing). Eventually with
        # that you have the possibility of stopping an ongoing movement!
        self._interactive_mode = True
        self._activate_magnet_settings()

        # connect the actions of the toolbar:
        self._mw.magnet_settings_Action.triggered.connect(self.open_magnet_settings)
        self._mw.default_view_Action.triggered.connect(self.set_default_view_main_window)

        curr_pos = self.update_pos()
        # update the values also of the absolute movement display:
        for axis_label in curr_pos:
            dspinbox_move_abs_ref = self.get_ref_move_abs_ScienDSpinBox(axis_label)
            dspinbox_move_abs_ref.setValue(curr_pos[axis_label])

        self._magnet_logic.sigPosChanged.connect(self.update_pos)

        # Connect alignment GUI elements:

        self._magnet_logic.sigMeasurementFinished.connect(self._change_display_to_stop_2d_alignment)



        self._mw.align_2d_axis0_name_ComboBox.currentIndexChanged.connect(self._update_limits_axis0)
        self._mw.align_2d_axis1_name_ComboBox.currentIndexChanged.connect(self._update_limits_axis1)
        self._mw.align_2d_axis0_set_vel_CheckBox.stateChanged.connect(self._set_vel_display_axis0)
        self._mw.align_2d_axis1_set_vel_CheckBox.stateChanged.connect(self._set_vel_display_axis1)


        self._mw.alignment_2d_cb_min_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_cb_max_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_cb_low_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_cb_high_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)

        self._update_limits_axis0()
        self._update_limits_axis1()
        self._set_vel_display_axis0()
        self._set_vel_display_axis1()

        self._2d_alignment_ImageItem = pg.ImageItem(
            image=self._magnet_logic.get_2d_data_matrix())
          #  axisOrder='row-major')

        axis0, axis1 = self._magnet_logic.get_2d_axis_arrays()
        self._2d_alignment_ImageItem.setRect(QtCore.QRectF(axis0[0],
                                                           axis1[0],
                                                           axis0[-1]-axis0[0],
                                                           axis1[-1]-axis1[0],))

        self._mw.alignment_2d_GraphicsView.addItem(self._2d_alignment_ImageItem)

        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()

        self._2d_alignment_ImageItem.setLookupTable(my_colors.lut)



        # Configuration of Colorbar:
        self._2d_alignment_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        self._mw.alignment_2d_cb_GraphicsView.addItem(self._2d_alignment_cb)
        self._mw.alignment_2d_cb_GraphicsView.hideAxis('bottom')
        self._mw.alignment_2d_cb_GraphicsView.hideAxis('left')

        self._mw.alignment_2d_cb_GraphicsView.addItem(self._2d_alignment_cb)
        self.roi_magnet = CrossROI(
            # [
            #     ini_pos_x_crosshair - len(arr01) / 40,
            #     ini_pos_y_crosshair - len(arr01) / 40
            # ],
            [
                ini_pos_x_crosshair - axis0[0],
                ini_pos_y_crosshair - axis1[1]
            ],
            # [len(arr01) / 20, len(arr01) / 20],
            [0.01, 0.01],
            pen={'color': "F0F", 'width': 1},
            removable=True
        )

        self._mw.alignment_2d_GraphicsView.addItem(self.roi_magnet)

        # create horizontal and vertical line as a crosshair in xy image:
        self.hline_magnet = CrossLine(pos=self.roi_magnet.pos() + self.roi_magnet.size() * 0.5,
                                  angle=0, pen={'color': palette.green, 'width': 1})
        self.vline_magnet = CrossLine(pos=self.roi_magnet.pos() + self.roi_magnet.size() * 0.5,
                                  angle=90, pen={'color': palette.green, 'width': 1})

        # connect the change of a region with the adjustment of the crosshair:
        self.roi_magnet.sigRegionChanged.connect(self.hline_magnet.adjust)
        self.roi_magnet.sigRegionChanged.connect(self.vline_magnet.adjust)
        self.roi_magnet.sigUserRegionUpdate.connect(self.update_from_roi_magnet)




        # add the configured crosshair to the magnet Widget
        self._mw.alignment_2d_GraphicsView.addItem(self.hline_magnet)
        self._mw.alignment_2d_GraphicsView.addItem(self.vline_magnet)

        self._mw.alignment_2d_cb_GraphicsView.setLabel('right',
            self._alignment_2d_cb_label,
            units=self._alignment_2d_cb_units)


        #FIXME: that should be actually set in the logic
        if 'measurement_type' in self._statusVariables:
            self.measurement_type = self._statusVariables['measurement_type']
        else:
            self.measurement_type = 'fluorescence'

        self._magnet_logic.sig2DAxisChanged.connect(self._update_2d_graph_axis)
        self._magnet_logic.sig2DMatrixChanged.connect(self._update_2d_graph_data)

        # Connect the buttons and inputs for the odmr colorbar
        self._mw.alignment_2d_manual_RadioButton.clicked.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_centiles_RadioButton.clicked.connect(self._update_2d_graph_data)

        self._update_2d_graph_data()
        self._update_2d_graph_cb()


        # Add save file tag input box
        self._mw.alignment_2d_nametag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.alignment_2d_nametag_LineEdit.setMaximumWidth(200)
        self._mw.alignment_2d_nametag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                                          'added to the filename.')

        self._mw.save_ToolBar.addWidget(self._mw.alignment_2d_nametag_LineEdit)
        self._mw.save_Action.triggered.connect(self.save_2d_plots_and_data)

        self._mw.run_stop_2d_alignment_Action.triggered.connect(self.run_stop_2d_alignment)
        self._mw.continue_2d_alignment_Action.triggered.connect(self.continue_stop_2d_alignment)

        # connect the signals:
        # --------------------

        # relative movement:

        constraints=self._magnet_logic.get_hardware_constraints()

        for axis_label in list(constraints):
            self.get_ref_move_rel_ScienDSpinBox(axis_label).setValue(self._magnet_logic.move_rel_dict[axis_label])
            self.get_ref_move_rel_ScienDSpinBox(axis_label).valueChanged.connect(self.move_rel_para_changed)
            #print('self.get_ref_move_rel_ScienDSpinBox('+axis_label+').valueChanged.connect(lambda: self.move_rel_changed('+axis_label+'))')



        # General 2d alignment:
        index = self._mw.align_2d_axis0_name_ComboBox.findText(self._magnet_logic.align_2d_axis0_name)
        self._mw.align_2d_axis0_name_ComboBox.setCurrentIndex(index)
        self._mw.align_2d_axis0_name_ComboBox.currentIndexChanged.connect(self.align_2d_axis0_name_changed)
        self._mw.align_2d_axis0_range_DSpinBox.setValue(self._magnet_logic.align_2d_axis0_range)
        self._mw.align_2d_axis0_range_DSpinBox.valueChanged.connect(self.align_2d_axis0_range_changed)
        self._mw.align_2d_axis0_range_DSpinBox.valueChanged.connect(self.update_roi_from_range)
        self._mw.align_2d_axis0_step_DSpinBox.setValue(self._magnet_logic.align_2d_axis0_step)
        self._mw.align_2d_axis0_step_DSpinBox.valueChanged.connect(self.align_2d_axis0_step_changed)
        self._mw.align_2d_axis0_vel_DSpinBox.setValue(self._magnet_logic.align_2d_axis0_vel)
        self._mw.align_2d_axis0_vel_DSpinBox.valueChanged.connect(self.align_2d_axis0_vel_changed)

        index = self._mw.align_2d_axis1_name_ComboBox.findText(self._magnet_logic.align_2d_axis1_name)
        self._mw.align_2d_axis1_name_ComboBox.setCurrentIndex(index)
        self._mw.align_2d_axis1_name_ComboBox.currentIndexChanged.connect(self.align_2d_axis1_name_changed)
        self._mw.align_2d_axis1_range_DSpinBox.setValue(self._magnet_logic.align_2d_axis1_range)
        self._mw.align_2d_axis1_range_DSpinBox.valueChanged.connect(self.align_2d_axis1_range_changed)
        self._mw.align_2d_axis1_range_DSpinBox.valueChanged.connect(self.update_roi_from_range)
        self._mw.align_2d_axis1_step_DSpinBox.setValue(self._magnet_logic.align_2d_axis1_step)
        self._mw.align_2d_axis1_step_DSpinBox.valueChanged.connect(self.align_2d_axis1_step_changed)
        self._mw.align_2d_axis1_vel_DSpinBox.setValue(self._magnet_logic.align_2d_axis1_vel)
        self._mw.align_2d_axis1_vel_DSpinBox.valueChanged.connect(self.align_2d_axis1_vel_changed)


        # for fluorescence alignment:
        self._mw.align_2d_fluorescence_optimize_freq_SpinBox.setValue(self._magnet_logic.get_optimize_pos_freq())
        self._mw.align_2d_fluorescence_integrationtime_DSpinBox.setValue(self._magnet_logic.get_fluorescence_integration_time())
        self._mw.align_2d_fluorescence_optimize_freq_SpinBox.valueChanged.connect(self.optimize_pos_freq_changed)
        self._mw.align_2d_fluorescence_integrationtime_DSpinBox.valueChanged.connect(self.fluorescence_integration_time_changed)

        # for odmr alignment:
        self._mw.meas_type_fluorescence_RadioButton.toggled.connect(self.set_measurement_type)
        self._mw.meas_type_odmr_RadioButton.toggled.connect(self.set_measurement_type)
        self._mw.meas_type_nuclear_spin_RadioButton.toggled.connect(self.set_measurement_type)
        self.set_measurement_type()

        # for odmr alignment:
        self._mw.align_2d_odmr_low_fit_func_ComboBox.clear()
        self._mw.align_2d_odmr_low_fit_func_ComboBox.addItems(self._magnet_logic.odmr_2d_low_fitfunction_list)
        self._mw.align_2d_odmr_low_fit_func_ComboBox.setCurrentIndex(1)
        self._mw.align_2d_odmr_low_center_freq_DSpinBox.setValue(self._magnet_logic.odmr_2d_low_center_freq)
        self._mw.align_2d_odmr_low_range_freq_DSpinBox.setValue(self._magnet_logic.odmr_2d_low_range_freq)
        self._mw.align_2d_odmr_low_step_freq_DSpinBox.setValue(self._magnet_logic.odmr_2d_low_step_freq)
        self._mw.align_2d_odmr_low_power_DSpinBox.setValue(self._magnet_logic.odmr_2d_low_power)
        self._mw.align_2d_odmr_low_runtime_DSpinBox.setValue(self._magnet_logic.odmr_2d_low_runtime)

        self._mw.align_2d_odmr_high_fit_func_ComboBox.clear()
        self._mw.align_2d_odmr_high_fit_func_ComboBox.addItems(self._magnet_logic.odmr_2d_high_fitfunction_list)
        self._mw.align_2d_odmr_high_fit_func_ComboBox.setCurrentIndex(1)
        self._mw.align_2d_odmr_high_center_freq_DSpinBox.setValue(self._magnet_logic.odmr_2d_high_center_freq)
        self._mw.align_2d_odmr_high_range_freq_DSpinBox.setValue(self._magnet_logic.odmr_2d_high_range_freq)
        self._mw.align_2d_odmr_high_step_freq_DSpinBox.setValue(self._magnet_logic.odmr_2d_high_step_freq)
        self._mw.align_2d_odmr_high_power_DSpinBox.setValue(self._magnet_logic.odmr_2d_high_power)
        self._mw.align_2d_odmr_high_runtime_DSpinBox.setValue(self._magnet_logic.odmr_2d_high_runtime)

        self._mw.align_2d_odmr_save_after_measure_CheckBox.setChecked(self._magnet_logic.odmr_2d_save_after_measure)

        self._mw.odmr_2d_single_trans_CheckBox.stateChanged.connect(self._odmr_single_trans_alignment_changed)

        # peak shift for odmr:
        self._mw.align_2d_axis0_shift_DSpinBox.setValue(self._magnet_logic.odmr_2d_peak_axis0_move_ratio/1e12)
        self._mw.align_2d_axis1_shift_DSpinBox.setValue(self._magnet_logic.odmr_2d_peak_axis1_move_ratio/1e12)



        # for single shot alignment of a nuclear spin:
        self._mw.align_2d_nuclear_rabi_periode_DSpinBox.setValue(self._magnet_logic.nuclear_2d_rabi_periode)
        self._mw.align_2d_nuclear_mw_freq_DSpinBox.setValue(self._magnet_logic.nuclear_2d_mw_freq)
        self._mw.align_2d_nuclear_mw_channel_SpinBox.setValue(self._magnet_logic.nuclear_2d_mw_channel)
        self._mw.align_2d_nuclear_mw_power_DSpinBox.setValue(self._magnet_logic.nuclear_2d_mw_power)
        self._mw.align_2d_nuclear_laser_time_DSpinBox.setValue(self._magnet_logic.nuclear_2d_laser_time)
        self._mw.align_2d_nuclear_laser_channel_SpinBox.setValue(self._magnet_logic.nuclear_2d_laser_channel)
        self._mw.align_2d_nuclear_detect_channel_SpinBox.setValue(self._magnet_logic.nuclear_2d_detect_channel)
        self._mw.align_2d_nuclear_idle_time_DSpinBox.setValue(self._magnet_logic.nuclear_2d_idle_time)
        self._mw.align_2d_nuclear_reps_within_ssr_SpinBox.setValue(self._magnet_logic.nuclear_2d_reps_within_ssr)
        self._mw.align_2d_nuclear_num_of_ssr_SpinBox.setValue(self._magnet_logic.nuclear_2d_num_ssr)

        # process signals from magnet_logic

        self._magnet_logic.sigMoveRelChanged.connect(self.update_move_rel_para)

        self._magnet_logic.sig2DAxis0NameChanged.connect(self.update_align_2d_axis0_name)
        self._magnet_logic.sig2DAxis0RangeChanged.connect(self.update_align_2d_axis0_range)
        self._magnet_logic.sig2DAxis0StepChanged.connect(self.update_align_2d_axis0_step)
        self._magnet_logic.sig2DAxis0VelChanged.connect(self.update_align_2d_axis0_vel)

        self._magnet_logic.sig2DAxis1NameChanged.connect(self.update_align_2d_axis1_name)
        self._magnet_logic.sig2DAxis1RangeChanged.connect(self.update_align_2d_axis1_range)
        self._magnet_logic.sig2DAxis1StepChanged.connect(self.update_align_2d_axis1_step)
        self._magnet_logic.sig2DAxis1VelChanged.connect(self.update_align_2d_axis1_vel)

        self._magnet_logic.sigOptPosFreqChanged.connect(self.update_optimize_pos_freq)
        self._magnet_logic.sigFluoIntTimeChanged.connect(self.update_fluorescence_integration_time)


        return 0


    def _activate_magnet_settings(self):
        """ Activate magnet settings.
        """
        self._ms = MagnetSettingsWindow()
        # default config is normal_mode
        self._ms.normal_mode_checkBox.setChecked(True)
        self._ms.z_mode_checkBox.setChecked(False)
        # make sure the buttons are exclusively checked
        self._ms.normal_mode_checkBox.stateChanged.connect(self.trig_wrapper_normal_mode)
        self._ms.z_mode_checkBox.stateChanged.connect(self.trig_wrapper_z_mode)

        #self._ms.z_mode_checkBox.stateChanged.connect(self._ms.normal_mode_checkBox.toggle)
        self._ms.accepted.connect(self.update_magnet_settings)
        self._ms.rejected.connect(self.keep_former_magnet_settings)
        self._ms.ButtonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_magnet_settings)

        self.keep_former_magnet_settings()



    def trig_wrapper_normal_mode(self):
        if not self._ms.normal_mode_checkBox.isChecked() and not self._ms.z_mode_checkBox.isChecked():
            self._ms.z_mode_checkBox.toggle()
        elif self._ms.normal_mode_checkBox.isChecked() and self._ms.z_mode_checkBox.isChecked():
            self._ms.z_mode_checkBox.toggle()

    def trig_wrapper_z_mode(self):
        if not self._ms.normal_mode_checkBox.isChecked() and not self._ms.z_mode_checkBox.isChecked():
            self._ms.normal_mode_checkBox.toggle()
        elif self._ms.normal_mode_checkBox.isChecked() and self._ms.z_mode_checkBox.isChecked():
            self._ms.normal_mode_checkBox.toggle()




    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._statusVariables['measurement_type'] = self.measurement_type
        self._alignment_2d_cb_label =  self._mw.alignment_2d_cb_GraphicsView.plotItem.axes['right']['item'].labelText
        self._alignment_2d_cb_units = self._mw.alignment_2d_cb_GraphicsView.plotItem.axes['right']['item'].labelUnits


        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def set_default_view_main_window(self):
        """ Establish the default dock Widget configuration. """

        # connect all widgets to the main Window
        self._mw.curr_pos_DockWidget.setFloating(False)
        self._mw.move_rel_DockWidget.setFloating(False)
        self._mw.move_abs_DockWidget.setFloating(False)
        self._mw.alignment_DockWidget.setFloating(False)

        # QtCore.Qt.LeftDockWidgetArea        0x1
        # QtCore.Qt.RightDockWidgetArea       0x2
        # QtCore.Qt.TopDockWidgetArea         0x4
        # QtCore.Qt.BottomDockWidgetArea      0x8
        # QtCore.Qt.AllDockWidgetAreas        DockWidgetArea_Mask
        # QtCore.Qt.NoDockWidgetArea          0

        # align the widget
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.curr_pos_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.move_rel_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.move_abs_DockWidget)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2),
                               self._mw.alignment_DockWidget)

    def open_magnet_settings(self):
        """ This method opens the settings menu. """
        self._ms.exec_()

    def update_magnet_settings(self):
        """ Apply the set configuration in the Settings Window. """

        if self._ms.interactive_mode_CheckBox.isChecked():
            self._interactive_mode = True
        else:
            self._interactive_mode = False
        if self._ms.z_mode_checkBox.isChecked() and not self._ms.normal_mode_checkBox.isChecked():
            self.log.warning("dum dum")

        if self._ms.normal_mode_checkBox.isChecked() and not self._ms.z_mode_checkBox.isChecked():
            self.log.warning("dam dam")


        if self._ms.interactive_mode_CheckBox.isChecked():
            self._interactive_mode = True
        else:
            self._interactive_mode = False
        if self._ms.z_mode_checkBox.isChecked():
            self._z_mode = True
            self._magnet_logic._magnet_device.mode = 'z_mode'
        else:
            self._z_mode = False
            self._magnet_logic._magnet_device.mode = 'normal_mode'

        if self._ms.normal_mode_checkBox.isChecked():
            self._normal_mode = True
            self._magnet_logic._magnet_device.mode = 'normal_mode'
        else:
            self._normal_mode = False
            self._magnet_logic._magnet_device.mode = 'z_mode'

    def keep_former_magnet_settings(self):

        self._ms.interactive_mode_CheckBox.setChecked(self._interactive_mode)

    def _create_meas_type_RadioButtons(self):
        """ Create the measurement Buttons for the desired measurements:

        @return:
        """

        self._mw.alignment_2d_ButtonGroup = QtWidgets.QButtonGroup(self._mw)

        self._mw.meas_type_fluorescence_RadioButton = QtWidgets.QRadioButton(parent=self._mw)
        self._mw.alignment_2d_ButtonGroup.addButton(self._mw.meas_type_fluorescence_RadioButton)
        self._mw.alignment_2d_ToolBar.addWidget(self._mw.meas_type_fluorescence_RadioButton)
        self._mw.meas_type_fluorescence_RadioButton.setText('Fluorescence')

        self._mw.meas_type_odmr_RadioButton = QtWidgets.QRadioButton(parent=self._mw)
        self._mw.alignment_2d_ButtonGroup.addButton(self._mw.meas_type_odmr_RadioButton)
        self._mw.alignment_2d_ToolBar.addWidget(self._mw.meas_type_odmr_RadioButton)
        self._mw.meas_type_odmr_RadioButton.setText('ODMR')

        self._mw.meas_type_nuclear_spin_RadioButton = QtWidgets.QRadioButton(parent=self._mw)
        self._mw.alignment_2d_ButtonGroup.addButton(self._mw.meas_type_nuclear_spin_RadioButton)
        self._mw.alignment_2d_ToolBar.addWidget(self._mw.meas_type_nuclear_spin_RadioButton)
        self._mw.meas_type_nuclear_spin_RadioButton.setText('Nuclear Spin')

        self._mw.meas_type_fluorescence_RadioButton.setChecked(True)


    def _create_axis_pos_disp(self):
        """ Create the axis position display.

        The generic variable name for a created QLable is:
            curr_pos_axis{0}_Label
        The generic variable name for a created ScienDSpinBox is:
            curr_pos_axis{0}_ScienDSpinBox
        where in {0} the name of the axis will be inserted.

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Use the method get_ref_curr_pos_ScienDSpinBox with the appropriated
        label, otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()
        # set the parameters in the curr_pos_DockWidget:
        for index, axis_label in enumerate(constraints):

            # Set the QLabel according to the grid
            # this is the name prototype for the label of current position display
            label_var_name = 'curr_pos_axis{0}_Label'.format(axis_label)
            setattr(self._mw, label_var_name, QtWidgets.QLabel(self._mw.curr_pos_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name)
            label_var.setObjectName(label_var_name)
            label_var.setText('{0}'.format(axis_label))
            self._mw.curr_pos_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the ScienDSpinBox according to the grid
            # this is the name prototype for the current position display
            dspinbox_ref_name = 'curr_pos_axis{0}_ScienDSpinBox'.format(axis_label)

            setattr(self._mw, dspinbox_ref_name, ScienDSpinBox(parent=self._mw.curr_pos_DockWidgetContents))
            dspinbox_ref = getattr(self._mw, dspinbox_ref_name)
            dspinbox_ref.setObjectName(dspinbox_ref_name)
            dspinbox_ref.setReadOnly(True)
            dspinbox_ref.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            dspinbox_ref.setMaximum(np.inf)
            dspinbox_ref.setMinimum(-np.inf)

            # dspinbox_ref.setOpts(minStep=constraints[axis_label]['pos_step'])
            dspinbox_ref.setSingleStep(0.001, dynamic_stepping=False)
            dspinbox_ref.setSuffix(constraints[axis_label]['unit'])

            self._mw.curr_pos_GridLayout.addWidget(dspinbox_ref, index, 1, 1, 1)

        extension = len(constraints)
        self._mw.curr_pos_GridLayout.addWidget(self._mw.curr_pos_get_pos_PushButton, 0, 2, extension, 1)
        self._mw.curr_pos_GridLayout.addWidget(self._mw.curr_pos_stop_PushButton, 0, 3, extension, 1)
        self._mw.curr_pos_get_pos_PushButton.clicked.connect(self.update_pos)
        self._mw.curr_pos_stop_PushButton.clicked.connect(self.stop_movement)

    def _create_move_rel_control(self):
        """ Create all the gui elements to control a relative movement.

        The generic variable name for a created QLable is:
            move_rel_axis_{0}_Label
        The generic variable name for a created ScienDSpinBox is:
            move_rel_axis_{0}_ScienDSpinBox
        The generic variable name for a created QPushButton in negative dir is:
            move_rel_axis_{0}_m_PushButton
        The generic variable name for a created QPushButton in positive dir is:
            move_rel_axis_{0}_p_PushButton

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Use the method get_ref_move_rel_ScienDSpinBox with the appropriated
        label, otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

        # set the axis_labels in the curr_pos_DockWidget:
        for index, axis_label in enumerate(constraints):

            label_var_name = 'move_rel_axis_{0}_Label'.format(axis_label)
            setattr(self._mw, label_var_name, QtWidgets.QLabel(self._mw.move_rel_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name) # get the reference
            label_var.setObjectName(label_var_name) # set axis_label for the label
            label_var.setText('{0}'.format(axis_label))
            # add the label to the grid:
            self._mw.move_rel_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the ScienDSpinBox according to the grid
            # this is the name prototype for the relative movement display
            dspinbox_ref_name = 'move_rel_axis_{0}_ScienDSpinBox'.format(axis_label)
            setattr(self._mw, dspinbox_ref_name, ScienDSpinBox(parent=self._mw.move_rel_DockWidgetContents))
            dspinbox_ref = getattr(self._mw, dspinbox_ref_name)
            dspinbox_ref.setObjectName(dspinbox_ref_name)
#            dspinbox_ref.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)

            dspinbox_ref.setMaximum(constraints[axis_label]['pos_max'])
            dspinbox_ref.setMinimum(constraints[axis_label]['pos_min'])

            # dspinbox_ref.setOpts(minStep=constraints[axis_label]['pos_step'])
            dspinbox_ref.setSingleStep(0.001, dynamic_stepping=False)
            dspinbox_ref.setSuffix(constraints[axis_label]['unit'])

            self._mw.move_rel_GridLayout.addWidget(dspinbox_ref, index, 1, 1, 1)


            # this is the name prototype for the relative movement minus button
            func_name = 'move_rel_axis_{0}_m'.format(axis_label)
            # create a method and assign it as attribute:
            setattr(self, func_name, self._function_builder_move_rel(func_name,axis_label,-1) )
            move_rel_m_ref =  getattr(self, func_name)  # get the reference

            # the change of the PushButton is connected to the previous method.
            button_var_name = 'move_rel_axis_{0}_m_PushButton'.format(axis_label)
            setattr(self._mw, button_var_name, QtWidgets.QPushButton(self._mw.move_rel_DockWidgetContents))
            button_var = getattr(self._mw, button_var_name)
            button_var.setObjectName(button_var_name)
            button_var.setText('-')
            button_var.clicked.connect(move_rel_m_ref, type=QtCore.Qt.QueuedConnection)
            self._mw.move_rel_GridLayout.addWidget(button_var, index, 2, 1, 1)

            # this is the name prototype for the relative movement plus button
            func_name = 'move_rel_axis_{0}_p'.format(axis_label)
            setattr(self, func_name, self._function_builder_move_rel(func_name,axis_label,1) )
            move_rel_p_ref = getattr(self, func_name)

            # the change of the PushButton is connected to the previous method.
            button_var_name = 'move_rel_axis_{0}_p_PushButton'.format(axis_label)
            setattr(self._mw, button_var_name, QtWidgets.QPushButton(self._mw.move_rel_DockWidgetContents))
            button_var = getattr(self._mw, button_var_name)
            button_var.setObjectName(button_var_name)
            button_var.setText('+')
            button_var.clicked.connect(move_rel_p_ref, type=QtCore.Qt.QueuedConnection)
            self._mw.move_rel_GridLayout.addWidget(button_var, index, 3, 1, 1)

    def _create_move_abs_control(self):
        """ Create all the GUI elements to control a relative movement.

        The generic variable name for a created QLable is:
            move_abs_axis_{0}_Label
        The generic variable name for a created QLable is:
            move_abs_axis_{0}_Slider
        The generic variable name for a created ScienDSpinBox is:
            move_abs_axis_{0}_ScienDSpinBox
        The generic variable name for a created QPushButton for move is:
            move_abs_PushButton

        These methods should not be called:
        The generic variable name for a update method for the ScienDSpinBox:
            _update_move_abs_{0}_dspinbox
        The generic variable name for a update method for the QSlider:
            _update_move_abs_{0}_slider

        DO NOT CALL THESE VARIABLES DIRECTLY! USE THE DEDICATED METHOD INSTEAD!
        Use the method get_ref_move_abs_ScienDSpinBox with the appropriated
        label, otherwise you will break the generality.
        """

        constraints = self._magnet_logic.get_hardware_constraints()

        for index, axis_label in enumerate(constraints):

            label_var_name = 'move_abs_axis_{0}_Label'.format(axis_label)
            setattr(self._mw, label_var_name, QtWidgets.QLabel(self._mw.move_abs_DockWidgetContents))
            label_var = getattr(self._mw, label_var_name) # get the reference
            # set axis_label for the label:
            label_var.setObjectName(label_var_name)
            label_var.setText(axis_label)

            # make the steps of the splider as a multiple of 10
            # smallest_step_slider = 10**int(np.log10(constraints[axis_label]['pos_step']) -1)
            smallest_step_slider = constraints[axis_label]['pos_step']

            # add the label to the grid:
            self._mw.move_abs_GridLayout.addWidget(label_var, index, 0, 1, 1)

            # Set the ScienDSpinBox according to the grid
            # this is the name prototype for the relative movement display
            slider_obj_name = 'move_abs_axis_{0}_Slider'.format(axis_label)
            setattr(self._mw, slider_obj_name, QtWidgets.QSlider(self._mw.move_abs_DockWidgetContents))
            slider_obj = getattr(self._mw, slider_obj_name)
            slider_obj.setObjectName(slider_obj_name)
            slider_obj.setOrientation(QtCore.Qt.Horizontal)
#            dspinbox_ref.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)

            max_val = abs(constraints[axis_label]['pos_max'] - constraints[axis_label]['pos_min'])

            # set the step size of the slider to a fixed resolution, that
            # prevents really ugly rounding error behaviours in display.
            # Set precision to nanometer scale, which is actually never reached.
            max_steps = int(max_val/smallest_step_slider)


            slider_obj.setMaximum(max_steps)
            slider_obj.setMinimum(0)
            #TODO: set the decimals also from the constraints!
#            slider_obj.setDecimals(3)
            slider_obj.setSingleStep(1)
            # slider_obj.setEnabled(False)

            self._mw.move_abs_GridLayout.addWidget(slider_obj, index, 1, 1, 1)

            # Set the ScienDSpinBox according to the grid
            # this is the name prototype for the relative movement display
            dspinbox_ref_name = 'move_abs_axis_{0}_ScienDSpinBox'.format(axis_label)
            setattr(self._mw, dspinbox_ref_name, ScienDSpinBox(parent=self._mw.move_abs_DockWidgetContents))
            dspinbox_ref = getattr(self._mw, dspinbox_ref_name)
            dspinbox_ref.setObjectName(dspinbox_ref_name)
#            dspinbox_ref.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)

            dspinbox_ref.setMaximum(constraints[axis_label]['pos_max'])
            dspinbox_ref.setMinimum(constraints[axis_label]['pos_min'])

            # dspinbox_ref.setOpts(minStep=constraints[axis_label]['pos_step'])
            dspinbox_ref.setSingleStep(0.001, dynamic_stepping=False)
            dspinbox_ref.setSuffix(constraints[axis_label]['unit'])

            # set the horizontal size to 100 pixel:
            dspinbox_ref.setMaximumSize(QtCore.QSize(80, 16777215))

            self._mw.move_abs_GridLayout.addWidget(dspinbox_ref, index, 2, 1, 1)

            # build a function to change the dspinbox value and connect a
            # slidermove event to it:
            func_name = '_update_move_abs_{0}_dspinbox'.format(axis_label)
            setattr(self, func_name, self._function_builder_update_viewbox(func_name, axis_label, dspinbox_ref))
            update_func_dspinbox_ref = getattr(self, func_name)
            slider_obj.valueChanged.connect(update_func_dspinbox_ref)

            # build a function to change the slider value and connect a
            # spinbox value change event to it:
            func_name = '_update_move_abs_{0}_slider'.format(axis_label)
            setattr(self, func_name, self._function_builder_update_slider(func_name, axis_label, slider_obj))
            update_func_slider_ref = getattr(self, func_name)
            # dspinbox_ref.valueChanged.connect(update_func_slider_ref)

            # the editingFinished idea has to be implemented properly at first:
            dspinbox_ref.editingFinished.connect(update_func_slider_ref)

        extension = len(constraints)
        self._mw.move_abs_GridLayout.addWidget(self._mw.move_abs_PushButton, 0, 3, extension, 1)
        self._mw.move_abs_PushButton.clicked.connect(self.move_abs)
        self._mw.move_abs_PushButton.clicked.connect(self.update_roi_from_abs_movement)

    def _function_builder_move_rel(self, func_name, axis_label, direction):
        """ Create a function/method, which gets executed for pressing move_rel.

        @param str func_name: name how the function should be called.
        @param str axis_label: label of the axis you want to create a control
                               function for.
        @param int direction: either 1 or -1 depending on the relative movement.
        @return: function with name func_name

        A routine to construct a method on the fly and attach it as attribute
        to the object, so that it can be used or so that other signals can be
        connected to it. That means the return value is already fixed for a
        function name.
        """

        def func_dummy_name():
            self.move_rel(axis_label, direction)

        func_dummy_name.__name__ = func_name
        return func_dummy_name

        # create the signals for the push buttons and connect them to the move
        # rel method in the Logic

    def _function_builder_update_viewbox(self, func_name, axis_label,
                                         ref_dspinbox):
        """ Create a function/method, which gets executed for pressing move_rel.

        @param str func_name: name how the function should be called.
        @param str axis_label: label of the axis you want to create a control
                               function for.
        @param object ref_dspinbox: a reference to the dspinbox object, which
                                    will actually apply the changed within the
                                    created method.

        @return: function with name func_name

        A routine to construct a method on the fly and attach it as attribute
        to the object, so that it can be used or so that other signals can be
        connected to it. The connection of a signal to this method must appear
        outside of the present function.
        """

        def func_dummy_name(slider_val):
            """
            @param int slider_val: The current value of the slider, will be an
                                   integer value between
                                       [0,(pos_max - pos_min)/pos_step]
                                   of the corresponding axis label.
                                   Now convert this value back to a viewbox
                                   value like:
                                       pos_min + slider_step*pos_step
            """

            constraints = self._magnet_logic.get_hardware_constraints()
            # set the resolution of the slider to nanometer precision, that is
            # better for the display behaviour. In the end, that will just make
            # everything smoother but not actually affect the displayed number:

            # max_step_slider = 10**int(np.log10(constraints[axis_label]['pos_step']) -1)
            max_step_slider = constraints[axis_label]['pos_step']

            actual_pos = (constraints[axis_label]['pos_min'] + slider_val * max_step_slider)
            ref_dspinbox.setValue(actual_pos)

        func_dummy_name.__name__ = func_name
        return func_dummy_name

    def _function_builder_update_slider(self, func_name, axis_label, ref_slider):
        """ Create a function/method, which gets executed for pressing move_rel.

        Create a function/method, which gets executed for pressing move_rel.

        @param str func_name: name how the function should be called.
        @param str axis_label: label of the axis you want to create a control
                               function for.
        @param object ref_slider: a reference to the slider object, which
                                  will actually apply the changed within the
                                  created method.

        @return: function with name func_name

        A routine to construct a method on the fly and attach it as attribute
        to the object, so that it can be used or so that other signals can be
        connected to it. The connection of a signal to this method must appear
        outside of the present function.
        """

        def func_dummy_name():
            """
            @param int slider_step: The current value of the slider, will be an
                                    integer value between
                                        [0,(pos_max - pos_min)/pos_step]
                                    of the corresponding axis label.
                                    Now convert this value back to a viewbox
                                    value like:
                                        pos_min + slider_step*pos_step
            """

            dspinbox_obj = self.get_ref_move_abs_ScienDSpinBox(axis_label)
            viewbox_val = dspinbox_obj.value()

            constraints = self._magnet_logic.get_hardware_constraints()
            # set the resolution of the slider to nanometer precision, that is
            # better for the display behaviour. In the end, that will just make
            # everything smoother but not actually affect the displayed number:

            # max_step_slider = 10**int(np.log10(constraints[axis_label]['pos_step']) -1)
            max_step_slider = constraints[axis_label]['pos_step']

            slider_val = abs(viewbox_val - constraints[axis_label]['pos_min'])/max_step_slider
            ref_slider.setValue(slider_val)

        func_dummy_name.__name__ = func_name
        return func_dummy_name

        # create the signals for the push buttons and connect them to the move
        # rel method in the Logic

    def move_rel(self, axis_label, direction):
        """ Move relative by the axis with given label an direction.

        @param str axis_label: tells which axis should move.
        @param int direction: either 1 or -1 depending on the relative movement.

        That method get called from methods, which are created on the fly at
        runtime during the activation of that module (basically from the
        methods with the generic name move_rel_axis_{0}_p or
        move_rel_axis_{0}_m with the appropriate label).
        """
        #constraints = self._magnet_logic.get_hardware_constraints()
        dspinbox = self.get_ref_move_rel_ScienDSpinBox(axis_label)

        movement = dspinbox.value() * direction

        self._magnet_logic.move_rel({axis_label: movement})
        # if self._interactive_mode:
        #     self.update_pos()
        return axis_label, direction

    def move_abs(self, param_dict=None):
        """ Perform an absolute movement.

        @param param_dict: with {<axis_label>:<position>}, can of course
                           contain many entries of the same kind.

        Basically all the axis can be controlled at the same time.
        """

        if (param_dict is not None) and (type(param_dict) is not bool):
            self._magnet_logic.move_abs(param_dict)
        else:
            constraints = self._magnet_logic.get_hardware_constraints()

            # create the move_abs dict
            move_abs = {}
            for label in constraints:
                move_abs[label] = self.get_ref_move_abs_ScienDSpinBox(label).value()

            self._magnet_logic.move_abs(move_abs)

        # if self._interactive_mode:
        #     self.update_pos()
            return param_dict


    def get_ref_curr_pos_ScienDSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """

        dspinbox_name = 'curr_pos_axis{0}_ScienDSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def get_ref_move_rel_ScienDSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """

        dspinbox_name = 'move_rel_axis_{0}_ScienDSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def get_ref_move_abs_ScienDSpinBox(self, label):
        """ Get the reference to the double spin box for the passed label. """

        dspinbox_name = 'move_abs_axis_{0}_ScienDSpinBox'.format(label)
        dspinbox_ref = getattr(self._mw, dspinbox_name)
        return dspinbox_ref

    def get_ref_move_abs_Slider(self, label):
        """ Get the reference to the slider for the passed label. """

        slider_name = 'move_abs_axis_{0}_Slider'.format(label)
        slider_ref = getattr(self._mw, slider_name)
        return slider_ref

    def move_rel_para_changed(self):
        """ Pass the current GUI value to the logic

        @return dict: Passed move relative parameter
        """
        dict={}
        axes=list(self._magnet_logic.get_hardware_constraints())
        for axis_label in axes:
            dspinbox = self.get_ref_move_rel_ScienDSpinBox(axis_label)
            dict[axis_label]=dspinbox.value()
        self._magnet_logic.set_move_rel_para(dict)
        return dict

    def align_2d_axis0_name_changed(self):
        """ Pass the current GUI value to the logic

        @return str: Passed axis name
        """
        axisname = self._mw.align_2d_axis0_name_ComboBox.currentText()
        self._magnet_logic.set_align_2d_axis0_name(axisname)
        return axisname

    def align_2d_axis0_range_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed range
        """
        range = self._mw.align_2d_axis0_range_DSpinBox.value()
        self._magnet_logic.set_align_2d_axis0_range(range)
        return range

    def align_2d_axis0_step_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed step
        """
        step = self._mw.align_2d_axis0_step_DSpinBox.value()
        self._magnet_logic.set_align_2d_axis0_step(step)
        return step

    def align_2d_axis0_vel_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed velocity
        """
        vel = self._mw.align_2d_axis0_vel_DSpinBox.value()
        self._magnet_logic.set_align_2d_axis0_vel(vel)
        return vel

    def align_2d_axis1_name_changed(self):
        """ Pass the current GUI value to the logic

        @return str: Passed axis name
        """
        axisname = self._mw.align_2d_axis1_name_ComboBox.currentText()
        self._magnet_logic.set_align_2d_axis1_name(axisname)
        return axisname

    def align_2d_axis1_range_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed range
        """
        range = self._mw.align_2d_axis1_range_DSpinBox.value()
        self._magnet_logic.set_align_2d_axis1_range(range)
        return range

    def align_2d_axis1_step_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed step size
        """
        step = self._mw.align_2d_axis1_step_DSpinBox.value()
        self._magnet_logic.set_align_2d_axis1_step(step)
        return step

    def align_2d_axis1_vel_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed velocity
        """
        vel = self._mw.align_2d_axis1_vel_DSpinBox.value()
        self._magnet_logic.set_align_2d_axis1_vel(vel)
        return vel

    def optimize_pos_freq_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed frequency
         """
        freq = self._mw.align_2d_fluorescence_optimize_freq_SpinBox.value()
        self._magnet_logic.set_optimize_pos_freq(freq)
        return freq

    def fluorescence_integration_time_changed(self):
        """ Pass the current GUI value to the logic

        @return float: Passed integration time
         """
        time = self._mw.align_2d_fluorescence_integrationtime_DSpinBox.value()
        self._magnet_logic.set_fluorescence_integration_time(time)
        return time

    def stop_movement(self):
        """ Invokes an immediate stop of the hardware.

        MAKE SURE THAT THE HARDWARE CAN BE CALLED DURING AN ACTION!
        If the parameter _interactive_mode is set to False no stop can be done
        since the device would anyway not respond to a method call.
        """

        if self._interactive_mode:
            self._magnet_logic.stop_movement()
        else:
            self.log.warning('Movement cannot be stopped during a movement '
                    'anyway! Set the interactive mode to True in the Magnet '
                    'Settings! Otherwise this method is useless.')

    def update_pos(self, param_list=None):
        """ Update the current position.

        @param list param_list: optional, if specific positions needed to be
                                updated.

        If no value is passed, the current position is retrieved from the
        logic and the display is changed.
        """
        constraints = self._magnet_logic.get_hardware_constraints()
        curr_pos =  self._magnet_logic.get_pos()
        if (param_list is not None) and (type(param_list) is not bool):
            param_list = list(param_list)
            # param_list =list(param_list) # convert for safety to a list
            curr_pos =  self._magnet_logic.get_pos(param_list)

        for axis_label in curr_pos:
            # update the values of the current position viewboxes:
            dspinbox_pos_ref = self.get_ref_curr_pos_ScienDSpinBox(axis_label)

            dspinbox_pos_ref.setValue(curr_pos[axis_label])

            # update the values also of the absolute movement display:
            #dspinbox_move_abs_ref = self.get_ref_move_abs_ScienDSpinBox(axis_label)
            #dspinbox_move_abs_ref.setValue(curr_pos[axis_label])

        return curr_pos


    def run_stop_2d_alignment(self, is_checked):
        """ Manage what happens if 2d magnet scan is started/stopped

        @param bool is_checked: state if the current scan, True = started,
                                False = stopped
        """

        if is_checked:
            self.start_2d_alignment_clicked()

        else:
            self.abort_2d_alignment_clicked()

    def _change_display_to_stop_2d_alignment(self):
        """ Changes every display component back to the stopped state. """

        self._mw.run_stop_2d_alignment_Action.blockSignals(True)
        self._mw.run_stop_2d_alignment_Action.setChecked(False)

        self._mw.continue_2d_alignment_Action.blockSignals(True)
        self._mw.continue_2d_alignment_Action.setChecked(False)

        self._mw.run_stop_2d_alignment_Action.blockSignals(False)
        self._mw.continue_2d_alignment_Action.blockSignals(False)

    def start_2d_alignment_clicked(self):
        """ Start the 2d alignment. """

        if self.measurement_type == '2d_fluorescence':
            self._magnet_logic.curr_alignment_method = self.measurement_type

            self._magnet_logic.fluorescence_integration_time = self._mw.align_2d_fluorescence_integrationtime_DSpinBox.value()
            self._mw.alignment_2d_cb_GraphicsView.setLabel('right', 'Fluorescence', units='c/s')

        elif self.measurement_type == '2d_odmr':
            self._magnet_logic.curr_alignment_method = self.measurement_type

            self._magnet_logic.odmr_2d_low_center_freq = self._mw.align_2d_odmr_low_center_freq_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_range_freq = self._mw.align_2d_odmr_low_range_freq_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_step_freq = self._mw.align_2d_odmr_low_step_freq_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_power = self._mw.align_2d_odmr_low_power_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_runtime  = self._mw.align_2d_odmr_low_runtime_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_fitfunction = self._mw.align_2d_odmr_low_fit_func_ComboBox.currentText()

            self._magnet_logic.odmr_2d_high_center_freq = self._mw.align_2d_odmr_high_center_freq_DSpinBox.value()
            self._magnet_logic.odmr_2d_high_range_freq = self._mw.align_2d_odmr_high_range_freq_DSpinBox.value()
            self._magnet_logic.odmr_2d_high_step_freq = self._mw.align_2d_odmr_high_step_freq_DSpinBox.value()
            self._magnet_logic.odmr_2d_high_power = self._mw.align_2d_odmr_high_power_DSpinBox.value()
            self._magnet_logic.odmr_2d_high_runtime = self._mw.align_2d_odmr_high_runtime_DSpinBox.value()
            self._magnet_logic.odmr_2d_high_fitfunction = self._mw.align_2d_odmr_high_fit_func_ComboBox.currentText()

            self._magnet_logic.odmr_2d_peak_axis0_move_ratio = self._mw.align_2d_axis0_shift_DSpinBox.value()*1e12
            self._magnet_logic.odmr_2d_peak_axis1_move_ratio = self._mw.align_2d_axis1_shift_DSpinBox.value()*1e12

            self._magnet_logic.odmr_2d_single_trans = self._mw.odmr_2d_single_trans_CheckBox.isChecked()

            if self._mw.odmr_2d_single_trans_CheckBox.isChecked():
                self._mw.alignment_2d_cb_GraphicsView.setLabel('right', 'ODMR transition contrast', units='%')
            else:
                self._mw.alignment_2d_cb_GraphicsView.setLabel('right', 'Half ODMR splitting', units='Hz')

        elif self.measurement_type == '2d_nuclear':
            self._magnet_logic.curr_alignment_method = self.measurement_type

            # ODMR stuff:
            self._magnet_logic.odmr_2d_low_center_freq = self._mw.align_2d_odmr_low_center_freq_DSpinBox.value()*1e6
            self._magnet_logic.odmr_2d_low_step_freq = self._mw.align_2d_odmr_low_step_freq_DSpinBox.value()*1e6
            self._magnet_logic.odmr_2d_low_range_freq = self._mw.align_2d_odmr_low_range_freq_DSpinBox.value()*1e6
            self._magnet_logic.odmr_2d_low_power = self._mw.align_2d_odmr_low_power_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_runtime  = self._mw.align_2d_odmr_low_runtime_DSpinBox.value()
            self._magnet_logic.odmr_2d_low_fitfunction = self._mw.align_2d_odmr_low_fit_func_ComboBox.currentText()

            self._magnet_logic.odmr_2d_peak_axis0_move_ratio = self._mw.align_2d_axis0_shift_DSpinBox.value()*1e12
            self._magnet_logic.odmr_2d_peak_axis1_move_ratio = self._mw.align_2d_axis1_shift_DSpinBox.value()*1e12

            self._magnet_logic.odmr_2d_single_trans = self._mw.odmr_2d_single_trans_CheckBox.isChecked()

            # nuclear ops:
            self._magnet_logic.nuclear_2d_rabi_periode = self._mw.align_2d_nuclear_rabi_periode_DSpinBox.value()*1e-9
            self._magnet_logic.nuclear_2d_mw_freq = self._mw.align_2d_nuclear_mw_freq_DSpinBox.value()*1e6
            self._magnet_logic.nuclear_2d_mw_channel = self._mw.align_2d_nuclear_mw_channel_SpinBox.value()
            self._magnet_logic.nuclear_2d_mw_power = self._mw.align_2d_nuclear_mw_power_DSpinBox.value()
            self._magnet_logic.nuclear_2d_laser_time = self._mw.align_2d_nuclear_laser_time_DSpinBox.value()
            self._magnet_logic.nuclear_2d_laser_channel = self._mw.align_2d_nuclear_laser_channel_SpinBox.value()
            self._magnet_logic.nuclear_2d_detect_channel = self._mw.align_2d_nuclear_detect_channel_SpinBox.value()
            self._magnet_logic.nuclear_2d_idle_time = self._mw.align_2d_nuclear_idle_time_DSpinBox.value()
            self._magnet_logic.nuclear_2d_reps_within_ssr = self._mw.align_2d_nuclear_reps_within_ssr_SpinBox.value()
            self._magnet_logic.nuclear_2d_num_ssr = self._mw.align_2d_nuclear_num_of_ssr_SpinBox.value()

            self._mw.alignment_2d_cb_GraphicsView.setLabel('right', 'Single shot readout fidelity', units='%')


        # constraints = self._magnet_logic.get_hardware_constraints()

        # axis0_name = self._mw.align_2d_axis0_name_ComboBox.currentText()
        # axis0_range = self._mw.align_2d_axis0_range_DSpinBox.value()
        # axis0_step = self._mw.align_2d_axis0_step_DSpinBox.value()
        #
        # axis1_name = self._mw.align_2d_axis1_name_ComboBox.currentText()
        # axis1_range = self._mw.align_2d_axis1_range_DSpinBox.value()
        # axis1_step = self._mw.align_2d_axis1_step_DSpinBox.value()

        # if axis0_name == axis1_name:
        #     self.log.error('Fluorescence Alignment cannot be started since the '
        #                 'same axis with name "{0}" was chosen for axis0 and '
        #                 'axis1!\n'
        #                 'Alignment will not be started. Change the '
        #                 'settings!'.format(axis0_name))
        #     return

        # if self._mw.align_2d_axis0_set_vel_CheckBox.isChecked():
        #     axis0_vel = self._mw.align_2d_axis0_vel_DSpinBox.value()
        # else:
        #     axis0_vel = None
        #
        # if self._mw.align_2d_axis1_set_vel_CheckBox.isChecked():
        #     axis1_vel = self._mw.align_2d_axis1_vel_DSpinBox.value()
        # else:
        #     axis1_vel = None

        self._magnet_logic.start_2d_alignment(continue_meas=self._continue_2d_fluorescence_alignment)

        self._continue_2d_fluorescence_alignment = False

    def continue_stop_2d_alignment(self, is_checked):
        """ Manage what happens if 2d magnet scan is continued/stopped

        @param bool is_checked: state if the current scan, True = continue,
                                False = stopped
        """

        if is_checked:
            self.continue_2d_alignment_clicked()
        else:
            self.abort_2d_alignment_clicked()


    def continue_2d_alignment_clicked(self):

        self._continue_2d_fluorescence_alignment = True
        self.start_2d_alignment_clicked()


    def abort_2d_alignment_clicked(self):
        """ Stops the current Fluorescence alignment. """

        self._change_display_to_stop_2d_alignment()
        self._magnet_logic.stop_alignment()

    def _update_limits_axis0(self):
        """ Whenever a new axis name was chosen in axis0 config, the limits of the
            viewboxes will be adjusted.
        """

        constraints = self._magnet_logic.get_hardware_constraints()
        axis0_name = self._mw.align_2d_axis0_name_ComboBox.currentText()

        # set the range constraints:
        self._mw.align_2d_axis0_range_DSpinBox.setMinimum(0)
        self._mw.align_2d_axis0_range_DSpinBox.setMaximum(constraints[axis0_name]['pos_max'])
        self._mw.align_2d_axis0_range_DSpinBox.setSingleStep(constraints[axis0_name]['pos_step'],
                                                             dynamic_stepping=False)
        self._mw.align_2d_axis0_range_DSpinBox.setSuffix(constraints[axis0_name]['unit'])

        # set the step constraints:
        self._mw.align_2d_axis0_step_DSpinBox.setMinimum(0)
        self._mw.align_2d_axis0_step_DSpinBox.setMaximum(constraints[axis0_name]['pos_max'])
        self._mw.align_2d_axis0_step_DSpinBox.setSingleStep(constraints[axis0_name]['pos_step'],
                                                            dynamic_stepping=False)
        self._mw.align_2d_axis0_step_DSpinBox.setSuffix(constraints[axis0_name]['unit'])

        # set the velocity constraints:
        self._mw.align_2d_axis0_vel_DSpinBox.setMinimum(constraints[axis0_name]['vel_min'])
        self._mw.align_2d_axis0_vel_DSpinBox.setMaximum(constraints[axis0_name]['vel_max'])
        self._mw.align_2d_axis0_vel_DSpinBox.setSingleStep(constraints[axis0_name]['vel_step'],
                                                           dynamic_stepping=False)
        self._mw.align_2d_axis0_vel_DSpinBox.setSuffix(constraints[axis0_name]['unit']+'/s')

    def _update_limits_axis1(self):
        """ Whenever a new axis name was chosen in axis0 config, the limits of the
            viewboxes will be adjusted.
        """

        constraints = self._magnet_logic.get_hardware_constraints()
        axis1_name = self._mw.align_2d_axis1_name_ComboBox.currentText()

        self._mw.align_2d_axis1_range_DSpinBox.setMinimum(0)
        self._mw.align_2d_axis1_range_DSpinBox.setMaximum(constraints[axis1_name]['pos_max'])
        self._mw.align_2d_axis1_range_DSpinBox.setSingleStep(constraints[axis1_name]['pos_step'],
                                                             dynamic_stepping=False)
        self._mw.align_2d_axis1_range_DSpinBox.setSuffix(constraints[axis1_name]['unit'])

        self._mw.align_2d_axis1_step_DSpinBox.setMinimum(0)
        self._mw.align_2d_axis1_step_DSpinBox.setMaximum(constraints[axis1_name]['pos_max'])
        self._mw.align_2d_axis1_step_DSpinBox.setSingleStep(constraints[axis1_name]['pos_step'],
                                                            dynamic_stepping=False)
        self._mw.align_2d_axis1_step_DSpinBox.setSuffix(constraints[axis1_name]['unit'])

        self._mw.align_2d_axis1_vel_DSpinBox.setMinimum(constraints[axis1_name]['vel_min'])
        self._mw.align_2d_axis1_vel_DSpinBox.setMaximum(constraints[axis1_name]['vel_max'])
        self._mw.align_2d_axis1_vel_DSpinBox.setSingleStep(constraints[axis1_name]['vel_step'],
                                                           dynamic_stepping=False)
        self._mw.align_2d_axis1_vel_DSpinBox.setSuffix(constraints[axis1_name]['unit']+'/s')

    def _set_vel_display_axis0(self):
        """ Set the visibility of the velocity display for axis 0. """

        if self._mw.align_2d_axis0_set_vel_CheckBox.isChecked():
            self._mw.align_2d_axis0_vel_DSpinBox.setVisible(True)
        else:
            self._mw.align_2d_axis0_vel_DSpinBox.setVisible(False)

    def _set_vel_display_axis1(self):
        """ Set the visibility of the velocity display for axis 1. """

        if self._mw.align_2d_axis1_set_vel_CheckBox.isChecked():
            self._mw.align_2d_axis1_vel_DSpinBox.setVisible(True)
        else:
            self._mw.align_2d_axis1_vel_DSpinBox.setVisible(False)

    def _update_2d_graph_axis(self):

        constraints = self._magnet_logic.get_hardware_constraints()

        axis0_name = self._mw.align_2d_axis0_name_ComboBox.currentText()
        axis0_unit = constraints[axis0_name]['unit']
        axis1_name = self._mw.align_2d_axis1_name_ComboBox.currentText()
        axis1_unit = constraints[axis1_name]['unit']

        axis0_array, axis1_array = self._magnet_logic.get_2d_axis_arrays()

        self._2d_alignment_ImageItem.setRect(QtCore.QRectF(axis0_array[0],
                                                           axis1_array[0],
                                                           axis0_array[-1]-axis0_array[0],
                                                           axis1_array[-1]-axis1_array[0],))

        self._mw.alignment_2d_GraphicsView.setLabel('bottom', 'Absolute Position, Axis0: ' + axis0_name, units=axis0_unit)
        self._mw.alignment_2d_GraphicsView.setLabel('left', 'Absolute Position, Axis1: '+ axis1_name, units=axis1_unit)

    def _update_2d_graph_cb(self):
        """ Update the colorbar to a new scaling.

        That function alters the color scaling of the colorbar next to the main
        picture.
        """

        # If "Centiles" is checked, adjust colour scaling automatically to
        # centiles. Otherwise, take user-defined values.

        if self._mw.alignment_2d_centiles_RadioButton.isChecked():

            low_centile = self._mw.alignment_2d_cb_low_centiles_DSpinBox.value()
            high_centile = self._mw.alignment_2d_cb_high_centiles_DSpinBox.value()

            if np.isclose(low_centile, 0.0):
                low_centile = 0.0

            # mask the array such that the arrays will be
            masked_image = np.ma.masked_equal(self._2d_alignment_ImageItem.image, 0.0)

            if len(masked_image.compressed()) == 0:
                cb_min = np.percentile(self._2d_alignment_ImageItem.image, low_centile)
                cb_max = np.percentile(self._2d_alignment_ImageItem.image, high_centile)
            else:
                cb_min = np.percentile(masked_image.compressed(), low_centile)
                cb_max = np.percentile(masked_image.compressed(), high_centile)

        else:
            cb_min = self._mw.alignment_2d_cb_min_centiles_DSpinBox.value()
            cb_max = self._mw.alignment_2d_cb_max_centiles_DSpinBox.value()

        self._2d_alignment_cb.refresh_colorbar(cb_min, cb_max)
        self._mw.alignment_2d_cb_GraphicsView.update()

    def _update_2d_graph_data(self):
        """ Refresh the 2D-matrix image. """
        matrix_data = self._magnet_logic.get_2d_data_matrix()

        if self._mw.alignment_2d_centiles_RadioButton.isChecked():

            low_centile = self._mw.alignment_2d_cb_low_centiles_DSpinBox.value()
            high_centile = self._mw.alignment_2d_cb_high_centiles_DSpinBox.value()

            if np.isclose(low_centile, 0.0):
                low_centile = 0.0

            # mask the array in order to mark the values which are zeros with
            # True, the rest with False:
            masked_image = np.ma.masked_equal(matrix_data, 0.0)

            # compress the 2D masked array to a 1D array where the zero values
            # are excluded:
            if len(masked_image.compressed()) == 0:
                cb_min = np.percentile(self._2d_alignment_ImageItem.image, low_centile)
                cb_max = np.percentile(self._2d_alignment_ImageItem.image, high_centile)
            else:
                cb_min = np.percentile(masked_image.compressed(), low_centile)
                cb_max = np.percentile(masked_image.compressed(), high_centile)
        else:
            cb_min = self._mw.alignment_2d_cb_min_centiles_DSpinBox.value()
            cb_max = self._mw.alignment_2d_cb_max_centiles_DSpinBox.value()


        self._2d_alignment_ImageItem.setImage(image=matrix_data,
                                              levels=(cb_min, cb_max))
        self._update_2d_graph_axis()

        self._update_2d_graph_cb()

        # get data from logic


    def save_2d_plots_and_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        timestamp = datetime.datetime.now()
        filetag = self._mw.alignment_2d_nametag_LineEdit.text()
        filepath = self._save_logic.get_path_for_module(module_name='Magnet')

        if len(filetag) > 0:
            filename = os.path.join(filepath, '{0}_{1}_Magnet'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
        else:
            filename = os.path.join(filepath, '{0}_Magnet'.format(timestamp.strftime('%Y%m%d-%H%M-%S'),))

        exporter_graph = pyqtgraph.exporters.SVGExporter(self._mw.alignment_2d_GraphicsView.plotItem.scene())
        #exporter_graph = pg.exporters.ImageExporter(self._mw.odmr_PlotWidget.plotItem)
        exporter_graph.export(filename  + '.svg')

        # self._save_logic.
        self._magnet_logic.save_2d_data(filetag, timestamp)

    def set_measurement_type(self):
        """ According to the selected Radiobox a measurement type will be chosen."""

        #FIXME: the measurement type should actually be set and saved in the logic

        if self._mw.meas_type_fluorescence_RadioButton.isChecked():
            self.measurement_type = '2d_fluorescence'
        elif self._mw.meas_type_odmr_RadioButton.isChecked():
            self.measurement_type = '2d_odmr'
        elif self._mw.meas_type_nuclear_spin_RadioButton.isChecked():
            self.measurement_type = '2d_nuclear'
        else:
            self.log.error('No measurement type specified in Magnet GUI!')
    def _odmr_single_trans_alignment_changed(self):
        """ Adjust the GUI display if only one ODMR transition is used. """

        if self._mw.odmr_2d_single_trans_CheckBox.isChecked():
            self._mw.odmr_2d_high_trans_GroupBox.setVisible(False)
        else:
            self._mw.odmr_2d_high_trans_GroupBox.setVisible(True)

    def update_from_roi_magnet(self, roi):
        """The user manually moved the XY ROI, adjust all other GUI elements accordingly

        @params object roi: PyQtGraph ROI object
        """
        x_pos = roi.pos()[0] + 0.5 * roi.size()[0]
        y_pos = roi.pos()[1] + 0.5 * roi.size()[1]

        if hasattr(self._magnet_logic, '_axis0_name') and hasattr(self._magnet_logic, '_axis1_name'):
            axis0_name = self._magnet_logic._axis0_name
            axis1_name = self._magnet_logic._axis1_name
        else:
            axis0_name = 'axis0'
            axis1_name = 'axis1'

        self._mw.pos_label.setText('({0}, {1})'.format(axis0_name, axis1_name))
        self._mw.pos_show.setText('({0:.6f}, {1:.6f})'.format(x_pos, y_pos))
        # I only need to update my label here.
        # which I would like to create in the QtDesigner

    def update_roi_from_abs_movement(self):
        """
        User changed magnetic field through absolute movement, therefore the roi has to be adjusted.
        @return:
        """
        axis0_name = self._mw.align_2d_axis0_name_ComboBox.currentText()
        axis1_name = self._mw.align_2d_axis1_name_ComboBox.currentText()
        self.log.debug('get the axis0_name: {0}'.format(axis0_name))
        self.log.debug('get the axis0_name: {0}'.format(axis1_name))
        axis0_value = self.get_ref_move_abs_ScienDSpinBox(axis0_name).value()
        axis1_value = self.get_ref_move_abs_ScienDSpinBox(axis1_name).value()

        center_x = axis0_value + 0.5 * self.roi_magnet.size()[0]
        center_y = axis1_value + 0.5 * self.roi_magnet.size()[1]
        self.roi_magnet.setPos([center_x, center_y])

        return 0


    def update_move_rel_para(self,dict):
        """ The GUT is updated taking dict into account. Thereby no signal is triggered!

        @params dictionary: Dictionary containing the values to update

        @return dictionary: Dictionary containing the values to update
         """
        for axis_label in dict:
            dspinbox = self.get_ref_move_rel_ScienDSpinBox(axis_label)
            dspinbox.blockSignals(True)
            dspinbox.setValue(dict[axis_label])
            dspinbox.blockSignals(False)
        return dict

    def update_roi_from_range(self):
        """
        User changed scan range and therefore the rectangular should be adjusted
        @return:
        """
        # first get the size of axis0 and axis1 range
        x_range = self._mw.align_2d_axis0_range_DSpinBox.value()
        y_range = self._mw.align_2d_axis0_range_DSpinBox.value()
        self.roi_magnet.setSize([x_range/100, y_range/100])


    def update_align_2d_axis0_name(self,axisname):
        """ The GUT is updated taking axisname into account. Thereby no signal is triggered!

        @params str: Axis name to update

        @return str: Axis name to update
         """
        self._mw.align_2d_axis0_name_ComboBox.blockSignals(True)
        index = self._mw.align_2d_axis0_name_ComboBox.findText(axisname)
        self._mw.align_2d_axis0_name_ComboBox.setCurrentIndex(index)
        self._mw.align_2d_axis0_name_ComboBox.blockSignals(False)
        return axisname

    def update_align_2d_axis0_range(self,range):
        """ The GUT is updated taking range into account. Thereby no signal is triggered!

        @params float: Range to update

        @return float: Range to update
         """
        self._mw.align_2d_axis0_range_DSpinBox.blockSignals(True)
        self._mw.align_2d_axis0_range_DSpinBox.setValue(range)
        self._mw.align_2d_axis0_range_DSpinBox.blockSignals(False)
        return range

    def update_align_2d_axis0_step(self,step):
        """ The GUT is updated taking step into account. Thereby no signal is triggered!

        @params float: Step to update in m

        @return float: Step to update in m
         """
        self._mw.align_2d_axis0_step_DSpinBox.blockSignals(True)
        self._mw.align_2d_axis0_step_DSpinBox.setValue(step)
        self._mw.align_2d_axis0_step_DSpinBox.blockSignals(False)
        return step

    def update_align_2d_axis0_vel(self,vel):
        """ The GUT is updated taking vel into account. Thereby no signal is triggered!

        @params float: Velocity to update

        @return float: Velocity to update
         """
        self._mw.align_2d_axis0_vel_DSpinBox.blockSignals(True)
        self._mw.align_2d_axis0_vel_DSpinBox.setValue(vel)
        self._mw.align_2d_axis0_vel_DSpinBox.blockSignals(False)
        return vel

    def update_align_2d_axis1_name(self, axisname):
        """ The GUT is updated taking axisname into account. Thereby no signal is triggered!

        @params str: Axis name to update

        @return str: Axis name to update
         """
        self._mw.align_2d_axis1_name_ComboBox.blockSignals(True)
        index = self._mw.align_2d_axis1_name_ComboBox.findText(axisname)
        self._mw.align_2d_axis1_name_ComboBox.setCurrentIndex(index)
        self._mw.align_2d_axis1_name_ComboBox.blockSignals(False)
        return index

    def update_align_2d_axis1_range(self, range):
        """ The GUT is updated taking range into account. Thereby no signal is triggered!

        @params float: Range to update

        @return float: Range to update
         """
        self._mw.align_2d_axis1_range_DSpinBox.blockSignals(True)
        self._mw.align_2d_axis1_range_DSpinBox.setValue(range)
        self._mw.align_2d_axis1_range_DSpinBox.blockSignals(False)
        return range

    def update_align_2d_axis1_step(self, step):
        """ The GUT is updated taking step into account. Thereby no signal is triggered!

        @params float: Step to update in m

        @return float: Step to update in m
         """
        self._mw.align_2d_axis1_step_DSpinBox.blockSignals(True)
        self._mw.align_2d_axis1_step_DSpinBox.setValue(step)
        self._mw.align_2d_axis1_step_DSpinBox.blockSignals(False)
        return step

    def update_align_2d_axis1_vel(self,vel):
        """ The GUT is updated taking vel into account. Thereby no signal is triggered!

        @params float: Velocity to update

        @return float: Velocity to update
         """
        self._mw.align_2d_axis1_vel_DSpinBox.blockSignals(True)
        self._mw.align_2d_axis1_vel_DSpinBox.setValue(vel)
        self._mw.align_2d_axis1_vel_DSpinBox.blockSignals(False)
        return vel


    def update_optimize_pos_freq(self, freq):
        """ The GUT is updated taking freq into account. Thereby no signal is triggered!

        @params float: Frequency to update

        @return float: Frequency to update
         """
        self._mw.align_2d_fluorescence_optimize_freq_SpinBox.blockSignals(True)
        self._mw.align_2d_fluorescence_optimize_freq_SpinBox.setValue(freq)
        self._mw.align_2d_fluorescence_optimize_freq_SpinBox.blockSignals(False)
        return freq

    def update_fluorescence_integration_time(self, time):
        """ The GUT is updated taking time into account. Thereby no signal is triggered!

        @params float: Integration time to update

        @return float: Integration time to update
         """
        self._mw.align_2d_fluorescence_integrationtime_DSpinBox.blockSignals(True)
        self._mw.align_2d_fluorescence_integrationtime_DSpinBox.setValue(time)
        self._mw.align_2d_fluorescence_integrationtime_DSpinBox.blockSignals(False)
        return time

def get_ref_curr_pos_ScienDSpinBox(self, label):
    """ Get the reference to the double spin box for the passed label. """

    dspinbox_name = 'curr_pos_axis{0}_ScienDSpinBox'.format(label)
    dspinbox_ref = getattr(self._mw, dspinbox_name)
    return dspinbox_ref


def get_ref_move_rel_ScienDSpinBox(self, label):
    """ Get the reference to the double spin box for the passed label. """

    dspinbox_name = 'move_rel_axis_{0}_ScienDSpinBox'.format(label)
    dspinbox_ref = getattr(self._mw, dspinbox_name)
    return dspinbox_ref

