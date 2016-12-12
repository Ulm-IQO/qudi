# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for piezo stepper.

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

import abc
from core.util.interfaces import InterfaceMetaclass


class PiezoStepperInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the simple
    piezo stepper hardware.
    """

    _modtype = 'PiezoStepperInterface'
    _modclass = 'interface'


    @abc.abstractmethod
    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        pass

    @abc.abstractmethod
    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [n][2] myrange: array of n ranges with an array containing
                                     lower and upper limit, n defined in config

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_amplitude(self, amplitude=None):
        """ Sets the voltage of the steps.

        @param float amplitude: float specifying the voltage used per step

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_temperature(self, temp):
        """Changes the temperature settings of the setup to the given temperature adjusting ranges

        @param float temp: current hardware measured temperature of the setup
        @return int, float : error code (0:OK, -1:error), temperature the setup was set to
        """
        pass

    @abc.abstractmethod
    def step(self, steps=None, axis=None):
        """ Steps the stepper a given number of steps

        @param steps: Number of steps, None equals one, -1 steps continuously
        @param int axis: Defines the axis which is to be stepped

        @return: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_stepper(self):
        """ Closes the stepper and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass