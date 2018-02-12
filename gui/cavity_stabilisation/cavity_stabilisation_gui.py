# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module to operate a cavity length stabilisation.
It is based on analogue input that serves as feedback about the cavity
and analogue output that is used to change the length of the cavity.

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
from collections import OrderedDict
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic


class CavityStabilisationMainWindow(QtGui.QMainWindow):

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_cavity_stabilisation_gui.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class CavityStabilisationGui(GUIBase):
    """
    This is the GUI Class for software driven cavity length stabilisation, both in reflection and transmission.
    """
    _modclass = 'CavityStabilisationGui'
    _modtype = 'gui'

    # declare connectors
    cavity_stabilisation_logic = Connector(interface='CavityStabilisationLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    sigUpdateGotoPos = QtCore.Signal(float)

    def __init__(self, config, **kwargs):
        ## declare actions for state transitions
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key, config[key]))

    def on_deactivate(self):
        """ Reverse steps of activation

        @param e: error code

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def on_activate(self):
        """ Definition, configuration and initialisation of the cavity stabilisation GUI.

          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.

        """

        self._cavity_stabilisation_logic = self.get_connector('cavity_stabilisation_logic')

        # GUI element:
        self._mw = CavityStabilisationMainWindow()

        # set up dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)


        self.cavity_scan_image = pg.PlotDataItem(self._cavity_stabilisation_logic.scan_raw_data[0],
                                          self._cavity_stabilisation_logic.scan_raw_data[1],
                                          pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)


        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.cavity_scan_PlotWidget.addItem(self.cavity_scan_image)
        self._mw.cavity_scan_PlotWidget.setLabel(axis='left', text='Input Voltage', units='V')
        self._mw.cavity_scan_PlotWidget.setLabel(axis='bottom', text='Time', units='s')
        self._mw.cavity_scan_PlotWidget.showGrid(x=True, y=True, alpha=0.8)


        # setting default parameters
        self._mw.start_spinBox.setRange(self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0], self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[1])
        self._mw.start_spinBox.setValue(self._cavity_stabilisation_logic._start_voltage)
        self._mw.start_spinBox.editingFinished.connect(self.start_value_changed, QtCore.Qt.QueuedConnection)

        self._mw.stop_spinBox.setRange(self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0], self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[1])
        self._mw.stop_spinBox.setValue(self._cavity_stabilisation_logic._end_voltage)
        self._mw.stop_spinBox.editingFinished.connect(self.stop_value_changed, QtCore.Qt.QueuedConnection)

        self._mw.position_spinBox.setRange(self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0], self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[1])
        self._mw.position_spinBox.setValue(self._cavity_stabilisation_logic._start_voltage)
        self._mw.position_spinBox.editingFinished.connect(self.update_from_pos_spinBox, QtCore.Qt.QueuedConnection)

        self._mw.scan_frequency_spinBox.setValue(self._cavity_stabilisation_logic._scan_frequency)
        self._mw.scan_resolution_spinBox.setValue(self._cavity_stabilisation_logic._scan_resolution)

        # setting up the slider
        self.slider_res = 0.001

        # number of points needed for the slider
        num_of_points_slider = (self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[1] - self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0])/self.slider_res

        # setting range for the slider
        self._mw.position_slider.setRange(0, num_of_points_slider)
        self._mw.position_slider.setValue((self._cavity_stabilisation_logic._start_voltage-self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0])/self.slider_res)

        # handle slider movement
        self._mw.position_slider.sliderMoved.connect(self.update_from_pos_slider, QtCore.Qt.QueuedConnection)


        # connecting user interactions
        self._mw.action_start_scanning.triggered.connect(self.start_clicked)
        self._mw.action_stop_scanning.triggered.connect(self.stop_clicked)
        self._mw.action_Save.triggered.connect(self.save_clicked)


        self._mw.scan_frequency_spinBox.valueChanged.connect(self.scan_frequency_changed)
        self._mw.scan_resolution_spinBox.valueChanged.connect(self.scan_resolution_changed)


        self._cavity_stabilisation_logic.sigCavityScanPlotUpdated.connect(self.update_plot, QtCore.Qt.QueuedConnection)
        self.sigUpdateGotoPos.connect(self.update_goto_pos, QtCore.Qt.QueuedConnection)

        # Connect other signals from the logic with an update of the gui
        #self._cavity_stabilisation_logic.signal_start_scanning.connect(self.logic_started_scanning)

        #setting GUI elements enabled
        self._mw.start_spinBox.setEnabled(True)
        self._mw.stop_spinBox.setEnabled(True)
        self._mw.position_spinBox.setEnabled(True)
        self._mw.position_slider.setEnabled(True)
        self._mw.scan_frequency_spinBox.setEnabled(True)
        self._mw.scan_resolution_spinBox.setEnabled(True)

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        self.disable_scan_actions()
        self._cavity_stabilisation_logic._initialise_scanner()
        self._cavity_stabilisation_logic._do_next_line()

    def stop_clicked(self):
        """ Stop the scan if the state has switched to ready.
        """
        self._cavity_stabilisation_logic.stopRequested = True
        self.enable_scan_actions()
        self._mw.position_spinBox.setValue(self._cavity_stabilisation_logic.axis_class[
                                               self._cavity_stabilisation_logic.control_axis].output_voltage)
        self._mw.position_slider.setValue((self._cavity_stabilisation_logic.axis_class[
                                               self._cavity_stabilisation_logic.control_axis].output_voltage-self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0])/self.slider_res)

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._cavity_stabilisation_logic.save_data()


    def update_pos_slider(self, output_value):
        """ Update position_slider if other GUI elements are changed.
        """
        self._mw.position_slider.setValue((output_value-self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0])/self.slider_res)

    def update_from_pos_slider(self, slider_value):
        """  If position_slider is moved, adjust GUI elements.
        """
        output_value = self._cavity_stabilisation_logic.axis_class[self._cavity_stabilisation_logic.control_axis].output_voltage_range[0] + slider_value * self.slider_res
        self.update_pos_spinBox(output_value)
        self.sigUpdateGotoPos.emit(output_value)

    def update_pos_spinBox(self, output_value):
        """ Update position_spinBox if other GUI elements are changed.
        """
        self._mw.position_spinBox.setValue(output_value)

    def update_from_pos_spinBox(self, output_value=None):
        """  If position_spinBox is moved, adjust GUI elements.
        """
        if output_value is None:
            output_value = self._mw.position_spinBox.value()
        self.update_pos_slider(output_value)
        self.sigUpdateGotoPos.emit(output_value)

    def update_goto_pos(self, output_value):
        self._cavity_stabilisation_logic.change_analogue_output_voltage(output_value)

    def update_plot(self, cavity_scan_data_x, cavity_scan_data_y):
        """ Refresh the plot widget with new data. """
        # Update mean signal plot
        self.cavity_scan_image.setData(cavity_scan_data_x, cavity_scan_data_y)


    def scan_frequency_changed(self):
        frequency = self._mw.scan_frequency_spinBox.value()
        self._cavity_stabilisation_logic._scan_frequency = frequency

    def scan_resolution_changed(self):
        resolution = self._mw.scan_resolution_spinBox.value()
        self._cavity_stabilisation_logic._scan_resolution = resolution

    def start_value_changed(self):
        start = self._mw.start_spinBox.value()
        self._cavity_stabilisation_logic._start_voltage = start

    def stop_value_changed(self):
        stop = self._mw.stop_spinBox.value()
        self._cavity_stabilisation_logic._end_voltage = stop


    def disable_scan_actions(self):
        """ Disables the button for scanning.
        """
        # Enable the stop scanning button
        self._mw.action_stop_scanning.setEnabled(True)

        # Disable the start scan button
        self._mw.action_start_scanning.setEnabled(False)

        self._mw.start_spinBox.setEnabled(False)
        self._mw.stop_spinBox.setEnabled(False)
        self._mw.position_spinBox.setEnabled(False)
        self._mw.position_slider.setEnabled(False)
        self._mw.scan_frequency_spinBox.setEnabled(False)
        self._mw.scan_resolution_spinBox.setEnabled(False)

    def enable_scan_actions(self):
        """ Enables the button for scanning.
        """
        # Ensable the start scanning button
        self._mw.action_start_scanning.setEnabled(True)

        # Disable the stop scan button
        self._mw.action_stop_scanning.setEnabled(False)

        self._mw.start_spinBox.setEnabled(True)
        self._mw.stop_spinBox.setEnabled(True)
        self._mw.position_spinBox.setEnabled(True)
        self._mw.position_slider.setEnabled(True)
        self._mw.scan_frequency_spinBox.setEnabled(True)
        self._mw.scan_resolution_spinBox.setEnabled(True)

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.cavity_DockWidget.show()
        self._mw.scan_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.cavity_DockWidget.setFloating(False)
        self._mw.scan_parameters_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.cavity_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.scan_parameters_DockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.scan_control_ToolBar)