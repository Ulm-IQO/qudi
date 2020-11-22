# -*- coding: utf-8 -*-

"""
Laser management.

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

import time
import numpy as np
from PySide2 import QtCore

from qudi.core import qudi_slot
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.interface.simple_laser_interface import ControlMode, ShutterState, LaserState


class LaserLogic(LogicBase):
    """ ToDo: Document
    """

    _laser = Connector(name='laser', interface='SimpleLaserInterface')

    # waiting time between queries im seconds
    _query_interval = ConfigOption(name='query_interval', default=0.2)
    _buffer_length = ConfigOption(name='buffer_length', default=100)

    sigPowerSetpointChanged = QtCore.Signal(float, object)
    sigCurrentSetpointChanged = QtCore.Signal(float, object)
    sigControlModeChanged = QtCore.Signal(object)
    sigLaserStateChanged = QtCore.Signal(object)
    sigShutterStateChanged = QtCore.Signal(object)
    sigDataChanged = QtCore.Signal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()

        self.__timer = None
        self._stop_requested = True

        # data buffer
        self._data = dict()
        self._last_shutter_state = None
        self._last_laser_state = None
        self._last_power_setpoint = None
        self._last_current_setpoint = None
        self._last_control_mode = None

    def on_activate(self):
        """ Prepare logic module for work.
        """
        # delay timer for querying laser
        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(1000 * self._query_interval)
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self._query_loop_body, QtCore.Qt.QueuedConnection)

        # initialize data buffer
        laser = self._laser()
        allowed_modes = laser.allowed_control_modes()
        self._data = {name: np.zeros(self._buffer_length) for name in laser.get_temperatures()}
        self._data['time'] = time.time() - np.arange(self._buffer_length)[::-1] * self._query_interval
        if ControlMode.POWER in allowed_modes:
            self._data['power'] = np.zeros(self._buffer_length)
        else:
            self._data['power'] = None
        if ControlMode.CURRENT in allowed_modes:
            self._data['current'] = np.zeros(self._buffer_length)
        else:
            self._data['current'] = None
        self._last_shutter_state = laser.get_shutter_state()
        self._last_laser_state = laser.get_laser_state()
        self._last_power_setpoint = laser.get_power_setpoint()
        self._last_current_setpoint = laser.get_current_setpoint()
        self._last_control_mode = laser.get_control_mode()

        # start timed query loop
        QtCore.QTimer.singleShot(0, self.start_query_loop)

    def on_deactivate(self):
        """ Deactivate module
        """
        self.stop_query_loop()
        for i in range(5):
            time.sleep(self._query_interval)
            QtCore.QCoreApplication.processEvents()

    @property
    def allowed_control_modes(self):
        with self._thread_lock:
            return self._laser().allowed_control_modes()

    @property
    def extra_info(self):
        with self._thread_lock:
            return self._laser().get_extra_info()

    @property
    def current_range(self):
        with self._thread_lock:
            return self._laser().get_current_range()

    @property
    def power_range(self):
        with self._thread_lock:
            return self._laser().get_power_range()

    @property
    def current_unit(self):
        with self._thread_lock:
            return self._laser().get_current_unit()

    @property
    def data(self):
        return self._data.copy()

    @property
    def temperatures(self):
        with self._thread_lock:
            return self._laser().get_temperatures()

    @property
    def laser_state(self):
        with self._thread_lock:
            self._last_laser_state = self._laser().get_laser_state()
            return self._last_laser_state

    @laser_state.setter
    def laser_state(self, state):
        self.set_laser_state(state)

    @property
    def shutter_state(self):
        with self._thread_lock:
            self._last_shutter_state = self._laser().get_shutter_state()
            return self._last_shutter_state

    @shutter_state.setter
    def shutter_state(self, state):
        self.set_shutter_state(state)

    @property
    def power(self):
        with self._thread_lock:
            return self._laser().get_power()

    @property
    def power_setpoint(self):
        with self._thread_lock:
            self._last_power_setpoint = self._laser().get_power_setpoint()
            return self._last_power_setpoint

    @power_setpoint.setter
    def power_setpoint(self, value):
        self.set_power(value)

    @property
    def current(self):
        with self._thread_lock:
            return self._laser().get_current()

    @property
    def current_setpoint(self):
        with self._thread_lock:
            self._last_current_setpoint = self._laser().get_current_setpoint()
            return self._last_current_setpoint

    @current_setpoint.setter
    def current_setpoint(self, value):
        self.set_current(value)

    @property
    def control_mode(self):
        with self._thread_lock:
            self._last_control_mode = self._laser().get_control_mode()
            return self._last_control_mode

    @control_mode.setter
    def control_mode(self, mode):
        self.set_control_mode(mode)

    @qudi_slot()
    def _query_loop_body(self):
        """ Get power, current, shutter state and temperatures from laser. """
        with self._thread_lock:
            if self.module_state() != 'locked':
                return

            laser = self._laser()
            # Check if settings have changed by e.g. a device front panel
            try:
                laser_state = laser.get_laser_state()
                if laser_state != self._last_laser_state:
                    self._last_laser_state = laser_state
                    self.sigLaserStateChanged.emit(self._last_laser_state)
            except:
                pass
            try:
                shutter_state = laser.get_shutter_state()
                if shutter_state != self._last_shutter_state:
                    self._last_shutter_state = shutter_state
                    self.sigShutterStateChanged.emit(self._last_shutter_state)
            except:
                pass
            try:
                power_setpoint = laser.get_power_setpoint()
                if power_setpoint != self._last_power_setpoint:
                    self._last_power_setpoint = power_setpoint
                    self.sigPowerSetpointChanged.emit(self._last_power_setpoint, None)
            except:
                pass
            try:
                current_setpoint = laser.get_current_setpoint()
                if current_setpoint != self._last_current_setpoint:
                    self._last_current_setpoint = current_setpoint
                    self.sigCurrentSetpointChanged.emit(self._last_current_setpoint, None)
            except:
                pass
            try:
                control_mode = laser.get_control_mode()
                if control_mode != self._last_control_mode:
                    self._last_control_mode = control_mode
                    self.sigControlModeChanged.emit(self._last_control_mode, None)
            except:
                pass
            # Read current, power and temperature values and put them in the data buffer
            try:
                temperatures = laser.get_temperatures()
                current = laser.get_current()
                power = laser.get_power()
                curr_time = time.time()
            except:
                self.log.exception('Exception in laser data query. Stopping laser polling.')
            else:
                self._data['time'] = np.roll(self._data['time'], -1)
                self._data['time'][-1] = curr_time
                for name, temp in temperatures.items():
                    self._data[name] = np.roll(self._data[name], -1)
                    self._data[name][-1] = temp
                if self._data['power'] is not None:
                    self._data['power'] = np.roll(self._data['power'], -1)
                    self._data['power'][-1] = power
                if self._data['current'] is not None:
                    self._data['current'] = np.roll(self._data['current'], -1)
                    self._data['current'][-1] = current

                self.sigDataChanged.emit(self.data)
                self.__timer.start()

    @qudi_slot()
    def start_query_loop(self):
        """ Start the readout loop. """
        if self.thread() is not QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'start_query_loop',
                                            QtCore.Qt.BlockingQueuedConnection)
            return

        with self._thread_lock:
            if self.module_state() == 'idle':
                self.module_state.lock()
                self.__timer.start()

    @qudi_slot()
    def stop_query_loop(self):
        """ Stop the readout loop. """
        if self.thread() is not QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'stop_query_loop',
                                            QtCore.Qt.BlockingQueuedConnection)
            return

        with self._thread_lock:
            if self.module_state() == 'locked':
                self.__timer.stop()
                self.module_state.unlock()

    @qudi_slot(object)
    def set_control_mode(self, mode):
        """ Change whether the laser output is controlled by current or power setpoint
        """
        with self._thread_lock:
            if mode is ControlMode.UNKNOWN or mode not in self.allowed_control_modes:
                self.log.error(f'Invalid control mode "{mode}" for laser encountered.')
            else:
                try:
                    self._laser().set_control_mode(mode)
                except:
                    self.log.exception('Error while setting laser control mode:')
            self.sigControlModeChanged.emit(self.control_mode)

    @qudi_slot(object)
    def set_laser_state(self, state):
        """ Turn laser on or off
        """
        with self._thread_lock:
            try:
                state = LaserState(state)
            except ValueError:
                self.log.error(f'Invalid laser state to set: "{state}"')
            else:
                try:
                    self._laser().set_laser_state(state)
                except:
                    self.log.exception('Error while setting laser state:')
            self.sigLaserStateChanged.emit(self.laser_state)

    @qudi_slot(object)
    def set_shutter_state(self, state):
        """ Open or close the laser shutter
        """
        with self._thread_lock:
            if state in (ShutterState.OPEN, ShutterState.CLOSED):
                try:
                    self._laser().set_shutter_state(state)
                except:
                    self.log.exception('Error while setting shutter state:')
            else:
                self.log.error(f'Invalid shutter state to set: "{state}"')
            self.sigShutterStateChanged.emit(self.shutter_state)

    @qudi_slot(float, object)
    def set_power(self, power, caller_id=None):
        """ Set laser output power """
        with self._thread_lock:
            self._laser().set_power(power)
            self.sigPowerSetpointChanged.emit(self.power_setpoint, caller_id)

    @qudi_slot(float, object)
    def set_current(self, current, caller_id=None):
        """ Set laser (diode) current """
        with self._thread_lock:
            self._laser().set_current(current)
            self.sigCurrentSetpointChanged.emit(self.current_setpoint, caller_id)
