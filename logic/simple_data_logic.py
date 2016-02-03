# -*- coding: utf-8 -*-
"""
Buffer for simple data

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore
import numpy as np

class SimpleDataLogic(GenericLogic):        
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'smple_data'
    _modtype = 'logic'
    _in = {'simpledata': 'SimpleData'}
    _out = {'simplelogic': 'SimpleDataLogic'}
        
    sigRepeat = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        """ Create logic object
          
          @param object manager: reference to module Manager
          @param str name: unique module name
          @param dict config: configuration in a dict
          @param dict kwargs: additional parameters as a dict
        """
        ## declare actions for state transitions
        state_actions = { 'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

    def activation(self, e):
        """ Prepare logic module for work.

          @param object e: Fysom state change notification
        """
        self._data_logic = self.connector['in']['simpledata']['object']
        self.stopRequest = False
        self.bufferLength = 1000
        self.sigRepeat.connect(self.measureLoop, QtCore.Qt.QueuedConnection)

    def deactivation(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        self.stopMeasure()

    def startMeasure(self):
        """ Start measurement: zero the buffer and call loop function."""
        self.buf = np.zeros(self.bufferLength)
        self.smooth = np.zeros(self.bufferLength)
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

        self.buf = np.roll(self.buf, -10)
        self.buf[-11:-1] = data
        window_len = 50
        w = np.hanning(window_len)
        s = np.r_[self.buf[window_len-1:0:-1], self.buf, self.buf[-1:-window_len:-1]]
        self.smooth = np.convolve(w/w.sum(), s, mode='valid')
        self.sigRepeat.emit()

