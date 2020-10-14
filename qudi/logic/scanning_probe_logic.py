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

from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.core.util.mutex import Mutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.core import qudi_slot


class ScanningProbeLogic(LogicBase):
    """
    This is the Logic class for 1D/2D SPM measurements.
    Scanning in this context means moving something along 1 or 2 dimensions and collecting data from
    possibly multiple sources at each position.
    """

    # declare connectors
    _scanner = Connector(name='scanner', interface='ScanningProbeInterface')

    # status vars
    _scan_ranges = StatusVar(name='scan_ranges', default=None)
    _scan_resolution = StatusVar(name='scan_resolution', default=None)
    _scan_frequency = StatusVar(name='scan_frequency', default=None)

    # config options
    _max_scan_update_interval = ConfigOption(name='max_scan_update_interval', default=5)
    _min_scan_update_interval = ConfigOption(name='min_scan_update_interval', default=0.25)
    _position_update_interval = ConfigOption(name='position_update_interval', default=1)

    # signals
    sigScanStateChanged = QtCore.Signal(bool, tuple)
    sigScannerPositionChanged = QtCore.Signal(dict, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigScanDataChanged = QtCore.Signal(object)

    __sigStopTimer = QtCore.Signal()
    __sigStartTimer = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = Mutex()

        # others
        self.__timer = None
        self.__current_scan_data = None
        self.__scan_update_interval = 0
        self.__scan_stop_requested = True
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        constr = self.scanner_constraints

        # scanner settings
        if not isinstance(self._scan_ranges, dict):
            self._scan_ranges = {ax.name: ax.value_range for ax in constr.axes.values()}
        if not isinstance(self._scan_resolution, dict):
            self._scan_resolution = {ax.name: max(ax.min_resolution, min(128, ax.max_resolution))
                                     for ax in constr.axes.values()}
        if not isinstance(self._scan_frequency, dict):
            self._scan_frequency = {ax.name: ax.max_frequency for ax in constr.axes.values()}

        self.__current_scan_data = None
        self.__scan_update_interval = 0
        self.__scan_stop_requested = True

        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(int(round(self._position_update_interval * 1000)))
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self._update_scanner_position_loop, QtCore.Qt.QueuedConnection)
        self.__sigStartTimer.connect(self.__timer.start, QtCore.Qt.QueuedConnection)
        self.__sigStopTimer.connect(self.__timer.stop, QtCore.Qt.QueuedConnection)
        self.__timer.start()
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__timer.stop()
        self.__timer.timeout.disconnect()
        self.__sigStartTimer.disconnect()
        self.__sigStopTimer.disconnect()
        if self.module_state() != 'idle':
            self._scanner().stop_scan()
        return

    @property
    def scan_data(self):
        with self._thread_lock:
            if self.module_state() != 'idle':
                return self._scanner().get_scan_data()
            return self.__current_scan_data

    @property
    def scanner_position(self):
        with self._thread_lock:
            return self._scanner().get_position()

    @property
    def scanner_target(self):
        with self._thread_lock:
            return self._scanner().get_target()

    @property
    def scanner_axes(self):
        return self.scanner_constraints.axes

    @property
    def scanner_channels(self):
        return self.scanner_constraints.channels

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
    def scan_frequency(self):
        with self._thread_lock:
            return self._scan_frequency.copy()

    @property
    def scan_settings(self):
        with self._thread_lock:
            return {'range': self._scan_ranges.copy(),
                    'resolution': self._scan_resolution.copy(),
                    'frequency': self._scan_frequency.copy()}

    @qudi_slot(dict)
    def set_scan_settings(self, settings):
        if 'range' in settings:
            self.set_scan_range(settings['range'])
        if 'resolution' in settings:
            self.set_scan_resolution(settings['resolution'])
        if 'frequency' in settings:
            self.set_scan_frequency(settings['frequency'])

    @qudi_slot(dict)
    def set_scan_range(self, ranges):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.warning('Scan is running. Unable to change scan ranges.')
                new_ranges = self._scan_ranges.copy()
                self.sigScanSettingsChanged.emit({'range': new_ranges})
                return new_ranges

            constr = self.scanner_constraints
            for ax, ax_range in ranges.items():
                if ax not in constr.axes:
                    self.log.error('Unknown scanner axis "{0}" encountered.'.format(ax))
                    new_ranges = self._scan_ranges.copy()
                    self.sigScanSettingsChanged.emit({'range': new_ranges})
                    return new_ranges

                self._scan_ranges[ax] = (constr.axes[ax].clip_value(float(min(ax_range))),
                                         constr.axes[ax].clip_value(float(max(ax_range))))

            new_ranges = {ax: self._scan_ranges[ax] for ax in ranges}
            self.sigScanSettingsChanged.emit({'range': new_ranges})
            return new_ranges

    @qudi_slot(dict)
    def set_scan_resolution(self, resolution):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.warning('Scan is running. Unable to change scan resolution.')
                new_res = self._scan_resolution.copy()
                self.sigScanSettingsChanged.emit({'resolution': new_res})
                return new_res

            constr = self.scanner_constraints
            for ax, ax_res in resolution.items():
                if ax not in constr.axes:
                    self.log.error('Unknown axis "{0}" encountered.'.format(ax))
                    new_res = self._scan_resolution.copy()
                    self.sigScanSettingsChanged.emit({'resolution': new_res})
                    return new_res

                self._scan_resolution[ax] = constr.axes[ax].clip_resolution(int(ax_res))

            new_resolution = {ax: self._scan_resolution[ax] for ax in resolution}
            self.sigScanSettingsChanged.emit({'resolution': new_resolution})
            return new_resolution

    @qudi_slot(dict)
    def set_scan_frequency(self, frequency):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.warning('Scan is running. Unable to change scan frequency.')
                new_freq = self._scan_frequency.copy()
                self.sigScanSettingsChanged.emit({'frequency': new_freq})
                return new_freq

            constr = self.scanner_constraints
            for ax, ax_freq in frequency.items():
                if ax not in constr.axes:
                    self.log.error('Unknown axis "{0}" encountered.'.format(ax))
                    new_freq = self._scan_frequency.copy()
                    self.sigScanSettingsChanged.emit({'frequency': new_freq})
                    return new_freq

                self._scan_frequency[ax] = constr.axes[ax].clip_frequency(float(ax_freq))

            new_freq = {ax: self._scan_frequency[ax] for ax in frequency}
            self.sigScanSettingsChanged.emit({'frequency': new_freq})
            return new_freq

    @qudi_slot(dict)
    @qudi_slot(dict, object)
    def set_scanner_target_position(self, pos_dict, caller_id=None):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.error('Unable to change scanner target position while a scan is running.')
                new_pos = self._scanner().get_target()
                self.sigScannerTargetChanged.emit(new_pos, id(self))
                return new_pos

            ax_constr = self.scanner_constraints.axes
            new_pos = pos_dict.copy()
            for ax, pos in pos_dict.items():
                if ax not in ax_constr:
                    self.log.error('Unknown scanner axis: "{0}"'.format(ax))
                    new_pos = self._scanner().get_target()
                    self.sigScannerTargetChanged.emit(new_pos, id(self))
                    return new_pos

                new_pos[ax] = ax_constr[ax].clip_value(pos)
                if pos != new_pos[ax]:
                    self.log.warning('Scanner position target value out of bounds for axis "{0}". '
                                     'Clipping value to {1:.3e.'.format(ax, new_pos[ax]))

            new_pos = self._scanner().move_absolute(new_pos)
            self.sigScannerTargetChanged.emit(new_pos, id(self) if caller_id is None else caller_id)
            return new_pos

    @qudi_slot()
    def _update_scanner_position_loop(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.sigScannerPositionChanged.emit(self._scanner().get_position(), id(self))
                self._start_timer()

    @qudi_slot()
    def update_scanner_position(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.sigScannerPositionChanged.emit(self._scanner().get_position(), id(self))

    @qudi_slot(bool)
    @qudi_slot(bool, tuple)
    def toggle_scan(self, start, scan_axes=None):
        scan_axes = tuple(scan_axes)
        with self._thread_lock:
            # ToDo: Check if the right scan is running/stopped (scan axes)
            if start and self.module_state() != 'idle':
                self.sigScanStateChanged.emit(True, scan_axes)
                return 0
            elif not start and self.module_state() == 'idle':
                self.sigScanStateChanged.emit(False, scan_axes)
                return 0

            if start:
                self.module_state.lock()

                settings = {'axes': tuple(scan_axes),
                            'range': tuple(self._scan_ranges[ax] for ax in scan_axes),
                            'resolution': tuple(self._scan_resolution[ax] for ax in scan_axes),
                            'frequency': self._scan_frequency[scan_axes[0]]}
                fail, new_settings = self._scanner().configure_scan(settings)
                if fail:
                    self.module_state.unlock()
                    self.sigScanStateChanged.emit(False, scan_axes)
                    return -1

                for ax_index, ax in enumerate(scan_axes):
                    # Update scan ranges if needed
                    new = tuple(new_settings['range'][ax_index])
                    if self._scan_ranges[ax] != new:
                        self._scan_ranges[ax] = new
                        self.sigScanSettingsChanged.emit({'range': {ax: self._scan_ranges[ax]}})

                    # Update scan resolution if needed
                    new = int(new_settings['resolution'][ax_index])
                    if self._scan_resolution[ax] != new:
                        self._scan_resolution[ax] = new
                        self.sigScanSettingsChanged.emit(
                            {'resolution': {ax: self._scan_resolution[ax]}}
                        )

                # Update scan frequency if needed
                new = float(new_settings['frequency'])
                if self._scan_frequency[scan_axes[0]] != new:
                    self._scan_frequency[scan_axes[0]] = new
                    self.sigScanSettingsChanged.emit({'frequency': {scan_axes[0]: new}})

                line_points = self._scan_resolution[scan_axes[0]] if len(scan_axes) > 1 else 1
                line_time = line_points / self._scan_frequency[scan_axes[0]]
                self.__scan_update_interval = max(self._min_scan_update_interval,
                                                  min(self._max_scan_update_interval, line_time))

                # Try to start scanner
                if self._scanner().start_scan() < 0:
                    self.log.error('Unable to start scanner.')
                    self.module_state.unlock()
                    self.sigScanStateChanged.emit(False, scan_axes)
                    return -1

                self.log.debug('Scanner successfully started')

                self._stop_timer()
                self.__timer.timeout.disconnect()
                self.__timer.setSingleShot(True)
                self.__timer.setInterval(int(round(self.__scan_update_interval * 1000)))
                self.__timer.timeout.connect(self._scan_loop, QtCore.Qt.QueuedConnection)

                self.sigScanStateChanged.emit(True, scan_axes)
                self.__scan_stop_requested = False
                self._start_timer()
            else:
                self.__scan_stop_requested = True
            return 0

    @qudi_slot()
    def _scan_loop(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                return

            self.__current_scan_data = self._scanner().get_scan_data()
            self.sigScanDataChanged.emit(self.__current_scan_data)
            # Terminate scan if finished
            if self.__current_scan_data.is_finished or self.__scan_stop_requested:
                if self._scanner().stop_scan() < 0:
                    self.log.error('Unable to stop scan.')

                self.__timer.timeout.disconnect()
                self.__timer.setSingleShot(True)
                self.__timer.setInterval(int(round(self._position_update_interval * 1000)))
                self.__timer.timeout.connect(
                    self._update_scanner_position_loop, QtCore.Qt.QueuedConnection
                )
                self.module_state.unlock()
                self.sigScanDataChanged.emit(self.__current_scan_data)
                self.sigScanStateChanged.emit(False, self.__current_scan_data.scan_axes)

            self._start_timer()
            return

    @qudi_slot()
    def set_full_scan_ranges(self):
        scan_range = {ax: axis.value_bounds for ax, axis in self.scanner_constraints.axes.items()}
        return self.set_scan_range(scan_range)

    @qudi_slot()
    def _start_timer(self):
        self.__sigStartTimer.emit()

    @qudi_slot()
    def _stop_timer(self):
        self.__sigStopTimer.emit()
