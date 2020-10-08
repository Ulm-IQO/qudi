# -*- coding: utf-8 -*-

"""
Control the Radiant Dyes flip mirror driver through the serial interface.

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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class SwitchInterface(metaclass=InterfaceMetaclass):
    """ Methods to control slow (mechanical) laser switching devices.

    Warning: This interface use CamelCase. This is should not be done in future versions. See more info here :
    documentation/programming_style.md
    """

    @abstract_interface_method
    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

          @return int: number of swiches on this hardware
        """
        pass

    @abstract_interface_method
    def getSwitchState(self, switchNumber):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if on, False if off, None on error
        """
        pass

    @abstract_interface_method
    def getCalibration(self, switchNumber, state):
        """ Get calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration parameter
          @param str switchState: state ['On', 'Off'] for which to get calibration parameter

          @return str: calibration parameter fir switch and state.
        """
        pass

    @abstract_interface_method
    def setCalibration(self, switchNumber, state, value):
        """ Set calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration parameter
          @param str switchState: state ['On', 'Off'] for which to get calibration parameter
          @param int value: calibration parameter to be set.

          @return bool: True if suceeds, False otherwise
        """
        pass

    @abstract_interface_method
    def switchOn(self, switchNumber):
        """ Switch on.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        pass

    @abstract_interface_method
    def switchOff(self, switchNumber):
        """ Switch off.

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        pass

    @abstract_interface_method
    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch
s
          @return float: time needed for switch state change
        """
        pass
