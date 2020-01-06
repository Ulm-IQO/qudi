# -*- coding: utf-8 -*-

"""
A module for that listen to joystick events and act on the confocal logic based on this events

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
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class JoystickToConfocal(GenericLogic):
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
    _modclass = 'joysticklogicconfocal'
    _modtype = 'logic'

    # declare connectors
    joystick_logic = Connector(interface='JoystickLogic')
    confocal = Connector(interface='ConfocalLogic')

    _button_step_ratio = ConfigOption('button_step_ratio', .01)  # a button push mean 1% of total range displacement
    _max_speed = ConfigOption('max_speed', 100e-6)  # the maximum speed in m/s
    _button_interlock = ConfigOption('button_trigger', 'right_up')  # if this button is not pushed, do nothing
    # this must be a button from logic _button_list
    _joystick_gamma_correction = ConfigOption('joystick_gamma_correction', 2.0)  # this button can be used to change the
    # sensitivity of the axes

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

        self.do_step('x', -1) if 'left_left' in state['pressed_buttons'] else None
        self.do_step('x', 1) if 'left_right' in state['pressed_buttons'] else None
        self.do_step('y', -1) if 'left_down' in state['pressed_buttons'] else None
        self.do_step('y', 1) if 'left_up' in state['pressed_buttons'] else None
        self.do_step('z', -1) if 'left_shoulder' in state['pressed_buttons'] else None
        self.do_step('z', 1) if 'right_shoulder' in state['pressed_buttons'] else None
        if 'middle_left' in state['pressed_buttons']:
            self.confocal().start_scanning(zscan=False, tag='joystick')
        if 'middle_right' in state['pressed_buttons']:
            self.confocal().stop_scanning()
        if state['axis']['left_horizontal'] != 0:
            self.do_move('x', state['axis']['left_horizontal'])
        if state['axis']['left_vertical'] != 0:
            self.do_move('y', state['axis']['left_vertical'])
        if state['axis']['trigger'] != 0:
            self.do_move('z', state['axis']['trigger'])

    def do_step(self, axis, direction=1):
        """ Function called when a button is pushed and should act on a position """
        step = self.get_step(axis, direction)
        position = self.confocal().get_position_dict()
        position[axis] += step
        self.confocal().set_position('joystick_button', **position)

    def do_move(self, axis, value):
        """ Function called when a joystick is moved to move the scanner position """
        position = self.confocal().get_position_dict()
        sign = value / abs(value)
        move = abs(value) ** self._joystick_gamma_correction * sign
        position[axis] += self._max_speed / self.joystick_logic().fps() * move
        self.confocal().set_position('joystick_axis', **position)

    def get_step(self, axis, direction=1):
        """ Helper function do compute the step for a given axis and a given direction """
        scanner_range = getattr(self.confocal(), '{}_range'.format(axis))
        step = (scanner_range[1] - scanner_range[0]) * self._button_step_ratio
        step = step * direction
        return step
