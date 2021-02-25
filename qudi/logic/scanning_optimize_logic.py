# -*- coding: utf-8 -*-
"""
This module is responsible for performing scanning probe measurements in order to find some optimal
position and move the scanner there.

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


import numpy as np
from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.core.fit_models.gaussian import Gaussian2D, Gaussian

from qudi.interface.scanning_probe_interface import ScanData


class ScanningOptimizeLogic(LogicBase):
    """
    ToDo: Write documentation
    """

    # declare connectors
    _scan_logic = Connector(name='scan_logic', interface='ScanningProbeLogic')

    # config options

    # status variables
    _scan_sequence = StatusVar(name='scan_sequence', default=None)
    _data_channel = StatusVar(name='data_channel', default=None)
    _scan_frequency = StatusVar(name='scan_frequency', default=None)
    _scan_range = StatusVar(name='scan_range', default=None)
    _scan_resolution = StatusVar(name='scan_resolution', default=None)

    # signals
    sigOptimizeStateChanged = QtCore.Signal(bool, dict, object)
    sigOptimizeSettingsChanged = QtCore.Signal(dict)

    _sigNextSequenceStep = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = RecursiveMutex()

        self._stashed_scan_settings = dict()
        self._sequence_index = 0
        self._optimal_position = dict()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        axes = self._scan_logic().scanner_axes
        channels = self._scan_logic().scanner_channels

        # optimize settings
        if not isinstance(self._scan_range, dict):
            self._scan_range = {ax.name: abs(ax.value_range[1] - ax.value_range[0]) / 100 for ax in
                                axes.values()}
        if not isinstance(self._scan_resolution, dict):
            self._scan_resolution = {ax.name: max(ax.min_resolution, min(16, ax.max_resolution))
                                     for ax in axes.values()}
        if not isinstance(self._scan_frequency, dict):
            self._scan_frequency = {ax.name: max(ax.min_frequency, min(50, ax.max_frequency)) for ax
                                    in axes.values()}
        if self._scan_sequence is None:
            avail_axes = tuple(axes.values())
            if len(avail_axes) >= 3:
                self._scan_sequence = [(avail_axes[0].name, avail_axes[1].name),
                                       (avail_axes[2].name,)]
            elif len(avail_axes) == 2:
                self._scan_sequence = [(avail_axes[0].name, avail_axes[1].name)]
            elif len(avail_axes) == 1:
                self._scan_sequence = [(avail_axes[0].name,)]
            else:
                self._scan_sequence = list()
        if self._data_channel is None:
            self._data_channel = tuple(channels.values())[0].name

        self._stashed_scan_settings = dict()
        self._sequence_index = 0
        self._optimal_position = dict()

        self._sigNextSequenceStep.connect(self._next_sequence_step, QtCore.Qt.QueuedConnection)
        self._scan_logic().sigScanStateChanged.connect(
            self._scan_state_changed, QtCore.Qt.QueuedConnection
        )
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self._scan_logic().sigScanStateChanged.disconnect()
        self._sigNextSequenceStep.disconnect()
        self.stop_optimize()
        return

    @property
    def data_channel(self):
        return self._data_channel

    @property
    def scan_frequency(self):
        return self._scan_frequency.copy()

    @property
    def scan_range(self):
        return self._scan_range.copy()

    @property
    def scan_resolution(self):
        return self._scan_resolution.copy()

    @property
    def scan_sequence(self):
        return self._scan_sequence.copy()

    @property
    def optimize_settings(self):
        return {'scan_frequency': self.scan_frequency,
                'data_channel': self._data_channel,
                'scan_range': self.scan_range,
                'scan_resolution': self.scan_resolution,
                'scan_sequence': self.scan_sequence}

    @property
    def optimal_position(self):
        return self._optimal_position.copy()

    @QtCore.Slot(dict)
    def set_optimize_settings(self, settings):
        """
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                settings_update = self.optimize_settings
                self.log.error('Can not change optimize settings. Optimization still in progress.')
            else:
                settings_update = dict()
                if 'scan_frequency' in settings:
                    self._scan_frequency.update(settings['scan_frequency'])
                    settings_update['scan_frequency'] = self.scan_frequency
                if 'data_channel' in settings:
                    self._data_channel = settings['data_channel']
                    settings_update['data_channel'] = self._data_channel
                if 'scan_range' in settings:
                    self._scan_range.update(settings['scan_range'])
                    settings_update['scan_range'] = self.scan_range
                if 'scan_resolution' in settings:
                    self._scan_resolution.update(settings['scan_resolution'])
                    settings_update['scan_resolution'] = self.scan_resolution

            self.sigOptimizeSettingsChanged.emit(settings_update)
            return settings_update

    @QtCore.Slot(bool)
    def toggle_optimize(self, start):
        if start:
            return self.start_optimize()
        return self.stop_optimize()

    @QtCore.Slot()
    def start_optimize(self):
        with self._thread_lock:
            print('start optimize')
            if self.module_state() != 'idle':
                self.sigOptimizeStateChanged.emit(True, dict(), None)
                return 0

            # ToDo: Sanity checks for settings go here

            self.module_state.lock()

            # stash old scanner settings
            self._stashed_scan_settings = self._scan_logic().scan_settings

            # Set scan ranges
            curr_pos = self._scan_logic().scanner_target
            optim_ranges = {ax: (pos - self._scan_range[ax] / 2, pos + self._scan_range[ax] / 2) for
                            ax, pos in curr_pos.items()}
            actual_setting = self._scan_logic().set_scan_range(optim_ranges)
            if any(val != optim_ranges[ax] for ax, val in actual_setting.items()):
                self.log.warning('Some optimize scan ranges have been changed by the scanner.')
                self.set_optimize_settings(
                    {'scan_range': {ax: abs(r[1] - r[0]) for ax, r in actual_setting.items()}}
                )

            # Set scan frequency
            actual_setting = self._scan_logic().set_scan_frequency(self._scan_frequency)
            if any(val != self._scan_frequency[ax] for ax, val in actual_setting.items()):
                self.log.warning('Some optimize scan frequencies have been changed by the scanner.')
                self.set_optimize_settings({'scan_frequency': actual_setting})

            # Set scan resolution
            actual_setting = self._scan_logic().set_scan_resolution(self._scan_resolution)
            if any(val != self._scan_resolution[ax] for ax, val in actual_setting.items()):
                self.log.warning(
                    'Some optimize scan resolutions have been changed by the scanner.')
                self.set_optimize_settings({'scan_resolution': actual_setting})

            self._sequence_index = 0
            self._optimal_position = dict()
            self.sigOptimizeStateChanged.emit(True, self.optimal_position, None)
            self._sigNextSequenceStep.emit()
            return 0

    @QtCore.Slot()
    def _next_sequence_step(self):
        with self._thread_lock:
            print('next sequence step')
            if self.module_state() == 'idle':
                return
            print('... module not idle. Toggling scan ...')

            if self._scan_logic().toggle_scan(True,
                                              self._scan_sequence[self._sequence_index],
                                              self.module_state.uuid) < 0:
                self.log.error('Unable to start {0} scan. Optimize aborted.'.format(
                    self._scan_sequence[self._sequence_index])
                )
                self.stop_optimize()
            return

    @QtCore.Slot(bool, object, object)
    def _scan_state_changed(self, is_running, data, caller_id):
        with self._thread_lock:
            if is_running or self.module_state() == 'idle' or caller_id != self.module_state.uuid:
                return
            elif data is not None:
                if data.scan_dimension == 1:
                    x = np.linspace(*data.scan_range[0], data.scan_resolution[0])
                    opt_pos, fit_data = self._get_pos_from_1d_gauss_fit(
                        x,
                        data.data[self._data_channel]
                    )
                else:
                    x = np.linspace(*data.scan_range[0], data.scan_resolution[0])
                    y = np.linspace(*data.scan_range[1], data.scan_resolution[1])
                    xy = np.meshgrid(x, y, indexing='ij')
                    opt_pos, fit_data = self._get_pos_from_2d_gauss_fit(
                        xy,
                        data.data[self._data_channel].ravel()
                    )
                position_update = {ax: opt_pos[ii] for ii, ax in enumerate(data.scan_axes)}
                if fit_data is not None:
                    new_pos = self._scan_logic().set_target_position(position_update)
                    for ax in tuple(position_update):
                        position_update[ax] = new_pos[ax]
                self._optimal_position.update(position_update)
                self.sigOptimizeStateChanged.emit(True, position_update, fit_data)

                # Abort optimize if fit failed
                if fit_data is None:
                    self.stop_optimize()
                    return
            print('... Scan complete ...')
            self._sequence_index += 1

            # Terminate optimize sequence if finished; continue with next sequence step otherwise
            if self._sequence_index >= len(self._scan_sequence):
                self.stop_optimize()
            else:
                self._sigNextSequenceStep.emit()
            return

    @QtCore.Slot()
    def stop_optimize(self):
        with self._thread_lock:
            print('stop optimize')
            if self.module_state() == 'idle':
                self.sigOptimizeStateChanged.emit(False, dict(), None)
                return 0

            if self._scan_logic().module_state() != 'idle':
                err = self._scan_logic().stop_scan()
            else:
                err = 0
            self._scan_logic().set_scan_settings(self._stashed_scan_settings)
            self._stashed_scan_settings = dict()
            self.module_state.unlock()
            self.sigOptimizeStateChanged.emit(False, dict(), None)
            return err

    def _get_pos_from_2d_gauss_fit(self, xy, data):
        model = Gaussian2D()
        print('fit 2D gaussian')
        try:
            fit_result = model.fit(data, xy=xy, **model.estimate_peak(data, xy))
        except:
            x_min, x_max = xy[0].min(), xy[0].max()
            y_min, y_max = xy[1].min(), xy[1].max()
            x_middle = (x_max - x_min) / 2 + x_min
            y_middle = (y_max - y_min) / 2 + y_min
            self.log.exception('2D Gaussian fit unsuccessful. Aborting optimization sequence.')
            return (x_middle, y_middle), None
        print('DONE: fit 2D gaussian')
        return (fit_result.best_values['center_x'],
                fit_result.best_values['center_y']), fit_result.best_fit.reshape(xy[0].shape)

    def _get_pos_from_1d_gauss_fit(self, x, data):
        model = Gaussian()
        print('fit 1D gaussian')
        try:
            fit_result = model.fit(data, x=x, **model.estimate_peak(data, x))
        except:
            x_min, x_max = x.min(), x.max()
            middle = (x_max - x_min) / 2 + x_min
            self.log.exception('1D Gaussian fit unsuccessful. Aborting optimization sequence.')
            return middle, None
        print('DONE: fit 1D gaussian')
        return (fit_result.best_values['center'],), fit_result.best_fit
