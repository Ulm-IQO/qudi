# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module to interface a spectrometer camera and grating.

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
from enum import Enum

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption

from interface.grating_spectrometer_interface import PortType
from interface.science_camera_interface import ReadMode, ShutterState
from hardware.camera.andor_camera import TriggerMode, ImageAdvancedParameters

from scipy import optimize

import time


class AcquisitionMode(Enum):
    """ Internal class defining the possible read modes of the camera

    SINGLE_SCAN : single scan acquisition
    MULTI_SCAN : multiple scan acquisition
    LIVE_SCAN : live scan acquisition
    """
    SINGLE_SCAN = 0
    MULTI_SCAN = 1
    LIVE_SCAN = 2


class SpectrumLogic(GenericLogic):
    """ This logic module handle the spectrometer gratings and camera """

    spectrometer = Connector(interface='GratingSpectrometerInterface')
    camera = Connector(interface='ScienceCameraInterface')
    savelogic = Connector(interface='SaveLogic')

    # declare config options :
    _reverse_data_with_side_output = ConfigOption('reverse_data_with_side_output', False)

    # declare status variables (logic attribute) :
    _acquired_data = StatusVar('acquired_data', None)
    _acquired_wavelength = StatusVar('acquired_wavelength', None)
    _wavelength_calibration = StatusVar('wavelength_calibration', np.array([0., 0., 0.]))

    # declare status variables (camera attribute) :
    _camera_gain = StatusVar('camera_gain', None)
    _readout_speed = StatusVar('readout_speed', None)
    _exposure_time = StatusVar('exposure_time', None)
    _scan_delay = StatusVar('scan_delay', 0)
    _scan_wavelength_step = StatusVar('scan_wavelength_step', 0)
    _number_of_scan = StatusVar('number_of_scan', 1)
    _acquisition_mode = StatusVar('acquisition_mode', 'SINGLE_SCAN')
    _temperature_setpoint = StatusVar('temperature_setpoint', None)
    _shutter_state = StatusVar('shutter_state', "AUTO")
    _active_tracks = StatusVar('active_tracks', [])
    _image_advanced_dict = StatusVar('image_advanced_dict', None) #TODO : fix bug

    _sigStart = QtCore.Signal()
    _sigCheckStatus = QtCore.Signal()
    sigUpdateData = QtCore.Signal()
    sigUpdateSettings = QtCore.Signal()

    ##############################################################################
    #                            Basic functions
    ##############################################################################

    def __init__(self, **kwargs):
        """ Create SpectrumLogic object with connectors and status variables loaded.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)
        self.threadlock = Mutex()

        # Public attributes
        self.spectro_constraints = None
        self.camera_constraints = None

        # Private attributes
        self._cooler_status = None
        self._grating = None
        self._center_wavelength = None
        self._input_ports = None
        self._output_ports = None
        self._input_port = None
        self._output_port = None
        self._input_slit_width = None
        self._output_slit_width = None
        self._read_mode = None
        self._trigger_mode = None
        self._loop_counter = None
        self._loop_timer = None
        self._acquisition_params = None

    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        self.spectro_constraints = self.spectrometer().get_constraints()
        self.camera_constraints = self.camera().get_constraints()

        ports = self.spectro_constraints.ports
        self._output_ports = [port for port in ports if port.type == PortType.OUTPUT_SIDE or
                              port.type == PortType.OUTPUT_FRONT]
        self._input_ports = [port for port in ports if port.type == PortType.INPUT_SIDE or
                             port.type == PortType.INPUT_FRONT]

        # Get current physical state
        self._grating = self.spectrometer().get_grating()
        self._center_wavelength = self.spectrometer().get_wavelength()
        self._input_port = self.spectrometer().get_input_port()
        self._output_port = self.spectrometer().get_output_port()
        self._input_slit_width = [self.spectrometer().get_slit_width(port.type) if port.is_motorized else 0
                                  for port in self._input_ports]
        self._output_slit_width = [self.spectrometer().get_slit_width(port.type) if port.is_motorized else 0
                                   for port in self._output_ports]

        # Get camera state
        self._read_mode = self.camera().get_read_mode()
        self._trigger_mode = self.camera().get_trigger_mode()

        # Try status variable value or take current hardware value if status variable is None
        self.readout_speed = self._readout_speed or self.camera().get_readout_speed()
        self.camera_gain = self._camera_gain or self.camera().get_gain()
        self.exposure_time = self._exposure_time or self.camera().get_exposure_time()

        if self.camera_constraints.has_cooler:
            if self._temperature_setpoint:
                self.temperature_setpoint = self._temperature_setpoint
            else:
                self.temperature_setpoint = self.camera().get_temperature_setpoint()

        if self._image_advanced_dict:
            self._image_advanced = ImageAdvancedParameters()
            self._image_advanced.vertical_start = self._image_advanced_dict["vertical_start"]
            self._image_advanced.vertical_end = self._image_advanced_dict["vertical_end"]
            self._image_advanced.horizontal_start = self._image_advanced_dict["horizontal_start"]
            self._image_advanced.horizontal_end = self._image_advanced_dict["horizontal_end"]
            self._image_advanced.horizontal_binning = self._image_advanced_dict["horizontal_binning"]
            self._image_advanced.vertical_binning = self._image_advanced_dict["vertical_binning"]
            self.camera().set_image_advanced_parameters(self._image_advanced)
        else:
            self._image_advanced = self.camera().get_image_advanced_parameters()

        if self._active_tracks != []:
            self.camera().set_active_tracks(self.active_tracks)

        self._cooler_status = self.cooler_status

        # QTimer for asynchronous execution :
        self._loop_counter = 0

        self._acquisition_params = OrderedDict()
        self._update_acquisition_params()

        self._sigStart.connect(self._start_acquisition)
        self._sigCheckStatus.connect(self._check_status, QtCore.Qt.QueuedConnection)
        self._loop_timer = QtCore.QTimer()
        self._loop_timer.setSingleShot(True)
        self._loop_timer.timeout.connect(self._acquisition_loop, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module. """
        if self.module_state() != 'idle':
            self.stop_acquisition()
            self.log.warning('Stopping running acquisition due to module deactivation.')

        self._image_advanced_dict = {"vertical_start":self._image_advanced.vertical_start,
                                     "vertical_end":self._image_advanced.vertical_end,
                                     "horizontal_start":self._image_advanced.horizontal_start,
                                     "horizontal_end":self._image_advanced.horizontal_end,
                                     "horizontal_binning":self._image_advanced.horizontal_binning,
                                     "vertical_binning":self._image_advanced.vertical_binning,
                                     }

        self._sigStart.disconnect()
        self._sigCheckStatus.disconnect()
        self.sigUpdateSettings.disconnect()



    ##############################################################################
    #                            Acquisition functions
    ##############################################################################

    def take_acquisition(self):
        """ Method use by other modules and script to start acquisition, wait for the end and return the result

        @return (np.ndarray):  The newly acquired data
        """
        if self.module_state() == 'locked':
            self.log.error("Module acquisition is still running, module state is currently locked.")
        self.start_acquisition()
        time.sleep(self._exposure_time)
        while self.module_state() != 'idle':
            time.sleep(0.1)
        return self.acquired_data

    def start_acquisition(self):
        """ Start acquisition in the module's thread and return immediately """
        if self.module_state() == 'locked':
            self.log.error("Module acquisition is still running, module state is currently locked.")
            return
        self.module_state.lock()
        self._update_acquisition_params()
        self._sigStart.emit()

    def _start_acquisition(self):
        """ Start acquisition method initializing the acquisitions constants and calling the acquisition method """
        if self.acquisition_mode == 'MULTI_SCAN':
            self._loop_counter = self.number_of_scan
        self._acquisition_loop()

    def _acquisition_loop(self):
        """ Acquisition method starting hardware acquisition and emitting Qtimer signal connected to check status method
        """
        self._loop_counter -= 1
        self.camera().start_acquisition()
        self._sigCheckStatus.emit()

    def _check_status(self):
        """ Method / Slot used by the acquisition call by Qtimer signal to check if the acquisition is complete """
        # If module unlocked by stop_acquisition
        if self.module_state() != 'locked':
            self.sigUpdateData.emit()
            self.center_wavelength = self.center_wavelength
            self.log.info("Acquisition stopped. Status loop stopped.")
            return

        # If hardware still running
        if not self.camera().get_ready_state():
            self._sigCheckStatus.emit()
            return

        if self.acquisition_mode == 'SINGLE_SCAN':
            self._acquired_wavelength = self.wavelength_spectrum
            self._acquired_data = self.get_acquired_data()
            self.module_state.unlock()
            self.sigUpdateData.emit()
            self.log.info("Acquisition finished : module state is 'idle' ")
            return

        elif self.acquisition_mode == 'LIVE_SCAN':
            self._loop_counter += 1
            self._acquired_wavelength = self.wavelength_spectrum
            self._acquired_data = self.get_acquired_data()
            self.sigUpdateData.emit()
            self._acquisition_loop()
            return

        else:
            if self._loop_counter == self._acquisition_params["number_of_scan"]-1:
                self._acquired_wavelength = [self.wavelength_spectrum]
                self._acquired_data = [self.get_acquired_data()]
            else:
                self._acquired_wavelength.append(self.wavelength_spectrum)
                self._acquired_data.append(self.get_acquired_data())

            if self._loop_counter <= 0:
                self.module_state.unlock()
                self.sigUpdateData.emit()
                self.center_wavelength = self.center_wavelength
                self.log.info("Acquisition finished : module state is 'idle' ")
            else:
                self.sigUpdateData.emit()
                self._do_scan_step()
                self._loop_timer.start(self.scan_delay*1000)
                return

    def stop_acquisition(self):
        """ Method to abort the acquisition """
        if self.camera().get_ready_state() == 'locked':
            self.camera().abort_acquisition()
        if self.module_state() == 'locked':
            self.module_state.unlock()
        self.log.debug("Acquisition stopped : module state is 'idle' ")

    @property
    def acquired_data(self):
        """ Getter method returning the last acquired data. """
        return np.array(self._acquired_data)

    @property
    def acquired_wavelength(self):
        """ Getter method returning the last acquired data. """
        return np.array(self._acquired_wavelength)

    @property
    def acquisition_params(self):
        """ Getter method returning the last acquisition parameters. """
        return self._acquisition_params

    def _update_acquisition_params(self):
        self._acquisition_params['read_mode'] = self.read_mode
        self._acquisition_params['acquisition_mode'] = self.acquisition_mode
        if self.read_mode == 'IMAGE_ADVANCED':
            self._acquisition_params['image_advanced'] = (self.image_advanced_binning, self.image_advanced_area)
        if self.read_mode == 'MULTIPLE_TRACKS':
            self._acquisition_params['tracks'] = self.active_tracks
        if self.acquisition_mode == 'MULTI_SCAN':
            self._acquisition_params['scan_delay'] = self.scan_delay
            self._acquisition_params['number_of_scan'] = self.number_of_scan
            self._acquisition_params['scan_wavelength_step'] = self.scan_wavelength_step
        self._acquisition_params['camera_gain'] = self.camera_gain
        self._acquisition_params['readout_speed'] = self.readout_speed
        self._acquisition_params['exposure_time'] = self.exposure_time
        self._acquisition_params['center_wavelength'] = self.center_wavelength
        self._acquisition_params['grating'] = self.grating
        self._acquisition_params['spectro_ports'] = self.input_port, self.output_port
        self._acquisition_params['slit_width'] = self._input_slit_width, self._output_slit_width
        self._acquisition_params['wavelength_calibration'] = self.wavelength_calibration

    def save_acquired_data(self):
        """ Getter method returning the last acquisition parameters. """

        filepath = self.savelogic().get_path_for_module(module_name='spectrum')
        data = np.array(self._acquired_data)

        if self.acquisition_params['read_mode'] == 'IMAGE_ADVANCED':
            acquisition = {'data': data.flatten()}
        else:
            spectrum = np.array(self._acquired_wavelength)
            acquisition = {'wavelength' : spectrum.flatten(), 'data': data.flatten()}

        self.savelogic().save_data(acquisition, filepath=filepath, parameters=self.acquisition_params)

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
        """ Getter method returning the grating index used by the spectrometer.

        @return (int): active grating index
        """
        return self._grating

    @grating.setter
    def grating(self, grating):
        """ Setter method setting the grating index to use by the spectrometer.

        @param (int) grating: gating index to set active
        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        grating = int(grating)
        if grating == self._grating:
            return
        number_of_gratings = len(self.spectro_constraints.gratings)
        if not 0 <= grating < number_of_gratings:
            self.log.error('Grating number parameter is not correct : it must be in range 0 to {} '
                           .format(number_of_gratings - 1))
            return
        self.spectrometer().set_grating(grating)
        self._grating = self.spectrometer().get_grating()
        self.sigUpdateSettings.emit()

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################

    @property
    def center_wavelength(self):
        """Getter method returning the center wavelength of the measured spectral range.

        @return: (float) the spectrum center wavelength

        """
        if self._center_wavelength == 0:
            return self._center_wavelength
        else:
            return self._center_wavelength + self.wavelength_calibration

    @center_wavelength.setter
    def center_wavelength(self, wavelength):
        """Setter method setting the center wavelength of the measured spectral range.

        @param wavelength: (float) center wavelength


        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        wavelength = float(wavelength)
        if wavelength != 0:
            wavelength = float(wavelength - self.wavelength_calibration)
        else:
            wavelength = float(wavelength)
        wavelength_max = self.spectro_constraints.gratings[self.grating].wavelength_max
        if not 0 <= wavelength < wavelength_max:
            self.log.error('Wavelength parameter is not correct : it must be in range {} to {} '
                           .format(0, wavelength_max))
            return
        self.spectrometer().set_wavelength(wavelength)
        self._center_wavelength = self.spectrometer().get_wavelength()
        self.sigUpdateSettings.emit()

    def _do_scan_step(self):
        """Setter method setting the center wavelength of the measured spectral range.

        @param wavelength: (float) center wavelength


        """
        if self._scan_wavelength_step == 0:
            self.log.info('The wavelength step of the scan is 0, no change of the center wavelength.')
            return
        wavelength = self.spectrometer().get_wavelength() + self._scan_wavelength_step
        wavelength_max = self.spectro_constraints.gratings[self.grating].wavelength_max
        if not 0 <= wavelength < wavelength_max:
            self.log.error('Wavelength parameter is not correct : it must be in range {} to {} '
                           .format(0, wavelength_max))
            return
        self.spectrometer().set_wavelength(wavelength)

    @property
    def wavelength_spectrum(self):
        """Getter method returning the wavelength array of the full measured spectral range.
        (used for plotting spectrum with the spectral range)

        @return: (ndarray) measured wavelength array


        """
        pixel_width = self.camera_constraints.pixel_size_width
        image_width = self.camera_constraints.width
        if self._center_wavelength == 0:
            return np.arange(0, image_width)*pixel_width
        else:
            return self.spectrometer().get_spectrometer_dispersion(image_width, pixel_width) + self.wavelength_calibration

    @property
    def wavelength_calibration(self):
        """Getter method returning the wavelength calibration parameter currently used for
        shifting the spectrum.

        @return: (float) wavelength_calibration used for spectrum calibration
        """
        return self._wavelength_calibration[self.grating]

    @wavelength_calibration.setter
    def wavelength_calibration(self, wavelength_calibration):
        """Setter method

        @param wavelength_calibration (float) : wavelength shift used for spectrum calibration

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        self._wavelength_calibration[self.grating] = float(wavelength_calibration)
        self.sigUpdateSettings.emit()


    ##############################################################################
    #                      Ports and Slits functions
    ##############################################################################

    @property
    def input_port(self):
        """Getter method returning the active current input port of the spectrometer.

        @return: (int) active input port (0 front and 1 side)

        """
        return self._input_port.name

    @input_port.setter
    def input_port(self, input_port):
        """Setter method setting the active current input port of the spectrometer.

        @param input_port: (str|PortType) active input port (front or side)


        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if len(self._input_ports) < 2:
            self.log.warning('Input port has no flipper mirror : this port can\'t be changed ')
            return
        elif input_port == 'front':
            input_port = PortType.INPUT_FRONT
        elif input_port == 'side':
            input_port = PortType.INPUT_SIDE
        elif isinstance(input_port, str) and input_port in PortType.__members__:
            input_port = PortType[input_port]
        if not np.any([input_port==port.type for port in self._input_ports]):
            self.log.error('Function parameter must be an INPUT value from the input ports of the camera ')
            return
        if input_port == self._input_port:
            return
        self.spectrometer().set_input_port(input_port)
        self._input_port = self.spectrometer().get_input_port()
        self.sigUpdateSettings.emit()

    @property
    def output_port(self):
        """Getter method returning the active current output port of the spectrometer.

        @return: (int) active output port (0 front and 1 side)

        """
        return self._output_port.name

    @output_port.setter
    def output_port(self, output_port):
        """Setter method setting the active current output port of the spectrometer.

        @param output_port: (int) active output port (0 front and 1 side)


        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if len(self._output_ports) < 2:
            self.log.warning('Output port has no flipper mirror : this port can\'t be changed ')
            return
        elif output_port == 'front':
            output_port = PortType.OUTPUT_FRONT
        elif output_port == 'side':
            output_port = PortType.OUTPUT_SIDE
        elif isinstance(output_port, str) and output_port in PortType.__members__:
            output_port = PortType[output_port]
        if not np.any([output_port==port.type for port in self._output_ports]):
            self.log.error('Function parameter must be an OUTPUT value from the output ports of the camera ')
            return
        if output_port == self._output_port:
            return
        self.spectrometer().set_output_port(output_port)
        self._output_port = self.spectrometer().get_output_port()
        self.sigUpdateSettings.emit()

    @property
    def input_slit_width(self):
        """Getter method returning the active input port slit width of the spectrometer.

        @return: (float) input port slit width
        """
        return self.get_input_slit_width()

    @input_slit_width.setter
    def input_slit_width(self, slit_width):
        """Setter method setting the active input port slit width of the spectrometer.

        @param slit_width: (float) input port slit width

        """
        self.set_input_slit_width(slit_width)

    @property
    def output_slit_width(self):
        """Getter method returning the active output port slit width of the spectrometer.

        @return: (float) output port slit width

        """
        return self.get_output_slit_width()

    @output_slit_width.setter
    def output_slit_width(self, slit_width):
        """Setter method setting the active output port slit width of the spectrometer.

        @param slit_width: (float) output port slit width

        """
        self.set_output_slit_width(slit_width)

    def get_input_slit_width(self, port='current'):
        """Getter method returning the active input port slit width of the spectrometer.

        @param input port: (Port|str) port
        @return: (float) input port slit width
        """
        if port == 'current':
            port = self._input_port
        elif port == 'front':
            port = PortType.INPUT_FRONT
        elif port == 'side':
            port = PortType.INPUT_SIDE
        elif isinstance(port, PortType):
            port = port.name
        elif isinstance(port, str) and port in PortType.__members__:
            port = PortType[port]
        else:
            self.log.error("Port parameter do not match with the possible values : 'current', 'front' and 'side' ")
            return
        input_types = [port.type for port in self._input_ports]
        if port not in input_types:
            self.log.error('Input port {} doesn\'t exist on your hardware '.format(port.name))
            return 0
        index = input_types.index(port)
        return self._input_slit_width[index]

    def set_input_slit_width(self, slit_width, port='current'):
        """Setter method setting the active input port slit width of the spectrometer.

        @param slit_width: (float) input port slit width
        @param input port: (Port|str) port
        """
        slit_width = float(slit_width)
        if port == 'current':
            port = self._input_port
        elif port == 'front':
            port = PortType.INPUT_FRONT
        elif port == 'side':
            port = PortType.INPUT_SIDE
        elif not isinstance(port, PortType):
            self.log.error("Port parameter do not match with the possible values : 'current', 'front' and 'side' ")
            return
        input_types = [port.type for port in self._input_ports]
        if port not in input_types:
            self.log.error('Input port {} doesn\'t exist on your hardware '.format(port.name))
            return
        index = input_types.index(port)
        if self._input_slit_width[index] == slit_width:
            return
        self.spectrometer().set_slit_width(port, slit_width)
        self._input_slit_width[index] = self.spectrometer().get_slit_width(port)
        self.sigUpdateSettings.emit()

    def get_output_slit_width(self, port='current'):
        """Getter method returning the active output port slit width of the spectrometer.

        @param output port: (Port|str) port
        @return: (float) output port slit width

        """
        if port == 'current':
            port = self._output_port
        elif port == 'front':
            port = PortType.OUTPUT_FRONT
        elif port == 'side':
            port = PortType.OUTPUT_SIDE
        elif isinstance(port, PortType):
            port = port.name
        elif isinstance(port, str) and port in PortType.__members__:
            port = PortType[port]
        else:
            self.log.error("Port parameter do not match with the possible values : 'current', 'front' and 'side' ")
            return
        output_types = [port.type for port in self._output_ports]
        if port not in output_types:
            self.log.error('Output port {} doesn\'t exist on your hardware '.format(port.name))
            return 0
        index = output_types.index(port)
        return self._output_slit_width[index]

    def set_output_slit_width(self, slit_width, port='current'):
        """Setter method setting the active output port slit width of the spectrometer.

        @param slit_width: (float) output port slit width
        @param output port: (Port|str) port

        """
        slit_width = float(slit_width)
        if port == 'current':
            port = self._output_port
        elif port == 'front':
            port = PortType.OUTPUT_FRONT
        elif port == 'side':
            port = PortType.OUTPUT_SIDE
        elif not isinstance(port, PortType):
            self.log.error("Port parameter do not match with the possible values : 'current', 'front' and 'side' ")
            return
        output_types = [port.type for port in self._output_ports]
        if port not in output_types:
            self.log.error('Output port {} doesn\'t exist on your hardware '.format(port.name))
            return
        index = output_types.index(port)
        if self._output_slit_width[index] == slit_width:
            return
        self.spectrometer().set_slit_width(port, slit_width)
        self._output_slit_width[index] = self.spectrometer().get_slit_width(port)
        self.sigUpdateSettings.emit()

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
        """ Return an array of last acquired data.

           @return: Data in the format depending on the read mode.

           Depending on the read mode, the format is :
           'FVB' : 1d array
           'MULTIPLE_TRACKS' : list of 1d arrays
           'IMAGE' 2d array of shape (width, height)
           'IMAGE_ADVANCED' 2d array of shape (width, height)

           Each value might be a float or an integer.
           """
        data = self.camera().get_acquired_data()
        if self._reverse_data_with_side_output and self.output_port == "OUTPUT_SIDE":
            return netobtain(data.T[::-1].T)
        return netobtain(data)

    ##############################################################################
    #                           Read mode functions
    ##############################################################################

    @property
    def read_mode(self):
        """Getter method returning the current read mode used by the camera.

        @return: (str) read mode logic attribute

        """
        return self._read_mode

    @read_mode.setter
    def read_mode(self, read_mode):
        """Setter method setting the read mode used by the camera.

        @param read_mode: (str|ReadMode) read mode

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if read_mode == self._read_mode:
            return
        if isinstance(read_mode, str) and read_mode in ReadMode.__members__:
            read_mode = ReadMode[read_mode]
        if read_mode not in self.camera_constraints.read_modes:
            self.log.error("Read mode parameter do not match with any of the available read "
                           "modes of the camera ")
            return
        self.camera().set_read_mode(read_mode)
        self._read_mode = self.camera().get_read_mode().name

    @property
    def readout_speed(self):
        """Getter method returning the readout speed used by the camera.

        @return: (float) readout speed in Hz

        """
        return self._readout_speed

    @readout_speed.setter
    def readout_speed(self, readout_speed):
        """Setter method setting the readout speed to use by the camera.

        @param readout_speed: (float) readout speed in Hz


        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        readout_speed = float(readout_speed)
        index = (np.abs(np.array(self.camera_constraints.readout_speeds)-readout_speed)).argmin()
        readout_speed = self.camera_constraints.readout_speeds[index]
        if readout_speed == self._readout_speed:
            return
        self.camera().set_readout_speed(readout_speed)
        self._readout_speed = self.camera().get_readout_speed()

    @property
    def active_tracks(self):
        """Getter method returning the read mode tracks parameters of the camera.

        @return: (list) active tracks positions [1st track start, 1st track end, ... ]

        """
        return self._active_tracks

    @active_tracks.setter
    def active_tracks(self, active_tracks):
        """
        Setter method setting the read mode tracks parameters of the camera.

        @param active_tracks: (list/ndarray) active tracks positions [1st track start, 1st track end, ... ]


        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        active_tracks = np.array(active_tracks, dtype=int)
        image_height = self.camera_constraints.height


        if not len(active_tracks)%2 == 0:
            active_tracks = np.append(active_tracks, image_height-1)
        sorted_tracks = np.argsort(active_tracks)
        if np.any(np.abs(sorted_tracks[::2]-sorted_tracks[1::2])!= 1):
            self.log.error("The input active tracks are overlapping !")
            return
        self.camera().set_active_tracks(active_tracks)
        self._active_tracks = np.array(self.camera().get_active_tracks())

    @property
    def image_advanced_binning(self):
        return {'horizontal_binning': self._image_advanced.horizontal_binning,
                 'vertical_binning': self._image_advanced.vertical_binning}

    @image_advanced_binning.setter
    def image_advanced_binning(self, binning):
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        binning = list(binning)
        if len(binning) != 2:
            self.log.error("Binning parameter must be a tuple or list of 2 elements respectively the horizontal and "
                           "vertical binning ")
            return
        width = abs(self.image_advanced_area['horizontal_range'][1]-self.image_advanced_area['horizontal_range'][0])
        height = abs(self.image_advanced_area['vertical_range'][1]-self.image_advanced_area['vertical_range'][0])
        if not 0<binning[0]<width or not 0<binning[1]<height:
            self.log.error("Binning parameter is out of range : the binning is outside the image dimensions in pixel ")
            return
        self._image_advanced.horizontal_binning = int(binning[0])
        self._image_advanced.vertical_binning = int(binning[1])
        self.image_advanced_area = [self._image_advanced.horizontal_start, self._image_advanced.horizontal_end,
                                    self._image_advanced.vertical_start, self._image_advanced.vertical_end]

    @property
    def image_advanced_area(self):
        return {'horizontal_range': (self._image_advanced.horizontal_start, self._image_advanced.horizontal_end),
                'vertical_range': (self._image_advanced.vertical_start, self._image_advanced.vertical_end)}

    @image_advanced_area.setter
    def image_advanced_area(self, image_advanced_area):
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        image_advanced_area = list(image_advanced_area)
        if len(image_advanced_area) != 4:
            self.log.error("Image area parameter must be a tuple or list of 4 elements like this [horizontal start, "
                           "horizontal end, vertical start, vertical end] ")
            return

        width = self.camera_constraints.width
        height = self.camera_constraints.height
        if image_advanced_area[0] > image_advanced_area[1]:
            image_advanced_area[0], image_advanced_area[1] = image_advanced_area[1], image_advanced_area[0]
        if 0 > image_advanced_area[0]:
            image_advanced_area[0] = 0
        if image_advanced_area[1] > width:
            image_advanced_area[1] = width-1
        if image_advanced_area[2] > image_advanced_area[3]:
            image_advanced_area[2], image_advanced_area[3] = image_advanced_area[3], image_advanced_area[2]
        if 0 > image_advanced_area[2]:
            image_advanced_area[2] = 0
        if image_advanced_area[3] > height:
            image_advanced_area[3] = height-1

        hbin = self._image_advanced.horizontal_binning
        vbin = self._image_advanced.vertical_binning
        if not (image_advanced_area[1]-image_advanced_area[0]+1) % hbin == 0:
            image_advanced_area[1] = (image_advanced_area[1] - image_advanced_area[0]+1) // hbin * hbin -1 + image_advanced_area[0]
        if not (image_advanced_area[3]-image_advanced_area[2]+1) % vbin == 0:
            image_advanced_area[3] = (image_advanced_area[3] - image_advanced_area[2]+1) // vbin * vbin -1 + image_advanced_area[2]

        self._image_advanced.horizontal_start = int(image_advanced_area[0])
        self._image_advanced.horizontal_end = int(image_advanced_area[1])
        self._image_advanced.vertical_start = int(image_advanced_area[2])
        self._image_advanced.vertical_end = int(image_advanced_area[3])

        self.camera().set_image_advanced_parameters(self._image_advanced)

    ##############################################################################
    #                           Acquisition functions
    ##############################################################################

    @property
    def acquisition_mode(self):
        """Getter method returning the current acquisition mode used by the logic module during acquisition.

        @return (str): acquisition mode

        """
        return self._acquisition_mode


    @acquisition_mode.setter
    def acquisition_mode(self, acquisition_mode):
        """Setter method setting the acquisition mode used by the camera.

        @param (str|AcquisitionMode): Acquisition mode as a string or an object

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if isinstance(acquisition_mode, AcquisitionMode):
            acquisition_mode = acquisition_mode.name
        if acquisition_mode not in AcquisitionMode.__members__:
            self.log.error("Acquisition mode parameter do not match with any of the available acquisition "
                           "modes of the logic " )
            return
        self._acquisition_mode = acquisition_mode

    @property
    def camera_gain(self):
        """ Get the gain.

        @return: (float) exposure gain

        """
        return self._camera_gain

    @camera_gain.setter
    def camera_gain(self, camera_gain):
        """ Set the gain.

        @param camera_gain: (float) new gain to set to the camera preamplifier which must correspond to the
        internal gain list given by the constraints dictionary.


        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        camera_gain = float(camera_gain)
        if not camera_gain in self.camera_constraints.internal_gains:
            self.log.error("Camera gain parameter do not match with any of the available camera internal gains ")
            return
        if camera_gain == self._camera_gain:
            return
        self.camera().set_gain(camera_gain)
        self._camera_gain = self.camera().get_gain()
        self.sigUpdateSettings.emit()

    @property
    def exposure_time(self):
        """ Get the exposure time in seconds

        @return: (float) exposure time

        """
        return self._exposure_time

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        """ Set the exposure time in seconds.

        @param exposure_time: (float) desired new exposure time

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        exposure_time = float(exposure_time)
        if not exposure_time >= 0:
            self.log.error("Exposure time parameter must be a positive number ")
            return
        if exposure_time == self._exposure_time:
            return
        self.camera().set_exposure_time(exposure_time)
        self._exposure_time = self.camera().get_exposure_time()

    @property
    def scan_delay(self):
        """Getter method returning the scan delay between consecutive scan during multiple acquisition mode.

        @return: (float) scan delay

        """
        return self._scan_delay

    @scan_delay.setter
    def scan_delay(self, scan_delay):
        """Setter method setting the scan delay between consecutive scan during multiple acquisition mode.

        @param scan_delay: (float) scan delay

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        scan_delay = float(scan_delay)
        if not scan_delay >= 0:
            self.log.error("Scan delay parameter must be a positive number ")
            return
        if scan_delay == self._scan_delay:
            return
        self._scan_delay = scan_delay

    @property
    def scan_wavelength_step(self):
        """Getter method returning the scan wavelength step between consecutive scan during multiple acquisition mode.

        @return: (float) scan wavelength step in meter

        """
        return self._scan_wavelength_step

    @scan_wavelength_step.setter
    def scan_wavelength_step(self, scan_wavelength_step):
        """Setter method setting the scan wavelength step between consecutive scan during multiple acquisition mode.

        @param scan_delay: (float) scan wavelength step in meter

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        scan_wavelength_step = float(scan_wavelength_step)
        if not scan_wavelength_step >= 0:
            self.log.error("Scan delay parameter must be a positive number ")
            return
        wavelength_max = self.spectro_constraints.gratings[self.grating].wavelength_max
        if not scan_wavelength_step < wavelength_max:
            self.log.error('Scan wavelength step parameter is not correct : it must be in range {} to {} '
                           .format(0, wavelength_max))
            return
        if scan_wavelength_step == self._scan_wavelength_step:
            return
        self._scan_wavelength_step = scan_wavelength_step

    @property
    def number_of_scan(self):
        """Getter method returning the number of acquired scan during multiple acquisition mode.

        @return: (int) number of acquired scan

        """
        return self._number_of_scan

    @number_of_scan.setter
    def number_of_scan(self, number_scan):
        """Setter method setting the number of acquired scan during multiple acquisition mode.

        @param number_scan: (int) number of acquired scan

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        number_scan = int(number_scan)
        if not number_scan > 0:
            self.log.error("Number of acquired scan parameter must be positive ")
            return
        if number_scan == self._number_of_scan:
            return
        self._number_of_scan = number_scan

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################

    @property
    def trigger_mode(self):
        """Getter method returning the current trigger mode used by the camera.

        @return: (str) trigger mode (must be compared to the list)

        """
        return self._trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode):
        """Setter method setting the trigger mode used by the camera.

        @param trigger_mode: (str) trigger mode

        """
        if self.module_state() == 'locked':
            self.log.error("Acquisition process is currently running : you can't change this parameter"
                           " until the acquisition is completely stopped ")
            return
        if isinstance(trigger_mode, TriggerMode):
            trigger_mode = trigger_mode.name
        if trigger_mode not in self.camera_constraints.trigger_modes:
            self.log.error("Trigger mode parameter do not match with any of available trigger "
                           "modes of the camera ")
            return
        if trigger_mode == self._trigger_mode:
            return
        self.camera().set_trigger_mode(trigger_mode)
        self._trigger_mode = self.camera().get_trigger_mode()
        self.sigUpdateSettings.emit()

    ##############################################################################
    #                           Shutter mode functions (optional)
    ##############################################################################

    @property
    def shutter_state(self):
        """Getter method returning the shutter state.

        @return: (str) shutter state

        """
        if not self.camera_constraints.has_shutter:
            self.log.error("No shutter is available in your hardware ")
            return
        return self._shutter_state

    @shutter_state.setter
    def shutter_state(self, shutter_state):
        """Setter method setting the shutter state.

        @param shutter_state: (str) shutter state

        """
        if not self.camera_constraints.has_shutter:
            self.log.error("No shutter is available in your hardware ")
            return
        if self._shutter_state == shutter_state:
            return
        if isinstance(shutter_state, str) and shutter_state in ShutterState.__members__:
            shutter_state = ShutterState[shutter_state]
        if not isinstance(shutter_state, ShutterState):
            self.log.error("Shutter state parameter do not match with shutter states of the camera ")
            return
        self.camera().set_shutter_state(shutter_state)
        self._shutter_state = self.camera().get_shutter_state()
        self.sigUpdateSettings.emit()

    ##############################################################################
    #                           Temperature functions
    ##############################################################################

    @property
    def cooler_status(self):
        """Getter method returning the cooler status if ON or OFF.

        @return (bool): True if the cooler is on

        """
        if not self.camera_constraints.has_cooler:
            self.log.info("No cooler is available in your hardware ")
            return
        return self.camera().get_cooler_on()

    @cooler_status.setter
    def cooler_status(self, cooler_status):
        """ Setter method returning the cooler status if ON or OFF.

        @param (bool) value: True to turn it on, False to turn it off

        """
        if not self.camera_constraints.has_cooler:
            self.log.error("No cooler is available in your hardware ")
            return
        self._cooler_status = bool(cooler_status)
        self.camera().set_cooler_on(cooler_status)
        self.sigUpdateSettings.emit()

    @property
    def camera_temperature(self):
        """ Getter method returning the temperature of the camera.

        @return (float): temperature (in Kelvin)

        """
        if not self.camera_constraints.has_cooler:
            self.log.info("No cooler is available in your hardware ")
            return
        return self.camera().get_temperature()

    @property
    def temperature_setpoint(self):
        """ Getter method for the temperature setpoint of the camera.

        @return (float): Current setpoint in Kelvin

        """
        if not self.camera_constraints.has_cooler:
            self.log.info("No cooler is available in your hardware ")
            return
        return self._temperature_setpoint

    @temperature_setpoint.setter
    def temperature_setpoint(self, value):
        """ Setter method for the the temperature setpoint of the camera.

        @param (float) value: New setpoint in Kelvin

        """
        if not self.camera_constraints.has_cooler:
            self.log.error("No cooler is available in your hardware ")
            return
        if value <= 0:
            self.log.error("Temperature setpoint can't be negative or 0 ")
            return
        self.camera().set_temperature_setpoint(value)
        self._temperature_setpoint = self.camera().get_temperature_setpoint()
        self.sigUpdateSettings.emit()