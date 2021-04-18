# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

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

import time
import numpy as np
from PySide2 import QtCore
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.module import LogicBase


class CameraLogic(LogicBase):
    """
    Control a camera.
    """

    # declare connectors
    _camera = Connector(name='camera', interface='CameraInterface')
    # declare config options
    _minimum_exposure_time = ConfigOption(name='minimum_exposure_time',
                                          default=0.05,
                                          missing='warn')

    # signals
    sigFrameChanged = QtCore.Signal(object)
    sigAcquisitionFinished = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.__timer = None
        self._thread_lock = RecursiveMutex()
        self._exposure = -1
        self._gain = -1
        self._last_frame = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # delay timer for querying camera
        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(1000 * self._query_interval)
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self._query_loop_body, QtCore.Qt.QueuedConnection)

        self.camera = self._camera()
        self._settings = self.get_settings()

        self.__timer = QtCore.QTimer()
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self.__acquire_video_frame)

    def on_deactivate(self):
        """ Perform required deactivation. """
        self.__timer.stop()
        self.__timer.timeout.disconnect()
        self.__timer = None

    # functions for configuration of the camera
    @property
    def get_settings(self):
        """
        Bundle all the information about the camera into a dictionary.
        This dictionary later on serves as meta data for the image
        acquisition and initialisation and updating of the settings GUI.
        @return:
        """
        initial_settings = dict()

        return initial_settings

    @property
    def name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        try:
            camera_name = self._camera.name
        except:
            self.log.error('Could not retrieve the name of the camera.')
        return camera_name

    @property
    def size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        try:
            sensor_area = self._camera.size
        except:
            self.log.error('Could not retrieve the sensor area of the camera.')
        return sensor_area

    @property
    def state(self):
        """ Is the camera ready for an acquisition ?
        @return bool: ready ?
        """
        try:
            state = self._camera.state
        except:
            self.log.error('Could not retrieve the state of the camera.')
        return state

    @property
    def binning_available(self):
        """
        Does the camera support binning?
        @return:
        """
        try:
            binning = self._camera.binning_available
        except:
            self.log.error('Could not find out if binning is available for camera {}'.format(self.name))
        return binning

    @property
    def crop_available(self):
        """
        Does the camera support image cropping.
        @return:
        """
        try:
            cropping = self._camera.crop_available
        except:
            self.log.error('Could not find out if cropping is available for camera {}'.format(self.name))
        return cropping

    @property
    def exposure(self):
        """ Get the exposure time in seconds

            @return float exposure time
        """
        try:
            exposure = self._camera.crop_available
        except:
            self.log.error('Could not get the exposure time from the camera {}'.format(self.name))
        return exposure

    @exposure.setter
    def exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time
        """
        try:
            self._camera.exposure(exposure)
        except:
            self.log.error('Could not set the exposure time for the camera {}'.format(self.name))
        return

    @property
    def available_amplifiers(self):
        """
        Return a list of amplifiers the camera has
        @return list amplifiers: list of amplifiers
        """
        try:
            available_amplifers = self._camera.available_amplifiers
        except:
            self.log.error('Could not read the available amplifiers from the camera {}'.format(self.name))
        return available_amplifers

    @property
    def amplifiers(self):
        """
        Return the list of currently used amplifiers and their gains
        @return:
        """
        try:
            available_amplifers = self._camera.available_amplifiers
        except:
            self.log.error('Could not read the used amplifiers from the camera {}'.format(self.name))
        return available_amplifers

    @amplifiers.setter
    def amplifiers(self, amp_gain_dict):
        """
        Set up the chain of amplifiers with their gains
        @param list amp_gain_dict: List of the amplifiers to be set
        @return float: boolean success?
        """
        try:
            self._camera.amplifiers(amp_gain_dict)
        except:
            self.log.error('Could not set the amplifiers for the camera {}'.format(self.name))
        return

    @property
    def available_readout_speeds(self):
        """
        Readout speeds on the device
        @return: list of available readout speeds on the device
        """
        try:
            available_readout_speeds = self._camera.available_readout_speeds
        except:
            self.log.error('Could not read the available readout speeds from the camera {}'.format(self.name))
        return available_readout_speeds

    @property
    def readout_speeds(self):
        """
        Get the current readout speed e.g. {'horizontal': 1e6, 'vertical':3e6} in Hz
        @return dict readout_speeds: Dictionary with horizontal
                                     and vertical readout speed
        """
        try:
            readout_speeds = self._camera.readout_speeds
        except:
            self.log.error('Could not read the readout speeds used from the camera {}'.format(self.name))
        return readout_speeds

    @readout_speeds.setter
    def readout_speeds(self, speed_dict):
        """
        Set the readout speed e.g. {'horizontal': 10e6, 'vertical':1e6} in Hz
        @param speed_dict:
        """
        try:
            self._camera.readout_speeds(speed_dict)
        except:
            self.log.error('Could not set the readout speeds for the camera {}'.format(self.name))
        return

    @property
    def readout_time(self):
        """
        Return how long the readout of a single image will take
        @return float time: Time it takes to read out an image from the sensor
        """
        try:
            readout_time = self._camera.readout_time
        except:
            self.log.error('Could not get the readout time from the camera {}'.format(self.name))
        return readout_time

    @property
    def sensor_area_settings(self):
        """
        Return the current binning and crop settings of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)}
        @return: dict of the sensor area settings
        """
        try:
            sensor_area_settings = self._camera.sensor_area_settings
        except:
            self.log.error('Could not get the sensor area settings for the camera {}'.format(self.name))
        return sensor_area_settings

    @sensor_area_settings.setter
    def sensor_area_settings(self, settings):
        """
        Binning and extracting a certain part of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)} takes 4 pixels
        together to 1 and takes from all the pixels and area of 128 by 256
        """
        try:
            self._camera.sensor_area_settings(settings)
        except:
            self.log.error('Could not set the sensor area settings for the camera {}'.format(self.name))
        return

    @property
    def bit_depth(self):
        """
        Return the bit depth of the camera
        @return:
        """
        try:
            bit_depth = self._camera.bit_depth
        except:
            self.log.error('Could not get the bit depth of the camera {}'.format(self.name))
        return bit_depth

    @property
    def num_ad_channels(self):
        """
        Get the number of ad channels
        @return: int num_ad_channels: number of ad channels
        """
        try:
            num_ad_channels = self._camera.num_ad_channels
        except:
            self.log.error('Could not get the number of ad channels {}'.format(self.name))
        return num_ad_channels

    @property
    def ad_channel(self):
        """
        Return the currently used ad channel
        @return int ad_channel: Number used to identify channel
        """
        try:
            ad_channel = self._camera.ad_channel
        except:
            self.log.error('Could not get the current ad channel of the camera {}'.format(self.name))
        return ad_channel

    @ad_channel.setter
    def ad_channel(self, channel):
        """
        Depending if the camera has different ad converters select one.
        @param int channel: New channel to be used
        """
        try:
            self._camera.ad_channel(channel)
        except:
            self.log.error('Could not set the ad channel for the camera {}'.format(self.name))
        return

    @property
    def quantum_efficiency(self):
        """
        Return the quantum efficiency at a given wavelength.
        @param float wavelength: Wavelength of light falling on the sensor.
        @return: float quantum efficiency between 0 and 1
        """
        try:
            quantum_efficiency = self._camera.quantum_efficiency
        except:
            self.log.error('Could not get the quantum efficiency of the camera {}'.format(self.name))
        return quantum_efficiency

    @quantum_efficiency.setter
    def quantum_efficiency(self, wavelength):
        """
        Let the camera know which wavelength you are operating at.
        @param float wavelength: Wavelength of light falling on the sensor.
        """
        try:
            self._camera.quantum_efficiency(wavelength)
        except:
            self.log.error('Could not set the wavelength for the camera {}'.format(self.name))
        return

    @property
    def count_convert_mode(self):
        """
        Get the currently set count convert mode.
        The GUI will make use of this to display what is recorded.
        @return string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        """
        try:
            count_convert_mode = self._camera.count_convert_mode
        except:
            self.log.error('Could not get the count mode of the camera {}'.format(self.name))
        return count_convert_mode

    @count_convert_mode.setter
    def count_convert_mode(self, mode):
        """
        Return signal in 'Counts', 'Electrons' or 'Photons'
        @param string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        """
        try:
            self._camera.count_convert_mode(mode)
        except:
            self.log.error('Could not set the count convert mode for the camera {}'.format(self.name))
        return

    @property
    def available_readout_modes(self):
        """
        Readout modes on the device
        @return: list of available readout modes
        """
        try:
            available_readout_modes = self._camera.available_readout_modes
        except:
            self.log.error('Could not get the available readout modes of the camera {}'.format(self.name))
        return available_readout_modes

    @property
    def read_mode(self):
        """
        Get the read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @return string read_mode: string containing the current read_mode
        """
        try:
            read_mode = self._camera.read_mode
        except:
            self.log.error('Could not get the read mode of the camera {}'.format(self.name))
        return read_mode

    @read_mode.setter
    def read_mode(self, read_mode):
        """
        Set the read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @param str read_mode: Read mode to be set
        """
        try:
            self._camera.read_mode(read_mode)
        except:
            self.log.error('Could not set the read mode for the camera {}'.format(self.name))
        return

    @property
    def available_acquisition_modes(self):
        """
        Get the available acuqisitions modes of the camera
        @return: dict containing lists.
        The keys tell if they fall into 'Single Scan' or 'Series' category.
        """
        try:
             available_acquisition_modes = self._camera.available_acquisition_modes
        except:
            self.log.error('Could not get the available acquisition modes of the camera {}'.format(self.name))
        return available_acquisition_modes

    @property
    def acquisition_mode(self):
        """
        Get the acquisition mode of the camera
        @return: string acquisition mode of the camera
        """
        try:
            acquisition_mode = self._camera.acquisition_mode
        except:
            self.log.error('Could not get the acquisition mode of the camera {}'.format(self.name))
        return acquisition_mode

    @acquisition_mode.setter
    def acquisition_mode(self, acquisition_mode):
        """
        Set the readout mode of the camera (i.e. 'Single scan', 'Series' and 'Continuous')
        @param str acquisition_mode: readout mode to be set
        """
        try:
            self._camera.read_mode(acquisition_mode)
        except:
            self.log.error('Could not set the acquisition mode for the camera {}'.format(self.name))
        return

    @property
    def available_trigger_modes(self):
        """
        Trigger modes on the device
        @return: list of available trigger modes
        """
        try:
            available_trigger_modes = self._camera.available_trigger_modes
        except:
            self.log.error('Could not get the available trigger modes of the camera {}'.format(self.name))
        return available_trigger_modes

    @property
    def trigger_mode(self):
        """
        Get the currently used trigger mode
        @return: String of the set trigger mode
        """
        try:
            trigger_mode = self._camera.trigger_mode
        except:
            self.log.error('Could not get the trigger mode of the camera {}'.format(self.name))
        return trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode):
        """
        Set the trigger mode ('Internal', 'External' ... )
        @param str trigger_mode: Target trigger mode
        """
        try:
            self._camera.trigger_mode(trigger_mode)
        except:
            self.log.error('Could not set the trigger mode for the camera {}'.format(self.name))
        return

    @property
    def shutter_state(self):
        """
        Query the camera if a shutter exists.
        @return boolean: True if yes, False if not
        """
        try:
            shutter_state = self._camera.shutter_state
        except:
            self.log.error('Could not get the shutter state of the camera {}'.format(self.name))
        return shutter_state

    @shutter_state.setter
    def shutter_state(self, state):
        """
        Open the shutter
        """
        try:
            self._camera.shutter_state(state)
        except:
            self.log.error('Could not set the shutter state for the camera {}'.format(self.name))
        return

    @property
    def temperature(self):
        """
        Query the camera if it has temperature control
        @return boolen: True if yes, False if not
        """
        try:
            temperature = self._camera.temperature
        except:
            self.log.error('Could not get the temperature of the camera {}'.format(self.name))
        return temperature

    @temperature.setter
    def temperature(self, temperature):
        """
        Sets the temperature of the camera
        @param float temperature: Target temperature of the camera
        """
        try:
            self._camera.shutter_state(temperature)
        except:
            self.log.error('Could not set the temperature for the camera {}'.format(self.name))
        return