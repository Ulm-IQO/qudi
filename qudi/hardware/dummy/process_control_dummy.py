# -*- coding: utf-8 -*-

"""
This file contains the Qudi dummy hardware file to mimic a simple process control device via
ProcessControlInterface.

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
from qudi.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption
from qudi.interface.process_control_interface import ProcessControlConstraints
from qudi.interface.process_control_interface import ProcessSetpointInterface
from qudi.interface.process_control_interface import ProcessValueInterface


class ProcessControlDummy(ProcessSetpointInterface, ProcessValueInterface):
    """ A dummy class to emulate a process control device (setpoints and process values)

    Example config for copy-paste:

    process_control_dummy:
        module.Class: 'dummy.process_control_dummy.ProcessControlDummy'
        process_value_channels:
            Temperature:
                unit: 'K'
                limits: [0, .inf]
                dtype: float
            Voltage:
                unit: 'V'
                limits: [-10.0, 10.0]
                dtype: float
        setpoint_channels:
            Power:
                unit: 'dBm'
                limits: [-120.0, 30.0]
                dtype: float
            Frequency:
                unit: 'Hz'
                limits: [100.0e3, 20.0e9]
                dtype: float
    """

    _setpoint_channels = ConfigOption(
        name='setpoint_channels',
        default={'Power': {'unit': 'dBm', 'limits': (-120.0, 30.0), 'dtype': float},
                 'Frequency': {'unit': 'Hz', 'limits': (100.0e3, 20.0e9), 'dtype': float}}
    )
    _process_value_channels = ConfigOption(
        name='process_value_channels',
        default={'Temperature': {'unit': 'K', 'limits': (0, np.inf), 'dtype': float},
                 'Voltage': {'unit': 'V', 'limits': (-10.0, 10.0), 'dtype': float}}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = RecursiveMutex()

        # setpoints
        self._setpoints = dict()
        # internal variables
        self._is_active = False
        self.__constraints = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._is_active = False
        units = {ch: d['unit'] for ch, d in self._setpoint_channels.items() if 'unit' in d}
        units.update({ch: d['unit'] for ch, d in self._process_value_channels.items() if 'unit' in d})
        limits = {ch: d['limits'] for ch, d in self._setpoint_channels.items() if 'limits' in d}
        limits.update({ch: d['limits'] for ch, d in self._process_value_channels.items() if 'limits' in d})
        dtypes = {ch: d['dtype'] for ch, d in self._setpoint_channels.items() if 'dtype' in d}
        dtypes.update({ch: d['dtype'] for ch, d in self._process_value_channels.items() if 'dtype' in d})
        self.__constraints = ProcessControlConstraints(
            setpoint_channels=tuple(self._setpoint_channels),
            process_channels=tuple(self._process_value_channels),
            units=units,
            limits=limits,
            dtypes=dtypes
        )
        self._setpoints = {ch: min(max(lim[0], 0), lim[1]) for ch, lim in
                           self.__constraints.channel_limits.items() if
                           ch in self._setpoint_channels}

    def on_deactivate(self):
        pass

    @property
    def constraints(self):
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.

        @return ProcessControlConstraints: Hardware constraints
        """
        return self.__constraints

    @property
    def is_active(self):
        """ Current activity state.
        State is bool type and refers to active (True) and inactive (False).

        @return bool: Activity state (active: True, inactive: False)
        """
        with self._thread_lock:
            return self._is_active

    @is_active.setter
    def is_active(self, active):
        """ Set activity state.
        State is bool type and refers to active (True) and inactive (False).

        @param bool active: Activity state to set (active: True, inactive: False)
        """
        self.set_activity_state(active)

    @property
    def process_values(self):
        """ Read-Only property returning a snapshot of current process values for all channels.

        @return dict: Snapshot of the current process values (values) for all channels (keys)
        """
        return {ch: self.get_process_value(ch) for ch in self.__constraints.process_channels}

    @property
    def setpoints(self):
        """ The current setpoints for all channels.

        @return dict: Currently set target values (values) for all channels (keys)
        """
        with self._thread_lock:
            return self._setpoints.copy()

    @setpoints.setter
    def setpoints(self, values):
        """ Set the setpoints for all channels at once.

        @param dict values: Target values (values) to set for all channels (keys)
        """
        assert set(values).issubset(self._setpoints), \
            f'Invalid setpoint channels encountered. Valid channels are: {set(self._setpoints)}'
        assert all(self.__constraints.channel_value_in_range(v, ch)[0] for ch, v in
                   values.items()), 'One or more setpoints out of allowed value bounds'
        with self._thread_lock:
            for channel, value in values.items():
                self._setpoints[channel] = self.__constraints.channel_dtypes[channel](value)

    def set_activity_state(self, active):
        """ Set activity state. State is bool type and refers to active (True) and inactive (False).

        @param bool active: Activity state to set (active: True, inactive: False)
        """
        assert isinstance(active, bool), '<is_active> flag must be bool type'
        with self._thread_lock:
            if active != self._is_active:
                time.sleep(0.5)
                self._is_active = active
                if active and self.module_state() != 'locked':
                    self.module_state.lock()
                elif not active and self.module_state() == 'locked':
                    self.module_state.unlock()

    def get_process_value(self, channel):
        """ Get current process value for a single channel.

        @param str channel: Channel to get the process value for
        @return float|int: The current process value for <channel>
        """
        assert channel in self.__constraints.process_channels, \
            f'Invalid process channel "{channel}" encountered. Valid channels are: ' \
            f'{self.__constraints.process_channels}'
        # Return random sample from allowed value range
        min_val, max_val = self.__constraints.channel_limits[channel]
        if min_val == -np.inf:
            min_val = -1000
        if max_val == np.inf:
            max_val = 1000
        value_span = max_val - min_val
        return min_val + np.random.rand() * value_span

    def set_setpoint(self, value, channel):
        """ Set new setpoint for a single channel.

        @param float|int value: Setpoint value to set
        @param str channel: Channel to set
        """
        assert channel in self._setpoints, \
            f'Invalid setpoint channel "{channel}" encountered. Valid channels are: ' \
            f'{set(self._setpoints)}'
        assert self.__constraints.channel_value_in_range(value, channel)[0], \
            'Setpoint out of allowed value bounds'
        with self._thread_lock:
            self._setpoints[channel] = self.__constraints.channel_dtypes[channel](value)

    def get_setpoint(self, channel):
        """ Get current setpoint for a single channel.

        @param str channel: Channel to get the setpoint for
        @return float|int: The current setpoint for <channel>
        """
        assert channel in self._setpoints, f'Invalid setpoint channel "{channel}" encountered.' \
                                           f' Valid channels are: {set(self._setpoints)}'
        with self._thread_lock:
            return self._setpoints[channel]


class ProcessSetpointDummy(ProcessControlDummy):
    """ A dummy class to emulate a process setpoint device.

    Example config for copy-paste:

    process_setpoint_dummy:
        module.Class: 'dummy.process_control_dummy.ProcessSetpointDummy'
        setpoint_channels:
            Power:
                unit: 'dBm'
                limits: [-120.0, 30.0]
                dtype: float
            Frequency:
                unit: 'Hz'
                limits: [100.0e3, 20.0e9]
                dtype: float
    """
    _process_value_channels = ConfigOption(name='process_value_channels', default=dict())


class ProcessValueDummy(ProcessControlDummy):
    """ A dummy class to emulate a process value reading device.

    Example config for copy-paste:

    process_value_dummy:
        module.Class: 'dummy.process_control_dummy.ProcessValueDummy'
        process_value_channels:
            Temperature:
                unit: 'K'
                limits: [0, .inf]
                dtype: float
            Voltage:
                unit: 'V'
                limits: [-10.0, 10.0]
                dtype: float
    """
    _setpoint_channels = ConfigOption(name='setpoint_channels', default=dict())
