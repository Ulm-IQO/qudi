"""
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
from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass

class NewfocusLaserInterface(metaclass=InterfaceMetaclass):
    _modtype = 'NewfocusLaserInterface'
    _modclass = 'interface'

    @abstract_interface_method
    def get_power_range(self):
        """ Return laser power
        @return tuple(p1, p2): Laser power range in watts
        """
        pass

    @abstract_interface_method
    def get_power(self):
        """ Return laser power
        @return float: Actual laser power in watts
        """
        pass

    @abstract_interface_method
    def set_power(self, power):
        """ Set laer power ins watts
          @param float power: laser power setpoint in watts

          @return float: laser power setpoint in watts
        """
        pass

    @abstract_interface_method
    def get_power_setpoint(self):
        """ Return laser power setpoint
        @return float: Laser power setpoint in watts
        """
        pass

    @abstract_interface_method
    def get_current(self):
        """ Return laser current
        @return float: actual laser current as ampere or percentage of maximum current
        """
        pass

    @abstract_interface_method
    def get_current_range(self):
        """ Return laser current range
        @return tuple(c1, c2): Laser current range in current units
        """
        pass

    @abstract_interface_method
    def get_current_setpoint(self):
        """ Return laser current
        @return float: Laser current setpoint in amperes
        """
        pass

    @abstract_interface_method
    def set_current(self, current):
        """ Set laser current
        @param float current: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        pass

    @abstract_interface_method
    def allowed_control_modes(self):
        """ Get available control mode of laser
          @return list: list with enum control modes
        """
        pass

    @abstract_interface_method
    def get_control_mode(self):
        """ Get control mode of laser
          @return enum ControlMode: control mode
        """
        pass

    @abstract_interface_method
    def set_control_mode(self, control_mode):
        """ Set laser control mode.
          @param enum control_mode: desired control mode
          @return enum ControlMode: actual control mode
        """
        pass

    @abstract_interface_method
    def output_enable(self):
        """ Turn on laser. Does not open shutter if one is present.
          @return enum LaserState: actual laser state
        """
        pass

    @abstract_interface_method
    def output_disable(self):
        """ Turn ooff laser. Does not close shutter if one is present.
          @return enum LaserState: actual laser state
        """
        pass

    @abstract_interface_method
    def get_output_state(self):
        """ Get laser state.
          @return enum LaserState: laser state
        """
        pass

    @abstract_interface_method
    def set_wavelength(self, wavelength):
        """ Set laser state.
          @param enum state: desired laser state
          @return enum LaserState: actual laser state
        """
        pass

    @abstract_interface_method
    def get_wavelength(self):
        """ Get shutter state. Has a state for no shutter present.
          @return enum ShutterState: actual shutter state
        """
        pass

    @abstract_interface_method
    def set_piezo_percentage(self, percentage):
        """ Set shutter state.
          @param enum state: desired shutter state
          @return enum ShutterState: actual shutter state
        """
        pass

    @abstract_interface_method
    def get_piezo_percentage(self):
        """ Get all available temperatures from laser.
          @return dict: dict of name, value for temperatures
        """
        pass

    @abstract_interface_method
    def get_wavelength_tracking_state(self):
        """ Get all available temperature setpoints from laser.
          @return dict: dict of name, value for temperature setpoints
        """
        pass

    @abstract_interface_method
    def set_wavelength_tracking_state(self, state):
        """ Set laser temperatures.
          @param temps: dict of name, value to be set
          @return dict: dict of name, value of temperatures that were set
        """
        pass
