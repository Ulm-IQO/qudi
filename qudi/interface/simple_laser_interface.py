# -*- coding: utf-8 -*-
"""
Interface file for lasers where current and power can be set.

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

from enum import IntEnum
from abc import abstractmethod
from qudi.core.module import Base


class ControlMode(IntEnum):
    POWER = 0
    CURRENT = 1
    UNKNOWN = 2


class ShutterState(IntEnum):
    CLOSED = 0
    OPEN = 1
    NO_SHUTTER = 2
    UNKNOWN = 3


class LaserState(IntEnum):
    OFF = 0
    ON = 1
    LOCKED = 2
    UNKNOWN = 3


class SimpleLaserInterface(Base):
    """ This interface can be used to control a simple laser. It handles power control, control modes and shutter states

    This interface is useful for a standard, fixed wavelength laser that you can find in a lab.
    It handles power control via constant power or constant current mode, a shutter state if the hardware has a shutter
    and a temperature regulation control.

    """

    @abstractmethod
    def get_power_range(self):
        """ Return laser power range

        @return float[2]: power range (min, max)
        """
        pass

    @abstractmethod
    def get_power(self):
        """ Return actual laser power

        @return float: Laser power in watts
        """
        pass

    @abstractmethod
    def set_power(self, power):
        """ Set power setpoint.

        @param float power: power to set
        """
        pass

    @abstractmethod
    def get_power_setpoint(self):
        """ Return laser power setpoint.

        @return float: power setpoint in watts
        """
        pass

    @abstractmethod
    def get_current_unit(self):
        """ Get unit for laser current.

        @return str: unit
        """
        pass

    @abstractmethod
    def get_current(self):
        """ Get actual laser current

        @return float: laser current in current units
        """
        pass

    @abstractmethod
    def get_current_range(self):
        """ Get laser current range.

        @return float[2]: laser current range
        """
        pass

    @abstractmethod
    def get_current_setpoint(self):
        """ Get laser current setpoint

        @return float: laser current setpoint
        """
        pass

    @abstractmethod
    def set_current(self, current):
        """ Set laser current setpoint

        @param float current: desired laser current setpoint
        """
        pass

    @abstractmethod
    def allowed_control_modes(self):
        """ Get supported control modes

        @return frozenset: set of supported ControlMode enums
        """
        pass

    @abstractmethod
    def get_control_mode(self):
        """ Get the currently active control mode

        @return ControlMode: active control mode enum
        """
        pass

    @abstractmethod
    def set_control_mode(self, control_mode):
        """ Set the active control mode

        @param ControlMode control_mode: desired control mode enum
        """
        pass

    @abstractmethod
    def get_laser_state(self):
        """ Get laser state

        @return LaserState: current laser state
        """
        pass

    @abstractmethod
    def set_laser_state(self, state):
        """ Set laser state.

        @param LaserState state: desired laser state enum
        """
        pass

    @abstractmethod
    def get_shutter_state(self):
        """ Get laser shutter state

        @return ShutterState: actual laser shutter state
        """
        pass

    @abstractmethod
    def set_shutter_state(self, state):
        """ Set laser shutter state.

        @param ShutterState state: desired laser shutter state
        """
        pass

    @abstractmethod
    def get_temperatures(self):
        """ Get all available temperatures.

        @return dict: dict of temperature names and value in degrees Celsius
        """
        pass

    @abstractmethod
    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        pass
