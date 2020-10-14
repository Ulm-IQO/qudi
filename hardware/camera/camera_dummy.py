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

    # capabilities of the camera, in actual hardware many of these attributes should
    # be obtained by querying the camera on startup
    _support_live = ConfigOption('support_live', True)
    _support_binning = ConfigOption('support_binning', True)
    _support_crop = ConfigOption('support_crop', True)
    _camera_name = ConfigOption('camera_name', 'Dummy camera')
    _resolution = ConfigOption('resolution', (512, 512))
    # just for the generation of dummy data
    _data_acquistion = ConfigOption('random_images', 'random images')
    _available_amplifiers = ConfigOption('amplifiers', {'EM', 'preamp'})
    _read_out_modes = ConfigOption('readout_modes', ['Image', 'Cropped', 'FVB'])
    _acquistion_modes = ConfigOption('acquisition_mode', ['Single Scan', 'Kinetic Series'])
    _available_read_out_speeds = ConfigOption('readout_speeds', {'horizontal': [1e6, 3e6, 9e6],
                                                                 'vertical': [0.5e6, 1e6, 1.5e6]})
    _available_trigger_modes = ConfigOption('available_trigger_modes', ['Internal', 'External', 'Software'])
    _has_shutter = ConfigOption('has_shutter', True)
    _has_temperature_control = ConfigOption('has_temperature_control', True)
    _bit_depth = ConfigOption('bit_depth', 16)
    _wave_length = ConfigOption('wave_length', 640e-9)
    _num_ad_channels = ConfigOption('num_ad_channels', 3)
    _ad_channel = ConfigOption('ad_channel', 0)
    _count_convert_mode = ConfigOption('count_convert_mode', 'Counts')

    # state of the 'Camera'
    _live = False
    _acquiring = False
    _exposure = ConfigOption('exposure', .1)
    _current_amplifiers = ConfigOption('current_amplifiers', {'preamp': 4.0})
    _binning = ConfigOption('binning', {2, 2})
    _crop = ConfigOption('crop', ((100, 400), (0, 280)))
    _current_resolution = _resolution
    _read_out_speed = ConfigOption('readout_speed', {'horizontal': 1e6,
                                                     'vertical': 0.5e6})
    _read_mode = ConfigOption('read_mode', 'Image')
    _acquisition_mode = ConfigOption('acquisition_mode', 'Kinetic Series')
    _num_sequences = ConfigOption('num_sequences', 2)
    _num_images = ConfigOption('num_images', 5)
    _exposures = ConfigOption('exposures', [0.1 * i + 0.01 for i in range(10)])
    _trigger_mode = ConfigOption('trigger_mode', 'Internal')
    _temperature = ConfigOption('temperature', -70)
    _temperature_control = ConfigOption('temperature_control', False)
    _ambient_temperature = ConfigOption('temperature', 20)
    _cooling_speed = ConfigOption('cooling_speed', 0.5)
    _time = 0.0
    _start_time = 0.0


    if _has_shutter:
        _shutter = ConfigOption('shutter', True)
    else:
        shutter = None


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._set_up_sensor_area({'binning': self._binning, 'crop': self._crop})
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
        return self._resolution

    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        return self._support_live

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        if self._support_live & self._acquisition_mode == 'Single Scan':
            self._live = True
            self._acquiring = False

    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        return not (self._live or self._acquiring)

    def binning_available(self):
        """
        Does the cammera support binning?
        @return:
        """
        return self._support_binning

    def crop_available(self):
        """
        Does the camera support cropping the image.
        @return:
        """
        return self._support_crop

    def start_single_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        if self._live:
            return False
        else:
            self._acquiring = True
            time.sleep(float(self._exposure + 10 / 1000))
            self._acquiring = False
            return True

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
            data = np.random.random(self._cur_resolution) * self._exposure * self._gain
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

        return self._read_out_speeds

    def set_readout_speeds(self, speed_dict):
        """
        Set the readout speed e.g. {'horizontal': 10e6, 'vertical':1e6} in Hz
        @param speed_dict:
        @return int error code: (0: OK, -1: error)
        """
        self._read_out_speed = speed_dict
        return 0

    def get_readout_speeds(self):
        """
        Get the current readout speed e.g. {'horizontal': 1e6, 'vertical':3e6} in Hz
        @return dict readout_speeds: Dictionary with horizontal
                                     and vertical readout speed
        """
        return self._read_out_speed

    def get_readout_time(self):
        """
        Return how long the readout of a single image will take
        @return float time: Time it takes to read out an image from the sensor
        """
        horizontal_readout_time = self._cur_resolution[0] * self._read_out_speed['horizontal']
        vertical_readout_time = self._cur_resolution[1] * self._read_out_speed['horizontal']
        readout_time = horizontal_readout_time + vertical_readout_time
        return readout_time

    def set_up_sensor_area(self, settings):
        """
        Binning and extracting a certain part of the sensor e.g. {'binning': (2,2), 'crop' (128, 256)} takes 4 pixels
        together to 1 and takes from all the pixels and area of 128 by 256
        @return int error code: (0: OK, -1: error)
        """
        if self._read_mode == 'Image':
            self._binning = settings['binning']
            self._crop = settings['crop']
            horizontal_coord, vertical_coord = self._crop[0], self._crop[1]
            horizontal = horizontal_coord[1] - horizontal_coord[0]
            vertical = vertical_coord[1] - vertical_coord[0]
            horizontal //= self._binning[0]
            vertical //= self._binning[1]
            self._cur_resolution = (horizontal, vertical)
        elif self._read_mode == 'FVB':
            self._binning = (1, self._resolution[1])
            self._crop = ((1, self._resolution[0]), (1, self._resolution[1]))
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
            return amp / (1 + (width / (x - center)) ** 2)

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

    def set_acquisition_mode(self, readout_mode):
        """
        Set the readout mode of the camera ('single acquisition', 'kinetic series')
        @param str readout_mode: readout mode to be set
        @return int error code: (0:OK, -1:error)
        """
        self._read_mode = readout_mode
        return 0

    def get_acquisition_mode(self):
        """
        Get the acquisition mode of the camera
        @return: string acquisition mode of the camera
        """
        return self._acquisition_mode

    def set_up_image_sequence(self, num_sequences, num_images, exposures):
        """
        Set up the camera for the acquisition of an image sequence.

        @param int num_sequences: Number of sequences to be recorded
        @param int num_images: Number of images to be taken
        @param list exposures: List of length(num_images) containing the exposures to be used
        @return int error code: (0:OK, -1:error)
        """
        if self._acquisition_mode == 'Kinetic Series':
            self._num_sequences = num_sequences
            self._num_images = num_images
            self._exposures = exposures
            return 0
        else:
            return -1

    def acquire_image_sequence(self):
        """
        Reads image sequence from the camera
        @return: numpy nd array of dimension (seq_length, px_x, px_y)
        """
        if self._acquisition_mode == 'Kinetic Series':
            qe = self.get_quantum_efficiency(self._wave_length)
            data = np.zeros((self._num_sequences, self._num_images,
                            self._cur_resolution[0], self._cur_resolution[1]))
            if self._data_acquistion == 'random images':
                for seq_run in range(self._num_sequences):
                    for image in range(self._num_images):
                        data[seq_run, image, :, :] = qe * np.random.random(self._cur_resolution)\
                                                     * self._exposure * self._gain * self._exposures[image]
        return data

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
            self._set_temperature = temperature
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
            self._start_temperature = self._temperature
            return 0
        else:
            return -1

    def stop_temperature_control(self):
        """
        Stop the temperature control of the camera
        @return int error code: (0:OK, -1:error)
        """

        if self._has_temperature_control:
            self._temperature_control = False
            return 0
        else:
            return -1

    def get_temperature(self):
        """
        Gets the temperature of the camera
        @return int error code: (0:OK, -1:error)
        """
        if self._temperature_control:
            self._update_temperature()
        return self._temperature

    def _update_temperature(self):
        target_temperature = self._set_temperature
        init_temperature
        cooling_speed = self._cooling_speed
        time = time.clock() + self._time

        self._temperature = target_temperature * (1 - np.exp(-cooling_speed * time)) \
                            + init_temperature * np.exp(-cooling_speed * time)
        return
