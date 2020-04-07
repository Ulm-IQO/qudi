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

    ##############################################################################
    #                            Gratings functions
    ##############################################################################

    @abstract_interface_method
    def get_grating(self):
        """
        Returns the current grating identification (0 to self.get_number_gratings-1)
        """
        pass

    @abstract_interface_method
    def set_grating(self, grating):
        """
        Sets the required grating (0 to self.get_number_gratings-1)

        @param int grating: grating identification number
        @return: void
        """
        pass

    @abstract_interface_method
    def get_number_gratings(self):
        """
        Returns the number of gratings in the spectrometer

        @return int number_of_gratings
        """
        pass

    @abstract_interface_method
    def get_grating_offset(self, grating):
        """
        Returns the grating offset (unit is motor steps)

        @param int grating (between 0 and number_of_gratings)
        @return int grating offset (step)
        """
        pass

    @abstract_interface_method
    def set_grating_offset(self, grating, offset):
        """
        Sets the grating offset (unit is motor step)

        @param int grating : grating id (0..self.get_number_gratings()
                int offset : grating offset (step)
        """
        pass

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################

    @abstract_interface_method
    def get_wavelength(self):
        """
        Returns the central current wavelength (m)
        @return float wavelength (m)
        """
        pass

    @abstract_interface_method
    def set_wavelength(self, wavelength):
        """
        Sets the new central wavelength
        @params float wavelength (m)
        """

        pass

    @abstract_interface_method
    def get_wavelength_limit(self, grating):
        """
        Returns the wavelength limits (m) of the grating (0-self.get_number_gratings)
        @params int grating
        """
        pass

    @abstract_interface_method
    def get_calibration(self, number_pixels):
        """
        Returns the wavelength calibration of each pixel (m)
        @params int number_pixels
        """
        pass

    @abstract_interface_method
    def get_number_of_pixels(self):
        """
        Returns the number of pixel that has to be previously set with self.set_number_of_pixels()
        :return: int pixel number
        """
        pass

    @abstract_interface_method
    def set_number_of_pixels(self, number_of_pixels):
        """
        Sets the number of pixels of the detector (to prepare for calibration)
        :param number_of_pixels: int
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_pixel_width(self):
        """
        Returns the pixel width along dispersion axis.
        Note that pixel width has to be previously set with self.set_pixel_width(width)
        :return: int pixel number
        """
        pass

    @abstract_interface_method
    def set_pixel_width(self, width):
        """
        Sets the pixel width along the dispersion axis (to prepare for calibration)
        :param width: float unit is m
        :return: nothing
        """
        pass

    ##############################################################################
    #                            Detector functions
    ##############################################################################

    @abstract_interface_method
    def get_detector_offset(self):
        """
        Returns the detector offset in pixels
        :return: int offset
        """
        pass

    @abstract_interface_method
    def set_detector_offset(self, offset):
        """
        Sets the detecotor offset in pixels
        :param offset : int
        :return: nothing
        """
        pass

    ##############################################################################
    #                        Ports and Slits functions
    ##############################################################################

    @abstract_interface_method
    def flipper_mirror_is_present(self, flipper):
        """
        Returns 1 if flipper mirror is present, 0 if not

        :param flipper: int 1 is for input, 2 is for output
        :return: 1 or 0
        """

        pass

    @abstract_interface_method
    def get_input_port(self):
        """
        Returns the current port for the input flipper mirror.
        0 is for front port, 1 is for side port
        in case of no flipper mirror, front port (0) is used
        """
        pass

    @abstract_interface_method
    def set_input_port(self, input_port):
        """
        Sets the input port - 0 is for front port, 1 is for side port

        :param input_port: int. has to be in [0, 1]
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_output_port(self):
        """
        Returns the current port for the output flipper mirror.
        0 is for front port, 1 is for side port
        in case of no flipper mirror, front port (0) is used
        """
        pass

    @abstract_interface_method
    def set_output_port(self, output_port):
        """
        Sets the input port - 0 is for front port, 1 is for side port

        :param input_port: int. has to be in [0, 1]
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_auto_slit_width(self, flipper, port):
        """
        Returns the input slit width (um) in case of a motorized slit,
        :param  string flipper - within ['input', 'output']
                int port - within[0,1] for front or side port
        :return  int offset - slit width, unit is meter (SI)
        """
        pass

    @abstract_interface_method
    def set_auto_slit_width(self, flipper, port, slit_width):
        """
        Sets the new slit width for the required slit
        :param flipper: string flipper - within ['input', 'output']
        :param port: int - within[0,1] for front or side port
        :param slit_width: float - unit is meter (SI)
        :return: nothing
        """
        pass

    @abstract_interface_method
    def auto_slit_is_present(self, flipper, port):
        """
        Return whether the required slit is present or not
        :param flipper: string flipper - within ['input', 'output']
        :param port: int - within[0,1] for front or side port
        :return: 1 if present, 0 if not
        """
        pass

