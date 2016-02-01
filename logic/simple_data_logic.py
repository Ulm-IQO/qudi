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
        self.bufferLength = 100
        self.sigRepeat.connect(self.measureLoop, QtCore.Qt.QueuedConnection)

    def deactivation(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        pass

    def startMeasure(self):
        self.buf = np.zeros(self.bufferLength)
        self.sigRepeat.emit()

    def stopMeasure(self):
        self.stopRequest = True

    def measureLoop(self):
        if self.stopRequest:
            self.stopRequest = False
            return

        data = self._data_logic.getData()
        self.buf = np.roll(self.buf, -1)
        self.buf[-1] = data
        self.sigRepeat.emit()

