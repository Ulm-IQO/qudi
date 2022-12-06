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
import time
from datetime import timedelta


class EOMControlGuiMainWindow(QtGui.QMainWindow):

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eom_control_gui.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class EOMControlGui(GUIBase):
    """
    This is the GUI Class for software driven EOM regulation.
    """
    _modclass = 'EOMControlGUI'
    _modtype = 'gui'

    # declare connectors
    eom_control_logic = Connector(interface='EOMControlLogic')


    def __init__(self, config, **kwargs):
        ## declare actions for state transitions
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key, config[key]))

    def on_activate(self):
        """ Definition, configuration and initialisation of the EOM regulation GUI.

          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.

        """
        self._mw = EOMControlGuiMainWindow()

        self._eom_control_logic = self.eom_control_logic()
        self._eom_control_logic._counter_logic.sigCounterUpdated.connect(self.update_counter_data_timeseries)

        self._mw.counter_plotWidget.setLabel(axis='left', text='counts', units='cs')
        self._mw.counter_plotWidget.setLabel(axis='bottom', text='Time', units='s')
        self._mw.counter_plotWidget.showGrid(x=True, y=True, alpha=0.4)
        self.counter_data_image = pg.PlotDataItem(
            pen=pg.mkPen(palette.c1, style=QtCore.Qt.SolidLine, width=1),
            symbol=None,
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=1)
        self._mw.counter_plotWidget.addItem(self.counter_data_image)
        self.counter_data_image_smoothed = pg.PlotDataItem(
            pen=pg.mkPen(palette.c2, style=QtCore.Qt.SolidLine, width=3),
            symbol=None,
            symbolPen=palette.c2,
            symbolBrush=palette.c2,
            symbolSize=1)
        self._mw.counter_plotWidget.addItem(self.counter_data_image_smoothed)

        self.plot1 = self._mw.process_plotWidget.plotItem
        self.plot1.setLabel('left', 'Contrast', units='%', color=palette.c1.name())
        self.plot1.setLabel('bottom', 'Elapsed Time', units='s')
        self.plot1.setYRange(98, 100)
        self._curve1 = pg.PlotDataItem(pen=pg.mkPen(palette.c1),
                                       symbol='o',
                                       symbolPen=palette.c1,
                                       symbolBrush=palette.c2,
                                       symbolSize=3)

        self.plot2 = pg.ViewBox()
        self.plot1.scene().addItem(self.plot2)

        self.plot1.showAxis('right')
        self._curve2 = pg.PlotDataItem(pen=pg.mkPen(palette.c2),
                                       symbol='o',
                                       symbolPen=palette.c2,
                                       symbolBrush=palette.c1,
                                       symbolSize=3)
        self.plot1.getAxis('right').setLabel('Voltage', units='V', color=palette.c2.name())
        self.plot1.getAxis('right').linkToView(self.plot2)
        self.plot2.setXLink(self.plot1)
        self.updateViews()
        self.plot1.vb.sigResized.connect(self.updateViews)
        self.plot1.addItem(self._curve1)
        self.plot2.addItem(self._curve2)

        self._mw.laser_data_plotWidget.setLabel(axis='left', text='counts', units='cs')
        self._mw.laser_data_plotWidget.setLabel(axis='bottom', text='Time', units='s')
        self._mw.laser_data_plotWidget.showGrid(x=True, y=True, alpha=0.4)
        self.laser_data_image = pg.PlotDataItem(
            pen=pg.mkPen(palette.c1, style=QtCore.Qt.SolidLine, width=1),
            symbol='o',
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=1)
        self._mw.laser_data_plotWidget.addItem(self.laser_data_image)

        self._mw.sweep_plotWidget.setLabel(axis='left', text='counts', units='cs')
        self._mw.sweep_plotWidget.setLabel(axis='bottom', text='Bias', units='V')
        self._mw.sweep_plotWidget.showGrid(x=True, y=True, alpha=0.4)
        self.sweep_data_image = pg.PlotDataItem(
            symbol='o',
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=1)
        self._mw.sweep_plotWidget.addItem(self.sweep_data_image)
        self.sweep_fit_image = pg.PlotDataItem(
            pen=pg.mkPen(palette.c2, style=QtCore.Qt.SolidLine, width=1),
            symbol=None,
            symbolPen=palette.c2,
            symbolBrush=palette.c2,
            symbolSize=1)
        self._mw.sweep_plotWidget.addItem(self.sweep_fit_image)

        # Receiving signals from control logic
        self._eom_control_logic.sigUpdateProcessValueTimeSeries.connect(self.update_process_value_timeseries, QtCore.Qt.QueuedConnection)
        self._eom_control_logic.sigUpdateControlValue.connect(self.update_control_value, QtCore.Qt.QueuedConnection)
        self._eom_control_logic.sigUpdateControlValueTimeSeries.connect(self.update_control_value_timeseries, QtCore.Qt.QueuedConnection)
        self._eom_control_logic.sigUpdateLaserData.connect(self.update_laser_data, QtCore.Qt.QueuedConnection)
        self._eom_control_logic.sigSweepStateChanged.connect(self.sweep_state_changed, QtCore.Qt.QueuedConnection)
        self._eom_control_logic.sigUpdateControlParams.connect(self.update_control_params, QtCore.Qt.QueuedConnection)
        self._eom_control_logic.sigUpdateVpi.connect(self.update_vpi)
        self._eom_control_logic.sigUpdateSweepPlot.connect(self.update_sweep_data)

        # Emitting signals to control logic
        # Double Spin Boxes
        self._mw.sweep_Action.triggered.connect(self.change_sweep_state, QtCore.Qt.QueuedConnection)
        self._mw.control_Start_Action.triggered.connect(self.start_control, QtCore.Qt.QueuedConnection)
        self._mw.control_Pause_Action.triggered.connect(self.pause_control, QtCore.Qt.QueuedConnection)
        self._mw.action_close.triggered.connect(self._mw.close)
        self._mw.action_save.triggered.connect(self._eom_control_logic.save_data)

        # Connect signals of interactive fields
        self._mw.controlVoltageStep_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.controlTimeStep_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.num_points_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.numDiffPoints_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.invertingThreshold_LineEdit.editingFinished.connect(self.inputsChanged)

        self._mw.extremum_ComboBox.currentIndexChanged.connect(self.inputsChanged)
        self._mw.extremumState = {0: 'Minimum', 1: 'Maximum'}
        self._mw.extremum_ComboBox.addItems(self._mw.extremumState.values())
        self._mw.sweepVoltageStart_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.sweepVoltageStop_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.sweepVoltageStep_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.sweepVoltageTimeStep_LineEdit.editingFinished.connect(self.inputsChanged)
        self._mw.biasVoltage_horizontalSlider.sliderMoved.connect(self.change_bias_voltage_from_slider)

        # Initialize input fields from logic
        self.initialize_inputs()

        self.restoreWindowGeometryState(self._mw)

    def on_deactivate(self):
        """ Reverse steps of activation

        @param e: error code

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        self._eom_control_logic._counter_logic.sigCounterUpdated.disconnect()

        return 0

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def initialize_inputs(self):
        self._mw.controlVoltageStep_LineEdit.setText(str(self._eom_control_logic.bias_voltage_step*1000))
        self._mw.controlTimeStep_LineEdit.setText(str(2*self._eom_control_logic.control_timestep))
        self._mw.num_points_LineEdit.setText(str(self._eom_control_logic.num_points))
        self._mw.numDiffPoints_LineEdit.setText(str(self._eom_control_logic.num_diff_points))
        self._mw.invertingThreshold_LineEdit.setText(str(self._eom_control_logic.inverting_threshold*100))

        self._mw.extremum_ComboBox.setCurrentText(str(self._mw.extremumState[self._eom_control_logic.extremum]))
        self._mw.sweepVoltageStart_LineEdit.setText(str(self._eom_control_logic.sweep_voltage_start))
        self._mw.sweepVoltageStop_LineEdit.setText(str(self._eom_control_logic.sweep_voltage_stop))
        self._mw.sweepVoltageStep_LineEdit.setText(str(self._eom_control_logic.sweep_voltage_step*1000))
        self._mw.sweepVoltageTimeStep_LineEdit.setText(str(self._eom_control_logic.sweep_timestep))

        self._mw.biasVoltage_horizontalSlider.setRange(
            0, (self._eom_control_logic._bias_voltage_max-self._eom_control_logic._bias_voltage_min)/self._eom_control_logic._bias_voltage_step_min)
        self.change_slider_from_bias(self._eom_control_logic.bias_voltages[-1])

    def inputsChanged(self):
        try:
            self._eom_control_logic.bias_voltage_step = float(self._mw.controlVoltageStep_LineEdit.text())/1000
            self._eom_control_logic.control_timestep = float(self._mw.controlTimeStep_LineEdit.text())
            self._eom_control_logic.num_points = int(self._mw.num_points_LineEdit.text())
            self._eom_control_logic.num_diff_points = int(self._mw.numDiffPoints_LineEdit.text())
            self._eom_control_logic.inverting_threshold = float(self._mw.invertingThreshold_LineEdit.text())/100

            self._eom_control_logic.extremum = 0 if self._mw.extremum_ComboBox.currentText() == 'Minimum' else 1
            self._eom_control_logic.sweep_voltage_start = float(self._mw.sweepVoltageStart_LineEdit.text())
            self._eom_control_logic.sweep_voltage_stop = float(self._mw.sweepVoltageStop_LineEdit.text())
            self._eom_control_logic.sweep_voltage_step = float(self._mw.sweepVoltageStep_LineEdit.text())/1000
            self._eom_control_logic.sweep_timestep = float(self._mw.sweepVoltageTimeStep_LineEdit.text())
            self._eom_control_logic.bias_voltage = self._mw.biasVoltage_horizontalSlider.value()
        except Exception as e:
            pass

    def update_control_params(self, pulseSeqName, histLength, histBinWidth, fcBinWidth):
        self._mw.pulseSeqName_Label.setText(pulseSeqName)
        self._mw.histBinWidth_Label.setText(histBinWidth)
        self._mw.fastcounterBinWidth_Label.setText(fcBinWidth)
        self._mw.histLength_Label.setText(histLength)


    def change_bias_voltage_from_slider(self):
        bias_voltage = self._mw.biasVoltage_horizontalSlider.value()/self._mw.biasVoltage_horizontalSlider.maximum() \
                        * (self._eom_control_logic._bias_voltage_max - self._eom_control_logic._bias_voltage_min) \
                        + self._eom_control_logic._bias_voltage_min
        self._eom_control_logic.changeBiasVoltage(bias_voltage)

    def change_slider_from_bias(self, bias_voltage):
        self._mw.biasVoltage_horizontalSlider.setValue(
            (bias_voltage - self._eom_control_logic._bias_voltage_min)/
            (self._eom_control_logic._bias_voltage_max - self._eom_control_logic._bias_voltage_min) \
            * self._mw.biasVoltage_horizontalSlider.maximum()
        )

    def change_sweep_state(self):
        self._eom_control_logic.sigChangeSweepState.emit()

    def sweep_state_changed(self, state):
        self._mw.sweep_Action.setChecked(state)

    def change_control_state(self):
        self._eom_control_logic.sigChangeControlState.emit(0)

    def start_control(self):
        self._eom_control_logic.sigStartControl.emit(self._mw.control_Start_Action.isChecked())
        self._mw.control_Pause_Action.setEnabled(self._mw.control_Start_Action.isChecked())
        self.set_inputs_state(not self._mw.control_Start_Action.isChecked())

    def pause_control(self):
        self._eom_control_logic.sigPauseControl.emit(self._mw.control_Pause_Action.isChecked())

    def stop_control(self):
        self._eom_control_logic.sigChangeControlState.emit(-1)

    def set_inputs_state(self, state):
        self._mw.controlVoltageStep_LineEdit.setEnabled(state)
        self._mw.controlTimeStep_LineEdit.setEnabled(state)
        self._mw.num_points_LineEdit.setEnabled(state)
        self._mw.numDiffPoints_LineEdit.setEnabled(state)
        self._mw.invertingThreshold_LineEdit.setEnabled(state)

        self._mw.extremum_ComboBox.setEnabled(state)
        self._mw.sweepVoltageStart_LineEdit.setEnabled(state)
        self._mw.sweepVoltageStop_LineEdit.setEnabled(state)
        self._mw.sweepVoltageStep_LineEdit.setEnabled(state)
        self._mw.sweepVoltageTimeStep_LineEdit.setEnabled(state)
        self._mw.biasVoltage_horizontalSlider.setEnabled(state)

    def update_control_value(self, control_value):
        self._mw.control_value_label.setText(str(round(control_value, 3)) + 'V')

    def update_control_value_timeseries(self, timedeltas, control_values):
        self._curve2.setData(timedeltas, control_values)

    def update_process_value_timeseries(self, timedeltas, process_value):
        self._mw.process_value_label.setText(str(round(process_value[-1]*100, 4))+'%')
        self._curve1.setData(timedeltas, 100*np.array(process_value))

    def update_laser_data(self, t, laser_data):
        self.laser_data_image.setData(t, laser_data)

    def update_counter_data_timeseries(self):
        x_vals = np.arange(0, self._eom_control_logic._counter_logic.get_count_length())/self._eom_control_logic._counter_logic.get_count_frequency()

        self.counter_data_image.setData(
            y=self._eom_control_logic._counter_logic.countdata.flatten(), x=x_vals)
        self.counter_data_image_smoothed.setData(
            y=self._eom_control_logic._counter_logic.countdata_smoothed.flatten(), x=x_vals
            )
        self._mw.counter_data_smoothed_Label.setText(str(self._eom_control_logic._counter_logic.countdata_smoothed.flatten()[-1]))

    def updateViews(self):
        self.plot2.setGeometry(self.plot1.vb.sceneBoundingRect())
        self.plot2.linkedViewChanged(self.plot1.vb, self.plot2.XAxis)

    def update_sweep_data(self, V, cts, fit):
        self.sweep_data_image.setData(V, cts)
        self.sweep_fit_image.setData(V, fit)

    def update_vpi(self, Vpi, V0):
        self._mw.vpi_Label.setText(str(Vpi))
        self._mw.v0_Label.setText(str(V0))