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

    @abstract_interface_method
    def get_constraint(self):
        """Returns all the fixed parameters of the hardware which can be used by the logic.

        @return: (dict) constraint dict : {

            'name' : (str) give the camera manufacture name (ex : 'Newton940')

            'image_size' : (tuple) ((int) image_width, (int) image_length) give the camera image size in pixels units,

            'pixel_size' : (tuple) ((float) pixel_width, (float) pixel_length) give the pixels size in m,

            'read_modes' : (list) [(str) read_mode, ..] give the available read modes of the camera (ex : ['FVB']),

            'internal_gains' : (list) [(float) gain, ..] give the available internal gain which can be set
            to the camera preamplifier,

            'trigger_modes' : (list) [(str) trigger_mode, ..] give the available trigger modes of the camera,

            'has_cooler' : (bool) give if the camera has temperature controller installed,

            (optional) : let this key empty if no shutter is installed !
            'shutter_modes' : (ndarray) [(str) shutter_mode, ..] give the shutter modes available if any
            shutter is installed.

        """
        pass

    ##############################################################################
    #                           Basic functions
    ##############################################################################

    @abstract_interface_method
    def start_acquisition(self):
        """ Start a single acquisition

        @return: nothing
        """
        pass

    @abstract_interface_method
    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return: (ndarray) image data in format [[row],[row]...]
        Each pixel might be a float, integer or sub pixels
        """
        pass

    ##############################################################################
    #                           Read mode functions
    ##############################################################################

    @abstract_interface_method
    def get_read_mode(self):
        """Getter method returning the current read mode used by the camera.

        @return: (str) read mode
        """
        pass

    @abstract_interface_method
    def set_read_mode(self, read_mode):
        """Setter method setting the read mode used by the camera.

        @param read_mode: (str) read mode
        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_readout_speed(self):
        pass

    @abstract_interface_method
    def set_readout_speed(self, readout_speed):
        pass

    @abstract_interface_method
    def get_active_tracks(self):
        """Getter method returning the read mode tracks parameters of the camera.

        @return: (ndarray) active tracks positions [1st track start, 1st track end, ... ]
        """
        pass

    @abstract_interface_method
    def set_active_tracks(self, active_tracks):
        """
        Setter method setting the read mode tracks parameters of the camera.

        @param active_tracks: (ndarray) active tracks positions [((int) start row, (int) end row ), ... ]
        in pixel unit.
        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_active_image(self):
        """Getter method returning the read mode image parameters of the camera.

        @return: (ndarray) active image parameters [hbin, vbin, hstart, hend, vstart, vend]
        """
        pass

    @abstract_interface_method
    def set_active_image(self,hbin, vbin, hstart, hend, vstart, vend):
        """Setter method setting the read mode image parameters of the camera.

        @param hbin: (int) horizontal pixel binning
        @param vbin: (int) vertical pixel binning
        @param hstart: (int) image starting row
        @param hend: (int) image ending row
        @param vstart: (int) image starting column
        @param vend: (int) image ending column
        @return: nothing
        """
        pass

    ##############################################################################
    #                           Acquisition mode functions
    ##############################################################################

    @abstract_interface_method
    def get_gain(self):
        """ Get the gain.

        @return: (float) exposure gain
        """
        pass

    @abstract_interface_method
    def set_gain(self, gain):
        """ Set the gain.

        @param camera_gain: (float) desired new gain

        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_exposure_time(self):
        """ Get the exposure time in seconds

        @return: (float) exposure time
        """
        pass

    @abstract_interface_method
    def set_exposure_time(self, exposure_time):
        """ Set the exposure time in seconds.

        @param exposure_time: (float) desired new exposure time

        @return: nothing
        """
        pass

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################

    @abstract_interface_method
    def get_trigger_mode(self):
        """Getter method returning the current trigger mode used by the camera.

        @return: (str) trigger mode (must be compared to the list)
        """
        pass

    @abstract_interface_method
    def set_trigger_mode(self, trigger_mode):
        """Setter method setting the trigger mode used by the camera.

        @param trigger_mode: (str) trigger mode (must be compared to the list)
        @return: nothing
        """
        pass

    ##############################################################################
    #                        Shutter mode function (optional)
    ##############################################################################
    # Shutter mode function are used in logic only if the camera constraints
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

    ##############################################################################
    #                           Temperature functions
    ##############################################################################

    @abstract_interface_method
    def get_cooler_status(self):
        """Getter method returning the cooler status if ON or OFF.

        @return: (int) 1 if ON or 0 if OFF
        """
        pass

    @abstract_interface_method
    def set_cooler_status(self, cooler_status):
        """Getter method returning the cooler status if ON or OFF.

        @param cooler_status: (bool) 1 if ON or 0 if OFF
        @return: nothing
        """
        pass

    @abstract_interface_method
    def get_temperature(self):
        """Getter method returning the temperature of the camera.

        @return: (float) temperature
        """
        pass

    @abstract_interface_method
    def set_temperature(self, temperature):
        """Getter method returning the temperature of the camera.

        @param temperature: (float) temperature
        @return: nothing
        """
        pass