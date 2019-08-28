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

from core.module import Connector, ConfigOption
from logic.generic_logic import GenericLogic
import numpy as np
import time


class JoystickToSteppers(GenericLogic):
    """ This logic module get callbacks from joystick logic and interact with confocal logic based on these events

    This module needs joystick_logic to function

    To prevent accidentally changing things, module only act if some 'trigger_keys' are pushed.

    Example configuration :
        connector_joystick_confocal:
        module.Class: 'logic_connectors.joystick_to_confocal.JoystickToConfocal'
        connect:
            joystick_logic: joystick_logic
            confocal: scanner
    """

    # declare connectors
    joystick_logic = Connector(interface='JoystickLogic')
    hardware = Connector(interface='SteppersInterface')

    _button_interlock = ConfigOption('button_trigger', 'right_left')  # if this button is not pushed, do nothing
    # this must be a button from logic _button_list
    _joystick_gamma_correction = ConfigOption('joystick_gamma_correction', 2.0)  # this button can be used to change the
    # sensitivity of the axes

    _hardware_frequency = ConfigOption('hardware_frequency', 100)
    _hardware_voltage = ConfigOption('hardware_voltage', 30)
    _axis = ConfigOption('axis', ('x', 'y', 'z'))
    _xy_max_velocity = ConfigOption('xy_max_velocity', 100)  # the maximum number of steps by second
    _z_max_velocity = ConfigOption('z_max_velocity', 20)  # the maximum number of steps by second

    _joystick_setpoint_position = np.zeros(3)
    _hardware_position = np.zeros(3)

    _enabled = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.setup_axis()
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
        power = self._joystick_gamma_correction
        fps = self.joystick_logic().fps()
        x = x**power / fps * self._xy_max_velocity
        y = y**power / fps * self._xy_max_velocity
        z = z**power / fps * self._z_max_velocity
        self.discrete_movement((x, y, z))

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
                    self.hardware().steps(axis, steps)
                    changed = True
        self._hardware_position = after
        # if changed:
        #     self.log.debug('New position ({}, {}, {})'.format(*after))

    def setup_axis(self):
        """ Set axis as in config file"""
        for axis in self._axis:
            if axis:
                self.hardware().frequency(axis, self._hardware_frequency)
                self.hardware().voltage(axis, self._hardware_voltage)

    def hello(self):
        """ Greet humans properly """

        axis = self._axis[0]
        notes = {'c': 261, 'd': 294, 'e': 329, 'f': 349, 'g': 391, 'gS': 415, 'a': 440, 'aS': 455, 'b': 466, 'cH': 523,
                 'cSH': 554, 'dH': 587, 'dSH': 622, 'eH': 659, 'fH': 698, 'fSH': 740, 'gH': 784, 'gSH': 830, 'aH': 880}

        first_section = [('a', 500), ('a', 500), ('a', 500), ('f', 350), ('cH', 150), ('a', 500), ('f', 350),
                         ('cH', 150), ('a', 650), ('', 500), ('eH', 500), ('eH', 500), ('eH', 500), ('fH', 350),
                         ('cH', 150), ('gS', 500), ('f', 350), ('cH', 150), ('a', 650), ('', 500)]
        second_section = [('aH', 500), ('a', 300), ('a', 150), ('aH', 500), ('gSH', 325), ('fSH', 125), ('fH', 125),
                          ('fSH', 250), ('', 325), ('aS', 250), ('dSH', 500), ('dH', 325), ('cSH', 175), ('cH', 125),
                          ('b', 125), ('cH', 250), ('', 350)]
        variant_1 = [('f', 250), ('gS', 500), ('f', 350), ('a', 125), ('cH', 500), ('a', 375), ('cH', 125), ('eH', 650),
                     ('', 500)]
        variant_2 = [('f', 250), ('gS', 500), ('f', 375), ('cH', 125), ('a', 500), ('f', 375), ('cH', 125), ('a', 650),
                     ('', 650)]
        total = first_section + second_section + variant_1 + second_section + variant_2
        count = 0
        up = True
        for note, duration in total:
            if note != '':
                frequency = notes[note]
                steps = int(frequency * (float(duration)/1000.))
                self.hardware().frequency(axis, frequency)
                if not up:
                    steps = -steps
                count += steps
                self.hardware().steps(axis, steps)
            time.sleep((duration + 50)/1000)
            up = not up
        self.hardware().steps(axis, -count)  # Back to origin
