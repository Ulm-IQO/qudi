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

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from logic.save_logic import SaveLogic

from datetime import date

class SpectrumLogic(GenericLogic):
    """This logic module gathers data from the spectrometer.
    """

    # declare connectors
    spectrometer = Connector(interface='SpectrometerInterface')
    camera = Connector(interface='CameraInterface')
    savelogic = Connector(interface='SaveLogic')

    # declare status variables (logic attribute) :
    _acquired_data = np.empty((2, 0))

    # declare status variables (spectro attribute) :
    _wavelength_calibration = StatusVar('wavelength_calibration', 0)

    # declare status variables (camera attribute) :
    _readout_speed = StatusVar('readout_speed', None)
    _camera_gain = StatusVar('camera_gain', None)
    _exposure_time = StatusVar('exposure_time', None)
    _accumulation_delay = StatusVar('accumulation_delay', 1e-2)
    _scan_delay = StatusVar('scan_delay', 1)
    _number_of_scan = StatusVar('number_of_scan', 1)
    _number_accumulated_scan = StatusVar('number_accumulated_scan', 1)

    _acquisition_mode = StatusVar('acquisition_mode', 'SINGLE_SCAN')

    _trigger_mode = StatusVar('trigger_mode', 'INTERNAL')

    # cosmic rejection coeff :
    _coeff_rej_cosmic = StatusVar('coeff_cosmic_rejection', 2.2)

    ##############################################################################
    #                            Basic functions
    ##############################################################################

    def __init__(self, **kwargs):
        """ Create SpectrumLogic object with connectors and status variables loaded.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._save_logic = self.savelogic()

        # hardware constraints :
        self.spectro_constraints = self.spectrometer().get_constraints()
        self.camera_constraints = self.camera().get_constraints()

        self._acquisition_mode_list = ['SINGLE_SCAN', 'MULTI_SCAN', 'LIVE_SCAN', 'ACC_MULTI_SCAN',
                                       'ACC_LIVE_SCAN']

        # gratings :
        self._grating_number = self.spectrometer().get_grating_number()

        # wavelength :
        self._center_wavelength = self.spectrometer().get_wavelength()

        # spectro configurations :
        self._input_port = self.spectrometer().get_input_port()
        self._output_port = self.spectrometer().get_output_port()
        self._input_slit_width = self.spectrometer().get_input_slit_width()
        self._output_slit_width = self.spectrometer().get_output_slit_width()

        # read mode :
        if 'shutter_modes' in self.camera_constraints:
            self._shutter_mode = self.camera().get_shutter_status()
        if 'shutter_modes' in self.spectro_constraints:
            self._shutter_mode = self.spectrometer().get_shutter_status()

        self._read_mode = self.camera().get_read_mode()
        self._active_tracks = self.camera().get_active_tracks()
        self._active_image = self.camera().get_active_image()

        if self._camera_gain==None:
            self._camera_gain = self.camera().get_gain()

        if self._exposure_time==None:
            self._exposure_time = self.camera().get_exposure_time()

        if self._readout_speed==None:
            self._readout_speed = self.camera().get_readout_speed()

        # QTimer for asynchronous execution :
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.loop_acquisition)
        self._loop_counter = 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_acquisition()
            pass

    ##############################################################################
    #                            Acquisition functions
    ##############################################################################

    def start_acquisition(self):
        """ Start acquisition by launching the timer signal calling the 'acquire_data' function.
        """
        if self.module_state() == 'locked':
            self.log.error("Module acquisition is still running, wait before launching a new acquisition "
                           ": module state is currently locked. ")
            return
        self.module_state.lock()
        if self._acquisition_mode == "SINGLE_SCAN":
            self.camera().start_acquisition()
            self.module_state.unlock()
            self._acquired_data = self.get_acquired_data()
            self.log.info("Acquisition finished : module state is 'idle' ")
            return
        self._loop_counter = 0
        self.loop_acquisition()

    def loop_acquisition(self):
        """ Method acquiring data by using the camera hardware method 'start_acquisition'. This method is connected
        to a timer signal : after timer start this slot is called with a period of a time delay. After a certain
        number of call this method can stop the timer if not in 'LIVE' acquisition.

        Tested : yes
        SI check : yes
        """
        self.camera().start_acquisition()
        # Get acquired data : new scan if 'LIVE' or concatenate scan if 'MULTI'
        if self._shutter_mode[-4:] == 'LIVE':
            self._acquired_data = self.get_acquired_data()
        else:
            self._acquired_data = np.append(self._acquired_data, self.get_acquired_data())
        # If 'MULTI' stop acquisition after number_of_scan*number_accumulation loop
        if self._acquisition_mode[-10:-5] == 'MULTI' and self._loop_counter%self._number_of_scan == 0\
                and self._loop_counter!=0:
            self._timer.stop()
            self.module_state.unlock()
            self.log.info("Loop acquisition finished : module state is 'idle' ")
            return
        else:
            delay_time = self._scan_delay
        # Accumulation mode starting with 'ACC' : if accumulation finished apply cosmic rejection from this last data
        if self._acquisition_mode[:3] == 'ACC':
            if self._loop_counter%self._number_accumulated_scan == 0 and self._loop_counter!=0:
                data = self._acquired_data[-self._number_accumulated_scan]
                np.delete(self._acquired_data, np.s_[-self._number_accumulated_scan], axis=0)
                self._acquired_data = np.append(self._acquired_data, self.reject_cosmic(data))
                delay_time = self._scan_delay
            else:
                delay_time = self._accumulation_delay
        # Callback the loop function after delay time
        self._timer.start(delay_time)


    def reject_cosmic(self, data):
        """This function is used to reject cosmic features from acquired spectrum by computing the standard deviation
        of an ensemble of accumulated scan parametrized by the number_accumulated_scan and the accumulation_delay
        parameters. The rejection is carry out with a mask rejecting values outside their standard deviation with a
        weight given by a coeff coeff_rej_cosmic. This method should be only used in "accumulation mode".

        Tested : yes
        SI check : yes
        """
        if len(data)<self._number_accumulated_scan:
            self.log.error("Cosmic rejection impossible : the number of scan in the data parameter is less than the"
                           " number of accumulated scan selected. Choose a different number of accumulated scan or"
                           " make more scan. ")
            return
        mean_data = np.nanstd(data, axis=0)
        std_dev_data = np.nanstd((data-mean_data)**2, axis=0)
        mask_min = mean_data - std_dev_data * self._coeff_rej_cosmic
        mask_max = mean_data + std_dev_data * self._coeff_rej_cosmic
        if len(data.shape) == 2:
            clean_data = np.ma.masked_array([np.ma.masked_outside(pixel, mask_min[i], mask_max[i])
                                             for i,pixel in enumerate(data.T)]).T
            return clean_data
        clean_data = np.transpose(np.empty(np.shape(data)), (1,2,0))
        for i,track in enumerate(np.transpose(data, (1,2,0))):
            clean_track = np.ma.masked_array([np.ma.masked_outside(pixel, mask_min[i, j], mask_max[i, j])
                                             for j,pixel in enumerate(track)])
            clean_data = np.append(clean_data, clean_track)
        return np.transpose(clean_data,(2,0,1))


    def stop_acquisition(self):
        """Method calling the stop acquisition method from the camera hardware module and changing the
        logic module state to 'unlocked'.

        Tested : yes
        SI check : yes
        """
        self._timer.timeout.stop()
        self.camera().stop_acquisition()
        self.module_state.unlock()
        self.log.info("Acquisition stopped : module state is 'idle' ")

    @property
    def acquired_data(self):
        """Getter method returning the last acquired data.
        """
        return self._acquired_data

    @acquired_data.setter
    def acquired_data(self, data):
        """Setter method setting the new acquired data.
        """
        self._acquired_data = data

    def save_acquired_data(self, filepath=None, filename=None):
        parameters = {"camera_gain" : self._camera_gain,
                      "exposure_time" : self._exposure_time,
                      "scan_delay" : self._scan_delay,
                      "accumulation_delay" : self._accumulation_delay,
                      "number_accumulated_scan" : self._number_accumulated_scan,
                      "grating_number" : self._grating_number,
                      "wavelength_calibration" : self._wavelength_calibration}
        self.save_data(self._acquired_data, filepath=filepath, parameters=parameters , filename=filename)

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
    def grating_number(self):
        """Getter method returning the grating number used by the spectrometer.

        @return: (int) active grating number

        Tested : yes
        SI check : yes
        """
        return self._grating_number


    @grating_number.setter
    def grating_number(self, grating_number):
        """Setter method setting the grating number to use by the spectrometer.

        @param grating_number: (int) gating number to set active
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        grating_number = int(grating_number)
        if not 0 < grating_number < self.spectro_constraints['number_of_gratings']:
            self.log.warning('Grating number parameter is not correct : it must be in range 0 to {} '
                           .format(self.spectro_constraints['number_of_gratings'] - 1))
            return
        self.spectrometer().set_grating_number(grating_number)
        self._grating_number = self.spectrometer().get_grating_number()

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################

    @property
    def center_wavelength(self):
        """Getter method returning the center wavelength of the measured spectral range.

        @return: (float) the spectrum center wavelength

        Tested : yes
        SI check : yes
        """
        return self._center_wavelength

    @center_wavelength.setter
    def center_wavelength(self, wavelength):
        """Setter method setting the center wavelength of the measured spectral range.

        @param wavelength: (float) center wavelength
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        wavelength = float(wavelength)
        wavelength_min, wavelength_max = self.spectro_constraints['wavelength_limits'][self._grating_number]
        if not wavelength_min < wavelength < wavelength_max:
            self.log.warning('Wavelength parameter is not correct : it must be in range {} to {} '
                           .format(wavelength_min, wavelength_max))
            return
        self.spectrometer().set_wavelength(wavelength)
        self._center_wavelength = self.spectrometer().get_wavelength()

    @property
    def wavelength_spectrum(self):
        """Getter method returning the wavelength array of the full measured spectral range.
        (used for plotting spectrum with the spectral range)

        @return: (ndarray) measured wavelength array

        Tested : yes (need to
        SI check : yes
        """
        image_length = self.camera_constraints['image_size'][1]
        pixel_length = self.camera_constraints['pixel_size'][1]
        pixels_vector = np.arange(-image_length//2, image_length//2 - image_length%2)*pixel_length
        focal_length, angular_dev, focal_tilt = self.spectro_constraints['optical_parameters']
        ruling, blaze = self.spectro_constraints['gratings_info'][self._grating_number]
        wavelength_spectrum = pixels_vector/np.sqrt(focal_length**2+pixels_vector**2)/ruling + self._center_wavelength
        return wavelength_spectrum

    @property
    def wavelength_calibration(self):
        """Getter method returning the wavelength calibration parameter currently used for
        shifting the spectrum.

        @return: (float) wavelength_calibration used for spectrum calibration
        """
        return self._wavelength_calibration

    @property
    def wavelength_calibration(self, wavelength_calibration):
        """Setter method

        @param wavelength_calibration (float) : wavelength shift used for spectrum calibration
        @return: nothing
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        self.center_wavelength = self._center_wavelength - wavelength_calibration
        self._wavelength_calibration = wavelength_calibration


    ##############################################################################
    #                      Ports and Slits functions
    ##############################################################################

    @property
    def input_port(self):
        """Getter method returning the active current input port of the spectrometer.

        @return: (int) active input port (0 front and 1 side)

        Tested : yes
        SI check : yes
        """
        return self.spectrometer().get_input_port()

    @input_port.setter
    def input_port(self, input_port):
        """Setter method setting the active current input port of the spectrometer.

        @param input_port: (int) active input port (0 front and 1 side)
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if input_port not in self.spectro_constraints['available_port'][0]:
            self.log.warning('Input port parameter is invalid : this parameter must match with input_port '
                           'dictionnary in spectro_constraints')
        self.spectrometer().set_input_port(input_port)
        self._input_port = self.spectrometer().get_input_port()

    @property
    def output_port(self):
        """Getter method returning the active current output port of the spectrometer.

        @return: (int) active output port (0 front and 1 side)

        Tested : yes
        SI check : yes
        """
        return self.spectrometer().get_output_port()

    @output_port.setter
    def output_port(self, output_port):
        """Setter method setting the active current output port of the spectrometer.

        @param output_port: (int) active output port (0 front and 1 side)
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if output_port not in self.spectro_constraints['available_port'][1]:
            self.log.warning('Output port parameter is outvalid : this parameter must match with output_port '
                           'dictionnary in spectro_constraints')
        self.spectrometer().set_output_port(output_port)
        self._output_port = self.spectrometer().get_output_port()

    @property
    def input_slit_width(self):
        """Getter method returning the active input port slit width of the spectrometer.

        @return: (float) input port slit width

        Tested : yes
        SI check : yes
        """
        return self._input_slit_width

    @input_slit_width.setter
    def input_slit_width(self, slit_width):
        """Setter method setting the active input port slit width of the spectrometer.

        @param slit_width: (float) input port slit width
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if not self.spectro_constraints['auto_slit_installed'][0, self._input_port]:
            self.log.warning('Input auto slit is not installed at this input port ')
            return
        slit_width = float(slit_width)
        self.spectrometer().set_input_slit_width(slit_width)
        self._input_slit_width = self.spectrometer().get_input_slit_width()

    @property
    def output_slit_width(self):
        """Getter method returning the active output port slit width of the spectrometer.

        @return: (float) output port slit width

        Tested : yes
        SI check : yes
        """
        return self._output_slit_width

    @output_slit_width.setter
    def output_slit_width(self, slit_width):
        """Setter method setting the active output port slit width of the spectrometer.

        @param slit_width: (float) output port slit width
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if not self.spectro_constraints['auto_slit_installed'][1, self._output_port]:
            self.log.warning('Output auto slit is not installed at this output port ')
            return
        slit_width = float(slit_width)
        self.spectrometer().set_output_slit_width(slit_width)
        self._output_slit_width = self.spectrometer().get_output_slit_width()


    ##############################################################################
    #                            Camera functions
    ##############################################################################
    # All functions defined in this part should be used to
    #
    #
    ##############################################################################
    #                           Basic functions
    ##############################################################################

    def get_acquired_data(self):
        """ Return an array of the last acquired data from camera hardware

        @return: (ndarray) spectrum data of size (number_of_tracks x image_length)
        (for image data the number_of_tracks correspond to image width)
        (if camera only support FVB number_of tracks is 1)
        Each pixel might be a float, integer or sub pixels

        Tested : yes
        SI check : yes
        """
        return self.camera().get_acquired_data()

    ##############################################################################
    #                           Read mode functions
    ##############################################################################

    @property
    def read_mode(self):
        """Getter method returning the current read mode used by the camera.

        @return: (str) read mode logic attribute

        Tested : yes
        SI check : yes
        """
        return self._read_mode

    @read_mode.setter
    def read_mode(self, read_mode):
        """Setter method setting the read mode used by the camera.

        @param read_mode: (str) read mode (must be compared to the list)
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if not read_mode in self.camera_constraints['read_modes']:
            self.log.warning("Read mode parameter do not match with any of the available read "
                           "mode of the camera ")
            return
        self.camera().set_read_mode(read_mode)
        self._read_mode = self.camera().get_read_mode()

    @property
    def readout_speed(self):
        """Getter method returning the readout speed used by the camera.

        @return: (float) readout speed in Hz

        Tested : yes
        SI check : yes
        """
        return self._readout_speed

    @readout_speed.setter
    def readout_speed(self, readout_speed):
        """Setter method setting the readout speed to use by the camera.

        @param readout_speed: (float) readout speed in Hz
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        readout_speed = float(readout_speed)
        if not readout_speed in self.camera_constraints['readout_speeds']:
            self.log.warning("Readout speed parameter must be positive ")
            return
        self.camera().set_readout_speed(readout_speed)
        self._readout_speed = self.camera().get_readout_speed()

    @property
    def active_tracks(self):
        """Getter method returning the read mode tracks parameters of the camera.

        @return: (ndarray) active tracks positions [1st track start, 1st track end, ... ]

        Tested : yes
        SI check : yes
        """
        return self._active_tracks

    @active_tracks.setter
    def active_tracks(self, active_tracks):
        """
        Setter method setting the read mode tracks parameters of the camera.

        @param active_tracks: (ndarray) active tracks positions [1st track start, 1st track end, ... ]
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        image_size = self.camera_constraints['image_size']
        if not np.all(active_tracks[::2]<image_size[0]) or not np.all(active_tracks[1::2]<image_size[1]):
            self.log.warning("Active tracks positions are out of range : some position are out of the pixel matrix ")
            return
        active_tracks = np.array(active_tracks)
        self.camera().set_active_tracks(active_tracks)
        self._active_tracks = self.camera().get_active_tracks()

    @property
    def active_image(self):
        """Getter method returning the acquired area of the camera matrix when in image mode.

        @return: (ndarray) active image parameters [vbin, hbin, vstart, vend, hstart, hend,]

        Tested : yes
        SI check : yes
        """
        return self._active_image

    @active_image.setter
    def active_image(self, active_image):
        """
        Setter method setting the read mode image parameters of the camera.

        @param active_image: (tuple) (vbin, hbin, vstart, vend, hstart, hend)
        vertical_binning: (int) vertical pixel binning
        horizontal_binning: (int) horizontal pixel binning
        vertical_start: (int) image starting row
        vertical_end: (int) image ending row
        horizontal_start: (int) image starting column
        horizontal_end: (int) image ending column

        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        vertical_start = int(active_image[2])
        vertical_end = int(active_image[3])
        vertical_binning = int(active_image[0])
        horizontal_start = int(active_image[4])
        horizontal_end = int(active_image[5])
        horizontal_binning = int(active_image[1])
        if not 0<vertical_start<self.camera_constraints['image_size'][0]\
            or not 0<vertical_end<self.camera_constraints['image_size'][0]:
            self.log.warning("Acquired image vertical range parameters must be positive and "
                           "less than the camera matrix width ")
            return
        if not 0<horizontal_start<self.camera_constraints['image_size'][1]\
            or not 0<horizontal_end<self.camera_constraints['image_size'][1]:
            self.log.warning("Acquired image horizontal range parameters must be positive and "
                           "less than the camera matrix width ")
            return
        if vertical_end<vertical_start:
            vertical_start, vertical_end = vertical_end, vertical_start
        if horizontal_end<horizontal_start:
            horizontal_start, horizontal_end = horizontal_end, horizontal_start
        if not (0 < vertical_binning and vertical_binning%(vertical_end - vertical_start)==0):
            self.log.warning("Pixel vertical binning is not positive or is not a divider of the vertical range ")
            return
        if not (0 < horizontal_binning and horizontal_binning%(horizontal_end - horizontal_start))==0:
            self.log.warning("Pixel horizontal binning is not positive or is not a divider of the horizontal range ")
            return
        self.camera().set_active_image(vertical_binning, horizontal_binning,
                                        vertical_start, vertical_end, horizontal_start, horizontal_end)
        self._active_image = self.camera().get_active_image()

    ##############################################################################
    #                           Acquisition functions
    ##############################################################################

    @property
    def acquisition_mode(self):
        """Getter method returning the current acquisition mode used by the logic module during acquisition.

        @return: (str) acquisition mode logic attribute

        Tested : yes
        SI check : yes
        """
        return self._acquisition_mode


    @acquisition_mode.setter
    def acquisition_mode(self, acquisition_mode):
        """Setter method setting the acquisition mode used by the camera.

        @param acquisition_mode: (str) acquisition mode (must be compared to the list)
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if not acquisition_mode in self._acquisition_mode_list:
            self.log.warning("Acquisition mode parameter do not match with any of the available acquisition "
                           "of the logic module " )
            return
        self._acquisition_mode = acquisition_mode

    @property
    def camera_gain(self):
        """ Get the gain.

        @return: (float) exposure gain

        Tested : yes
        SI check : yes
        """
        return self._camera_gain

    @camera_gain.setter
    def camera_gain(self, camera_gain):
        """ Set the gain.

        @param camera_gain: (float) new gain to set to the camera preamplifier which must correspond to the
        internal gain list given by the constraints dictionary.

        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if not camera_gain in self.camera_constraints['internal_gains']:
            self.log.warning("Camera gain parameter must match with the internal gains list given by the camera "
                           "constraints dictionary ")
            return
        self.camera().set_gain(camera_gain)
        self._camera_gain = self.camera().get_gain()

    @property
    def exposure_time(self):
        """ Get the exposure time in seconds

        @return: (float) exposure time

        Tested : yes
        SI check : yes
        """
        return self._exposure_time

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        """ Set the exposure time in seconds.

        @param exposure_time: (float) desired new exposure time

        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        exposure_time = float(exposure_time)
        if not exposure_time > 0:
            self.log.warning("Exposure time parameter must be a positive number ")
            return
        self.camera().set_exposure_time(exposure_time)
        self._exposure_time = self.camera().get_exposure_time()

    @property
    def accumulation_delay(self):
        """Getter method returning the accumulation delay between consecutive scan during accumulate acquisition mode.

        @return: (float) accumulation delay

        Tested : yes
        SI check : yes
        """
        return self._accumulation_delay

    @accumulation_delay.setter
    def accumulation_delay(self, accumulation_delay):
        """Setter method setting the accumulation delay between consecutive scan during an accumulate acquisition mode.

        @param accumulation_delay: (float) accumulation delay
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        accumulation_delay = float(accumulation_delay)
        if not accumulation_delay > 0 :
            self.log.warning("Accumulation delay parameter must be a positive number ")
            return
        if not self._exposure_time < accumulation_delay < self._scan_delay:
            self.log.warning("Accumulation delay parameter must be a value between"
                           "the current exposure time and scan delay values ")
            return
        self._accumulation_delay = accumulation_delay

    @property
    def scan_delay(self):
        """Getter method returning the scan delay between consecutive scan during multiple acquisition mode.

        @return: (float) scan delay

        Tested : yes
        SI check : yes
        """
        return self._scan_delay

    @scan_delay.setter
    def scan_delay(self, scan_delay):
        """Setter method setting the scan delay between consecutive scan during multiple acquisition mode.

        @param scan_delay: (float) scan delay
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        scan_delay = float(scan_delay)
        if not scan_delay > 0:
            self.log.warning("Scan delay parameter must be a positive number ")
            return
        if not self._exposure_time < self._scan_delay:
            self.log.warning("Scan delay parameter must be a value bigger than"
                           "the current exposure time ")
            return
        self._scan_delay = scan_delay

    @property
    def number_accumulated_scan(self):
        """Getter method returning the number of accumulated scan during accumulate acquisition mode.

        @return: (int) number of accumulated scan

        Tested : yes
        SI check : yes
        """
        return self._number_accumulated_scan

    @number_accumulated_scan.setter
    def number_accumulated_scan(self, number_scan):
        """Setter method setting the number of accumulated scan during accumulate acquisition mode.

        @param number_scan: (int) number of accumulated scan
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        number_scan = int(number_scan)
        if not number_scan > 0:
            self.log.warning("Number of accumulated scan parameter must be positive ")
            return
        self._number_accumulated_scan = number_scan

    @property
    def number_of_scan(self):
        """Getter method returning the number of acquired scan during multiple acquisition mode.

        @return: (int) number of acquired scan

        Tested : yes
        SI check : yes
        """
        return self._number_of_scan

    @number_of_scan.setter
    def number_of_scan(self, number_scan):
        """Setter method setting the number of acquired scan during multiple acquisition mode.

        @param number_scan: (int) number of acquired scan
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        number_scan = int(number_scan)
        if not number_scan > 0:
            self.log.warning("Number of acquired scan parameter must be positive ")
            return
        self._number_of_scan = number_scan

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################

    @property
    def trigger_mode(self):
        """Getter method returning the current trigger mode used by the camera.

        @return: (str) trigger mode (must be compared to the list)

        Tested : yes
        SI check : yes
        """
        return self._trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode):
        """Setter method setting the trigger mode used by the camera.

        @param trigger_mode: (str) trigger mode (must be compared to the list)
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if not trigger_mode in self.camera_constraints['trigger_modes']:
            self.log.warning("Trigger mode parameter do not match with any of available trigger "
                           "mode of the camera in the camera_constraints dictionary ")
            return
        self.camera().set_trigger_mode(trigger_mode)
        self._trigger_mode = self.camera().get_trigger_mode()

    ##############################################################################
    #                           Shutter mode functions (optional)
    ##############################################################################

    @property
    def shutter_mode(self):
        """Getter method returning the shutter mode.

        @return: (str) shutter mode (must be compared to the list)

        Tested : yes
        SI check : yes
        """
        if 'shutter_modes' in self.camera_constraints:
            return self._shutter_mode
        if 'shutter_modes' in self.spectro_constraints:
            return self._shutter_mode
        self.log.warning("Your hardware seems to don't have any shutter available has mentioned in"
                       "the constraints dictionaries ")
        return None

    @shutter_mode.setter
    def shutter_mode(self, shutter_mode):
        """Setter method setting the shutter mode.

        @param shutter_mode: (str) shutter mode (must be compared to the list)
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if 'shutter_modes' in self.camera_constraints:
            self.camera().set_shutter_status(shutter_mode)
            self._shutter_mode = self.camera().get_shutter_status()
            return
        if 'shutter_modes' in self.spectro_constraints:
            self.spectrometer().set_shutter_status(shutter_mode)
            self._shutter_mode = self.spectrometer().get_shutter_status()
            return
        self.log.warning("Shutter mode parameter do not match with any of available shutter "
                        "mode of the camera ")

    ##############################################################################
    #                           Temperature functions
    ##############################################################################

    @property
    def cooler_status(self):
        """Getter method returning the cooler status if ON or OFF.

        @return: (str) cooler status

        Tested : yes
        SI check : yes
        """
        if self.camera_constraints['has_cooler'] == True:
            return self.camera().get_cooler_status()
        self.log.warning("Your camera hardware seems to don't have any temperature controller set as mentioned in"
                       "the camera_constraints dictionary ")
        return None

    @cooler_status.setter
    def cooler_status(self, cooler_status):
        """Setter method returning the cooler status if ON or OFF.

        @param cooler_status: (bool) 1 if ON or 0 if OFF
        @return: nothing

        Tested : yes
        SI check : yes
        """
        cooler_status = int(cooler_status)
        if not cooler_status in [0, 1]:
            self.log.warning("Cooler status parameter is not correct : it must be 1 (ON) or 0 (OFF) ")
            return
        if self.camera_constraints['has_cooler'] == True:
            self.camera().set_cooler_status(cooler_status)
            return
        self.log.warning("Your camera hardware seems to don't have any temperature controller set as mentioned in"
                       "the camera_constraints dictionary ")

    @property
    def camera_temperature(self):
        """Getter method returning the temperature of the camera.

        @return: (float) temperature

        Tested : yes
        SI check : yes
        """
        if self.camera_constraints['has_cooler'] == True:
            return self.camera().get_temperature()
        self.log.warning("Your camera hardware seems to don't have any temperature controller set as mentioned in"
                       "the camera_constraints dictionary ")
        return None

    @camera_temperature.setter
    def camera_temperature(self, temperature_setpoint):
        """Setter method returning the temperature of the camera.

        @param temperature: (float) temperature
        @return: nothing

        Tested : yes
        SI check : yes
        """
        if self.camera_constraints['has_cooler'] == True:
            temperature_setpoint = float(temperature_setpoint)
            if temperature_setpoint<0:
                self.log.warning("Camera temperature setpoint parameter must be a positive number : the temperature unit"
                               "is in Kelvin ")
                return
            self.camera().set_temperature(temperature_setpoint)
        self.log.warning("Your camera hardware seems to don't have any temperature controller set as mentioned in"
                       "the camera_constraints dictionary ")
        return None