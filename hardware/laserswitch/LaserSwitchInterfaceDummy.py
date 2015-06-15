# -*- coding: utf-8 -*-
"""
Dummy implementation for switching interface.

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

from core.Base import Base
from collections import OrderedDict
from .LaserSwitchInterface import LaserSwitchInterface

class LaserSwitchInterfaceDummy(Base, LaserSwitchInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'laserswitchinterface'
    _modtype = 'hardware'

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict)

        self.connector['out']['switch'] = OrderedDict()
        self.connector['out']['switch']['class'] = 'LaserSwitchInterface'

        self.switchState = [False, False, False]
        self.switchCalibration = dict()
        self.switchCalibration['On'] = [0.9, 0.8, 0.88]
        self.switchCalibration['Off'] = [0.15, 0.3, 0.2]

    def activation(self, e):
        pass

    def deactivation(self, e):
        pass

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.
        """
        return len(self.switchState)

    def getSwitchState(self, switchNumber):
        """
        """
        return self.switchState[switchNumber]

    def getCalibration(self, switchNumber, state):
        """
        """
        return self.switchCalibration[state][switchNumber]

    def setCalibration(self, switchNumber, state, value):
        """
        """
        self.switchCalibration[state][switchNumber] = value

    def switchOn(self, switchNumber):
        """
        """
        self.switchState[switchNumber] = True
        return self.switchState[switchNumber]
    
    def switchOff(self, switchNumber):
        """
        """
        self.switchState[switchNumber] = False
        return self.switchState[switchNumber]

    def getSwitchTime(self, switchNumber):
        return 0.5
