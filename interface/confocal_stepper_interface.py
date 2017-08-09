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
    def change_step_size(self, axis, stepsize, temp):
        """Changes the step size of the attocubes according to a list give in the config file
        @param str  axis: axis  for which steps size is to be changed
        @param float stepsize: The wanted stepsize in nm
        @param float temp: The estimated temperature of the attocubes

        @return: float, float : Actual stepsize and used temperature"""
        pass

    @abc.abstractmethod
    def set_step_amplitude(self, axis, voltage=None):
        """Sets the step voltage/amplitude for an axis

        @param str axis: the axis to be changed
        @param int voltage: the stepping amplitude/voltage the axis should be set to
        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_step_amplitude(self, axis):
        """ Reads the amplitude of a step for a specific axis from the device

        @param str axis: the axis for which the step amplitude is to be read
        @return float: the step amplitude of the axis
        """
        pass

    @abc.abstractmethod
    def set_step_freq(self, axis, freq=None):
        """Sets the step frequency for an axis

        @param str axis: the axis to be changed
        @param int freq: the stepping frequency the axis should be set to
        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_step_freq(self, axis):
        """ Reads the step frequency for a specific axis from the device

        @param str axis: the axis for which the frequency is to be read
        @return float: the step amplitude of the axis
        """
        pass

    @abc.abstractmethod
    def set_axis_mode(self, axis, mode):
        """Changes Attocube axis mode

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param str mode: mode to be set
        @return int: error code (0: OK, -1:error)
        """
        pass

    def get_axis_mode(self, axis):
        """ Checks the mode for a specific axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the mode of the axis, -1 for error
        """
        pass

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
		
    @abc.abstractmethod
    def get_amplitude_range_stepper(self):
        """Returns the current possible stepping voltage range of the stepping device for all axes
        @return list: voltage range of scanner
        """
        pass

	@abc.abstractmethod
	def get_freq_range_stepper(self):
		"""Returns the current possible frequency range of the stepping device for all axes
		@return dict: key[axis], value[list of range]
		"""
        pass
		

	
