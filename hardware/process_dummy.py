# -*- coding: utf-8 -*-
"""
Dummy implementation for process control.

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

from core.module import Base
from interface.process_interface import ProcessInterface
from interface.process_control_interface import ProcessControlInterface
from qtpy import QtCore
import numpy as np

class ProcessDummy(Base, ProcessInterface, ProcessControlInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'Process'
    _modtype = 'hardware'

    def on_activate(self):
        """ Activate module.
        """
        self.temperature = 300.0
        self.pwmpower = 0

        self.recalctimer = QtCore.QTimer()
        self.recalctimer.timeout.connect(self._recalcTemp)
        self.recalctimer.start(100)

    def on_deactivate(self):
        """ Deactivate module.
        """
        pass

    def getProcessValue(self):
        """ Process value, here temperature.

            @return float: process value
        """
        return self.temperature

    def getProcessUnit(self):
        """ Process unit, here kelvin.

            @return float: process unit
        """
        return ('K', 'kelvin')

    def setControlValue(self, value):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        self.pwmpower = value

    def getControlValue(self):
        """ Get current control value, here heating power

            @return float: current control value
        """
        return self.pwmpower

    def getControlUnit(self):
        """ Get unit of control value.

            @return tuple(str): short and text unit of control value
        """
        return ('%', 'percent')

    def getControlLimits(self):
        """ Get minimum and maximum of control value.

            @return tuple(float, float): minimum and maximum of control value
        """
        return (-100, 100)

    def _recalcTemp(self):
        """ Update current temperature based on model.
        """
        pfactor = 1
        heatCapacity = self.metalHeatCapacity(self.temperature)
        dt = self.pwmpower * abs((self.temperature - 4)/self.temperature) * pfactor / heatCapacity
        if abs(dt) > 10:
            dt = 10*np.sign(dt)
        self.temperature = self.temperature + dt
        # print(self.temperature, self.pwmpower, heatCapacity)

    def metalHeatCapacity(self, T):
        """ Calculate heat capacity of copper at given temperature.

            @param float T: temperature at which to calculate heat capacity

            @return float: hrat capacity at temperature T
        """
        NA = 6.02214086 * 10**23  # Avogadro constant
        k = 1.38064852 * 10**(-23)  # Boltzmann constant
        TD = 343.5 # Debye temperatre of copper
        Ef = 7 * 1.602176565 * 10**(-19) # fermi energy of copper (7eV)
        heatcapacity = np.pi**2 * NA * k**2 * T / (2*Ef) + 12 * np.pi**4 * NA * k * T**3 / (5 * TD**3)
        if heatcapacity < 0.0005:
            return 0.0005
        return heatcapacity

