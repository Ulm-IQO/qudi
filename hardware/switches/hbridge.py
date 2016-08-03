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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import time
from core.base import Base
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface

class HBridge(Base, SwitchInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'switchinterface'
    _modtype = 'hardware'
    _out = {'switch': 'SwitchInterface'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lock = Mutex()

    def on_activate(self, e):
        config = self.getConfiguration()
        if not 'interface' in config:
            raise KeyError('{0} definitely needs an "interface" configuration value.'.format(self.__class__.__name__))
        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(
                config['interface'],
                baud_rate=9600,
                write_termination='\r\n',
                read_termination='\r\n',
                timeout=10,
                send_end=True
        )

    def on_deactivate(self, e):
        self.inst.close()

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

          @return int: number of switches
        """
        return 4

    def getSwitchState(self, switchNumber):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if on, False if off, None on error
        """
        with self.lock:
            pos = self.inst.ask('STATUS')
            ret = list()
            for i in pos.split():
                ret.append(int(i))
            return ret[switchNumber]

    def getCalibration(self, switchNumber, state):
        """ Get calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration parameter
          @param str switchState: state ['On', 'Off'] for which to get calibration parameter

          @return str: calibration parameter fir switch and state.

        In this case, the calibration parameter is the time for which current is
        applied to the coil/motor for switching.

        """
        return 0

    def setCalibration(self, switchNumber, state, value):
        """ Set calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration parameter
          @param str switchState: state ['On', 'Off'] for which to get calibration parameter
          @param int value: calibration parameter to be set.

          @return bool: True if success, False on error
        """
        pass

    def switchOn(self, switchNumber):
        """ Extend coil or move motor.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        coilnr = int(switchNumber) + 1
        if int(coilnr) > 0 and int(coilnr) < 5:
            with self.lock:
                try:
                    answer = self.inst.ask('P{0}=1'.format(coilnr))
                    if answer != 'P{0}=1'.format(coilnr):
                        return False
                    time.sleep(self.getSwitchTime(switchNumber))
                    self.log.info('{0} switch {1}: On'.format(
                        self._name, switchNumber))
                except:
                    return False
                return True
        else:
            self.log.error('You are trying to use non-existing output no {0}'
                    ''.format(coilnr))

    def switchOff(self, switchNumber):
        """ Retract coil ore move motor.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        coilnr = int(switchNumber) + 1
        if int(coilnr) > 0 and int(coilnr) < 5:
            with self.lock:
                try:
                    answer = self.inst.ask('P{0}=0'.format(coilnr))
                    if answer != 'P{0}=0'.format(coilnr):
                        return False
                    time.sleep(self.getSwitchTime(switchNumber))
                    self.log.info('{0} switch {1}: Off'.format(
                        self._name, switchNumber))
                except:
                    return False
                return True
        else:
            self.log.error('You are trying to use non-existing output no {0}'
                    ''.format(coilnr))

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change

          Coils typically switch faster than 0.5s, but safety first!
        """
        return 0.5

