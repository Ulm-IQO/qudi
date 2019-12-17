# -*- coding: utf-8 -*-
"""
This module interface for a Yenista Optics / Exfo T100S_HP tunable_laser

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
import visa
from core.module import Base
from core.configoption import ConfigOption
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import LaserState
from interface.simple_laser_interface import ShutterState
from interface.simple_laser_interface import ControlMode


class TunableLaser(Base, SimpleLaserInterface):
    """ Module to interface for a Yenista Optics / Exfo T100S_HP tunable_laser

    Example config for copy-paste:

    laser_tunable:
        module.Class: 'laser_tunable.T100S_HP.TunableLaser'

    """

    _connection_type = ConfigOption('connection_type', 'GPIB', missing='warn')
    _physical_interface = ConfigOption('physical_interface')
    _timeout = ConfigOption('timeout', 2)

    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)
        self.laser_state = LaserState.OFF
        self.shutter = ShutterState.NOSHUTTER
        self._mode = ControlMode.POWER
        self._current_setpoint = 0
        self._power_setpoint = 0
        self._enabled = False

    def on_activate(self):
        """ Activate module.
        """
        self.rm = visa.ResourceManager()

        if self._connection_type == 'GPIB':

            try:
                self._gpib_connection = self.rm.open_resource(
                    self._physical_interface,
                    timeout=self._timeout * 1000)
            except:
                self.log.error('Hardware connection through GPIB '
                               'address >>{}<< failed.'.format(self._gpib_address))
                raise
            self.model = self._gpib_connection.query('*IDN?').split(',')[1]
            self.log.info('T100S_HP connected.')

    def on_deactivate(self):
        """ Deactivate module.
        """
        self._gpib_connection.close()
        self.rm.close()

    def get_power_range(self):
        """ Return optical power range

            @return (float, float): power range
        """
        return 0, 0.02  # 20 mW maxi in specs

    def get_power(self):
        """ Return laser power

            @return float: Laser power in watts
        """
        power = self._query('MW;P?')
        if power == 'DISABLED':
            return 0
        else:  # 'P=xx.xx'
            return float(power[2:])*1e-3

    def get_power_setpoint(self):
        """ Return optical power setpoint.

            @return float: power setpoint in watts
        """
        return self._power_setpoint

    def set_power(self, power):
        """ Set power setpoint.

            @param float power: power setpoint

            @return float: actual new power setpoint
        """
        mini, maxi = self.get_control_limit()
        if mini <= power <= maxi:
            self._power_setpoint = power
            self._write("MW;P={}".format(power))
        else:
            self.log.error('Power value {} out of range'.format(power))
        return self._power_setpoint

    def get_current_unit(self):
        """ Get unit for laser current.

            @return str: unit
        """
        return 'mA'

    def get_current_range(self):
        """ Get laser current range.

            @return (float, float): laser current range
        """
        return 0, 400  # 400 mA in specs

    def get_current(self):
        """ Get current laser current

            @return float: laser current in current curent units
        """
        current = self._query('I?')
        if current == 'DISABLED':
            return 0
        else:  # 'P=xx.xx'
            return float(current[2:])

    def get_current_setpoint(self):
        """ Get laser curent setpoint

            @return float: laser current setpoint
        """
        return self._current_setpoint

    def set_current(self, current):
        """ Set laser current setpoint

            @prarm float current: desired laser current setpoint

            @return float: actual laser current setpoint
        """
        mini, maxi = self.get_current_range()
        if mini <= current <= maxi:
            self._current_setpoint = current
            self._write("I={}".format(current))
        else:
            self.log.error('Current value {} out of range'.format(current))
        return self._power_setpoint

    def allowed_control_modes(self):
        """ Get supported control modes

            @return list(): list of supported ControlMode
        """
        return [ControlMode.POWER]

    def get_control_mode(self):
        """ Get the currently active control mode

            @return ControlMode: active control mode
        """
        return self._mode

    def set_control_mode(self, control_mode):
        """ Set the active control mode

            @param ControlMode control_mode: desired control mode

            @return ControlMode: actual active ControlMode
        """
        if control_mode in self.allowed_control_modes():
            self._mode = control_mode
        return self._mode

    def on(self):
        """ Turn on laser.

            @return LaserState: actual laser state
        """
        self._enabled = True
        self._write('ENABLE')
        return LaserState.ON

    def off(self):
        """ Turn off laser.

            @return LaserState: actual laser state
        """
        self._enabled = True
        self._write('ENABLE')
        return LaserState.OFF

    def get_laser_state(self):
        """ Get laser state

            @return LaserState: actual laser state
        """
        return self.lstate

    def set_laser_state(self, state):
        """ Set laser state.

            @param LaserState state: desired laser state

            @return LaserState: actual laser state
        """
        time.sleep(1)
        self.lstate = state
        return self.lstate

    def get_shutter_state(self):
        """ Get laser shutter state

            @return ShutterState: actual laser shutter state
        """
        return self.shutter

    def set_shutter_state(self, state):
        """ Set laser shutter state.

            @param ShutterState state: desired laser shutter state

            @return ShutterState: actual laser shutter state
        """
        time.sleep(1)
        self.shutter = state
        return self.shutter

    def get_temperatures(self):
        """ Get all available temperatures.

            @return dict: dict of temperature namce and value in degrees Celsius
        """
        return {
            'psu': 32.2 * random.gauss(1, 0.1),
            'head': 42.0 * random.gauss(1, 0.2)
            }

    def set_temperatures(self, temps):
        """ Set temperatures for lasers with tunable temperatures.

            @return {}: empty dict, dummy not a tunable laser
        """
        return {}

    def get_temperature_setpoints(self):
        """ Get temperature setpoints.

            @return dict: temperature setpoints for temperature tunable lasers
        """
        return {'psu': 32.2, 'head': 42.0}

    def get_extra_info(self):
        """ Multiple lines of dignostic information

            @return str: much laser, very useful
        """
        return "Dummy laser v0.9.9\nnot used very much\nvery cheap price very good quality"

# Define general read write function

    def _write(self, text):
        """ Write to the hardware

        @param (str) text: The text to send """
        if self._connection_type == 'GPIB':
            self._gpib_connection.write(text)
        else:
            self.log.error('Serial connection not implemented.')

    def _read(self):
        """ Read from the hardware

        @return (str): Readable message from the hardware """
        if self._connection_type == 'GPIB':
            output = self._gpib_connection.read()
            return output
        else:
            self.log.error('Serial connection not implemented.')

    def _query(self, text):
        """ Read from the hardware
        @param (str) text: The text to send

        @return (str): Readable message from the hardware """
        if self._connection_type == 'GPIB':
            output = self._gpib_connection.query(text)
            return output
        else:
            self.log.error('Serial connection not implemented.')


# Define hardware getters and setters

    def _get_power(self):
        """ Query the power to the hardware

        @return float: Power in Watts
        """
        output = self._query('MW;P?')
        if output =='DISABLED':
            return 0
        else:
            return float(output.split('=')[1])/1e3


