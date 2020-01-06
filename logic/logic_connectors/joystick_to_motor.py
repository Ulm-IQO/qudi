# -*- coding: utf-8 -*-

"""
A module for that listen to joystick events and act on stepper hardware based on this events

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

from core.module import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
import numpy as np
import time


class JoystickToMotor(GenericLogic):
    """ This logic module get callbacks from joystick logic and interact with motor hardware based on these events

    This module needs joystick_logic to function

    To prevent accidentally changing things, module only act if some 'trigger_keys' are pushed.

    Example configuration :
        connector_joystick_motor:
        module.Class: 'logic_connectors.joystick_to_motor.JoystickToMotor'
        connect:
            joystick_logic: joystick_logic
            motor: motor_logic
    """

    # declare connectors
    joystick_logic = Connector(interface='JoystickLogic')
    motor_hardware = Connector(interface='MotorInterface')

    _button_interlock = ConfigOption('button_trigger', 'right_left')  # if this button is not pushed, do nothing
    # this must be a button from logic _button_list
    _joystick_gamma_correction = ConfigOption('joystick_gamma_correction', 2.0)  # this button can be used to change the
    # sensitivity of the axes

    _hardware_frequency = ConfigOption('hardware_frequency', 100)
    _axis = ConfigOption('axis', ('x', 'y', 'z'))
    _xy_max_velocity = ConfigOption('xy_max_velocity', 100)  # the maximum number of steps by second
    _z_max_velocity = ConfigOption('z_max_velocity', 20)  # the maximum number of steps by second

    _joystick_setpoint_position = np.zeros(3)
    _hardware_position = np.zeros(3)

    _enabled = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.joystick_logic().register(str(self), self.callback, trigger_keys={str(self._button_interlock): True})

    def on_deactivate(self):
        """ Perform required deactivation.
        """
        self.joystick_logic().unregister(str(self))

    def callback(self, state):
        """ Function called by the joystick logic """

        self.discrete_movement((0, 1, 0)) if 'left_up' in state['pressed_buttons'] else None
        self.discrete_movement((0, -1, 0)) if 'left_down' in state['pressed_buttons'] else None
        self.discrete_movement((-1, 0, 0)) if 'left_left' in state['pressed_buttons'] else None
        self.discrete_movement((1, 0, 0)) if 'left_right' in state['pressed_buttons'] else None
        self.discrete_movement((0, 0, -1)) if 'left_shoulder' in state['pressed_buttons'] else None
        self.discrete_movement((0, 0, 1)) if 'right_shoulder' in state['pressed_buttons'] else None

        x, y, z = state['axis']['left_horizontal'], state['axis']['left_vertical'], state['axis']['trigger']
        fps = self.joystick_logic().fps()
        x = self._to_relative_distance(x) / fps * self._xy_max_velocity
        y = self._to_relative_distance(y) / fps * self._xy_max_velocity
        z = self._to_relative_distance(z) / fps * self._z_max_velocity
        self.discrete_movement((x, y, z))

    def _to_relative_distance(self, value):
        """ Helper function to compute gamma correction """
        if value == 0:
            return 0
        sign = value / abs(value)
        move = abs(value) ** self._joystick_gamma_correction * sign
        return move

    def discrete_movement(self, relative_movement):
        """ Function to do a discrete relative movement """
        self._joystick_setpoint_position += relative_movement
        self._update_hardware()

    def _update_hardware(self):
        """ Eventually send command to hardware if position has changed
        """
        before = self._hardware_position
        after = np.floor(self._joystick_setpoint_position)

        difference = after - before
        changed = False
        for index, axis in enumerate(self._axis):
            if axis:
                steps = difference[int(index)]
                if steps:
                    self.motor_hardware().move_rel({axis: steps})
                    changed = True
        self._hardware_position = after
        # if changed:
        #     self.log.debug('New position ({}, {}, {})'.format(*after))
