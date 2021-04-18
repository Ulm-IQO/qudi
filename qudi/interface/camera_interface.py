# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface for a camera.


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

from enum import IntEnum
from qudi.core.interface import abstract_interface_method
from qudi.core.meta import InterfaceMetaclass

class ShutterState(IntEnum):
    CLOSED = 0
    OPEN = 1
    NO_SHUTTER = 2
    UNKNOWN = 3

class AcqusitionState(IntEnum):
    SINGLE_IMAGE = 0
    IMAGE_SEQUENCE = 1
    VIDEO = 2
    UNKNOWN = 3

class TemperatureState(IntEnum):
    OFF = 0
    ON = 1
    NO_CONTROL = 2
    UNKNOWN = 3

class TriggerState(IntEnum):
    SOFTWARE = 0
    INTERNAL = 1
    EXTERNAL = 2
    UNKNOWN = 3

class CameraState(IntEnum):
    OFF = 0
    ON = 1
    LOCKED = 2
    UNKNOWN = 3

class AcquisitionMode(IntEnum):
    SINGLE_ACQUSITION = 0
    CONTINUOUS_ACQUSITION = 1
    SEQUENCE_ACQUISITION = 2

class CameraInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to manage and visualize a simple camera
    """

    @property
    @abstract_interface_method
    def name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        pass

    @property
    @abstract_interface_method
    def size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        pass

    @property
    @abstract_interface_method
    def state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        pass

    @property
    @abstract_interface_method
    def binning_available(self):
        """
        Given the current state of the camera (selected settings ) is
        hardware wise binning possible.
        @return bool avail: True if yes False if No
        """
        pass

    @property
    @abstract_interface_method
    def crop_available(self):
        """
        Given the current state of the camera (selected settings) is
        hardware wise crop possible
        """
        pass

    @abstract_interface_method
    def start_acquisition(self):
        """
        Start an acquisition. The acquisition settings
        will determine if you record a single image, or image sequence.
        """
        pass

    @abstract_interface_method
    def stop_acquisition(self):
        """
        Stop/abort live or single acquisition

        @return bool: Success ?
        """
        pass

    @property
    @abstract_interface_method
    def exposure(self):
        """
        Set the exposure time in seconds

        @param float exposure: desired new exposure time

        @return float:  bool success ?
        """
        pass

    @property
    @abstract_interface_method
    def available_amplifiers(self):
        """
        Return a list of available amplifiers
        @return list amplifiers: List of the available amplifiers
        """
        pass

    @property
    @abstract_interface_method
    def amplifiers(self):
        """
        Set up the chain of amplifiers with corresponding gains
        @return dict amp_gain_dict: the amplifiers comprise the keys and their corresponding
                                    gain values as values
        """
        pass

    @property
    @abstract_interface_method
    def available_readout_speeds(self):
        """
        Readout speeds the device is capable of.
        @return: list of available readout speeds on the device
        """
        pass

    @property
    @abstract_interface_method
    def readout_speeds(self):
        """
        @return the readout speed e.g. {'horizontal': 10e6, 'vertical':1e6} in Hz
        """
        pass

    @property
    @abstract_interface_method
    def readout_time(self):
        """
        Return how long the readout of a single image will take
        @return float time: Time it takes to read out an image from the sensor
        """
        pass

    @property
    @abstract_interface_method
    def sensor_area_settings(self):
        """
        Binning and extracting a certain part of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)} takes 4 pixels
        together to 1 and takes from all the pixels and area of 128 by 256
        """
        pass

    @property
    @abstract_interface_method
    def bit_depth(self):
        """
        Bit depth the camera has
        Return the current
        @return int bit_depth: Number of bits the AD converter has.
        """
        pass

    @property
    @abstract_interface_method
    def num_ad_channels(self):
        """
        Get the number of ad channels
        @return int num_ad_channels: number of ad channels
        """
        pass

    @property
    @abstract_interface_method
    def ad_channel(self):
        """
        Currently used ad channel
        @param int channel: Return currently used channel
        """
        pass

    @property
    @abstract_interface_method
    def quantum_efficiency(self):
        """
        Return the quantum efficiency at a given wavelength.
        @return: float quantum efficiency between 0 and 1
        """
        pass

    @property
    @abstract_interface_method
    def count_convert_mode(self):
        """
        Some cameras can be set up to show different outputs.
        @return string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        """
        pass

    @property
    @abstract_interface_method
    def available_readout_modes(self):
        """
        Readout modes on the device
        @return: list read_modes: containing available readout modes
        """
        pass

    @property
    @abstract_interface_method
    def read_mode(self):
        """
        Read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @return str read_mode: Read mode of the device
        """
        pass

    @property
    @abstract_interface_method
    def available_acquisition_modes(self):
        """
        Get the available acquisitions modes of the camera
        The keys consist of the acquisition modes and the values are 'Single Scan', 'Series', 'Continuous'.
        """
        pass

    @property
    @abstract_interface_method
    def acquisition_mode(self):
        """
        Acquisition mode of the camera
        """
        pass

    @abstract_interface_method
    def set_up_image_sequence(self, num_sequences, num_images, exposures):
        """
        Set up the camera for the acquisition of an image sequence.

        @param int num_sequences: Number of sequences to be recorded
        @param int num_images: Number of images to be taken
        @param list exposures: List of length(num_images) containing the exposures to be used
        """
        pass

    @abstract_interface_method
    def get_images(self, image_num):
        """
        Get image_num oldest images from the memory.
        @param int image_num: Number of images requested
        @return: numpy nd array of dimension (image_num, px_x, px_y)
        """
        pass

    @property
    @abstract_interface_method
    def available_trigger_modes(self):
        """
        Trigger modes on the device
        @return: list of available trigger modes
        """
        pass

    @property
    @abstract_interface_method
    def trigger_mode(self):
        """
        The currently used trigger mode
        @return: String of the set trigger mode
        """
        pass

    @property
    @abstract_interface_method
    def shutter_sate(self):
        """
        Return the current shutter state
        """
        pass

    @property
    @abstract_interface_method
    def temperature(self):
        """
        The temperature of the camera
        @param float temperature: Temperature of the camera
        """
        pass

    @abstract_interface_method
    def start_temperature_control(self):
        """
        Start the temperature control of the camera
        """
        pass

    @abstract_interface_method
    def stop_temperature_control(self):
        """
        Stop the temperature control of the camera
        """
        pass



