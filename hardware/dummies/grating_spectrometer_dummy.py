# -*- coding: utf-8 -*-
"""
This module interface Shamrock spectrometer from Andor.

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
na=not applicable
"""
import numpy as np

from core.module import Base
from core.configoption import ConfigOption

from interface.grating_spectrometer_interface import SpectrometerInterface
from interface.grating_spectrometer_interface import Grating, PortType, Port, Constraints


class Main(Base, GratingSpectrometerInterface):
    """ Hardware module that interface a dummy grating spectrometer
    """

    # Declarations of attributes to make Pycharm happy
    def __init__(self):
        self._constraints = None
        self._dll = None
        self._shutter_status = None
        self._device_id = None

    ##############################################################################
    #                            Basic functions
    ##############################################################################
    def on_activate(self):
        """ Activate module """

        self._constraints = self._build_constraints()

        self._grating_index = 0
        self._center_wavelength = 600e-9
        self._input_port = PortType.INPUT_FRONT
        self._output_port = PortType.OUTPUT_SIDE
        self._slit_width = {PortType.INPUT_FRONT: 100e-6, PortType.INPUT_SIDE: 100e-6, PortType.OUTPUT_FRONT: 100e-6}



    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        pass

    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only once by on_activate
         """
        constraints = Constraints()

        constraints.focal_length = 0.5
        constraints.angular_deviation = 0.3*np.pi/180
        constraints.focal_tilt = 0

        number_of_gratings = 3

        grating = Grating()
        grating.ruling = 150e-3
        grating.blaze = 600e-9
        grating.wavelength_max = 1500e-9
        constraints.gratings.append(grating)

        grating = Grating()
        grating.ruling = 300e-3
        grating.blaze = 700e-9
        grating.wavelength_max = 1600e-9
        constraints.gratings.append(grating)

        grating = Grating()
        grating.ruling = 600e-3
        grating.blaze = 500e-9
        grating.wavelength_max = 1200e-9
        constraints.gratings.append(grating)

        port = Port(PortType.INPUT_FRONT)
        port.is_motorized = True
        constraints.ports.append(port)

        port = Port(PortType.INPUT_SIDE)
        port.is_motorized = True
        constraints.ports.append(port)

        port = Port(PortType.OUTPUT_FRONT)
        port.is_motorized = True
        constraints.ports.append(port)

        port = Port(PortType.OUTPUT_SIDE)
        port.is_motorized = False
        constraints.ports.append(port)

        for port in constraints.ports:
            port.constraints.min = 10e-6
            port.constraints.max = 1500e-6

        return constraints

    ##############################################################################
    #                            Interface functions
    ##############################################################################
    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        return self._constraints

    def get_grating_index(self):
        """ Returns the current grating index

        @return (int): Current grating index
        """
        return self._grating_index

    def set_grating_index(self, value):
        """ Sets the grating by index

        @param (int) value: grating index
        """
        self._grating_index = value

    def get_wavelength(self):
        """ Returns the current central wavelength in meter

        @return (float): current central wavelength (meter)
        """
        return self._center_wavelength

    def set_wavelength(self, value):
        """ Sets the new central wavelength in meter

        @params (float) value: The new central wavelength (meter)
        """
        grating_index = self.get_grating_index()
        maxi = self.get_constraints().gratings[grating_index].wavelength_max
        if 0 <= value <= maxi:
            self._center_wavelength = value
        else:
            self.log.error('The wavelength {} nm is not in the range {} nm , {} nm'.format(value*1e9, 0, maxi*1e9))

    def get_input_port(self):
        """ Returns the current input port

        @return (PortType): current port side
        """
        return self._input_port

    def set_input_port(self, value):
        """ Set the current input port

        @param (PortType) value: The port side to set
        """
        if isinstance(value, PortType):
            self._input_port = value
        else:
            self.log.error("The value is not a port")

    def get_output_port(self):
        """ Returns the current output port

        @return (PortType): current port side
        """
        return self._output_port

    def set_output_port(self, value):
        """ Set the current output port

        @param (PortType) value: The port side to set
        """
        if isinstance(value, PortType):
            self._output_port = value
        else:
            self.log.error("The value is not a port")

    def get_slit_width(self, port_type):
        """ Getter for the current slit width in meter on a given port

        @param (PortType) port_type: The port to inquire

        @return (float): input slit width (in meter)
        """
        return self._slit_width[port_type]

    def set_slit_width(self, port_type, value):
        """ Setter for the input slit width in meter

        @param (PortType) port_type: The port to set
        @param (float) value: input slit width (in meter)
        """
        for port in self.get_constraints().ports:
            if port.type == port_type:
                if port.is_motorized and (port.constraints.min <= value <= port.constraints.max):
                    self._slit_width[port_type] = value