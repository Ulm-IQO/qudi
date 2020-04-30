# -*- coding: utf-8 -*-

"""
This hardware module implement the camera spectrometer interface to use an Andor Camera.
It use a dll to interface with instruments via USB (only available physical interface)
This module does aim at replacing Solis.

---

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

from enum import Enum
from ctypes import *
import numpy as np
import ctypes as ct

from core.module import Base
from core.configoption import ConfigOption

from interface.camera_complete_interface import CameraInterface
from core.util.modules import get_main_dir
import os

# Bellow are the classes used by Andor dll. They are not par of Qudi interfaces


class ReadMode(Enum):
    """ Class defining the possible read mode supported by Andor dll

     Only FVB, RANDOM_TRACK and IMAGE are used by this module.
     """
    FVB = 0
    MULTI_TRACK = 1
    RANDOM_TRACK = 2
    SINGLE_TRACK = 3
    IMAGE = 4


class AcquisitionMode(Enum):
    """ Class defining the possible acquisition mode supported by Andor dll

     Only SINGLE_SCAN is used by this module.
     """
    SINGLE_SCAN = 1
    ACCUMULATE = 2
    KINETICS = 3
    FAST_KINETICS = 4
    RUN_TILL_ABORT = 5


class TriggerMode(Enum):
    """ Class defining the possible trigger mode supported by Andor dll """
    INTERNAL = 0
    EXTERNAL = 1
    EXTERNAL_START = 6
    EXTERNAL_EXPOSURE = 7
    SOFTWARE_TRIGGER = 10
    EXTERNAL_CHARGE_SHIFTING = 12


class ShutterMode(Enum):
    """ Class defining the possible shutter mode supported by Andor dll """
    AUTO = 0
    OPEN = 1
    CLOSE = 2


OK_CODE = 20002


ERROR_DICT = {
    20001: "DRV_ERROR_CODES",
    20002: "DRV_SUCCESS",
    20003: "DRV_VX_NOT_INSTALLED",
    20006: "DRV_ERROR_FILE_LOAD",
    20007: "DRV_ERROR_VXD_INIT",
    20010: "DRV_ERROR_PAGE_LOCK",
    20011: "DRV_ERROR_PAGE_UNLOCK",
    20013: "DRV_ERROR_ACK",
    20024: "DRV_NO_NEW_DATA",
    20026: "DRV_SPOOL_ERROR",
    20034: "DRV_TEMP_OFF",
    20035: "DRV_TEMP_NOT_STABILIZED",
    20036: "DRV_TEMP_STABILIZED",
    20037: "DRV_TEMP_NOT_REACHED",
    20038: "DRV_TEMP_OUT_RANGE",
    20039: "DRV_TEMP_NOT_SUPPORTED",
    20040: "DRV_TEMP_DRIFT",
    20050: "DRV_COF_NOT_LOADED",
    20053: "DRV_FLEX_ERROR",
    20066: "DRV_P1INVALID",
    20067: "DRV_P2INVALID",
    20068: "DRV_P3INVALID",
    20069: "DRV_P4INVALID",
    20070: "DRV_INI_ERROR",
    20071: "DRV_CO_ERROR",
    20072: "DRV_ACQUIRING",
    20073: "DRV_IDLE",
    20074: "DRV_TEMP_CYCLE",
    20075: "DRV_NOT_INITIALIZED",
    20076: "DRV_P5INVALID",
    20077: "DRV_P6INVALID",
    20083: "P7_INVALID",
    20089: "DRV_USB_ERROR",
    20091: "DRV_NOT_SUPPORTED",
    20095: "DRV_INVALID_TRIGGER_MODE",
    20099: "DRV_BINNING_ERROR",
    20990: "DRV_NO_CAMERA",
    20991: "DRV_NOT_SUPPORTED",
    20992: "DRV_NOT_AVAILABLE"
}


class Newton940(Base, CameraInterface):  # Todo : rename class for any Andor camera
    """ Hardware class for Andor Newton940 CCD spectroscopy cameras  """

    _dll_location = ConfigOption('dll_location', missing='error')
    _close_shutter_on_deactivate = ConfigOption('close_shutter_on_deactivate', False)

    _default_cooler_status = ConfigOption('default_cooler_status', True)
    _default_temperature = ConfigOption('default_temperature', 260)
    _default_acquisition_mode = ConfigOption('default_acquisition_mode', 'SINGLE_SCAN') #todo: remove
    _default_read_mode = ConfigOption('default_read_mode', 'IMAGE') #todo: remove
    _default_readout_speed = ConfigOption('default_readout_speed', 50000) #todo: remove
    _default_preamp_gain = ConfigOption('default_preamp_gain', 1) #todo: remove
    _default_trigger_mode = ConfigOption('default_trigger_mode', 'INTERNAL')
    _default_exposure = ConfigOption('default_exposure', 1.0) #todo: remove
    _default_shutter_status = ConfigOption('default_shutter_status', 'CLOSE') #todo: remove, but maybe close on deactivate ?
    _default_active_tracks = ConfigOption('default_active_tracks', [246, 266]) #todo: remove
    _default_binning = ConfigOption('default_binning', [1, 1]) #todo: remove
    _default_ROI = ConfigOption('default_ROI', [1, 2048, 1, 512]) #todo: remove
    _default_max_exposure_time = ConfigOption('default_max_exposure_time', 600) #todo: does this come from the dll and why forbid it ?

    _camera_name = 'Newton940'#todo: from config option or read from dll ?

    _cooler_status = _default_cooler_status
    _temperature = _default_temperature
    _max_cooling = -85 # todo
    _acquisition_mode = _default_acquisition_mode
    _read_mode = _default_read_mode
    _readout_speed = _default_readout_speed
    _preamp_gain = _default_preamp_gain
    _trigger_mode = _default_trigger_mode

    _exposure = _default_exposure
    _max_exposure_time = _default_max_exposure_time
    _shutter_status = _default_shutter_status
    _shutter_TTL = 1
    _shutter_closing_time = 100  # ms!
    _shutter_opening_time = 100  # ms!

    _gain = 0
    _width = 0
    _height = 0
    _supported_read_mode = ReadMode
    _live = False

    _scans = 1
    _acquiring = False

    _number_of_tracks = 1
    _binning = _default_binning
    _ROI = _default_ROI

    _hbin = 1
    _vbin = 1
    _hstart = 1
    _hend = 2
    _vstart = 1
    _vend = 2

    _constraints = {} # not todo: this is nice !
    _min_temperature = 189 #todo: why ?
    _max_temperature = 262 # todo: why ?

    ##############################################################################
    #                            Basic module activation/deactivation
    ##############################################################################
    # is working
    # secured OK - tested PV - SI OK

    def on_activate(self):
        """ Initialization performed during activation of the module.
        """
        try:
            self.dll = ct.cdll.LoadLibrary(self._dll_location)
        except OSError:
            self.log.error('Error during dll loading of the Andor camera, check the dll path.')

        status_code = self.dll.Initialize()
        if status_code != OK_CODE:
            self.log.error('Problem during camera (Andor/Newton) initialization')
            return

        self._constraints = self.get_constraints()
        self._height, self._width = self.get_image_size()

        self.set_cooler_status(self._cooler_status)
        self.set_temperature(self._temperature)

        self.set_acquisition_mode(self._acquisition_mode) #todo: done by logic
        self.set_read_mode(self._read_mode) #todo: done by logic
        self.set_readout_speed(self._readout_speed) #todo: done by logic
        self.set_gain(self._preamp_gain) #todo: done by logic
        self.set_trigger_mode(self._trigger_mode)

        self.set_exposure_time(self._exposure) #todo: done by logic

        self.set_shutter_status(self._shutter_status)

        self._active_tracks = np.array(self._default_active_tracks)
        self._hbin = self._binning[0]
        self._vbin = self._binning[1]
        self._hstart = self._ROI[0]
        self._hend = self._ROI[1]
        self._vstart = self._ROI[2]
        self._vend = self._ROI[3]

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        if not (self.get_ready_state()):
            self.stop_acquisition()
        if self._close_shutter_on_deactivate:
            self.set_shutter_status('CLOSE') #todo: closed ?
        try:
            self.dll.ShutDown()
        except:
            self.log.warning('Error while shutting down Andor camera via dll.')

    ##############################################################################
    #                                     Error management
    ##############################################################################
    def check(self, func_val):
        """ Check routine for the received error codes.
         :return: the dll function error code
        Tested : no
        """

        if not func_val == OK_CODE:
            self.log.error('Error in Newton with error_code {0}:'
                           '{1}'.format(func_val, ERROR_DICT[func_val]))
        return func_val

    ##############################################################################
    #                                     Basic functions
    ##############################################################################
    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return: (dict) constraint dict : {

            'name' : (str) give the camera manufacture name (ex : 'Newton940')

            'image_size' : (tuple) ((int) image_width, (int) image_length) give the camera image size in pixels units,

            'pixel_size' : (tuple) ((float) pixel_width, (float) pixel_length) give the pixels size in m,

            'read_modes' : (list) [(str) read_mode, ..] give the available read modes of the camera (ex : ['FVB']),

            'readout_speed' : (list)

            'internal_gains' : (list) [(float) gain, ..] give the available internal gain which can be set
            to the camera preamplifier,

            'trigger_modes' : (list) [(str) trigger_mode, ..] give the available trigger modes of the camera,

            'has_cooler' : (bool) give if the camera has temperature controller installed,

            (optional) : let this key empty if no shutter is installed !
            'shutter_modes' : (ndarray) [(str) shutter_mode, ..] give the shutter modes available if any
            shutter is installed.

        """
        #todo: there is many thing, a class would probably be preferable

        internal_gains = [1, 2, 4]  # todo : read from hardware
        readout_speeds = [50000, 1000000, 3000000]  # todo : read from hardware

        constraints = {
            'name': self.get_name(),
            'image_size': self.get_image_size(),
            'pixel_size': self.get_pixel_size(),
            'read_modes': ['FVB', 'RANDOM_TRACK', 'IMAGE'],
            'readout_speeds': readout_speeds,
            'trigger_modes': ['INTERNAL', 'EXTERNAL', 'EXTERNAL_START', 'EXTERNAL_EXPOSURE',
                                  'SOFTWARE_TRIGGER', 'EXTERNAL_CHARGE_SHIFTING'],
            'acquisition_modes': ['SINGLE_SCAN'],
            'internal_gains': internal_gains,
            'has_cooler': True,
            'shutter_modes': ['AUTO', 'OPEN', 'CLOSE'],
        }
        return constraints

    def start_acquisition(self):
        """ Starts the acquisition """
        self.check(self.dll.StartAcquisition())
        self.dll.WaitForAcquisition()  # todo: this is not synchronous

    def stop_acquisition(self):
        """ Aborts the acquisition """
        self.check(self.dll.AbortAcquisition())

    def get_acquired_data(self):
        """ Return the last acquired data.

        @return numpy array: image data in format [[row],[row]...]
        """
        if self._read_mode == 'FVB':
            height = 1
        if self._read_mode == 'RANDOM_TRACK':
            height = self._number_of_tracks
        if self._read_mode == 'IMAGE':
            height = self._height
        dim = int(self._width * height)
        image_array = np.zeros(dim)
        c_image_array = c_int * dim
        c_image = c_image_array()

        status_code = self.dll.GetAcquiredData(pointer(c_image), dim)

        if status_code != OK_CODE:
            self.log.warning('Could not retrieve an image. {0}'.format(ERROR_DICT[status_code]))
        else:
            for i in range(len(c_image)): #todo: there must be something better here
                image_array[i] = c_image[i]

        return np.reshape(image_array, (self._width, height))

    ##############################################################################
    #                           Read mode functions
    ##############################################################################
    def get_read_mode(self):
        """ Getter method returning the current read mode used by the camera.

        @return  (str): read mode
        """
        return self._read_mode

    def set_read_mode(self, read_mode):
        """ Setter method setting the read mode used by the camera.

        @param (str) read_mode: read mode among those defined in the self.get_constraint
        """

        if hasattr(ReadMode, read_mode) and (read_mode in self._constraints['read_modes']):
            n_mode = c_int(getattr(ReadMode, read_mode).value)
            self.check(self.dll.SetReadMode(n_mode))
        else:
            self.log.error('read_mode not supported')
            return

        self._read_mode = read_mode

        if read_mode == 'IMAGE':
            self.set_active_image(1, 1, 1, self._height, 1, self._width)

        elif read_mode == 'RANDOM_TRACK':
            self.set_active_tracks(self._active_tracks)

    def get_readout_speed(self):
        """  Get the current readout speed (in Hz)

        @return (float): the readout_speed (Horizontal shift) in Hz
        """
        return self._readout_speed

    def set_readout_speed(self, readout_speed):
        """ Set the readout speed (in Hz)

        @param (float) readout_speed: horizontal shift in Hz
        """
        if readout_speed in self._constraints['readout_speeds']:
            readout_speed_index = self._constraints['readout_speeds'].index(readout_speed)
            self.check(self.dll.SetHSSpeed(0, readout_speed_index))
            self._readout_speed = readout_speed
        else:
            self.log.error('Readout_speed value error, value {} is not in correct.'.format(readout_speed))

    def get_active_tracks(self):
        """ Getter method returning the read mode tracks parameters of the camera.

        @return (list):  active tracks positions [(start_1, end_1), (start_2, end_2), ... ]
        """
        return self._active_tracks

    def set_active_tracks(self, active_tracks):
        """ Setter method for the active tracks of the camera.

        @param (list) active_tracks: active tracks positions  as [(start_1, end_1), (start_2, end_2), ... ]
        """
        if self._read_mode != 'RANDOM_TRACK':
            self.log.error('Active tracks are defined outside of RANDOM_TRACK mode.')
            return
        number_of_tracks = int(len(active_tracks))
        active_tracks = [item for item_tuple in active_tracks for item in item_tuple] #todo: decompose this, do not use imbricated loops in one line loop
        self.dll.SetRandomTracks.argtypes = [ct.c_int32, ct.c_void_p]
        self.check(self.dll.SetRandomTracks(number_of_tracks, active_tracks.ctypes.data))
        self._active_tracks = active_tracks
        self._number_of_tracks = number_of_tracks

    def get_active_image(self):
        """ Getter method returning the read mode image parameters of the camera.

        @return: (np array) active image parameters [hbin, vbin, hstart, hend, vstart, vend]
        tested : yes
        SI check : yes
        """
        active_image_parameters = [self._vbin, self._hbin, self._vstart, self._vend, self._hstart, self._hend]
        return active_image_parameters

    def set_active_image(self, vbin, hbin, vstart, vend, hstart, hend):
        """ Setter method setting the read mode image parameters of the camera.

        @param hbin: (int) horizontal pixel binning
        @param vbin: (int) vertical pixel binning
        @param hstart: (int) image starting row
        @param hend: (int) image ending row
        @param vstart: (int) image starting column
        @param vend: (int) image ending column
        @return: nothing
        tested : yes
        SI check : yes
        """
        hbin, vbin, hstart, hend, vstart, vend = c_int(hbin), c_int(vbin), c_int(hstart), c_int(hend),\
            c_int(vstart), c_int(vend)

        status_code = self.check(self.dll.SetImage(hbin, vbin, hstart, hend, vstart, vend))
        if status_code == OK_CODE:
            self._hbin = hbin.value
            self._vbin = vbin.value
            self._hstart = hstart.value
            self._hend = hend.value
            self._vstart = vstart.value
            self._vend = vend.value
            self._width = int((self._hend - self._hstart + 1) / self._hbin)
            self._height = int((self._vend - self._vstart + 1) / self._vbin)
            self._ROI = (self._hstart, self._hend, self._vstart, self._vend)
            self._binning = (self._hbin, self._vbin)
        else:
            self.log.error('Call to set_active_image went wrong:{0}'.format(ERROR_DICT[status_code]))
        return

    ##############################################################################
    #                           Acquisition mode functions
    ##############################################################################

    def get_acquisition_mode(self):
        """ Getter method returning the current acquisition mode used by the camera.

        @return (str): acquisition mode
        """
        return self._acquisition_mode

    def set_acquisition_mode(self, acquisition_mode):
        """ Setter method setting the acquisition mode used by the camera.

        @param acquisition_mode: @str read mode (must be compared to a dict)
        """

        if hasattr(AcquisitionMode, acquisition_mode) \
                and (acquisition_mode in self._constraints['acquisition_modes']):
            n_mode = c_int(getattr(AcquisitionMode, acquisition_mode).value)
            self.check(self.dll.SetAcquisitionMode(n_mode))
        else:
            self.log.error('{} mode is not supported'.format(acquisition_mode))
            return
        self._acquisition_mode = acquisition_mode
        return

    def get_exposure_time(self):
        """ Get the exposure time in seconds

        @return (float) : exposure time in s
        """
        return self._get_acquisition_timings['exposure']

    def _get_acquisition_timings(self):
        """ Get the acquisitions timings from the dll

        @return (dict): dict containing keys 'exposure', 'accumulate', 'kinetic' and their values in seconds """
        exposure, accumulate, kinetic = c_float(), c_float(), c_float()
        self.check(self.dll.GetAcquisitionTimings(byref(exposure), byref(accumulate), byref(kinetic)))
        return {'exposure': exposure.value, 'accumulate': accumulate.value, 'kinetic': kinetic.value}

    def set_exposure_time(self, exposure_time):
        """ Set the exposure time in seconds

        @param (float) exposure_time: desired new exposure time
        """
        if exposure_time < 0:
            self.log.error('Exposure_time can not be negative.')
            return
        if exposure_time > self._max_exposure_time:
            self.log.error('Exposure time is above the high limit : {0} s'.format(self._max_exposure_time))
            return
        self.check(self.dll.SetExposureTime(c_float(exposure_time)))

    def get_gain(self):
        """ Get the gain

        @return (float): exposure gain
        """
        return self._preamp_gain #todo: read from hardware ?

    def set_gain(self, gain):
        """ Set the gain

        @param (float) gain: desired new gain
        """
        if gain not in self._constraints['internal_gains']:
            self.log.error('gain value {} is not available.'.format(gain))
            return
        gain_index = self._constraints['internal_gains'].index(gain)
        self.check(self.dll.SetPreAmpGain(gain_index))

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################
    def get_trigger_mode(self):
        """ Getter method returning the current trigger mode used by the camera.

        @return (str): current trigger mode
        """
        return self._trigger_mode #todo: read from hardware ?

    def set_trigger_mode(self, trigger_mode):
        """ Setter method for the trigger mode used by the camera.

        @param (str) trigger_mode: trigger mode (must be compared to a dict)
        """
        if hasattr(TriggerMode, trigger_mode) \
                and (trigger_mode in self._constraints['trigger_modes']):
            n_mode = c_int(getattr(TriggerMode, trigger_mode).value)
            self.check(self.dll.SetTriggerMode(n_mode))
            self._trigger_mode = trigger_mode
        else:
            self.log.warning('Trigger mode {} is not supported.'.format(trigger_mode))
            return
        self._trigger_mode = trigger_mode
        return

    ##############################################################################
    #                           Shutter mode functions
    ##############################################################################
    def get_shutter_status(self):
        """ Getter method returning if the shutter is open.

        @return (bool): @bool shutter open ? #todo: status
        tested : yes
        SI check : yes
        """
        return self._shutter_status #todo from hardware ?

    def set_shutter_status(self, shutter_status):
        """ Setter method for the shutter state.

        @param (str): shutter_status
        """

        if hasattr(ShutterMode, shutter_status) \
                and (shutter_status in self._constraints['shutter_modes']):
            mode = c_int(getattr(ShutterMode, shutter_status).value)
            self.check(self.dll.SetShutter(self._shutter_TTL, mode,
                                           self._shutter_closing_time, self._shutter_opening_time))
            self._shutter_status = shutter_status
        else:
            self.log.warning('HW/Newton940/set_shutter_status() : '
                             '{0} mode is not supported'.format(shutter_status))
            return
        self._shutter_status = shutter_status
        return

    ##############################################################################
    #                           Temperature functions
    ##############################################################################
    def get_cooler_status(self):
        """ Getter method returning the cooler status if ON or OFF.

        @return (bool): True if ON or False if OFF or 0 if error
        """
        return self._cooler_status #todo: from harware

    def set_cooler_status(self, cooler_status):
        """ Setter method for the cooler status.

        @param (bool) cooler_status: True if ON or False if OFF
        """
        if cooler_status:
            self.check(self.dll.CoolerON())
            self._cooler_status = True #todo: handled by camera
        else:
            self.check(self.dll.CoolerOFF())
            self._cooler_status = False #todo: handled by camera

    def get_temperature(self):
        """ Getter method returning the temperature of the camera.

        @return (float): temperature (in Kelvin)
        """
        temp = c_int32()
        self.dll.GetTemperature(byref(temp))
        return temp.value + 273.15

    def set_temperature(self, temperature):
        """ Setter method for the the temperature setpoint of the camera.

        @param (float) temperature: temperature (in Kelvin)
        """
        temperature = int(temperature) #todo: conversion to integer might mess things up, this has do ne checked nicely
        if self._min_temperature < temperature < self._max_temperature:
            temperature = int(temperature-273.15)
            self.check(self.dll.SetTemperature(temperature))
            self._temperature = temperature+273.15
        else:
            self.log.warning('Temperature {} Kelvin is not in the validity range.')

    #todo: setpoint getter ?

    ##############################################################################
    #               Internal functions, for constraints preparation
    ##############################################################################
    def get_name(self):
        """ Get a name for the camera

        @return (str): local camera name with serial number
        """
        serial = ct.c_int()
        self.check(self.dll.GetCameraSerialNumber(byref(serial)))
        name = self._camera_name + " serial number " + str(serial.value)
        return name

    def get_image_size(self):
        """ Returns the sensor size in pixels (width, height)

        @return tuple(int, int): number of pixel in width and height
        """
        nx_px = ct.c_int()
        ny_px = ct.c_int()
        self.check(self.dll.GetDetector(byref(nx_px), byref(ny_px)))
        return ny_px.value, nx_px.value

    def get_pixel_size(self):
        """ Get the physical pixel size (width, height) in meter

        @return tuple(float, float): physical pixel size in meter
        """
        x_px = ct.c_float()
        y_px = ct.c_float()
        self.check(self.dll.GetPixelSize(byref(x_px), byref(y_px)))
        return y_px.value * 1e-6, x_px.value * 1e-6

    def get_ready_state(self):
        """ Get the state of the camera to know if the acquisition is finished or not yet.

        @return (bool): True if camera state is idle
        """
        code = ct.c_int()
        self.check(self.dll.GetStatus(byref(code)))
        return code.value == OK_CODE

    def _get_current_config(self):
        """ Internal helper method to get the camera parameters in a printable dict.

        @return (dict): dictionary with camera current configuration.
        """
        config = { #todo use getters for most of them
            'camera ID..................................': self.get_name(),
            'sensor size (pixels).......................': self.get_image_size(),
            'pixel size (m)............................': self.get_pixel_size(),
            'acquisition mode...........................': self._acquisition_mode,
            'read mode..................................': self._read_mode,
            'readout speed (Hz).........................': self._readout_speed,
            'gain (x)...................................': self._preamp_gain,
            'trigger_mode...............................': self._trigger_mode,
            'exposure_time..............................': self._exposure,
            'ROI geometry (readmode = IMAGE)............': self._ROI,
            'ROI binning (readmode = IMAGE).............': self._binning,
            'number of tracks (readmode = RANDOM TRACK).': self._number_of_tracks,
            'tracks definition (readmode = RANDOM TRACK)': self._active_tracks,
            'temperature (K)............................': self._temperature,
            'shutter_status.............................': self._shutter_status,
        }
        return config
