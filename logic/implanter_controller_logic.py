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

from core.module import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import numpy as np
import time


class ImplanterControllerLogic(GenericLogic):
    """ Logic module for controlling the implanter.
    """
    _modclass = 'implanter_control'
    _modtype = 'logic'

    # declare connectors
    amperemeter = Connector(interface='AmperemeterInterface')

    sigRepeat = QtCore.Signal()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._amperemeter_hardware = self.get_connector('amperemeter')
        self.stopRequest = False
        self._bufferLength = 300
        self._window_len = 50
        self._current_data = 0.0
        self.sigRepeat.connect(self.measureLoop, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Deactivate modeule.
        """
        self.stopMeasure()

    def startMeasure(self):
        """ Start measurement: zero the buffer and call loop function."""
        self._data_buffer = np.zeros(self._bufferLength)
        self._time_buffer = np.zeros(self._bufferLength)
        self._start_time = time.time()
        self._data_smooth = np.zeros(self._bufferLength)
        self.module_state.lock()
        self.sigRepeat.emit()

    def stopMeasure(self):
        """ Ask the measurement loop to stop. """
        self.stopRequest = True

    def measureLoop(self):
        """ Measure one value, add them to buffer and remove the oldest value.
        """
        if self.stopRequest:
            self.stopRequest = False
            self.module_state.unlock()
            return

        self._current_data = float(self._amperemeter_hardware.get_value())

        self._data_buffer[0] = self._current_data
        self._time_buffer[0] = time.time() - self._start_time
        self._data_buffer = np.roll(self._data_buffer, -1, axis=0)
        self._time_buffer = np.roll(self._time_buffer, -1, axis=0)

        # calculate the median and save it
        self._data_smooth = np.roll(self._data_smooth, -1, axis=0)
        window = -int(self._window_len / 2) - 1
        self._data_smooth[window:] = np.median(self._data_buffer[-self._window_len:])
        self.sigRepeat.emit()

    @property
    def window_length(self):
        return self._window_len

    @window_length.setter
    def window_length(self, value):
        if self.module_state() == 'locked':
            self.log.error('Window length cannot be set while in locked state.')
        elif value > self._bufferLength:
            self.log.error('Window length ({0:d}) cannot be set to be bigger than the data buffer ({1:d}).'
                           .format(value, self._bufferLength))
        else:
            self._window_len = value

    @property
    def current_data(self):
        return self._current_data

    @property
    def data_buffer(self):
        return self._data_buffer

    @property
    def time_buffer(self):
        return self._time_buffer

    @property
    def data_smooth(self):
        return self._data_smooth