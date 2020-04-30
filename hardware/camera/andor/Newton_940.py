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
import numpy as np
import ctypes as ct

from core.module import Base
from core.configoption import ConfigOption

from interface.camera_complete_interface import CameraInterface, ReadMode, Constraints, ImageAdvancedParameters


# Bellow are the classes used by Andor dll. They are not par of Qudi interfaces
class ReadModeDLL(Enum):
    """ Class defining the possible read mode supported by Andor DLL

    This read mode is different from the class of the interface, be careful!
    Only FVB, RANDOM_TRACK and IMAGE are used by this module.
     """
    FVB = 0
    MULTI_TRACK = 1
    RANDOM_TRACK = 2
    SINGLE_TRACK = 3
    IMAGE = 4


class AcquisitionMode(Enum):
    """ Class defining the possible acquisition mode supported by Andor DLL

     Only SINGLE_SCAN is used by this module.
     """
    SINGLE_SCAN = 1
    ACCUMULATE = 2
    KINETICS = 3
    FAST_KINETICS = 4
    RUN_TILL_ABORT = 5


class TriggerMode(Enum):
    """ Class defining the possible trigger mode supported by Andor DLL """
    INTERNAL = 0
    EXTERNAL = 1
    EXTERNAL_START = 6
    EXTERNAL_EXPOSURE = 7
    SOFTWARE_TRIGGER = 10
    EXTERNAL_CHARGE_SHIFTING = 12


class ShutterMode(Enum):
    """ Class defining the possible shutter mode supported by Andor DLL """
    AUTO = 0
    OPEN = 1
    CLOSE = 2


OK_CODE = 20002  # Status code associated with DRV_SUCCESS

# Error codes and strings defines by the DLL
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


class Main(Base, CameraInterface):
    """ Hardware class for Andor CCD spectroscopy cameras

    Tested with :
     - Newton 940
    """
    _dll_location = ConfigOption('dll_location', missing='error')
    _close_shutter_on_deactivate = ConfigOption('close_shutter_on_deactivate', False)
    #todo: open shutter_on_activate ?

    _start_cooler_on_activate = ConfigOption('start_cooler_on_activate', True)
    _default_temperature = ConfigOption('default_temperature', 260)
    _default_trigger_mode = ConfigOption('default_trigger_mode', 'INTERNAL')
    _max_exposure_time = ConfigOption('max_exposure_time', 600)  # todo: does this come from the dll and why forbid it ?

    _min_temperature = 189 #todo: why ?
    _max_temperature = 262 # todo: why ?

    # Declarations of attributes to make Pycharm happy
    def __init__(self):
        self._constraints = None
        self._dll = None
        self._active_tracks = None
        self._image_advanced_parameters = None

    ##############################################################################
    #                            Basic module activation/deactivation
    ##############################################################################
    def on_activate(self):
        """ Initialization performed during activation of the module. """
        try:
            self._dll = ct.cdll.LoadLibrary(self._dll_location)
        except OSError:
            self.log.error('Error during dll loading of the Andor camera, check the dll path.')

        status_code = self.dll.Initialize()
        if status_code != OK_CODE:
            self.log.error('Problem during camera initialization')
            return

        self._constraints = self._build_constraints()

        if self._constraints.has_cooler and self._start_cooler_on_activate:
            self.set_cooler_on(True)

        self.set_read_mode(ReadMode.FVB)
        self.set_trigger_mode(self._default_trigger_mode)
        self.set_temperature_setpoint(self._default_temperature)

        self.set_acquisition_mode(AcquisitionMode.SINGLE_SCAN)
        self._active_tracks = []
        self._image_advanced_parameters = None

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        if self.module_state() == 'locked':
            self.stop_acquisition()
        if self._close_shutter_on_deactivate:
            self.set_shutter_open_state(False)
        try:
            self.dll.ShutDown()
        except:
            self.log.warning('Error while shutting down Andor camera via dll.')

    ##############################################################################
    #                                     Error management
    ##############################################################################
    def _check(self, func_val):
        """ Check routine for the received error codes.

        @param (int) func_val: Status code returned by the DLL

        @return: The DLL function error code
        """
        if not func_val == OK_CODE:
            self.log.error('Error in Andor camera with error_code {}:{}'.format(func_val, ERROR_DICT[func_val]))
        return func_val

    ##############################################################################
    #                                     Constraints functions
    ##############################################################################
    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only onced by on_activate
         """
        constraints = Constraints()
        constraints.name = self._get_name()
        constraints.width, constraints.width = self._get_image_size()
        constraints.pixel_size_width, constraints.pixel_size_width = self._get_pixel_size()
        constraints.internal_gains = [1, 2, 4]  # # todo : from hardware
        constraints.readout_speeds = [50000, 1000000, 3000000]  # todo : read from hardware
        constraints.has_cooler = True # todo : from hardware ?
        constraints.trigger_modes = list(TriggerMode.__members__) # todo : from hardware if only some are available ?
        constraints.has_shutter = True  # todo : from hardware ?
        constraints.read_modes = [ReadMode.FVB]
        if constraints.height > 1:
            constraints.read_modes.extend([ReadMode.MULTIPLE_TRACKS, ReadMode.IMAGE, ReadMode.IMAGE_ADVANCED])
        return constraints

    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        return self._constraints

    ##############################################################################
    #                                     Basic functions
    ##############################################################################
    def start_acquisition(self):
        """ Starts the acquisition """
        self.check(self.dll.StartAcquisition())

    def _wait_for_acquisition(self):
        """ Internal function, can be used to wait till acquisition is finished """
        self.dll.WaitForAcquisition()

    def abort_acquisition(self):
        """ Aborts the acquisition """
        self.check(self.dll.AbortAcquisition())

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
        if self.get_read_mode() == ReadMode.FVB:
            height = 1
        elif self.get_read_mode() == ReadMode.MULTIPLE_TRACKS:
            height = len(self.get_active_tracks())
        elif self.get_read_mode() == ReadMode.IMAGE:
            height = self.get_constraints().height
        elif self.get_read_mode() == ReadMode.IMAGE_ADVANCED:
            pass #todo

        dimension = int(self.get_constraints().width * height)
        c_image_array = ct.c_int * dimension
        c_image = c_image_array()
        status_code = self.dll.GetAcquiredData(ct.pointer(c_image), dimension)
        if status_code != OK_CODE:
            self.log.error('Could not retrieve data from camera. {0}'.format(ERROR_DICT[status_code]))

        if self.get_read_mode() == ReadMode.FVB:
            return np.array(c_image)
        else:
            return np.reshape(np.array(c_image), (self._width, height)).transpose()

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

        if value not in self.get_constraints().read_modes:
            self.log.error('read_mode not supported')
            return

        conversion_dict = {ReadMode.FVB: ReadModeDLL.FVB,
                           ReadMode.MULTIPLE_TRACKS: ReadModeDLL.RANDOM_TRACK,
                           ReadMode.IMAGE: ReadModeDLL.IMAGE,
                           ReadMode.IMAGE_ADVANCED: ReadModeDLL.IMAGE}

        n_mode = conversion_dict[value].value
        self.check(self.dll.SetReadMode(n_mode))
        self._read_mode = value

        if value == ReadMode.IMAGE or value == ReadMode.IMAGE_ADVANCED:
            self._update_image()
        elif value == ReadMode.MULTIPLE_TRACKS():
            self._update_active_tracks()

    def get_readout_speed(self):
        """  Get the current readout speed (in Hz)

        @return (float): the readout_speed (Horizontal shift) in Hz
        """
        return self._readout_speed

    def set_readout_speed(self, value):
        """ Set the readout speed (in Hz)

        @param (float) value: horizontal readout speed in Hz
        """
        if value in self._constraints['readout_speeds']:
            readout_speed_index = self._constraints['readout_speeds'].index(value)
            self.check(self.dll.SetHSSpeed(0, readout_speed_index))
            self._readout_speed = value
        else:
            self.log.error('Readout_speed value error, value {} is not in correct.'.format(value))

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

    def _set_image(self, vbin, hbin, vstart, vend, hstart, hend):
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
        self.check(self.dll.GetAcquisitionTimings(ct.byref(exposure), ct.byref(accumulate), ct.byref(kinetic)))
        return {'exposure': exposure.value, 'accumulate': accumulate.value, 'kinetic': kinetic.value}

    def set_exposure_time(self, value):
        """ Set the exposure time in seconds

        @param (float) value: desired new exposure time
        """
        if value < 0:
            self.log.error('Exposure_time can not be negative.')
            return
        if value > self._max_exposure_time:
            self.log.error('Exposure time is above the high limit : {0} s'.format(self._max_exposure_time))
            return
        self.check(self.dll.SetExposureTime(c_float(value)))

    def get_gain(self):
        """ Get the gain

        @return (float): exposure gain
        """
        return self._preamp_gain #todo: read from hardware ?

    def set_gain(self, value):
        """ Set the gain

        @param (float) value: desired new gain
        """
        if value not in self._constraints['internal_gains']:
            self.log.error('gain value {} is not available.'.format(value))
            return
        gain_index = self._constraints['internal_gains'].index(value)
        self.check(self.dll.SetPreAmpGain(gain_index))

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################
    def get_trigger_mode(self):
        """ Getter method returning the current trigger mode used by the camera.

        @return (str): current trigger mode
        """
        return self._trigger_mode #todo: read from hardware ?

    def set_trigger_mode(self, value):
        """ Setter method for the trigger mode used by the camera.

        @param (str) value: trigger mode (must be compared to a dict)
        """
        if hasattr(TriggerMode, value) \
                and (value in self._constraints['trigger_modes']):
            n_mode = c_int(getattr(TriggerMode, value).value)
            self.check(self.dll.SetTriggerMode(n_mode))
            self._trigger_mode = value
        else:
            self.log.warning('Trigger mode {} is not supported.'.format(value))
            return
        self._trigger_mode = value
        return

    ##############################################################################
    #                           Shutter mode functions
    ##############################################################################
    def get_shutter_open_state(self):
        """ Getter method returning if the shutter is open.

        @return (bool): @bool shutter open ? #todo: status
        tested : yes
        SI check : yes
        """
        return self._shutter_status #todo from hardware

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
        self.dll.GetTemperature(ct.byref(temp))
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
        self.check(self.dll.GetCameraSerialNumber(ct.byref(serial)))
        name = self._camera_name + " serial number " + str(serial.value)
        return name

    def get_image_size(self):
        """ Returns the sensor size in pixels (width, height)

        @return tuple(int, int): number of pixel in width and height
        """
        nx_px = ct.c_int()
        ny_px = ct.c_int()
        self.check(self.dll.GetDetector(ct.byref(nx_px), ct.byref(ny_px)))
        return nx_px.value, ny_px.value

    def get_pixel_size(self):
        """ Get the physical pixel size (width, height) in meter

        @return tuple(float, float): physical pixel size in meter
        """
        x_px = ct.c_float()
        y_px = ct.c_float()
        self.check(self.dll.GetPixelSize(ct.byref(x_px), ct.byref(y_px)))
        return y_px.value * 1e-6, x_px.value * 1e-6

    def get_ready_state(self):
        """ Get the state of the camera to know if the acquisition is finished or not yet.

        @return (bool): True if camera state is idle
        """
        code = ct.c_int()
        self.check(self.dll.GetStatus(ct.byref(code)))
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
