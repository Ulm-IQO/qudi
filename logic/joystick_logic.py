# -*- coding: utf-8 -*-

"""
A module for reading a joystick controller via joystick itnerface.

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
import time


class JoystickLogic(GenericLogic):
    """ This logic module get data from a hardware controller and emit signals based on input

    This module should be between the hardware and other logic modules

    Example configuration :
        joystick_logic:
        module.Class: 'joystick_logic.JoystickLogic'
        max_fps: 100
        connect:
            hardware: dummy_joystick
    """
    _modclass = 'joysticklogic'
    _modtype = 'logic'

    # declare connectors
    hardware = Connector(interface='JoystickInterface')

    _max_fps = ConfigOption('max_fps', 100)
    _axis_threshold = ConfigOption('axis_threshold', 0.05)  # a smaller axis position will not trigger an event
    _fps = _max_fps

    enabled = False

    _last_state = None

    _button_list = ['left_up', 'left_down', 'left_left', 'left_right', 'left_joystick',
               'right_up', 'right_down', 'right_left', 'right_right', 'right_joystick',
               'middle_left', 'middle_right', 'left_shoulder', 'right_shoulder']

    _axis_list = ['left_vertical', 'left_horizontal', 'right_vertical', 'right_horizontal',
                  'left_trigger', 'right_trigger']

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._module_list_listening = {}

        self.enabled = True
        self._last_state = self.hardware().get_state()
        self.loop()

    def on_deactivate(self):
        """ Perform required deactivation.
        """
        self.stop_loop()
        self._module_list_listening = {}
        pass

    def fps(self, value=None):
        """ Set ou get the frequency at which the hardware is read
        """
        if value is not None:
            self._fps = value
        return self._fps

    def stop_loop(self):
        """ Stop the data recording loop.
        """
        self.enabled = False

    def loop(self):
        """ Loop function of the module. Get state and emit event
        """
        old_state = self._last_state
        state = self.hardware().get_state()
        self._last_state = state

        if not self.enabled:
            return

        # First this look at button pressed/released and creates an easily accessible list
        state['pressed_buttons'] = []
        state['released_buttons'] = []
        for button in self._button_list:
            if state['buttons'][button] != old_state['buttons'][button]:
                if state['buttons'][button]:
                    state['pressed_buttons'].append(button)
                else:
                    state['released_buttons'].append(button)

        # Secondly, this look at the modules who are listening and tell the one who have to be triggered
        for module_key in self._module_list_listening:
            module = self._module_list_listening[module_key]

            module_triggered = True
            for trigger_key in module.trigger_keys:
                if state['buttons'][trigger_key] != module.trigger_keys[trigger_key]:
                    module_triggered = False

            if module_triggered:
                module['callback'](state)

        time.sleep(1*self._fps)

    def get_last_state(self):
        """ Return last acquired state
        """
        return self._last_state

    # def calibrate(self, calibration_time=1, calibration_fps=100):
    #     """ Function to calibrate the axis zeros
    #
    #     Execute this function while not touching the controller to calibrate it.
    #
    #     """
    #     elapsed_time = 0
    #     n = 0
    #     while elapsed_time < calibration_time:
    #         state = self._hardware.get_state()
    #         time.sleep(1/calibration_fps)
    #         elapsed_time += 1/calibration_fps
    #     #TODO
