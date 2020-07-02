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
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.connector import Connector
from interface.temporary_scanning_interface import ScanSettings


class ScanningLogic(GenericLogic):
    """
    This is the Logic class for 1D/2D scanning measurements.
    Scanning in this context means moving something along 1 or 2 dimensions and collecting data
    at each position.
    """

    # declare connectors
    scanner = Connector(interface='TemporaryScanningDummy')
    savelogic = Connector(interface='SaveLogic')

    # optimizer settings status vars
    _optim_xy_scan_range = StatusVar(name='optim_xy_scan_range', default=1e-6)
    _optim_z_scan_range = StatusVar(name='optim_z_scan_range', default=3e-6)
    _optim_xy_resolution = StatusVar(name='optim_xy_resolution', default=20)
    _optim_z_resolution = StatusVar(name='optim_z_resolution', default=20)
    _optim_scan_frequency = StatusVar(name='optim_scan_frequency', default=50)
    _optim_scan_sequence = StatusVar(name='optim_scan_sequence', default=('xy', 'z'))

    # scan settings status vars
    _x_scan_range = StatusVar(name='x_scan_range', default=None)
    _y_scan_range = StatusVar(name='y_scan_range', default=None)
    _z_scan_range = StatusVar(name='z_scan_range', default=None)
    _xy_scan_resolution = StatusVar(name='xy_scan_resolution', default=100)
    _z_scan_resolution = StatusVar(name='z_scan_resolution', default=100)
    _scan_frequency = StatusVar(name='scan_frequency', default=500.0)

    # signals
    sigScanStateChanged = QtCore.Signal(bool, str)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScannerSettingsChanged = QtCore.Signal(dict)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigScanDataChanged = QtCore.Signal(str, np.ndarray)

    __sigNextLine = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

        # Scan data buffer
        self._xy_scan_data = np.zeros((0, 0))
        self._xz_scan_data = np.zeros((0, 0))

        # others
        self.__scan_line_count = 0
        self.current_scan = 'xy'
        self.__scan_stop_requested = True
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
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
        self._xy_scan_resolution = int(self._xy_scan_resolution)
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
        elif self._scan_frequency > max_freq:
            self._scan_frequency = max_freq

        # Scan data buffer
        self._xy_scan_data = np.zeros((self._xy_scan_resolution, self._xy_scan_resolution))
        self._xz_scan_data = np.zeros((self._xy_scan_resolution, self._z_scan_resolution))

        self.__scan_line_count = 0
        self.current_scan = 'xy'
        self.__scan_stop_requested = True
        self.__sigNextLine.connect(self._scan_loop, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__sigNextLine.disconnect()
        return

    @property
    def xy_scan_data(self):
        return self._xy_scan_data.copy()

    @property
    def xz_scan_data(self):
        return self._xz_scan_data.copy()

    @property
    def scanner_target(self):
        return self.scanner().get_target()

    @property
    def scanner_constraints(self):
        return self.scanner().get_constraints()

    @property
    def scanner_settings(self):
        return {'pixel_clock_frequency': self._scan_frequency,
                'scan_resolution': self._xy_scan_resolution,
                'x_scan_range': self._x_scan_range,
                'y_scan_range': self._y_scan_range,
                'z_scan_range': self._z_scan_range}

    @property
    def optimizer_settings(self):
        return {'pixel_clock': self._optim_scan_frequency,
                'sequence': self._optim_scan_sequence,
                'x_range': self._optim_xy_scan_range,
                'y_range': self._optim_xy_scan_range,
                'z_range': self._optim_z_scan_range,
                'x_resolution': self._optim_xy_resolution,
                'y_resolution': self._optim_xy_resolution,
                'z_resolution': self._optim_z_resolution}

    @QtCore.Slot(dict)
    def set_scanner_settings(self, settings):
        if self.module_state() == 'locked':
            self.log.warning('Scan is running. Unable to change scanner settings.')
            self.sigScannerSettingsChanged.emit(self.scanner_settings)
            return

        if 'pixel_clock_frequency' in settings:
            self._scan_frequency = int(settings['pixel_clock_frequency'])
        if 'scan_resolution' in settings:
            self._xy_scan_resolution = int(settings['scan_resolution'])
            self._z_scan_resolution = int(settings['scan_resolution'])
        if 'x_scan_range' in settings:
            self._x_scan_range = settings['x_scan_range']
        if 'y_scan_range' in settings:
            self._y_scan_range = settings['y_scan_range']
        if 'z_scan_range' in settings:
            self._z_scan_range = settings['z_scan_range']
        self.sigScannerSettingsChanged.emit(self.scanner_settings)
        return

    @QtCore.Slot(dict)
    def set_optimizer_settings(self, settings):
        if self.module_state() == 'locked':
            self.log.warning('Scan is running. Unable to change optimizer settings.')
            self.sigOptimizerSettingsChanged.emit(self.optimizer_settings)
            return

        if 'pixel_clock' in settings:
            self._optim_scan_frequency = float(settings['pixel_clock'])
        if 'sequence' in settings:
            seq = tuple(x.strip().lower() for x in settings['sequence'] if x.strip().lower() in ('xy', 'z'))
            self._optim_scan_sequence = seq
        if 'x_range' in settings:
            self._optim_xy_scan_range = float(settings['x_range'])
        elif 'y_range' in settings:
            self._optim_xy_scan_range = float(settings['y_range'])
        if 'z_range' in settings:
            self._optim_z_scan_range = float(settings['z_range'])
        if 'x_resolution' in settings:
            self._optim_xy_resolution = int(settings['x_resolution'])
        elif 'y_resolution' in settings:
            self._optim_xy_resolution = int(settings['y_resolution'])
        if 'z_resolution' in settings:
            self._optim_z_resolution = int(settings['z_resolution'])
        self.sigOptimizerSettingsChanged.emit(self.optimizer_settings)
        return

    @QtCore.Slot(dict)
    @QtCore.Slot(dict, object)
    def set_scanner_target_position(self, pos_dict, caller_id=None):
        self.scanner().move_absolute(pos_dict)
        self.sigScannerTargetChanged.emit(pos_dict, id(self) if caller_id is None else caller_id)
        return

    @QtCore.Slot(bool, str)
    def toggle_scan(self, start, axes):
        with self.threadlock:
            if start and self.module_state() != 'idle':
                self.log.error('Unable to start scan. Scan already in progress.')
                self.sigScanStateChanged.emit(True, self.current_scan)
                return
            elif not start and self.module_state() == 'idle':
                self.log.error('Unable to stop scan. No scan running.')
                self.sigScanStateChanged.emit(False, self.current_scan)
                return
            elif start and axes not in ('xy', 'xz'):
                self.log.error('Unable to start scan. Scan type unknown: "{0}".'.format(axes))
                self.sigScanStateChanged.emit(False, self.current_scan)
                return

            if start:
                self.__scan_stop_requested = False
                self.module_state.lock()
                self.sigScanStateChanged.emit(True, axes)
                self.current_scan = axes

                if axes == 'xz':
                    self.__scan_line_count = self._z_scan_resolution
                    self._xz_scan_data = np.zeros((self._xy_scan_resolution, self._z_scan_resolution))
                    settings = ScanSettings(
                        axes=('x', 'z'),
                        ranges=(self._x_scan_range, self._z_scan_range),
                        resolution=(self._xy_scan_resolution, self._z_scan_resolution),
                        px_frequency=self._scan_frequency,
                        position_feedback=False)
                else:
                    self.__scan_line_count = self._xy_scan_resolution
                    self._xy_scan_data = np.zeros((self._xy_scan_resolution, self._xy_scan_resolution))
                    settings = ScanSettings(
                        axes=('x', 'y'),
                        ranges=(self._x_scan_range, self._y_scan_range),
                        resolution=(self._xy_scan_resolution, self._xy_scan_resolution),
                        px_frequency=self._scan_frequency,
                        position_feedback=False)

                # Configure scanner
                err, new_settings = self.scanner().configure_scan(settings)
                if err < 0:
                    self.log.error('Something went wrong while setting up scanner.')
                    self.module_state().unlock()
                    self.sigScanStateChanged.emit(False, self.current_scan)
                    return
                # Update new settings
                self._scan_frequency = new_settings.px_frequency
                self._xy_scan_resolution = new_settings.resolution[0]
                if new_settings.axes[1] == 'z':
                    self._z_scan_resolution = new_settings.resolution[1]
                self._x_scan_range = new_settings.ranges[0]
                if new_settings.axes[1] == 'z':
                    self._z_scan_range = new_settings.ranges[1]
                else:
                    self._y_scan_range = new_settings.ranges[1]
                self.sigScannerSettingsChanged.emit(self.scanner_settings)
                # Start scan
                err = self.scanner().lock_scanner()
                if err < 0:
                    self.log.error('Something went wrong while starting scanner.')
                    self.module_state().unlock()
                    self.sigScanStateChanged.emit(False, self.current_scan)
                    return
                self.__sigNextLine.emit()
        return

    @QtCore.Slot()
    def _scan_loop(self):
        if self.module_state() != 'locked':
            return

        with self.threadlock:
            if self.module_state() != 'locked':
                return
            if self.__scan_stop_requested or self.__scan_line_count <= 0:
                self.module_state.unlock()
                self.scanner().unlock_scanner()
                self.sigScanStateChanged.emit(False, self.current_scan)
                return

            if self.current_scan == 'xy':
                line_index = self._xy_scan_data.shape[1] - self.__scan_line_count
                data_dict = self.scanner().get_scan_line(line_index)
                data = data_dict[tuple(data_dict)[0]]
                self._xy_scan_data[:, line_index] = data
                self.sigScanDataChanged.emit(self.current_scan, self.xy_scan_data)
            else:
                line_index = self._xz_scan_data.shape[1] - self.__scan_line_count
                data_dict = self.scanner().get_scan_line(line_index)
                data = data_dict[tuple(data_dict)[0]]
                self._xz_scan_data[:, line_index] = data
                self.sigScanDataChanged.emit(self.current_scan, self.xz_scan_data)

            self.__scan_line_count -= 1
            self.__sigNextLine.emit()
        return

    @QtCore.Slot()
    def history_backwards(self):
        pass

    @QtCore.Slot()
    def history_forward(self):
        pass

    # def restore_from_history(self, index):
    #     if self.module_state() == 'locked':
    #         self.log.warning('Scan is running. Unable to restore history state.')
    #         return
    #     if not isinstance(index, int):
    #         self.log.error('History index to restore must be int type.')
    #         return
    #
    #     try:
    #         data = self._history[index]
    #     except IndexError:
    #         self.log.error('History index "{0}" out of range.'.format(index))
    #         return
    #
    #     axes = data.scan_axes
    #     resolution = data.resolution
    #     ranges = data.target_ranges
    #     for i, axis in enumerate(axes):
    #         self._scanner_settings['scan_resolution'][axis] = resolution[i]
    #         self._scanner_settings['scan_range'][axis] = ranges[i]
    #     self._history_index = index
    #     self.sigScannerSettingsChanged.emit(self.scanner_settings)
    #     self.sigScanDataChanged.emit({axes: data})
    #     return

    # @QtCore.Slot()
    # def set_full_scan_ranges(self):
    #     scan_ranges = {ax: (ax_dict['min_value'], ax_dict['max_value']) for ax, ax_dict in
    #                    self.scanner_constraints['axes'].items()}
    #     self.set_scanner_settings({'scan_range': scan_ranges})
    #     return
