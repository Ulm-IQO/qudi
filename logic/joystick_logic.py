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
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


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
    _hardware = None

    _max_fps = ConfigOption('max_fps', 100)
    _axis_threshold = ConfigOption('axis_threshold', 0.05)  # a smaller axis position will not trigger an event
    _fps = _max_fps

    # signals - this can not be created in a loop because Qt wants them declared like this
    sig_new_frame = QtCore.Signal()
    sig_controller_changed = QtCore.Signal()

    signal_left_up_pushed = QtCore.Signal()
    signal_left_down_pushed = QtCore.Signal()
    signal_left_left_pushed = QtCore.Signal()
    signal_left_right_pushed = QtCore.Signal()
    signal_left_shoulder_pushed = QtCore.Signal()
    signal_right_shoulder_pushed = QtCore.Signal()

    signal_right_up_pushed = QtCore.Signal()
    signal_right_down_pushed = QtCore.Signal()
    signal_right_left_pushed = QtCore.Signal()
    signal_right_right_pushed = QtCore.Signal()

    signal_left_joystick_pushed = QtCore.Signal()
    signal_right_joystick_pushed = QtCore.Signal()

    signal_middle_left_pushed = QtCore.Signal()
    signal_middle_right_pushed = QtCore.Signal()

    signal_left_vertical = QtCore.Signal()
    signal_left_horizontal = QtCore.Signal()
    signal_right_vertical = QtCore.Signal()
    signal_right_horizontal = QtCore.Signal()
    signal_left_trigger = QtCore.Signal()
    signal_right_trigger = QtCore.Signal()

    # Action may be applied only if the axis is at a maximum
    signal_left_vertical_max = QtCore.Signal()
    signal_left_horizontal_max = QtCore.Signal()
    signal_right_vertical_max = QtCore.Signal()
    signal_right_horizontal_max = QtCore.Signal()
    signal_left_trigger_max = QtCore.Signal()
    signal_right_trigger_max = QtCore.Signal()

    timer = None
    enabled = False

    _last_state = None

    _button_list = ['left_up', 'left_down', 'left_left', 'left_right', 'left_joystick',
               'right_up', 'right_down', 'right_left', 'right_right', 'right_joystick',
               'middle_left', 'middle_right', 'left_shoulder', 'right_shoulder']

    _axis_list = ['left_vertical', 'left_horizontal', 'right_vertical', 'right_horizontal',
                  'left_trigger', 'right_trigger']

    events = {}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._hardware = self.hardware()

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.loop)
        self._last_state = self._hardware.get_state()
        self.start_loop()

    def on_deactivate(self):
        """ Perform required deactivation.
        """
        self.stop_loop()
        pass

    def fps(self, value=None):
        """ Set  ou get the frequency at which the hardware is read
        """
        if value is not None:
            self._fps = value
        return self._fps

    def start_loop(self):
        """ Start the running loop.
        """
        self.enabled = True
        self.timer.start(1000*1/self._fps)

    def stop_loop(self):
        """ Stop the data recording loop.
        """
        self.timer.stop()
        self.enabled = False

    def loop(self):
        """ Loop function of the module. Get state and emit event
        """
        old_state = self._last_state
        state = self._hardware.get_state()
        changed = False
        self._last_state = state

        if not self.enabled:
            return

        for button in self._button_list:
            if state['buttons'][button] != old_state['buttons'][button]:
                changed = True
                if state['buttons'][button]:
                    if hasattr(self, 'signal_{}_pushed'.format(button)):
                        getattr(self, 'signal_{}_pushed'.format(button)).emit()

        for axis in self._axis_list:
            if state['axis'][axis] != old_state['axis'][axis]:
                changed = True
            if abs(state['axis'][axis]) > self._axis_threshold:
                getattr(self, 'signal_{}'.format(axis)).emit()
            if abs(state['axis'][axis]) >= 1:
                getattr(self, 'signal_{}_max'.format(axis)).emit()

        if changed:
            self.sig_controller_changed.emit()
        self.sig_new_frame.emit()

        self.timer.start(1000 * 1 / self._fps)

    def get_last_state(self):
        """ Return last acquired state
        """
        return self._last_state

    def get_fps(self):
        """ Return the frequency of controller request
        """
        return self._fps
