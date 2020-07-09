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


class ScanData:
    """
    Object representing all data associated to a SPM measurement.
    """
    def __init__(self, axes, axes_units, scan_axes, scan_range, scan_resolution, channels, channel_units, timestamp=None):
        """

        @param str[] axes: name of all available axes
        @param str[] axes_units: physical units for all axes. No unit prefix allowed.
        @param str[] scan_axes: name of the axes involved in the scan
        @param float[][2] scan_range: inclusive range for each scan axis
        @param int[] scan_resolution: planned number of points for each scan axis
        @param str[] channels: the names for each data channel
        @param str[] channel_units: physical unit for each data channel
        @param datetime.datetime timestamp: optional, timestamp used for creation time
        """
        # Sanity checking
        if len(axes) != len(axes_units):
            raise ValueError('Parameters "axes" and "axes_units" must have same len. Given {0:d} '
                             'and {1:d}, respectively.'.format(len(axes), len(axes_units)))
        if len(scan_axes) != len(scan_range):
            raise ValueError('Parameters "scan_axes" and "scan_range" must have same len. Given '
                             '{0:d} and {1:d}, respectively.'.format(len(scan_axes),
                                                                     len(scan_range)))
        if len(scan_axes) != len(scan_resolution):
            raise ValueError('Parameters "scan_axes" and "scan_resolution" must have same len. '
                             'Given {0:d} and {1:d}, respectively.'.format(len(scan_axes),
                                                                           len(scan_resolution)))
        if len(channels) != len(channel_units):
            raise ValueError('Parameters "channels" and "channel_units" must have same len. Given '
                             '{0:d} and {1:d}, respectively.'.format(len(channels),
                                                                     len(channel_units)))
        if not all(isinstance(ax, str) for ax in axes):
            raise TypeError('Parameter "axes" must be iterable containing only str type items')
        if not all(isinstance(ax, str) for ax in scan_axes):
            raise TypeError('Parameter "scan_axes" must be iterable containing only str type items')
        if not all(ax in axes for ax in scan_axes):
            raise ValueError('Parameter "scan_axes" ({0}) must contain a subset of "axes" ({1}).'
                             ''.format(scan_axes, axes))
        if not all(len(ax_range) == 2 for ax_range in scan_range):
            raise TypeError(
                'Parameter "scan_range" must be iterable containing only value pairs (len=2).')
        if not all(isinstance(res, (int, np.integer)) for res in scan_resolution):
            raise TypeError(
                'Parameter "scan_resolution" must be iterable containing only integers.')
        if not all(isinstance(unit, str) for unit in axes_units):
            raise TypeError(
                'Parameter "axes_units" must be iterable containing only str type items')
        if not all(isinstance(ch, str) for ch in channels):
            raise TypeError('Parameter "channels" must be iterable containing only str type items')
        if not all(isinstance(unit, str) for unit in channel_units):
            raise TypeError(
                'Parameter "channel_units" must be iterable containing only str type items')

        self._axes = tuple(str(ax) for ax in axes)
        self._scan_axes = tuple(str(ax) for ax in scan_axes)
        self._axes_units = {self._axes[i]: str(unit) for i, unit in enumerate(axes_units)}
        self._ranges = {self._scan_axes[i]: (float(start), float(stop)) for i, (start, stop) in
                        enumerate(scan_range)}
        self._resolutions = {self._scan_axes[i]: int(res) for i, res in enumerate(scan_resolution)}
        self._channels = tuple(str(ch) for ch in channels)
        self._channel_units = {self._channels[i]: str(unit) for i, unit in enumerate(channel_units)}

        self.timestamp = None
        self._data = None
        self._position_data = None
        self.__data_size = None
        self.__current_data_index = None
        self.new_data(timestamp=timestamp)
        # TODO: Automatic interpolation onto rectangular grid needs to be implemented
        return

    @property
    def scan_axes(self):
        return self._scan_axes

    @property
    def axes(self):
        return self._axes

    @property
    def scan_ranges(self):
        return self._ranges.copy()

    @property
    def scan_resolutions(self):
        return self._resolutions.copy()

    @property
    def scan_size(self):
        return self.__data_size

    @property
    def data_channels(self):
        return self._channels

    @property
    def data_channel_units(self):
        return self._channel_units.copy()

    @property
    def data(self):
        return self._data

    @property
    def position_data(self):
        return self._position_data

    def new_data(self, timestamp=None):
        """

        @param timestamp:
        """
        self.__data_size = np.prod(tuple(self._resolutions.values()))
        self.__current_data_index = 0
        self._position_data = {ax: np.zeros(self.__data_size) for ax in self._axes}
        self._data = {ch: np.zeros(self.__data_size) for ch in self._channels}
        if timestamp is None:
            self.timestamp = datetime.datetime.now()
        elif isinstance(timestamp, datetime.datetime):
            self.timestamp = timestamp
        else:
            raise TypeError('Parameter "timestamp" must be datetime.datetime object.')
        return

    def add_data_array(self, position, data):
        start_index = self.__current_data_index
        stop_index = self.__current_data_index + len(position[list(position)[0]])
        return self._add_data(position, data, start_index, stop_index)

    def add_data_point(self, position, data):
        start_index = self.__current_data_index
        stop_index = self.__current_data_index + 1
        return self._add_data(position, data, start_index, stop_index)

    def _add_data(self, position, data, start_index, stop_index):
        if set(position) != set(self._axes):
            raise KeyError('position dict must contain all available axes {0}.'.format(self._axes))
        if set(data) != set(self._channels):
            raise KeyError(
                'data dict must contain all available channels {0}.'.format(self._channels))

        # Extend pre-allocated data arrays if the amount of data exceeds the planned size to avoid
        # data loss.
        if stop_index > self.__data_size:
            append_size = stop_index - self.__data_size
            print('Ooops... Planned scan size of {0:d} points exceeded by {1:d} points.'
                  ''.format(self.__data_size, append_size))
            for channel in self._channels:
                self._data[channel] = np.append(self._data[channel], np.zeros(append_size))
            for axis in self._axes:
                self._position_data[axis] = np.append(self._position_data[axis],
                                                      np.zeros(append_size))
            self.__data_size += append_size

        # Add channel data
        for channel, data_arr in data.items():
            self._data[channel][start_index:stop_index] = data_arr
        # Add positional data
        for axis, pos_arr in position.items():
            self._position_data[axis][start_index:stop_index] = pos_arr

        self.__current_data_index = stop_index
        return


class ScanningProbeLogic(LogicBase):
    """
    This is the Logic class for 1D/2D SPM measurements.
    Scanning in this context means moving something along 1 or 2 dimensions and collecting data from
    possibly multiple sources at each position.
    """

    # declare connectors
    scanner = Connector(interface='ScannerInterface')

    savelogic = Connector(interface='SaveLogic')

    # status vars

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

        # Create semi-random dummy constraints
        self._constraints = dict()
        self._constraints['data_channels'] = dict()
        self._constraints['data_channels']['fluorescence'] = dict()
        self._constraints['data_channels']['fluorescence']['unit'] = 'c/s'
        self._constraints['data_channels']['unfug'] = dict()
        self._constraints['data_channels']['unfug']['unit'] = 'bpm'
        self._constraints['axes'] = dict()
        for axis in ('x', 'y', 'z', 'phi'):
            self._constraints['axes'][axis] = dict()
            limit = 50e-6 + 50e-6 * np.random.rand()
            self._constraints['axes'][axis]['min_value'] = -limit
            self._constraints['axes'][axis]['max_value'] = limit
            self._constraints['axes'][axis]['min_step'] = 1e-9
            self._constraints['axes'][axis]['min_resolution'] = 2
            self._constraints['axes'][axis]['max_resolution'] = np.inf
            self._constraints['axes'][axis]['unit'] = 'm' if axis != 'phi' else '°'

        # scanner settings
        self._scanner_settings = dict()
        self._scanner_settings['scan_axes'] = (*combinations(self.scanner_constraints['axes'],
                                                                 2), ('x',))
        self._scanner_settings['pixel_clock_frequency'] = 1000
        self._scanner_settings['backscan_points'] = 50
        self._scanner_settings['scan_resolution'] = dict()
        self._scanner_settings['scan_range'] = dict()
        for axis, constr_dict in self._constraints['axes'].items():
            self._scanner_settings['scan_resolution'][axis] = np.random.randint(
                max(constr_dict['min_resolution'], 100),
                min(constr_dict['max_resolution'], 400) + 1)
            self._scanner_settings['scan_range'][axis] = (constr_dict['min_value'],
                                                          constr_dict['max_value'])

        # Scanner target position
        self._target = dict()
        for axis, axis_dict in self.scanner_constraints['axes'].items():
            extent = axis_dict['max_value'] - axis_dict['min_value']
            self._target[axis] = axis_dict['min_value'] + extent * np.random.rand()

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
