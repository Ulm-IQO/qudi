# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module to operate a EOM regulation.
The aim of the program is to use the data of the pure laser signal from
the pulsed measurement to readjust the EOM via an analog output voltage
(compensation of the DC drift). To do this, the voltage at which
the entire laser signal (of the slow counter) is blocked must first
be found. Then the voltage is adjusted during the running pulse
sequence by the data of the pulsed measurement.


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

from core.configoption import ConfigOption
from core.connector import Connector
from core.statusvariable import StatusVar
from collections import OrderedDict
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic


class EOMRegulationMainWindow(QtGui.QMainWindow):

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eom_regulation_gui.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class EOMRegulationGui(GUIBase):
    """
    This is the GUI Class for software driven EOM regulation.
    """
    _modclass = 'EOMRegulationGui'
    _modtype = 'gui'

    # declare connectors
    eom_regulation_logic = Connector(interface='EOMRegulationLogic')

    sigGotoPos = QtCore.Signal(float)

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
        """ Definition, configuration and initialisation of the EOM regulation GUI.

          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.

        """
        self._eom_regulation_logic = self.eom_regulation_logic()

        # GUI element:
        self._mw = EOMRegulationMainWindow()

        # Add the display item ViewWidget, which was defined in the UI file.
        self._mw.laser_signal_plotWidget.setLabel(axis='left', text='counts', units='cs')
        self._mw.laser_signal_plotWidget.setLabel(axis='bottom', text='Time', units='s')
        self._mw.laser_signal_plotWidget.showGrid(x=True, y=True, alpha=0.4)

        self.laser_signal_image = pg.PlotDataItem(
            pen=pg.mkPen(palette.c1, style=QtCore.Qt.SolidLine, width=1),
            symbol='o',
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=1)

        self._mw.laser_signal_plotWidget.addItem(self.laser_signal_image)

        # Actual voltage:
        self._mw.actual_voltage_doubleSpinBox.setValue(self._eom_regulation_logic._actual_voltage)

        # connecting signals
        self._eom_regulation_logic.sigVoltageUpdate.connect(self.update_actual_voltage, QtCore.Qt.QueuedConnection)
        self._eom_regulation_logic.sigRegulationPlotUpdated.connect(self.update_plot, QtCore.Qt.QueuedConnection)
        self._eom_regulation_logic.sigChangeButton.connect(self.change_button, QtCore.Qt.QueuedConnection)
        self.sigGotoPos.connect(self.update_goto_pos, QtCore.Qt.QueuedConnection)
        self._eom_regulation_logic.sigsuppressionUpdate.connect(self.update_suppression, QtCore.Qt.QueuedConnection)

        ###############################################################################################################
        #                                                General Parameters                                           #
        ###############################################################################################################
        self._mw.voltage_doubleSpinBox.setValue(self._eom_regulation_logic._actual_voltage)
        self._mw.voltage_doubleSpinBox.setRange(self._eom_regulation_logic._voltage_min, self._eom_regulation_logic._voltage_max)
        self._mw.voltage_doubleSpinBox.editingFinished.connect(self.update_from_voltage_doubleSpinBox, QtCore.Qt.QueuedConnection)

        # setting up the slider
        self.slider_res = 0.001

        # number of points needed for the slider
        num_of_points_slider = (self._eom_regulation_logic._voltage_max-self._eom_regulation_logic._voltage_min) / self.slider_res

        # setting range for the slider
        self._mw.voltage_horizontalSlider.setRange(0, num_of_points_slider)
        self._mw.voltage_horizontalSlider.setValue(self._eom_regulation_logic._actual_voltage)

        # handle slider movement
        self._mw.voltage_horizontalSlider.sliderMoved.connect(self.update_from_voltage_horizontalSlider, QtCore.Qt.QueuedConnection)

        self._mw.start_voltage_doubleSpinBox.setValue(self._eom_regulation_logic._start_voltage)
        self._mw.start_voltage_doubleSpinBox.editingFinished.connect(self.start_voltage_changed)

        self._mw.rough_voltage_step_doubleSpinBox.setValue(self._eom_regulation_logic._rough_voltage_step)
        self._mw.rough_voltage_step_doubleSpinBox.editingFinished.connect(self.rough_voltage_step_changed)

        self._mw.fine_voltage_step_doubleSpinBox.setValue(self._eom_regulation_logic._fine_voltage_step)
        self._mw.fine_voltage_step_doubleSpinBox.editingFinished.connect(self.fine_voltage_step_changed)

        self._mw.fine_step_counts_spinBox.setValue(self._eom_regulation_logic._fine_step_counts)
        self._mw.fine_step_counts_spinBox.editingFinished.connect(self.fine_step_counts_changed)

        self._mw.voltage_step_doubleSpinBox.setValue(self._eom_regulation_logic._regulation_voltage_step)
        self._mw.voltage_step_doubleSpinBox.editingFinished.connect(self.voltage_step_changed)

        self._mw.regulation_interval_doubleSpinBox.setValue(self._eom_regulation_logic._regulation_interval)
        self._mw.regulation_interval_doubleSpinBox.editingFinished.connect(self.regulation_interval_changed)

        self._mw.record_length_DSpinBox.setValue(self._eom_regulation_logic._record_length)
        self._mw.record_length_DSpinBox.editingFinished.connect(self.record_length_changed)

        self._mw.neglect_0_checkBox.setChecked(self._eom_regulation_logic._neglect_0)
        self._mw.neglect_0_checkBox.toggled.connect(self.neglect_0_changed)


        # connecting user interactions
        self._mw.action_start_find_minimum.triggered.connect(self.start_clicked_minimum)
        self._mw.action_stop_find_minimum.triggered.connect(self.stop_clicked_minimum)
        self._mw.action_save.triggered.connect(self.save_clicked)

        self._mw.action_start_regulation.triggered.connect(self.start_regulation_clicked)
        self._mw.action_stop_regulation.triggered.connect(self.stop_regulation_clicked)

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def start_clicked_minimum(self):
        self._eom_regulation_logic.initialise_find_minimum()

    def stop_clicked_minimum(self):
        self._eom_regulation_logic.stopRequested_minimum = True
        self.enable_find_minimum_actions()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
                """
        self._eom_regulation_logic.save_data()

    def start_regulation_clicked(self):
        self._eom_regulation_logic.initialise_regulation()

    def stop_regulation_clicked(self):
        self._eom_regulation_logic.stopRequested_regulation = True
        self.enable_regulation_actions()

    def change_button(self, option):
        """ Enables (e) and disables (d) buttons for regulation (r) and find minimum (m), option = "me","md","re","rd"
                        """
        if option == "md": self.disable_find_minimum_actions()
        if option == "me": self.enable_find_minimum_actions()
        if option == "re": self.enable_regulation_actions()
        if option == "rd": self.disable_regulation_actions()

    def disable_find_minimum_actions(self):
        """ Disables the button for find minimum.
        """
        # Enable the stop find minimum button
        self._mw.action_stop_find_minimum.setEnabled(True)

        # Disable other buttons
        self._mw.action_start_regulation.setEnabled(False)
        self._mw.action_start_find_minimum.setEnabled(False)

        # Disable parameter inputs
        self._mw.voltage_doubleSpinBox.setEnabled(False)
        self._mw.voltage_horizontalSlider.setEnabled(False)
        self._mw.start_voltage_doubleSpinBox.setEnabled(False)
        self._mw.rough_voltage_step_doubleSpinBox.setEnabled(False)
        self._mw.fine_voltage_step_doubleSpinBox.setEnabled(False)
        self._mw.fine_step_counts_spinBox.setEnabled(False)


    def enable_find_minimum_actions(self):
        """ Enables the button for find minimum.
        """
        # Disable the stop find minimum button
        self._mw.action_stop_find_minimum.setEnabled(False)

        # Enable other button
        self._mw.action_start_regulation.setEnabled(True)
        self._mw.action_start_find_minimum.setEnabled(True)

        # Enable parameter inputs
        self._mw.voltage_doubleSpinBox.setEnabled(True)
        self._mw.voltage_horizontalSlider.setEnabled(True)
        self._mw.start_voltage_doubleSpinBox.setEnabled(True)
        self._mw.rough_voltage_step_doubleSpinBox.setEnabled(True)
        self._mw.fine_voltage_step_doubleSpinBox.setEnabled(True)
        self._mw.fine_step_counts_spinBox.setEnabled(True)

    def disable_regulation_actions(self):
        """ Disables the button for regulation.
        """
        # Enable the stop regulation button
        self._mw.action_stop_regulation.setEnabled(True)

        # Disable other buttons
        self._mw.action_start_regulation.setEnabled(False)
        self._mw.action_start_find_minimum.setEnabled(False)

        # Disable parameter inputs
        self._mw.voltage_doubleSpinBox.setEnabled(False)
        self._mw.voltage_horizontalSlider.setEnabled(False)
        self._mw.voltage_step_doubleSpinBox.setEnabled(False)
        self._mw.regulation_interval_doubleSpinBox.setEnabled(False)
        self._mw.record_length_DSpinBox.setEnabled(False)
        self._mw.neglect_0_checkBox.setEnabled(False)

    def enable_regulation_actions(self):
        """ Enables the button for regulation.
        """
        # Disable the stop regulation button
        self._mw.action_stop_regulation.setEnabled(False)

        # Enable other buttons
        self._mw.action_start_regulation.setEnabled(True)
        self._mw.action_start_find_minimum.setEnabled(True)

        # Enable parameter inputs
        self._mw.voltage_doubleSpinBox.setEnabled(True)
        self._mw.voltage_horizontalSlider.setEnabled(True)
        self._mw.voltage_step_doubleSpinBox.setEnabled(True)
        self._mw.regulation_interval_doubleSpinBox.setEnabled(True)
        self._mw.record_length_DSpinBox.setEnabled(True)
        self._mw.neglect_0_checkBox.setEnabled(True)


 ##########   Update after GUI change   ########

    def update_voltage_horizontalSlider(self, output_value):
        """ Update voltage_horizontalSlider if other GUI elements are changed.
        """
        self._mw.voltage_horizontalSlider.setValue((output_value - self._eom_regulation_logic._voltage_min) / self.slider_res)

    def update_from_voltage_horizontalSlider(self, slider_value):
        """  If voltage_horizontalSlider is moved, adjust GUI elements.
        """
        output_value = self._eom_regulation_logic._voltage_min + slider_value * self.slider_res
        self.update_voltage_doubleSpinBox(output_value)
        self.update_actual_voltage(output_value)
        self.sigGotoPos.emit(output_value)

    def update_voltage_doubleSpinBox(self, output_value):
        """ Update update_voltage_doubleSpinBox if other GUI elements are changed.
        """
        self._mw.voltage_doubleSpinBox.setValue(output_value)

    def update_from_voltage_doubleSpinBox(self, output_value=None):
        """  If update_voltage_doubleSpinBox is moved, adjust GUI elements.
        """
        if output_value is None:
            output_value = self._mw.voltage_doubleSpinBox.value()
        self.update_voltage_horizontalSlider(output_value)
        self.update_actual_voltage(output_value)
        self.sigGotoPos.emit(output_value)

###############   EOM Update Data   ########

    def update_actual_voltage(self, output_value):
        """ Update actual_voltage_doubleSpinBox.
                """
        self._eom_regulation_logic._actual_voltage=output_value
        self._mw.actual_voltage_doubleSpinBox.setValue(output_value)


    def update_plot(self, laser_signal_data_x, laser_signal_data_y,):
        """ Refresh the plot widget with new data.
        """
        #self.update_actual_voltage(output_value)
        self.laser_signal_image.setData(laser_signal_data_x, laser_signal_data_y)

    def update_goto_pos(self, output_value):
        #pass
        self._eom_regulation_logic.sigChangeAnalogOutputVoltage.emit(output_value)

    def update_suppression(self, suppression):
        self._mw.Suppression_spinbox.setValue(suppression)

############   EOM Regulation Parameters   ########

    def start_voltage_changed(self):
        start_voltage = self._mw.start_voltage_doubleSpinBox.value()
        self._eom_regulation_logic._start_voltage = start_voltage

    def rough_voltage_step_changed(self):
        rough_voltage_step = self._mw.rough_voltage_step.value()
        self._eom_regulation_logic._rough_voltage_steps = rough_voltage_step

    def fine_voltage_step_changed(self):
        fine_voltage_step = self._mw.fine_voltage_step_doubleSpinBox.value()
        self._eom_regulation_logic._fine_voltage_steps = fine_voltage_step

    def fine_step_counts_changed(self):
        fine_step_counts = self._mw.fine_step_counts_spinBox.value()
        self._eom_regulation_logic._fine_step_counts = fine_step_counts

    def voltage_step_changed(self):
        voltage_step_changed = self._mw.voltage_step_doubleSpinBox.value()
        self._eom_regulation_logic._regulation_voltage_step= voltage_step_changed

    def regulation_interval_changed(self):
        regulation_interval = self._mw.regulation_interval_doubleSpinBox.value()
        self._eom_regulation_logic._regulation_interval = regulation_interval

    def record_length_changed(self):
        record_length = self._mw.record_length_DSpinBox.value()
        self._eom_regulation_logic._record_length = record_length
        self._eom_regulation_logic.pulsedmeasurementlogic2().set_fast_counter_settings(record_length=record_length)

    def neglect_0_changed(self):
        neglect_0 = self._mw.neglect_0_checkBox.isChecked()
        self._eom_regulation_logic._neglect_0 = neglect_0


