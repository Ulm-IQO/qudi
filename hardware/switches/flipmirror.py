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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import time
import core.logger as logger
from core.base import Base
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface

class FlipMirror(Base, SwitchInterface):
    """ This class is implements communication with the Radiant Dyes flip mirror driver
        through pyVISA.
    """
    _modclass = 'switchinterface'
    _modtype = 'hardware'
    _out = {'switch':'SwitchInterface'}

    def __init__(self, manager, name, config, **kwargs):
        """ Creae flip mirror control module

          @param object manager: reference to module manager
          @param str name: unique module name
          @param dict config; configuration parameters in a dict
          @param dict kwargs: aditional parameters in a dict
        """
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)
        self.lock = Mutex()
        print(config)
        print(self._configuration)

    def activation(self, e):
        """ Prepare module, connect to hardware.

          @param e: Fysom stae change notification.
        """
        config = self.getConfiguration()
        if not 'interface' in config:
            raise KeyError('{0} definitely needs an "interface" configuration value.'.format(self.__class__.__name__))
        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(
                config['interface'],
                baud_rate=115200,
                write_termination='\r\n',
                read_termination='\r\n',
                timeout=10,
                send_end=True
        )

    def deactivation(self, e):
        """ Disconnect from hardware on deactivation.

          @param e: Fysom stae change notification.
        """
        self.inst.close()
        self.rm.close()

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

          @return int: number of swiches on this hardware
        """
        return 1

    def getSwitchState(self, switchNumber):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if vertical, False if horizontal, None on error
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
        """ Get calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration parameter
          @param str switchState: state ['On', 'Off'] for which to get calibration parameter

          @return str: calibration parameter fir switch and state.

        In this case, the calibration parameter is a integer number that says where the
        horizontal and vertical position of the flip mirror is in the 16 bit PWM range of the motor driver.
        The number is returned as a string, not as an int, and needs to be converted.
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
        """ Set calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration parameter
          @param str switchState: state ['On', 'Off'] for which to get calibration parameter
          @param int value: calibration parameter to be set.

          @return bool: True if success, False on error
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
        """ Turn the flip mirror to vertical position.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        with self.lock:
            try:
                answer = self.inst.ask('SV1')
                if answer != 'OK1':
                    return False
                time.sleep(self.getSwitchTime(switchNumber))
                logger.info('{0} switch {1}: On'.format(
                    self._name, switchNumber))
            except:
                return False
            return True

    def switchOff(self, switchNumber):
        """ Turn the flip mirror to horizontal position.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        with self.lock:
            try:
                answer = self.inst.ask('SH1')
                if answer != 'OK1':
                    return False
                time.sleep(self.getSwitchTime(switchNumber))
                logger.info('{0} switch {1}: Off'.format(
                    self._name, switchNumber))
            except:
                return False
            return True


    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change
        """
        return 2.0
