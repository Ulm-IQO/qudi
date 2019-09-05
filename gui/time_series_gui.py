# -*- coding: utf-8 -*-

"""
This file contains the qudi time series streaming gui.

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
import time
import pyqtgraph as pg

from core.module import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class TimeSeriesMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_time_series_gui.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class TimeSeriesGui(GUIBase):
    """ FIXME: Please document
    """

    # declare connectors
    _time_series_logic_con = Connector(interface='CounterLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()
    sigStartRecording = QtCore.Signal()
    sigStopRecording = QtCore.Signal()
    sigSettingsChanged = QtCore.Signal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._time_series_logic = None
        self._mw = None
        self._pw = None
        self.curves = None
        self._display_trace = None
        self._trace_selection = None

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._time_series_logic = self._time_series_logic_con()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'TimeSeriesMainWindow' to create the GUI window
        self._mw = TimeSeriesMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Plot labels.
        self._pw = self._mw.counter_trace_PlotWidget

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')
        # self._pw.disableAutoRange()

        self.curves = list()

        for i, ch in enumerate(self._time_series_logic.channel_names):
            if i % 2 == 0:
                self.curves.append(pg.PlotDataItem(pen={'color': palette.c2, 'width': 4}, symbol=None))
                self._pw.addItem(self.curves[-1])
                self.curves.append(pg.PlotDataItem(pen={'color': palette.c1, 'width': 2}, symbol=None))
                self._pw.addItem(self.curves[-1])
            else:
                self.curves.append(pg.PlotDataItem(pen={'color': palette.c4, 'width': 4}, symbol=None))
                self._pw.addItem(self.curves[-1])
                self.curves.append(pg.PlotDataItem(pen={'color': palette.c3, 'width': 2}, symbol=None))
                self._pw.addItem(self.curves[-1])

        # setting the x axis length correctly
        # self._pw.setXRange(0, self._time_series_logic.trace_window_size)

        #####################
        # Setting default parameters
        self.update_status(self._time_series_logic.module_state() == 'locked',
                           self._time_series_logic.data_recording_active)
        self.update_settings(self._time_series_logic.all_settings)
        self.update_data()

        #####################
        # Connecting user interactions
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.record_counts_Action.triggered.connect(self.save_clicked)

        self._mw.count_length_DoubleSpinBox.editingFinished.connect(self.data_window_changed)
        self._mw.count_freq_DoubleSpinBox.editingFinished.connect(self.data_rate_changed)
        self._mw.oversampling_SpinBox.editingFinished.connect(self.oversampling_changed)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        # starting the physical measurement
        self.sigStartCounter.connect(
            self._time_series_logic.start_reading, QtCore.Qt.QueuedConnection)
        self.sigStopCounter.connect(
            self._time_series_logic.stop_reading, QtCore.Qt.QueuedConnection)
        self.sigStartRecording.connect(
            self._time_series_logic.start_recording, QtCore.Qt.QueuedConnection)
        self.sigStopRecording.connect(
            self._time_series_logic.stop_recording, QtCore.Qt.QueuedConnection)
        self.sigSettingsChanged.connect(
            self._time_series_logic.configure_settings, QtCore.Qt.QueuedConnection)

        ##################
        # Handling signals from the logic
        self._time_series_logic.sigDataChanged.connect(
            self.update_data, QtCore.Qt.QueuedConnection)
        self._time_series_logic.sigSettingsChanged.connect(
            self.update_settings, QtCore.Qt.QueuedConnection)
        self._time_series_logic.sigStatusChanged.connect(
            self.update_status, QtCore.Qt.QueuedConnection)
        return 0

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        """ Deactivate the module
        """
        # disconnect signals
        self._mw.start_counter_Action.triggered.disconnect()
        self._mw.record_counts_Action.triggered.disconnect()
        self._mw.count_length_DoubleSpinBox.editingFinished.disconnect()
        self._mw.count_freq_DoubleSpinBox.editingFinished.disconnect()
        self._mw.oversampling_SpinBox.editingFinished.disconnect()
        self._mw.restore_default_view_Action.triggered.disconnect()
        self.sigStartCounter.disconnect()
        self.sigStopCounter.disconnect()
        self.sigStartRecording.disconnect()
        self.sigStopRecording.disconnect()
        self.sigSettingsChanged.disconnect()
        self._time_series_logic.sigDataChanged.disconnect()
        self._time_series_logic.sigSettingsChanged.disconnect()
        self._time_series_logic.sigStatusChanged.disconnect()

        self._mw.close()
        return

    def update_data(self):
        """ The function that grabs the data and sends it to the plot.
        """
        start = time.perf_counter()
        data = self._time_series_logic.trace_data
        smooth_data = self._time_series_logic.trace_data_averaged

        # x_min, x_max = x_vals.min(), x_vals.max()
        # y_min, y_max = data.min(), data.max()
        # view_range = self._pw.visibleRange()
        # if view_range.left() > x_min or view_range.right() < x_max:
        #     self._pw.setXRange(x_min, x_max)
        # elif view_range.width() > (x_max - x_min) * 0.7:
        #     self._pw.setXRange(x_min, x_max)
        #
        # if view_range.top() > y_min or view_range.bottom() < y_max:
        #     self._pw.setYRange(y_min, y_max)
        # elif view_range.height() > (y_max - y_min) * 0.7:
        #     self._pw.setYRange(y_min, y_max)

        for i, ch in enumerate(self._time_series_logic.channel_names):
            self.curves[2 * i].setData(y=self._time_series_logic.trace_data[i], x=self._time_series_logic.trace_time_axis)
            self.curves[2 * i + 1].setData(y=self._time_series_logic.trace_data_averaged[i], x=self._time_series_logic.averaged_trace_time_axis)
        print('Plot time: {0:.3e}s'.format(time.perf_counter() - start))
        return 0

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        self._mw.start_counter_Action.setEnabled(False)
        if self._time_series_logic.module_state() == 'locked':
            self.sigStopCounter.emit()
        else:
            self.sigStartCounter.emit()
        return

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._mw.record_counts_Action.setEnabled(False)
        self._mw.count_freq_DoubleSpinBox.setEnabled(False)
        self._mw.oversampling_SpinBox.setEnabled(False)
        self._mw.count_length_DoubleSpinBox.setEnabled(False)
        if self._time_series_logic.data_recording_active:
            self.sigStopRecording.emit()
        else:
            self.sigStartRecording.emit()
        return

    def update_status(self, running, recording):
        """
        Function to ensure that the GUI displays the current measurement status

        @param bool running: True if the data trace streaming is running
        @param bool recording: True if the data trace recording is active
        """
        if running:
            self._mw.start_counter_Action.setText('Stop trace')
        else:
            self._mw.start_counter_Action.setText('Start trace')

        if recording:
            self._mw.record_counts_Action.setText('Save recorded')
            self._mw.count_freq_DoubleSpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
            self._mw.count_length_DoubleSpinBox.setEnabled(False)
        else:
            self._mw.record_counts_Action.setText('Start recording')
            self._mw.count_freq_DoubleSpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)
            self._mw.count_length_DoubleSpinBox.setEnabled(True)

        self._mw.start_counter_Action.setEnabled(True)
        self._mw.record_counts_Action.setEnabled(True)
        return

    ########
    # Input parameters changed via GUI
    def data_window_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
        val = self._mw.count_length_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'trace_window_size': val})
        # self._pw.setXRange(0,
        #                    self._counting_logic.count_length / self._counting_logic.count_frequency)
        return

    def data_rate_changed(self):
        """ Handling the change of the count_frequency and sending it to the measurement.
        """
        val = self._mw.count_freq_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'data_rate': val})
        return

    def oversampling_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        val = self._mw.oversampling_SpinBox.value()
        self.sigSettingsChanged.emit({'oversampling_factor': val})
        return

    ########
    # Restore default values
    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.counter_trace_DockWidget.show()
        # self._mw.slow_counter_control_DockWidget.show()
        self._mw.slow_counter_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.counter_trace_DockWidget.setFloating(False)
        self._mw.slow_counter_parameters_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.counter_trace_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.slow_counter_parameters_DockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.counting_control_ToolBar)
        return 0

    ##########
    # Handle signals from logic
    def update_settings(self, settings_dict):
        if 'oversampling_factor' in settings_dict:
            self._mw.oversampling_SpinBox.blockSignals(True)
            self._mw.oversampling_SpinBox.setValue(settings_dict['oversampling_factor'])
            self._mw.oversampling_SpinBox.blockSignals(False)
        if 'trace_window_size' in settings_dict:
            self._mw.count_length_DoubleSpinBox.blockSignals(True)
            self._mw.count_length_DoubleSpinBox.setValue(settings_dict['trace_window_size'])
            self._mw.count_length_DoubleSpinBox.blockSignals(False)
        if 'data_rate' in settings_dict:
            self._mw.count_freq_DoubleSpinBox.blockSignals(True)
            self._mw.count_freq_DoubleSpinBox.setValue(settings_dict['data_rate'])
            self._mw.count_freq_DoubleSpinBox.blockSignals(False)
        return
