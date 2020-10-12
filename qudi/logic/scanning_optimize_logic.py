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
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        return

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        return
