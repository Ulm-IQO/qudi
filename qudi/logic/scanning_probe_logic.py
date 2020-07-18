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
    _scanner = Connector(name='scanner', interface='ScanningProbeInterface')
    # savelogic = Connector(interface='SaveLogic')

    # status vars
    _scan_ranges = StatusVar(name='scan_ranges', default=None)
    _scan_resolution = StatusVar(name='scan_resolution', default=None)
    _scan_settings = StatusVar(name='scan_settings', default=None)
    _scan_history = StatusVar(name='scan_history', default=list())

    # config options
    _max_history_length = ConfigOption(name='max_history_length', default=10)
    _max_scan_update_interval = ConfigOption(name='max_scan_update_interval', default=5)
    _min_scan_update_interval = ConfigOption(name='min_scan_update_interval', default=0.25)
    _position_update_interval = ConfigOption(name='position_update_interval', default=1)

    # signals
    sigScanStateChanged = QtCore.Signal(bool, tuple)
    sigScannerPositionChanged = QtCore.Signal(dict, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanRangesChanged = QtCore.Signal(dict)
    sigScanResolutionChanged = QtCore.Signal(dict)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigScanDataChanged = QtCore.Signal(object)

    __sigStopTimer = QtCore.Signal()
    __sigStartTimer = QtCore.Signal()

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

        # Scan history
        self._curr_history_index = 0

        # others
        self.__timer = None
        self.__current_scan = None
        self.__scan_update_interval = 0
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

        self.__current_scan = None
        self.__scan_update_interval = 0

        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(int(round(self._position_update_interval * 1000)))
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self._update_scanner_position_loop, QtCore.Qt.QueuedConnection)
        self.__sigStartTimer.connect(self.__timer.start)
        self.__sigStopTimer.connect(self.__timer.stop)
        self.__timer.start()
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__timer.stop()
        self.__timer.timeout.disconnect()
        self.__sigStartTimer.disconnect()
        self.__sigStopTimer.disconnect()
        return

    @property
    def scan_data(self):
        return self._scanner().get_scan_data()

    @property
    def scanner_position(self):
        with self._thread_lock:
            return self._scanner().get_position()

    @property
    def scanner_target(self):
        with self._thread_lock:
            return self._scanner().get_target()

    @property
    def scanner_axes_names(self):
        return tuple(self.scanner_constraints.axes)

    @property
    def scanner_constraints(self):
        return self._scanner().get_constraints()

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
                new_ranges = self._scan_ranges.copy()
                self.sigScanRangesChanged.emit(new_ranges)
                return new_ranges

            ax_constr = self.scanner_constraints.axes
            for ax, ax_range in ranges.items():
                if ax not in self._scan_ranges:
                    self.log.error('Unknown axis "{0}" encountered.'.format(ax))
                    new_ranges = self._scan_ranges.copy()
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
                new_res = self._scan_resolution.copy()
                self.sigScanResolutionChanged.emit(new_res)
                return new_res

            ax_constr = self.scanner_constraints.axes
            for ax, ax_res in resolution.items():
                if ax not in self._scan_resolution:
                    self.log.error('Unknown axis "{0}" encountered.'.format(ax))
                    new_res = self._scan_resolution.copy()
                    self.sigScanResolutionChanged.emit(new_res)
                    return new_res

                new_res = (
                    min(ax_constr[ax].max_resolution, max(ax_constr[ax].min_resolution, ax_res[0])),
                    min(ax_constr[ax].max_resolution, max(ax_constr[ax].min_resolution, ax_res[1]))
                )
                if new_res[0] > new_res[1]:
                    new_res = (new_res[0], new_res[0])
                self._scan_ranges[ax] = new_res

            new_resolution = {ax: r for ax, r in self._scan_ranges if ax in resolution}
            self.sigScanResolutionChanged.emit(new_resolution)
            return new_resolution

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
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.error('Unable to change scanner target position while a scan is running.')
                return self._scanner().get_target()

            ax_constr = self.scanner_constraints.axes
            for ax, pos in pos_dict.items():
                if ax not in ax_constr:
                    self.log.error('Unknown scanner axis: "{0}"'.format(ax))
                    return self._scanner().get_target()
                tmp_val = ax_constr[ax].clip_value(pos)
                if pos != tmp_val:
                    self.log.warning('Scanner position target value out of bounds for axis "{0}". '
                                     'Clipping value.'.format(ax))
                    pos_dict[ax] = tmp_val

            new_pos = self._scanner().move_absolute(pos_dict)
            self.sigScannerTargetChanged.emit(new_pos, id(self) if caller_id is None else caller_id)
            return

    @QtCore.Slot()
    def _update_scanner_position_loop(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.sigScannerPositionChanged.emit(self._scanner().get_position(), id(self))
                self._start_timer()

    @QtCore.Slot()
    def update_scanner_position(self):
        with self._thread_lock:
            self.sigScannerPositionChanged.emit(self._scanner().get_position(), id(self))

    @QtCore.Slot(bool)
    @QtCore.Slot(bool, tuple)
    def toggle_scan(self, start, scan_axes=None):
        with self._thread_lock:
            if start and self.module_state() != 'idle':
                self.sigScanStateChanged.emit(True, self.__current_scan)
                return 0
            elif not start and self.module_state() == 'idle':
                self.sigScanStateChanged.emit(True, self.__current_scan)
                return 0

            if start:
                if scan_axes is None or not (0 < len(scan_axes) < 3):
                    self.log.error('Unable to start scan. Scan axes must be tuple of len 1 or 2.')
                    return -1

                self.module_state.lock()

                self.__current_scan = tuple(scan_axes)
                settings = {'axes': tuple(scan_axes),
                            'range': tuple(self._scan_ranges[ax] for ax in scan_axes),
                            'resolution': tuple(self._scan_resolution[ax] for ax in scan_axes),
                            'frequency': self._scan_settings['frequency']}
                new_settings = self._scanner().configure_scan(settings)
                if new_settings['axes'] != self.__current_scan:
                    self.log.error('Something went wrong while configuring scanner. Axes to scan '
                                   'returned by scanner {0} do not match the intended scan axes '
                                   '{1}.'.format(new_settings['axes'], self.__current_scan))
                    self.module_state.unlock()
                    self.sigScanStateChanged.emit(False, self.__current_scan)
                    return -1
                for ax_index, ax in enumerate(scan_axes):
                    # Update scan ranges if needed
                    old = self._scan_ranges[ax]
                    new = new_settings['range'][ax_index]
                    if old[0] != new[0] or old[1] != new[1]:
                        self._scan_ranges[ax] = tuple(new)
                        self.sigScanRangesChanged.emit({ax: self._scan_ranges[ax]})

                    # Update scan resolution if needed
                    old = self._scan_resolution[ax]
                    new = new_settings['resolution'][ax_index]
                    if old != new:
                        self._scan_resolution[ax] = int(new)
                        self.sigScanResolutionChanged.emit({ax: self._scan_resolution[ax]})

                # Update scan frequency if needed
                old = self._scan_settings['frequency']
                new = new_settings['frequency']
                if old != new:
                    self._scan_settings['frequency'] = float(new)
                    self.sigScanSettingsChanged.emit(
                        {'frequency': self._scan_settings['frequency']})

                line_points = self._scan_resolution[scan_axes[0]] if len(scan_axes) > 1 else 1
                self.__scan_update_interval = max(
                    self._min_scan_update_interval,
                    min(self._max_scan_update_interval,
                        line_points / self._scan_settings['frequency'])
                )

                # Try to start scanner
                if self._scanner().start_scan() < 0:
                    self.log.error('Unable to start scanner.')
                    self.module_state.unlock()
                    self.sigScanStateChanged.emit(False, self.__current_scan)
                    return -1

                self.log.debug('Scanner successfully started')

                self._stop_timer()
                self.log.debug('Timer stopped')
                self.__timer.timeout.disconnect()
                self.__timer.setSingleShot(True)
                self.__timer.setInterval(int(round(self.__scan_update_interval * 1000)))
                self.__timer.timeout.connect(self._scan_loop, QtCore.Qt.QueuedConnection)
                self.log.debug('Timer connected')
                self.sigScanStateChanged.emit(True, self.__current_scan)
                self.log.debug('Starting scan timer')
                self._start_timer()
            else:
                scan_data = self._scanner().get_scan_data()
                while len(self._scan_history) >= self._max_history_length:
                    self._scan_history.pop(0)
                self._scan_history.append(scan_data)
                self._curr_history_index = len(self._scan_history) - 1
                self.sigScanDataChanged.emit(scan_data)
                if self._scanner().stop_scan() < 0:
                    self.log.error(
                        'Unable to stop scan. Waiting for currently running scan to finish.')
                    self.sigScanStateChanged.emit(True, self.__current_scan)
                    return -1
                self._stop_timer()
                self.__timer.timeout.disconnect()
                self.__timer.setSingleShot(True)
                self.__timer.setInterval(int(round(self._position_update_interval * 1000)))
                self.__timer.timeout.connect(
                    self._update_scanner_position_loop, QtCore.Qt.QueuedConnection)
                self.module_state.unlock()
                self.sigScanStateChanged.emit(False, self.__current_scan)
                self._start_timer()
            print('Returning from toggle')
            return 0

    @QtCore.Slot()
    def _scan_loop(self):
        print('SCAN LOOP')
        with self._thread_lock:
            print('Scan loop in lock')
            if self.module_state() != 'locked':
                print('Module not locked.')
                return

            scan_data = self._scanner().get_scan_data()
            print('scan data:', scan_data)
            # Terminate scan if finished
            if scan_data.finished:
                print('scan stopped')
                if self._scanner().stop_scan() < 0:
                    self.log.error('Unable to stop scan.')
                self._stop_timer()
                self.__timer.timeout.disconnect()
                self.__timer.setSingleShot(True)
                self.__timer.setInterval(int(round(self._position_update_interval * 1000)))
                self.__timer.timeout.connect(
                    self._update_scanner_position_loop, QtCore.Qt.QueuedConnection)
                self.module_state.unlock()
                self.sigScanStateChanged.emit(False, self.__current_scan)
                while len(self._scan_history) >= self._max_history_length:
                    self._scan_history.pop(0)
                self._scan_history.append(scan_data)
                self._curr_history_index = len(self._scan_history) - 1
                self._start_timer()

            self.sigScanDataChanged.emit(scan_data)
            self._start_timer()
            return

    @QtCore.Slot()
    def history_backwards(self):
        with self._thread_lock:
            if self._curr_history_index < 1:
                self.log.warning('Unable to restore previous state from scan history. '
                                 'Already at earliest history entry.')
                return
        return self.restore_from_history(self._curr_history_index - 1)

    @QtCore.Slot()
    def history_forward(self):
        with self._thread_lock:
            if self._curr_history_index >= len(self._history) - 1:
                self.log.warning('Unable to restore next state from scan history. '
                                 'Already at latest history entry.')
                return
        return self.restore_from_history(self._curr_history_index + 1)

    @QtCore.Slot(int)
    def restore_from_history(self, index):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.error('Scan is running. Unable to restore history state.')
                return
            if not isinstance(index, int):
                self.log.error('History index to restore must be int type.')
                return

            try:
                data = self._scan_history[index]
            except IndexError:
                self.log.error('History index "{0}" out of range.'.format(index))
                return

            ax_constr = self.scanner_constraints.axes
            for i, ax in enumerate(data.scan_axes):
                constr = ax_constr[ax]
                self._scan_resolution[ax] = int(constr.clip_resolution(data.resolution[i]))
                self._scan_ranges[ax] = tuple(
                    constr.clip_value(val) for val in data.target_ranges[i])
            self._scan_settings['frequency'] = data.scan_frequency
            self._curr_history_index = index
            self.sigScanRangesChanged.emit(self._scan_ranges.copy())
            self.sigScanResolutionChanged.emit(self._scan_resolution.copy())
            self.sigScanSettingsChanged.emit(self._scan_settings.copy())
            self.sigScanDataChanged.emit(data)
            return

    @QtCore.Slot()
    def set_full_scan_ranges(self):
        scan_range = {ax: axis.value_bounds for ax, axis in self.scanner_constraints.axes.items()}
        return self.set_scan_range(scan_range)

    @QtCore.Slot()
    def _start_timer(self):
        self.__sigStartTimer.emit()

    @QtCore.Slot()
    def _stop_timer(self):
        self.__sigStopTimer.emit()
