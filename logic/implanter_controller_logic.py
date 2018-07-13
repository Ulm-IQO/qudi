# -*- coding: utf-8 -*-
"""
Buffer for simple data

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

from core.module import Connector, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import numpy as np
import datetime
import time


class ImplanterControllerLogic(GenericLogic):
    """ Logic module for controlling the implanter.
    """
    _modclass = 'implanter_control'
    _modtype = 'logic'

    # declare connectors
    implanter_timer = Connector(interface='ExposureControllerInterface')

    # status var
    _countdown = StatusVar('countdown', default=3)
    low_time = StatusVar('lowtime', default=100e-6)
    high_time = StatusVar('hightime', default=100e-6)
    idle_level = StatusVar('idle_level', default=True)

    sigLoop = QtCore.Signal()
    sigFinished = QtCore.Signal()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._hardware = self.implanter_timer()
        self.stopRequest = False
        self.waitRequest = False
        self.starttime = datetime.datetime.now()
        self.current_countdown = self._countdown

        self.sigLoop.connect(self.timerLoop, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Deactivate modeule.
        """
        self.stopMeasure()

    def startMeasure(self):
        """ Start measurement: zero the buffer and call loop function."""
        self.module_state.lock()
        self.current_countdown = self.countdown
        self.starttime = datetime.datetime.now()
        self._hardware.configure_exposure(self.low_time, self.high_time, self.idle_level)
        self._hardware.prepare_exposure()
        self.sigLoop.emit()

    def stopMeasure(self):
        """ Ask the measurement loop to stop. """
        self.stopRequest = True

    def timerLoop(self):
        """ Measure one value, add them to buffer and remove the oldest value.
        """
        if self.stopRequest:
            self.stopRequest = False
            self.waitRequest = False
            self._hardware.stop_exposure()
            self.module_state.unlock()
            self.sigFinished.emit()
            return

        delta = datetime.datetime.now() - self.starttime
        if not self.waitRequest and delta.seconds > self.current_countdown:
            self._hardware.start_exposure()
            self.waitRequest = True

        if self.waitRequest:
            if self._hardware.get_status() > 0:
                self.stopRequest = False
                self.waitRequest = False
                self._hardware.stop_exposure()
                self.module_state.unlock()
                self.sigFinished.emit()
                return

        time.sleep(0.1)
        self.sigLoop.emit()

    @property
    def countdown(self):
        return self._countdown

    @countdown.setter
    def countdown(self, countdown):
        self._countdown = int(countdown)
