# -*- coding: utf-8 -*-
"""
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

import visa
from core.module import Base
from core.configoption import ConfigOption
from interface.switch_interface import SwitchInterface


class Main(Base, SwitchInterface):
    """ This class is implements communication with Thorlabs OSW12(22) fibered switch

    Example config for copy-paste:

    fibered_switch:
        module.Class: 'switches.osw12.Main'
        interface: 'ASRL1::INSTR'
    """

    interface = ConfigOption('interface', 'ASRL1::INSTR', missing='error')

    _rm = None
    _inst = None

    def on_activate(self):
        """ Module activation method """
        self._rm = visa.ResourceManager()
        try:
            self._inst = self._rm.open_resource(self.serial_interface, baud_rate=115200, write_termination='\n',
                                                read_termination='\r\n')
        except:
            self.log.error('Could not connect to OSW device')

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        self._inst.close()
        self._rm.close()

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

          @return int: number of swiches on this hardware
        """
        return 1

    def getSwitchState(self, switchNumber=0):
        """ Get the state of the switch.

          @param int switchNumber: index of switch

          @return bool: True if 1, False if 2
        """
        state = self._inst.query('S ?')
        if state == '1':
            return True
        elif state == '2':
            return False
        else:
            self.log.error('Hardware returned {} as switch state.'.format(state))

    def getCalibration(self, switchNumber, state):
        """ Get calibration parameter for switch.

        Function not used by this module
        """
        return 0

    def setCalibration(self, switchNumber, state, value):
        """ Set calibration parameter for switch.

        Function not used by this module
        """
        return True

    def switchOn(self, switchNumber):
        """ Set the state to on (channel 1)

          @param int switchNumber: number of switch to be switched

          @return bool: True if succeeds, False otherwise
        """
        self._inst.write('S 1')
        return True

    def switchOff(self, switchNumber):
        """ Set the state to off (channel 2)

          @param int switchNumber: number of switch to be switched

          @return bool: True if suceeds, False otherwise
        """
        self._inst.write('S 2')
        return True

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change
        """
        return 1e-3  # max. 1 ms; typ. 0.5 ms
