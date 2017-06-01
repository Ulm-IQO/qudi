# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for confocal stepper.

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


class ConfocalStepperInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the confocal microscope using a 
    stepper hardware.
    """

    _modtype = 'ConfocalStepperInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        pass

    # ============================== Stepper Commands ====================================

    @abc.abstractmethod
    def set_voltage_range_stepper(self, myrange=None):
        """ Sets the voltage range of the attocubes.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_stepper_axes(self):
        """ Find out how many axes the scanning device is using for confocal and their names.

        @return list(str): list of axis names

        Example:
          For 3D confocal microscopy in cartesian coordinates, ['x', 'y', 'z'] is a sensible value.
          For 2D, ['x', 'y'] would be typical.
          You could build a turntable microscope with ['r', 'phi', 'z'].
          Most callers of this function will only care about the number of axes, though.

          On error, return an empty list.
        """
        pass

    @abc.abstractmethod
    def get_stepper_axes(self):
        """"
        Checks which axes of the hardware have a reaction by the hardware

         @return list: list of booleans for each possible axis, if true axis exists

         On error, return empty list
        """
        pass

    @abc.abstractmethod
    def get_stepper_axes_use(self):
        """ Find out how the axes of the stepping device are used for confocal and their names.

        @return list(str): list of axis dictionary

        Example:
          For 3D confocal microscopy in cartesian coordinates, ['x':1, 'y':2, 'z':3] is a sensible 
          value.
          If you only care about the number of axes and not the assignment and names 
          use get_stepper_axes
          On error, return an empty list.
        """
        pass

    @abc.abstractmethod
    def move_attocube(self, axis, mode=True, direction=True, steps=1):
        """Moves steppers either continuously or by a number of steps
        in one off 2 directions

        @param str axis: axis to be moved, can only be part of dictionary axes
        @param bool mode: Sets mode of stepper. True: Stepping, False: Continuous 
        @param bool direction: True for one, False for other movement direction
        @param int steps: number of steps to be moved, ignore for continuous mode
        @return int:  error code (0: OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def stop_attocube_movement(self, axis):
        """Stops motion on specified axis

        @param str axis: can only be part of dictionary axes
        @return int: error code (0: OK, -1:error)"""
        pass

    @abc.abstractmethod
    def stop_all_attocube_motion(self):
        """Stops any motion of the steppers
        @return 0 
        """
        pass

    # ============================== Counter Commands ====================================

    @abc.abstractmethod
    def get_scanner_count_channels(self):
        """ Returns the list of channels that are recorded while scanning an image.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels.
        """
        pass
        # Todo this is connected to NIDAQ not attocube and has to be checked later

    @abc.abstractmethod
    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        pass
        # Todo this is connected to NIDAQ not attocube and has to be checked later

    @abc.abstractmethod
    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

        # ============================== Mixed Commands ====================================
