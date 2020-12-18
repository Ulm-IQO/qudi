# -*- coding: utf-8 -*-

"""
This file contains the qudi hardware module to use a National Instruments 9263 Analog output module

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

import numpy as np
import nidaqmx as ni

from core.module import Base
from core.configoption import ConfigOption

from interface.process_control_interface import ProcessControlInterface


class NIAnalogOutput(Base, ProcessControlInterface):
    """ A module to interface a National Instruments device that can apply an anlog output +/- 10 V on 4 channels

    Tested with : NI9263 connected via USB cDAQ-9171

    Example config :

    ni_analog_output:
        module.Class: 'ni_analog_output.NIAnalogOutput'
        device_name: 'cDAQ1Mod1' # optional
        voltage_limits: [[-10, 10], [-10, 10], [-10, 10], [-10, 10]] # optional
    """

    _device_name = ConfigOption(name='device_name', default='cDAQ1Mod1')
    _voltage_limits_config = ConfigOption('voltage_limits', default=[[-10, 10], [-10, 10], [-10, 10], [-10, 10]])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._system = None
        self._device = None
        self._output_number = None
        self._tasks = None
        self._voltage_limits = None
        self._current_state = None

    def on_activate(self):
        """ Starts up the NI-card and performs sanity checks. """
        # Device check
        self._system = ni.system.System.local()
        device_names = self._system.devices.device_names
        if self._device_name not in device_names:
            self.log.error('Device "{0}" not found in connected devices: {1}'.format(self._device_name, device_names))
        self._device = self._system.devices[self._device_name]
        self._output_number = len(self._device.ao_physical_chans)
        # Config check
        self._voltage_limits = np.array(self._voltage_limits_config)
        if self._voltage_limits.shape != (self._output_number, 2):
            self.log.error('Hardware has {} analog output. Config limits specifies {}.'.format(
                                self._output_number, self._voltage_limits.shape[0]))
        self._tasks = []
        for i, channel in enumerate(self._device.ao_physical_chans):
            task = ni.Task()
            task.ao_channels.add_ao_voltage_chan(channel.name,
                                                 min_val=self._voltage_limits[i, 0], max_val=self._voltage_limits[i, 1])
            self._tasks.append(task)
        self._current_state = np.zeros(self._output_number)

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        for task in self._tasks:
            task.write(0)
            task.close()
        self._current_state[:] = 0

    def set_control_value(self, value, channel=0):
        """ Set the voltage on an analog output channel """
        self._tasks[channel].write(value)
        self._current_state[channel] = value

    def get_control_value(self, channel=None):
        """ Get the voltage on an analog output channel

         NI API does not give any getter for current state so value is stored by the hardware module.
         """
        return self._current_state[channel]

    def get_control_unit(self, channel=None):
        """ Return the unit that the value is set in as a tuple of ('abbreviation', 'full unit name')"""
        return 'V', 'Volt'

    def get_control_limit(self, channel=0):
        """ Return limits within which the controlled value can be set as a tuple of (low limit, high limit) """
        return self._voltage_limits[channel]

    def process_control_supports_multiple_channels(self):
        """ Function to test if hardware support multiple channels """
        return True

    def process_control_get_number_channels(self):
        """ Function to get the number of channels available for control """
        return self._output_number
