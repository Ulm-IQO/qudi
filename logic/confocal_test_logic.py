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
    sigScannerPositionChanged = QtCore.Signal(dict, object)
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

        # Create semi-random dummy constraints
        self.constraints = dict()
        for axis in ('x', 'y', 'z', 'phi'):
            self.constraints[axis] = dict()
            limit = 50e-6 + 100e-6 * np.random.rand()
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
                constr_dict['min_resolution'], min(constr_dict['max_resolution'], 200) + 1)
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
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(500)
        self.__timer.setSingleShot(False)
        self.__timer.timeout.connect(self.notify_scanner_position_change)
        self.__timer.start()
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self.__timer.stop()
        self.__timer.timeout.disconnect()
        return

    @property
    def scan_data(self):
        settings = self.scanner_settings
        data = list()
        for axes in settings['scan_axes']:
            scan = dict()
            scan['unit'] = 'c/s'
            scan['axes'] = dict()
            scan['axes']['names'] = tuple([*axes])
            if len(axes) == 1:
                scan['scan'] = 1e6 * np.random.rand(settings['scan_resolution'][axes[0]])
                scan['axes']['extent'] = (settings['scan_range'][axes[0]],)
            else:
                scan['scan'] = 1e6 * np.random.rand(settings['scan_resolution'][axes[0]],
                                                    settings['scan_resolution'][axes[1]])
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
    def set_scanner_target_position(self, pos_dict, caller=None):
        constr = self.scanner_constraints
        for ax, pos in pos_dict.items():
            if ax not in constr:
                self.log.error('Unknown scanner axis: "{0}"'.format(ax))
                return

        self.target.update(pos_dict)
        self.sigScannerTargetChanged.emit(pos_dict, caller)
        time.sleep(0.01)
        self.notify_scanner_position_change()
        return

    @QtCore.Slot()
    def notify_scanner_position_change(self):
        self.sigScannerPositionChanged.emit(self.scanner_position, self)
