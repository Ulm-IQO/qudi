# -*- coding: utf-8 -*-
"""
This module acts like a tunable laser.

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

from core.module import Base
from interface.tunable_laser_interface import TunableLaserInterface, PowerControlMode, WavelengthControlMode, LaserState, ShutterState
import math
import random
import time

class TunableLaserDummy(Base, TunableLaserInterface):
    """
    Tunable laser dummy
    """
    _modclass = 'tunablelaserdummy'
    _modtype = 'hardware'

    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)
        self.lstate = LaserState.OFF
        self.shutter = ShutterState.CLOSED
        self.power_mode = PowerControlMode.POWER
        self.wavelength_mode = WavelengthControlMode.WAVELENGTH_IN_METERS
        self.wavelength = 950
        self.current_setpoint = 0
        self.power_setpoint = 0
        self.wavelength_setpoint = 637e-9

    def on_activate(self):
        """ Activate module.
        """
        pass

    def on_deactivate(self):
        """ Deactivate module.
        """
        pass

    def get_power_range(self):
        """ Return laser power
        @return tuple(p1, p2): Laser power range in watts
        """
        return (0, 0.250)

    def get_power(self):
        """ Return laser power
        @return float: Actual laser power in watts
        """
        return self.power_setpoint * random.gauss(1, 0.01)

    def set_power(self, power):
        """ Set laser power ins watts
          @param float power: laser power setpoint in watts

          @return float: laser power setpoint in watts
        """
        self.power_setpoint = power
        self.current_setpoint = math.sqrt(4*self.power_setpoint)*100
        return self.power_setpoint

    def get_power_setpoint(self):
        """ Return laser power setpoint
        @return float: Laser power setpoint in watts
        """
        return self.power_setpoint

    def get_wavelength(self):
        """ Get laser wavelength in units defined by the wavelength control mode
          @param float wavelength: laser wavelength in units defined by the wavelength control mode
        """
        if self.wavelength_mode is WavelengthControlMode.WAVELENGTH_IN_METERS:
            return self.wavelength_setpoint * random.gauss(1, 1e-5)
        else:
            return self._wavelength_to_voltage(self.wavelength_setpoint * random.gauss(1, 1e-5))

    def set_wavelength(self, wavelength):
        """ Set wavelength in units defined by the wavelength control mode
          @param float wavelength: laser wavelength in units defined by the wavelength control mode
          @return float: laser wavelength setpoint in units defined by the wavelength control mode
        """
        if self.wavelength_mode is WavelengthControlMode.WAVELENGTH_IN_METERS:
            self.wavelength_setpoint = wavelength
            return wavelength
        else:
            self.wavelength_setpoint = self._voltage_to_wavelength(wavelength)
            return wavelength

    def get_wavelength_setpoint(self):
        """ Return laser wavelength setpoint in units defined by the wavelength control mode
        @return float: Laser wavelength setpoint in units defined by the wavelength control mode
        """
        if self.wavelength_mode is WavelengthControlMode.WAVELENGTH_IN_METERS:
            return self.wavelength_setpoint
        else:
            return self._wavelength_to_voltage(self.wavelength_setpoint)

    def get_wavelength_range(self):
        """ Return wavelength range
        @return tuple(p1, p2): Laser wavelength range in units defined by the wavelength control mode
        """
        if self.wavelength_mode is WavelengthControlMode.WAVELENGTH_IN_METERS:
            return (636e-9, 638e-9)
        else:
            return (-10, 10)

    def get_current_unit(self):
        """ Return laser current unit
        @return str: unit
        """
        return "%"

    def get_current(self):
        """ Return laser current
        @return float: actual laser current as ampere or percentage of maximum current
        """
        return self.current_setpoint * random.gauss(1, 0.05)

    def get_current_range(self):
        """ Return laser current range
        @return tuple(c1, c2): Laser current range in current units
        """
        return (0, 100)

    def get_current_setpoint(self):
        """ Return laser current
        @return float: Laser current setpoint in amperes
        """
        return self.current_setpoint

    def set_current(self, current):
        """ Set laser current
        @param float current: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        self.current_setpoint = current
        self.power_setpoint = math.pow(self.current_setpoint/100, 2)/4
        return self.current_setpoint

    def allowed_power_control_modes(self):
        """ Get available power control mode of laser
          @return list: list with enum power control modes
        """
        return [PowerControlMode.POWER, PowerControlMode.CURRENT]

    def get_power_control_mode(self):
        """ Get power control mode of laser
          @return enum PowerControlMode: power control mode
        """
        return self.power_mode

    def set_power_control_mode(self, power_control_mode):
        """ Set laser power control mode.
          @param enum power_control_mode: desired power control mode
          @return enum PowerControlMode: actual power control mode
        """
        self.power_mode = power_control_mode
        return self.power_mode

    def allowed_wavelength_control_modes(self):
        """ Get available wavelength control mode of laser
          @return list: list with enum wavelength control modes
        """
        return [WavelengthControlMode.WAVELENGTH_IN_METERS, WavelengthControlMode.VOLTAGE_IN_VOLTS]

    def get_wavelength_control_mode(self):
        """ Get power control mode of laser
          @return enum WavelengthControlMode: power control mode
        """
        return self.wavelength_mode

    def set_wavelength_control_mode(self, wavelength_control_mode):
        """ Set laser wavelength control mode.
          @param enum wavelength_control_mode: desired wavelength control mode
          @return enum WavelengthControlMode: actual wavelength control mode
        """
        self.wavelength_mode = wavelength_control_mode
        return self.wavelength_mode

    def on(self):
        """ Turn on laser. Does not open shutter if one is present.
          @return enum LaserState: actual laser state
        """
        time.sleep(1)
        self.lstate = LaserState.ON
        return self.lstate

    def off(self):
        """ Turn ooff laser. Does not close shutter if one is present.
          @return enum LaserState: actual laser state
        """
        time.sleep(1)
        self.lstate = LaserState.OFF
        return self.lstate

    def get_laser_state(self):
        """ Get laser state.
          @return enum LaserState: laser state
        """
        return self.lstate

    def set_laser_state(self, state):
        """ Set laser state.
          @param enum state: desired laser state
          @return enum LaserState: actual laser state
        """
        time.sleep(1)
        self.lstate = state
        return self.lstate

    def get_shutter_state(self):
        """ Get shutter state. Has a state for no shutter present.
          @return enum ShutterState: actual shutter state
        """
        return self.shutter

    def set_shutter_state(self, state):
        """ Set shutter state.
          @param enum state: desired shutter state
          @return enum ShutterState: actual shutter state
        """
        time.sleep(1)
        self.shutter = state
        return self.shutter

    def get_temperatures(self):
        """ Get all available temperatures from laser.
          @return dict: dict of name, value for temperatures
        """
        return {
            'psu': 32.2 * random.gauss(1, 0.1),
            'head': 42.0 * random.gauss(1, 0.2)
        }

    def get_temperature_setpoints(self):
        """ Get all available temperature setpoints from laser.
          @return dict: dict of name, value for temperature setpoints
        """
        return {'psu': 32.2, 'head': 42.0}

    def set_temperatures(self, temps):
        """ Set laser temperatures.
          @param temps: dict of name, value to be set
          @return dict: dict of name, value of temperatures that were set
        """
        return {} # cannot set temperatures of dummy laser

    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        return "Dummy tunable laser v0.9.9\nnot used very much\nvery cheap price very good quality"

    def _voltage_to_wavelength(self, voltage):
        return (voltage + 6370)/1e10

    def _wavelength_to_voltage(self, wavelength):
        return (1e10 * wavelength) - 6370