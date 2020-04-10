# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class that captures and processes photoluminescence
spectra and the spot image.

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

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption

from time import sleep
from datetime import date


class SpectrumLogic(GenericLogic):
    """This logic module gathers data from the spectrometer.
    """

    # declare connectors
    spectrometer = Connector(interface='SpectrometerInterface')
    camera = Connector(interface='CameraInterface')
    savelogic = Connector(interface='SaveLogic', optional=True)

    # declare status variables (logic attribute) :
    _spectrum_data = StatusVar('spectrum_data', np.empty((2, 0)))
    _background_data = StatusVar('background_data', np.empty((2, 0)))
    _image_data = StatusVar('image_data', np.empty((2, 0)))

    # Allow to set a default save directory in the config file :
    _default_save_file_path = ConfigOption('default_save_file_path')
    _save_file_path = StatusVar('save_file_path', _default_save_file_path)

    # declare status variables (camera attribute) :
    _read_mode = StatusVar('read_mode', 'FVB')
    _number_of_track = StatusVar('number_of_track', 1)
    _track_height = StatusVar('track_height', 50)
    _track_offset = StatusVar('track_offset', 0)
    _pixel_height = StatusVar('pixel_height', 1e-4)
    _pixel_width = StatusVar('pixel_width', 1e-4)

    _acquistion_mode = StatusVar('acquistion_mode', 'SINGLESCAN')
    _number_accumulated_scan = StatusVar('number_accumulated_scan', 1)
    _accumulation_time = StatusVar('number_accumulated_scan', 1e-3)
    _number_of_scan = StatusVar('number_of_scan', 1)
    _scan_delay = StatusVar('scan_delay', 1e-2)
    _exposure_time = StatusVar('exposure_time', 1e-4)
    _camera_gain = StatusVar('camera_gain', 1)

    _shutter_mode = StatusVar('shutter_mode', (1, 1e-4, 1e-4, True))
    ##############################################################################
    #                            Basic functions
    ##############################################################################

    def __init__(self, **kwargs):
        """ Create SpectrumLogic object with connectors and status variables loaded.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.spectrometer_device = self.spectrometer()
        self.camera_device = self.camera()

        # declare spectrometer attributes :
        self._grating = self.grating
        self._grating_offset = self.grating_offset

        self._center_wavelength = self.center_wavelength
        self._wavelength_range = self.wavelength_range

        self._detector_offset = self.detector_offset

        self._input_port = self.input_port
        self._output_port = self.output_port
        self._input_slit_width = self.input_slit_width
        self._output_slit_width = self.output_slit_width

        # declare camera attributes :
        self._camera_size = self.camera_device.size()

        self._save_logic = self.savelogic()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            pass

    ##############################################################################
    #                            Save functions
    ##############################################################################

    def save_data(self, data_type = 'spectrum', file_name = None, save_path = None):
        """
        Method used to save the data using the savelogic module

        :param data_type:
        :param file_name:
        :param save_path:
        :return: nothing
        """
        data = OrderedDict()
        today = date.today()
        if data_type == 'image':
            data = self._image_data[:, :]
        else:
            if data_type == 'spectrum':
                data['Wavelength (m)'] = self._spectrum_data[0, :]
                data['PL intensity (u.a)'] = self._spectrum_data[1, :]
            elif data_type == 'background':
                data['Wavelength (m)'] = self._background_data[0, :]
                data['PL intensity (u.a)'] = self._background_data[1, :]
            else:
                self.log.debug('Data type parameter is not defined : it can only be \'spectrum\','
                               ' \'background\' or \'image\'')
        if file_name is not None:
            file_label = file_name
        else:
            file_label = '{}_'.format(data_type) + today.strftime("%d%m%Y")
        if save_path is not None:
            self._save_file_path = save_path
        self._save_logic.save_data(data,
                                   filepath=self._save_file_path,
                                   filelabel=file_label)
        self.log.info('{} data saved in {}'.format(data_type.capitalize(), self._save_file_path))

    ##############################################################################
    #                            Acquisition functions
    ##############################################################################

    def acquire_spectrum(self):
        for i in range(0, self._number_of_scan):
            self.camera_device.start_acquisition()
            self._spectrum_data[i] = self.camera_device.get_acquired_data()
            sleep(self._scan_delay)
        self.log.info("Spectrum acquisition succeed ! Number of acquired scan : {} "
                      "/ Delay between each scan : {}".format(self._number_of_scan, self._scan_delay))

    def acquire_background(self):
        if self.get_shutter_mode()[0] != 0:
            self.set_shutter_mode(0)
        for i in range(0, self._number_of_scan):
            self.camera_device.start_acquisition()
            self._background_data[i] = self.camera_device.get_acquired_data()
            sleep(self._scan_delay)
        self.log.info("Background acquisition succeed ! Number of acquired scan : {} "
                      "/ Delay between each scan : {}".format(self._number_of_scan, self._scan_delay))
        self.set_shutter_mode(*self._shutter_mode)

    def acquire_image(self):
        if self.get_shutter_mode()[0] != 0:
            self.set_shutter_mode(0)
        for i in range(0, self._number_of_scan):
            self.camera_device.start_acquisition()
            self._background_data[i] = self.camera_device.get_acquired_data()
            sleep(self._scan_delay)
        self.log.info("Background acquisition succeed ! Number of acquired scan : {} "
                      "/ Delay between each scan : {}".format(self._number_of_scan, self._scan_delay))
        self.set_shutter_mode(*self._shutter_mode)

    @property
    def spectrum_data(self):
        return self._spectrum_data

    @property
    def background_data(self):
        return self._background_data

    @property
    def image_data(self):
        return self._image_data

    ##############################################################################
    #                            Spectrometer functions
    ##############################################################################
    # All functions defined in this part should be used to
    #
    #
    ##############################################################################
    #                            Gratings functions
    ##############################################################################

    @property
    def grating(self):
        """
        Getter method returning the grating number used by the spectrometer.

        :return: @int active grating number or 0 if error
        """
        grating_number = self.spectrometer_device.get_grating()
        is_int = isinstance(grating_number, int)
        if is_int:
            self._grating = grating_number
            return grating_number
        else:
            self.log.error('Your hardware getter function \'get_grating()\' is not returning an integer ')
            return 0


    @grating.setter
    def grating(self, grating_number):
        """
        Setter method setting the grating number to use by the spectrometer.

        :param grating_number: @int gating number to set active
        :return: nothing
        """
        number_gratings = self.spectrometer_device.get_number_gratings()
        is_int = isinstance(grating_number, int)
        is_in_range = 0 < grating_number < number_gratings
        is_change = grating_number != self._grating
        if is_int and is_in_range and is_change:
            self.spectrometer_device.set_grating(grating_number)
            self.log.info('Spectrometer grating has been changed correctly ')
            self._grating = grating_number
        else:
            if is_int:
                self.log.debug('Grating parameter is not correct : it must be an integer ')
            if is_in_range:
                self.log.debug('Grating parameter is not correct : it must be in range 0 to {} '
                               .format(number_gratings-1))
            else:
                self.log.info('Grating parameter has not been changed')

    @property
    def grating_offset(self, grating_number):
        """
        Getter method returning the grating offset of the grating selected by the grating_number parameter.

        :param grating_number: @int grating number which correspond the offset
        :return: @int the corresponding grating offset or 0 if error
        """
        number_gratings = self.spectrometer_device.get_number_gratings()
        var_is_int = isinstance(grating_number, int)
        var_is_in_range = 0 < grating_number < number_gratings
        var_is_change = grating_number != self._grating
        if var_is_int and var_is_in_range and var_is_change:
            grating_offset = self.spectrometer_device.get_grating_offset()
            is_int = isinstance(grating_number, int)
            if is_int:
                self._grating_offset = grating_offset
                return grating_offset
            else:
                self.log.error('Your hardware getter function \'get_grating_offset()\' is not returning an integer ')
                return 0
        else:
            if var_is_int:
                self.log.debug('Grating parameter is not correct : it must be an integer ')
            if var_is_in_range:
                self.log.debug('Grating parameter is not correct : it must be in range 0 to {} '
                               .format(number_gratings-1))
            else:
                self.log.info('Grating parameter has not been changed')
            return 0

    @grating_offset.setter
    def grating_offset(self, grating_number, grating_offset):
        """
        Setter method setting the grating offset of the grating selected by the grating_number parameter.

        :param grating_number: @int grating number which correspond the offset
        :param grating_offset:  @int grating offset
        :return: nothing
        """
        number_gratings = self.spectrometer_device.get_number_gratings()
        grating_is_int = isinstance(grating_number, int)
        grating_is_in_range = -1 < grating_number < number_gratings
        grating_is_change = grating_number != self._grating
        grating_is_correct = grating_is_int and grating_is_in_range and grating_is_change
        number_pixels = self.number_of_pixels()
        offset_min = -number_pixels//2 - number_pixels % 2
        offset_max = number_pixels//2
        offset_is_int = isinstance(grating_offset, int)
        offset_is_in_range = offset_min < grating_offset < offset_max
        offset_is_change = grating_offset != self._grating_offset
        offset_is_correct = offset_is_int and offset_is_in_range and offset_is_change
        if grating_is_correct and offset_is_correct:
            self.spectrometer_device.set_grating_offset(grating_offset)
            self.log.info('Spectrometer grating offset has been changed correctly ')
            self._grating = grating_number
        else:
            if grating_is_int:
                self.log.debug('Grating parameter is not correct : it must be an integer ')
            elif grating_is_in_range:
                self.log.debug('Grating parameter is not correct : it must be in range 0 to {} '
                               .format(number_gratings-1))
            elif grating_is_change:
                self.log.info('Grating parameter has not been changed')
            elif offset_is_int:
                self.log.debug('Offset parameter is not correct : it must be an integer ')
            elif offset_is_in_range:
                self.log.debug('Offset parameter is not correct : it must be in range {} to {} '
                               .format(offset_min, offset_max))
            elif offset_is_change:
                self.log.info('Offset parameter has not been changed')

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################

    @property
    def center_wavelength(self):
        """
        Getter method returning the center wavelength of the measured spectral range.

        :return: @float the spectrum center wavelength or 0 if error
        """
        wavelength = self.spectrometer_device.get_wavelength()
        is_float = isinstance(wavelength, float)
        if is_float:
            self._center_wavelength = wavelength
            return wavelength
        else:
            self.log.error('Your hardware getter function \'get_wavelength()\' is not returning a float ')
            return 0

    @center_wavelength.setter
    def center_wavelength(self, wavelength):
        """
        Setter method setting the center wavelength of the measured spectral range.

        :param wavelength: @float center wavelength
        :return: nothing
        """
        wavelength_min, wavelength_max = self.spectrometer_device.get_wavelength_limit(self._grating)
        is_float = isinstance(wavelength, float)
        is_in_range = wavelength_min < wavelength < wavelength_max
        is_change = wavelength != self._center_wavelength
        if is_float and is_in_range and is_change:
            self.spectrometer_device.set_wavelength(wavelength)
            self.log.info('Spectrometer wavelength has been changed correctly ')
            self._center_wavelength = wavelength
        else:
            if is_float:
                self.log.debug('Wavelength parameter is not correct : it must be a float ')
            elif is_in_range:
                self.log.debug('Wavelength parameter is not correct : it must be in range {} to {} '
                               .format(wavelength_min, wavelength_max))
            else:
                self.log.info('Wavelength parameter has not been changed')

    @property
    def wavelength_range(self):
        """
        Getter method returning the wavelength array of the full measured spectral range.
        (used for plotting spectrum with the spectral range)

        :return: @ndarray measured wavelength array or 0 if error
        """
        wavelength_min, wavelength_max = self.spectrometer_device.get_wavelength_limit(self._grating)
        wavelength_range = self.spectrometer_device.get_calibration(self._pixel_matrix_dimension[0])
        is_ndarray = isinstance(wavelength_range, np.ndarray)
        is_in_range = np.min(wavelength_range) > wavelength_min and np.max(wavelength_range) > wavelength_max
        if is_ndarray and is_in_range:
            self._wavelength_range = wavelength_range
            return wavelength_range
        else:
            if is_ndarray:
                self.log.error('Your hardware getter function \'get_calibration()\' is not returning a ndarray ')
            else:
                self.log.error('Your hardware getter function \'get_calibration()\' is not returning a '
                               'wavelength in range of the current grating wavelength limits ')
            return 0

    @property
    def number_of_pixels(self):
        """
        Getter method returning the number of pixels used by the spectrometer DLLs calibration function.
        (the value return by this function must match with the real pixel number of the camera)

        :return: @int number of pixels or 0 if error
        """
        number_pixels = self.spectrometer_device.get_number_of_pixels()
        is_int = isinstance(number_pixels, int)
        is_positive = 0 < number_pixels
        if is_int and is_positive:
            self._pixel_matrix_dimension[0] = number_pixels
            return number_pixels
        else:
            if is_int:
                self.log.error('Your hardware getter function \'get_number_of_pixels()\' is not returning a int ')
            else:
                self.log.error('Your hardware getter function \'get_number_of_pixels()\' is not returning a '
                               'positive number ')
            return 0

    @number_of_pixels.setter
    def number_of_pixels(self, number_pixels):
        """
        Setter method setting the number of pixels used by the spectrometer DLLs calibration function.
        (the value set by this function must be the real pixel number of the camera)

        :param number_pixels: @int number of pixels
        :return: nothing
        """
        is_int = isinstance(number_pixels, int)
        is_positive = 0 < number_pixels
        is_change = number_pixels != self._pixel_matrix_dimension[0]
        if is_int and is_positive and is_change:
            self.spectrometer_device.get_pixel_width(number_pixels)
            self.log.info('Number of pixels has been changed correctly ')
            self._pixel_matrix_dimension[0] = number_pixels
        else:
            if is_int:
                self.log.debug('Number of pixels parameter is not correct : it must be a int ')
            elif is_positive:
                self.log.debug('Number of pixels parameter is not correct : it must be positive ')
            else:
                self.log.info('Number of pixels parameter has not been changed')

    @property
    def pixel_width(self):
        """
        Getter method returning the pixel width used by the spectrometer DLLs calibration function.
        (the value returned by this function must match the real pixel width of the camera)

        :return: @int pixel width or 0 if error
        """
        pixel_width = self.spectrometer_device.get_pixel_width()
        is_float = isinstance(pixel_width, float)
        is_positive = 0 < pixel_width
        if is_float and is_positive:
            self._pixel_width = pixel_width
            return pixel_width
        else:
            if is_float:
                self.log.error('Your hardware getter function \'get_pixel_width()\' is not returning a float ')
            else:
                self.log.error('Your hardware getter function \'get_pixel_width()\' is not returning a '
                               'positive number ')
            return 0

    @pixel_width.setter
    def pixel_width(self, pixel_width):
        """
        Setter method setting the pixel width used by the spectrometer DLLs calibration function.
        (the value set by this function must be the real pixel width of the camera)

        :param pixel_width: @int pixel width
        :return: nothing
        """
        is_float = isinstance(pixel_width, float)
        is_positive = 0 < pixel_width
        is_change = pixel_width != self._pixel_width
        if is_float and is_positive and is_change:
            self.spectrometer_device.set_pixel_width(pixel_width)
            self.log.info('Pixel width has been changed correctly ')
            self._pixel_width = pixel_width
        else:
            if is_float:
                self.log.debug('Pixel width parameter is not correct : it must be a float ')
            elif is_positive:
                self.log.debug('Pixel width parameter is not correct : it must be positive ')
            else:
                self.log.info('Pixel width parameter has not been changed')

    ##############################################################################
    #                            Detector functions
    ##############################################################################

    @property
    def detector_offset(self):
        """
        Getter method returning the detector offset used by the spectrometer DLLs calibration function.
        (the value returned by this function must match the real detector offset value of the camera)

        :return: @int detector offset or 0 error
        """
        offset = self.spectrometer_device.get_detector_offset()
        is_int = isinstance(offset, int)
        if is_int:
            self._detector_offset = offset
            return offset
        else:
            self.log.error('Your hardware getter function \'get_detector_offset()\' is not returning a int ')
            return 0

    @detector_offset.setter
    def detector_offset(self, detector_offset):
        """
        Setter method returning the detector offset used by the spectrometer DLLs calibration function.
        (the value returned by this function must be the real detector offset value of the camera)

        :param detector_offset: @int detetcor offset
        :return: nothing
        """
        number_pixels = 514 #TODO : add the Newton funtion returning the number of pixels (Hardcoding)
        offset_min = -number_pixels//2 - 1
        offset_max = number_pixels//2
        is_int = isinstance(detector_offset, int)
        is_in_range = offset_min - 1 < detector_offset < offset_max + 1
        is_change = detector_offset != self._detector_offset
        if is_int and is_in_range and is_change:
            self.spectrometer_device.set_detector_offset(detector_offset)
            self.log.info('Detector offset has been changed correctly ')
            self._detector_offset = detector_offset
        else:
            if is_int:
                self.log.debug('Detector offset parameter is not correct : it must be a int ')
            elif is_in_range:
                self.log.debug('Detector offset parameter is not correct : it must be in range {} to {} '
                               .format(offset_min, offset_max))
            else:
                self.log.info('Detector offset parameter has not been changed')

    ##############################################################################
    #                      Ports and Slits functions
    ##############################################################################

    @property
    def input_port(self):
        """
        Getter method returning the active current input port of the spectrometer.

        :return: @int active input port (0 front and 1 side) or 0 if error
        """
        input_port = self.spectrometer_device.get_input_port()
        is_int = isinstance(input_port, int)
        is_in_range = -1 < input_port < 2
        if is_int and is_in_range:
            self._input_port = input_port
            return input_port
        else:
            if is_int:
                self.log.error('Your hardware getter function \'get_input_port()\' is not returning a int ')
            else:
                self.log.error('Your hardware getter function \'get_input_port()\' is not in range 0 to 1 ')
            return 0

    @input_port.setter
    def input_port(self, input_port):
        """
        Setter method setting the active current input port of the spectrometer.

        :param input_port: input port
        :return: nothing
        """
        side_port_possible = self.spectrometer_device.flipper_mirror_is_present(1)
        is_int = isinstance(input_port, int)
        is_in_range = -1 < input_port < 2
        is_change = input_port != self._input_port
        if is_int and is_in_range and is_change:
            if side_port_possible or input_port == 0:
                self.spectrometer_device.set_input_port(input_port)
                self.log.info('Input port has been changed correctly ')
                self._input_port = input_port
            else:
                self.log.debug('Your hardware do not have any flipper mirror present at the input port ')
        else:
            if is_int:
                self.log.debug('Input port parameter is not correct : it must be a int ')
            elif is_in_range:
                self.log.debug('Input port parameter is not correct : it must be 0 or 1 ')
            else:
                self.log.info('Input port parameter has not been changed')

    @property
    def output_port(self):
        """
        Getter method returning the active current output port of the spectrometer.

        :return: @int active output port (0 front and 1 side) or 0 if error
        """
        output_port = self.spectrometer_device.get_output_port()
        is_int = isinstance(output_port, int)
        is_in_range = -1 < output_port < 2
        if is_int and is_in_range:
            self._input_port = output_port
            return output_port
        else:
            if is_int:
                self.log.error('Your hardware getter function \'get_output_port()\' is not returning a int ')
            else:
                self.log.error('Your hardware getter function \'get_output_port()\' is not in range 0 to 1 ')
            return 0

    @output_port.setter
    def output_port(self, output_port):
        """
        Setter method setting the active current output port of the spectrometer.

        :param output_port: output port
        :return: nothing
        """
        side_port_possible = self.spectrometer_device.flipper_mirror_is_present(2)
        is_int = isinstance(output_port, int)
        is_in_range = -1 < output_port < 2
        is_change = output_port != self._output_port
        if is_int and is_in_range and is_change:
            if side_port_possible or output_port == 0:
                self.spectrometer_device.set_output_port(output_port)
                self.log.info('Output port has been changed correctly ')
                self._output_port = output_port
            else:
                self.log.debug('Your hardware do not have any flipper mirror present at the output port ')
        else:
            if is_int:
                self.log.debug('Output port parameter is not correct : it must be a int ')
            elif is_in_range:
                self.log.debug('Output port parameter is not correct : it must be 0 or 1 ')
            else:
                self.log.info('Output port parameter has not been changed')

    @property
    def input_slit_width(self):
        """
        Getter method returning the active input port slit width of the spectrometer.

        :return: @float input port slit width or 0 if error
        """
        slit_width = self.spectrometer_device.get_auto_slit_width('input', self._input_port)
        is_float = isinstance(slit_width, float)
        if is_float:
            self._input_slit_width = slit_width
            return slit_width
        else:
            self.log.error('Your hardware getter function \'get_auto_slit_width()\' is not returning a float ')
            return 0

    @input_slit_width.setter
    def input_slit_width(self, slit_width):
        """
        Setter method setting the active input port slit width of the spectrometer.

        :param slit_width: @float input port slit width
        :return: nothing
        """
        slit_is_present = self.spectrometer_device.auto_slit_is_present('input', self._input_port)
        is_float = isinstance(slit_width, float)
        if is_float:
            if slit_is_present:
                self.spectrometer_device.set_auto_slit_width('input', self._input_port, slit_width)
                self.log.info('Output slit width has been changed correctly ')
                self._input_slit_width = slit_width
            else:
                self.log.debug('Your hardware do not have any auto slit present at the selected input port ')
        else:
            self.log.debug('Input slit width parameter is not correct : it must be a float ')


    @property
    def output_slit_width(self):
        """
        Getter method returning the active output port slit width of the spectrometer.

        :return: @float output port slit width or 0 if error
        """
        slit_width = self.spectrometer_device.get_auto_slit_width('output', self._output_port)
        is_float = isinstance(slit_width, float)
        if is_float:
            self._output_slit_width = slit_width
            return slit_width
        else:
            self.log.error('Your hardware getter function \'get_auto_slit_width()\' is not returning a float ')

    @output_slit_width.setter
    def output_slit_width(self, slit_width):
        """
        Setter method setting the active output port slit width of the spectrometer.

        :param slit_width: @float output port slit width
        :return: nothing
        """
        slit_is_present = self.spectrometer_device.auto_slit_is_present('output', self._output_port)
        is_float = isinstance(slit_width, float)
        if is_float:
            if slit_is_present:
                self.spectrometer_device.set_auto_slit_width('output', self._output_port, slit_width)
                self.log.info('Output slit width has been changed correctly ')
                self._output_slit_width = slit_width
            else:
                self.log.debug('Your hardware do not have any auto slit present at the selected output port ')
        else:
            self.log.debug('Output slit width parameter is not correct : it must be a float ')

    ##############################################################################
    #                            Camera functions
    ##############################################################################
    # All functions defined in this part should be used to
    #
    #
    ##############################################################################
    #                           Basic functions
    ##############################################################################

    @property
    def acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]
        Each pixel might be a float, integer or sub pixels
        """

    @property
    def ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        pass

    ##############################################################################
    #                           Read mode functions
    ##############################################################################

    @property
    def read_mode(self):
        """
        Getter method returning the current read mode used by the camera.

        :return: @str read mode (must be compared to a dict)
        """
        pass

    @read_mode.setter
    def read_mode(self, read_mode):
        """
        Setter method setting the read mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :return: nothing
        """
        pass

    def get_track_parameters(self):
        """
        Getter method returning the read mode tracks parameters of the camera.

        :return: @tuple (@int number of track, @int track height, @int track offset) or 0 if error
        """
        pass

    def set_track_parameters(self, number_of_track, track_heigth, track_offset):
        """
        Setter method setting the read mode tracks parameters of the camera.

        :param number_of_track: @int number of track
        :param track_heigth: @int track height
        :param track_offset: @int track offset
        :return: nothing
        """
        pass

    def get_image_parameters(self):
        """
        Getter method returning the read mode image parameters of the camera.

        :return: @tuple (@int pixel height, @int pixel width, @tuple (@int start raw, @int end raw),
        @tuple (@int start column, @int end column)) or 0 if error
        """
        pass

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

    @property
    def acquisition_mode(self):
        """
        Getter method returning the current acquisition mode used by the camera.

        :return: @str acquisition mode (must be compared to a dict)
        """
        pass

    @acquisition_mode.setter
    def acquisition_mode(self, acquisition_mode):
        """
        Setter method setting the acquisition mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :param kwargs: packed @dict which contain a series of arguments specific to the differents acquisition modes
        :return: nothing
        """
        pass

    @property
    def accumulation_time(self):
        """
        Getter method returning the accumulation cycle time scan carry out during an accumulate acquisition mode
         by the camera.

        :return: @int accumulation cycle time or 0 if error
        """
        pass

    @accumulation_time.setter
    def accumulation_time(self, accumulation_time):
        """
        Setter method setting the accumulation cycle time scan carry out during an accumulate acquisition mode
        by the camera.

        :param accumulation_time: @int accumulation cycle time
        :return: nothing
        """
        pass

    @property
    def number_accumulated_scan(self):
        """
        Getter method returning the number of accumulated scan carry out during an accumulate acquisition mode
         by the camera.

        :return: @int number of accumulated scan or 0 if error
        """
        pass

    @number_accumulated_scan.setter
    def number_accumulated_scan(self, number_scan):
        """
        Setter method setting the number of accumulated scan carry out during an accumulate acquisition mode
         by the camera.

        :param number_scan: @int number of accumulated scan
        :return: nothing
        """
        pass

    @property
    def exposure_time(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        pass

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        """ Set the exposure time in seconds

        @param float time: desired new exposure time

        @return float: setted new exposure time
        """
        pass

    @property
    def camera_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        pass

    @camera_gain.setter
    def camera_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """
        pass

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################

    @property
    def trigger_mode(self):
        """
        Getter method returning the current trigger mode used by the camera.

        :return: @str trigger mode (must be compared to a dict)
        """
        pass

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode):
        """
        Setter method setting the trigger mode used by the camera.

        :param trigger_mode: @str trigger mode (must be compared to a dict)
        :return: nothing
        """
        pass

    ##############################################################################
    #                           Shutter mode functions
    ##############################################################################

    @property
    def shutter_is_open(self):
        """
        Getter method returning if the shutter is open.

        :return: @bool shutter open ?
        """
        pass

    @shutter_is_open.setter
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

    @property
    def cooler_ON(self):
        """
        Getter method returning the cooler status if ON or OFF.

        :return: @bool True if ON or False if OFF or 0 if error
        """
        pass

    @cooler_ON.setter
    def cooler_ON(self, cooler_ON):
        """
        Getter method returning the cooler status if ON or OFF.

        :cooler_ON: @bool True if ON or False if OFF
        :return: nothing
        """
        pass

    @property
    def temperature(self):
        """
        Getter method returning the temperature of the camera.

        :return: @float temperature or 0 if error
        """
        pass

    @temperature.setter
    def temperature(self, temperature):
        """
        Getter method returning the temperature of the camera.

        :param temperature: @float temperature or 0 if error
        :return: nothing
        """
        pass