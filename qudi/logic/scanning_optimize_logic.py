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
    _settle_time = StatusVar(name='settle_time', default=1)
    _data_channel = StatusVar(name='data_channel', default=None)
    _scan_frequency = StatusVar(name='scan_frequency', default=None)
    _scan_range = StatusVar(name='scan_range', default=None)
    _scan_resolution = StatusVar(name='scan_resolution', default=None)

    # signals
    sigOptimalPositionChanged = QtCore.Signal(dict)
    sigOptimizeStateChanged = QtCore.Signal(bool)
    sigOptimizeSettingsChanged = QtCore.Signal(dict)
    sigOptimizeScanDataChanged = QtCore.Signal(object)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._thread_lock = RecursiveMutex()

        self._scan_in_progress = False
        self._curr_scan_data = dict()

        # optimize settings

        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        return

    @property
    def settle_time(self):
        return self._settle_time

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
    def optimize_settings(self):
        return {'settle_time': self._settle_time,
                'scan_frequency': self.scan_frequency,
                'data_channel': self._data_channel,
                'scan_range': self.scan_range,
                'scan_resolution': self.scan_resolution}

    def set_optimize_settings(self, settings):
        """
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                settings_update = self.optimize_settings
                self.log.error('Can not change optimize settings. Optimization still in progress.')
            else:
                settings_update = dict()
                if 'settle_time' in settings:
                    if settings['settle_time'] < 0:
                        self.log.error('optimizer "settle_time" must not be negative.')
                    else:
                        self._settle_time = float(settings['settle_time'])
                    settings_update['settle_time'] = self._settle_time
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

    def start_optimize(self):
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.log.error('Unable to start optimization sequence. Optimizer still running.')
                self.sigOptimizeStateChanged.emit(True)
                return True

            # ToDo: Sanity checks for settings go here

            # stash old scanner settings
            old_scan_settings = self._scan_logic().scan_settings

            # Set scan ranges
            actual_setting = self._scan_logic().set_scan_range(self._scan_range)
            if any(val != self._scan_range[ax] for ax, val in actual_setting.items()):
                self.log.warning('Some optimize scan ranges have been changed by the scanner.')
                self.set_optimize_settings({'scan_range': actual_setting})

            # Set scan frequency
            actual_setting = self._scan_logic().set_scan_frequency(self._scan_frequency)
            if any(val != self._scan_frequency[ax] for ax, val in actual_setting.items()):
                self.log.warning('Some optimize scan frequencies have been changed by the scanner.')
                self.set_optimize_settings({'scan_frequency': actual_setting})

            # Set scan frequency
            actual_setting = self._scan_logic().set_scan_frequency(self._scan_frequency)
            if any(val != self._scan_frequency[ax] for ax, val in actual_setting.items()):
                self.log.warning(
                    'Some optimize scan frequencies have been changed by the scanner.')
                self.set_optimize_settings({'scan_frequency': actual_setting})

            # Iterate through scan sequence and perform corresponding scans and gaussian fits
            for sequence in self._scan_sequence:
                # Peform 1D scan
                if len(sequence) == 1:
                    ax = sequence[0]
                    self._scan_logic().set_scan_settings({'resolution': self._scan_resolution[ax],
                                                          'frequency': }
                    )
                # Perform 2D scan
                elif len(sequence) == 2:

                else:
                    self.log.warning(
                        'Optimize scan sequence must contain only tuples of len 1 or 2. '
                        'Ignoring optimization step.'
                    )

