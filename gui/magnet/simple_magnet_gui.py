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


class MagnetMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_simple_magnet_gui.ui')

        # Load it
        super(MagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class MagnetGui(GUIBase):
    """ Main GUI for the magnet. """

    _modclass = 'MagnetGui'
    _modtype = 'gui'

    # declare connectors
    magnetlogic = Connector(interface='MagnetLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.current_pos_widgets = dict()
        self.move_abs_widgets = dict()
        self.move_rel_widgets = dict()
        self.alignment_method_radiobuttons = dict()

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._mw = MagnetMainWindow()

        # create all the needed control elements. They will manage the
        # connection with each other themselves. Note some buttons are also
        # connected within these functions because they have to be placed at
        # first in the GUI Layout, otherwise the signals will not react.
        self._create_axis_pos_disp()
        self._create_move_rel_control()
        self._create_move_abs_control()
        self._create_meas_type_RadioButtons()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

        # connect the actions of the toolbar:
        self._mw.default_view_Action.triggered.connect(self.set_default_view_main_window)

        # update the values also of the absolute movement display:
        for axis, pos in self.magnetlogic().magnet_position.items():
            self.move_abs_widgets[axis]['spinbox'].setValue(pos)
            self.current_pos_widgets[axis]['spinbox'].setValue(pos)

        # Connect signals from logic
        self.magnetlogic().sigMagnetPositionUpdated.connect(
            self.update_pos, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigMeasurementStatusUpdated.connect(
            self.measurement_status_updated, QtCore.Qt.QueuedConnection)

        # self._mw.alignment_2d_cb_min_centiles_DSpinBox.valueChanged.connect(self._update_2d_data)
        # self._mw.alignment_2d_cb_max_centiles_DSpinBox.valueChanged.connect(self._update_2d_data)
        # self._mw.alignment_2d_cb_low_centiles_DSpinBox.valueChanged.connect(self._update_2d_data)
        # self._mw.alignment_2d_cb_high_centiles_DSpinBox.valueChanged.connect(self._update_2d_data)

        # self._2d_alignment_ImageItem = pg.ImageItem(
        #     image=self._magnet_logic.get_2d_data_matrix())
        #   #  axisOrder='row-major')

        # axis0, axis1 = self._magnet_logic.get_2d_axis_arrays()
        # step0 = axis0[1]-axis0[0]
        # step1 = axis1[1] - axis1[0]
        # self._2d_alignment_ImageItem.setRect(QtCore.QRectF(axis0[0]-step0/2,
        #                                                    axis1[0]-step1/2,
        #                                                    axis0[-1]-axis0[0]+step0,
        #                                                    axis1[-1]-axis1[0]+step1,))

        # self._mw.alignment_2d_GraphicsView.addItem(self._2d_alignment_ImageItem)

        # Get the colorscales at set LUT
        # my_colors = ColorScaleInferno()

        # self._2d_alignment_ImageItem.setLookupTable(my_colors.lut)

        # Configuration of Colorbar:
        # self._2d_alignment_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        # self._mw.alignment_2d_cb_GraphicsView.addItem(self._2d_alignment_cb)
        # self._mw.alignment_2d_cb_GraphicsView.hideAxis('bottom')
        # self._mw.alignment_2d_cb_GraphicsView.hideAxis('left')

        # self._mw.alignment_2d_cb_GraphicsView.addItem(self._2d_alignment_cb)

        # self._mw.alignment_2d_cb_GraphicsView.setLabel('right',
        #     self._alignment_2d_cb_label,
        #     units=self._alignment_2d_cb_units)

        # self._update_2d_data()
        # self._update_2d_graph_cb()

        # Add save file tag input box
        self._mw.alignment_2d_nametag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.alignment_2d_nametag_LineEdit.setMaximumWidth(200)
        self._mw.alignment_2d_nametag_LineEdit.setToolTip('Enter a nametag to add to the filename.')

        self._mw.save_ToolBar.addWidget(self._mw.alignment_2d_nametag_LineEdit)
        self._mw.save_Action.triggered.connect(self.save_data)

        # Connect the buttons and inputs for the odmr colorbar
        # self._mw.alignment_2d_manual_RadioButton.clicked.connect(self._update_2d_data)
        # self._mw.alignment_2d_centiles_RadioButton.clicked.connect(self._update_2d_data)
        self._mw.run_stop_2d_alignment_Action.triggered.connect(self.run_stop_alignment)
        # self._mw.continue_2d_alignment_Action.triggered.connect(self.continue_stop_alignment)

        # General tab signals:
        self._mw.general_meas_time_doubleSpinBox.editingFinished.connect(self.general_params_changed)
        self._mw.general_save_each_checkBox.stateChanged.connect(self.general_params_changed)

        # ODMR frequency tab signals
        self._mw.odmr_low_start_freq_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)
        self._mw.odmr_low_stop_freq_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)
        self._mw.odmr_low_points_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)
        self._mw.odmr_low_power_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)

        self._mw.odmr_high_start_freq_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)
        self._mw.odmr_high_stop_freq_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)
        self._mw.odmr_high_points_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)
        self._mw.odmr_high_power_DSpinBox.editingFinished.connect(self.odmr_freq_params_changed)

        # ODMR contrast tab signals
        self._mw.odmr_start_freq_DSpinBox.editingFinished.connect(self.odmr_contrast_params_changed)
        self._mw.odmr_stop_freq_DSpinBox.editingFinished.connect(self.odmr_contrast_params_changed)
        self._mw.odmr_points_DSpinBox.editingFinished.connect(self.odmr_contrast_params_changed)
        self._mw.odmr_power_DSpinBox.editingFinished.connect(self.odmr_contrast_params_changed)
        return

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.save_Action.triggered.disconnect()
        # self._mw.alignment_2d_manual_RadioButton.clicked.disconnect()
        # self._mw.alignment_2d_centiles_RadioButton.clicked.disconnect()
        self._mw.run_stop_2d_alignment_Action.triggered.disconnect()
        # self._mw.continue_2d_alignment_Action.triggered.connect(self.continue_stop_alignment)

        # General tab signals:
        self._mw.general_meas_time_doubleSpinBox.editingFinished.disconnect()
        self._mw.general_save_each_checkBox.stateChanged.disconnect()

        # ODMR frequency tab signals
        self._mw.odmr_low_start_freq_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_low_stop_freq_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_low_points_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_low_power_DSpinBox.editingFinished.disconnect()

        self._mw.odmr_high_start_freq_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_high_stop_freq_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_high_points_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_high_power_DSpinBox.editingFinished.disconnect()

        # ODMR contrast tab signals
        self._mw.odmr_start_freq_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_stop_freq_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_points_DSpinBox.editingFinished.disconnect()
        self._mw.odmr_power_DSpinBox.editingFinished.disconnect()

        self._mw.curr_pos_get_pos_PushButton.clicked.disconnect()
        self._mw.curr_pos_stop_PushButton.clicked.disconnect()

        for widget_dict in self.move_abs_widgets.values():
            widget_dict['button'].clicked.disconnect()
        for widget_dict in self.move_rel_widgets.values():
            widget_dict['minus_button'].clicked.disconnect()
            widget_dict['plus_button'].clicked.disconnect()
        for widget in self.alignment_method_radiobuttons.values():
            widget.toggled.disconnect()

        self._mw.close()
        return

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

        # align the widget
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.curr_pos_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.move_rel_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.move_abs_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.alignment_DockWidget)
        return

    def _create_meas_type_RadioButtons(self):
        """ Create the measurement Buttons for the desired measurements:

        @return:
        """
        self.alignment_method_radiobuttons = dict()

        self._mw.alignment_2d_ButtonGroup = QtWidgets.QButtonGroup(self._mw)

        for i, method in enumerate(self.magnetlogic().available_alignment_methods):
            radiobutton = QtWidgets.QRadioButton(parent=self._mw)
            radiobutton.setText(method)
            if i == 0:
                radiobutton.setChecked(True)
            self._mw.alignment_2d_ButtonGroup.addButton(radiobutton)
            self._mw.alignment_2d_ToolBar.addWidget(radiobutton)
            self.alignment_method_radiobuttons[method] = radiobutton
            radiobutton.toggled.connect(self.alignment_method_changed)
        return

    def _create_axis_pos_disp(self):
        """ Create the axis position display.
        """
        self.current_pos_widgets = dict()
        # set the parameters in the curr_pos_DockWidget:
        for index, (axis, axis_dict) in enumerate(self.magnetlogic().magnet_constraints.items()):
            # Set the QLabel according to the grid
            label = QtWidgets.QLabel(parent=self._mw.curr_pos_DockWidgetContents)
            label.setText('{0}:'.format(axis))
            label.setAlignment(QtCore.Qt.AlignRight)
            self._mw.curr_pos_GridLayout.addWidget(label, index, 0, 1, 1)

            # Set the ScienDSpinBox according to the grid
            spinbox = ScienDSpinBox(parent=self._mw.curr_pos_DockWidgetContents)
            spinbox.setReadOnly(True)
            spinbox.setSuffix(axis_dict['unit'])
            spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            spinbox.setMaximum(np.inf)
            spinbox.setMinimum(-np.inf)
            self._mw.curr_pos_GridLayout.addWidget(spinbox, index, 1, 1, 1)

            self.current_pos_widgets[axis] = {'label': label, 'spinbox': spinbox}

        extension = len(self.current_pos_widgets)
        self._mw.curr_pos_GridLayout.addWidget(
            self._mw.curr_pos_get_pos_PushButton, 0, 2, extension, 1)
        self._mw.curr_pos_GridLayout.addWidget(
            self._mw.curr_pos_stop_PushButton, 0, 3, extension, 1)
        self._mw.curr_pos_get_pos_PushButton.clicked.connect(self.update_pos)
        self._mw.curr_pos_stop_PushButton.clicked.connect(self.stop_movement)
        return

    def _create_move_rel_control(self):
        """ Create all the gui elements to control a relative movement.
        """
        self.move_rel_widgets = dict()
        # set the parameters in the curr_pos_DockWidget:
        for index, (axis, axis_dict) in enumerate(self.magnetlogic().magnet_constraints.items()):
            # Create the QLabel
            label = QtWidgets.QLabel(parent=self._mw.move_rel_DockWidgetContents)
            label.setText('{0}:'.format(axis))
            label.setAlignment(QtCore.Qt.AlignRight)
            self._mw.move_rel_GridLayout.addWidget(label, index, 0, 1, 1)

            # Create the ScienDSpinBox
            spinbox = ScienDSpinBox(parent=self._mw.move_rel_DockWidgetContents)
            spinbox.setSuffix(axis_dict['unit'])
            spinbox.setMinimum(axis_dict['pos_min'])
            spinbox.setMaximum(axis_dict['pos_max'])
            self._mw.move_rel_GridLayout.addWidget(spinbox, index, 1, 1, 1)

            # Create the minus button
            minus_button = QtWidgets.QPushButton(parent=self._mw.move_rel_DockWidgetContents)
            minus_button.setText('-{0}'.format(axis))
            minus_button.setObjectName('move_minus_rel_{0}'.format(axis))
            self._mw.move_rel_GridLayout.addWidget(minus_button, index, 2, 1, 1)
            minus_button.clicked.connect(self.move_rel)

            # Create the plus button
            plus_button = QtWidgets.QPushButton(parent=self._mw.move_rel_DockWidgetContents)
            plus_button.setText('+{0}'.format(axis))
            plus_button.setObjectName('move_plus_rel_{0}'.format(axis))
            self._mw.move_rel_GridLayout.addWidget(plus_button, index, 3, 1, 1)
            plus_button.clicked.connect(self.move_rel)

            self.move_rel_widgets[axis] = {'label': label,
                                           'spinbox': spinbox,
                                           'minus_button': minus_button,
                                           'plus_button': plus_button}
        return

    def _create_move_abs_control(self):
        """ Create all the GUI elements to control a relative movement.
        """
        self.move_abs_widgets = dict()
        # set the parameters in the curr_pos_DockWidget:
        for index, (axis, axis_dict) in enumerate(self.magnetlogic().magnet_constraints.items()):
            # Create the QLabel
            label = QtWidgets.QLabel(parent=self._mw.move_abs_DockWidgetContents)
            label.setText('{0}:'.format(axis))
            label.setAlignment(QtCore.Qt.AlignRight)
            self._mw.move_abs_GridLayout.addWidget(label, index, 0, 1, 1)

            # Create the ScienDSpinBox
            spinbox = ScienDSpinBox(parent=self._mw.move_abs_DockWidgetContents)
            spinbox.setSuffix(axis_dict['unit'])
            spinbox.setMinimum(axis_dict['pos_min'])
            spinbox.setMaximum(axis_dict['pos_max'])
            self._mw.move_abs_GridLayout.addWidget(spinbox, index, 1, 1, 1)

            # Create the minus button
            button = QtWidgets.QPushButton(parent=self._mw.move_abs_DockWidgetContents)
            button.setText('move {0}'.format(axis))
            button.setObjectName('move_abs_{0}'.format(axis))
            self._mw.move_abs_GridLayout.addWidget(button, index, 2, 1, 1)
            button.clicked.connect(self.move_abs)

            self.move_abs_widgets[axis] = {'label': label, 'spinbox': spinbox, 'button': button}
        return

    @QtCore.Slot()
    def move_rel(self):
        """ Move relative by the axis determined from sender
        """
        button_name = self.sender().objectName()
        if not button_name.startswith('move_') or '_rel_' not in button_name:
            self.log.warning('Unknown caller for move_rel: "{0}".'.format(button_name))
            return
        axis = button_name.rsplit('_', 1)[-1]
        value = self.move_rel_widgets[axis]['spinbox'].value()
        if button_name.startswith('move_minus_'):
            value *= -1

        self.magnetlogic().move_magnet_rel({axis: value})
        return

    @QtCore.Slot()
    def move_abs(self):
        """ Perform an absolute movement.
        """
        button_name = self.sender().objectName()
        if not button_name.startswith('move_abs_'):
            self.log.warning('Unknown caller for move_abs: "{0}".'.format(button_name))
            return
        axis = button_name.rsplit('_', 1)[-1]
        value = self.move_abs_widgets[axis]['spinbox'].value()

        self.magnetlogic().move_magnet_abs({axis: value})
        return

    def general_params_changed(self):
        """

        """
        param_dict = dict()
        param_dict['measurement_time'] = self._mw.general_meas_time_doubleSpinBox.value()
        param_dict['save_after_measure'] = self._mw.general_save_each_checkBox.isChecked()
        self.magnetlogic().set_general_parameters(param_dict)
        return

    def odmr_freq_params_changed(self):
        """

        """
        param_dict = dict()
        param_dict['low_freq_range'] = (float(self._mw.odmr_low_start_freq_DSpinBox.value()),
                                        float(self._mw.odmr_low_stop_freq_DSpinBox.value()))
        param_dict['low_points'] = int(self._mw.odmr_low_points_DSpinBox.value())
        param_dict['low_power'] = float(self._mw.odmr_low_power_DSpinBox.value())
        param_dict['high_freq_range'] = (float(self._mw.odmr_high_start_freq_DSpinBox.value()),
                                         float(self._mw.odmr_high_stop_freq_DSpinBox.value()))
        param_dict['high_points'] = int(self._mw.odmr_high_points_DSpinBox.value())
        param_dict['high_power'] = float(self._mw.odmr_high_power_DSpinBox.value())

        self.magnetlogic().set_odmr_frequency_parameters(param_dict)
        return

    def odmr_contrast_params_changed(self):
        """

        """
        param_dict = dict()
        param_dict['freq_range'] = (float(self._mw.odmr_start_freq_DSpinBox.value()),
                                        float(self._mw.odmr_stop_freq_DSpinBox.value()))
        param_dict['points'] = int(self._mw.odmr_points_DSpinBox.value())
        param_dict['power'] = float(self._mw.odmr_power_DSpinBox.value())

        self.magnetlogic().set_odmr_contrast_parameters(param_dict)
        return

    def stop_movement(self):
        """ Invokes an immediate stop of the hardware.
        """
        self.magnetlogic().abort_movement()
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_pos(self, pos_dict=None):
        """ Update the current position.
        """
        if not isinstance(pos_dict, dict):
            pos_dict = self.magnetlogic().magnet_position

        for axis, pos in pos_dict.items():
            self.current_pos_widgets[axis]['spinbox'].setValue(pos)
        return

    def run_stop_alignment(self, is_checked):
        """ Manage what happens if 2d magnet scan is started/stopped

        @param bool is_checked: state if the current scan, True = started,
                                False = stopped
        """
        if is_checked:
            self.general_params_changed()
            for method, button in self.alignment_method_radiobuttons.items():
                if button.isChecked():
                    break
            if method.lower() == 'odmr_frequency':
                self.odmr_freq_params_changed()
            elif method.lower() == 'odmr_contrast':
                self.odmr_contrast_params_changed()

            self.magnetlogic().start_measurement()
        else:
            self.magnetlogic().stop_measurement()
        return

    @QtCore.Slot(bool, bool)
    def measurement_status_updated(self, is_running, is_paused):
        """ Changes every display component back to the stopped state. """
        self._mw.run_stop_alignment_Action.blockSignals(True)
        self._mw.run_stop_alignment_Action.setChecked(is_running)
        self._mw.run_stop_alignment_Action.blockSignals(False)

        self._mw.continue_2d_alignment_Action.blockSignals(True)
        self._mw.continue_2d_alignment_Action.setChecked(is_paused)
        self._mw.continue_2d_alignment_Action.blockSignals(False)
        return

    def alignment_method_changed(self):
        """ According to the selected Radiobox a measurement type will be chosen."""
        for method, button in self.alignment_method_radiobuttons.items():
            if button.isChecked():
                self.magnetlogic().set_alignment_method(method)
                break
        return

    def save_data(self):
        """

        """
        tag = self._mw.alignment_2d_nametag_LineEdit.text()
        self.magnetlogic().save_2d_data(tag)
        return
