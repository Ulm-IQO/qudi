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

from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.interface.camera_interface import CameraInterface, ShutterState,\
    TemperatureState, TriggerState, CameraState, AcquisitionMode

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

        # Presets from the ENUM classes
        self._shutter = ShutterState.CLOSED
        self._temperature_control = TemperatureState.OFF
        self._trigger_mode = TriggerState.SOFTWARE
        self._camera_state = CameraState.ON
        self._acqusition_mode = AcquisitionMode.SINGLE_ACQUSITION
        # Defaults of the camera
        self._support_live = True
        self._support_binning = True
        self._support_crop = True
        self._camera_name = 'Dummy camera'
        self._sensor_area = (512, 512)
        # just for the generation of dummy data
        self._data_acquistion = 'random images'
        self._available_amplifiers = {'EM', 'preamp'}
        self._read_out_modes = ['Image', 'Cropped', 'FVB']
        self._available_acquistion_modes = {'Single Scan': ['SINGLE_SCAN'],
                                            'Series': ['KINETIC_SERIES'],
                                            'Continuous': ['RUN_TILL_ABORT']}
        self._available_read_out_speeds = {'horizontal': [1e6, 3e6, 9e6], 'vertical': [0.5e6, 1e6, 1.5e6]}
        self._available_trigger_modes = ['Internal', 'External', 'Software']
        self._has_shutter = True
        self._has_temperature_control = True
        self._bit_depth = 16
        self._wavelength = 640e-9
        self._num_ad_channels = 3
        self._ad_channel = 0
        self._count_convert_mode = 'Counts'

        # state of the 'Camera'
        self._live = False
        self._acquiring = False
        self._measurement_start = 0.0
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
        self._trigger_mode = TriggerState.INTERNAL

        # internal dummy variables
        self._sensor_temperature = 20
        self._sensor_setpoint_temperature = 20
        self._ambient_temperature = 20
        self._temperature_control = False
        self._cooling_speed = 0.04
        self._thermal_contact = 0.01
        self._time = 0.0
        self._start_time = 0.0
        self._camera_memory = None
        self._start_temperature = self._ambient_temperature
        self._image_generation_method = 'random_images'
        # variable to only allow reading of images within the exposure time limit
        self._available_images = 0

        self._shutter = ConfigOption('shutter', 1)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # TODO: Try except statements to capture
        # errors from hardware side
        self.sensor_area = {'binning': self._binning, 'crop': self._crop}
        # Shutter
        self.shutter_state = self._shutter
        # Trigger
        self.trigger_mode = self._trigger_mode
        # Camera State
        if self.state:
            self._camera_state = CameraState.ON
        else:
            self._camera_state = CameraState.LOCKED

        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stop_acquisition()

    @property
    def name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        return self._camera_name

    @property
    def size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        return self._sensor_area

    @property
    def state(self):
        """ Is the camera ready for an acquisition ?
        @return bool: ready ?
        """
        if self._acquiring:
            cur_time = time.time()
            dur = cur_time - self._measurement_start

            if dur < self._total_acquisition_time:
                self._acquiring = False
                return False
        else:
            return True

    @property
    def binning_available(self):
        """
        Does the camera support binning?
        @return:
        """
        return self._support_binning

    @property
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
        """
        self._measurement_start = time.time()
        self._acquiring = True

        return

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        self._live = False
        self._acquiring = False
        return True

    @property
    def exposure(self):
        """ Get the exposure time in seconds

            @return float exposure time
        """
        return self._exposure

    @exposure.setter
    def exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time
        """
        self._exposure = exposure
        return

    @property
    def available_amplifiers(self):
        """
        Return a list of amplifiers the camera has
        @return list amplifiers: list of amplifiers
        """
        return self._available_amplifiers

    @property
    def amplifiers(self):
        """
        Return the list of currently used amplifiers and their gains
        @return:
        """
        return self._current_amplifiers

    @amplifiers.setter
    def amplifiers(self, amp_gain_dict):
        """
        Set up the chain of amplifiers with their gains
        @param list amp_gain_dict: List of the amplifiers to be set
        @return float: boolean success?
        """
        self._current_amplifiers = amp_gain_dict
        return

    @property
    def available_readout_speeds(self):
        """
        Readout speeds on the device
        @return: list of available readout speeds on the device
        """
        return self._available_read_out_speeds

    @property
    def readout_speeds(self):
        """
        Get the current readout speed e.g. {'horizontal': 1e6, 'vertical':3e6} in Hz
        @return dict readout_speeds: Dictionary with horizontal
                                     and vertical readout speed
        """
        return self._read_out_speeds

    @readout_speeds.setter
    def readout_speeds(self, speed_dict):
        """
        Set the readout speed e.g. {'horizontal': 10e6, 'vertical':1e6} in Hz
        @param speed_dict:
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
        return

    @property
    def readout_time(self):
        """
        Return how long the readout of a single image will take
        @return float time: Time it takes to read out an image from the sensor
        """
        horizontal_readout_time = self._current_sensor_area[0] / self._read_out_speeds['horizontal']
        vertical_readout_time = self._current_sensor_area[1] / self._read_out_speeds['vertical']
        readout_time = self._current_sensor_area[1] * horizontal_readout_time + vertical_readout_time
        return readout_time

    @property
    def sensor_area_settings(self):
        """
        Return the current binning and crop settings of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)}
        @return: dict of the sensor area settings
        """
        if self._support_crop:
            area_settings = {'binning': self._binning, 'crop': self._crop}
        else:
            area_settings = {}
        return area_settings

    @sensor_area_settings.setter
    def sensor_area_settings(self, settings):
        """
        Binning and extracting a certain part of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)} takes 4 pixels
        together to 1 and takes from all the pixels and area of 128 by 256
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
        return


    @property
    def bit_depth(self):
        """
        Return the bit depth of the camera
        @return:
        """
        return self._bit_depth

    @property
    def num_ad_channels(self):
        """
        Get the number of ad channels
        @return: int num_ad_channels: number of ad channels
        """
        return self._num_ad_channels

    @property
    def ad_channel(self):
        """
        Return the currently used ad channel
        @return int ad_channel: Number used to identify channel
        """
        return self._ad_channel

    @ad_channel.setter
    def ad_channel(self, channel):
        """
        Depending if the camera has different ad converters select one.
        @param int channel: New channel to be used
        """
        self._ad_channel = channel
        return

    @property
    def quantum_efficiency(self):
        """
        Return the quantum efficiency at a given wavelength.
        @param float wavelength: Wavelength of light falling on the sensor.
        @return: float quantum efficiency between 0 and 1
        """
        def lorentzian(x, amp, width, center):
            return amp / (1 + ((x - center) / width) ** 2)

        qe = lorentzian(self._wavelength, 1.0, 100e-9, 640e-9)

        return qe

    @quantum_efficiency.setter
    def quantum_efficiency(self, wavelength):
        """
        Let the camera know which wavelength you are operating at.
        @param float wavelength: Wavelength of light falling on the sensor.
        """
        self._wavelength = wavelength
        return

    @property
    def count_convert_mode(self):
        """
        Get the currently set count convert mode.
        The GUI will make use of this to display what is recorded.
        @return string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        """
        return self._count_convert_mode

    @count_convert_mode.setter
    def count_convert_mode(self, mode):
        """
        Return signal in 'Counts', 'Electrons' or 'Photons'
        @param string mode: i.e. 'Counts', 'Electrons' or 'Photons'
        """
        self._count_convert_mode = mode
        return

    @property
    def available_readout_modes(self):
        """
        Readout modes on the device
        @return: list of available readout modes
        """
        return self._read_out_modes

    @property
    def read_mode(self):
        """
        Get the read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @return string read_mode: string containing the current read_mode
        """
        return self._read_mode

    @read_mode.setter
    def read_mode(self, read_mode):
        """
        Set the read mode of the device (i.e. Image, Full Vertical Binning, Single-Track)
        @param str read_mode: Read mode to be set
        """
        self._read_mode = read_mode
        return

    @property
    def available_acquisition_modes(self):
        """
        Get the available acuqisitions modes of the camera
        @return: dict containing lists.
        The keys tell if they fall into 'Single Scan' or 'Series' category.
        """
        return self._available_acquistion_modes

    @property
    def acquisition_mode(self):
        """
        Get the acquisition mode of the camera
        @return: string acquisition mode of the camera
        """
        return self._acquisition_mode

    @acquisition_mode.setter
    def acquisition_mode(self, acquisition_mode):
        """
        Set the readout mode of the camera (i.e. 'Single scan', 'Series' and 'Continuous')
        @param str acquisition_mode: readout mode to be set
        """
        if acquisition_mode in self._available_acquistion_modes['Single Scan']:
            self._acquisition_mode = {'Single scan': acquisition_mode}
        elif acquisition_mode in self._available_acquistion_modes['Series']:
            self._acquisition_mode = {'Series': acquisition_mode}
        elif acquisition_mode in self._available_acquistion_modes['Continuous']:
            self._acquisition_mode = {'Continuous': acquisition_mode}
        return

    @property
    def available_trigger_modes(self):
        """
        Trigger modes on the device
        @return: list of available trigger modes
        """
        return self._available_trigger_modes

    @property
    def trigger_mode(self):
        """
        Get the currently used trigger mode
        @return: String of the set trigger mode
        """
        return self._trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode):
        """
        Set the trigger mode ('Internal', 'External' ... )
        @param str trigger_mode: Target trigger mode
        """
        self._trigger_mode = trigger_mode

    @property
    def shutter_state(self):
        """
        Query the camera if a shutter exists.
        @return boolean: True if yes, False if not
        """
        return self._shutter

    @shutter_state.setter
    def shutter_state(self, state):
        """
        Open the shutter
        """
        if self._shutter != (2 | 3):
            self._shutter = state
            return
        else:
            self.log.error('Camera has no shutter. No meaning in setting shutter state.')
            return

    @property
    def temperature(self):
        """
        Query the camera if it has temperature control
        @return boolen: True if yes, False if not
        """
        self._update_temperature()
        return self._sensor_temperature

    @temperature.setter
    def temperature(self, temperature):
        """
        Sets the temperature of the camera
        @param float temperature: Target temperature of the camera
        """
        self._sensor_setpoint_temperature = temperature
        return

    def start_temperature_control(self):
        """
        Start the temperature control of the camera
        """
        if self._temperature_control != (2 | 3):
            self._temperature_control = 1
            self._temperature_control_start = time.time()
            self._time = 0.0
            self._start_temperature = self._sensor_temperature
        return

    def stop_temperature_control(self):
        """
        Stop the temperature control of the camera
        """
        # TODO: Implement reheating to ambient temperature after stopping the cooling
        if self._temperature_control != (2 | 3):
            self._temperature_control = 0
            self._time = 0.0
            self._start_temperature = self._sensor_temperature
        return

    def set_up_image_sequence(self, num_sequences, num_images, exposures):
        """
        Set up the camera for the acquisition of an image sequence.

        @param int num_sequences: Number of sequences to be recorded
        @param int num_images: Number of images to be taken
        @param list exposures: List of length(num_images) containing the exposures to be used
        """
        if 'Series' in self._acquisition_mode:
            self._num_sequences = num_sequences
            self._num_images = num_images
            self._exposures = exposures
        else:
            self.log.error('In the current acquisition mode '
                           'taking an image_sequence is not supported')
        return

    def get_images(self, image_num):
        """
        Read images from the camera memory.

        @param int run_index: nth run of the sequence
        @param int image_num: Number of most recent images
        @param int stop_index: Index of the last image
        @return: numpy nd array of dimension (stop_index - start_index, px_x, px_y)
        """
        cur_time = time.time()
        if self._acquiring:
            qe = self.get_quantum_efficiency(self._wavelength)
            total_gain = self._get_total_gain(self.get_amplifiers())
            if self._acqusition_mode in ['Series', ' Continuous']:
                start_time = self._start_time
                time_past = cur_time - start_time
                self._total_acquisition_time -= time_past
                if self._total_acquisition_time < 0:
                    self._acquiring = False
                num_new_images = time_past // np.max(self._exposures)
                new_images = self._image_generator(num_new_images,
                                                        total_gain * qe, self._exposures,
                                                        method=self._image_generation_method)
            else:
                new_images = self._image_generator(1, total_gain * qe,
                                                   method=self._image_generation_method)

        return new_images

    # non interface methods
    def _update_temperature(self):
        self._time = time.time() - self._temperature_control_start
        init_temperature = self._start_temperature
        if self._temperature_control:
            target_temperature = self._sensor_setpoint_temperature
            effective_cooling = self._cooling_speed - self._thermal_contact

            self._sensor_temperature = target_temperature * \
                                       (1 - np.exp(-effective_cooling * self._time))\
                                       + init_temperature * np.exp(-effective_cooling * self._time)
        else:
            target_temperature = self._ambient_temperature
            self._sensor_temperature = target_temperature * \
                                       (1 - np.exp(-self._thermal_contact * self._time)) \
                                       + init_temperature * np.exp(-self._thermal_contact * self._time)
        return

    def _image_generation(self, method='random_images'):
        if method == 'random_images':
            image = np.random.poisson(150e3, self._current_sensor_area)
        return image

    def _image_generator(self, num_images, scale_factor, exposures, method='random_images'):
        num = 0
        seq_len = len(exposures)

        while num < num_images:
            cur_exposure_ind = num % seq_len
            yield scale_factor * seq_len * exposures[cur_exposure_ind] * self._image_generation(method=method)
            num += 1

    def _get_total_gain(self, amp_dict):
        return reduce(lambda x, y: x * y, [amp_dict[_] for _ in amp_dict], 1)

