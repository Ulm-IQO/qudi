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

    # declare signals
    sigToggleMeasurement = QtCore.Signal(bool)
    sigAlignmentParametersChanged = QtCore.Signal(str, dict)
    sigGeneralParametersChanged = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.current_pos_widgets = dict()
        self.move_abs_widgets = dict()
        self.move_rel_widgets = dict()
        self.alignment_param_widgets = dict()
        self.alignment_param_changed_methods = dict()

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._mw = MagnetMainWindow()

        # Automatically create GUI elements from axis constraints
        self._create_axis_pos_disp()
        self._create_move_rel_control()
        self._create_move_abs_control()

        # Initialize general parameter widgets (constraints and values)
        self._init_general_parameters()

        # Automatically create GUI elements from alignment parameter objects
        self._create_alignment_parameter_tabs()
        # Automatically create value changed methods for the widgets created above to connect to.
        self._create_parameter_changed_methods()
        # Initialize the automatically created widgets with values from logic
        self._init_alignment_parameters()

        # Add save file tag input box
        self._mw.save_nametag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_nametag_LineEdit.setMaximumWidth(400)
        self._mw.save_nametag_LineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                     QtWidgets.QSizePolicy.Fixed)
        self._mw.save_nametag_LineEdit.setToolTip('Enter a nametag to add to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_nametag_LineEdit)

        # Initialize the values of the absolute movement and current position displays:
        for axis, pos in self.magnetlogic().magnet_position.items():
            self.move_abs_widgets[axis]['spinbox'].setValue(pos)
            self.current_pos_widgets[axis]['spinbox'].setValue(pos)

        # Initialize dockwidget layout
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

        # Connect toolbar/menu actions
        self._mw.default_view_Action.triggered.connect(self.set_default_view_main_window)
        self._mw.save_Action.triggered.connect(self.save_data)
        self._mw.run_stop_alignment_Action.toggled.connect(self.run_stop_alignment)
        self._mw.continue_alignment_Action.toggled.connect(
            self.magnetlogic().toggle_measurement_pause, QtCore.Qt.QueuedConnection)

        # Connect update signals from logic
        self.magnetlogic().sigMagnetPositionUpdated.connect(
            self.magnet_position_updated, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigMeasurementStatusUpdated.connect(
            self.measurement_status_updated, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigMagnetMoving.connect(
            self.magnet_moving_updated, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigMagnetVelocityUpdated.connect(
            self.magnet_velocity_updated, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigAlignmentParametersUpdated.connect(
            self.alignment_parameters_updated, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigGeneralParametersUpdated.connect(
            self.general_parameters_updated, QtCore.Qt.QueuedConnection)
        self.magnetlogic().sigDataUpdated.connect(
            self.update_plot_data, QtCore.Qt.QueuedConnection)

        # Connect control signals to logic
        self.sigToggleMeasurement.connect(
            self.magnetlogic().toggle_measurement, QtCore.Qt.QueuedConnection)
        self.sigAlignmentParametersChanged.connect(
            self.magnetlogic().set_alignment_parameters, QtCore.Qt.QueuedConnection)
        self.sigGeneralParametersChanged.connect(
            self.magnetlogic().set_general_parameters, QtCore.Qt.QueuedConnection)

        # Connect general parameter widgets
        self._mw.general_method_comboBox.currentIndexChanged.connect(
            self.general_parameters_changed)
        self._mw.general_pathmode_comboBox.currentIndexChanged.connect(
            self.general_parameters_changed)
        self._mw.general_x_axis_comboBox.currentIndexChanged.connect(
            self.general_parameters_changed)
        self._mw.general_y_axis_comboBox.currentIndexChanged.connect(
            self.general_parameters_changed)
        self._mw.general_x_start_doubleSpinBox.editingFinished.connect(
            self.general_parameters_changed)
        self._mw.general_y_start_doubleSpinBox.editingFinished.connect(
            self.general_parameters_changed)
        self._mw.general_x_stop_doubleSpinBox.editingFinished.connect(
            self.general_parameters_changed)
        self._mw.general_y_stop_doubleSpinBox.editingFinished.connect(
            self.general_parameters_changed)
        self._mw.general_x_points_spinBox.editingFinished.connect(self.general_parameters_changed)
        self._mw.general_y_points_spinBox.editingFinished.connect(self.general_parameters_changed)
        self._mw.general_measurement_time_doubleSpinBox.editingFinished.connect(
            self.general_parameters_changed)
        self._mw.general_save_measurements_checkBox.stateChanged.connect(
            self.general_parameters_changed)

        # Connect alignment method parameter widgets
        for method, widget_dict in self.alignment_param_widgets.items():
            for widget in widget_dict.values():
                if hasattr(widget, 'editingFinished'):
                    widget.editingFinished.connect(self.alignment_param_changed_methods[method])
                elif hasattr(widget, 'stateChanged'):
                    widget.stateChanged.connect(self.alignment_param_changed_methods[method])
                else:
                    self.log.error('Failed to connect "{0}" changed signal. Unknown widget type.'
                                   ''.format(widget.objectName()))

        # Connect axis position/movement signals
        self._mw.curr_pos_get_pos_PushButton.clicked.connect(
            self.magnetlogic().update_magnet_position, QtCore.Qt.QueuedConnection)
        self._mw.curr_pos_stop_PushButton.clicked.connect(
            self.magnetlogic().abort_movement, QtCore.Qt.DirectConnection)
        for widget_dict in self.move_abs_widgets.values():
            widget_dict['button'].clicked.connect(self.move_abs)
        for widget_dict in self.move_rel_widgets.values():
            widget_dict['minus_button'].clicked.connect(self.move_rel)
            widget_dict['plus_button'].clicked.connect(self.move_rel)


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

        # Connect the buttons and inputs for the odmr colorbar
        # self._mw.alignment_2d_manual_RadioButton.clicked.connect(self._update_2d_data)
        # self._mw.alignment_2d_centiles_RadioButton.clicked.connect(self._update_2d_data)

        return

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        # Disconnect update signals from logic
        self.magnetlogic().sigMagnetPositionUpdated.disconnect()
        self.magnetlogic().sigMeasurementStatusUpdated.disconnect()
        self.magnetlogic().sigMagnetMoving.disconnect()
        self.magnetlogic().sigMagnetVelocityUpdated.disconnect()
        self.magnetlogic().sigAlignmentParametersUpdated.disconnect()
        self.magnetlogic().sigGeneralParametersUpdated.disconnect()
        self.magnetlogic().sigDataUpdated.disconnect()

        # Disconnect control signals to logic
        self.sigToggleMeasurement.disconnect()
        self.sigAlignmentParametersChanged.disconnect()
        self.sigGeneralParametersChanged.disconnect()

        # Disconnect general parameter widgets
        self._mw.general_method_comboBox.currentIndexChanged.disconnect()
        self._mw.general_pathmode_comboBox.currentIndexChanged.disconnect()
        self._mw.general_x_axis_comboBox.currentIndexChanged.disconnect()
        self._mw.general_y_axis_comboBox.currentIndexChanged.disconnect()
        self._mw.general_x_start_doubleSpinBox.editingFinished.disconnect()
        self._mw.general_y_start_doubleSpinBox.editingFinished.disconnect()
        self._mw.general_x_stop_doubleSpinBox.editingFinished.disconnect()
        self._mw.general_y_stop_doubleSpinBox.editingFinished.disconnect()
        self._mw.general_x_points_spinBox.editingFinished.disconnect()
        self._mw.general_y_points_spinBox.editingFinished.disconnect()
        self._mw.general_measurement_time_doubleSpinBox.editingFinished.disconnect()
        self._mw.general_save_measurements_checkBox.stateChanged.disconnect()

        # Disconnect toolbar/menu actions
        self._mw.default_view_Action.triggered.disconnect()
        self._mw.save_Action.triggered.disconnect()
        self._mw.run_stop_alignment_Action.toggled.disconnect()
        self._mw.continue_alignment_Action.toggled.disconnect()

        # Disconnect alignment method parameter widgets
        for method, widget_dict in self.alignment_param_widgets.items():
            for widget in widget_dict.values():
                if hasattr(widget, 'editingFinished'):
                    widget.editingFinished.disconnect()
                elif hasattr(widget, 'stateChanged'):
                    widget.stateChanged.disconnect()

        # Disconnect axis position/movement signals
        self._mw.curr_pos_get_pos_PushButton.clicked.disconnect()
        self._mw.curr_pos_stop_PushButton.clicked.disconnect()
        for widget_dict in self.move_abs_widgets.values():
            widget_dict['button'].clicked.disconnect()
        for widget_dict in self.move_rel_widgets.values():
            widget_dict['minus_button'].clicked.disconnect()
            widget_dict['plus_button'].clicked.disconnect()

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
        self._mw.parameters_DockWidget.setFloating(False)

        # align the widget
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(
            QtCore.Qt.LeftDockWidgetArea), self._mw.curr_pos_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(
            QtCore.Qt.LeftDockWidgetArea), self._mw.move_rel_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(
            QtCore.Qt.LeftDockWidgetArea), self._mw.move_abs_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(
            QtCore.Qt.RightDockWidgetArea), self._mw.parameters_DockWidget)

        # Adjust dockwidget size
        dockwidget_size = QtCore.QSize(self._mw.size().width() / 4, self._mw.size().height() / 3)
        self._mw.resizeDocks([self._mw.parameters_DockWidget,
                              self._mw.curr_pos_DockWidget,
                              self._mw.move_rel_DockWidget,
                              self._mw.move_abs_DockWidget],
                             [dockwidget_size.width()]*4,
                             QtCore.Qt.Horizontal)
        self._mw.resizeDocks([self._mw.curr_pos_DockWidget,
                              self._mw.move_rel_DockWidget,
                              self._mw.move_abs_DockWidget],
                             [dockwidget_size.height()] * 3,
                             QtCore.Qt.Vertical)
        self._mw.resizeDocks([self._mw.parameters_DockWidget],
                             [self._mw.size().height()],
                             QtCore.Qt.Vertical)
        return

    def _init_general_parameters(self):
        """
        Initialize the general alignment parameters tab.
        Set constraints for widgets and fill comboboxes.
        """
        # Populate ComboBoxes
        self._mw.general_method_comboBox.clear()
        self._mw.general_method_comboBox.addItems(self.magnetlogic().available_alignment_methods)

        self._mw.general_pathmode_comboBox.clear()
        self._mw.general_pathmode_comboBox.addItems(self.magnetlogic().available_path_modes)

        self._mw.general_x_axis_comboBox.clear()
        self._mw.general_x_axis_comboBox.addItems(self.magnetlogic().available_axes_names)
        self._mw.general_y_axis_comboBox.clear()
        self._mw.general_y_axis_comboBox.addItems(self.magnetlogic().available_axes_names)

        # Set fixed constraints for SpinBoxes
        self._mw.general_x_points_spinBox.setMinimum(2)
        self._mw.general_x_points_spinBox.setMaximum(2**31-1)
        self._mw.general_y_points_spinBox.setMinimum(2)
        self._mw.general_y_points_spinBox.setMaximum(2**31 - 1)

        # Configure and initialize (Double)SpinBoxes as well as setting constraints
        self.general_parameters_updated()
        return

    def _init_alignment_parameters(self):
        """
        Initialize the automatically generated widgets for the method-specific alignment parameters.
        """
        for method, param_dict in self.magnetlogic().alignment_parameters.items():
            if method not in self.alignment_param_widgets:
                continue
            self.alignment_parameters_updated(method=method, param_dict=param_dict)
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
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            # label.setAlignment(QtCore.Qt.AlignVCenter)
            self._mw.curr_pos_gridLayout.addWidget(label, index, 0, 1, 1)

            # Set the ScienDSpinBox according to the grid
            spinbox = ScienDSpinBox(parent=self._mw.curr_pos_DockWidgetContents)
            spinbox.setReadOnly(True)
            spinbox.setSuffix(axis_dict['unit'])
            spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            spinbox.setMaximum(np.inf)
            spinbox.setMinimum(-np.inf)
            spinbox.setDecimals(6)
            spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._mw.curr_pos_gridLayout.addWidget(spinbox, index, 1, 1, 1)

            self.current_pos_widgets[axis] = {'label': label, 'spinbox': spinbox}
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
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_rel_GridLayout.addWidget(label, index, 0, 1, 1)

            # Create the ScienDSpinBox
            spinbox = ScienDSpinBox(parent=self._mw.move_rel_DockWidgetContents)
            spinbox.setSuffix(axis_dict['unit'])
            spinbox.setMinimum(axis_dict['pos_min'])
            spinbox.setMaximum(axis_dict['pos_max'])
            spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_rel_GridLayout.addWidget(spinbox, index, 1, 1, 1)

            # Create the minus button
            minus_button = QtWidgets.QPushButton(parent=self._mw.move_rel_DockWidgetContents)
            minus_button.setText('-{0}'.format(axis))
            minus_button.setObjectName('move_minus_rel_{0}'.format(axis))
            minus_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_rel_GridLayout.addWidget(minus_button, index, 2, 1, 1)

            # Create the plus button
            plus_button = QtWidgets.QPushButton(parent=self._mw.move_rel_DockWidgetContents)
            plus_button.setText('+{0}'.format(axis))
            plus_button.setObjectName('move_plus_rel_{0}'.format(axis))
            plus_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_rel_GridLayout.addWidget(plus_button, index, 3, 1, 1)

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
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_abs_GridLayout.addWidget(label, index, 0, 1, 1)

            # Create the ScienDSpinBox
            spinbox = ScienDSpinBox(parent=self._mw.move_abs_DockWidgetContents)
            spinbox.setSuffix(axis_dict['unit'])
            spinbox.setMinimum(axis_dict['pos_min'])
            spinbox.setMaximum(axis_dict['pos_max'])
            spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_abs_GridLayout.addWidget(spinbox, index, 1, 1, 1)

            # Create the minus button
            button = QtWidgets.QPushButton(parent=self._mw.move_abs_DockWidgetContents)
            button.setText('move {0}'.format(axis))
            button.setObjectName('move_abs_{0}'.format(axis))
            button.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self._mw.move_abs_GridLayout.addWidget(button, index, 2, 1, 1)

            self.move_abs_widgets[axis] = {'label': label, 'spinbox': spinbox, 'button': button}
        return

    def _create_alignment_parameter_tabs(self):
        """

        """
        self.alignment_param_widgets = dict()

        for method, params_dict in self.magnetlogic().alignment_parameter_signatures.items():
            # Create no tab if no additional parameters (additional to general params) are needed.
            if not params_dict:
                continue

            # Create dict to store references to input widgets and parameter names as keys
            self.alignment_param_widgets[method] = dict()

            # Create new tab widget
            tab_widget = QtWidgets.QWidget()
            layout = QtWidgets.QGridLayout()
            for index, (param_name, param_dict) in enumerate(params_dict.items()):
                # Create label
                label = QtWidgets.QLabel(param_name + ':')
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

                # Create input widget
                if param_dict['type'] is float:
                    widget = ScienDSpinBox()
                    if param_dict['unit']:
                        widget.setSuffix(param_dict['unit'])
                    if param_dict['min']:
                        widget.setMinimum(param_dict['min'])
                    if param_dict['max']:
                        widget.setMaximum(param_dict['max'])
                elif param_dict['type'] is int:
                    widget = QtWidgets.QSpinBox()
                    if param_dict['unit']:
                        widget.setSuffix(param_dict['unit'])
                    if param_dict['min']:
                        if param_dict['min'] < -(2**31 - 1):
                            widget.setMinimum(-(2**31 - 1))
                        else:
                            widget.setMinimum(param_dict['min'])
                    if param_dict['max']:
                        if param_dict['max'] > 2**31 - 1:
                            widget.setMaximum(2**31 - 1)
                        else:
                            widget.setMaximum(param_dict['max'])
                elif param_dict['type'] is bool:
                    widget = QtWidgets.QCheckBox()
                elif param_dict['type'] is str:
                    widget = QtWidgets.QLineEdit()
                else:
                    self.log.error('Unknown input type for alignment method "{0}" parameter "{1}": '
                                   '{2}'.format(method, param_name, str(param_dict['type'])))
                    return
                widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                widget.setObjectName('{0}_{1}_widget'.format(method, param_name))

                # Add label and widget to layout
                layout.addWidget(label, index, 0, 1, 1)
                layout.addWidget(widget, index, 1, 1, 1)
                # Add widget to alignment_param_widgets dict
                self.alignment_param_widgets[method][param_name] = widget

            # Add spacer to layout
            spacer = QtWidgets.QSpacerItem(20, 40,
                                           QtWidgets.QSizePolicy.Minimum,
                                           QtWidgets.QSizePolicy.Expanding)
            layout.addItem(spacer, index+1, 0, 1, 1)
            # Assign layout to tab_widget
            tab_widget.setLayout(layout)
            # Add tab to TabWidget
            self._mw.parameters_tabWidget.addTab(tab_widget, method)
        return

    def _create_parameter_changed_methods(self):
        self.alignment_param_changed_methods = dict()
        for method in self.alignment_param_widgets:
            method_name = '{0}_alignment_parameters_changed'.format(method)
            setattr(MagnetGui, method_name, self.__get_parameter_changed_method(method))
            self.alignment_param_changed_methods[method] = getattr(self, method_name)
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

    @QtCore.Slot(bool)
    def magnet_moving_updated(self, is_moving):
        self._mw.run_stop_alignment_Action.setEnabled(not is_moving)
        self._mw.continue_alignment_Action.setEnabled(not is_moving)
        return

    def set_axis_constraints(self, axis_names=None):
        if axis_names is None:
            axis_names = self.magnetlogic().current_align_axes

        constr = self.magnetlogic().magnet_constraints

        self._mw.general_x_start_doubleSpinBox.blockSignals(True)
        old_val = self._mw.general_x_start_doubleSpinBox.value()
        self._mw.general_x_start_doubleSpinBox.setMinimum(constr[axis_names[0]]['pos_min'])
        self._mw.general_x_start_doubleSpinBox.setMaximum(constr[axis_names[0]]['pos_max'])
        self._mw.general_x_start_doubleSpinBox.setSuffix(constr[axis_names[0]]['unit'])
        if old_val != self._mw.general_x_start_doubleSpinBox.value():
            self._mw.general_x_start_doubleSpinBox.setValue(
                self.magnetlogic().current_align_ranges[0][0])
        self._mw.general_x_start_doubleSpinBox.blockSignals(False)

        self._mw.general_y_start_doubleSpinBox.blockSignals(True)
        old_val = self._mw.general_y_start_doubleSpinBox.value()
        self._mw.general_y_start_doubleSpinBox.setMinimum(constr[axis_names[1]]['pos_min'])
        self._mw.general_y_start_doubleSpinBox.setMaximum(constr[axis_names[1]]['pos_max'])
        self._mw.general_y_start_doubleSpinBox.setSuffix(constr[axis_names[1]]['unit'])
        if old_val != self._mw.general_y_start_doubleSpinBox.value():
            self._mw.general_y_start_doubleSpinBox.setValue(
                self.magnetlogic().current_align_ranges[1][0])
        self._mw.general_y_start_doubleSpinBox.blockSignals(False)

        self._mw.general_x_stop_doubleSpinBox.blockSignals(True)
        old_val = self._mw.general_x_stop_doubleSpinBox.value()
        self._mw.general_x_stop_doubleSpinBox.setMinimum(constr[axis_names[0]]['pos_min'])
        self._mw.general_x_stop_doubleSpinBox.setMaximum(constr[axis_names[0]]['pos_max'])
        self._mw.general_x_stop_doubleSpinBox.setSuffix(constr[axis_names[0]]['unit'])
        if old_val != self._mw.general_x_stop_doubleSpinBox.value():
            self._mw.general_x_stop_doubleSpinBox.setValue(
                self.magnetlogic().current_align_ranges[0][1])
        self._mw.general_x_stop_doubleSpinBox.blockSignals(False)

        self._mw.general_y_stop_doubleSpinBox.blockSignals(True)
        old_val = self._mw.general_y_stop_doubleSpinBox.value()
        self._mw.general_y_stop_doubleSpinBox.setMinimum(constr[axis_names[1]]['pos_min'])
        self._mw.general_y_stop_doubleSpinBox.setMaximum(constr[axis_names[1]]['pos_max'])
        self._mw.general_y_stop_doubleSpinBox.setSuffix(constr[axis_names[1]]['unit'])
        if old_val != self._mw.general_y_stop_doubleSpinBox.value():
            self._mw.general_y_stop_doubleSpinBox.setValue(
                self.magnetlogic().current_align_ranges[1][1])
        self._mw.general_y_stop_doubleSpinBox.blockSignals(False)
        return

    @QtCore.Slot()
    def general_parameters_changed(self, send_all=False):
        """

        """
        obj_name = self.sender().objectName() if not send_all else ''

        param_dict = dict()
        if obj_name.startswith('general_method') or send_all:
            param_dict['alignment_method'] = self._mw.general_method_comboBox.currentText()
        if obj_name.startswith('general_pathmode') or send_all:
            param_dict['pathway_mode'] = self._mw.general_pathmode_comboBox.currentText()
        if obj_name.startswith(('general_x_axis', 'general_y_axis')) or send_all:
            param_dict['axis_names'] = (self._mw.general_x_axis_comboBox.currentText(),
                                        self._mw.general_y_axis_comboBox.currentText())
        if obj_name.startswith(('general_x_start', 'general_y_start', 'general_x_stop', 'general_y_stop')) or send_all:
            param_dict['axis_ranges'] = ((self._mw.general_x_start_doubleSpinBox.value(),
                                          self._mw.general_x_stop_doubleSpinBox.value()),
                                         (self._mw.general_y_start_doubleSpinBox.value(),
                                          self._mw.general_y_stop_doubleSpinBox.value()))
        if obj_name.startswith(('general_x_points', 'general_y_points')) or send_all:
            param_dict['axis_points'] = (self._mw.general_x_points_spinBox.value(),
                                         self._mw.general_y_points_spinBox.value())
        if obj_name.startswith('general_measurement_time') or send_all:
            param_dict['measurement_time'] = self._mw.general_measurement_time_doubleSpinBox.value()
        if obj_name.startswith('general_save_measurements') or send_all:
            param_dict[
                'save_measurements'] = self._mw.general_save_measurements_checkBox.isChecked()

        self.sigGeneralParametersChanged.emit(param_dict)
        return

    @QtCore.Slot(dict)
    def general_parameters_updated(self, param_dict=None):
        if param_dict is None:
            param_dict = self.magnetlogic().general_parameters

        if 'axis_names' in param_dict:
            self._mw.general_x_axis_comboBox.blockSignals(True)
            self._mw.general_y_axis_comboBox.blockSignals(True)
            self._mw.general_x_axis_comboBox.setCurrentText(param_dict['axis_names'][0])
            self._mw.general_y_axis_comboBox.setCurrentText(param_dict['axis_names'][1])
            self._mw.general_x_axis_comboBox.blockSignals(False)
            self._mw.general_y_axis_comboBox.blockSignals(False)
            self.set_axis_constraints(param_dict['axis_names'])
        if 'measurement_time' in param_dict:
            self._mw.general_measurement_time_doubleSpinBox.blockSignals(True)
            self._mw.general_measurement_time_doubleSpinBox.setValue(param_dict['measurement_time'])
            self._mw.general_measurement_time_doubleSpinBox.blockSignals(False)
        if 'save_measurements' in param_dict:
            self._mw.general_save_measurements_checkBox.blockSignals(True)
            self._mw.general_save_measurements_checkBox.setChecked(param_dict['save_measurements'])
            self._mw.general_save_measurements_checkBox.blockSignals(False)
        if 'alignment_method' in param_dict:
            self._mw.general_method_comboBox.blockSignals(True)
            self._mw.general_method_comboBox.setCurrentText(param_dict['alignment_method'])
            self._mw.general_method_comboBox.blockSignals(False)
        if 'pathway_mode' in param_dict:
            self._mw.general_pathmode_comboBox.blockSignals(True)
            self._mw.general_pathmode_comboBox.setCurrentText(param_dict['pathway_mode'])
            self._mw.general_pathmode_comboBox.blockSignals(False)
        if 'axis_points' in param_dict:
            self._mw.general_x_points_spinBox.blockSignals(True)
            self._mw.general_y_points_spinBox.blockSignals(True)
            self._mw.general_x_points_spinBox.setValue(param_dict['axis_points'][0])
            self._mw.general_y_points_spinBox.setValue(param_dict['axis_points'][1])
            self._mw.general_x_points_spinBox.blockSignals(False)
            self._mw.general_y_points_spinBox.blockSignals(False)
        if 'axis_ranges' in param_dict:
            self._mw.general_x_start_doubleSpinBox.blockSignals(True)
            self._mw.general_y_start_doubleSpinBox.blockSignals(True)
            self._mw.general_x_stop_doubleSpinBox.blockSignals(True)
            self._mw.general_y_stop_doubleSpinBox.blockSignals(True)
            self._mw.general_x_start_doubleSpinBox.setValue(param_dict['axis_ranges'][0][0])
            self._mw.general_y_start_doubleSpinBox.setValue(param_dict['axis_ranges'][1][0])
            self._mw.general_x_stop_doubleSpinBox.setValue(param_dict['axis_ranges'][0][1])
            self._mw.general_y_stop_doubleSpinBox.setValue(param_dict['axis_ranges'][1][1])
            self._mw.general_x_start_doubleSpinBox.blockSignals(False)
            self._mw.general_y_start_doubleSpinBox.blockSignals(False)
            self._mw.general_x_stop_doubleSpinBox.blockSignals(False)
            self._mw.general_y_stop_doubleSpinBox.blockSignals(False)
        return

    @QtCore.Slot(str, dict)
    def alignment_parameters_updated(self, method, param_dict):
        for param, value in param_dict.items():
            widget = self.alignment_param_widgets[method][param]
            widget.blockSignals(True)
            if hasattr(widget, 'setValue'):
                widget.setValue(value)
            elif hasattr(widget, 'setChecked'):
                widget.setChecked(value)
            elif hasattr(widget, 'setText'):
                widget.setText(value)
            else:
                self.log.error('Unable to set value "{0}" for parameter "{1}" in widget "{2}". '
                               'Unknown widget/data type.'
                               ''.format(value, param, widget.objectName()))
            widget.blockSignals(False)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def magnet_position_updated(self, pos_dict=None):
        """ Update the current position.
        """
        if not isinstance(pos_dict, dict):
            pos_dict = self.magnetlogic().magnet_position

        for axis, pos in pos_dict.items():
            self.current_pos_widgets[axis]['spinbox'].setValue(pos)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def magnet_velocity_updated(self, vel_dict=None):
        """ Update the current velocity.
        """
        if not isinstance(vel_dict, dict):
            vel_dict = self.magnetlogic().magnet_velocity

        for axis, vel in vel_dict.items():
            pass
            # self.current_pos_widgets[axis]['spinbox'].setValue(pos)
        return

    @QtCore.Slot(np.ndarray, tuple)
    def update_plot_data(self, image, img_ranges):
        pass

    @QtCore.Slot(bool)
    def run_stop_alignment(self, is_checked):
        """ Manage what happens if 2d magnet scan is started/stopped

        @param bool is_checked: state if the current scan, True = started,
                                False = stopped
        """
        if is_checked:
            self.general_parameters_changed(True)
            # FIXME: Send alignment parameters to logic

        self.sigToggleMeasurement.emit(is_checked)
        return

    @QtCore.Slot(bool, bool)
    def measurement_status_updated(self, is_running, is_paused):
        """ Changes every display component back to the stopped state. """
        self._mw.run_stop_alignment_Action.blockSignals(True)
        self._mw.run_stop_alignment_Action.setChecked(is_running)
        self._mw.run_stop_alignment_Action.blockSignals(False)

        self._mw.continue_alignment_Action.blockSignals(True)
        self._mw.continue_alignment_Action.setEnabled(is_running)
        self._mw.continue_alignment_Action.setChecked(is_paused)
        self._mw.continue_alignment_Action.blockSignals(False)
        return

    @QtCore.Slot()
    def save_data(self):
        """

        """
        tag = self._mw.save_nametag_LineEdit.text()
        self.magnetlogic().save_data(tag)
        return

    @staticmethod
    def __get_parameter_changed_method(method):
        """
        Create a instance/bound method to attach to MagnetGui class.
        This method can be used as slot for value changed signal of the dynamically created
        alignment parameter widgets.

        @param str method: The alignment method name to create this method for.
        """

        def method_template(self, send_all=False):
            obj_name = self.sender().objectName() if not send_all else ''
            param_dict = dict()
            for param_name, widget in self.alignment_param_widgets[method].items():
                if obj_name == widget.objectName() or send_all:
                    if hasattr(widget, 'isChecked'):
                        param_dict[param_name] = widget.isChecked()
                    elif hasattr(widget, 'value'):
                        param_dict[param_name] = widget.value()
                    elif hasattr(widget, 'text'):
                        param_dict[param_name] = widget.text()
                    if not send_all:
                        break
            self.sigAlignmentParametersChanged.emit(method, param_dict)
            return param_dict

        return method_template
