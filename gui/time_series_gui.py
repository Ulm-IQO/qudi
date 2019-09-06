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
from qtpy import QtCore, QtGui
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
        self._pw = self._mw.data_trace_PlotWidget

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')
        self._pw.disableAutoRange()
        self._pw.setMouseEnabled(x=False, y=False)
        self._pw.setMouseTracking(False)
        self._pw.setMenuEnabled(False)
        self._pw.hideButtons()

        self.curves = list()
        for i, ch in enumerate(self._time_series_logic.channel_names):
            if i % 2 == 0:
                self.curves.append(pg.PlotCurveItem(pen={'color': palette.c2, 'width': 4},
                                                    clipToView=True,
                                                    downsampleMethod='subsample',
                                                    autoDownsample=True))
                self._pw.addItem(self.curves[-1])
                self.curves.append(pg.PlotCurveItem(pen={'color': palette.c1, 'width': 2},
                                                    clipToView=True,
                                                    downsampleMethod='subsample',
                                                    autoDownsample=True))
                self._pw.addItem(self.curves[-1])
            else:
                self.curves.append(pg.PlotCurveItem(pen={'color': palette.c4, 'width': 4},
                                                    clipToView=True,
                                                    downsampleMethod='subsample',
                                                    autoDownsample=True))
                self._pw.addItem(self.curves[-1])
                self.curves.append(pg.PlotCurveItem(pen={'color': palette.c3, 'width': 2},
                                                    clipToView=True,
                                                    downsampleMethod='subsample',
                                                    autoDownsample=True))
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
        self._mw.start_trace_Action.triggered.connect(self.start_clicked)
        self._mw.record_trace_Action.triggered.connect(self.record_clicked)

        self._mw.trace_length_DoubleSpinBox.editingFinished.connect(self.data_window_changed)
        self._mw.data_rate_DoubleSpinBox.editingFinished.connect(self.data_rate_changed)
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
        self._mw.start_trace_Action.triggered.disconnect()
        self._mw.record_trace_Action.triggered.disconnect()
        self._mw.trace_length_DoubleSpinBox.editingFinished.disconnect()
        self._mw.data_rate_DoubleSpinBox.editingFinished.disconnect()
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

    @QtCore.Slot()
    @QtCore.Slot(np.ndarray, np.ndarray)
    @QtCore.Slot(np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    def update_data(self, data_time=None, data=None, smooth_time=None, smooth_data=None):
        """ The function that grabs the data and sends it to the plot.
        """
        if data_time is None and data is None and smooth_data is None and smooth_time is None:
            data = self._time_series_logic.trace_data
            data_time = self._time_series_logic.trace_time_axis
            smooth_data = self._time_series_logic.trace_data_averaged
            smooth_time = self._time_series_logic.averaged_trace_time_axis
        elif (data_time is None) ^ (data is None) or (smooth_time is None) ^ (smooth_data is None):
            self.log.error('Must provide a full data set of x and y values. update_data failed.')
            return

        start = time.perf_counter()
        if data is not None:
            x_min, x_max = data_time.min(), data_time.max()
            y_min, y_max = data.min(), data.max()
            self._pw.setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), update=False)

        # if update_all:
        for i, ch in enumerate(self._time_series_logic.channel_names):
            if data is not None:
                self.curves[2 * i].setData(y=data[i], x=data_time)
            if smooth_data is not None:
                self.curves[2 * i + 1].setData(y=smooth_data[i], x=smooth_time)

        # QtWidgets.QApplication.processEvents()
        # self._pw.autoRange()
        print('Plot time: {0:.3e}s'.format(time.perf_counter() - start))
        return 0

    @QtCore.Slot()
    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        self._mw.start_trace_Action.setEnabled(False)
        self._mw.record_trace_Action.setEnabled(False)
        if self._mw.start_trace_Action.isChecked():
            self.sigStartCounter.emit()
        else:
            self.sigStopCounter.emit()
        return

    @QtCore.Slot()
    def record_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._mw.record_trace_Action.setEnabled(False)
        self._mw.data_rate_DoubleSpinBox.setEnabled(False)
        self._mw.oversampling_SpinBox.setEnabled(False)
        self._mw.trace_length_DoubleSpinBox.setEnabled(False)
        if self._mw.record_trace_Action.isChecked():
            self.sigStartRecording.emit()
        else:
            self.sigStopRecording.emit()
        return

    @QtCore.Slot()
    @QtCore.Slot(bool, bool)
    def update_status(self, running=None, recording=None):
        """
        Function to ensure that the GUI displays the current measurement status

        @param bool running: True if the data trace streaming is running
        @param bool recording: True if the data trace recording is active
        """
        if running is None:
            running = self._time_series_logic.module_state() == 'locked'
        if recording is None:
            recording = self._time_series_logic.data_recording_active

        self._mw.start_trace_Action.setChecked(running)
        self._mw.start_trace_Action.setText('Stop trace' if running else 'Start trace')

        self._mw.record_trace_Action.setChecked(recording)
        self._mw.record_trace_Action.setText('Save recorded' if recording else 'Start recording')
        self._mw.data_rate_DoubleSpinBox.setEnabled(not recording)
        self._mw.oversampling_SpinBox.setEnabled(not recording)
        self._mw.trace_length_DoubleSpinBox.setEnabled(not recording)

        self._mw.start_trace_Action.setEnabled(True)
        self._mw.record_trace_Action.setEnabled(True)
        return

    @QtCore.Slot()
    def data_window_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
        val = self._mw.trace_length_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'trace_window_size': val})
        # self._pw.setXRange(0,
        #                    self._counting_logic.count_length / self._counting_logic.count_frequency)
        return

    @QtCore.Slot()
    def data_rate_changed(self):
        """ Handling the change of the count_frequency and sending it to the measurement.
        """
        val = self._mw.data_rate_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'data_rate': val})
        return

    @QtCore.Slot()
    def oversampling_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        val = self._mw.oversampling_SpinBox.value()
        self.sigSettingsChanged.emit({'oversampling_factor': val})
        return

    @QtCore.Slot()
    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.data_trace_DockWidget.show()
        # self._mw.slow_counter_control_DockWidget.show()
        self._mw.trace_settings_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.data_trace_DockWidget.setFloating(False)
        self._mw.trace_settings_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.data_trace_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.trace_settings_DockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.trace_control_ToolBar)

        # Restore status if something went wrong
        self.update_status(self._time_series_logic.module_state() == 'locked',
                           self._time_series_logic.data_recording_active)
        return 0

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_settings(self, settings_dict=None):
        if settings_dict is None:
            settings_dict = self._time_series_logic.all_settings

        if 'oversampling_factor' in settings_dict:
            self._mw.oversampling_SpinBox.blockSignals(True)
            self._mw.oversampling_SpinBox.setValue(settings_dict['oversampling_factor'])
            self._mw.oversampling_SpinBox.blockSignals(False)
        if 'trace_window_size' in settings_dict:
            self._mw.trace_length_DoubleSpinBox.blockSignals(True)
            self._mw.trace_length_DoubleSpinBox.setValue(settings_dict['trace_window_size'])
            self._mw.trace_length_DoubleSpinBox.blockSignals(False)
        if 'data_rate' in settings_dict:
            self._mw.data_rate_DoubleSpinBox.blockSignals(True)
            self._mw.data_rate_DoubleSpinBox.setValue(settings_dict['data_rate'])
            self._mw.data_rate_DoubleSpinBox.blockSignals(False)
        return
