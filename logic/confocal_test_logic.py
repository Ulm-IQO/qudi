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
    signal_start_scanning = QtCore.Signal(str)
    signal_continue_scanning = QtCore.Signal(str)
    signal_stop_scanning = QtCore.Signal()
    signal_scan_lines_next = QtCore.Signal()
    signal_xy_image_updated = QtCore.Signal()
    signal_depth_image_updated = QtCore.Signal()
    signal_change_position = QtCore.Signal(str)
    signal_xy_data_saved = QtCore.Signal()
    signal_depth_data_saved = QtCore.Signal()
    signal_tilt_correction_active = QtCore.Signal(bool)
    signal_tilt_correction_update = QtCore.Signal()
    signal_draw_figure_completed = QtCore.Signal()
    signal_position_changed = QtCore.Signal()

    sigImageXYInitialized = QtCore.Signal()
    sigImageDepthInitialized = QtCore.Signal()

    signal_history_event = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        # Create semi-random dummy constraints
        self.constraints = dict()
        for axis in ('x', 'y', 'z', 'phi'):
            self.constraints[axis] = dict()
            limit = 50e-6 + 100e-6 * np.random.rand()
            self.constraints[axis]['min_value'] = -limit
            self.constraints[axis]['max_value'] = limit
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
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        pass

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
        for axis, axis_dict in self.scanner_constraints.items():
            extent = axis_dict['max_value'] - axis_dict['min_value']
            pos[axis] = axis_dict['min_value'] + extent * np.random.rand()
        return pos

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
