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
    def get_size(self):
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
    def set_read_mode(self, read_mode, **kwargs):
        """
        Setter method setting the read mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :param kwargs: packed @dict which contain a series of arguments used by the differents read modes
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
    def set_acquisition_mode(self, acquisition_mode, **kwargs):
        """
        Setter method setting the acquisition mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :param kwargs: packed @dict which contain a series of arguments specific to the differents acquisition modes
        :return: nothing
        """
        pass

    @abstract_interface_method
    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        pass

    @abstract_interface_method
    def set_exposure(self, exposure):
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
    def set_trigger_mode(self, trigger_mode, **kwargs):
        """
        Setter method setting the trigger mode used by the camera.

        :param trigger_mode: @str trigger mode (must be compared to a dict)
        :param kwargs: packed @dict which contain a series of arguments specific to the differents trigger modes
        :return: nothing
        """
        pass

