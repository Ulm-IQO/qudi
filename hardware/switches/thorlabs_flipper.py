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
from operator import xor
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
        os.environ['PATH'] = str(self.dll_folder) + os.pathsep + os.environ['PATH']  # needed otherwise dll don't load
        self._dll = ct.cdll.LoadLibrary(self.dll_file)
        self._dll.TLI_BuildDeviceList()

        self._serial_numbers = {}
        for serial_number in self.serial_numbers:
            serial_number_c = ct.c_char_p(str(serial_number).encode('utf-8'))
            self._dll.FF_Open(serial_number_c)
            self._dll.FF_StartPolling(serial_number_c, ct.c_int(200))
            self._serial_numbers[serial_number] = serial_number_c

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        for serial_number in self.serial_numbers:
            serial_number_c = self._serial_numbers[serial_number]
            self._dll.FF_ClearMessageQueue(serial_number_c)
            self._dll.FF_StopPolling(serial_number_c)
            self._dll.FF_Close(serial_number_c)

    @property
    def name(self):
        """ Name of the hardware as string. """
        return 'Thorlabs flippers'

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples."""
        states = {}
        for serial in self.serial_numbers:
            states[str(serial)] = ('1', '2')
        return states

    def get_state(self, switch):
        """ Get the state of the switch."""
        return str(self._dll.FF_GetPosition(self._serial_numbers[int(switch)]))

    def set_state(self, switch, state):
        """ Query state of single switch by name """
        self._dll.FF_MoveToPosition(self._serial_numbers[int(switch)], int(state))

    # Bellow is a just a copy paste to prevent a conflict between interface overloading and non abstract methods
    @property
    def states(self):
        """ The setter for the states of the hardware. """
        return {switch: self.get_state(switch) for switch in self.available_states}

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware."""
        assert isinstance(state_dict), 'Parameter "state_dict" must be dict type'
        for switch, state in state_dict.items():
            self.set_state(switch, state)