# -*- coding: utf-8 -*-
"""
This module operates a confocal microsope.

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

from qtpy import QtCore
from collections import OrderedDict
from itertools import combinations
import time
import datetime
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import copy

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.connector import Connector
from interface.temporary_scanning_interface import ScanSettings


class ScanData:
    """

    """
    def __init__(self, scan_axes, channel_config, scanner_settings):
        self.timestamp = datetime.datetime.now()
        self._scan_axes = tuple(scan_axes)
        if self._scan_axes not in scanner_settings['scan_axes']:
            raise ValueError('scan_axes must be tuple of axes name strings contained in '
                             'scanner_settings')
        self._target_ranges = tuple(scanner_settings['scan_range'][ax] for ax in self._scan_axes)
        self._resolution = tuple(scanner_settings['scan_resolution'][ax] for ax in self._scan_axes)
        self._channel_names = tuple(channel_config)
        self._channel_units = {ch: ch_dict['unit'] for ch, ch_dict in channel_config.items()}
        self.__available_axes = tuple(scanner_settings['scan_resolution'])
        self._position_data = {ax: np.zeros((*self._resolution,)) for ax in self.__available_axes}
        self._data = {ch: np.zeros((*self._resolution,)) for ch in self._channel_names}
        # TODO: Automatic interpolation onto regular grid needs to be implemented
        return

    @property
    def scan_axes(self):
        return self._scan_axes

    @property
    def target_ranges(self):
        return self._target_ranges

    @property
    def resolution(self):
        return self._resolution

    @property
    def channel_names(self):
        return self._channel_names

    @property
    def channel_units(self):
        return self._channel_units

    @property
    def data(self):
        return self._data

    @property
    def position_data(self):
        return self._position_data

    def new_data(self):
        self._position_data = {ax: np.zeros((*self.resolution,)) for ax in self.__available_axes}
        self._data = {ch: np.zeros((*self.resolution,)) for ch in self.channel_names}
        self.timestamp = datetime.datetime.now()
        return

    def add_line_data(self, position, data, y_index=None, x_index=None):
        """

        @param dict data:
        @param int y_index:
        @param int x_index:
        """
        if x_index is None and y_index is None:
            raise ValueError('Must pass either x_index or y_index to add line data.')

        if set(position) != set(self.__available_axes):
            raise ValueError('position dict must contain all available axes {0}.'
                             ''.format(self.__available_axes))
        if set(data) != set(self.channel_names):
            raise ValueError('data dict must contain all available data channels {0}.'
                             ''.format(self.channel_names))
        for arr in position.values():
            if y_index is None and arr.size != self.resolution[1]:
                raise ValueError('Size of line position data array must be {0} but is {1}'
                                 ''.format(self.resolution[1], arr.size))
            if x_index is None and arr.size != self.resolution[0]:
                raise ValueError('Size of line position data array must be {0} but is {1}'
                                 ''.format(self.resolution[0], arr.size))
        for arr in data.values():
            if y_index is None and arr.size != self.resolution[1]:
                raise ValueError('Size of line data array must be {0} but is {1}'
                                 ''.format(self.resolution[1], arr.size))
            if x_index is None and arr.size != self.resolution[0]:
                raise ValueError('Size of line data array must be {0} but is {1}'
                                 ''.format(self.resolution[0], arr.size))

        for channel, arr in data.items():
            if y_index is None:
                self._data[channel][int(x_index), :] = arr
            elif x_index is None:
                self._data[channel][:, int(y_index)] = arr

        for axis, arr in position.items():
            if y_index is None:
                self._position_data[axis][int(x_index), :] = arr
            elif x_index is None:
                self._position_data[axis][:, int(y_index)] = arr
        return

    def add_data_point(self, position, data, index):
        if set(position) != set(self.__available_axes):
            raise ValueError('position dict must contain all available axes {0}.'
                             ''.format(self.__available_axes))

        for channel, value in data.items():
            self._data[channel][index] = value

        for axis, value in position.items():
            self._position_data[axis][index] = value
        return


class OptimizerSettings:
    def __init__(self, resolution_2d, resolution_1d, initial_position, scan_frequency):
        self.resolution_2d = int(resolution_2d)
        self.resolution_1d = int(resolution_1d)
        self.initial_pos = dict(initial_position)
        self.scan_frequency = float(scan_frequency)


class ScanningLogic(GenericLogic):
    """
    This is the Logic class for 1D/2D scanning measurements.
    Scanning in this context means moving something along 1 or 2 dimensions and collecting data
    at each position.
    """
    _modclass = 'scanninglogic'
    _modtype = 'logic'

    # declare connectors
    scanner = Connector(interface='TemporaryScanningInterface')
    savelogic = Connector(interface='SaveLogic')

    # optimizer settings status vars
    _optim_xy_scan_range = StatusVar(name='optim_xy_scan_range', default=1e-6)
    _optim_z_scan_range = StatusVar(name='optim_z_scan_range', default=3e-6)
    _optim_xy_resolution = StatusVar(name='optim_xy_resolution', default=20)
    _optim_z_resolution = StatusVar(name='optim_z_resolution', default=20)
    _optim_scan_frequency = StatusVar(name='optim_scan_frequency', default=50)

    # scan settings status vars
    _x_scan_range = StatusVar(name='x_scan_range', default=None)
    _y_scan_range = StatusVar(name='y_scan_range', default=None)
    _z_scan_range = StatusVar(name='z_scan_range', default=None)
    _xy_scan_resolution = StatusVar(name='xy_scan_resolution', default=100)
    _z_scan_resolution = StatusVar(name='z_scan_resolution', default=100)
    _scan_frequency = StatusVar(name='scan_frequency', default=500.0)

    # signals
    sigScanStateChanged = QtCore.Signal(bool, tuple)
    sigScannerPositionChanged = QtCore.Signal(dict, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScannerSettingsChanged = QtCore.Signal(dict)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigScanDataChanged = QtCore.Signal(dict)

    __sigNextLine = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

        constraints = self.scanner().get_constraints()

        # Constraint scan ranges
        if self._x_scan_range is None:
            self._x_scan_range = list(constraints['axes_position_ranges']['x'])
        else:
            self._x_scan_range = [
                max(min(self._x_scan_range), min(constraints['axes_position_ranges']['x'])),
                min(max(self._x_scan_range), max(constraints['axes_position_ranges']['x']))]
        if self._y_scan_range is None:
            self._y_scan_range = list(constraints['axes_position_ranges']['y'])
        else:
            self._y_scan_range = [
                max(min(self._y_scan_range), min(constraints['axes_position_ranges']['y'])),
                min(max(self._y_scan_range), max(constraints['axes_position_ranges']['y']))]
        if self._z_scan_range is None:
            self._z_scan_range = list(constraints['axes_position_ranges']['z'])
        else:
            self._z_scan_range = [
                max(min(self._z_scan_range), min(constraints['axes_position_ranges']['z'])),
                min(max(self._z_scan_range), max(constraints['axes_position_ranges']['z']))]

        # Constraint scan resolution
        xy_min_res = int(max(min(constraints['axes_resolution_ranges']['x']),
                             min(constraints['axes_resolution_ranges']['y'])))
        xy_max_res = int(min(max(constraints['axes_resolution_ranges']['x']),
                             max(constraints['axes_resolution_ranges']['y'])))
        self._xy_scan_resolution = int(self._xy_scan_resolutio)
        if self._xy_scan_resolution < xy_min_res:
            self._xy_scan_resolution = xy_min_res
        elif self._xy_scan_resolution > xy_max_res:
            self._xy_scan_resolution = xy_max_res
        z_min_res = int(min(constraints['axes_resolution_ranges']['z']))
        z_max_res = int(max(constraints['axes_resolution_ranges']['z']))
        self._z_scan_resolution = int(self._z_scan_resolution)
        if self._z_scan_resolution < z_min_res:
            self._z_scan_resolution = z_min_res
        elif self._z_scan_resolution > z_max_res:
            self._z_scan_resolution = z_max_res

        # Constraint scan frequency
        min_freq = float(max(min(constraints['axes_frequency_ranges']['x']),
                             min(constraints['axes_frequency_ranges']['y'])))
        max_freq = float(min(max(constraints['axes_frequency_ranges']['x']),
                             max(constraints['axes_frequency_ranges']['y'])))
        self._scan_frequency = float(self._scan_frequency)
        if self._scan_frequency < min_freq:
            self._scan_frequency = min_freq
        elif self._scan_frequency < max_freq:
            self._scan_frequency = max_freq

        # Scan history
        self._history = list()
        self._history_index = 0
        self.max_history_length = 10

        # Scan data buffer
        self._current_dummy_data = None
        self._scan_data = dict()
        for axes in self._scanner_settings['scan_axes']:
            self._scan_data[tuple(axes)] = ScanData(
                scan_axes=axes,
                channel_config=self.scanner_constraints['data_channels'],
                scanner_settings=self.scanner_settings)
            self._scan_data[tuple(axes)].new_data()

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
        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(500)
        self.__timer.setSingleShot(False)
        self.__timer.timeout.connect(self.notify_scanner_position_change)
        self.__timer.start()

        self.__scan_line_count = 0
        self.__running_scan = None
        self.__scan_start_time = time.time()
        self.__scan_line_interval = None
        self.__scan_stop_requested = True
        self.__sigNextLine.connect(self._scan_loop, QtCore.Qt.QueuedConnection)
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
        return self._scan_data.copy()

    @property
    def scanner_position(self):
        pos = dict()
        for axis, value in self._target.items():
            axis_range = abs(
                self._constraints['axes'][axis]['max_value'] - self._constraints['axes'][axis][
                    'min_value'])
            pos[axis] = value + (np.random.rand() - 0.5) * axis_range * 0.01
        return pos

    @property
    def scanner_target(self):
        return self._target.copy()

    @property
    def scanner_axes_names(self):
        return tuple(self.scanner_constraints['axes'])

    @property
    def scanner_constraints(self):
        return self._constraints.copy()

    @property
    def scanner_settings(self):
        return self._scanner_settings.copy()

    @property
    def optimizer_settings(self):
        return self._optimizer_settings.copy()

    @QtCore.Slot(dict)
    def set_scanner_settings(self, settings):
        if self.module_state() == 'locked':
            self.log.warning('Scan is running. Unable to change scanner settings.')
            return

        if 'scan_axes' in settings:
            for axes in settings['scan_axes']:
                if not (0 < len(axes) < 3):
                    self.log.error('Scan_axes must contain only tuples of len 1 or 2.')
                    return
                for axis in axes:
                    if axis not in self._constraints['axes']:
                        self.log.error('Axis "{0}" is no valid axis for scanner.'.format(axis))
                        return
            self._scanner_settings['scan_axes'] = tuple(settings['scan_axes'])
        if 'pixel_clock_frequency' in settings:
            if settings['pixel_clock_frequency'] < 1:
                self.log.error('Pixel clock frequency must be integer number >= 1.')
                return
            self._scanner_settings['pixel_clock_frequency'] = int(settings['pixel_clock_frequency'])
        if 'backscan_points' in settings:
            if settings['backscan_points'] < 1:
                self.log.error('Backscan points must be integer number >= 1.')
                return
            self._scanner_settings['backscan_points'] = int(settings['backscan_points'])
        if 'scan_resolution' in settings:
            for axis, res in settings['scan_resolution'].items():
                if axis not in self._constraints['axes']:
                    self.log.error('Axis "{0}" is no valid axis for scanner.'.format(axis))
                    return
                if res < self._constraints['axes'][axis]['min_resolution']:
                    self.log.error('Resolution to set not within allowed boundaries.')
                    return
                elif res > self._constraints['axes'][axis]['max_resolution']:
                    self.log.error('Resolution to set not within allowed boundaries.')
                    return
            self._scanner_settings['scan_resolution'].update(settings['scan_resolution'])
        if 'scan_range' in settings:
            for axis, range in settings['scan_range'].items():
                if axis not in self._constraints['axes']:
                    self.log.error('Axis "{0}" is no valid axis for scanner.'.format(axis))
                    return
                if min(range) < self._constraints['axes'][axis]['min_value']:
                    self.log.error('Scan range to set not within allowed boundaries.')
                    return
                elif max(range) > self._constraints['axes'][axis]['max_value']:
                    self.log.error('Resolution to set not within allowed boundaries.')
                    return
            self._scanner_settings['scan_range'].update(settings['scan_range'])
        self.sigScannerSettingsChanged.emit(self.scanner_settings)
        return

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
        with self.threadlock:
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

        with self.threadlock:
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
