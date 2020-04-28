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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class SpectrometerInterface(metaclass=InterfaceMetaclass):
    """
    This is the Interface class to define the controls for spectrometer hardware
    """

    @abstract_interface_method
    def get_constraints(self):
        """Returns all the fixed parameters of the hardware which can be used by the logic.

        @return: (dict) constraint dict : {

            'optical_parameters' : (tuple) (focal_length, angular_deviation, focal_tilt)
                            focal_length : focal length in m
                             angular_deviation : angular deviation in rad
                              focal_tilt : focal tilt in rad
            give the optical parameters (in s.i) used to measure the wavelength dispersion of the spectrometer,

            'gratings_info' : (list) [(tuple) (ruling, blaze), ..] give the gratings info for any gratings installed
            with position corresponding to grating index,

            'number_of_gratings' : (int) give the number of gratings installed (ex:3),

            'wavelength_limits' : (list) [[(float) wavelength_min, (float) wavelength_max], .. ] give the list of
             the wavelength limits for any gratings installed with position corresponding to grating index,

            'available_port' : (list) [[(int) input port, ..], [(int) output port, ..]] give the available
            input (1st list) and output (2nd port) ports in the spectrometer,

            'auto_slit_installed' : (list) [[(bool) input slit installed, ..], [(bool) output slit installed, ..]]
            give if the related input (1st list) and output (2nd list ) ports has motorized auto slit installed.

            (optional) : let this key empty if no shutter is installed !
            'shutter_modes' : (list) [(str) shutter_mode, ..] give the shutter modes available if any
            shutter is installed.
            }
        """
        pass

    ##############################################################################
    #                            Gratings functions
    ##############################################################################

    @abstract_interface_method
    def get_grating_number(self):
        """Returns the current grating identification (0 to self.get_number_gratings-1)
        """
        pass

    @abstract_interface_method
    def set_grating_number(self, grating):
        """Sets the required grating (0 to self.get_number_gratings-1)

        @param (int) grating: grating identification number
        @return: void
        """
        pass

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################

    @abstract_interface_method
    def get_wavelength(self):
        """Returns the central current wavelength (m)

        @return (float) wavelength (m)
        """
        pass

    @abstract_interface_method
    def set_wavelength(self, wavelength):
        """Sets the new central wavelength (m)

        @params (float) wavelength (m)
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

    def get_shutter_status(self):
        """Getter method returning the shutter mode.

        @return: (str) shutter mode (must be compared to the list)
        """
        pass

    def set_shutter_status(self, shutter_mode):
        """Setter method setting the shutter mode.

        @param shutter_mode: (str) shutter mode (must be compared to the list)
        @return: nothing
        """
        pass
