# -*- coding: utf-8 -*-
"""
This module is responsible for controlling any kind of scanning probe imaging for 1D and 2D
scanning.

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


import time
import copy
import datetime
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from qtpy import QtCore

from qudi.core.module import LogicBase
from qudi.core.util.mutex import Mutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar


class ScanningProbeLogic(LogicBase):
    """
    This is the Logic class for 1D/2D SPM measurements.
    Scanning in this context means moving something along 1 or 2 dimensions and collecting data from
    possibly multiple sources at each position.
    """

    # declare connectors
    scanner = Connector(interface='ScannerInterface')
    # savelogic = Connector(interface='SaveLogic')

    # status vars
    _scan_ranges = StatusVar(name='scan_ranges', default=None)
    _scan_resolution = StatusVar(name='scan_resolution', default=None)
    _scan_settings = StatusVar(name='scan_settings', default=None)
    _scan_history = StatusVar(name='scan_history', default=list())

    # config options
    _max_history_length = ConfigOption(name='max_history_length', default=10)

    # signals
    sigScanStateChanged = QtCore.Signal(bool, tuple)
    sigScannerPositionChanged = QtCore.Signal(dict, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanRangesChanged = QtCore.Signal(dict)
    sigScanResolutionChanged = QtCore.Signal(dict)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigScanDataChanged = QtCore.Signal(dict)

    __sigNextLine = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = Mutex()

        # Optimizer settings
        self._optimizer_settings = dict()
        self._optimizer_settings['settle_time'] = 0.1
        self._optimizer_settings['pixel_clock'] = 50
        self._optimizer_settings['backscan_pts'] = 20
        self._optimizer_settings['sequence'] = ('xy', 'z')
        self._optimizer_settings['axes'] = dict()
        self._optimizer_settings['axes']['x'] = {'resolution': 15, 'range': 1e-6}
        self._optimizer_settings['axes']['y'] = {'resolution': 15, 'range': 1e-6}
        self._optimizer_settings['axes']['z'] = {'resolution': 15, 'range': 1e-6}
        self._optimizer_settings['axes']['phi'] = {'resolution': 15, 'range': 1e-6}

        # Scan history
        self._curr_history_index = 0

        # others
        self.__timer = None
        self.__scan_line_count = 0
        self.__running_scan = None
        self.__scan_start_time = 0
        self.__scan_line_interval = None
        self.__scan_line_positions = dict()
        self.__scan_stop_requested = True
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        constr = self.scanner_constraints

        # scanner settings
        if not isinstance(self._scan_ranges, dict):
            self._scan_ranges = {ax.name: ax.value_bounds for ax in constr.axes.values()}
        if not isinstance(self._scan_resolution, dict):
            self._scan_resolution = {ax.name: max(ax.min_resolution, min(128, ax.max_resolution))
                                     for ax in constr.axes.values()}
        if not isinstance(self._scan_settings, dict):
            self._scan_settings = {
                'frequency': min(ax.max_frequency for ax in constr.axes.values())}

        self.__scan_line_count = 0
        self.__running_scan = None
        self.__scan_start_time = time.time()
        self.__scan_line_interval = None
        self.__scan_stop_requested = True
        self.__sigNextLine.connect(self._scan_loop, QtCore.Qt.QueuedConnection)

        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(500)
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self.update_scanner_position)
        self.__timer.start()
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__timer.stop()
        self.__timer.timeout.disconnect()
        self.__sigNextLine.disconnect()
        return

    @property
    def scan_data(self):
        return self.scanner().get_scan_data()

    @property
    def scanner_position(self):
        with self._thread_lock:
            return self.scanner().get_position()

    @property
    def scanner_target(self):
        with self._thread_lock:
            return self.scanner().get_target()

    @property
    def scanner_axes_names(self):
        return tuple(self.scanner_constraints['axes'])

    @property
    def scanner_constraints(self):
        return self.scanner().get_constrainst()

    @property
    def scan_ranges(self):
        with self._thread_lock:
            return self._scan_ranges.copy()

    @property
    def scan_resolution(self):
        with self._thread_lock:
            return self._scan_resolution.copy()

    @property
    def scan_settings(self):
        with self._thread_lock:
            return self._scan_settings.copy()

    @property
    def optimizer_settings(self):
        with self._thread_lock:
            return self._optimizer_settings.copy()

    @QtCore.Slot(dict)
    def set_scan_range(self, ranges):
        with self._thread_lock:
            if self.module_state() == 'locked':
                self.log.warning('Scan is running. Unable to change scan ranges.')
                new_ranges = self.scan_ranges
                self.sigScanRangesChanged.emit(new_ranges)
                return new_ranges

            ax_constr = self.scanner_constraints.axes
            for ax, ax_range in ranges.items():
                if ax not in self._scan_ranges:
                    self.log.error('Unknown axis "{0}" encountered.'.format(ax))
                    new_ranges = self.scan_ranges
                    self.sigScanRangesChanged.emit(new_ranges)
                    return new_ranges

                new_range = (
                    min(ax_constr[ax].max_value, max(ax_constr[ax].min_value, ax_range[0])),
                    min(ax_constr[ax].max_value, max(ax_constr[ax].min_value, ax_range[1]))
                )
                if new_range[0] > new_range[1]:
                    new_range = (new_range[0], new_range[0])
                self._scan_ranges[ax] = new_range

            new_ranges = {ax: r for ax, r in self._scan_ranges if ax in ranges}
            self.sigScanRangesChanged.emit(new_ranges)
            return new_ranges

    @QtCore.Slot(dict)
    def set_scan_resolution(self, resolution):
        with self._thread_lock:
            if self.module_state() == 'locked':
                self.log.warning('Scan is running. Unable to change scan resolution.')
                new_res = self.scan_resolution
                self.sigScanResolutionChanged.emit(new_res)
                return new_res

            ax_constr = self.scanner_constraints.axes
            for ax, ax_res in resolution.items():
                if ax not in self._scan_resolution:
                    self.log.error('Unknown axis "{0}" encountered.'.format(ax))
                    new_res = self.scan_resolution
                    self.sigScanResolutionChanged.emit(new_res)
                    return new_res

                new_res = (
                    min(ax_constr[ax].max_resolution, max(ax_constr[ax].min_resolution, ax_res[0])),
                    min(ax_constr[ax].max_resolution, max(ax_constr[ax].min_resolution, ax_res[1]))
                )
                if new_res[0] > new_res[1]:
                    new_res = (new_res[0], new_res[0])
                self._scan_ranges[ax] = new_range

            new_ranges = {ax: r for ax, r in self._scan_ranges if ax in ranges}
            self.sigScanResolutionChanged.emit(new_ranges)
            return new_ranges

    @QtCore.Slot(dict)
    def set_optimizer_settings(self, settings):
        if 'axes' in settings:
            for axis, axis_dict in settings['axes'].items():
                self._optimizer_settings['axes'][axis].update(axis_dict)
        if 'settle_time' in settings:
            if settings['settle_time'] < 0:
                self.log.error('Optimizer settle time must be positive number.')
            else:
                self._optimizer_settings['settle_time'] = float(settings['settle_time'])
        if 'pixel_clock' in settings:
            if settings['pixel_clock'] < 1:
                self.log.error('Optimizer pixel clock must be integer number >= 1.')
            else:
                self._optimizer_settings['pixel_clock'] = int(settings['pixel_clock'])
        if 'backscan_pts' in settings:
            if settings['backscan_pts'] < 1:
                self.log.error('Optimizer backscan points must be integer number >= 1.')
            else:
                self._optimizer_settings['backscan_pts'] = int(settings['backscan_pts'])
        if 'sequence' in settings:
            self._optimizer_settings['sequence'] = tuple(settings['sequence'])

        self.sigOptimizerSettingsChanged.emit(self.optimizer_settings)
        return

    @QtCore.Slot(dict)
    @QtCore.Slot(dict, object)
    def set_scanner_target_position(self, pos_dict, caller_id=None):
        constr = self.scanner_constraints
        for ax, pos in pos_dict.items():
            if ax not in constr['axes']:
                self.log.error('Unknown scanner axis: "{0}"'.format(ax))
                return

        self._target.update(pos_dict)
        self.sigScannerTargetChanged.emit(pos_dict, id(self) if caller_id is None else caller_id)
        time.sleep(0.01)
        self.notify_scanner_position_change()
        return

    @QtCore.Slot()
    def notify_scanner_position_change(self):
        self.sigScannerPositionChanged.emit(self.scanner_position, id(self))

    @QtCore.Slot(tuple, bool)
    def toggle_scan(self, scan_axes, start):
        with self._thread_lock:
            if start and self.module_state() != 'idle':
                self.log.error('Unable to start scan. Scan already in progress.')
                return
            elif not start and self.module_state() == 'idle':
                self.log.error('Unable to stop scan. No scan running.')
                return

            if start:
                self.module_state.lock()
                self.__timer.stop()
                self.__running_scan = scan_axes
                self.sigScanStateChanged.emit(True, self.__running_scan)
                if len(scan_axes) > 1:
                    self._current_dummy_data = self._generate_2d_dummy_data(scan_axes)
                else:
                    self._current_dummy_data = self.generate_1d_dummy_data(scan_axes[0])
                self.__scan_line_count = 0
                self.__scan_start_time = time.time()
                self._scan_data[self.__running_scan] = ScanData(
                    scan_axes=self.__running_scan,
                    channel_config=self.scanner_constraints['data_channels'],
                    scanner_settings=self.scanner_settings)
                self._scan_data[self.__running_scan].new_data()
                num_x_vals = self.scanner_settings['scan_resolution'][scan_axes[0]]
                if len(scan_axes) > 1:
                    self.__scan_line_interval = num_x_vals / self.scanner_settings[
                        'pixel_clock_frequency']
                    self.__scan_line_positions = {ax: np.full(num_x_vals, self.scanner_target[ax])
                                                  for
                                                  ax in self._constraints['axes']}
                    min_val, max_val = self.scanner_settings['scan_range'][self.__running_scan[0]]
                    self.__scan_line_positions[self.__running_scan[0]] = np.linspace(min_val,
                                                                                     max_val,
                                                                                     num_x_vals)
                else:
                    self.__scan_line_interval = 10 / self.scanner_settings['pixel_clock_frequency']
                    self.__scan_line_positions = self.scanner_target.copy()

                self.__scan_stop_requested = False
                self.__sigNextLine.emit()
            else:
                self.__scan_stop_requested = True
        return

    @QtCore.Slot()
    def _scan_loop(self):
        if self.module_state() != 'locked':
            return

        with self._thread_lock:
            if len(self.__running_scan) > 1:
                max_number_of_lines = self.scanner_settings['scan_resolution'][self.__running_scan[1]]
            else:
                max_number_of_lines = self.scanner_settings['scan_resolution'][self.__running_scan[0]]
            if self.__scan_line_count >= max_number_of_lines or self.__scan_stop_requested:
                while len(self._history) >= self.max_history_length:
                    self._history.pop(0)
                self._history.append(copy.deepcopy(self.scan_data[self.__running_scan]))
                self._history_index = len(self._history) - 1
                self.module_state.unlock()
                self.sigScanStateChanged.emit(False, self.__running_scan)
                self.__timer.start()
                return

            if len(self.__running_scan) > 1:
                y_min, y_max = self.scanner_settings['scan_range'][self.__running_scan[1]]
                self.__scan_line_positions[self.__running_scan[1]] = np.full(
                    self.scanner_settings['scan_resolution'][self.__running_scan[0]],
                    y_min + (y_max - y_min) / (max_number_of_lines - 1))
            else:
                x_min, x_max = self.scanner_settings['scan_range'][self.__running_scan[0]]
                self.__scan_line_positions[self.__running_scan[0]] = x_min + (x_max - x_min) / (
                            max_number_of_lines - 1)

            self.__scan_line_count += 1
            next_line_time = self.__scan_start_time + self.__scan_line_count * self.__scan_line_interval
            while time.time() < next_line_time:
                time.sleep(0.1)

            channels = self._scan_data[self.__running_scan].channel_names
            if len(self.__running_scan) > 1:
                scan_line = self._current_dummy_data[:, self.__scan_line_count - 1]
                self._scan_data[self.__running_scan].add_line_data(
                    position=self.__scan_line_positions,
                    data={chnl: scan_line * (i+1) for i, chnl in enumerate(channels)},
                    y_index=self.__scan_line_count-1)
            else:
                scan_point = self._current_dummy_data[self.__scan_line_count - 1]
                self._scan_data[self.__running_scan].add_data_point(
                    position=self.__scan_line_positions,
                    data={chnl: scan_point * (i+1) for i, chnl in enumerate(channels)},
                    index=self.__scan_line_count-1)

            self.sigScanDataChanged.emit({self.__running_scan: self.scan_data[self.__running_scan]})
            self.__sigNextLine.emit()
        return

    def _generate_2d_dummy_data(self, axes):
        x_res = self._scanner_settings['scan_resolution'][axes[0]]
        y_res = self._scanner_settings['scan_resolution'][axes[1]]
        x_start = self._scanner_settings['scan_range'][axes[0]][0]
        y_start = self._scanner_settings['scan_range'][axes[1]][0]
        z_start = -5e-6
        x_end = self._scanner_settings['scan_range'][axes[0]][1]
        y_end = self._scanner_settings['scan_range'][axes[1]][1]
        z_end = 5e-6
        x_range = x_end - x_start
        y_range = y_end - y_start
        z_range = z_end - z_start

        area_density = 1 / (5e-6 * 5e-6)

        params = np.random.rand(round(area_density * x_range * y_range), 7)
        params[:, 0] = params[:, 0] * x_range + x_start     # X displacement
        params[:, 1] = params[:, 1] * y_range + y_start     # Y displacement
        params[:, 2] = params[:, 2] * z_range + z_start     # Z displacement
        params[:, 3] = params[:, 3] * 50e-9 + 150e-9        # X sigma
        params[:, 4] = params[:, 4] * 50e-9 + 150e-9        # Y sigma
        params[:, 5] = params[:, 5] * 100e-9 + 450e-9       # Z sigma
        params[:, 6] = params[:, 6] * 2 * np.pi             # theta

        amplitude = 200000
        offset = 20000

        def gauss_ensemble(x, y):
            result = np.zeros(x.shape)
            for x0, y0, z0, sigmax, sigmay, sigmaz, theta in params:
                a = np.cos(theta) ** 2 / (2 * sigmax ** 2) + np.sin(theta) ** 2 / (2 * sigmay ** 2)
                b = np.sin(2 * theta) / (4 * sigmay ** 2) - np.sin(2 * theta) / (4 * sigmax ** 2)
                c = np.sin(theta) ** 2 / (2 * sigmax ** 2) + np.cos(theta) ** 2 / (2 * sigmay ** 2)
                zfactor = np.exp(-(z0 ** 2) / (2 * sigmaz**2))
                result += zfactor * np.exp(
                    -(a * (x - x0) ** 2 + 2 * b * (x - x0) * (y - y0) + c * (y - y0) ** 2))
            result *= amplitude - offset
            result += offset
            return result

        xx, yy = np.meshgrid(np.linspace(x_start, x_end, x_res),
                             np.linspace(y_start, y_end, y_res),
                             indexing='ij')
        return np.random.rand(xx.shape[0], xx.shape[1]) * amplitude * 0.10 + gauss_ensemble(xx, yy)

    def generate_1d_dummy_data(self, axis):
        res = self._scanner_settings['scan_resolution'][axis]
        start, stop = self._scanner_settings['scan_range'][axis]
        range = stop - start

        density = 1 / 10e-6

        params = np.random.rand(round(density * range), 2)
        params[:, 0] = params[:, 0] * range + start  # displacement
        params[:, 1] = params[:, 1] * 50e-9 + 150e-9  # sigma

        amplitude = 200000
        offset = 20000

        def gauss(x):
            result = np.zeros(x.size)
            for mu, sigma in params:
                result += np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))
            result *= amplitude - offset
            result += offset
            return result

        pos_arr = np.linspace(start, stop, res)
        return np.random.rand(pos_arr.size) * amplitude * 0.10 + gauss(pos_arr)

    @QtCore.Slot()
    def history_backwards(self):
        if self._history_index < 1:
            self.log.warning('Unable to restore previous state from scan history. '
                             'Already at first history entry.')
            return
        self.restore_from_history(self._history_index - 1)
        return

    @QtCore.Slot()
    def history_forward(self):
        if self._history_index >= len(self._history) - 1:
            self.log.warning('Unable to restore next state from scan history. '
                             'Already at last history entry.')
            return
        self.restore_from_history(self._history_index + 1)
        return

    def restore_from_history(self, index):
        if self.module_state() == 'locked':
            self.log.warning('Scan is running. Unable to restore history state.')
            return
        if not isinstance(index, int):
            self.log.error('History index to restore must be int type.')
            return

        try:
            data = self._history[index]
        except IndexError:
            self.log.error('History index "{0}" out of range.'.format(index))
            return

        axes = data.scan_axes
        resolution = data.resolution
        ranges = data.target_ranges
        for i, axis in enumerate(axes):
            self._scanner_settings['scan_resolution'][axis] = resolution[i]
            self._scanner_settings['scan_range'][axis] = ranges[i]
        self._history_index = index
        self.sigScannerSettingsChanged.emit(self.scanner_settings)
        self.sigScanDataChanged.emit({axes: data})
        return

    @QtCore.Slot()
    def set_full_scan_ranges(self):
        scan_ranges = {ax: (ax_dict['min_value'], ax_dict['max_value']) for ax, ax_dict in
                       self.scanner_constraints['axes'].items()}
        self.set_scanner_settings({'scan_range': scan_ranges})
        return
