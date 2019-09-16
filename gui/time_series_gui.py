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

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from qtpy import QtCore, QtGui
from qtpy import QtWidgets
from qtpy import uic
from interface.data_instream_interface import StreamChannelType


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


class TimeSeriesSelectionDialog(QtWidgets.QDialog):
    """ Create the trace selection dialog based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'time_series_selector_dialog.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)


class TimeSeriesGui(GUIBase):
    """ FIXME: Please document
    """

    # declare connectors
    _time_series_logic_con = Connector(interface='TimeSeriesReaderLogic')

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
        self._vsd = None
        self._vsd_widgets = dict()
        self._csd = None
        self._csd_widgets = dict()
        self.curves = dict()
        self.averaged_curves = dict()

        self._hidden_data_traces = None
        self._hidden_averaged_traces = None

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

        # Get hardware constraints
        hw_constr = self._time_series_logic.streamer_constraints

        # Plot labels.
        self._pw = self._mw.data_trace_PlotWidget

        self._pw.setLabel('left', 'Not quite sure...', units='#')
        self._pw.setLabel('bottom', 'Time', units='s')
        self._pw.disableAutoRange()
        self._pw.setMouseEnabled(x=False, y=False)
        self._pw.setMouseTracking(False)
        self._pw.setMenuEnabled(False)
        self._pw.hideButtons()

        self.curves = dict()
        self.averaged_curves = dict()
        all_channels = list(hw_constr.digital_channels) + list(hw_constr.analog_channels)
        self._mw.curr_value_comboBox.addItem('None')
        self._mw.curr_value_comboBox.addItems(['average {0}'.format(ch) for ch in all_channels])
        self._mw.curr_value_comboBox.addItems(all_channels)
        self.current_value_channel_changed()
        for i, ch in enumerate(all_channels):
            if i % 2 == 0:
                # pen1 = {'color': palette.c2, 'width': 2}
                # pen2 = {'color': palette.c1, 'width': 1}
                pen1 = pg.mkPen(palette.c2, cosmetic=True)
                pen2 = pg.mkPen(palette.c1, cosmetic=True)
            else:
                # pen1 = {'color': palette.c4, 'width': 2}
                # pen2 = {'color': palette.c3, 'width': 1}
                pen1 = pg.mkPen(palette.c4, cosmetic=True)
                pen2 = pg.mkPen(palette.c3, cosmetic=True)
            self.averaged_curves[ch] = pg.PlotCurveItem(pen=pen1,
                                                        clipToView=True,
                                                        downsampleMethod='subsample',
                                                        autoDownsample=True)
            self.curves[ch] = pg.PlotCurveItem(pen=pen2,
                                               clipToView=True,
                                               downsampleMethod='subsample',
                                               autoDownsample=True)
            self._pw.addItem(self.curves[ch])
        for curve in self.averaged_curves.values():
            self._pw.addItem(curve)

        #####################
        # Set up channel settings dialog
        self._init_channel_settings_dialog()

        #####################
        # Set up trace view selection dialog
        self._init_trace_view_selection_dialog()

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
        self._mw.trace_snapshot_Action.triggered.connect(
            self._time_series_logic.save_trace_snapshot, QtCore.Qt.QueuedConnection)

        self._mw.trace_length_DoubleSpinBox.editingFinished.connect(self.data_window_changed)
        self._mw.data_rate_DoubleSpinBox.editingFinished.connect(self.data_rate_changed)
        self._mw.oversampling_SpinBox.editingFinished.connect(self.oversampling_changed)
        self._mw.moving_average_spinBox.editingFinished.connect(self.moving_average_changed)
        self._mw.curr_value_comboBox.currentIndexChanged.connect(self.current_value_channel_changed)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        self._mw.trace_view_selection_Action.triggered.connect(self._vsd.show)
        self._mw.channel_settings_Action.triggered.connect(self._csd.show)

        self._vsd.accepted.connect(self.apply_trace_view_selection)
        self._vsd.rejected.connect(self.keep_former_trace_view_selection)
        self._vsd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.apply_trace_view_selection)
        self._csd.accepted.connect(self.apply_channel_settings)
        self._csd.rejected.connect(self.keep_former_channel_settings)
        self._csd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.apply_channel_settings)

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
        self._vsd.accepted.disconnect()
        self._vsd.rejected.disconnect()
        self._vsd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        self._csd.accepted.disconnect()
        self._csd.rejected.disconnect()
        self._csd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()

        self._mw.start_trace_Action.triggered.disconnect()
        self._mw.record_trace_Action.triggered.disconnect()
        self._mw.trace_snapshot_Action.triggered.disconnect()
        self._mw.trace_length_DoubleSpinBox.editingFinished.disconnect()
        self._mw.data_rate_DoubleSpinBox.editingFinished.disconnect()
        self._mw.oversampling_SpinBox.editingFinished.disconnect()
        self._mw.moving_average_spinBox.editingFinished.disconnect()
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

    def _init_trace_view_selection_dialog(self):
        hw_constr = self._time_series_logic.streamer_constraints
        all_channels = list(hw_constr.digital_channels) + list(hw_constr.analog_channels)
        self._vsd = TimeSeriesSelectionDialog()
        self._vsd.setWindowTitle('View Trace Selection')
        self._vsd_widgets = dict()
        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel('Channel Name'), 0, 0)
        layout.addWidget(QtWidgets.QLabel('Hide Data?'), 0, 1)
        layout.addWidget(QtWidgets.QLabel('Hide Average?'), 0, 2)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, 1, 0, 1, 3)
        for i, chnl in enumerate(all_channels, 2):
            widget_dict = dict()
            widget_dict['label'] = QtWidgets.QLabel(chnl)
            widget_dict['checkbox1'] = QtWidgets.QCheckBox()
            widget_dict['checkbox2'] = QtWidgets.QCheckBox()
            layout.addWidget(widget_dict['label'], i, 0)
            layout.addWidget(widget_dict['checkbox1'], i, 1)
            layout.addWidget(widget_dict['checkbox2'], i, 2)
            widget_dict['checkbox1'].setChecked(False)
            widget_dict['checkbox2'].setChecked(False)
            self._vsd_widgets[chnl] = widget_dict
        layout.setRowStretch(i + 1, 1)
        self._vsd.trace_selection_scrollArea.setLayout(layout)

    def _init_channel_settings_dialog(self):
        hw_constr = self._time_series_logic.streamer_constraints
        all_channels = list(hw_constr.digital_channels) + list(hw_constr.analog_channels)
        self._csd = TimeSeriesSelectionDialog()
        self._csd.setWindowTitle('Data Channel Settings')
        self._csd_widgets = dict()
        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel('Channel Name'), 0, 0)
        layout.addWidget(QtWidgets.QLabel('Is Active?'), 0, 1)
        layout.addWidget(QtWidgets.QLabel('Moving Average?'), 0, 2)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, 1, 0, 1, 3)
        for i, chnl in enumerate(all_channels, 2):
            widget_dict = dict()
            widget_dict['label'] = QtWidgets.QLabel(chnl)
            widget_dict['checkbox1'] = QtWidgets.QCheckBox()
            widget_dict['checkbox2'] = QtWidgets.QCheckBox()
            layout.addWidget(widget_dict['label'], i, 0)
            layout.addWidget(widget_dict['checkbox1'], i, 1)
            layout.addWidget(widget_dict['checkbox2'], i, 2)
            widget_dict['checkbox1'].setChecked(True)
            widget_dict['checkbox2'].setChecked(True)
            self._csd_widgets[chnl] = widget_dict
        layout.setRowStretch(i + 1, 1)
        self._csd.trace_selection_scrollArea.setLayout(layout)

    @QtCore.Slot()
    def apply_trace_view_selection(self):
        """
        """
        for chnl, widgets in self._csd_widgets.items():
            data_active = widgets['checkbox1'].isChecked()
            average_active = widgets['checkbox2'].isChecked()

            self._toggle_channel_data_plot(chnl, data_active, average_active)
        return

    @QtCore.Slot()
    def keep_former_trace_view_selection(self):
        """
        """
        curr_items = self._pw.items()
        for chnl, widgets in self._vsd_widgets.items():
            widgets['checkbox1'].setChecked(self.curves[chnl] not in curr_items)
            widgets['checkbox2'].setChecked(self.averaged_curves[chnl] not in curr_items)
        return

    @QtCore.Slot()
    def apply_channel_settings(self):
        """
        """
        channels = tuple(ch for ch, w in self._csd_widgets.items() if w['checkbox1'].isChecked())
        av_channels = tuple(ch for ch, w in self._csd_widgets.items() if w['checkbox2'].isChecked())
        # Update combobox
        old_value = self._mw.curr_value_comboBox.currentText()
        self._mw.curr_value_comboBox.clear()
        self._mw.curr_value_comboBox.addItem('None')
        self._mw.curr_value_comboBox.addItems(
            ['average {0}'.format(ch) for ch in av_channels if ch in channels])
        self._mw.curr_value_comboBox.addItems(channels)
        index = self._mw.curr_value_comboBox.findText(old_value)
        if index < 0:
            self._mw.curr_value_comboBox.setCurrentIndex(1)
        else:
            self._mw.curr_value_comboBox.setCurrentIndex(index)
        average_active = self._time_series_logic.moving_average_width > 1
        for chnl, widgets in self._vsd_widgets.items():
            # Hide corresponding view selection
            visible = chnl in channels
            av_visible = visible and chnl in av_channels
            widgets['label'].setVisible(visible)
            widgets['checkbox1'].setVisible(visible)
            widgets['checkbox2'].setVisible(visible)
            widgets['checkbox2'].setEnabled(av_visible and average_active)
            # hide/show corresponding plot curves
            self._toggle_channel_data_plot(chnl, visible, av_visible)

        self.sigSettingsChanged.emit(
            {'active_channels': channels, 'averaged_channels': av_channels})
        return

    @QtCore.Slot()
    def keep_former_channel_settings(self):
        """
        """
        curr_channels = self._time_series_logic.channel_names
        curr_av_channels = self._time_series_logic.averaged_channels
        for chnl, widgets in self._csd_widgets.items():
            widgets['checkbox1'].setChecked(chnl in curr_channels)
            widgets['checkbox2'].setChecked(chnl in curr_av_channels)
        return

    @QtCore.Slot()
    @QtCore.Slot(np.ndarray, dict)
    @QtCore.Slot(np.ndarray, dict, object, object)
    def update_data(self, data_time=None, data=None, smooth_time=None, smooth_data=None):
        """ The function that grabs the data and sends it to the plot.
        """
        if data_time is None and data is None and smooth_data is None and smooth_time is None:
            data_time, data = self._time_series_logic.trace_data
            smooth_time, smooth_data = self._time_series_logic.averaged_trace_data
        elif (data_time is None) ^ (data is None) or (smooth_time is None) ^ (smooth_data is None):
            self.log.error('Must provide a full data set of x and y values. update_data failed.')
            return

        x_min, x_max = np.inf, -np.inf
        y_min, y_max = np.inf, -np.inf
        if data is not None:
            x_min, x_max = min(x_min, data_time.min()), max(x_max, data_time.max())
            for channel, y_arr in data.items():
                y_min, y_max = min(y_min, y_arr.min()), max(y_max, y_arr.max())
                self.curves[channel].setData(y=y_arr, x=data_time)
        if smooth_data is not None:
            x_min, x_max = min(x_min, smooth_time.min()), max(x_max, smooth_time.max())
            for channel, y_arr in smooth_data.items():
                y_min, y_max = min(y_min, y_arr.min()), max(y_max, y_arr.max())
                self.averaged_curves[channel].setData(y=y_arr, x=smooth_time)

        if data is not None or smooth_data is not None:
            self._pw.setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), update=False)

        curr_value_channel = self._mw.curr_value_comboBox.currentText()
        if curr_value_channel != 'None':
            if curr_value_channel.startswith('average '):
                chnl = curr_value_channel.split('average ', 1)[-1]
                val = smooth_data[chnl][-1]
            else:
                chnl = curr_value_channel
                val = data[chnl][-1]
            ch_type = self._time_series_logic.channel_types[chnl]
            ch_unit = self._time_series_logic.channel_units[chnl]
            if ch_type == StreamChannelType.ANALOG:
                self._mw.curr_value_Label.setText('{0:.3f} {1}'.format(val, ch_unit))
            else:
                self._mw.curr_value_Label.setText('{0:,d} {1}'.format(int(round(val)), ch_unit))
        return 0

    @QtCore.Slot()
    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        self._mw.start_trace_Action.setEnabled(False)
        self._mw.record_trace_Action.setEnabled(False)
        self._mw.data_rate_DoubleSpinBox.setEnabled(False)
        self._mw.oversampling_SpinBox.setEnabled(False)
        self._mw.trace_length_DoubleSpinBox.setEnabled(False)
        self._mw.moving_average_spinBox.setEnabled(False)
        self._mw.channel_settings_Action.setEnabled(False)
        if self._mw.start_trace_Action.isChecked():
            settings = {'trace_window_size': self._mw.trace_length_DoubleSpinBox.value(),
                        'data_rate': self._mw.data_rate_DoubleSpinBox.value(),
                        'oversampling_factor': self._mw.oversampling_SpinBox.value(),
                        'moving_average_width': self._mw.moving_average_spinBox.value()}
            self.sigSettingsChanged.emit(settings)
            self.sigStartCounter.emit()
        else:
            self.sigStopCounter.emit()
        return

    @QtCore.Slot()
    def record_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._mw.start_trace_Action.setEnabled(False)
        self._mw.record_trace_Action.setEnabled(False)
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

        self._mw.data_rate_DoubleSpinBox.setEnabled(not running)
        self._mw.oversampling_SpinBox.setEnabled(not running)
        self._mw.trace_length_DoubleSpinBox.setEnabled(not running)
        self._mw.moving_average_spinBox.setEnabled(not running)
        self._mw.channel_settings_Action.setEnabled(not running)

        self._mw.start_trace_Action.setEnabled(True)
        self._mw.record_trace_Action.setEnabled(running)
        return

    @QtCore.Slot()
    def data_window_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
        val = self._mw.trace_length_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'trace_window_size': val})
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
    def moving_average_changed(self):
        """
        """
        val = self._mw.moving_average_spinBox.value()
        self.sigSettingsChanged.emit({'moving_average_width': val})

    @QtCore.Slot()
    def current_value_channel_changed(self):
        """
        """
        val = self._mw.curr_value_comboBox.currentText()
        self._mw.curr_value_Label.setVisible(val != 'None')

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
        self.update_status()
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
        if 'moving_average_width' in settings_dict:
            val = settings_dict['moving_average_width']
            self._mw.moving_average_spinBox.blockSignals(True)
            self._mw.moving_average_spinBox.setValue(val)
            self._mw.moving_average_spinBox.blockSignals(False)
            if self.curves and self.averaged_curves:
                if val > 1:
                    for chnl, w in self._vsd_widgets.items():
                        average_active = self._csd_widgets[chnl]['checkbox2'].isChecked()
                        data_active = self._csd_widgets[chnl]['checkbox1'].isChecked()
                        if not w['checkbox2'].isEnabled() and average_active:
                            w['checkbox2'].setEnabled(True)
                            w['checkbox2'].setChecked(False)
                        self._toggle_channel_data_plot(chnl, data_active, average_active)
                else:
                    for chnl, w in self._vsd_widgets.items():
                        w['checkbox2'].setEnabled(False)
                        w['checkbox2'].setChecked(True)
                        data_active = self._csd_widgets[chnl]['checkbox1'].isChecked()
                        self._toggle_channel_data_plot(chnl, data_active, False)
        return

    def _toggle_channel_data_plot(self, channel, show_data, show_average):
        """
        """
        if channel not in self.curves or channel not in self.averaged_curves:
            return

        data_visible = self.curves[channel] in self._pw.items()
        average_visible = self.averaged_curves[channel] in self._pw.items()

        if data_visible:
            self._pw.removeItem(self.curves[channel])
        if average_visible:
            self._pw.removeItem(self.averaged_curves[channel])

        if show_data and not self._vsd_widgets[channel]['checkbox1'].isChecked():
            self._pw.addItem(self.curves[channel])
        if show_average and not self._vsd_widgets[channel]['checkbox2'].isChecked():
            self._pw.addItem(self.averaged_curves[channel])
        return
