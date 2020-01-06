# -*- coding: utf-8 -*-

"""
A module for that listen to joystick events and act on the poi manager

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


class JoystickToPOI(GenericLogic):
    """ This logic module get callbacks from joystick logic and interact with the POI manager based on these events

    This module needs optimizer_logic to function

    To prevent accidentally changing things, module only act if some 'trigger_keys' are pushed.

    Example configuration :
        connector_joystick_poi:
        module.Class: 'logic_connectors.joystick_to_poi.JoystickToPOI'
        connect:
            joystick_logic: 'joystick_logic'
            poi_manager: 'poimanager'
    """
    _modclass = 'joysticklogicpoi'
    _modtype = 'logic'

    # declare connectors
    joystick_logic = Connector(interface='JoystickLogic')
    poi_manager = Connector(interface='PoiManagerLogic')

    _button_interlock = ConfigOption('button_trigger', 'right_down')  # if this button is not pushed, do nothing

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

        if ('left_shoulder' in state['pressed_buttons'] and state['buttons']['right_shoulder']) or \
                ('right_shoulder' in state['pressed_buttons'] and state['buttons']['left_shoulder']):
            self.poi_manager().optimise_poi_position()
