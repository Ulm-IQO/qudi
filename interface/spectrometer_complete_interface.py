# -*- coding: utf-8 -*-
"""
Interface module for spectrometer hardware

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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass
from core.interface import ScalarConstraint


class Grating:
    """ Class defining formally a hardware grating """
    def __init__(self):
        self.ruling = None               # Ruling in line per meter
        self.blaze = None                # Blaze in meter
        self.wavelength_constraints = ScalarConstraint(unit='m')       # Wavelength limits in meter


class Port(Enum):
    """ Class defining the possible port for input or output """
    FRONT = 0
    SIDE = 1


class Constraints:
    """ Class defining formally the hardware constraints """
    def __init__(self):
        self.focal_length = None         # Focal length in meter
        self.angular_deviation = None    # Angular deviation in radian
        self.focal_tilt = None           # Focal tilt in radian
        self.gratings = []               # List of Grating object
        self.has_side_input = False      # Tells if the hardware has an second input on the side
        self.has_side_output = False     # Tells if the hardware has an second output on the side
        self.input_motorized_slit = ScalarConstraint(unit='m')      # Motorized slit constraints or None
        self.output_motorized_slit = ScalarConstraint(unit='m')     # Motorized slit constraints or None
        self.shutter_modes = []          # Hardware defined shutter modes (list of string)


class SpectrometerInterface(metaclass=InterfaceMetaclass):
    """ This is the interface class to define the controls for spectrometer hardware

    This interface only deals with the part of the spectrometer that set central wavelength and gratings.
    For the parameter of the spectroscopy camera, see the "spectroscopy_camera_interface".
    """

    @abstract_interface_method
    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        pass

    ##############################################################################
    #                            Gratings functions
    ##############################################################################
    @abstract_interface_method
    def get_grating_index(self):
        """ Returns the current grating index

        @return (int): Current grating index
        """
        pass

    @abstract_interface_method
    def set_grating_index(self, value):
        """ Sets the grating by index

        @param (int) value: grating index
        """
        pass

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################
    @abstract_interface_method
    def get_wavelength(self):
        """ Returns the current central wavelength in meter

        @return (float): current central wavelength (meter)
        """
        pass

    @abstract_interface_method
    def set_wavelength(self, value):
        """ Sets the new central wavelength in meter

        @params (float) value: The new central wavelength (meter)
        """
        pass

    ##############################################################################
    #                        Ports and Slits functions
    ##############################################################################

    @abstract_interface_method
    def get_input_port(self):
        """Returns the current port for the input flipper mirror.

        @return: (int) 0 is for front port, 1 is for side port
        in case of no flipper mirror, front port (0) is used
        """
        pass

    @abstract_interface_method
    def set_input_port(self, input_port):
        """Sets the input port - 0 is for front port, 1 is for side port

        @param input_port: (int). has to be 0 or 1
        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_output_port(self):
        """Returns the current port for the output flipper mirror.

        @return: (int) 0 is for front port, 1 is for side port
        in case of no flipper mirror, front port (0) is used
        """
        pass

    @abstract_interface_method
    def set_output_port(self, output_port):
        """Sets the input port - 0 is for front port, 1 is for side port

        @param output_port: (int). has to be 0 or 1
        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_input_slit_width(self):
        """Returns the input slit width (um) of the current input slit.

        @return:  (int) offset - slit width, unit is meter (SI)
        """
        pass

    @abstract_interface_method
    def set_input_slit_width(self, slit_width):
        """Sets the new slit width for the current input slit.

        @param slit_width: (float) slit width unit is meter (SI)
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_output_slit_width(self):
        """Returns the output slit width (um) of the current output slit.

        @return:  (int) offset - slit width, unit is meter (SI)
        """
        pass

    @abstract_interface_method
    def set_output_slit_width(self, slit_width):
        """Sets the new slit width for the current output slit.

        @param slit_width: (float) slit width unit is meter (SI)
        :return: nothing
        """
        pass

    ##############################################################################
    #                        Shutter mode function (optional)
    ##############################################################################
    # Shutter mode function are used in logic only if the spectrometer constraints
    # dictionary has 'shutter_modes' key filled. If empty this functions will not
    # be used and can be ignored.

    @abstract_interface_method
    def get_shutter_status(self):
        """Getter method returning the shutter mode.

        @return: (str) shutter mode (must be compared to the list)
        """
        pass

    @abstract_interface_method
    def set_shutter_status(self, shutter_mode):
        """Setter method setting the shutter mode.

        @param shutter_mode: (str) shutter mode (must be compared to the list)
        @return: nothing
        """
        pass
