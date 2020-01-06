# -*- coding: utf-8 -*-

"""
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

import abc
from core.meta import InterfaceMetaclass


class JoystickInterface(metaclass=InterfaceMetaclass):
    """ Define the interface with a joystick controller like a video game controller

    This interface suppose a generic game controller with
        2 joysticks : left and right - pushable (also button)
        2 triggers axis - left and right
        4 left buttons (generally arrows)
        4 right buttons (generally A, B, X, Y)
        2 middle buttons (generally back and start)
        2 shoulder button - left and right (buttons above the triggers)
    """

    _modtype = 'CameraInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_name(self):
        """ Retrieve an identifier the GUI can print

        @return string: identifier

        Maker, model, serial number, etc.
        """
        pass

    @abc.abstractmethod
    def is_connected(self):
        """ Return true if the joystick is connected without error

        @return boolean: Ok ?
        """
        pass

    @abc.abstractmethod
    def get_state(self):
        """ Retrieve the state of the controller (pressed or axis state)

        @return dictionary

        Should be a dictionary like this :
        {'axis': {
            'left_vertical': float,
            'left_horizontal': float,
            'right_vertical': float,
            'right_horizontal': float,
            'left_trigger': float,
            'right_trigger': float
            },
         'buttons': {
            'left_up': boolean,
            'left_down': boolean,
            'left_left': boolean,
            'left_right': boolean,
            'left_joystick': boolean,

            'right_up': boolean,
            'right_down': boolean,
            'right_left': boolean,
            'right_right': boolean,
            'right_joystick': boolean,

            'middle_left': boolean,
            'middle_right': boolean,

            'left_shoulder': boolean,
            'right_shoulder': boolean
            }
        }

        Axis should be normalised between -1. and 1. for vertical and horizontal & between 0. and 1. for triggers.
        If a feature is not implemented by hardware, use None as value
        """
        pass
