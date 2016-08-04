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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


from core.base import Base
from collections import OrderedDict
from interface.switch_interface import SwitchInterface
import time

class SwitchDummy(Base, SwitchInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'switchinterfacedummy'
    _modtype = 'hardware'

    # connectors
    _out = {'switch': 'SwitchInterface'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.switchState = [False, False, False]
        self.switchCalibration = dict()
        self.switchCalibration['On'] = [0.9, 0.8, 0.88]
        self.switchCalibration['Off'] = [0.15, 0.3, 0.2]

    def on_activate(self, e):
        pass

    def on_deactivate(self, e):
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
        time.sleep(self.getSwitchTime(switchNumber))
        self.log.info('{0} switch {1}: On'.format(self._name, switchNumber))
        return self.switchState[switchNumber]

    def switchOff(self, switchNumber):
        """
        """
        self.switchState[switchNumber] = False
        time.sleep(self.getSwitchTime(switchNumber))
        self.log.info('{0} switch {1}: Off'.format(self._name, switchNumber))
        return self.switchState[switchNumber]

    def getSwitchTime(self, switchNumber):
        return 0.5
