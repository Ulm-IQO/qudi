# -*- coding: utf-8 -*-

"""
This file contains a gui for the laser controller logic.

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
import time
import pyqtgraph as pg
from PySide2 import QtCore, QtWidgets

from qudi.core import qudi_slot
from qudi.core.connector import Connector
from qudi.core.gui.colordefs import QudiPalettePale as palette
from qudi.core.module import GuiBase
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.gui.qtwidgets.slider import DoubleSlider
from qudi.core.gui.qtwidgets.advanced_dockwidget import AdvancedDockWidget
from qudi.interface.simple_laser_interface import ControlMode, ShutterState, LaserState


class TimeAxisItem(pg.AxisItem):
    """ pyqtgraph AxisItem that shows a HH:MM:SS timestamp on ticks.
        X-Axis must be formatted as (floating point) Unix time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """ Hours:Minutes:Seconds string from float unix timestamp. """
        return [time.strftime("%H:%M:%S", time.localtime(value)) for value in values]


class LaserControlDockWidget(AdvancedDockWidget):
    """
    """
    sigControlModeChanged = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # generate main widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout()
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # generate child widgets
        self.laser_button = QtWidgets.QPushButton('Laser')
        self.laser_button.setCheckable(True)
        main_layout.addWidget(self.laser_button, 0, 0)
        self.shutter_button = QtWidgets.QPushButton('Shutter')
        self.shutter_button.setCheckable(True)
        main_layout.addWidget(self.shutter_button, 0, 1)

        group_box = QtWidgets.QGroupBox('Control Mode')
        layout = QtWidgets.QHBoxLayout()
        group_box.setLayout(layout)
        button_group = QtWidgets.QButtonGroup(self)
        self.control_power_radio_button = QtWidgets.QRadioButton('Power')
        self.control_current_radio_button = QtWidgets.QRadioButton('Current')
        button_group.addButton(self.control_power_radio_button)
        button_group.addButton(self.control_current_radio_button)
        layout.addWidget(self.control_power_radio_button)
        layout.addWidget(self.control_current_radio_button)
        self.control_power_radio_button.clicked.connect(
            lambda: self.sigControlModeChanged.emit(ControlMode.POWER)
        )
        self.control_current_radio_button.clicked.connect(
            lambda: self.sigControlModeChanged.emit(ControlMode.CURRENT)
        )
        main_layout.addWidget(group_box, 1, 0, 1, 2)

        group_box = QtWidgets.QGroupBox('Power')
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        group_box.setLayout(layout)
        self.power_spinbox = ScienDSpinBox()
        self.power_spinbox.setDecimals(2)
        self.power_spinbox.setMinimum(0)
        self.power_spinbox.setSuffix('W')
        self.power_spinbox.setMinimumWidth(75)
        self.power_spinbox.setReadOnly(True)
        self.power_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.power_spinbox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.power_spinbox.setMouseTracking(False)
        self.power_spinbox.setKeyboardTracking(False)
        layout.addWidget(self.power_spinbox)
        self.power_setpoint_spinbox = ScienDSpinBox()
        self.power_setpoint_spinbox.setDecimals(2)
        self.power_setpoint_spinbox.setMinimum(0)
        self.power_setpoint_spinbox.setSuffix('W')
        self.power_setpoint_spinbox.setMinimumWidth(75)
        layout.addWidget(self.power_setpoint_spinbox)
        self.power_slider = DoubleSlider(QtCore.Qt.Vertical)
        self.power_slider.set_granularity(10000)  # 0.01% precision
        self.power_slider.setMinimumHeight(200)
        self.power_slider.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                        QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.power_slider)
        main_layout.addWidget(group_box, 2, 0)

        group_box = QtWidgets.QGroupBox('Current')
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        group_box.setLayout(layout)
        self.current_spinbox = ScienDSpinBox()
        self.current_spinbox.setDecimals(2)
        self.current_spinbox.setMinimum(0)
        self.current_spinbox.setMinimumWidth(75)
        self.current_spinbox.setReadOnly(True)
        self.current_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.current_spinbox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.current_spinbox.setMouseTracking(False)
        self.current_spinbox.setKeyboardTracking(False)
        layout.addWidget(self.current_spinbox)
        self.current_setpoint_spinbox = ScienDSpinBox()
        self.current_setpoint_spinbox.setDecimals(2)
        self.current_setpoint_spinbox.setMinimum(0)
        self.current_setpoint_spinbox.setMinimumWidth(75)
        layout.addWidget(self.current_setpoint_spinbox)
        self.current_slider = DoubleSlider(QtCore.Qt.Vertical)
        self.current_slider.set_granularity(10000)  # 0.01% precision
        self.current_slider.setRange(0, 100)
        self.current_slider.setMinimumHeight(200)
        self.current_slider.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.current_slider)
        main_layout.addWidget(group_box, 2, 1)
        main_widget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        # main_layout.setSizeConstraint(main_layout.SetFixedSize)


class LaserOutputDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot_widget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot_widget.setLabel('bottom', 'Time', units=None)
        self.plot_widget.setLabel('left', 'Power', units='W', color=palette.c1.name())
        self.plot_widget.setLabel('right', 'Current', color=palette.c3.name())
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMouseTracking(False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()
        self.plot_widget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.plot_widget.setMinimumSize(200, 200)
        # Create second ViewBox to plot with two independent y-axes
        self.view_box2 = pg.ViewBox()
        self.plot_widget.scene().addItem(self.view_box2)
        self.plot_widget.getAxis('right').linkToView(self.view_box2)
        self.view_box2.setXLink(self.plot_widget)
        self.view_box2.setMouseEnabled(x=False, y=False)
        self.view_box2.setMenuEnabled(False)
        # Sync resize events
        self.plot_widget.plotItem.vb.sigResized.connect(self.__update_viewbox_sync)
        # Create plot data items
        self.power_data_item = pg.PlotCurveItem(pen=pg.mkPen(palette.c1, cosmetic=True),
                                                antialias=True)
        self.current_data_item = pg.PlotCurveItem(pen=pg.mkPen(palette.c3, cosmetic=True),
                                                  antialias=True)

        self.setWidget(self.plot_widget)

    @QtCore.Slot()
    def __update_viewbox_sync(self):
        """ Helper method to sync plots for both y-axes.
        """
        self.view_box2.setGeometry(self.plot_widget.plotItem.vb.sceneBoundingRect())
        self.view_box2.linkedViewChanged(self.plot_widget.plotItem.vb, self.view_box2.XAxis)


class LaserTemperatureDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, curve_names, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot_widget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot_widget.setLabel('bottom', 'Time', units=None)
        self.plot_widget.setLabel('left', 'Temperature', units='°C', color=palette.c1.name())
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMouseTracking(False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()
        self.plot_widget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.plot_widget.setMinimumSize(200, 200)
        self.temperature_data_items = dict()
        for name in curve_names:
            self.temperature_data_items[name] = pg.PlotCurveItem(
                pen=pg.mkPen(palette.c1, cosmetic=True),
                antialias=True
            )
            self.plot_widget.addItem(self.temperature_data_items[name])
        self.setWidget(self.plot_widget)


class LaserMainWindow(QtWidgets.QMainWindow):
    """ The main window for the LaserGui """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # create menu bar and actions
        menu_bar = QtWidgets.QMenuBar(self)
        self.setMenuBar(menu_bar)

        menu = menu_bar.addMenu('File')
        self.action_close = QtWidgets.QAction('Close')
        self.action_close.triggered.connect(self.close)
        menu.addAction(self.action_close)

        menu = menu_bar.addMenu('View')
        self.action_view_controls = QtWidgets.QAction('Show Controls')
        self.action_view_controls.setCheckable(True)
        self.action_view_controls.setChecked(True)
        menu.addAction(self.action_view_controls)
        self.action_view_output_graph = QtWidgets.QAction('Show Output Graph')
        self.action_view_output_graph.setCheckable(True)
        self.action_view_output_graph.setChecked(True)
        menu.addAction(self.action_view_output_graph)
        self.action_view_temperature_graph = QtWidgets.QAction('Show Temperature Graph')
        self.action_view_temperature_graph.setCheckable(True)
        self.action_view_temperature_graph.setChecked(True)
        menu.addAction(self.action_view_temperature_graph)
        menu.addSeparator()
        self.action_view_default = QtWidgets.QAction('Restore Default')
        menu.addAction(self.action_view_default)

        # Create status bar
        status_bar = QtWidgets.QStatusBar(self)
        status_bar.setStyleSheet('QStatusBar::item { border: 0px}')
        self.setStatusBar(status_bar)
        self.status_label = QtWidgets.QLabel('<laser status>')
        status_bar.addPermanentWidget(self.status_label, 1)


class LaserGui(GuiBase):
    """ FIXME: Please document
    """

    # declare connectors
    _laser_logic = Connector(name='laser_logic', interface='LaserLogic')

    sigLaserToggled = QtCore.Signal(bool)
    sigShutterToggled = QtCore.Signal(bool)
    sigControlModeChanged = QtCore.Signal(object)
    sigPowerChanged = QtCore.Signal(float, object)
    sigCurrentChanged = QtCore.Signal(float, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mw = None
        self.control_dock_widget = None
        self.output_graph_dock_widget = None
        self.temperature_graph_dock_widget = None

    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        logic = self._laser_logic()

        #####################
        # create main window
        self._mw = LaserMainWindow()
        self._mw.setDockNestingEnabled(True)
        # set up dock widgets
        self.control_dock_widget = LaserControlDockWidget()
        self.control_dock_widget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetClosable | QtWidgets.QDockWidget.DockWidgetMovable
        )
        self.control_dock_widget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self._mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.control_dock_widget)
        self.control_dock_widget.visibilityChanged.connect(self._mw.action_view_controls.setChecked)
        self._mw.action_view_controls.triggered[bool].connect(self.control_dock_widget.setVisible)
        self.control_dock_widget.power_slider.setRange(*logic.power_range)
        self.control_dock_widget.power_setpoint_spinbox.setRange(*logic.power_range)
        self.control_dock_widget.current_slider.setRange(*logic.current_range)
        self.control_dock_widget.current_setpoint_spinbox.setRange(*logic.current_range)
        self.control_dock_widget.current_setpoint_spinbox.setSuffix(logic.current_unit)
        self.control_dock_widget.current_spinbox.setSuffix(logic.current_unit)

        self.output_graph_dock_widget = LaserOutputDockWidget()
        self.output_graph_dock_widget.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        self.output_graph_dock_widget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.output_graph_dock_widget)
        self.output_graph_dock_widget.visibilityChanged.connect(
            self._mw.action_view_output_graph.setChecked
        )
        self._mw.action_view_output_graph.triggered[bool].connect(
            self.output_graph_dock_widget.setVisible
        )
        self.output_graph_dock_widget.plot_widget.setLabel('right',
                                                           'Current',
                                                           units=logic.current_unit,
                                                           color=palette.c3.name())

        self.temperature_graph_dock_widget = LaserTemperatureDockWidget(
            curve_names=tuple(logic.temperatures)
        )
        self.temperature_graph_dock_widget.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        self.temperature_graph_dock_widget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.temperature_graph_dock_widget)
        self.temperature_graph_dock_widget.visibilityChanged.connect(
            self._mw.action_view_temperature_graph.setChecked
        )
        self._mw.action_view_temperature_graph.triggered[bool].connect(
            self.temperature_graph_dock_widget.setVisible
        )

        self.restore_default_view()

        # Initialize data from logic
        self._mw.status_label.setText(logic.extra_info)
        self._shutter_state_updated(logic.shutter_state)
        self._laser_state_updated(logic.laser_state)
        self._control_mode_updated(logic.control_mode)
        self._current_setpoint_updated(logic.current_setpoint, None)
        self._power_setpoint_updated(logic.power_setpoint, None)
        self._data_updated(logic.data)

        # connect control dockwidget signals
        self.control_dock_widget.laser_button.clicked[bool].connect(self._laser_clicked)
        self.control_dock_widget.shutter_button.clicked[bool].connect(self._shutter_clicked)
        self.control_dock_widget.sigControlModeChanged.connect(self._control_mode_clicked)
        self.control_dock_widget.power_slider.doubleSliderMoved.connect(self._power_slider_moving)
        self.control_dock_widget.power_slider.sliderReleased.connect(self._power_slider_moved)
        self.control_dock_widget.current_slider.doubleSliderMoved.connect(
            self._current_slider_moving
        )
        self.control_dock_widget.current_slider.sliderReleased.connect(self._current_slider_moved)
        self.control_dock_widget.power_setpoint_spinbox.editingFinished.connect(
            self._power_setpoint_edited
        )
        self.control_dock_widget.current_setpoint_spinbox.editingFinished.connect(
            self._current_setpoint_edited
        )

        # connect remaining main window actions
        self._mw.action_view_default.triggered.connect(self.restore_default_view)

        # connect external signals to logic
        self.sigLaserToggled.connect(logic.set_laser_state)
        self.sigShutterToggled.connect(logic.set_shutter_state)
        self.sigCurrentChanged.connect(logic.set_current)
        self.sigPowerChanged.connect(logic.set_power)
        self.sigControlModeChanged.connect(logic.set_control_mode)

        # connect update signals from logic
        logic.sigPowerSetpointChanged.connect(
            self._power_setpoint_updated, QtCore.Qt.QueuedConnection
        )
        logic.sigCurrentSetpointChanged.connect(
            self._current_setpoint_updated, QtCore.Qt.QueuedConnection
        )
        logic.sigControlModeChanged.connect(self._control_mode_updated, QtCore.Qt.QueuedConnection)
        logic.sigLaserStateChanged.connect(self._laser_state_updated, QtCore.Qt.QueuedConnection)
        logic.sigShutterStateChanged.connect(
            self._shutter_state_updated, QtCore.Qt.QueuedConnection
        )
        logic.sigDataChanged.connect(self._data_updated, QtCore.Qt.QueuedConnection)

        self.show()

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.close()
        # disconnect all signals
        logic = self._laser_logic()
        logic.sigPowerSetpointChanged.disconnect(self._power_setpoint_updated)
        logic.sigCurrentSetpointChanged.disconnect(self._current_setpoint_updated)
        logic.sigControlModeChanged.disconnect(self._control_mode_updated)
        logic.sigLaserStateChanged.disconnect(self._laser_state_updated)
        logic.sigShutterStateChanged.disconnect(self._shutter_state_updated)
        logic.sigDataChanged.disconnect(self._data_updated)
        self.control_dock_widget.laser_button.clicked[bool].disconnect()
        self.control_dock_widget.shutter_button.clicked[bool].disconnect()
        self.control_dock_widget.sigControlModeChanged.disconnect()
        self.control_dock_widget.power_slider.doubleSliderMoved.disconnect()
        self.control_dock_widget.power_slider.sliderReleased.disconnect()
        self.control_dock_widget.current_slider.doubleSliderMoved.disconnect()
        self.control_dock_widget.current_slider.sliderReleased.disconnect()
        self.control_dock_widget.power_setpoint_spinbox.editingFinished.disconnect()
        self.control_dock_widget.current_setpoint_spinbox.editingFinished.disconnect()
        self._mw.action_view_default.triggered.disconnect()
        self.sigLaserToggled.disconnect()
        self.sigShutterToggled.disconnect()
        self.sigCurrentChanged.disconnect()
        self.sigPowerChanged.disconnect()
        self.sigControlModeChanged.disconnect()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        self._mw.show()
        self._mw.raise_()
        self._mw.activateWindow()

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self.control_dock_widget.show()
        self.output_graph_dock_widget.show()
        self.temperature_graph_dock_widget.show()

        # re-dock any floating dock widgets
        self.output_graph_dock_widget.setFloating(False)
        self.temperature_graph_dock_widget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.control_dock_widget)
        self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.output_graph_dock_widget)
        self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.temperature_graph_dock_widget)

    @qudi_slot(bool)
    def _laser_clicked(self, checked):
        """ Laser button callback. Disables button and sends a signal to the logic. Logic
        response will enable the button again.

        @param bool checked: Button check state after click
        """
        self.control_dock_widget.laser_button.setEnabled(False)
        self.sigLaserToggled.emit(checked)

    @qudi_slot(bool)
    def _shutter_clicked(self, checked):
        """ Shutter button callback. Disables button and sends a signal to the logic. Logic
        response will enable the button again.

        @param bool checked: Button check state after click
        """
        self.control_dock_widget.shutter_button.setEnabled(False)
        self.sigShutterToggled.emit(checked)

    @qudi_slot(object)
    def _control_mode_clicked(self, mode):
        """ Control mode button group callback. Disables control elements and sends a signal to the
        logic. Logic response will enable the control elements again.

        @param ControlMode mode: Selected ControlMode enum
        """
        self.control_dock_widget.control_current_radio_button.setEnabled(False)
        self.control_dock_widget.current_setpoint_spinbox.setEnabled(False)
        self.control_dock_widget.current_slider.setEnabled(False)
        self.control_dock_widget.control_power_radio_button.setEnabled(False)
        self.control_dock_widget.power_setpoint_spinbox.setEnabled(False)
        self.control_dock_widget.power_slider.setEnabled(False)
        self.sigControlModeChanged.emit(mode)

    @qudi_slot(float)
    def _power_slider_moving(self, value):
        """ ToDo: Document
        """
        self.control_dock_widget.power_setpoint_spinbox.setValue(value)

    @qudi_slot(float)
    def _current_slider_moving(self, value):
        """ ToDo: Document
        """
        self.control_dock_widget.current_setpoint_spinbox.setValue(value)

    @qudi_slot()
    def _power_slider_moved(self):
        """ ToDo: Document
        """
        value = self.control_dock_widget.power_slider.value()
        self.control_dock_widget.power_setpoint_spinbox.setValue(value)
        self.sigPowerChanged.emit(value, self.module_state.uuid)

    @qudi_slot()
    def _current_slider_moved(self):
        """ ToDo: Document
        """
        value = self.control_dock_widget.current_slider.value()
        self.control_dock_widget.current_setpoint_spinbox.setValue(value)
        self.sigCurrentChanged.emit(value, self.module_state.uuid)

    @qudi_slot()
    def _power_setpoint_edited(self):
        """ ToDo: Document
        """
        value = self.control_dock_widget.power_setpoint_spinbox.value()
        self.control_dock_widget.power_slider.setValue(value)
        self.sigPowerChanged.emit(value, self.module_state.uuid)

    @qudi_slot()
    def _current_setpoint_edited(self):
        """ ToDo: Document
        """
        value = self.control_dock_widget.current_setpoint_spinbox.value()
        self.control_dock_widget.current_slider.setValue(value)
        self.sigCurrentChanged.emit(value, self.module_state.uuid)

    @qudi_slot(float, object)
    def _power_setpoint_updated(self, value, caller_id):
        if caller_id != self.module_state.uuid:
            self.control_dock_widget.power_setpoint_spinbox.setValue(value)
            self.control_dock_widget.power_slider.setValue(value)

    @qudi_slot(float, object)
    def _current_setpoint_updated(self, value, caller_id):
        if caller_id != self.module_state.uuid:
            self.control_dock_widget.current_setpoint_spinbox.setValue(value)
            self.control_dock_widget.current_slider.setValue(value)

    @qudi_slot(object)
    def _control_mode_updated(self, mode):
        self.control_dock_widget.control_power_radio_button.setEnabled(True)
        self.control_dock_widget.control_current_radio_button.setEnabled(True)
        if mode == ControlMode.POWER:
            self.control_dock_widget.current_slider.setEnabled(False)
            self.control_dock_widget.current_setpoint_spinbox.setEnabled(False)
            self.control_dock_widget.power_slider.setEnabled(True)
            self.control_dock_widget.power_setpoint_spinbox.setEnabled(True)
            self.control_dock_widget.control_power_radio_button.setChecked(True)
        elif mode == ControlMode.CURRENT:
            self.control_dock_widget.power_slider.setEnabled(False)
            self.control_dock_widget.power_setpoint_spinbox.setEnabled(False)
            self.control_dock_widget.current_slider.setEnabled(True)
            self.control_dock_widget.current_setpoint_spinbox.setEnabled(True)
            self.control_dock_widget.control_current_radio_button.setChecked(True)
        else:
            self.control_dock_widget.current_slider.setEnabled(False)
            self.control_dock_widget.current_setpoint_spinbox.setEnabled(False)
            self.control_dock_widget.power_slider.setEnabled(False)
            self.control_dock_widget.power_setpoint_spinbox.setEnabled(False)

    @qudi_slot(object)
    def _laser_state_updated(self, state):
        if state == LaserState.ON:
            # self.control_dock_widget.laser_button.setText('Laser: ON')
            self.control_dock_widget.laser_button.setChecked(True)
            self.control_dock_widget.laser_button.setEnabled(True)
            if not self.control_dock_widget.laser_button.isVisible():
                self.control_dock_widget.laser_button.setVisible(True)
        elif state == LaserState.OFF:
            # self.control_dock_widget.laser_button.setText('Laser: OFF')
            self.control_dock_widget.laser_button.setChecked(False)
            self.control_dock_widget.laser_button.setEnabled(True)
            if not self.control_dock_widget.laser_button.isVisible():
                self.control_dock_widget.laser_button.setVisible(True)
        elif state == LaserState.LOCKED:
            # self.control_dock_widget.laser_button.setText('INTERLOCK')
            self.control_dock_widget.laser_button.setEnabled(False)
            self.control_dock_widget.laser_button.setChecked(False)
            if self.control_dock_widget.laser_button.isVisible():
                self.control_dock_widget.laser_button.setVisible(False)
        else:
            # self.control_dock_widget.laser_button.setText('Laser: ?')
            self.control_dock_widget.laser_button.setEnabled(False)
            if self.control_dock_widget.laser_button.isVisible():
                self.control_dock_widget.laser_button.setVisible(False)

    @qudi_slot(object)
    def _shutter_state_updated(self, state):
        if state == ShutterState.OPEN:
            # self.control_dock_widget.shutter_button.setText('Shutter: OPEN')
            self.control_dock_widget.shutter_button.setChecked(True)
            self.control_dock_widget.shutter_button.setEnabled(True)
            if not self.control_dock_widget.shutter_button.isVisible():
                self.control_dock_widget.shutter_button.setVisible(True)
        elif state == ShutterState.CLOSED:
            # self.control_dock_widget.shutter_button.setText('Shutter: CLOSED')
            self.control_dock_widget.shutter_button.setChecked(False)
            self.control_dock_widget.shutter_button.setEnabled(True)
            if not self.control_dock_widget.shutter_button.isVisible():
                self.control_dock_widget.shutter_button.setVisible(True)
        elif state == ShutterState.NO_SHUTTER:
            # self.control_dock_widget.shutter_button.setText('NO SHUTTER')
            self.control_dock_widget.shutter_button.setEnabled(False)
            self.control_dock_widget.shutter_button.setChecked(False)
            if self.control_dock_widget.shutter_button.isVisible():
                self.control_dock_widget.shutter_button.setVisible(False)
        else:
            # self.control_dock_widget.shutter_button.setText('Shutter: ?')
            self.control_dock_widget.shutter_button.setEnabled(False)
            if self.control_dock_widget.shutter_button.isVisible():
                self.control_dock_widget.shutter_button.setVisible(False)

    @qudi_slot(dict)
    def _data_updated(self, data):
        try:
            x = data.pop('time')
        except KeyError:
            self.log.error('No time information given in data dict.')
            return
        for name, y in data.items():
            if name == 'power':
                item = self.output_graph_dock_widget.power_data_item
                if y is None:
                    if item in self.output_graph_dock_widget.plot_widget.items():
                        self.output_graph_dock_widget.plot_widget.removeItem(item)
                else:
                    self.control_dock_widget.power_spinbox.setValue(y[-1])
                    item.setData(y=y, x=x)
                    if item not in self.output_graph_dock_widget.plot_widget.items():
                        self.output_graph_dock_widget.plot_widget.addItem(item)
            elif name == 'current':
                item = self.output_graph_dock_widget.current_data_item
                if y is None:
                    if item in self.output_graph_dock_widget.view_box2.addedItems:
                        self.output_graph_dock_widget.view_box2.removeItem(item)
                else:
                    self.control_dock_widget.current_spinbox.setValue(y[-1])
                    item.setData(y=y, x=x)
                    if item not in self.output_graph_dock_widget.view_box2.addedItems:
                        self.output_graph_dock_widget.view_box2.addItem(item)
            else:
                item = self.temperature_graph_dock_widget.temperature_data_items[name]
                item.setData(y=y, x=x)

    @qudi_slot()
    def updateButtonsEnabled(self):
        """ Logic told us to update our button states, so set the buttons accordingly. """
        logic = self._laser_logic()
        self._mw.laserButton.setEnabled(logic.laser_can_turn_on)
        if logic.laser_state == LaserState.ON:
            self._mw.laserButton.setText('Laser: ON')
            self._mw.laserButton.setChecked(True)
            self._mw.laserButton.setStyleSheet('')
        elif logic.laser_state == LaserState.OFF:
            self._mw.laserButton.setText('Laser: OFF')
            self._mw.laserButton.setChecked(False)
        elif logic.laser_state == LaserState.LOCKED:
            self._mw.laserButton.setText('INTERLOCK')
        else:
            self._mw.laserButton.setText('Laser: ?')

        self._mw.shutterButton.setEnabled(logic.has_shutter)
        if logic.laser_shutter == ShutterState.OPEN:
            self._mw.shutterButton.setText('Shutter: OPEN')
        elif logic.laser_shutter == ShutterState.CLOSED:
            self._mw.shutterButton.setText('Shutter: CLOSED')
        elif logic.laser_shutter == ShutterState.NOSHUTTER:
            self._mw.shutterButton.setText('No shutter.')
        else:
            self._mw.shutterButton.setText('Shutter: ?')

        self._mw.currentRadioButton.setEnabled(logic.laser_can_current)
        self._mw.powerRadioButton.setEnabled(logic.laser_can_power)

    @qudi_slot()
    def updateGui(self):
        """ Update labels, the plot and button states with new data. """
        logic = self._laser_logic()
        self._mw.currentLabel.setText(
            '{0:6.3f} {1}'.format(
                logic.laser_current,
                logic.laser_current_unit))
        self._mw.powerLabel.setText('{0:6.3f} W'.format(logic.laser_power))
        self._mw.extraLabel.setText(logic.laser_extra)
        self.updateButtonsEnabled()
        for name, curve in self.curves.items():
            curve.setData(x=logic.data['time'], y=logic.data[name])
