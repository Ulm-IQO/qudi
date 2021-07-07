# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for ODMR control.

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
import datetime
import numpy as np
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.util import units
from qudi.core.module import GuiBase
from qudi.core.gui.qtwidgets.fitting import FitConfigurationDialog
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.paths import get_artwork_dir

from .odmr_control_dockwidget import OdmrScanControlDockWidget, OdmrCwControlDockWidget
from .odmr_fit_dockwidget import OdmrFitDockWidget
from .odmr_main_window import OdmrMainWindow
from .odmr_settings_dialog import OdmrSettingsDialog


class OdmrGui(GuiBase):
    """
    This is the GUI Class for ODMR measurements
    """

    # declare connectors
    _odmr_logic = Connector(name='odmr_logic', interface='OdmrLogic')

    # declare status variables
    _max_shown_scans = StatusVar(name='max_shown_scans', default=50)

    sigToggleScan = QtCore.Signal(bool, bool)
    sigToggleCw = QtCore.Signal(bool)
    sigDoFit = QtCore.Signal(str, str, int)  # fit_config, channel, range_index
    sigSaveData = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mw = None
        self._plot_widget = None
        self._scan_control_dockwidget = None
        self._cw_control_dockwidget = None
        self._fit_dockwidget = None
        self._fit_config_dialog = None
        self._odmr_settings_dialog = None

        self.__cw_control_available = False  # Flag indicating if CW control is available

    def on_activate(self):
        # Create main window
        logic = self._odmr_logic()
        data_constraints = logic.data_constraints
        mw_constraints = logic.microwave_constraints
        self.__cw_control_available = True
        self._mw = OdmrMainWindow()
        self._plot_widget = self._mw.centralWidget()
        # ToDo: Get constraints from scanner
        self._scan_control_dockwidget = OdmrScanControlDockWidget(
            parent=self._mw,
            power_range=mw_constraints.power_limits,
            frequency_range=mw_constraints.frequency_limits,
            data_channels=data_constraints.channel_names,
            points_range=mw_constraints.scan_size_limits
        )
        if self.__cw_control_available:
            self._cw_control_dockwidget = OdmrCwControlDockWidget(
                parent=self._mw,
                power_range=mw_constraints.power_limits,
                frequency_range=mw_constraints.frequency_limits
            )
        else:
            self._cw_control_dockwidget = OdmrCwControlDockWidget(parent=self._mw)
        self._fit_dockwidget = OdmrFitDockWidget(parent=self._mw, fit_container=logic.fit_container)
        self._fit_config_dialog = FitConfigurationDialog(parent=self._mw,
                                                         fit_config_model=logic.fit_config_model)
        self._odmr_settings_dialog = OdmrSettingsDialog(parent=self._mw)

        # Initialize widget contents
        self._data_selection_changed()
        self._update_scan_parameters()
        self._update_scan_state()
        self._update_cw_parameters()
        self._update_cw_state()
        self._restore_odmr_settings()

        # Connect signals
        self.__connect_main_window_actions()
        self.__connect_fit_control_signals()
        self.__connect_cw_control_signals()
        self.__connect_scan_control_signals()
        self.__connect_logic_signals()
        self.__connect_gui_signals()

        # Hide CW controls if no CW source is connected to logic
        if not self.__cw_control_available:
            self._mw.action_toggle_cw.setVisible(False)
            self._mw.action_show_cw_controls.setEnabled(False)

        self.restore_default_view()
        self.show()

    def on_deactivate(self):
        # Disconnect signals
        self.__disconnect_main_window_actions()
        self.__disconnect_fit_control_signals()
        self.__disconnect_cw_control_signals()
        self.__disconnect_scan_control_signals()
        self.__disconnect_logic_signals()
        self.__disconnect_gui_signals()
        # Close dialogs and windows
        self._odmr_settings_dialog.close()
        self._fit_config_dialog.close()
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def __connect_main_window_actions(self):
        self._mw.action_toggle_measurement.triggered[bool].connect(self.run_stop_odmr)
        self._mw.action_resume_measurement.triggered.connect(self.resume_odmr)
        self._mw.action_save_measurement.triggered.connect(self.save_data)
        self._mw.action_toggle_cw.triggered[bool].connect(self.toggle_cw_mode)
        self._mw.action_show_cw_controls.triggered[bool].connect(
            self._cw_control_dockwidget.setVisible
        )
        self._mw.action_restore_default_view.triggered.connect(self.restore_default_view)
        self._mw.action_show_odmr_settings.triggered.connect(self._odmr_settings_dialog.exec_)
        # Let fit config be opened non-modal. So the user can switch back and forth between fit
        # config editing and data fitting in ODMR main window.
        self._mw.action_show_fit_configuration.triggered.connect(self._fit_config_dialog.show)

    def __connect_cw_control_signals(self):
        self._cw_control_dockwidget.sigCwParametersChanged.connect(
            self._odmr_logic().set_cw_parameters
        )
        self._cw_control_dockwidget.sigClosed.connect(
            lambda: self._mw.action_show_cw_controls.setChecked(False)
        )

    def __connect_fit_control_signals(self):
        self._fit_dockwidget.fit_widget.sigDoFit.connect(self._fit_clicked)

    def __connect_scan_control_signals(self):
        logic = self._odmr_logic()
        self._scan_control_dockwidget.sigRangeCountChanged.connect(
            logic.set_frequency_range_count, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigRangeChanged.connect(
            logic.set_frequency_range, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigRuntimeChanged.connect(
            logic.set_runtime, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigAveragedScansChanged.connect(
            logic.set_scans_to_average, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigDataSelectionChanged.connect(self._data_selection_changed)

        self._odmr_settings_dialog.button_box.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self._apply_odmr_settings
        )
        self._odmr_settings_dialog.button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
            self._apply_odmr_settings
        )
        self._odmr_settings_dialog.button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(
            self._restore_odmr_settings
        )

    def __connect_gui_signals(self):
        logic = self._odmr_logic()
        self.sigToggleScan.connect(logic.toggle_odmr_scan, QtCore.Qt.QueuedConnection)
        self.sigToggleCw.connect(logic.toggle_cw_output, QtCore.Qt.QueuedConnection)
        self.sigDoFit.connect(logic.do_fit, QtCore.Qt.QueuedConnection)
        self.sigSaveData.connect(logic.save_odmr_data, QtCore.Qt.QueuedConnection)

    def __connect_logic_signals(self):
        logic = self._odmr_logic()
        logic.sigScanStateUpdated.connect(self._update_scan_state, QtCore.Qt.QueuedConnection)
        logic.sigCwStateUpdated.connect(self._update_cw_state, QtCore.Qt.QueuedConnection)
        logic.sigElapsedUpdated.connect(self._mw.set_elapsed, QtCore.Qt.QueuedConnection)
        logic.sigScanParametersUpdated.connect(
            self._update_scan_parameters, QtCore.Qt.QueuedConnection
        )
        logic.sigCwParametersUpdated.connect(self._update_cw_parameters, QtCore.Qt.QueuedConnection)
        logic.sigScanDataUpdated.connect(self._update_scan_data, QtCore.Qt.QueuedConnection)
        logic.sigFitUpdated.connect(self._update_fit_result, QtCore.Qt.QueuedConnection)

    def __disconnect_main_window_actions(self):
        self._mw.action_toggle_measurement.triggered[bool].disconnect()
        self._mw.action_resume_measurement.triggered.disconnect()
        self._mw.action_save_measurement.triggered.disconnect()
        self._mw.action_toggle_cw.triggered[bool].disconnect()
        self._mw.action_show_cw_controls.triggered[bool].disconnect()
        self._mw.action_restore_default_view.triggered.disconnect()
        self._mw.action_show_odmr_settings.triggered.disconnect()
        self._mw.action_show_fit_configuration.triggered.disconnect()

    def __disconnect_cw_control_signals(self):
        self._cw_control_dockwidget.sigCwParametersChanged.disconnect()
        self._cw_control_dockwidget.sigClosed.disconnect()

    def __disconnect_fit_control_signals(self):
        self._fit_dockwidget.fit_widget.sigDoFit.disconnect()

    def __disconnect_scan_control_signals(self):
        self._scan_control_dockwidget.sigRangeCountChanged.disconnect()
        self._scan_control_dockwidget.sigRangeChanged.disconnect()
        self._scan_control_dockwidget.sigRuntimeChanged.disconnect()
        self._scan_control_dockwidget.sigAveragedScansChanged.disconnect()
        self._scan_control_dockwidget.sigDataSelectionChanged.disconnect()

    def __disconnect_gui_signals(self):
        self.sigToggleScan.disconnect()
        self.sigToggleCw.disconnect()
        self.sigDoFit.disconnect()
        self.sigSaveData.disconnect()

    def __disconnect_logic_signals(self):
        logic = self._odmr_logic()
        logic.sigScanStateUpdated.disconnect(self._update_scan_state)
        logic.sigCwStateUpdated.disconnect(self._update_cw_state)
        logic.sigElapsedUpdated.disconnect(self._mw.set_elapsed)
        logic.sigScanParametersUpdated.disconnect(self._update_scan_parameters)
        logic.sigCwParametersUpdated.disconnect(self._update_cw_parameters)
        logic.sigScanDataUpdated.disconnect(self._update_scan_data)
        logic.sigFitUpdated.disconnect(self._update_fit_result)

    @QtCore.Slot()
    def restore_default_view(self):
        self._scan_control_dockwidget.setFloating(False)
        self._fit_dockwidget.setFloating(False)
        self._mw.action_show_cw_controls.setChecked(True)
        self._cw_control_dockwidget.setFloating(False)
        self._cw_control_dockwidget.setVisible(self.__cw_control_available)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._cw_control_dockwidget)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._scan_control_dockwidget)
        self._mw.splitDockWidget(self._cw_control_dockwidget,
                                 self._scan_control_dockwidget,
                                 QtCore.Qt.Vertical)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._fit_dockwidget)

    @QtCore.Slot(bool)
    def run_stop_odmr(self, is_checked):
        """ Manages what happens if odmr scan is started/stopped. """
        # Disable controls until logic feedback is activating them again
        self._mw.action_toggle_measurement.setEnabled(False)
        self._mw.action_resume_measurement.setEnabled(False)
        self._mw.action_save_measurement.setEnabled(False)
        self._mw.action_toggle_cw.setEnabled(False)
        self._cw_control_dockwidget.parameters_set_enabled(False)
        self._scan_control_dockwidget.scan_parameters_set_enabled(False)
        # Notify logic
        self.sigToggleScan.emit(is_checked, False)  # start measurement, resume flag

    @QtCore.Slot()
    def resume_odmr(self):
        # Disable controls until logic feedback is activating them again
        self._mw.action_toggle_measurement.setEnabled(False)
        self._mw.action_resume_measurement.setEnabled(False)
        self._mw.action_save_measurement.setEnabled(False)
        self._mw.action_toggle_cw.setEnabled(False)
        self._cw_control_dockwidget.parameters_set_enabled(False)
        self._scan_control_dockwidget.scan_parameters_set_enabled(False)
        # Notify logic
        self.sigToggleScan.emit(True, True)  # start measurement, resume flag

    @QtCore.Slot(bool)
    def toggle_cw_mode(self, is_checked):
        """ Starts or stops CW microwave output if no measurement is running. """
        # Disable controls until logic feedback is activating them again
        self._mw.action_toggle_measurement.setEnabled(False)
        self._mw.action_resume_measurement.setEnabled(False)
        self._mw.action_toggle_cw.setEnabled(False)
        self._cw_control_dockwidget.parameters_set_enabled(False)
        # Notify logic
        self.sigToggleCw.emit(is_checked)

    @QtCore.Slot()
    def _apply_odmr_settings(self):
        self._odmr_logic().set_sample_rate(
            data_rate=self._odmr_settings_dialog.data_rate_spinbox.value(),
            oversampling=self._odmr_settings_dialog.oversampling_spinbox.value()
        )
        self._max_shown_scans = self._odmr_settings_dialog.max_scans_shown_spinbox.value()

    @QtCore.Slot()
    def _restore_odmr_settings(self):
        logic = self._odmr_logic()
        self._odmr_settings_dialog.oversampling_spinbox.setValue(logic.oversampling)
        self._odmr_settings_dialog.data_rate_spinbox.setValue(logic.data_rate)
        self._odmr_settings_dialog.max_scans_shown_spinbox.setValue(self._max_shown_scans)

    @QtCore.Slot(bool)
    def _update_scan_state(self, running=None):
        """ Update the display for a change in the microwave status (mode and output).

        @param bool running:
        """
        if running is None:
            running = self._odmr_logic().module_state() != 'idle'
        # set controls state
        self._mw.action_toggle_measurement.setEnabled(True)
        self._mw.action_resume_measurement.setEnabled(not running)
        self._mw.action_save_measurement.setEnabled(True)
        self._mw.action_toggle_cw.setEnabled(not running)
        self._cw_control_dockwidget.parameters_set_enabled(not running)
        self._scan_control_dockwidget.scan_parameters_set_enabled(not running)
        self._mw.action_toggle_measurement.setChecked(running)

    def _update_cw_state(self, running=None):
        """
        Update the display for a change in the microwave status (mode and output).

        @param bool running:
        """
        # ToDo: Get running state if running is None
        if running is None:
            return
        # set controls state
        self._mw.action_toggle_measurement.setEnabled(not running)
        self._mw.action_resume_measurement.setEnabled(not running)
        self._mw.action_toggle_cw.setEnabled(True)
        self._mw.action_toggle_cw.setChecked(running)
        self._cw_control_dockwidget.parameters_set_enabled(not running)

    def _update_cw_parameters(self, parameters=None):
        if parameters is None:
            parameters = self._odmr_logic().cw_parameters
        self._cw_control_dockwidget.set_cw_parameters(frequency=parameters.get('frequency', None),
                                                      power=parameters.get('power', None))

    def _update_scan_data(self):
        """ Refresh the plot widgets with new data. """
        range_index = self._scan_control_dockwidget.selected_range
        channel = self._scan_control_dockwidget.selected_channel
        logic = self._odmr_logic()
        signal_data = logic.signal_data
        raw_data = logic.raw_data
        frequency_data = logic.frequency_data
        self._plot_widget.set_data(
            frequency_data[range_index],
            raw_data[channel][range_index][:, :self._max_shown_scans],
            signal_data[channel][range_index]
        )

    def _update_scan_parameters(self, param_dict=None):
        """ Update the scan parameetrs in the GUI

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic.
        """
        if param_dict is None:
            logic = self._odmr_logic()
            param_dict = logic.scan_parameters

        param = param_dict.get('data_rate')
        if param is not None:
            self._odmr_settings_dialog.data_rate_spinbox.setValue(param)

        param = param_dict.get('oversampling')
        if param is not None:
            self._odmr_settings_dialog.oversampling_spinbox.setValue(param)

        param = param_dict.get('run_time')
        if param is not None:
            self._scan_control_dockwidget.set_runtime(param)

        param = param_dict.get('averaged_scans')
        if param is not None:
            self._scan_control_dockwidget.set_averaged_scans(param)

        param = param_dict.get('power')
        if param is not None:
            self._scan_control_dockwidget.set_scan_power(param)

        param = param_dict.get('frequency_ranges')
        if param is not None:
            self._scan_control_dockwidget.set_range_count(len(param))
            for ii, range_tuple in enumerate(param):
                self._scan_control_dockwidget.set_frequency_range(range_tuple, ii)

    def _data_selection_changed(self, channel=None, range_index=None):
        if channel is None:
            channel = self._scan_control_dockwidget.selected_channel
        if range_index is None:
            range_index = self._scan_control_dockwidget.selected_range
        logic = self._odmr_logic()
        channel_unit = logic.data_constraints.channel_units[channel]
        self._plot_widget.set_signal_label(channel, channel_unit)
        self._update_scan_data()
        fit_cfg_result = logic.fit_results[channel][range_index]
        self._update_fit_result(fit_cfg_result, channel, range_index)

    def _update_fit_result(self, fit_cfg_result, channel, range_index):
        current_channel = self._scan_control_dockwidget.selected_channel
        current_range_index = self._scan_control_dockwidget.selected_range
        if current_channel == channel and current_range_index == range_index:
            if fit_cfg_result is None:
                self._fit_dockwidget.fit_widget.update_fit_result('No Fit', None)
                self._plot_widget.set_fit_data(None, None)
            else:
                self._fit_dockwidget.fit_widget.update_fit_result(*fit_cfg_result)
                self._plot_widget.set_fit_data(*fit_cfg_result[1].high_res_best_fit)

    def _fit_clicked(self, fit_config):
        channel = self._scan_control_dockwidget.selected_channel
        range_index = self._scan_control_dockwidget.selected_range
        self.sigDoFit.emit(fit_config, channel, range_index)

    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        self.sigSaveData.emit(self._mw.save_nametag_lineedit.text())
