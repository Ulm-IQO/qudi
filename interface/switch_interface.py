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

from core.util.customexceptions import InterfaceImplementationError


class SwitchInterface():
    """ Methods to control slow (mechaincal) laser switching devices. """

    _modtype = 'SwitchInterface'
    _modclass = 'interface'

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

          @return int: number of swiches on this hardware
        """
        raise InterfaceImplementationError('SwitchInterface: getNumberOfSwitches')
        return -1

    def getSwitchState(self, switchNumber):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if on, False if off, None on error
        """
        raise InterfaceImplementationError('SwitchInterface: getSwitchStates')
        return -1

    def getCalibration(self, switchNumber, state):
        """ Get calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration
                                   parameter
          @param str switchState: state ['On', 'Off'] for which to get
                                  calibration parameter

          @return str: calibration parameter fir switch and state.
        """
        raise InterfaceImplementationError('SwitchInterface: getCalibration')
        return -1

    def setCalibration(self, switchNumber, state, value):
        """ Set calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration
                                   parameter
          @param str switchState: state ['On', 'Off'] for which to get
                                  calibration parameter
          @param int value: calibration parameter to be set.

          @return bool: True if suceeds, False otherwise
        """
        raise InterfaceImplementationError('SwitchInterface: setCalibration')
        return -1

    def switchOn(self, switchNumber):
        """ Switch on.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        raise InterfaceImplementationError('SwitchInterface: switchOn')
        return -1

    def switchOff(self, switchNumber):
        """ Switch off.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        raise InterfaceImplementationError('SwitchInterface: switchOff')
        return -1

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change
        """
        raise InterfaceImplementationError('SwitchInterface: getSwitchTime')
        return -1

