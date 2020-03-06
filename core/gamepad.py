# -*- coding: utf-8 -*-

"""
This module adds gamepad support for Windows systems (using DirectX).

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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""

import XInput
from enum import IntEnum

from qtpy import QtWidgets, QtCore, QtTest


class GamepadButton(IntEnum):
    SOUTH = XInput.BUTTON_A
    EAST = XInput.BUTTON_B
    NORTH = XInput.BUTTON_Y
    WEST = XInput.BUTTON_X
    DPAD_DOWN = XInput.BUTTON_DPAD_DOWN
    DPAD_RIGHT = XInput.BUTTON_DPAD_RIGHT
    DPAD_UP = XInput.BUTTON_DPAD_UP
    DPAD_LEFT = XInput.BUTTON_DPAD_LEFT
    SHOULDER_LEFT = XInput.BUTTON_LEFT_SHOULDER
    SHOULDER_RIGHT = XInput.BUTTON_RIGHT_SHOULDER
    THUMB_LEFT = XInput.BUTTON_LEFT_THUMB
    THUMB_RIGHT = XInput.BUTTON_RIGHT_THUMB
    START = XInput.BUTTON_START
    BACK = XInput.BUTTON_BACK


class GamepadTrigger(IntEnum):
    LEFT = XInput.LEFT
    RIGHT = XInput.RIGHT


class GamepadStick(IntEnum):
    LEFT = XInput.LEFT
    RIGHT = XInput.RIGHT


class GamepadEvent(IntEnum):
    BUTTON_PRESSED = XInput.EVENT_BUTTON_PRESSED
    BUTTON_RELEASED = XInput.EVENT_BUTTON_RELEASED
    STICK_MOVED = XInput.EVENT_STICK_MOVED
    TRIGGER_MOVED = XInput.EVENT_TRIGGER_MOVED
    CONNECTED = XInput.EVENT_CONNECTED
    DISCONNECTED = XInput.EVENT_DISCONNECTED


class GamepadEventHandler(QtCore.QObject):
    """

    """
    sigGamepadEvent = QtCore.Signal(object)

    __key_mapping = {XInput.BUTTON_A: QtCore.Qt.Key_A,
                     XInput.BUTTON_B: QtCore.Qt.Key_B,
                     XInput.BUTTON_Y: QtCore.Qt.Key_Y,
                     XInput.BUTTON_X: QtCore.Qt.Key_X,
                     XInput.BUTTON_DPAD_DOWN: QtCore.Qt.Key_Down,
                     XInput.BUTTON_DPAD_RIGHT: QtCore.Qt.Key_Right,
                     XInput.BUTTON_DPAD_UP: QtCore.Qt.Key_Up,
                     XInput.BUTTON_DPAD_LEFT: QtCore.Qt.Key_Left,
                     XInput.BUTTON_LEFT_SHOULDER: QtCore.Qt.Key_Q,
                     XInput.BUTTON_RIGHT_SHOULDER: QtCore.Qt.Key_E,
                     XInput.BUTTON_LEFT_THUMB: QtCore.Qt.Key_L,
                     XInput.BUTTON_RIGHT_THUMB: QtCore.Qt.Key_R,
                     XInput.BUTTON_START: QtCore.Qt.Key_Enter}

    def __init__(self, fps=1000, map_to_keyboard=True, parent=None):
        super().__init__(parent=parent)

        self._timer = QtCore.QTimer(self)
        self.map_to_keyboard = bool(map_to_keyboard)
        self._running = False
        self._time_delta = None
        self.frame_rate = fps
        self._timer.timeout.connect(self._handle_events, QtCore.Qt.QueuedConnection)

    @property
    def frame_rate(self):
        return 1. / self._time_delta

    @frame_rate.setter
    def frame_rate(self, new_rate):
        if new_rate > 1000:
            raise Exception(
                'It is impossible to increase the gamepad input frame rate beyond 1 kHz')
        was_running = self._running
        if was_running:
            self.stop()
        interval_ms = int(round(1000. / new_rate))
        self._time_delta = interval_ms / 1000.
        self._timer.setInterval(interval_ms)
        if was_running:
            self.start()

    @property
    def is_running(self):
        return self._running

    @property
    def gamepad_connected(self):
        return bool(self.connected_ids)

    @property
    def connected_ids(self):
        return tuple(ii for ii, connected in enumerate(XInput.get_connected()) if connected)

    @QtCore.Slot()
    def start(self):
        if self.thread() != QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self, 'start', QtCore.Qt.BlockingQueuedConnection)
            return
        self._running = True
        if not self._timer.isActive():
            self._timer.start()

    @QtCore.Slot()
    def stop(self):
        if self.thread() != QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self._timer, 'stop', QtCore.Qt.QueuedConnection)
            return
        self._running = False
        if self._timer.isActive():
            self._timer.stop()

    @QtCore.Slot()
    def _handle_events(self):
        if self._running:
            for event in XInput.get_events():
                if event.type == XInput.EVENT_STICK_MOVED:
                    self.process_stick_event(event)
                elif event.type in (XInput.EVENT_BUTTON_PRESSED, XInput.EVENT_BUTTON_RELEASED):
                    self.process_button_event(event)
                elif event.type == XInput.EVENT_TRIGGER_MOVED:
                    self.process_trigger_event(event)
                elif event.type in (XInput.EVENT_CONNECTED, XInput.EVENT_DISCONNECTED):
                    self.process_connection_event(event)

    def process_button_event(self, event):
        if self.map_to_keyboard and event.button_id in self.__key_mapping:
            window = QtWidgets.QApplication.activeWindow()
            if window:
                if event.type == XInput.EVENT_BUTTON_PRESSED:
                    QtTest.QTest.keyPress(window, self.__key_mapping[event.button_id])
                elif event.type == XInput.EVENT_BUTTON_RELEASED:
                    QtTest.QTest.keyRelease(window, self.__key_mapping[event.button_id])
        else:
            self.sigGamepadEvent.emit(event)

    def process_stick_event(self, event):
        event.timedelta_ms = self._time_delta  # Inject timedelta
        self.sigGamepadEvent.emit(event)

    def process_trigger_event(self, event):
        event.timedelta_ms = self._time_delta  # Inject timedelta
        self.sigGamepadEvent.emit(event)

    def process_connection_event(self, event):
        if event.type == XInput.EVENT_CONNECTED:
            print('Gamepad connected with ID: {0:d}'.format(event.user_index))
        elif event.type == XInput.EVENT_DISCONNECTED:
            print('Gamepad disconnected with ID: {0:d}'.format(event.user_index))
