# -*- coding: utf-8 -*-

"""
Dummy implementation for joystick interface.


This file contains the Qudi Interface for a joystick controller.

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

from core.module import Base, ConfigOption
from interface.joystick_interface import JoystickInterface


class JoystickDummy(Base, JoystickInterface):
    """ Dummy hardware for joystick interface

    Example configuration :
        dummy_joystick:
        module.Class: 'joystick.joystick_dummy.JoystickDummy'

    """

    _modtype = 'DummyJoystick'
    _modclass = 'hardware'

    _connected = ConfigOption('connected', True)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ Perform required deactivation.
        """
        pass

    def get_name(self):
        """ Retrieve an identifier the GUI can print

        @return string: identifier

        Maker, model, serial number, etc.
        """
        return "Dummy joystick 3000"

    def is_connected(self):
        """ Return true if the joystick is connected without error

        @return boolean: Ok ?
        """
        return self._connected

    def get_state(self):
        """ Retrieve the state of the controller
        """
        return {'axis': {
            'left_vertical': 0.,
            'left_horizontal': 0.,
            'right_vertical': 0.,
            'right_horizontal': 0.,
            'left_trigger': 0.,
            'right_trigger': 0.
            },
         'buttons': {
            'left_up': False,
            'left_down': False,
            'left_left': False,
            'left_right': False,
            'left_joystick': False,

            'right_up': False,
            'right_down': False,
            'right_left': False,
            'right_right': False,
            'right_joystick': False,

            'middle_left': None,
            'middle_right': None,

            'left_shoulder': None,
            'right_shoulder': None
         }
        }
