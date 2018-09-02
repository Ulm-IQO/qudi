# -*- coding: utf-8 -*-
"""
Interface file for lasers where current, power and wavelength / voltage can be set

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

from enum import Enum
import abc
from core.util.interfaces import InterfaceMetaclass


class PowerControlMode(Enum):
    MIXED = 0
    POWER = 1
    CURRENT = 2

class WavelengthControlMode(Enum):
    VOLTAGE_IN_VOLTS = 0
    WAVELENGTH_IN_METERS = 1

class ShutterState(Enum):
    CLOSED = 0
    OPEN = 1
    UNKNOWN = 2
    NOSHUTTER = 3

class LaserState(Enum):
    OFF = 0
    ON = 1
    LOCKED = 2
    UNKNOWN = 3

class TunableLaserInterface(metaclass=InterfaceMetaclass):
    _modtype = 'TunableLaserInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_power_range(self):
        """ Return laser power
        @return tuple(p1, p2): Laser power range in watts
        """
        pass

    @abc.abstractmethod
    def get_power(self):
        """ Return laser power
        @return float: Actual laser power in watts
        """
        pass

    @abc.abstractmethod
    def set_power(self, power):
        """ Set laser power ins watts
          @param float power: laser power setpoint in watts

          @return float: laser power setpoint in watts
        """
        pass

    @abc.abstractmethod
    def get_power_setpoint(self):
        """ Return laser power setpoint
        @return float: Laser power setpoint in watts
        """
        pass

    @abc.abstractmethod
    def get_wavelength(self):
        """ Get laser wavelength in units defined by the wavelength control mode
          @return float: laser wavelength in units defined by the wavelength control mode
        """
        pass

    @abc.abstractmethod
    def set_wavelength(self, wavelength):
        """ Set wavelength in units defined by the wavelength control mode
          @param float wavelength: laser wavelength in units defined by the wavelength control mode
          @return float: laser wavelength setpoint in units defined by the wavelength control mode
        """
        pass

    @abc.abstractmethod
    def get_wavelength_setpoint(self):
        """ Return laser wavelength setpoint in units defined by the wavelength control mode
        @return float: Laser wavelength setpoint in units defined by the wavelength control mode
        """
        pass

    @abc.abstractmethod
    def get_wavelength_range(self):
        """ Return wavelength range
        @return tuple(p1, p2): Laser wavelength range in units defined by the wavelength control mode
        """
        pass

    @abc.abstractmethod
    def get_current_unit(self):
        """ Return laser current unit
        @return str: unit
        """
        pass

    @abc.abstractmethod
    def get_current(self):
        """ Return laser current
        @return float: actual laser current as ampere or percentage of maximum current
        """
        pass

    @abc.abstractmethod
    def get_current_range(self):
        """ Return laser current range
        @return tuple(c1, c2): Laser current range in current units
        """
        pass

    @abc.abstractmethod
    def get_current_setpoint(self):
        """ Return laser current
        @return float: Laser current setpoint in amperes
        """
        pass

    @abc.abstractmethod
    def set_current(self, current):
        """ Set laser current
        @param float current: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        pass

    @abc.abstractmethod
    def allowed_power_control_modes(self):
        """ Get available power control mode of laser
          @return list: list with enum power control modes
        """
        pass

    @abc.abstractmethod
    def get_power_control_mode(self):
        """ Get power control mode of laser
          @return enum PowerControlMode: power control mode
        """
        pass

    @abc.abstractmethod
    def set_power_control_mode(self, power_control_mode):
        """ Set laser power control mode.
          @param enum power_control_mode: desired power control mode
          @return enum PowerControlMode: actual power control mode
        """
        pass

    @abc.abstractmethod
    def allowed_wavelength_control_modes(self):
        """ Get available wavelength control mode of laser
          @return list: list with enum wavelength control modes
        """
        pass

    @abc.abstractmethod
    def get_wavelength_control_mode(self):
        """ Get power control mode of laser
          @return enum WavelengthControlMode: power control mode
        """
        pass

    @abc.abstractmethod
    def set_wavelength_control_mode(self, wavelength_control_mode):
        """ Set laser wavelength control mode.
          @param enum wavelength_control_mode: desired wavelength control mode
          @return enum WavelengthControlMode: actual wavelength control mode
        """
        pass


    @abc.abstractmethod
    def on(self):
        """ Turn on laser. Does not open shutter if one is present.
          @return enum LaserState: actual laser state
        """
        pass

    @abc.abstractmethod
    def off(self):
        """ Turn ooff laser. Does not close shutter if one is present.
          @return enum LaserState: actual laser state
        """
        pass

    @abc.abstractmethod
    def get_laser_state(self):
        """ Get laser state.
          @return enum LaserState: laser state
        """
        pass

    @abc.abstractmethod
    def set_laser_state(self, state):
        """ Set laser state.
          @param enum state: desired laser state
          @return enum LaserState: actual laser state
        """
        pass

    @abc.abstractmethod
    def get_shutter_state(self):
        """ Get shutter state. Has a state for no shutter present.
          @return enum ShutterState: actual shutter state
        """
        pass

    @abc.abstractmethod
    def set_shutter_state(self, state):
        """ Set shutter state.
          @param enum state: desired shutter state
          @return enum ShutterState: actual shutter state
        """
        pass

    @abc.abstractmethod
    def get_temperatures(self):
        """ Get all available temperatures from laser.
          @return dict: dict of name, value for temperatures
        """
        pass

    @abc.abstractmethod
    def get_temperature_setpoints(self):
        """ Get all available temperature setpoints from laser.
          @return dict: dict of name, value for temperature setpoints
        """
        pass

    @abc.abstractmethod
    def set_temperatures(self, temps):
        """ Set laser temperatures.
          @param temps: dict of name, value to be set
          @return dict: dict of name, value of temperatures that were set
        """
        pass

    @abc.abstractmethod
    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        pass
