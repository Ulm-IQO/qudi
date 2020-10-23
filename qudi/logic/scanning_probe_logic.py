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
from qudi.core.util.mutex import RecursiveMutex
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

    # signals
    sigScanStateChanged = QtCore.Signal(bool, object, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanSettingsChanged = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = RecursiveMutex()

        # others
        self.__scan_poll_timer = None
        self.__scan_poll_interval = 0
        self.__scan_stop_requested = True
        self._curr_caller_id = id(self)
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

        self.__scan_poll_interval = 0
        self.__scan_stop_requested = True
        self._curr_caller_id = id(self)

        self.__scan_poll_timer = QtCore.QTimer()
        self.__scan_poll_timer.setSingleShot(True)
        self.__scan_poll_timer.timeout.connect(self.__scan_poll_loop, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__scan_poll_timer.stop()
        self.__scan_poll_timer.timeout.disconnect()
        if self.module_state() != 'idle':
            self._scanner().stop_scan()
        return

    @property
    def scan_data(self):
        with self._thread_lock:
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
        with self._thread_lock:
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
    def set_target_position(self, pos_dict, caller_id=None):
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
                                     'Clipping value to {1:.3e}.'.format(ax, new_pos[ax]))

            new_pos = self._scanner().move_absolute(new_pos)
            self.sigScannerTargetChanged.emit(new_pos, id(self) if caller_id is None else caller_id)
            return new_pos

    @qudi_slot(bool, tuple)
    @qudi_slot(bool, tuple, object)
    def toggle_scan(self, start, scan_axes, caller_id=None):
        with self._thread_lock:
            if start:
                return self.start_scan(scan_axes, caller_id)
            return self.stop_scan()

    @qudi_slot(tuple)
    @qudi_slot(tuple, object)
    def start_scan(self, scan_axes, caller_id=None):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.sigScanStateChanged.emit(True, self.scan_data, self._curr_caller_id)
                return 0

            scan_axes = tuple(scan_axes)
            self._curr_caller_id = id(self) if caller_id is None else caller_id

            self.module_state.lock()

            settings = {'axes': scan_axes,
                        'range': tuple(self._scan_ranges[ax] for ax in scan_axes),
                        'resolution': tuple(self._scan_resolution[ax] for ax in scan_axes),
                        'frequency': self._scan_frequency[scan_axes[0]]}
            fail, new_settings = self._scanner().configure_scan(settings)
            if fail:
                self.module_state.unlock()
                self.sigScanStateChanged.emit(False, None, self._curr_caller_id)
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

            # Calculate poll time to check for scan completion. Use line scan time estimate.
            line_points = self._scan_resolution[scan_axes[0]] if len(scan_axes) > 1 else 1
            self.__scan_poll_interval = line_points / self._scan_frequency[scan_axes[0]]
            self.__scan_poll_timer.setInterval(int(round(self.__scan_poll_interval * 1000)))

            if self._scanner().start_scan() < 0:
                self.module_state.unlock()
                self.sigScanStateChanged.emit(False, None, self._curr_caller_id)
                return -1

            self.sigScanStateChanged.emit(True, self.scan_data, self._curr_caller_id)
            self.__start_timer()
            return 0

    @qudi_slot()
    def stop_scan(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.sigScanStateChanged.emit(False, self.scan_data, self._curr_caller_id)
                return 0

            self.__stop_timer()

            err = self._scanner().stop_scan() if self._scanner().module_state() != 'idle' else 0

            self.module_state.unlock()
            self.sigScanStateChanged.emit(False, self.scan_data, self._curr_caller_id)
            return err

    @qudi_slot()
    def __scan_poll_loop(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                return

            if self._scanner().module_state() == 'idle':
                self.stop_scan()
                return

            # Queue next call to this slot
            self.__scan_poll_timer.start()
            return

    @qudi_slot()
    def set_full_scan_ranges(self):
        scan_range = {ax: axis.value_bounds for ax, axis in self.scanner_constraints.axes.items()}
        return self.set_scan_range(scan_range)

    def __start_timer(self):
        if self.thread() is not QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self.__scan_poll_timer,
                                            'start',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self.__scan_poll_timer.start()

    def __stop_timer(self):
        if self.thread() is not QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self.__scan_poll_timer,
                                            'stop',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self.__scan_poll_timer.stop()
