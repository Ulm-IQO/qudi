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
    def get_constraint(self):
        """Returns all the fixed parameters of the hardware which can be used by the logic.

        @return: (dict) constraint dict : {'number_of_gratings' : 3,
                    'wavelength_limits' : [[wavelength_min1, wavelength_max1], ... ],
                    'auto_slit_installed' : [[front input slit, side input slit], [front output slit, side output slit]],
                    'flipper_mirror_installed' : [input port, output port]}
        """
        pass

    ##############################################################################
    #                            Gratings functions
    ##############################################################################

    @abstract_interface_method
    def get_grating(self):
        """Returns the current grating identification (0 to self.get_number_gratings-1)
        """
        pass

    @abstract_interface_method
    def set_grating(self, grating):
        """Sets the required grating (0 to self.get_number_gratings-1)

        @param (int) grating: grating identification number
        @return: void
        """
        pass

    @abstract_interface_method
    def get_grating_offset(self, grating):
        """Returns the grating offset (unit is motor steps)

        @param (int) grating (between 0 and number_of_gratings)
        @return (int) grating offset (step)
        """
        pass

    @abstract_interface_method
    def set_grating_offset(self, grating, offset):
        """Sets the grating offset (unit is motor step)

        @param (int) grating : grating id (0..self.get_number_gratings()
                (int) offset : grating offset (step)
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
    #                            Calibration functions
    ##############################################################################

    @abstract_interface_method
    def get_calibration(self):
        """Returns the wavelength calibration of each pixel (m)

        @return: (ndarray) wavelength range for all the pixels of the camera
        """
        pass

    @abstract_interface_method
    def set_calibration(self, number_of_pixels, pixel_width, tracks_offset):
        """Returns the wavelength calibration of each pixel (m).

        @param number_of_pixels: (int) number of pixels in the horizontal direction
        @param pixel_width: (float) camera pixel width
        @param tracks_offset: (int) camera pixel matrix offset
        @return: nothing
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
    def get_auto_slit_width(self, flipper, port):
        """Returns the input slit width (um) in case of a motorized slit.

        @param flipper: (str) within ['input', 'output']
        @param port: (int) 0 for front or 1 for side port
        @return:  (int) offset - slit width, unit is meter (SI)
        """
        pass

    @abstract_interface_method
    def set_auto_slit_width(self, flipper, port, slit_width):
        """Sets the new slit width for the required slit.

        @param flipper: (str) within ['input', 'output']
        @param port: (int) 0 for front or 1 for side port
        @param slit_width: (float) slit width unit is meter (SI)
        :return: nothing
        """
        pass
