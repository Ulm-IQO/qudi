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
from qudi.core import qudi_slot

from qudi.interface.scanning_probe_interface import ScanData


class ScanningOptimizeLogic(LogicBase):
    """
    ToDo: Write documentation
    """

    # declare connectors
    _scan_logic = Connector(name='scan_logic', interface='ScanningProbeLogic')
    _data_logic = Connector(name='data_logic', interface='ScanningDataLogic')

    # config options

    # status variables
    _scan_sequence = StatusVar(name='scan_sequence', default=None)
    _data_channel = StatusVar(name='data_channel', default=None)
    _scan_frequency = StatusVar(name='scan_frequency', default=None)
    _scan_range = StatusVar(name='scan_range', default=None)
    _scan_resolution = StatusVar(name='scan_resolution', default=None)

    # signals
    sigOptimalPositionChanged = QtCore.Signal(dict, object)
    sigOptimizeStateChanged = QtCore.Signal(bool)
    sigOptimizeSettingsChanged = QtCore.Signal(dict)
    sigOptimizeScanDataChanged = QtCore.Signal(object)

    _sigNextSequenceStep = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = RecursiveMutex()

        self._stashed_scan_settings = dict()
        self._sequence_index = 0
        self._curr_scan_data = None
        self._stop_requested = True
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

        self._sigNextSequenceStep.connect(self._next_sequence_step, QtCore.Qt.QueuedConnection)
        self._scan_logic().sigScanStateChanged.connect(
            self._scan_state_changed, QtCore.Qt.QueuedConnection
        )
        self._scan_logic().sigScanDataChanged.connect(
            self._scan_data_changed, QtCore.Qt.QueuedConnection
        )
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self._sigNextSequenceStep.disconnect()
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

    @qudi_slot(dict)
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

    @qudi_slot(bool)
    def toggle_optimize(self, start):
        if start:
            return self.start_optimize()
        else:
            return self.stop_optimize()

    @qudi_slot()
    def start_optimize(self):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.error('Unable to start optimization sequence. Optimizer still running.')
                self.sigOptimizeStateChanged.emit(True)
                return -1

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

            # Ignore following scans for scan history
            self._data_logic().toggle_ignore_new_data(True)

            self._sequence_index = 0
            self._stop_requested = False
            self.sigOptimizeStateChanged.emit(True)
            self._sigNextSequenceStep.emit()
            return 0

    @qudi_slot()
    def _next_sequence_step(self):
        with self._thread_lock:
            print('_next_sequence_step')
            if self.module_state() == 'idle':
                return

            if self._scan_logic().toggle_scan(True, self._scan_sequence[self._sequence_index]) < 0:
                self.log.error('Unable to start {0} scan. Optimize aborted.'.format(
                    self._scan_sequence[self._sequence_index])
                )
                self._stop_requested = True
                self._data_logic().toggle_ignore_new_data(False)
                self._scan_logic().set_scan_settings(self._stashed_scan_settings)
                self._stashed_scan_settings = dict()
                self._curr_scan_data = None
                self.module_state.unlock()
                self.sigOptimizeStateChanged.emit(False)
            return

    @qudi_slot(object)
    def _scan_data_changed(self, data):
        with self._thread_lock:
            print('_scan_data_changed')
            if self.module_state() == 'idle':
                return

            self._curr_scan_data = data
            self.sigOptimizeScanDataChanged.emit(data)
            return

    @qudi_slot(bool, tuple)
    def _scan_state_changed(self, is_running, axes):
        with self._thread_lock:
            print('_scan_state_changed')
            if is_running or self.module_state() == 'idle':
                return

            # ToDo: Perform fit on last scan data and move scanner target position
            if not is_running and self._curr_scan_data is not None:
                if axes != self._curr_scan_data.scan_axes:
                    self.log.error('Current ScanData axes do not match finished scan axes.')
                else:
                    scan_data = self._curr_scan_data
                    if scan_data.scan_dimension == 1:
                        x = np.linspace(*scan_data.scan_range[0], scan_data.scan_resolution[0])
                        opt_pos, fit_data = self._get_pos_from_1d_gauss_fit(
                            x,
                            scan_data.data[self._data_channel]
                        )
                    else:
                        x = np.linspace(*scan_data.scan_range[0], scan_data.scan_resolution[0])
                        y = np.linspace(*scan_data.scan_range[1], scan_data.scan_resolution[1])
                        xy = np.meshgrid(x, y, indexing='ij')
                        opt_pos, fit_data = self._get_pos_from_2d_gauss_fit(
                            xy,
                            scan_data.data[self._data_channel].ravel()
                        )
                    opt_pos_dict = {ax: opt_pos[ii] for ii, ax in enumerate(axes)}
                    new_pos = self._scan_logic().set_scanner_target_position(opt_pos_dict)
                    self.sigOptimalPositionChanged.emit(
                        {ax: pos for ax, pos in new_pos.items() if ax in opt_pos_dict},
                        fit_data
                    )

            self._sequence_index += 1

            # Terminate optimize sequence if finished
            if self._stop_requested or self._sequence_index >= len(self._scan_sequence):
                self._stop_requested = True
                self._data_logic().toggle_ignore_new_data(False)
                self._scan_logic().set_scan_settings(self._stashed_scan_settings)
                self._stashed_scan_settings = dict()
                self._curr_scan_data = None
                self.module_state.unlock()
                self.sigOptimizeStateChanged.emit(False)
            else:
                self._sigNextSequenceStep.emit()
            return

    @qudi_slot()
    def stop_optimize(self):
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.log.error('Unable to stop optimization sequence. Optimizer is not running.')
                self.sigOptimizeStateChanged.emit(False)
                return -1

            self._stop_requested = True
            seq_index = min(self._sequence_index, len(self._scan_sequence) - 1)
            return self._scan_logic().toggle_scan(False, self._scan_sequence[seq_index])

    def _get_pos_from_2d_gauss_fit(self, xy, data):
        model = Gaussian2D()
        try:
            fit_result = model.fit(data, xy=xy, **model.guess(data, xy))
        except:
            self._stop_requested = True
            x_min, x_max = xy[0].min(), xy[0].max()
            y_min, y_max = xy[1].min(), xy[1].max()
            x_middle = (x_max - x_min) / 2 + x_min
            y_middle = (y_max - y_min) / 2 + y_min
            self.log.exception('2D Gaussian fit unsuccessful. Aborting optimization sequence.')
            return (x_middle, y_middle), None
        return (fit_result.best_values['center_x'],
                fit_result.best_values['center_y']), fit_result.best_fit.reshape(xy[0].shape)

    def _get_pos_from_1d_gauss_fit(self, x, data):
        model = Gaussian()
        try:
            fit_result = model.fit(data, x=x, **model.guess(data, x))
        except:
            self._stop_requested = True
            x_min, x_max = x.min(), x.max()
            middle = (x_max - x_min) / 2 + x_min
            self.log.exception('1D Gaussian fit unsuccessful. Aborting optimization sequence.')
            return middle, None
        return (fit_result.best_values['center'],), fit_result.best_fit
