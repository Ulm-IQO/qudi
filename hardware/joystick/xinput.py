# -*- coding: utf-8 -*-

"""
This hardware module implement the joystick interface to use an Xbox 360 or xbox one controller.
This use the xpinut api and only works for Windows

This module can be used with emulator like x360ce for non xinput controllers

---

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


import ctypes

from core.module import Base
from core.configoption import ConfigOption
from interface.joystick_interface import JoystickInterface


class JoystickXInput(Base, JoystickInterface):
    """
    Main class of the module

    Example configuration :
        joystick_hardware:
        module.Class: 'joystick.xinput.JoystickXInput'

    """

    _modtype = 'joystick'
    _modclass = 'hardware'

    _joystick_id = ConfigOption('joystick_id', 0)  # xinput support up to 4 controller
    _dll_path = ConfigOption('dll_path', None)
    _axis_maximum = ConfigOption('axis_maximum', 32767)
    _trigger_maximum = ConfigOption('trigger_maximum', 255)


    _dll = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        try:
            if self._dll_path is None:
                self._dll = ctypes.windll.xinput9_1_0
            else:
                self._dll = ctypes.WinDLL(self._dll_path)
        except OSError:
            self.log.error("Can not load xinput dll")

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_name(self):
        """ Retrieve an identifier the GUI can print
        Maker, model, serial number, etc.
        @return string: identifier
        """
        return "xinput controller #{}".format(self._joystick_id)

    def is_connected(self):
        """ Return true if the joystick is connected without error

        @return boolean: Ok ?
        """
        ERROR_SUCCESS = 0x00000000
        XINPUT_FLAG_GAMEPAD = 0x00000001

        status = self._dll.XInputGetCapabilities(ctypes.c_long(self._joystick_id), XINPUT_FLAG_GAMEPAD,
                                                 ctypes.c_void_p())

        self.log.debug(status)

        return status == ERROR_SUCCESS

    def get_state(self):
        """ Retrieve the state of the controller
        """
        state = XINPUT_STATE()
        self._dll.XInputGetState(ctypes.c_long(self._joystick_id), ctypes.byref(state))

        bitmasks = {
            'XINPUT_GAMEPAD_DPAD_UP': 0x00000001,
            'XINPUT_GAMEPAD_DPAD_DOWN': 0x00000002,
            'XINPUT_GAMEPAD_DPAD_LEFT': 0x00000004,
            'XINPUT_GAMEPAD_DPAD_RIGHT': 0x00000008,
            'XINPUT_GAMEPAD_START': 0x00000010,
            'XINPUT_GAMEPAD_BACK': 0x00000020,
            'XINPUT_GAMEPAD_LEFT_THUMB': 0x00000040,
            'XINPUT_GAMEPAD_RIGHT_THUMB': 0x00000080,
            'XINPUT_GAMEPAD_LEFT_SHOULDER': 0x0100,
            'XINPUT_GAMEPAD_RIGHT_SHOULDER': 0x0200,
            'XINPUT_GAMEPAD_A': 0x1000,
            'XINPUT_GAMEPAD_B': 0x2000,
            'XINPUT_GAMEPAD_X': 0x4000,
            'XINPUT_GAMEPAD_Y': 0x8000
        }

        state = state.Gamepad
        value_buttons = state.wButtons

        return {'axis': {
            'left_vertical': state.sThumbLY / self._axis_maximum,
            'left_horizontal': state.sThumbLX / self._axis_maximum,
            'right_vertical': state.sThumbRY / self._axis_maximum,
            'right_horizontal': state.sThumbRX / self._axis_maximum,
            'left_trigger': state.bLeftTrigger / self._trigger_maximum,
            'right_trigger': state.bRightTrigger / self._trigger_maximum
            },
         'buttons': {
            'left_up': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_DPAD_UP']),
            'left_down': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_DPAD_DOWN']),
            'left_left': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_DPAD_LEFT']),
            'left_right': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_DPAD_RIGHT']),
            'left_joystick': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_LEFT_THUMB']),

            'right_up': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_Y']),
            'right_down': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_A']),
            'right_left': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_X']),
            'right_right': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_B']),
            'right_joystick': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_RIGHT_THUMB']),

            'middle_left': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_BACK']),
            'middle_right': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_START']),

            'left_shoulder': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_LEFT_SHOULDER']),
            'right_shoulder': bool(value_buttons & bitmasks['XINPUT_GAMEPAD_RIGHT_SHOULDER'])
         }
        }

# Class defined in the xinput API


class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [
        ('wLeftMotorSpeed', ctypes.wintypes.WORD),
        ('wRightMotorSpeed', ctypes.wintypes.WORD)
    ]


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ('wButtons', ctypes.c_ushort),
        ('bLeftTrigger', ctypes.c_ubyte),
        ('bRightTrigger', ctypes.c_ubyte),
        ('sThumbLX', ctypes.c_short),
        ('sThumbLY', ctypes.c_short),
        ('sThumbRX', ctypes.c_short),
        ('sThumbRY', ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ('dwPacketNumber', ctypes.c_ulong),
        ('Gamepad', XINPUT_GAMEPAD),
    ]



