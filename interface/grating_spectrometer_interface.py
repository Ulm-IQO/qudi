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
    """ Class defining formally the grating constraints """
    def __init__(self):
        self.ruling = None               # Ruling in line per meter
        self.blaze = None                # Blaze in meter
        self.wavelength_max = None       # Wavelength limits in meter


class PortType(Enum):
    """ Class defining the possible type : input or output"""
    INPUT_FRONT = 0
    INPUT_SIDE = 1
    OUTPUT_FRONT = 2
    OUTPUT_SIDE = 3


class Port:
    """ Class defining formally the port constraints  """
    def __init__(self, _type):
        self.type = _type  # PortType.INPUT_FRONT
        self.is_motorized = True
        self.constraints = ScalarConstraint(unit='m')


class Constraints:
    """ Class defining formally the hardware constraints """
    def __init__(self):
        self.focal_length = None         # Focal length in meter
        self.angular_deviation = None    # Angular deviation in radian
        self.focal_tilt = None           # Focal tilt in radian
        self.gratings = []               # List of Grating object
        self.ports = []                  # List of Ports object


class GratingSpectrometerInterface(metaclass=InterfaceMetaclass):
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
        """ Returns the current input port

        @return (PortType): current port side
        """
        pass

    @abstract_interface_method
    def set_input_port(self, value):
        """ Set the current input port

        @param (PortType) value: The port side to set
        """
        pass

    @abstract_interface_method
    def get_output_port(self):
        """ Returns the current output port

        @return (PortType): current port side
        """
        pass

    @abstract_interface_method
    def set_output_port(self, value):
        """ Set the current output port

        @param (PortType) value: The port side to set
        """
        pass

    @abstract_interface_method
    def get_slit_width(self, port_type):
        """ Getter for the current slit width in meter on a given port

        @param (PortType) port_type: The port to inquire

        @return (float): input slit width (in meter)
        """
        pass

    @abstract_interface_method
    def set_slit_width(self, port_type, value):
        """ Setter for the input slit width in meter

        @param (PortType) port_type: The port to set
        @param (float) value: input slit width (in meter)
        """
        pass