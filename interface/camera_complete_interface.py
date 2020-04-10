# -*- coding: utf-8 -*-

"""
This file contains the updated Qudi Interface for a camera.


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


class CameraInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to manage and visualize a simple camera
    """

    ##############################################################################
    #                           Basic functions
    ##############################################################################

    @abstract_interface_method
    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        pass

    @abstract_interface_method
    def get_image_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        pass

    @abstract_interface_method
    def start_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        pass


    @abstract_interface_method
    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        pass

    ##############################################################################
    #                           Read mode functions
    ##############################################################################

    @abstract_interface_method
    def get_read_mode(self):
        """
        Getter method returning the current read mode used by the camera.

        :return: @str read mode (must be compared to a dict)
        """
        pass

    @abstract_interface_method
    def set_read_mode(self, read_mode):
        """
        Setter method setting the read mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_track_parameters(self):
        """
        Getter method returning the read mode tracks parameters of the camera.

        :return: @tuple (@int number of track, @int track height, @int track offset) or 0 if error
        """
        pass

    @abstract_interface_method
    def set_track_parameters(self, number_of_track, track_heigth, track_offset):
        """
        Setter method setting the read mode tracks parameters of the camera.

        :param number_of_track: @int number of track
        :param track_heigth: @int track height
        :param track_offset: @int track offset
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_image_parameters(self):
        """
        Getter method returning the read mode image parameters of the camera.

        :return: @tuple (@int pixel height, @int pixel width, @tuple (@int start raw, @int end raw),
        @tuple (@int start column, @int end column)) or 0 if error
        """
        pass

    @abstract_interface_method
    def set_image_parameters(self, pixel_height, pixel_width, raw_range, column_range):
        """
        Setter method setting the read mode image parameters of the camera.

        :param pixel_height: @int pixel height
        :param pixel_width: @int pixel width
        :param raw_range: @tuple (@int start raw, @int end raw)
        :param column_range: @tuple (@int start column, @int end column)
        :return: nothing
        """
        pass

    ##############################################################################
    #                           Acquisition mode functions
    ##############################################################################

    @abstract_interface_method
    def get_acquisition_mode(self):
        """
        Getter method returning the current acquisition mode used by the camera.

        :return: @str acquisition mode (must be compared to a dict)
        """
        pass

    @abstract_interface_method
    def set_acquisition_mode(self, acquisition_mode):
        """
        Setter method setting the acquisition mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :param kwargs: packed @dict which contain a series of arguments specific to the differents acquisition modes
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_accumulation_time(self):
        """
        Getter method returning the accumulation cycle time scan carry out during an accumulate acquisition mode
         by the camera.

        :return: @int accumulation cycle time or 0 if error
        """
        pass

    @abstract_interface_method
    def set_accumulation_time(self, accumulation_time):
        """
        Setter method setting the accumulation cycle time scan carry out during an accumulate acquisition mode
        by the camera.

        :param accumulation_time: @int accumulation cycle time
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_number_accumulated_scan(self):
        """
        Getter method returning the number of accumulated scan carry out during an accumulate acquisition mode
         by the camera.

        :return: @int number of accumulated scan or 0 if error
        """
        pass

    @abstract_interface_method
    def set_number_accumulated_scan(self, number_scan):
        """
        Setter method setting the number of accumulated scan carry out during an accumulate acquisition mode
         by the camera.

        :param number_scan: @int number of accumulated scan
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_exposure_time(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        pass

    @abstract_interface_method
    def set_exposure_time(self, exposure_time):
        """ Set the exposure time in seconds

        @param float time: desired new exposure time

        @return float: setted new exposure time
        """
        pass

    @abstract_interface_method
    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        pass

    @abstract_interface_method
    def set_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """
        pass

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################

    @abstract_interface_method
    def get_trigger_mode(self):
        """
        Getter method returning the current trigger mode used by the camera.

        :return: @str trigger mode (must be compared to a dict)
        """
        pass

    @abstract_interface_method
    def set_trigger_mode(self, trigger_mode):
        """
        Setter method setting the trigger mode used by the camera.

        :param trigger_mode: @str trigger mode (must be compared to a dict)
        :return: nothing
        """
        pass

    ##############################################################################
    #                           Shutter mode functions
    ##############################################################################

    @abstract_interface_method
    def shutter_is_open(self):
        """
        Getter method returning if the shutter is open.

        :return: @bool shutter open ?
        """
        pass

    @abstract_interface_method
    def shutter_is_open(self, shutter_open):
        """
        Setter method setting if the shutter is open.

        :param shutter_mode: @bool shutter open
        :return: nothing
        """
        pass

    ##############################################################################
    #                           Temperature functions
    ##############################################################################

    @abstract_interface_method
    def cooler_ON(self):
        """
        Getter method returning the cooler status if ON or OFF.

        :return: @bool True if ON or False if OFF or 0 if error
        """
        pass

    @abstract_interface_method
    def cooler_ON(self, cooler_ON):
        """
        Getter method returning the cooler status if ON or OFF.

        :cooler_ON: @bool True if ON or False if OFF
        :return: nothing
        """
        pass


    @abstract_interface_method
    def get_temperature(self):
        """
        Getter method returning the temperature of the camera.

        :return: @float temperature or 0 if error
        """
        pass

    @abstract_interface_method
    def set_temperature(self, temperature):
        """
        Getter method returning the temperature of the camera.

        :param temperature: @float temperature or 0 if error
        :return: nothing
        """
        pass