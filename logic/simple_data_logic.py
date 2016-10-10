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

from qtpy import QtCore
import numpy as np

from logic.generic_logic import GenericLogic


class SimpleDataLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'smple_data'
    _modtype = 'logic'
    _in = {'simpledata': 'SimpleData'}
    _out = {'simplelogic': 'SimpleDataLogic'}

    sigRepeat = QtCore.Signal()

    def on_activate(self, e):
        """ Prepare logic module for work.

          @param object e: Fysom state change notification
        """
        self._data_logic = self.get_in_connector('simpledata')
        self.stopRequest = False
        self.bufferLength = 1000
        self.sigRepeat.connect(self.measureLoop, QtCore.Qt.QueuedConnection)

    def on_deactivate(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        self.stopMeasure()

    def startMeasure(self):
        """ Start measurement: zero the buffer and call loop function."""
        self.window_len = 50
        self.buf = np.zeros((self.bufferLength,  self._data_logic.getChannels()))
        self.smooth = np.zeros((self.bufferLength + self.window_len - 1,  self._data_logic.getChannels()))
        self.lock()
        self.sigRepeat.emit()

    def stopMeasure(self):
        """ Ask the measurement loop to stop. """
        self.stopRequest = True

    def measureLoop(self):
        """ Measure 10 values, add them to buffer and remove the 10 oldest values.
        """
        if self.stopRequest:
            self.stopRequest = False
            self.unlock()
            return

        data = [self._data_logic.getData() for i in range(10)]

        self.buf = np.roll(self.buf, -10, axis=0)
        self.buf[-11:-1] = data
        w = np.hanning(self.window_len)
        s = np.r_[self.buf[self.window_len-1:0:-1], self.buf, self.buf[-1:-self.window_len:-1]]
        for channel in range(self._data_logic.getChannels()):
            convolved = np.convolve(w/w.sum(), s[:, channel], mode='valid')
            self.smooth[:, channel] = convolved
        self.sigRepeat.emit()

