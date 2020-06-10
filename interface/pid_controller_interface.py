# -*- coding: utf-8 -*-
"""
Interface file for a PID device.

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


class PIDControllerInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to control a PID device.

    From Wikipedia : https://en.wikipedia.org/wiki/PID_controller
    A proportional–integral–derivative controller (PID controller or three-term controller) is a control loop mechanism
    employing feedback that is widely used in industrial control systems and a variety of other applications requiring
    continuously modulated control. A PID controller continuously calculates an error value e(t) as the difference
    between a desired setpoint (SP) and a measured process variable (PV) and applies a correction based on proportional,
    integral, and derivative terms (denoted P, I, and D respectively), hence the name.

    If the device is enabled, the control value is computed by the the PID system of the hardware. If the device is
    disabled, the control value is set by the manual value.

    """

    @abstract_interface_method
    def get_kp(self):
        """ Get the coefficient associated with the proportional term

         @return (float): The current kp coefficient associated with the proportional term
         """
        pass

    @abstract_interface_method
    def set_kp(self, kp):
        """ Set the coefficient associated with the proportional term

         @param (float) kp: The new kp coefficient associated with the proportional term
         """
        pass

    @abstract_interface_method
    def get_ki(self):
        """ Get the coefficient associated with the integral term

         @return (float): The current ki coefficient associated with the integral term
         """
        pass

    @abstract_interface_method
    def set_ki(self, ki):
        """ Set the coefficient associated with the integral term

         @param (float) ki: The new ki coefficient associated with the integral term
         """
        pass

    @abstract_interface_method
    def get_kd(self):
        """ Get the coefficient associated with the derivative term

         @return (float): The current kd coefficient associated with the derivative term
         """
        pass

    @abstract_interface_method
    def set_kd(self, kd):
        """ Set the coefficient associated with the derivative term

         @param (float) kd: The new kd coefficient associated with the derivative term
         """
        pass

    @abstract_interface_method
    def get_setpoint(self):
        """ Get the setpoint value of the hardware device

         @return (float): The current setpoint value
         """
        pass

    @abstract_interface_method
    def set_setpoint(self, setpoint):
        """ Set the setpoint value of the hardware device

        @param (float) setpoint: The new setpoint value
        """
        pass

    @abstract_interface_method
    def get_manual_value(self):
        """ Get the manual value, used if the device is disabled

        @return (float): The current manual value
        """
        pass

    @abstract_interface_method
    def set_manual_value(self, manualvalue):
        """ Set the manual value, used if the device is disabled

        @param (float) manualvalue: The new manual value
        """
        pass

    @abstract_interface_method
    def get_enabled(self):
        """ Get if the PID is enabled (True) or if it is disabled (False) and the manual value is used

        @return (bool): True if enabled, False otherwise
        """
        pass

    @abstract_interface_method
    def set_enabled(self, enabled):
        """ Set if the PID is enabled (True) or if it is disabled (False) and the manual value is used

        @param (bool) enabled: True to enabled, False otherwise
        """
        pass

    @abstract_interface_method
    def get_control_limits(self):
        """ Get the current limits of the control value as a tuple

        @return (tuple(float, float)): The current control limits
        """
        pass

    @abstract_interface_method
    def set_control_limits(self, limits):
        """ Set the current limits of the control value as a tuple

        @param (tuple(float, float)) limits: The new control limits

        The hardware should check if these limits are within the maximum limits set by a config option.
        """
        pass

    @abstract_interface_method
    def get_process_value(self):
        """ Get the current process value read

        @return (float): The current process value
        """
        pass

    @abstract_interface_method
    def get_control_value(self):
        """ Get the current control value read

        @return (float): The current control value
        """
        pass

    @abstract_interface_method
    def get_extra(self):
        """ Get the P, I and D terms computed bu the hardware if available

         @return dict(): A dict with keys 'P', 'I', 'D' if available, an empty dict otherwise
         """
        pass
