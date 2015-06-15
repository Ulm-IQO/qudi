# -*- coding: utf-8 -*-
"""
Control custom board with 4 H bridges.

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
from core.Base import Base
from core.util.Mutex import Mutex
from .LaserSwitchInterface import LaserSwitchInterface

class HBridge(Base, LaserSwitchInterface):
    """ Methods to control slow laser switching devices.
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
                baud_rate = 9600,
                term_chars='\r\n',
                timeout=10,
                send_end=True
        )

    def deactivation(self, e):
        self.inst.close()

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.
        """
        return 4

    def getSwitchState(self, switchNumber):
        """
        """
        with self.lock:
            pos = self.inst.ask('STATUS')
            ret = list()
            for i in pos.split():
                ret.append(int(i))
            return ret[switchNumber]

    def getCalibration(self, switchNumber, state):
        """
        """
        return 0

    def setCalibration(self, switchNumber, state, value):
        """
        """
        pass

    def switchOn(self, switchNumber):
        """
        """
        coilnr = int(switchNumber) + 1
        if int(coilnr) > 0 and int(coilnr) < 5:
            with self.lock:
                try:
                    answer = self.inst.ask('P{0}=1'.format(coilnr))
                    if answer != 'P{0}=1'.format(coilnr):
                        return False
                    time.sleep(self.getSwitchTime(switchNumber))
                    self.logMsg('{0} switch {1}: On'.format(self._name, switchNumber))
                except:
                    return False
                return True
        else:
            self.logMsg('You are trying to use non-existing output no {0}'.format(coilnr), msgType='error')
    
    def switchOff(self, switchNumber):
        """
        """
        coilnr = int(switchNumber) + 1
        if int(coilnr) > 0 and int(coilnr) < 5:
            with self.lock:
                try:
                    answer = self.inst.ask('P{0}=0'.format(coilnr))
                    if answer != 'P{0}=0'.format(coilnr):
                        return False
                    time.sleep(self.getSwitchTime(switchNumber))
                    self.logMsg('{0} switch {1}: Off'.format(self._name, switchNumber))
                except:
                    return False
                return True
        else:
            self.logMsg('You are trying to use non-existing output no {0}'.format(coilnr), msgType='error')

    def getSwitchTime(self, switchNumber):
        return 0.5
