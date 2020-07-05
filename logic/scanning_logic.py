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

import lmfit
from qtpy import QtCore
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import RecursiveMutex
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.connector import Connector
from interface.temporary_scanning_interface import ScanSettings

__all__ = ('ScanningLogic',)


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
    sigOptimizerPositionChanged = QtCore.Signal(dict, dict, object)  # position, sigma

    __sigNextLine = QtCore.Signal()
    __sigOptimizeNextStep = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = RecursiveMutex()

        # Scan data buffer
        self._xy_scan_data = np.zeros((0, 0))
        self._xz_scan_data = np.zeros((0, 0))
        self._xy_optim_scan_data = np.zeros((0, 0))
        self._z_optim_scan_data = np.zeros(0)

        # others
        self.__scan_line_count = 0
        self.current_scan = 'xy'
        self.__scan_stop_requested = True
        self.__current_target = None
        self.__next_optimize_steps = list()
        self.__optim_xy_scan_range = (tuple(), tuple())
        self.__optim_z_scan_range = tuple()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        constraints = self.scanner_constraints

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
        self._xy_optim_scan_data = np.zeros((self._optim_xy_resolution, self._optim_xy_resolution))
        self._z_optim_scan_data = np.zeros(self._optim_z_resolution)

        self.__scan_line_count = 0
        self.current_scan = 'xy'
        self.__scan_stop_requested = True
        self.__current_target = self.scanner_target
        self.__sigNextLine.connect(self._scan_loop, QtCore.Qt.QueuedConnection)
        self.__sigOptimizeNextStep.connect(self._do_optimize_step, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__sigNextLine.disconnect()
        return

    @property
    def xy_scan_data(self):
        with self.threadlock:
            return self._xy_scan_data.copy()

    @property
    def xz_scan_data(self):
        with self.threadlock:
            return self._xz_scan_data.copy()

    @property
    def xy_optim_scan_data(self):
        with self.threadlock:
            return self._xy_optim_scan_data.copy()

    @property
    def z_optim_scan_data(self):
        with self.threadlock:
            return self._z_optim_scan_data.copy()

    @property
    def scanner_target(self):
        with self.threadlock:
            self.__current_target = self.scanner().get_target()
            return self.__current_target.copy()

    @property
    def scanner_constraints(self):
        return self.scanner().get_constraints()

    @property
    def scanner_settings(self):
        with self.threadlock:
            return {'pixel_clock_frequency': self._scan_frequency,
                    'xy_scan_resolution': self._xy_scan_resolution,
                    'z_scan_resolution': self._z_scan_resolution,
                    'x_scan_range': self._x_scan_range,
                    'y_scan_range': self._y_scan_range,
                    'z_scan_range': self._z_scan_range}

    @property
    def optimizer_settings(self):
        with self.threadlock:
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
        print('LOGIC CALLED: set_scanner_settings', settings)
        with self.threadlock:
            if self.module_state() != 'idle':
                self.log.warning('Scan is running. Unable to change scanner settings.')
                self.sigScannerSettingsChanged.emit(self.scanner_settings)
                return

            if 'pixel_clock_frequency' in settings:
                self._scan_frequency = int(settings['pixel_clock_frequency'])
            if 'xy_scan_resolution' in settings:
                self._xy_scan_resolution = int(settings['xy_scan_resolution'])
            if 'z_scan_resolution' in settings:
                self._z_scan_resolution = int(settings['z_scan_resolution'])
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
        print('LOGIC CALLED: set_optimizer_settings', settings)
        with self.threadlock:
            if self.module_state() != 'idle':
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
        print('LOGIC CALLED: set_scanner_target_position', pos_dict, caller_id)
        with self.threadlock:
            if self.module_state() != 'idle' and self.current_scan != 'optimize':
                self.log.warning('Scan is running. Unable to change target position.')
                self.sigScannerTargetChanged.emit(self.scanner_target, id(self))
                return
            if any(self.__current_target[ax] != pos for ax, pos in pos_dict.items()):
                self.__current_target = self.scanner().move_absolute(pos_dict)
            self.sigScannerTargetChanged.emit(self.__current_target.copy(),
                                              id(self) if caller_id is None else caller_id)
        return

    @QtCore.Slot(bool, str)
    def toggle_scan(self, start, axes):
        print('LOGIC CALLED: toggle_scan', start, axes)
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
                self.current_scan = axes
                self.sigScanStateChanged.emit(True, axes)

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
        with self.threadlock:
            if self.module_state() != 'locked':
                return
            if self.__scan_stop_requested or self.__scan_line_count <= 0:
                self.scanner().unlock_scanner()
                if self.current_scan == 'optimize':
                    self.__fit_optimize_scan()
                    self.__next_optimize_steps.pop(0)
                    self.__sigOptimizeNextStep.emit()
                else:
                    self.module_state.unlock()
                    self.sigScanStateChanged.emit(False, self.current_scan)
                return

            if self.current_scan == 'xy':
                line_index = self._xy_scan_data.shape[1] - self.__scan_line_count
                data_dict = self.scanner().get_scan_line(line_index)
                data = data_dict[tuple(data_dict)[0]]
                self._xy_scan_data[:, line_index] = data
                self.sigScanDataChanged.emit(self.current_scan, self.xy_scan_data)
            elif self.current_scan == 'xz':
                line_index = self._xz_scan_data.shape[1] - self.__scan_line_count
                data_dict = self.scanner().get_scan_line(line_index)
                data = data_dict[tuple(data_dict)[0]]
                self._xz_scan_data[:, line_index] = data
                self.sigScanDataChanged.emit(self.current_scan, self.xz_scan_data)
            elif self.current_scan == 'optimize':
                if self.__next_optimize_steps[0] == 'xy':
                    line_index = self._xy_optim_scan_data.shape[1] - self.__scan_line_count
                    data_dict = self.scanner().get_scan_line(line_index)
                    data = data_dict[tuple(data_dict)[0]]
                    self._xy_optim_scan_data[:, line_index] = data
                    self.sigScanDataChanged.emit(self.current_scan, self.xy_optim_scan_data)
                else:
                    data_dict = self.scanner().get_scan_line(0)
                    data = data_dict[tuple(data_dict)[0]]
                    self._z_optim_scan_data[:] = data
                    self.sigScanDataChanged.emit(self.current_scan, self.z_optim_scan_data)

            self.__scan_line_count -= 1
            self.__sigNextLine.emit()
        return

    @QtCore.Slot(bool)
    def toggle_optimize(self, start):
        print('LOGIC CALLED: toggle_optimize', start)
        with self.threadlock:
            if start and self.module_state() != 'idle':
                self.log.error('Unable to start optimizer scans. Scan already in progress.')
                self.sigScanStateChanged.emit(True, self.current_scan)
                return
            elif not start and self.module_state() == 'idle':
                self.log.error('Unable to stop optimizer scans. No scan running.')
                self.sigScanStateChanged.emit(False, self.current_scan)
                return

            if start:
                self.__scan_stop_requested = False
                self.module_state.lock()
                self.current_scan = 'optimize'
                self.__next_optimize_steps = list(self._optim_scan_sequence)
                self.sigScanStateChanged.emit(True, self.current_scan)
                self.__sigOptimizeNextStep.emit()
            return

    @QtCore.Slot()
    def _do_optimize_step(self):
        with self.threadlock:
            if self.module_state() != 'locked' or self.current_scan != 'optimize':
                self.log.error('Unable to perform next optimizer step. Optimizer not running.')
                self.sigScanStateChanged.emit(self.module_state() == 'locked', self.current_scan)
                return
            if len(self.__next_optimize_steps) == 0:
                self.__finish_optimize()
                return
            next_step = self.__next_optimize_steps[0]
            if next_step == 'xy':
                self.__scan_line_count = self._optim_xy_resolution
                self._xy_optim_scan_data = np.zeros(
                    (self._optim_xy_resolution, self._optim_xy_resolution))
                x_min = self.__current_target['x'] - (self._optim_xy_scan_range / 2)
                x_max = self.__current_target['x'] + (self._optim_xy_scan_range / 2)
                y_min = self.__current_target['y'] - (self._optim_xy_scan_range / 2)
                y_max = self.__current_target['y'] + (self._optim_xy_scan_range / 2)
                self.__optim_xy_scan_range = ((x_min, x_max), (y_min, y_max))
                settings = ScanSettings(
                    axes=('x', 'y'),
                    ranges=self.__optim_xy_scan_range,
                    resolution=(self._optim_xy_resolution, self._optim_xy_resolution),
                    px_frequency=self._optim_scan_frequency,
                    position_feedback=False)
            elif next_step == 'z':
                self.__scan_line_count = 1
                self._z_optim_scan_data = np.zeros(self._optim_z_resolution)
                x_min = self.__current_target['x']
                x_max = self.__current_target['x']
                z_min = self.__current_target['z'] - (self._optim_z_scan_range / 2)
                z_max = self.__current_target['z'] + (self._optim_z_scan_range / 2)
                self.__optim_z_scan_range = (z_min, z_max)
                settings = ScanSettings(
                    axes=('z', 'x'),
                    ranges=(self.__optim_z_scan_range, (x_min, x_max)),
                    resolution=(self._optim_z_resolution, 1),
                    px_frequency=self._optim_scan_frequency,
                    position_feedback=False)
            else:
                self.log.error(
                    'Unable to perform next optimizer step. Unknown step: "{0}".'.format(next_step))
                self.__finish_optimize()
                return

            # Configure scanner
            err, new_settings = self.scanner().configure_scan(settings)
            if err < 0:
                self.log.error('Something went wrong while setting up scanner for optimize.')
                self.__finish_optimize()
                return
            # Update new settings
            self._optim_scan_frequency = new_settings.px_frequency
            # ToDo: adjust resolution
            # ToDo: adjust scan range
            self.sigOptimizerSettingsChanged.emit(self.optimizer_settings)
            # Start scan
            err = self.scanner().lock_scanner()
            if err < 0:
                self.log.error('Something went wrong while starting scanner for optimize.')
                self.__finish_optimize()
                return
            self.__sigNextLine.emit()

    @QtCore.Slot()
    def __finish_optimize(self):
        self.__next_optimize_steps = list()
        self.module_state.unlock()
        self.sigScanStateChanged.emit(False, self.current_scan)

    @QtCore.Slot()
    def __fit_optimize_scan(self):
        if self.__next_optimize_steps[0] == 'xy':
            fit_result = self._fit_2d_gaussian()
            self.set_scanner_target_position(
                {'x': fit_result.values['x0'], 'y': fit_result.values['y0']})
            self.sigOptimizerPositionChanged.emit(
                {'x': fit_result.values['x0'], 'y': fit_result.values['y0']},
                {'x': fit_result.values['sigma_x'], 'y': fit_result.values['sigma_y']},
                None)
            print('theta:', np.rad2deg(fit_result.values['theta']))
        else:
            fit_result = self._fit_1d_gaussian()
            self.set_scanner_target_position({'z': fit_result.values['x0']})
            self.sigOptimizerPositionChanged.emit({'z': fit_result.values['x0']},
                                                  {'z': fit_result.values['sigma']},
                                                  fit_result.best_fit)

    @QtCore.Slot()
    def history_backwards(self):
        print('LOGIC CALLED: history_backwards')
        return

    @QtCore.Slot()
    def history_forward(self):
        print('LOGIC CALLED: history_forward')
        return

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

    @QtCore.Slot()
    def set_full_scan_ranges(self):
        print('LOGIC CALLED: set_full_scan_ranges')
        axes_ranges = self.scanner_constraints['axes_position_ranges']
        settings = {'{0}_scan_range'.format(ax): rng for ax, rng in axes_ranges.items()}
        self.set_scanner_settings(settings)
        return

    def _fit_1d_gaussian(self):
        model = lmfit.Model(self._gauss, independent_vars=['x'])
        result = model.fit(data=self._z_optim_scan_data,
                           x=np.linspace(self.__optim_z_scan_range[0],
                                         self.__optim_z_scan_range[1],
                                         self._optim_z_resolution),
                           amp=lmfit.Parameter('amp', value=50000, min=0),
                           x0=lmfit.Parameter(
                               'x0', value=self.__current_target['z'],
                               min=self.__current_target['z'] - 3 * self._optim_z_scan_range / 4,
                               max=self.__current_target['z'] + 3 * self._optim_z_scan_range / 4),
                           sigma=lmfit.Parameter('sigma',
                                                 value=self._optim_z_scan_range/2,
                                                 min=0,
                                                 max=self._optim_z_scan_range),
                           offset=lmfit.Parameter('offset', value=1000, min=0))
        return result

    def _fit_2d_gaussian(self):
        model = lmfit.Model(self._gauss2d, independent_vars=['xy'])
        result = model.fit(data=self._xy_optim_scan_data.flatten(),
                           xy=np.meshgrid(np.linspace(self.__optim_xy_scan_range[0][0],
                                                      self.__optim_xy_scan_range[0][1],
                                                      self._optim_xy_resolution),
                                          np.linspace(self.__optim_xy_scan_range[1][0],
                                                      self.__optim_xy_scan_range[1][1],
                                                      self._optim_xy_resolution),
                                          indexing='ij'),
                           amp=lmfit.Parameter('amp', value=50000, min=0),
                           x0=lmfit.Parameter(
                               'x0',
                               value=self.__current_target['x'],
                               min=self.__current_target['x'] - 3 * self._optim_xy_scan_range / 4,
                               max=self.__current_target['x'] + 3 * self._optim_xy_scan_range / 4),
                           y0=lmfit.Parameter(
                               'y0',
                               value=self.__current_target['y'],
                               min=self.__current_target['y'] - 3 * self._optim_xy_scan_range / 4,
                               max=self.__current_target['y'] + 3 * self._optim_xy_scan_range / 4),
                           sigma_x=lmfit.Parameter('sigma_x',
                                                   value=self._optim_xy_scan_range/2,
                                                   min=0,
                                                   max=self._optim_xy_scan_range),
                           sigma_y=lmfit.Parameter('sigma_y',
                                                   value=self._optim_xy_scan_range / 2,
                                                   min=0,
                                                   max=self._optim_xy_scan_range),
                           offset=lmfit.Parameter('offset', value=1000, min=0),
                           theta=lmfit.Parameter('theta', value=0, min=-np.pi/2, max=np.pi/2))
        return result

    @staticmethod
    def _gauss(x, amp, x0, sigma, offset):
        return offset + amp / (sigma * np.sqrt(2 * np.pi)) * np.exp(
            -(x - x0)**2 / (2 * sigma ** 2))

    @staticmethod
    def _gauss2d(xy, amp, offset, x0, y0, sigma_x, sigma_y, theta):
        x, y = xy
        a = np.cos(-theta) ** 2 / (2 * sigma_x ** 2) + np.sin(-theta) ** 2 / (2 * sigma_y ** 2)
        b = np.sin(2 * -theta) / (4 * sigma_y ** 2) - np.sin(2 * -theta) / (4 * sigma_x ** 2)
        c = np.sin(-theta) ** 2 / (2 * sigma_x ** 2) + np.cos(-theta) ** 2 / (2 * sigma_y ** 2)
        return (offset + amp * np.exp(
            -(a * (x - x0) ** 2 + 2 * b * (x - x0) * (y - y0) + c * (y - y0) ** 2))).flatten()
