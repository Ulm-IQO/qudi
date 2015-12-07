# -*- coding: utf-8 -*-
"""
Dummy implementation for process control.

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

from core.base import Base
from .process_interface import ProcessInterface
from .process_control_interface import ProcessControlInterface
from pyqtgraph.Qt import QtCore
import time
import os.path
import numpy as np

class ProcessDummy(Base, ProcessInterface, ProcessControlInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'Process'
    _modtype = 'hardware'

    # connectors
    _out = {'dummy': 'Process',}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict)

    def activation(self, e):
        data = np.loadtxt(os.path.join(self.get_main_dir(), 'tools', 'copper.dat'))
        self.x = data[:,0]
        self.y = data[:,1]
        self.temperature = 111.0
        self.pwmpower = 0

        self.recalctimer = QtCore.QTimer()
        self.recalctimer.timeout.connect(self._recalcTemp)
        self.recalctimer.start(100)

    def deactivation(self, e):
        pass

    def getProcessValue(self):
        return self.temperature

    def getProcessUnit(self):
        return ('K', 'kelvin')

    def setControlValue(self, value):
        self.pwmpower = value

    def getControlValue(self):
        return self.pwmpower

    def getControlUnit(self):
        return ('%', 'percent')

    def getControlLimits(self):
        return (-100, 100)


    def _recalcTemp(self):
        pfactor = 0.01
        heatCapacity = np.interp(self.temperature, self.x, self.y)
        self.temperature = self.temperature + self.pwmpower * pfactor * heatCapacity
        print(self.temperature, self.pwmpower, heatCapacity)
