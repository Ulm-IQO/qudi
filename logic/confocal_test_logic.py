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
from copy import copy
import time
import datetime
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from io import BytesIO

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.module import Connector, ConfigOption, StatusVar


class ConfocalLogic(GenericLogic):
    """
    This is the Logic class for confocal scanning.
    """
    _modclass = 'confocallogic'
    _modtype = 'logic'

    # declare connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _clock_frequency = StatusVar('clock_frequency', 500)
    return_slowness = StatusVar(default=50)
    max_history_length = StatusVar(default=10)

    # signals
    sigScanStateChanged = QtCore.Signal(bool)
    sigScannerPositionChanged = QtCore.Signal(dict, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigScanDataChanged = QtCore.Signal(list)

    __sigNextLine = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

        # Create semi-random dummy constraints
        self.constraints = dict()
        for axis in ('x', 'y', 'z', 'phi'):
            self.constraints[axis] = dict()
            limit = 50e-6 + 50e-6 * np.random.rand()
            self.constraints[axis]['min_value'] = -limit
            self.constraints[axis]['max_value'] = limit
            self.constraints[axis]['min_step'] = 1e-9
            self.constraints[axis]['min_resolution'] = 2
            self.constraints[axis]['max_resolution'] = np.inf
            self.constraints[axis]['unit'] = 'm' if axis != 'phi' else '°'

        # scanner settings
        self.pixel_clock_freq = 1000
        self.backscan_speed = 50
        self.scan_axes = (('y', 'x'), ('z', 'phi'), ('y', 'z'), ('x',))
        self.scan_resolution = dict()
        self.scan_range = dict()
        for axis, constr_dict in self.constraints.items():
            self.scan_resolution[axis] = np.random.randint(
                max(constr_dict['min_resolution'], 100),
                min(constr_dict['max_resolution'], 400) + 1)
            self.scan_range[axis] = (constr_dict['min_value'], constr_dict['max_value'])

        # Dummy scan data
        self.scan_images = [None] * len(self.scan_axes)

        # Scanner target position
        self.target = dict()
        for axis, axis_dict in self.scanner_constraints.items():
            extent = axis_dict['max_value'] - axis_dict['min_value']
            self.target[axis] = axis_dict['min_value'] + extent * np.random.rand()

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

        # Scan data buffer
        self._scan_data = dict()
        for axes in self.scan_axes:
            if len(axes) == 2:
                self._scan_data[tuple(axes)] = 1e6 * np.random.rand(self.scan_resolution[axes[0]],
                                                                    self.scan_resolution[axes[1]])
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
        settings = self.scanner_settings
        data = list()
        for axes in settings['scan_axes']:
            scan = dict()
            scan['unit'] = 'c/s'
            scan['axes'] = dict()
            scan['axes']['names'] = tuple(axes)
            if len(axes) == 1:
                scan['scan'] = 1e6 * np.random.rand(settings['scan_resolution'][axes[0]])
                scan['axes']['extent'] = (settings['scan_range'][axes[0]],)
            else:
                # scan['scan'] = 1e6 * np.random.rand(settings['scan_resolution'][axes[0]],
                #                                     settings['scan_resolution'][axes[1]])
                scan['scan'] = self._scan_data[tuple(axes)]
                scan['axes']['extent'] = (settings['scan_range'][axes[0]],
                                          settings['scan_range'][axes[1]])
            data.append(scan)
        return data

    @property
    def scanner_position(self):
        pos = dict()
        for axis, value in self.target.items():
            axis_range = abs(
                self.constraints[axis]['max_value'] - self.constraints[axis]['min_value'])
            pos[axis] = value + (np.random.rand() - 0.5) * axis_range * 0.01
        return pos

    @property
    def scanner_target(self):
        return self.target.copy()

    @property
    def scanner_axes_names(self):
        return tuple(self.scanner_constraints)

    @property
    def scanner_constraints(self):
        return self.constraints.copy()

    @property
    def scanner_settings(self):
        settings = dict()
        settings['scan_axes'] = self.scan_axes
        settings['pixel_clock_frequency'] = self.pixel_clock_freq
        settings['backscan_speed'] = self.backscan_speed
        settings['scan_resolution'] = self.scan_resolution.copy()
        settings['scan_range'] = self.scan_range.copy()
        return settings

    @property
    def optimizer_settings(self):
        return self._optimizer_settings.copy()

    @QtCore.Slot(dict)
    def set_optimizer_settings(self, settings):
        if 'axes' in settings:
            for axis, axis_dict in settings.pop('axes').items():
                self._optimizer_settings['axes'][axis].update(axis_dict)
        print(settings)
        self._optimizer_settings.update(settings)
        self.sigOptimizerSettingsChanged.emit(self.optimizer_settings)
        return

    @QtCore.Slot(dict)
    @QtCore.Slot(dict, object)
    def set_scanner_target_position(self, pos_dict, caller_id=None):
        constr = self.scanner_constraints
        for ax, pos in pos_dict.items():
            if ax not in constr:
                self.log.error('Unknown scanner axis: "{0}"'.format(ax))
                return

        self.target.update(pos_dict)
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
                self.sigScanStateChanged.emit(True)
                self._scan_data[scan_axes] = self._generate_2d_dummy_data(scan_axes)
                print(self._scan_data[scan_axes].shape)
                self.__scan_line_count = 0
                self.__scan_start_time = time.time()
                self.__running_scan = scan_axes
                self.__scan_line_interval = self.scan_resolution[scan_axes[0]] / self.pixel_clock_freq
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
            if self.__scan_line_count >= self.scan_resolution[self.__running_scan[1]] or self.__scan_stop_requested:
                print(self.__scan_line_count)
                self.module_state.unlock()
                self.sigScanStateChanged.emit(False)
                self.__timer.start()
                return

            self.__scan_line_count += 1
            next_line_time = self.__scan_start_time + self.__scan_line_count * self.__scan_line_interval
            while time.time() < next_line_time:
                time.sleep(0.1)

            scan = dict()
            scan['unit'] = 'c/s'
            scan['axes'] = dict()
            scan['axes']['names'] = self.__running_scan
            scan['scan'] = self._scan_data[self.__running_scan].copy()
            scan['scan'][:, self.__scan_line_count:] = 0
            scan['axes']['extent'] = (self.scan_range[self.__running_scan[0]],
                                      self.scan_range[self.__running_scan[1]])
            data = [scan]
            self.sigScanDataChanged.emit(data)
            self.__sigNextLine.emit()
        return

    def _generate_2d_dummy_data(self, axes):
        x_res = self.scan_resolution[axes[0]]
        y_res = self.scan_resolution[axes[1]]
        x_start = self.scan_range[axes[0]][0]
        y_start = self.scan_range[axes[1]][0]
        z_start = -5e-6
        x_end = self.scan_range[axes[0]][1]
        y_end = self.scan_range[axes[1]][1]
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
        print('xx', xx.shape, 'yy', yy.shape)
        return np.random.rand(xx.shape[0], xx.shape[1]) * amplitude * 0.10 + gauss_ensemble(xx, yy)


