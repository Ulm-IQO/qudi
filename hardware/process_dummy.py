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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.base import Base
from interface.process_interface import ProcessInterface
from interface.process_control_interface import ProcessControlInterface
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

    def on_activate(self, e):
        self.temperature = 300.0
        self.pwmpower = 0

        self.recalctimer = QtCore.QTimer()
        self.recalctimer.timeout.connect(self._recalcTemp)
        self.recalctimer.start(100)

    def on_deactivate(self, e):
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
        pfactor = 1
        heatCapacity = self.metalHeatCapacity(self.temperature)
        dt = self.pwmpower * abs((self.temperature - 4)/self.temperature) * pfactor / heatCapacity
        if abs(dt) > 10:
            dt = 10*np.sign(dt)
        self.temperature = self.temperature + dt
        # print(self.temperature, self.pwmpower, heatCapacity)

    def metalHeatCapacity(self, T):
        NA = 6.02214086 * 10**23  # Avogadro constant
        k = 1.38064852 * 10**(-23)  # Boltzmann constant
        TD = 343.5 # Debye temperatre of copper
        Ef = 7 * 1.602176565 * 10**(-19) # fermi energy of copper (7eV)
        heatcapacity = np.pi**2 * NA * k**2 * T / (2*Ef) + 12 * np.pi**4 * NA * k * T**3 / (5 * TD**3)
        if heatcapacity < 0.0005:
            return 0.0005
        return heatcapacity

