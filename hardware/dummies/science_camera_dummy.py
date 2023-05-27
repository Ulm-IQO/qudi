# -*- coding: utf-8 -*-
"""
This module contains fake a spectrometer camera.

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
from core.module import Base
from interface.science_camera_interface import ScienceCameraInterface
from interface.science_camera_interface import ReadMode, Constraints, ImageAdvancedParameters

from qtpy import QtCore


class Main(Base, ScienceCameraInterface):
    """ This module is the dummy module for the SpectroscopyCameraInterface interface

    spectroscopy_camera_dummy:
        module.Class: 'spectroscopy_camera_dummy.Main'
    """

    def on_activate(self):
        """ Activate module """
        self._build_constraints()

        self._acquisition_timer = QtCore.QTimer()
        self._acquisition_timer.setSingleShot(True)
        self._acquisition_timer.timeout.connect(self._end_acquisition, QtCore.Qt.QueuedConnection)

        self._acquired_data = None
        self._read_mode = ReadMode.FVB
        self._readout_speed = self.get_constraints().read_modes[0]
        self._active_tracks = []
        self._image_advanced_parameters = None
        self._gain = self.get_constraints().internal_gains[0]
        self._exposure = 1
        self._trigger_mode = self.get_constraints().trigger_modes[0]

        self._shutter_open_state = True
        self._cooler_on = True
        self._temperature_setpoint = 183  # ~-90°C

    def on_deactivate(self):
        """ Deactivate module """
        pass

    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        return self._constraints

    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only onced by on_activate
         """
        constraints = Constraints()
        constraints.name = 'Spectroscopy camera dummy'
        constraints.width, constraints.height = 1024, 256
        constraints.pixel_size_width, constraints.pixel_size_width = 13e-6, 13e-6
        constraints.internal_gains = [1, 2, 4]
        constraints.readout_speeds = [50000, 1000000, 3000000]
        constraints.trigger_modes = ['Internal', 'Dummy TTL']
        constraints.has_shutter = True
        constraints.read_modes = [ReadMode.FVB, ReadMode.MULTIPLE_TRACKS, ReadMode.IMAGE, ReadMode.IMAGE_ADVANCED]
        constraints.has_cooler = True
        constraints.temperature.min = 0.1  # Very good cooling !
        self._constraints = constraints

    ##############################################################################
    #                           Basic functions
    ##############################################################################
    def start_acquisition(self):
        """ Starts an acquisition of the current mode and returns immediately """
        self._acquired_data = None
        self.module_state.lock()
        self._acquisition_timer.start()

    def _end_acquisition(self):
        """ Function called when the dummy acquisition is finished (after the exposure time) """
        self.module_state.unlock()
        if self.get_read_mode() == ReadMode.FVB:
            self._acquired_data = self._get_fake_spectra()
        elif self.get_read_mode() == ReadMode.MULTIPLE_TRACKS:
            self._acquired_data = [self._get_fake_spectra() for track in self.get_active_tracks()]
        elif self.get_read_mode() == ReadMode.IMAGE:
            self._acquired_data = self._get_fake_image()
        elif self.get_read_mode() == ReadMode.IMAGE_ADVANCED:
            self._acquired_data = self._get_fake_image(image_advanced=True)

    def _get_fake_spectra(self):
        """ Function that build fake a spectrum """
        width = self.get_constraints().width
        data = np.random.uniform(0, 10, width)  # constant noise
        data += np.random.uniform(0, 1 * self.get_exposure_time(), width)  # noise linear with time
        if self.get_shutter_open_state():
            data += np.random.uniform(0, 0.2 * self.get_exposure_time(), width) # noise for background
        number_of_peaks = round(np.random.uniform(0, 20))
        peak_position = np.random.uniform(0, width, number_of_peaks)
        peak_linewidth = np.random.uniform(1, 5, number_of_peaks)
        peak_intensity = np.random.uniform(0, 20*self.get_exposure_time(), number_of_peaks)
        x = np.arange(width)
        for i in range(number_of_peaks):
            data += peak_intensity[i] * np.exp(-(x-peak_position[i])**2/(2*peak_linewidth[i]**2))
        data *= self.get_gain()
        return data

    def _get_fake_image(self, image_advanced=False, line_width_height=20):
        """ Function that build fake a image data """
        height = self.get_constraints().height
        spectra = self._get_fake_spectra()
        width = len(spectra)
        x = np.arange(height)
        intensity = np.exp(-(x-height/2)**2/(2*line_width_height**2))
        data = np.random.uniform(0.1, 1, (width, height))
        image = (data * intensity).T * spectra
        if image_advanced:
            params = self.get_image_advanced_parameters()
            image = image[params.vertical_start:params.vertical_end, params.horizontal_start:params.horizontal_end]
            image = image[::params.vertical_binning, ::params.horizontal_binning]
        return image

    def abort_acquisition(self):
        """ Abort acquisition """
        self._acquisition_timer.stop()
        self.module_state.unlock()

    def get_ready_state(self):
        """ Get the status of the camera, to know if the acquisition is finished or still ongoing.

        @return (bool): True if the camera is ready, False if an acquisition is ongoing

        As there is no synchronous acquisition in the interface, the logic needs a way to check the acquisition state.
        """
        return self.module_state() == 'idle'

    def get_acquired_data(self):
        """ Return an array of last acquired data.

        @return: Data in the format depending on the read mode.

        Depending on the read mode, the format is :
        'FVB' : 1d array
        'MULTIPLE_TRACKS' : list of 1d arrays
        'IMAGE' 2d array of shape (width, height)
        'IMAGE_ADVANCED' 2d array of shape (width, height)

        Each value might be a float or an integer.
        """
        return self._acquired_data

    ##############################################################################
    #                           Read mode functions
    ##############################################################################
    def get_read_mode(self):
        """ Getter method returning the current read mode used by the camera.

        @return (ReadMode): Current read mode
        """
        return self._read_mode

    def set_read_mode(self, value):
        """ Setter method setting the read mode used by the camera.

        @param (ReadMode) value: read mode to set
        """
        if value in self.get_constraints().read_modes:
            self._read_mode = value

    ##############################################################################
    #                           Readout speed functions
    ##############################################################################
    def get_readout_speed(self):
        """ Get the current readout speed of the camera

        This value is one of the possible values given by constraints
        """
        return self._readout_seed

    def set_readout_speed(self, value):
        """ Set the readout speed of the camera

        @param (float) value: Readout speed to set, must be a value from the constraints readout_speeds list
        """
        if value in self.get_constraints().readout_speeds:
            self._readout_speed = value

    ##############################################################################
    #                           Active tracks functions
    #
    # Method used only for read mode MULTIPLE_TRACKS
    ##############################################################################
    def get_active_tracks(self):
        """ Getter method returning the read mode tracks parameters of the camera.

        @return (list):  active tracks positions [(start_1, end_1), (start_2, end_2), ... ]

        Should only be used while in MULTIPLE_TRACKS mode
        """
        return self._active_tracks

    def set_active_tracks(self, value):
        """ Setter method for the active tracks of the camera.

        @param (list) value: active tracks positions  as [(start_1, end_1), (start_2, end_2), ... ]

        Some camera can sum the signal over tracks of pixels (all width times a height given by start and stop pixels)
        This sum is done internally before the analog to digital converter to reduce the signal noise.

        Should only be used while in MULTIPLE_TRACKS mode
        """
        self._active_tracks = value

    ##############################################################################
    #                           Image advanced functions
    #
    # Method used only for read mode IMAGE_ADVANCED
    ##############################################################################
    def get_image_advanced_parameters(self):
        """ Getter method returning the image parameters of the camera.

        @return (ImageAdvancedParameters): Current image advanced parameters

        Should only be used while in IMAGE_ADVANCED mode
        """
        return self._image_advanced_parameters

    def set_image_advanced_parameters(self, value):
        """ Setter method setting the read mode image parameters of the camera.

        @param (ImageAdvancedParameters) value: Parameters to set

        Should only be used while in IMAGE_ADVANCED mode
        """
        if not isinstance(value, ImageAdvancedParameters):
            self.log.error('ImageAdvancedParameters value error. Value {} is not correct.'.format(value))
        self._image_advanced_parameters = value

    ##############################################################################
    #                           Gain mode functions
    ##############################################################################
    def get_gain(self):
        """ Get the current gain.

        @return (float): Current gain

        Gain value should be one in the constraints internal_gains list.
        """
        return self._gain

    def set_gain(self, value):
        """ Set the gain.

        @param (float) value: New gain, value should be one in the constraints internal_gains list.
        """
        if value in self.get_constraints().internal_gains:
            self._gain = value

    ##############################################################################
    #                           Exposure functions
    ##############################################################################
    def get_exposure_time(self):
        """ Get the exposure time in seconds

        @return: (float) exposure time
        """
        return self._exposure

    def set_exposure_time(self, value):
        """ Set the exposure time in seconds.

        @param value: (float) desired new exposure time

        @return: nothing
        """
        if value > 0:
            self._exposure = value
        self._acquisition_timer.setInterval(value*1e3)

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################
    def get_trigger_mode(self):
        """ Getter method returning the current trigger mode used by the camera.

        @return (str): Trigger mode

        This string should match one in the constraints trigger_modes list.
        """
        return self._trigger_mode

    def set_trigger_mode(self, value):
        """ Setter method for the trigger mode used by the camera.

        @param (str) value: trigger mode, should match one in the constraints trigger_modes list.
        """
        if value in self.get_constraints().trigger_modes:
            self._trigger_mode = value

    ##############################################################################
    #                        Shutter mode function
    #
    # Method used only if constraints.has_shutter
    ##############################################################################
    def get_shutter_open_state(self):
        """ Getter method returning the shutter mode.

        @return (bool): True if the shutter is open, False of closed
        """
        return self._shutter_open_state

    def set_shutter_open_state(self, value):
        """ Setter method setting the shutter mode.

        @param (bool) value: True to open, False tp close
        """
        if isinstance(value, bool):
            self._shutter_open_state = value

    ##############################################################################
    #                           Temperature functions
    #
    # Method used only if constraints.has_cooler
    ##############################################################################
    def get_cooler_on(self):
        """ Getter method returning the cooler status

        @return (bool): True if the cooler is on
        """
        return self._cooler_on

    def set_cooler_on(self, value):
        """ Setter method for the the cooler status

        @param (bool) value: True to turn it on, False to turn it off
        """
        if isinstance(value, bool):
            self._cooler_on = value

    def get_temperature(self):
        """ Getter method returning the temperature of the camera in Kelvin.

        @return (float) : Measured temperature in kelvin
        """
        return self._temperature_setpoint

    def get_temperature_setpoint(self):
        """ Getter method for the temperature setpoint of the camera.

        @return (float): Current setpoint in Kelvin
        """
        return self._temperature_setpoint

    def set_temperature_setpoint(self, value):
        """ Setter method for the temperature setpoint of the camera.

        @param (float) value: New setpoint in Kelvin
        """
        if value > 0:
            self._temperature_setpoint = value
