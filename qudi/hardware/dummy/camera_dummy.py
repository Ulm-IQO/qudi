# -*- coding: utf-8 -*-

"""
Dummy implementation for camera_interface.

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

import numpy as np
import time
from functools import reduce

from core.module import Base
from core.configoption import ConfigOption
from interface.camera_interface import CameraInterface

class CameraDummy(Base, CameraInterface):
    """ Dummy hardware for camera interface

    Example config for copy-paste:

    camera_dummy:
        module.Class: 'camera.camera_dummy.CameraDummy'
        support_live: True
        camera_name: 'Dummy camera'
        resolution: (1280, 720)
        exposure: 0.1
        gain: 1.0
    """
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # capabilities of the camera, in actual hardware many of these attributes should
        # be obtained by querying the camera on startup
        self._support_live = True
        self._support_binning = True
        self._support_crop = True
        self._camera_name = 'Dummy camera'
        self._sensor_area = (512, 512)
        # just for the generation of dummy data
        self._data_acquistion = 'random images'
        self._available_amplifiers = {'EM', 'preamp'}
        self._read_out_modes = ['Image', 'Cropped', 'FVB']
        self._available_acquistion_modes = {'Single Scan': ['single_scan'],
                                            'Series': ['kinetic_series']}
        self._available_read_out_speeds = {'horizontal': [1e6, 3e6, 9e6], 'vertical': [0.5e6, 1e6, 1.5e6]}
        self._available_trigger_modes = ['Internal', 'External', 'Software']
        self._has_shutter = True
        self._has_temperature_control = True
        self._bit_depth = 16
        self._wave_length = 640e-9
        self._num_ad_channels = 3
        self._ad_channel = 0
        self._count_convert_mode = 'Counts'

        # state of the 'Camera'
        self._live = False
        self._acquiring = False
        self._exposure = .1
        self._current_amplifiers = {'preamp': 4.0}
        self._binning = (2, 2)
        self._crop = ((100, 400), (0, 280))
        self._current_sensor_area = self._sensor_area
        self._read_out_speeds = {'horizontal': 1e6, 'vertical': 0.5e6}
        self._read_mode = 'Image'
        self._acquisition_mode = {'Series': 'kinetic_series'}
        self._num_sequences = 2
        self._num_images = 5
        self._exposures = [0.1 * i + 0.01 for i in range(10)]
        self._trigger_mode = 'Internal'
        self._sensor_temperature = 20
        self._sensor_setpoint_temperature = 20
        self._ambient_temperature = 20
        self._temperature_control = False
        self._cooling_speed = 0.04
        self._thermal_contact = 0.01
        self._time = 0.0
        self._start_time = 0.0
        self._internal_memory = np.zeros(self._sensor_area)
        self._start_temperature = self._ambient_temperature
        self._image_generation_method = 'random_images'

        if self._has_shutter:
            self._shutter = ConfigOption('shutter', True)
        else:
            self._shutter = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.set_up_sensor_area({'binning': self._binning, 'crop': self._crop})
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stop_acquisition()

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        return self._camera_name

    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        return self._sensor_area

    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        return not (self._live or self._acquiring)

    def binning_available(self):
        """
        Does the camera support binning?
        @return:
        """
        return self._support_binning

    def crop_available(self):
        """
        Does the camera support cropping the image.
        @return:
        """
        return self._support_crop

    def start_acquisition(self):
        """
        Start an acquisition. The acquisition settings
        will determine if you record a single image, or image sequence.

        @return int error code: (0:OK, -1:error)
        """
        self._acquiring = True
        qe = self.get_quantum_efficiency(self._wave_length)
        total_gain = self._get_total_gain(self.get_amplifiers())
        if 'Series' in self._acquisition_mode:
            self._internal_memory = np.zeros((self._num_sequences, self._num_images,
                                              self._current_sensor_area[0], self._current_sensor_area[1]))

            for seq_run in range(self._num_sequences):
                for image_ind in range(self._num_images):
                    image = self._image_generation(method=self._image_generation_method)
                    time.sleep(self._exposures[image_ind])
                    self._internal_memory[seq_run, image_ind, :, :] = qe * total_gain * self._exposures[image_ind]\
                                                                      * image

        elif self._acquisition_mode == 'Single Scan':
            image = self._image_generation(method=self._image_generation_method)
            time.sleep(self._exposures[0])
            self._internal_memory = qe * total_gain * self._exposures[0] * image
        else:
            self.log.error('Acquisition mode does not fall into existing categories.')
        self._acquiring = False

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        self._live = False
        self._acquiring = False
        return True

    def get_acquired_data(self):
        """ Return an array of the most recent image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        if self._data_acquistion == 'random images':
            data = np.random.random(self._current_sensor_area) * self._exposure * self._gain
        # TODO: implement other dummy methods to get images (i.e. take real world images)
        return data.transpose()

    def set_exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time
        @return float exposure: new exposure time
        """
        self._exposure = exposure
        return True

    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        return self._exposure

    def set_amplifiers(self, amp_gain_dict):
        """
        Set up the chain of amplifiers with their gains
        @param list amp_gain_dict: List of the amplifiers to be set
        @return float: boolean success?
        """
        self._current_amplifiers = amp_gain_dict
        return True

    def get_available_amplifiers(self):
        """
        Return a list of amplifiers the camera has
        @return list amplifiers: list of amplifiers
        """
        return self._available_amplifiers

    def get_amplifiers(self):
        """
        Return the list of currently used amplifiers and their gains
        @return:
        """
        return self._current_amplifiers

    def get_available_readout_speeds(self):
        """
        Readout speeds on the device
        @return: list of available readout speeds on the device
        """
        return self._available_read_out_speeds

    def set_readout_speeds(self, speed_dict):
        """
        Set the readout speed e.g. {'horizontal': 10e6, 'vertical':1e6} in Hz
        @param speed_dict:
        @return int error code: (0: OK, -1: error)
        """
        keys_to_update = set(speed_dict.keys()).intersection(set(self._available_read_out_speeds.keys()))
        for up_key in keys_to_update:
            new_speed = speed_dict[up_key]
            available_speeds = self._available_read_out_speeds[up_key]
            num_speeds = len(self._available_read_out_speeds[up_key])
            if np.any(np.isclose(np.repeat(new_speed, num_speeds), available_speeds)):
                self._read_out_speeds[up_key] = new_speed
            else:
                self.log.error('requested speed is not supported by hardware')
        return 0

    def get_readout_speeds(self):
        """
        Get the current readout speed e.g. {'horizontal': 1e6, 'vertical':3e6} in Hz
        @return dict readout_speeds: Dictionary with horizontal
                                     and vertical readout speed
        """
        return self._read_out_speeds

    def get_readout_time(self):
        """
        Return how long the readout of a single image will take
        @return float time: Time it takes to read out an image from the sensor
        """
        horizontal_readout_time = self._current_sensor_area[0] / self._read_out_speeds['horizontal']
        vertical_readout_time = self._current_sensor_area[1] / self._read_out_speeds['vertical']
        readout_time = self._current_sensor_area[1] * horizontal_readout_time + vertical_readout_time
        return readout_time

    def set_up_sensor_area(self, settings):
        """
        Binning and extracting a certain part of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)} takes 4 pixels
        together to 1 and takes from all the pixels and area of 128 by 256
        @return int error code: (0: OK, -1: error)
        """
        # TODO: Write this in a way that the
        if self._read_mode == 'Image':
            if 'binning' in settings:
                self._binning = settings['binning']
            if 'crop' in settings:
                self._crop = settings['crop']
            horizontal_coord, vertical_coord = self._crop[0], self._crop[1]
            horizontal = horizontal_coord[1] - horizontal_coord[0]
            vertical = vertical_coord[1] - vertical_coord[0]
            horizontal //= self._binning[0]
            vertical //= self._binning[1]
            self._current_sensor_area = (horizontal, vertical)
        elif self._read_mode == 'FVB':
            self._binning = (1, self._sensor_area[1])
            self._crop = ((1, self._sensor_area[0]), (1, self._sensor_area[1]))
        return 0

    def get_sensor_area_settings(self):
        """
        Return the current binning and crop settings of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)}
        @return: dict of the sensor area settings
        """
        if self._support_crop:
            area_settings = {'binning': self._binning, 'crop': self._crop}
        else:
            area_settings = {}
        return area_settings

    def get_bit_depth(self):
        """
        Return the current
        @return:
        """
        return self._bit_depth

    def get_num_ad_channels(self):
        """
        Get the number of ad channels
        @return: int num_ad_channels: number of ad channels
        """
        return self._num_ad_channels

    def set_ad_channel(self, channel):
        """
        Depending if the camera has different ad converters select one.
        @param int channel: New channel to be used
        @return int error code: (0: OK, -1: error)
        """
        self._ad_channel = channel
        return 0

    def get_ad_channel(self):
        """
        Return the currently used ad channel
        @return int ad_channel: Number used to identify channel
        """
        return self._ad_channel

    def get_quantum_efficiency(self, wavelength):
        """
        Return the quantum efficiency at a given wavelength.
        @param float wavelength: Wavelength of light falling on the sensor.
        @return: float quantum efficiency between 0 and 1
        """
        def lorentzian(x, amp, width, center):
            return amp / (1 + ((x - center) / width) ** 2)

        qe = lorentzian(wavelength, 1.0, 100e-9, 640e-9)

        return qe

    def set_operating_wavelength(self, wavelength):
        """
        Let the camera know which wavelength you are operating at.
        @param float wavelength: Wavelength of light falling on the sensor.
        @return int error code: (0:OK, -1:error)
        """
        self._wave_length = wavelength
        return 0

    def set_count_convert_mode(self, mode):
        """
        Return signal in 'Counts', 'Electrons' or 'Photons'
        @param string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        @return int error code: (0:OK, -1:error)
        """
        self._count_convert_mode = mode
        return 0

    def get_count_convert_mode(self):
        """
        Get the currently set count convert mode.
        The GUI will make use of this to display what is recorded.
        @return string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        """
        return self._count_convert_mode

    def get_available_readout_modes(self):
        """
        Readout modes on the device
        @return: list of available readout modes
        """
        return self._read_out_modes

    def set_read_mode(self, read_mode):
        """
        Set the read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @param str read_mode: Read mode to be set
        @return int error code: (0:OK, -1:error)
        """
        self._read_mode = read_mode
        return 0

    def get_read_mode(self):
        """
        Get the read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @return string read_mode: string containing the current read_mode
        """
        return self._read_mode

    def set_acquisition_mode(self, acquisition_mode):
        """
        Set the readout mode of the camera (i.e. 'single acquisition', 'kinetic series')
        @param str acquisition_mode: readout mode to be set
        @return int error code: (0:OK, -1:error)
        """
        if acquisition_mode in self._available_acquistion_modes['Single Scan']:
            self._acquisition_mode = {'Single scan': acquisition_mode}
        elif acquisition_mode in self._available_acquistion_modes['Series']:
            self._acquisition_mode = {'Series': acquisition_mode}
        return 0

    def get_acquisition_mode(self):
        """
        Get the acquisition mode of the camera
        @return: string acquisition mode of the camera
        """
        return self._acquisition_mode

    def get_available_acquisition_modes(self):
        """
        Get the available acuqisitions modes of the camera
        @return: dict containing lists.
        The keys tell if they fall into 'Single Scan' or 'Series' category.
        """
        return self._available_acquistion_modes

    def set_up_image_sequence(self, num_sequences, num_images, exposures):
        """
        Set up the camera for the acquisition of an image sequence.

        @param int num_sequences: Number of sequences to be recorded
        @param int num_images: Number of images to be taken
        @param list exposures: List of length(num_images) containing the exposures to be used
        @return int error code: (0:OK, -1:error)
        """
        if 'Series' in self._acquisition_mode:
            self._num_sequences = num_sequences
            self._num_images = num_images
            self._exposures = exposures
            return 0
        else:
            self.log.error('In the current acquisition mode '
                           'taking an image_sequence is not supported')
            return -1

    def acquire_image_sequence(self):
        """
        Reads image sequence from the camera
        @return: numpy nd array of dimension (seq_length, px_x, px_y)
        """
        return self._internal_memory

    def get_images(self, run_index, start_index, stop_index):
        """
        Read the images between start_index and stop_index from the buffer.

        @param int run_index: nth run of the sequence
        @param int start_index: Index of the first image
        @param int stop_index: Index of the last image
        @return: numpy nd array of dimension (stop_index - start_index, px_x, px_y)
        """
        return self._internal_memory[run_index, start_index: stop_index + 1, :, :]

    def get_available_trigger_modes(self):
        """
        Trigger modes on the device
        @return: list of available trigger modes
        """
        return self._available_trigger_modes

    def set_up_trigger_mode(self, trigger_mode):
        """
        Set the trigger mode ('Internal', 'External' ... )
        @param str trigger_mode: Target trigger mode
        @return int error code: (0:OK, -1:error)
        """
        self._trigger_mode = trigger_mode
        return 0

    def get_trigger_mode(self):
        """
        Get the currently used trigger mode
        @return: String of the set trigger mode
        """
        return self._trigger_mode

    def has_shutter(self):
        """
        Query the camera if a shutter exists.
        @return boolean: True if yes, False if not
        """
        return self._has_shutter

    def open_shutter(self):
        """
        Open the shutter
        @return int error code: (0:OK, -1:error)
        """
        if self._has_shutter:
            self._shutter = True
            return 0
        else:
            return -1

    def close_shutter(self):
        """
        Close the shutter if the camera has a shutter
        @return int error code: (0:OK, -1:error)
        """
        if self._has_shutter:
            self._shutter = False
            return 0
        else:
            return -1

    def has_temperature_control(self):
        """
        Query the camera if it has temperature control
        @return boolen: True if yes, False if not
        """
        return self._has_temperature_control

    def set_temperature(self, temperature):
        """
        Sets the temperature of the camera
        @param float temperature: Target temperature of the camera
        @return int error code: (0:OK, -1:error)
        """
        if self._has_temperature_control:
            self._sensor_setpoint_temperature = temperature
            return 0
        else:
            return -1

    def start_temperature_control(self):
        """
        Start the temperature control of the camera
        @return int error code: (0:OK, -1:error)
        """
        if self._has_temperature_control:
            self._temperature_control = True
            self._time = 0.0
            self._start_temperature = self._sensor_temperature
            return 0
        else:
            return -1

    def stop_temperature_control(self):
        """
        Stop the temperature control of the camera
        @return int error code: (0:OK, -1:error)
        """
        # TODO: Implement reheating to ambient temperature after stopping the cooling
        if self._has_temperature_control:
            self._temperature_control = False
            self._time = 0.0
            self._start_temperature = self._sensor_temperature
            return 0
        else:
            return -1

    def get_temperature(self):
        """
        Gets the temperature of the camera
        @return int error code: (0:OK, -1:error)
        """
        self._update_temperature()
        return self._sensor_temperature

    def _update_temperature(self):
        self._time = time.clock() + self._time
        init_temperature = self._start_temperature
        if self._temperature_control:
            target_temperature = self._sensor_setpoint_temperature
            effective_cooling = self._cooling_speed - self._thermal_contact

            self._sensor_temperature = target_temperature * \
                                       (1 - np.exp(-effective_cooling * self._time))\
                                       + init_temperature * np.exp(-effective_cooling * self._time)
        else:
            target_temperature = self._ambient_temperature
            self._time = time.clock() + self._time
            self._sensor_temperature = target_temperature * \
                                       (1 - np.exp(-self._thermal_contact * self._time)) \
                                       + init_temperature * np.exp(-self._thermal_contact * self._time)
        return

    def _image_generation(self, method='random_images'):
        if method == 'random_images':
            image = np.random.poisson(150e3, self._current_sensor_area)
        return image

    def _get_total_gain(self, amp_dict):
        return reduce(lambda x, y: x * y, [amp_dict[_] for _ in amp_dict], 1)
