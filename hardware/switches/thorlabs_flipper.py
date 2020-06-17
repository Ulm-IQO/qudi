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

import os
import ctypes as ct
from core.module import Base
from core.configoption import ConfigOption
from interface.switch_interface import SwitchInterface


class Main(Base, SwitchInterface):
    """ This class is implements communication with Thorlabs MFF101 flipper via Kinesis dll

    Example config for copy-paste:

    flipper:
        module.Class: 'switches.thorlabs_flipper.Main'
        dll_folder: 'C:\Program Files\Thorlabs\Kinesis'
        serial_numbers: [000000123]

    Description of the hardware provided by Thorlabs:
        These Two-Position, High-Speed Flip Mounts flip lenses, filters, and other optical components into and out of a
         free-space beam.
    """
    dll_folder = ConfigOption('dll_folder', default=r'C:\Program Files\Thorlabs\Kinesis')
    dll_file = ConfigOption('dll_ffile', default='Thorlabs.MotionControl.FilterFlipper.dll')
    serial_numbers = ConfigOption('serial_numbers', missing='error')
    polling_rate_ms = ConfigOption('polling_rate_ms', default=200)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dll = None
        self._codes = None
        self._serial_numbers = None

    def on_activate(self):
        """ Module activation method """
        os.chdir(self.dll_folder)
        self._dll = ct.cdll.LoadLibrary(self.dll_file)
        self._dll.TLI_BuildDeviceList()

        self._serial_numbers = []
        for serial_number in self.serial_numbers:
            serial_number = ct.c_char_p(str(serial_number).encode('utf-8'))
            self._dll.FF_Open(serial_number)
            self._dll.FF_StartPolling(serial_number, ct.c_int(200))
            self._serial_numbers.append(serial_number)

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        for serial_number in self._serial_numbers:
            self._dll.FF_ClearMessageQueue(serial_number)
            self._dll.FF_StopPolling(serial_number)
            self._dll.FF_Close(serial_number)

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

          @return int: number of swiches on this hardware
        """
        return len(self._serial_numbers)

    def getSwitchState(self, switchNumber):
        """ Get the state of the switch.

          @param int switchNumber: index of switch

          @return bool: True if 2, False if 1 (homed)
        """
        return self._dll.FF_GetPosition(self._serial_numbers[switchNumber]) == 2

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

          @param (int) switchNumber: number of switch to be switched

          @return (bool): True if succeeds, False otherwise
        """
        self._dll.FF_MoveToPosition(self._serial_numbers[switchNumber], 2)
        return True

    def switchOff(self, switchNumber):
        """ Set the state to off (channel 2)

          @param (int) switchNumber: number of switch to be switched

          @return (bool): True if suceeds, False otherwise
        """
        self._dll.FF_MoveToPosition(self._serial_numbers[switchNumber], 1)
        return True

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change
        """
        return 500e-3  # max. 1 ms; typ. 0.5 ms
