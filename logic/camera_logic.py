# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

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

from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class PIDLogic(GenericLogic):
    """
    Control a camera.
    """
    _modclass = 'cameralogic'
    _modtype = 'logic'

    # declare connectors
    hardware = Connector(interface='CameraInterface')
    timestep = StatusVar(default=100)

    # signals
    sigUpdateDisplay = QtCore.Signal()
    timer = QtCore.QTimer()

    _exposure = 1.

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._hardware = self.hardware()

        self.enabled = False

        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.loop)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def set_exposure(self, time):
        self._hardware.set_exposure(time)
        self._exposure = self._hardware.get_exposure()

    def get_exposure(self):
        return self._exposure

    def startLoop(self):
        """ Start the data recording loop.
        """
        self.enabled = True
        self._hardware.start_acquisition()
        self.timer.start(self._exposure*1000)

    def stopLoop(self):
        """ Stop the data recording loop.
        """
        self.timer.stop()
        self.enabled = False

    def loop(self):
        """ Execute step in the data recording loop: save one of each control and process values
        """

        self.last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        if self.enabled:
            self._hardware.start_acquisition()
            self.timer.start(self._exposure * 1000)



