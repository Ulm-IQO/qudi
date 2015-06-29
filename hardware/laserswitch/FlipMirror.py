# -*- coding: utf-8 -*-
"""
Control the Radiant Dyes flip mirror driver through the serial interface.

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

import visa
import time
from core.base import Base
from core.util.mutex import Mutex
from .LaserSwitchInterface import LaserSwitchInterface

class FlipMirror(Base, LaserSwitchInterface):
    """ This class is implements communication with the Radiant Dyes flip mirror driver
        through pyVISA.
    """
    _modclass = 'laserswitchinterface'
    _modtype = 'hardware'

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict)

        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'LaserSwitchInterface'
        self.lock = Mutex()

    def activation(self, e):
        config = self.getConfiguration()
        if not 'interface' in config:
            raise KeyError('{0} definitely needs an "interface" configuration value.'.format(self.__class__.__name__))
        self.inst = visa.SerialInstrument(
                config['interface'],
                baud_rate = 115200,
                term_chars='\r\n',
                timeout=10,
                send_end=True
        )

    def deactivation(self, e):
        self.inst.close()

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.
        """
        return 1

    def getSwitchState(self, switchNumber):
        """
        """
        with self.lock:
            pos = self.inst.ask('GP1')
            if pos == 'H1':
                return False
            elif pos == 'V1':
                return True
            else:
                return None

    def getCalibration(self, switchNumber, state):
        """
        """
        with self.lock:
            try:
                if state == 'On':
                    answer = self.inst.ask('GVT1')
                else:
                    answer = self.inst.ask('GHT1')
                result = int(answer.split('=')[1])
            except:
                result = -1
            return result

    def setCalibration(self, switchNumber, state, value):
        """
        """
        with self.lock:
            try:
                answer = self.inst.ask('SHT1 {0}'.format(int(value)))
                if answer != 'OK1':
                    return False
            except:
                return False
            return True

    def switchOn(self, switchNumber):
        """
        """
        with self.lock:
            try:
                answer = self.inst.ask('SV1')
                if answer != 'OK1':
                    return False
                time.sleep(self.getSwitchTime(switchNumber))
                self.logMsg('{0} switch {1}: On'.format(self._name, switchNumber))
            except:
                return False
            return True
    
    def switchOff(self, switchNumber):
        """
        """
        with self.lock:
            try:
                answer = self.inst.ask('SH1')
                if answer != 'OK1':
                    return False
                time.sleep(self.getSwitchTime(switchNumber))
                self.logMsg('{0} switch {1}: Off'.format(self._name, switchNumber))
            except:
                return False
            return True


    def getSwitchTime(self, switchNumber):
        """
        """
        return 2.0
