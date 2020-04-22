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

from datetime import date


class SpectrumLogic(GenericLogic):
    """This logic module gathers data from the spectrometer.
    """

    # declare connectors
    spectrometer = Connector(interface='SpectrometerInterface')
    camera = Connector(interface='CameraInterface')
    savelogic = Connector(interface='SaveLogic')

    # declare status variables (logic attribute) :
    _spectrum_data = StatusVar('spectrum_data', np.empty((2, 0)))
    _background_data = StatusVar('background_data', np.empty((2, 0)))
    _image_data = StatusVar('image_data', np.empty((2, 0)))

    # Allow to set a default save directory in the config file :
    _default_save_file_path = ConfigOption('default_save_file_path') #TODO: Qudi savelogic handle the saving, it's better to let it do it things
    _save_file_path = StatusVar('save_file_path', _default_save_file_path) # TODO: same

    # declare status variables (camera attribute) :
    _read_mode = StatusVar('read_mode', 'FVB')
    _active_tracks = StatusVar('active_tracks', [240, 240]) # TODO: some camera have only one pixel height, or not support anything else than FVB

    _acquistion_mode = StatusVar('acquistion_mode', 'MULTI_SCAN')
    _exposure_time = StatusVar('exposure_time', 1)
    _camera_gain = StatusVar('camera_gain', 1) # TODO: even if unlikely, some camera might not have 1 in its possible value
    _number_of_scan = StatusVar('number_of_scan', 1)
    _scan_delay = StatusVar('scan_delay', 1e-2)
    _number_accumulated_scan = StatusVar('number_accumulated_scan', 1)
    _accumulation_delay = StatusVar('accumulation_delay', 1e-3)

    _trigger_mode = StatusVar('trigger_mode', 'INTERNAL')

    ##############################################################################
    #                            Basic functions
    ##############################################################################

    def __init__(self, **kwargs):
        """ Create SpectrumLogic object with connectors and status variables loaded.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)
        self.threadlock = Mutex() # TODO: This line on its own does nothing

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.spectrometer_device = self.spectrometer() #TODO: New modules prefer the syntax self.spectrometer() directly in the code rather than storing a second reference in a variable
        self.camera_device = self.camera()
        self._save_logic = self.savelogic()

        # hardware constraints :
        #TODO: You don't need to copy every entry to the module attributes, you can just use self.constraints['auto_slit_installed']
        # You can merge the two dictionaries or keep them separate
        spectro_constraints = self.spectrometer_device.get_constraints()
        self._number_of_gratings = spectro_constraints['number_of_gratings']
        self._wavelength_limits = spectro_constraints['wavelength_limits']
        self._auto_slit_installed = spectro_constraints['auto_slit_installed']
        self._flipper_mirror_installed = spectro_constraints['flipper_mirror_installed']

        camera_constraints = self.camera_device.get_constraints()
        self._read_mode_list = camera_constraints['read_mode_list']
        self._acquisition_mode_list = camera_constraints['acquisition_mode_list']
        self._trigger_mode_list = camera_constraints['trigger_mode_list']
        self._shutter_mode_list = camera_constraints['shutter_mode_list']
        self._image_size = camera_constraints['image_size']
        self._pixel_size = camera_constraints['pixel_size']

        # Spectrometer calibration using camera contraints parameters:
        self.spectrometer_device.set_calibration(self._image_size[1], self._pixel_size[1], self._image_size[0]/2) #TODO

        # declare spectrometer attributes :
        # grating :
        # TODO: Here you can initialize the hidden variable with :
        # self._attribute = self.spectrometer().get_attribute()
        # and then in the logic getter just return : self._attribute
        # Here is way it is initialize works but it quite unusual
        self._grating = self.grating
        # self._grating = self.spectrometer().get_grating() #todo and then in the grating property return self._grating directly
        self._grating_offset = self.grating_offset

        #wavelenght :
        self._center_wavelength = self.center_wavelength
        self._wavelength_range = self.wavelength_range

        self._input_port = self.input_port
        self._output_port = self.output_port
        self._input_slit_width = self.input_slit_width
        self._output_slit_width = self.output_slit_width

        # declare camera attributes :
        self._active_image = self._image_size #TODO This line surprise me from the variable name

        self._shutter_mode = self.shutter_mode
        self._cooler_status = self.cooler_status
        self._camera_temperature = self.camera_temperature

        # QTimer for asynchronous execution :
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.acquire_data)
        self._counter = 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated': #TODO: if the module is not idle, this function needs to stop the acquisition, it can not disobey !
            pass

    ##############################################################################
    #                            Save functions
    ##############################################################################

    def save_data(self, data_type = 'spectrum', file_name = None, save_path = None):
        """Method used to save the data using the savelogic module

        @param data_type: (str) must be 'image', 'spectrum' or 'background'
        @param file_name: (str) name of the saved file
        @param save_path: (str) relative path where the file should be saved
        @return: nothing
        """
        data = OrderedDict()
        today = date.today()
        if data_type == 'image':
            data = self._image_data[:, :] # TODO: tab[:, :] is equivalent to just tab
        if data_type == 'spectrum':
            data['Wavelength (m)'] = self._spectrum_data[0, :] #TODO: It's better to use simple variable-like name for this. This will be clear the day the data are treated !
            data['PL intensity (u.a)'] = self._spectrum_data[1, :] #TODO: just "counts" would be more appropriate, it's not (u.a.)
        elif data_type == 'background':
            data['Wavelength (m)'] = self._background_data[0, :]
            data['PL intensity (u.a)'] = self._background_data[1, :]
        else:
            self.log.debug('Data type parameter is not defined : it can only be \'spectrum\',' #TODO: this should be an error
                           ' \'background\' or \'image\'')
        if file_name is not None:
            file_label = file_name
        else:
            file_label = '{}_'.format(data_type) + today.strftime("%d%m%Y") #TODO: Savelogic already does timestamping
        if save_path is not None:
            self._save_file_path = save_path
        self._save_logic.save_data(data,
                                   filepath=self._save_file_path,
                                   filelabel=file_label)
        self.log.info('{} data saved in {}'.format(data_type.capitalize(), self._save_file_path))

    ##############################################################################
    #                            Acquisition functions
    ##############################################################################

    def start_spectrum_acquisition(self): #TODO: In the code this function also starts image
        """ Start acquisition by lauching the timer signal calling the 'acquire_data' function.
        """
        self._counter = 0
        self.module_state.lock() #TODO: this method should check if the module is already soemthing
        self._timer.start(1000 * self._scan_delay) #The argument of QTimer.start() is in ms #TODO: Why is the acquisition not started right away ? What exactly is _scan_delay ?

    def acquire_data(self):
        """ Method acquiring data by using the camera hardware methode 'start_acquistion'. This method is connected
        to a timer signal : after timer start this slot is called with a period of a time delay. After a certain
        number of call this method can stop the timer if not in 'LIVE' acquisition.
        """
        self.shutter_mode('OPEN') #TODO: Some hardware do not have a shutter
        self.camera_device.start_acquisition()
        self.shutter_mode('CLOSE') # TODO: start_acquisition only starts it, this line is executed while it is still ongoing
        self._counter += 1
        if self._read_mode == 'IMAGE':
            self._image_data = np.concatenate(self._image_data, self.acquired_data) #TODO: I don't understand what this tries to do
            name = 'Image'
        else:
            self._spectrum_data = np.concatenate(self._spectrum_data, self.acquired_data)
            name = 'Spectrum'
        if (self._number_of_scan - 1 < self._counter) and self._acquisition_mode != 'LIVE':
            self.module_state.unlock()
            self._timer.timeout.stop()
            self.log.info("{} acquisition succeed ! Number of acquired scan : {} "
                          "/ Delay between each scan : {}".format(name, self._number_of_scan, self._scan_delay))

    def acquire_background(self):
        """Method acquiring a background by closing the shutter and using the 'start_acquisition' method.
        """
        self.module_state.lock()
        self.shutter_mode('CLOSE')
        self.camera_device.start_acquisition()
        self._background_data = self.acquired_data
        self.module_state.unlock()
        self.log.info("Background acquired ")

    def stop_acquisition(self):
        """Method calling the stop acquisition method from the camera hardware module and changing the
        logic module state to 'unlocked'.
        """
        self.camera_device.stop_acquisition()
        self.module_state.unlock()
        self._timer.timeout.stop()
        self.log.info("Acquisition stopped : module state is 'idle' ")

    @property
    def spectrum_data(self):
        """Getter method returning the spectrum data.
        """
        return self._spectrum_data

    @property
    def background_data(self):
        """Getter method returning the background data.
        """
        return self._background_data

    @property
    def image_data(self):
        """Getter method returning the image data.
        """
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
    def grating(self): #TODO: From the name, it's unclear if it's the grating id or an object describing the grating that is returned
        """Getter method returning the grating number used by the spectrometer.

        @return: (int) active grating number
        """
        self._grating = self.spectrometer_device.get_grating()
        return self._grating


    @grating.setter
    def grating(self, grating_number):
        """Setter method setting the grating number to use by the spectrometer.

        @param grating_number: (int) gating number to set active
        @return: nothing
        """
        if not isinstance(grating_number, int):
            self.log.debug('Grating parameter is not correct : it must be an integer ')
            # TODO: a break is to end a loop in the middle of it, python will raise an error on this line
            # If you want to stop the function use return
            break
        if not 0 < grating_number < self._number_of_gratings:
            self.log.debug('Grating parameter is not correct : it must be in range 0 to {} '
                           .format(self._number_of_gratings - 1))
            break
        if not grating_number != self._grating: #TODO: This will only generate a lot of lines in the log file, it's common for the GUI to update an attribute to its current value
            #TODO: And if the value has not changed, they we should not invoke the hardware setter
            self.log.info('Grating parameter has not been changed') #
            break
        self.spectrometer_device.set_grating(grating_number)
        self._grating = grating_number
        self.log.info('Spectrometer grating has been changed correctly ')

    @property
    def grating_offset(self):
        """Getter method returning the grating offset of the grating selected by the grating_number parameter.

        @return: (int) the corresponding grating offset
        """
        self._grating_offset = self.spectrometer_device.get_grating_offset(self._grating) #TODO: I though we decided this to be handled in logic only
        return self._grating_offset

    @grating_offset.setter
    def grating_offset(self, grating_offset):
        """Setter method setting the grating offset of the grating selected by the grating_number parameter.

        @param grating_number: (int) grating number which correspond the offset
        @param grating_offset: (int) grating offset
        @return: nothing
        """
        if not isinstance(grating_offset, int):
            self.log.debug('Offset parameter is not correct : it must be an integer ')
            break
        offset_min = -self._number_of_gratings//2 - self._number_of_gratings % 2 #TODO: I don't understand what is the idea here
        offset_max = self._number_of_gratings//2
        if not offset_min < grating_offset < offset_max:
            self.log.debug('Offset parameter is not correct : it must be in range {} to {} '
                           .format(offset_min, offset_max))
            break
        if not grating_offset != self._grating_offset:
            self.log.info('Offset parameter has not been changed')
            break
        self._grating_offset = grating_offset
        self.spectrometer_device.set_grating_offset(grating_offset)
        self.log.info('Spectrometer grating offset has been changed correctly ')

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################

    @property
    def center_wavelength(self):
        """Getter method returning the center wavelength of the measured spectral range.

        @return: (float) the spectrum center wavelength
        """
        self._center_wavelength = self.spectrometer_device.get_wavelength()
        return self._center_wavelength

    @center_wavelength.setter
    def center_wavelength(self, wavelength):
        """Setter method setting the center wavelength of the measured spectral range.

        @param wavelength: (float) center wavelength
        @return: nothing
        """
        if not isinstance(wavelength, float): #TODO: This test is not essential and can generate problem in can the parameter is a int
            # If you want to be sure the wavelength is a float, you can do : wavelength = float(wavelength)
            # This way python tries to cast the type and raise an error if it's not possible
            # This is true for a lot of type testing in this module
            self.log.debug('Wavelength parameter is not correct : it must be a float ')
            break
        wavelength_min = self._wavelength_limits[self._grating, 0]
        wavelength_max = self._wavelength_limits[self._grating, 1] # TODO: You can write :
        #wavelength_min, wavelength_max = self._wavelength_limits[self._grating] # python will try to unpack automatically
        if not wavelength_min < wavelength < wavelength_max:
            self.log.debug('Wavelength parameter is not correct : it must be in range {} to {} '
                           .format(wavelength_min, wavelength_max))
            break
        if not wavelength != self._center_wavelength:
            self.log.info('Wavelength parameter has not been changed')
            break
        self._center_wavelength = wavelength
        self.spectrometer_device.set_wavelength(wavelength)
        self.log.info('Spectrometer wavelength has been changed correctly ')

    @property
    def wavelength_range(self): #TODO: The name of the property is confusing
        """Getter method returning the wavelength array of the full measured spectral range.
        (used for plotting spectrum with the spectral range)

        @return: (ndarray) measured wavelength array
        """
        self._wavelength_range = self.spectrometer_device.get_calibration() #TODO
        return self._wavelength_range

    ##############################################################################
    #                      Calibration functions
    ##############################################################################

    def set_calibration(self, number_of_pixels, pixel_width, tracks_offset): # TODO: This function will be erased in the future
        """Setter method returning the detector offset used by the spectrometer DLLs calibration function.
        (the value returned by this function must be the real detector offset value of the camera)

        @param number_of_pixels: (int) number of pixels
        @param pixel_width: (float) pixel width
        @param tracks_offset: (int) tracks offset
        @return: nothing
        """
        if not isinstance(number_of_pixels, int):
            self.log.debug('Number_of_pixels parameter is not correct : it must be a int ')
            break
        if not isinstance(pixel_width, float):
            self.log.debug('Pixel_width parameter is not correct : it must be a float ')
            break
        if not isinstance(tracks_offset, int):
            self.log.debug('Tracks_offset parameter is not correct : it must be a int ')
            break
        if number_of_pixels < 0:
            self.log.debug('Number_of_pixels parameter must be positive ')
            break
        if pixel_width < 0:
            self.log.debug('Pixel_width parameter must be positive ')
            break
        offset_min = -self._image_size[0]//2 - 1
        offset_max = self._image_size[0]//2
        if not offset_min - 1 < tracks_offset < offset_max + 1:
            self.log.debug('Tracks_offset parameter is not correct : it must be in range {} to {} '
                           .format(offset_min, offset_max))
            break
        self.spectrometer_device.set_calibration(number_of_pixels, pixel_width, tracks_offset)
        self.log.info('Calibration parameters have been set correctly ')

    ##############################################################################
    #                      Ports and Slits functions
    ##############################################################################

    @property
    def input_port(self):
        """Getter method returning the active current input port of the spectrometer.

        @return: (int) active input port (0 front and 1 side)
        """
        self._input_port = self.spectrometer_device.get_input_port()
        return self._input_port

    @input_port.setter
    def input_port(self, input_port):
        """Setter method setting the active current input port of the spectrometer.

        @param input_port: (int) active input port (0 front and 1 side)
        @return: nothing
        """
         #TODO: All this test could be replaced by :
        # if input_port not in self.constraints.input_ports:
        if input_port==1 and not self._flipper_mirror_installed[0]:
            self.log.debug('Your hardware do not have any flipper mirror present at the input port ')
            break
        if not isinstance(input_port, int):
            self.log.debug('Input port parameter is not correct : it must be a int ')
            break
        if not -1 < input_port < 2:
            self.log.debug('Input port parameter is not correct : it must be 0 or 1 ')
            break
        if not input_port != self._input_port:
            self.log.info('Input port parameter has not been changed')
            break
        self._input_port = input_port
        self.spectrometer_device.set_input_port(input_port)
        self.log.info('Input port has been changed correctly ')

    @property
    def output_port(self):
        """Getter method returning the active current output port of the spectrometer.

        @return: (int) active output port (0 front and 1 side)
        """
        self._output_port = self.spectrometer_device.get_output_port()
        return self._output_port

    @output_port.setter
    def output_port(self, output_port):
        """
        Setter method setting the active current output port of the spectrometer.

        @param output_port: (int) active output port (0 front and 1 side)
        @return: nothing
        """
        if output_port==1 and not self._flipper_mirror_installed[1]:
            self.log.debug('Your hardware do not have any flipper mirror present at the output port ')
            break
        if not isinstance(output_port, int):
            self.log.debug('Output port parameter is not correct : it must be a int ')
            break
        if not -1 < output_port < 2:
            self.log.debug('Output port parameter is not correct : it must be 0 or 1 ')
            break
        if not output_port != self._output_port:
            self.log.info('Output port parameter has not been changed')
            break
        self._output_port = output_port
        self.spectrometer_device.set_output_port(output_port)
        self.log.info('Output port has been changed correctly ')

    @property
    def input_slit_width(self):
        """Getter method returning the active input port slit width of the spectrometer.

        @return: (float) input port slit width
        """
        self._input_slit_width = self.spectrometer_device.get_auto_slit_width('input', self._input_port)
        return self._input_slit_width

    @input_slit_width.setter
    def input_slit_width(self, slit_width):
        """Setter method setting the active input port slit width of the spectrometer.

        @param slit_width: (float) input port slit width
        @return: nothing
        """
        if not self._auto_slit_installed[0, self._input_port]:
            self.log.debug('Input auto slit is not installed at this input port ')
            break
        if not isinstance(slit_width, float):
            self.log.debug('Input slit width parameter is not correct : it must be a float ')
            break
        if slit_width == self._input_slit_width:
            self.log.info("Input slit width parameter has not be changed ")
            break
        self._input_slit_width = slit_width
        self.spectrometer_device.set_auto_slit_width('input', self._input_port, slit_width)
        self.log.info('Output slit width has been changed correctly ')

    @property
    def output_slit_width(self):
        """Getter method returning the active output port slit width of the spectrometer.

        @return: (float) output port slit width
        """
        self._output_slit_width = self.spectrometer_device.get_auto_slit_width('output', self._output_port)
        return self._output_slit_width

    @output_slit_width.setter
    def output_slit_width(self, slit_width):
        """Setter method setting the active output port slit width of the spectrometer.

        @param slit_width: (float) output port slit width
        @return: nothing
        """
        if not self._auto_slit_installed[1, self._output_port]:
            self.log.debug('Output auto slit is not installed at this output port ')
            break
        if not isinstance(slit_width, float):
            self.log.debug('Output slit width parameter is not correct : it must be a float ')
            break
        if slit_width == self._output_slit_width:
            self.log.info("Output slit width parameter has not be changed ")
            break
        self._output_slit_width = slit_width
        self.spectrometer_device.set_auto_slit_width('output', self._output_port, slit_width)
        self.log.info('Output slit width has been changed correctly ')


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
        """ Return an array of last acquired image. #TODO: This function also works for spectra

        @return: (ndarray) image data in format [[row],[row]...]
        Each pixel might be a float, integer or sub pixels
        """
        return self.camera_device.get_acquired_data()

    ##############################################################################
    #                           Read mode functions
    ##############################################################################

    @property
    def read_mode(self):
        """Getter method returning the current read mode used by the camera.

        @return: (str) read mode (must be compared to the list)
        """
        self._read_mode = self.camera_device.get_read_mode()
        return self._read_mode


    @read_mode.setter
    def read_mode(self, read_mode):
        """Setter method setting the read mode used by the camera.

        @param read_mode: (str) read mode (must be compared to the list)
        @return: nothing
        """
        if not read_mode in self._read_mode_list:
            self.log.debug("Read mode parameter do not match with any of the available read "
                           "mode of the camera ")
            break
        if not isinstance(read_mode, str): #TODO: This test will never fail after the previous one
            self.log.debug("Read mode parameter must be a string ")
            break
        if not read_mode == self._read_mode:
            self.log.info("Read mode parameter has not be changed ")
            break
        self.camera_device.set_read_mode(read_mode)

    @property
    def active_tracks(self):
        """Getter method returning the read mode tracks parameters of the camera.

        @return: (ndarray) active tracks positions [1st track start, 1st track end, ... ]
        """
        self._active_tracks = self.camera_device.get_active_tracks()
        return self._active_tracks

    @active_tracks.setter
    def active_tracks(self, active_tracks):
        """
        Setter method setting the read mode tracks parameters of the camera.

        @param active_tracks: (ndarray) active tracks positions [1st track start, 1st track end, ... ]
        @return: nothing
        """
        # TODO: this function will change when the tracks become of the format [(10, 20), (55, 57), ...]
        if not (np.all(active_tracks[::2]<self._image_size[0]) and np.all(active_tracks[1::2]<self._image_size[1])):
            self.log.debug("Active tracks positions are out of range : some position are out of the pixel matrix ")
            break
        if not isinstance(active_tracks.dtype, np.dtype): #TODO: the input [(10, 20)] should be ok even without being a numpy array
            self.log.debug("Active tracks parameter is not correct : must be an numpy array ")
            break
        if not np.size(active_tracks)%2 == 0:
            active_tracks = np.concatenate(active_tracks, self._image_size[0]-1)
        if self._active_tracks == active_tracks:
            self.log.debug("Active tracks parameter has not been changed ")
            break
        self.camera_device.set_active_tracks(active_tracks)
        self._active_tracks = active_tracks
        self.log.info("Active tracks parameter has been set properly ")

    @property
    def active_image(self):
        """Getter method returning the read mode image parameters of the camera.

        @return: (ndarray) active image parameters [hbin, vbin, hstart, hend, vstart, vend]
        """
        self._active_image = self.camera_device.get_active_image()
        return self._active_image

    @active_image.setter
    def active_image(self, hbin, vbin, hstart, hend, vstart, vend):
        """
        Setter method setting the read mode image parameters of the camera.

        @param hbin: (int) horizontal pixel binning
        @param vbin: (int) vertical pixel binning
        @param hstart: (int) image starting row
        @param hend: (int) image ending row
        @param vstart: (int) image starting column
        @param vend: (int) image ending column
        @return: nothing
        """
        if not (isinstance(hbin, int) or isinstance(vbin, int)):
            self.log.debug("Pixels binning parameters must be int ")
            break
        if not (isinstance(hstart, int) or isinstance(vstart, int)):
            self.log.debug("Image starting point coordinates (bottom left corner) must be int ")
            break
        if not (isinstance(hend, int) or isinstance(vend, int)):
            self.log.debug("Image ending point coordinates (top right corner) must be int ")
            break
        if not (0<hbin<self._image_size[0] and 0<vbin<self._image_size[1]):
            self.log.debug("Pixels binning parameters must be positive and less than the pixel matrix dimensions ")
            break
        if not (0<hstart<self._image_size[0] and 0<vstart<self._image_size[1]):
            self.log.debug("Image starting point coordinates (bottom left corner) must be positive "
                           "and less than the pixel matrix dimensions ")
            break
        if not (0<hend<self._image_size[0] and 0<vend<self._image_size[1]):
            self.log.debug("Image ending point coordinates (top right corner) must be positive "
                           "and less than the pixel matrix dimensions ")
            break
        self._active_image = np.array([hbin, vbin, hstart, hend, vstart, vend])
        self.camera_device.set_active_image(hbin, vbin, hstart, hend, vstart, vend)
        self.log.info("Image parameters has been set properly ")

    ##############################################################################
    #                           Acquisition mode functions
    ##############################################################################

    @property
    def acquisition_mode(self):
        """Getter method returning the current acquisition mode used by the camera.

        @return: (str) acquisition mode (must be compared to the list)
        """
        self._acquisition_mode = self.camera_device.get_acquisition_mode()
        return self._acquisition_mode

    @acquisition_mode.setter
    def acquisition_mode(self, acquisition_mode):
        """Setter method setting the acquisition mode used by the camera.

        @param acquisition_mode: (str) acquistion mode (must be compared to the list)
        @return: nothing
        """
        if not isinstance(acquisition_mode, str):
            self.log.debug("Acquisition mode parameter must be a string ")
            break
        if not acquisition_mode in self._acquisition_mode_list:
            self.log.debug("Acquisition mode parameter do not match with any of the available acquisition "
                           "mode of the camera ")
            break
        if not acquisition_mode == self._acquistion_mode:
            self.log.info("Acquisition mode parameter has not be changed ")
            break
        self._acquisition_mode = acquisition_mode
        self.camera_device.set_acquisition_mode(acquisition_mode)
        self.log.info('Acquisition mode has been set correctly ')

    @property
    def accumulation_delay(self):
        """Getter method returning the accumulation delay between consecutive scan during accumulate acquisition mode.

        @return: (float) accumulation delay
        """
        self._accumulation_delay = self.camera_device.get_accumulation_delay()
        return self._accumulation_delay

    @accumulation_delay.setter
    def accumulation_delay(self, accumulation_delay):
        """Setter method setting the accumulation delay between consecutive scan during an accumulate acquisition mode.

        @param accumulation_delay: (float) accumulation delay
        @return: nothing
        """
        if not isinstance(accumulation_delay, float):
            self.log.debug("Accumulation time parameter must be a float ")
            break
        if not accumulation_delay > 0 :
            self.log.debug("Accumulation time parameter must be a positive number ")
            break
        if not self._exposure_time < accumulation_delay < self._scan_delay:
            self.log.debug("Accumulation time parameter must be a value between"
                           "the current exposure time and scan delay values ")
            break
        if not accumulation_delay == self._accumulation_delay:
            self.log.info("Accumulation time parameter has not be changed ")
            break
        self._accumulation_delay = accumulation_delay
        self.camera_device.set_accumulation_delay(accumulation_delay)
        self.log.info('Accumulation delay has been set correctly ')

    @property
    def number_accumulated_scan(self):
        """Getter method returning the number of accumulated scan during accumulate acquisition mode.

        @return: (int) number of accumulated scan
        """
        self._number_accumulated_scan = self.camera_device.get_number_accumulated_scan()
        return self._number_accumulated_scan

    @number_accumulated_scan.setter
    def number_accumulated_scan(self, number_scan):
        """Setter method setting the number of accumulated scan during accumulate acquisition mode.

        @param number_scan: (int) number of accumulated scan
        @return: nothing
        """
        if not isinstance(number_scan, int):
            self.log.debug("Number of accumulated scan parameter must be an integer ")
            break
        if not number_scan > 0:
            self.log.debug("Number of accumulated scan parameter must be positive ")
            break
        if not number_scan == self._number_of_scan:
            self.log.info("Number of accumulated scan parameter has not be changed ")
            break
        self._number_accumulated_scan = number_scan
        self.camera_device.set_number_accumulated_scan(number_scan)
        self.log.info('Number of accumulated scan has been set correctly ')

    @property
    def exposure_time(self):
        """ Get the exposure time in seconds

        @return: (float) exposure time
        """
        self._exposure_time = self.camera_device.get_exposure_time()
        return self._exposure_time

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        """ Set the exposure time in seconds.

        @param exposure_time: (float) desired new exposure time

        @return: nothing
        """
        if not isinstance(exposure_time, float):
            self.log.debug("Exposure time parameter must be a float ")
            break
        if not exposure_time > 0:
            self.log.debug("Exposure time parameter must be a positive number ")
            break
        if not exposure_time < self._accumulation_delay: #TODO: This is confusing
            self.log.debug("Exposure time parameter must be a value lower"
                           "that the current accumulation time values ")
            break
        if not exposure_time == self._exposure_time:
            self.log.info("Exposure time parameter has not be changed ")
            break
        self._exposure_time = exposure_time
        self.camera_device.set_exposure_time(exposure_time)
        self.log.info('Exposure time has been set correctly ')

    @property
    def camera_gain(self):
        """ Get the gain.

        @return: (float) exposure gain
        """
        self._camera_gain = self.camera_device.get_camera_gain()
        return self._camera_gain

    @camera_gain.setter
    def camera_gain(self, camera_gain):
        """ Set the gain.

        @param camera_gain: (float) desired new gain

        @return: nothing
        """
        if not isinstance(camera_gain, float):
            self.log.debug("Camera gain parameter must be a float ")
            break
        if not camera_gain > 0:
            self.log.debug("Camera gain parameter must be a positive number ")
            break
        if not camera_gain == self._camera_gain:
            self.log.info("Camera gain parameter has not be changed ")
        self._camera_gain = camera_gain
        self.camera_device.set_camera_gain(camera_gain)
        self.log.info('Camera gain has been set correctly ')

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################

    @property
    def trigger_mode(self):
        """Getter method returning the current trigger mode used by the camera.

        @return: (str) trigger mode (must be compared to the list)
        """
        self._trigger_mode = self.camera_device.get_trigger_mode()
        return self._trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, trigger_mode):
        """Setter method setting the trigger mode used by the camera.

        @param trigger_mode: (str) trigger mode (must be compared to the list)
        @return: nothing
        """
        if not trigger_mode in self._trigger_mode_list:
            self.log.debug("Trigger mode parameter do not match with any of available trigger "
                           "mode of the camera ")
            break
        if not isinstance(trigger_mode, str):
            self.log.debug("Trigger mode parameter must be a string ")
            break
        if not trigger_mode == self._trigger_mode:
            self.log.info("Trigger mode parameter has not be changed ")
        self._trigger_mode = trigger_mode
        self.camera_device.set_trigger_mode(trigger_mode)
        self.log.info("Trigger mode has been set correctly ")

    ##############################################################################
    #                           Shutter mode functions
    ##############################################################################

    @property
    def shutter_mode(self):
        """Getter method returning the shutter mode.

        @return: (str) shutter mode (must be compared to the list)
        """
        self._shutter_mode = self.camera_device.get_shutter_is_open()
        return self._shutter_mode

    @shutter_mode.setter
    def shutter_mode(self, shutter_mode):
        """Setter method setting the shutter mode.

        @param shutter_mode: (str) shutter mode (must be compared to the list)
        @return: nothing
        """
        if not shutter_mode in self._shutter_mode_list:
            self.log.debug("Shutter mode parameter do not match with any of available shutter "
                           "mode of the camera ")
            break
        if not isinstance(shutter_mode, int):
            self.log.debug("Shutter open mode parameter must be an int ")
            break
        if not shutter_mode == self._shutter_mode:
            self.log.info("Shutter mode parameter has not be changed ")
            break
        self._shutter_mode = shutter_mode
        self.camera_device.set_shutter_is_open(shutter_mode)
        self.log.info("Shutter mod has been set correctly ")

    ##############################################################################
    #                           Temperature functions
    ##############################################################################

    @property
    def cooler_status(self):
        """Getter method returning the cooler status if ON or OFF.

        @return: (int) 1 if ON or 0 if OFF #TODO: why not use 'ON' or 'OFF'
        """
        self._cooler_status = self.camera_device.get_cooler_status()
        return self._cooler_status

    @cooler_status.setter
    def cooler_status(self, cooler_status):
        """Setter method returning the cooler status if ON or OFF.

        @param cooler_status: (bool) 1 if ON or 0 if OFF
        @return: nothing
        """
        if not isinstance(cooler_status, int):
            self.log.debug("Cooler status parameter must be int  ")
            break
        if not cooler_status == self._cooler_status:
            self.log.info("Cooler status parameter has not be changed ")
            break
        self._cooler_ON = cooler_status
        self.camera_device.set_cooler_ON(cooler_status)
        self.log.info("Cooler status has been changed correctly ")

    @property
    def camera_temperature(self):
        """Getter method returning the temperature of the camera.

        @return: (float) temperature
        """
        self._camera_temperature = self.camera_device.get_temperature()
        return self._camera_temperature

    @camera_temperature.setter
    def camera_temperature(self, camera_temperature): #TODO: this set the setpoint, not the temperature
        """Setter method returning the temperature of the camera.

        @param temperature: (float) temperature
        @return: nothing
        """
        if not isinstance(camera_temperature, float):
            self.log.debug("Camera temperature parameter must be a float ")
            break
        if not camera_temperature > 0:
            self.log.debug("Camera temperature parameter must be a positive number ")
            break
        if not self._camera_temperature == camera_temperature:
            self.log.info("Camera temperature parameter has not be changed ")
            break
        self._camera_temperature = camera_temperature
        self.camera_device.set_temperature(camera_temperature)
        self.log.info("Camera temperature has been changed correctly ")