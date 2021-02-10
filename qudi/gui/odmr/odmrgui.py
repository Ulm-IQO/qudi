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
from qudi.core.util import units
from qudi.core.module import GuiBase
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.util.paths import get_artwork_dir

from .odmr_control_dockwidget import OdmrScanControlDockWidget, OdmrCwControlDockWidget
from .odmr_fit_dockwidget import OdmrFitDockWidget
from .odmr_main_window import OdmrMainWindow

#
#
# class ODMRSettingDialog(QtWidgets.QDialog):
#     """ The settings dialog for ODMR measurements.
#     """
#
#     def __init__(self):
#         # Get the path to the *.ui file
#         this_dir = os.path.dirname(__file__)
#         ui_file = os.path.join(this_dir, 'ui_odmr_settings.ui')
#
#         # Load it
#         super(ODMRSettingDialog, self).__init__()
#         uic.loadUi(ui_file, self)


class OdmrGui(GuiBase):
    """
    This is the GUI Class for ODMR measurements
    """

    # declare connectors
    _odmr_logic = Connector(name='odmr_logic', interface='OdmrLogic')

    sigToggleScan = QtCore.Signal(bool, bool)
    sigToggleCw = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mw = None
        self._plot_widget = None
        self._scan_control_dockwidget = None
        self._cw_control_dockwidget = None
        self._fit_dockwidget = None

    def on_activate(self):
        # Create main window
        logic = self._odmr_logic()
        scanner_constraints = logic.scanner_constraints
        cw_constraints = logic.cw_constraints
        self._mw = OdmrMainWindow()
        self._plot_widget = self._mw.centralWidget()
        # ToDo: Actual channel constraints
        self._scan_control_dockwidget = OdmrScanControlDockWidget(
            parent=self._mw,
            power_range=(-30, 30),
            frequency_range=(0, 10e9),
            data_channels=scanner_constraints.input_channel_names,
            points_range=scanner_constraints.frame_size_limits
        )
        self._cw_control_dockwidget = OdmrCwControlDockWidget(
            parent=self._mw,
            power_range=cw_constraints.channel_limits['Power'],
            frequency_range=cw_constraints.channel_limits['Frequency']
        )
        self._fit_dockwidget = OdmrFitDockWidget(parent=self._mw)
        self.restore_default_view()

        self._update_scan_data()

        # Connect signals
        self.__connect_main_window_actions()
        self.__connect_fit_control_signals()
        self.__connect_cw_control_signals()
        self.__connect_scan_control_signals()
        self.__connect_logic_signals()
        self.__connect_gui_signals()
        self.show()

    def on_deactivate(self):
        pass

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

    def __connect_cw_control_signals(self):
        self._cw_control_dockwidget.sigCwParametersChanged.connect(
            self._odmr_logic().set_cw_parameters
        )
        self._cw_control_dockwidget.sigClosed.connect(
            lambda: self._mw.action_show_cw_controls.setChecked(False)
        )

    def __connect_fit_control_signals(self):
        pass

    def __connect_scan_control_signals(self):
        logic = self._odmr_logic()
        self._scan_control_dockwidget.sigRangeCountChanged.connect(self._range_count_changed)
        self._scan_control_dockwidget.sigRangeChanged.connect(
            logic.set_frequency_range, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigRuntimeChanged.connect(
            logic.set_runtime, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigAveragedLinesChanged.connect(
            logic.set_average_length, QtCore.Qt.QueuedConnection
        )
        self._scan_control_dockwidget.sigDataSelectionChanged.connect(self._data_selection_changed)

    def __connect_gui_signals(self):
        logic = self._odmr_logic()
        self.sigToggleScan.connect(logic.toggle_odmr_scan, QtCore.Qt.QueuedConnection)
        self.sigToggleCw.connect(logic.toggle_cw_output, QtCore.Qt.QueuedConnection)

    def __connect_logic_signals(self):
        logic = self._odmr_logic()
        logic.sigScanStateUpdated.connect(self._update_scan_state, QtCore.Qt.QueuedConnection)
        logic.sigCwStateUpdated.connect(self._update_cw_state, QtCore.Qt.QueuedConnection)
        logic.sigElapsedUpdated.connect(self._mw.set_elapsed, QtCore.Qt.QueuedConnection)
        logic.sigScanParametersUpdated.connect(
            self._update_scan_parameters, QtCore.Qt.QueuedConnection
        )
        logic.sigScanDataUpdated.connect(self._update_scan_data, QtCore.Qt.QueuedConnection)
        # ToDo: Connect fit signal

    def restore_default_view(self):
        self._scan_control_dockwidget.setFloating(False)
        self._fit_dockwidget.setFloating(False)
        self._mw.action_show_cw_controls.setChecked(True)
        self._cw_control_dockwidget.setFloating(False)
        self._cw_control_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._cw_control_dockwidget)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._scan_control_dockwidget)
        self._mw.splitDockWidget(self._cw_control_dockwidget,
                                 self._scan_control_dockwidget,
                                 QtCore.Qt.Vertical)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._fit_dockwidget)

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

    def _update_scan_state(self, running):
        """
        Update the display for a change in the microwave status (mode and output).

        @param bool running:
        """
        # set controls state
        self._mw.action_toggle_measurement.setEnabled(True)
        self._mw.action_resume_measurement.setEnabled(not running)
        self._mw.action_save_measurement.setEnabled(True)
        self._mw.action_toggle_cw.setEnabled(not running)
        self._cw_control_dockwidget.parameters_set_enabled(not running)
        self._scan_control_dockwidget.scan_parameters_set_enabled(not running)
        self._mw.action_toggle_measurement.setChecked(running)

    def toggle_cw_mode(self, is_checked):
        """ Starts or stops CW microwave output if no measurement is running. """
        # Disable controls until logic feedback is activating them again
        self._mw.action_toggle_measurement.setEnabled(False)
        self._mw.action_resume_measurement.setEnabled(False)
        self._mw.action_toggle_cw.setEnabled(False)
        self._cw_control_dockwidget.parameters_set_enabled(False)
        # Notify logic
        self.sigToggleCw.emit(is_checked)

    def _update_cw_state(self, running):
        """
        Update the display for a change in the microwave status (mode and output).

        @param bool running:
        """
        # set controls state
        self._mw.action_toggle_measurement.setEnabled(not running)
        self._mw.action_resume_measurement.setEnabled(not running)
        self._mw.action_toggle_cw.setEnabled(True)
        self._mw.action_toggle_cw.setChecked(running)
        self._cw_control_dockwidget.parameters_set_enabled(not running)

    def _update_scan_data(self):
        """ Refresh the plot widgets with new data. """
        range_index = self._scan_control_dockwidget.selected_range
        channel = self._scan_control_dockwidget.selected_channel
        logic = self._odmr_logic()
        signal_data = logic.signal_data
        raw_data = logic.raw_data
        frequency_data = logic.frequency_data
        average_lines = logic.average_length
        self._plot_widget.set_data(
            frequency_data[range_index],
            raw_data[channel][range_index][:, :average_lines] if average_lines > 0 else raw_data[channel][range_index],
            signal_data[channel][range_index]
        )

    def average_level_changed(self):
        """
        Sends to lines to average to the logic
        """
        self.sigAverageLinesChanged.emit(self._mw.average_level_SpinBox.value())
        return

    def update_elapsedtime(self, elapsed_time, scanned_lines):
        """ Updates current elapsed measurement time and completed frequency sweeps """
        self._mw.elapsed_time_DisplayWidget.display(int(np.rint(elapsed_time)))
        self._mw.elapsed_sweeps_DisplayWidget.display(scanned_lines)
        return

    def update_settings(self):
        """ Write the new settings from the gui to the file. """
        number_of_lines = self._sd.matrix_lines_SpinBox.value()
        clock_frequency = self._sd.clock_frequency_DoubleSpinBox.value()
        oversampling = self._sd.oversampling_SpinBox.value()
        lock_in = self._sd.lock_in_CheckBox.isChecked()
        self.sigOversamplingChanged.emit(oversampling)
        self.sigLockInChanged.emit(lock_in)
        self.sigClockFreqChanged.emit(clock_frequency)
        self.sigNumberOfLinesChanged.emit(number_of_lines)
        return

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic.clock_frequency)
        self._sd.oversampling_SpinBox.setValue(self._odmr_logic.oversampling)
        self._sd.lock_in_CheckBox.setChecked(self._odmr_logic.lock_in)
        return

    def do_fit(self):
        fit_function = self._mw.fit_methods_ComboBox.getCurrentFit()[0]
        self.sigDoFit.emit(fit_function, None, None, self._mw.odmr_channel_ComboBox.currentIndex(),
                           self._mw.fit_range_SpinBox.value())
        return

    def update_fit(self, x_data, y_data, result_str_dict, current_fit):
        """ Update the shown fit. """
        if current_fit != 'No Fit':
            # display results as formatted text
            self._mw.odmr_fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            self._mw.odmr_fit_results_DisplayWidget.setPlainText(formated_results)

        self._mw.fit_methods_ComboBox.blockSignals(True)
        self._mw.fit_methods_ComboBox.setCurrentFit(current_fit)
        self._mw.fit_methods_ComboBox.blockSignals(False)

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if current_fit != 'No Fit':
            self.odmr_fit_image.setData(x=x_data, y=y_data)
            if self.odmr_fit_image not in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
        else:
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

        self._mw.odmr_PlotWidget.getViewBox().updateAutoRange()
        return

    def update_fit_range(self):
        self._odmr_logic.range_to_fit = self._mw.fit_range_SpinBox.value()
        return

    def _update_scan_parameters(self, param_dict):
        """ Update the scan parameetrs in the GUI

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic.
        """
        print('_update_scan_parameters:', param_dict)
        param = param_dict.get('sweep_mw_power')
        if param is not None:
            self._mw.sweep_power_DoubleSpinBox.blockSignals(True)
            self._mw.sweep_power_DoubleSpinBox.setValue(param)
            self._mw.sweep_power_DoubleSpinBox.blockSignals(False)

        mw_starts = param_dict.get('mw_starts')
        mw_steps = param_dict.get('mw_steps')
        mw_stops = param_dict.get('mw_stops')

        if mw_starts is not None:
            start_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('start')
            for mw_start, start_frequency_box in zip(mw_starts, start_frequency_boxes):
                start_frequency_box.blockSignals(True)
                start_frequency_box.setValue(mw_start)
                start_frequency_box.blockSignals(False)

        if mw_steps is not None:
            step_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('step')
            for mw_step, step_frequency_box in zip(mw_steps, step_frequency_boxes):
                step_frequency_box.blockSignals(True)
                step_frequency_box.setValue(mw_step)
                step_frequency_box.blockSignals(False)

        if mw_stops is not None:
            stop_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('stop')
            for mw_stop, stop_frequency_box in zip(mw_stops, stop_frequency_boxes):
                stop_frequency_box.blockSignals(True)
                stop_frequency_box.setValue(mw_stop)
                stop_frequency_box.blockSignals(False)

        param = param_dict.get('run_time')
        if param is not None:
            self._mw.runtime_DoubleSpinBox.blockSignals(True)
            self._mw.runtime_DoubleSpinBox.setValue(param)
            self._mw.runtime_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('number_of_lines')
        if param is not None:
            self._sd.matrix_lines_SpinBox.blockSignals(True)
            self._sd.matrix_lines_SpinBox.setValue(param)
            self._sd.matrix_lines_SpinBox.blockSignals(False)

        param = param_dict.get('clock_frequency')
        if param is not None:
            self._sd.clock_frequency_DoubleSpinBox.blockSignals(True)
            self._sd.clock_frequency_DoubleSpinBox.setValue(param)
            self._sd.clock_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('oversampling')
        if param is not None:
            self._sd.oversampling_SpinBox.blockSignals(True)
            self._sd.oversampling_SpinBox.setValue(param)
            self._sd.oversampling_SpinBox.blockSignals(False)

        param = param_dict.get('lock_in')
        if param is not None:
            self._sd.lock_in_CheckBox.blockSignals(True)
            self._sd.lock_in_CheckBox.setChecked(param)
            self._sd.lock_in_CheckBox.blockSignals(False)

        param = param_dict.get('cw_mw_frequency')
        if param is not None:
            self._mw.cw_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.cw_frequency_DoubleSpinBox.setValue(param)
            self._mw.cw_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('cw_mw_power')
        if param is not None:
            self._mw.cw_power_DoubleSpinBox.blockSignals(True)
            self._mw.cw_power_DoubleSpinBox.setValue(param)
            self._mw.cw_power_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('average_length')
        if param is not None:
            self._mw.average_level_SpinBox.blockSignals(True)
            self._mw.average_level_SpinBox.setValue(param)
            self._mw.average_level_SpinBox.blockSignals(False)
        return

    ############################################################################
    #                        Widget callback methods (Qt slots)                #
    ############################################################################

    def _range_count_changed(self, count):
        # ToDo: Implement
        print(f'range count changed to {count}')

    def _data_selection_changed(self, channel, range_index):
        print(f'data selection changed: channel "{channel}", range index {range_index}')

    def change_cw_params(self):
        """ Change CW frequency and power of microwave source """
        frequency = self._mw.cw_frequency_DoubleSpinBox.value()
        power = self._mw.cw_power_DoubleSpinBox.value()
        self.sigMwCwParamsChanged.emit(frequency, power)
        return

    def change_sweep_params(self):
        """ Change start, stop and step frequency of frequency sweep """
        starts = []
        steps = []
        stops = []

        num = self._odmr_logic.ranges

        for counter in range(num):
            # construct strings
            start, stop, step = self.get_frequencies_from_row(counter)

            starts.append(start)
            steps.append(step)
            stops.append(stop)

        power = self._mw.sweep_power_DoubleSpinBox.value()
        self.sigMwSweepParamsChanged.emit(starts, stops, steps, power)
        return

    def change_fit_range(self):
        self._odmr_logic.fit_range = self._mw.fit_range_SpinBox.value()
        return

    def change_runtime(self):
        """ Change time after which microwave sweep is stopped """
        runtime = self._mw.runtime_DoubleSpinBox.value()
        self.sigRuntimeChanged.emit(runtime)
        return

    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_nametag_lineedit.text()
        print(f'save measurement with tag "{filetag}"')
        # cb_range = self.get_matrix_cb_range()
        #
        # # Percentile range is None, unless the percentile scaling is selected in GUI.
        # pcile_range = None
        # if self._mw.odmr_cb_centiles_RadioButton.isChecked():
        #     low_centile = self._mw.odmr_cb_low_percentile_DoubleSpinBox.value()
        #     high_centile = self._mw.odmr_cb_high_percentile_DoubleSpinBox.value()
        #     pcile_range = [low_centile, high_centile]
        #
        # self.sigSaveMeasurement.emit(filetag, cb_range, pcile_range)
