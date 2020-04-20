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
import ctypes

from core.module import Base
from core.configoption import ConfigOption

from interface.camera_complete_interface import CameraInterface
from core.util.modules import get_main_dir
import os


class ReadMode(Enum):
    FVB = 0
    MULTI_TRACK = 1
    RANDOM_TRACK = 2
    SINGLE_TRACK = 3
    IMAGE = 4

class AcquisitionMode(Enum):
    SINGLE_SCAN = 1
    ACCUMULATE = 2
    KINETICS = 3
    FAST_KINETICS = 4
    RUN_TILL_ABORT = 5

class TriggerMode(Enum):
    INTERNAL = 0
    EXTERNAL = 1
    EXTERNAL_START = 6
    EXTERNAL_EXPOSURE = 7
    SOFTWARE_TRIGGER = 10
    EXTERNAL_CHARGE_SHIFTING = 12

class ShutterMode(Enum):
    AUTO = 0
    OPEN = 1
    CLOSE = 2

GAIN_DICT = {
    0: 1,       # index=0 - gain is 1x
    1: 2,       # index=1 - gain is 2x
    2: 4        # ...
}

READOUT_SPEED_DICT = {
    0: 50000,   # index=0 - Horizontal shift is 50kHz
    1: 1000000, # index=1 - Horizontal shift is 1MHz
    2: 3000000  # ...
}

ERROR_DICT = {
    20001: "DRV_ERROR_CODES",
    20002: "DRV_SUCCESS",
    20003: "DRV_VXNOTINSTALLED",
    20006: "DRV_ERROR_FILELOAD",
    20007: "DRV_ERROR_VXD_INIT",
    20010: "DRV_ERROR_PAGELOCK",
    20011: "DRV_ERROR_PAGE_UNLOCK",
    20013: "DRV_ERROR_ACK",
    20024: "DRV_NO_NEW_DATA",
    20026: "DRV_SPOOLERROR",
    20034: "DRV_TEMP_OFF",
    20035: "DRV_TEMP_NOT_STABILIZED",
    20036: "DRV_TEMP_STABILIZED",
    20037: "DRV_TEMP_NOT_REACHED",
    20038: "DRV_TEMP_OUT_RANGE",
    20039: "DRV_TEMP_NOT_SUPPORTED",
    20040: "DRV_TEMP_DRIFT",
    20050: "DRV_COF_NOTLOADED",
    20053: "DRV_FLEXERROR",
    20066: "DRV_P1INVALID",
    20067: "DRV_P2INVALID",
    20068: "DRV_P3INVALID",
    20069: "DRV_P4INVALID",
    20070: "DRV_INIERROR",
    20071: "DRV_COERROR",
    20072: "DRV_ACQUIRING",
    20073: "DRV_IDLE",
    20074: "DRV_TEMPCYCLE",
    20075: "DRV_NOT_INITIALIZED",
    20076: "DRV_P5INVALID",
    20077: "DRV_P6INVALID",
    20083: "P7_INVALID",
    20089: "DRV_USBERROR",
    20091: "DRV_NOT_SUPPORTED",
    20095: "DRV_INVALID_TRIGGER_MODE",
    20099: "DRV_BINNING_ERROR",
    20990: "DRV_NOCAMERA",
    20991: "DRV_NOT_SUPPORTED",
    20992: "DRV_NOT_AVAILABLE"
}


class Newton940(Base, CameraInterface):
    """
    Hardware class for Andor Newton940 CCD spectroscopy cameras
    """
    _modtype = 'camera'
    _modclass = 'hardware'

    _default_cooler_status = ConfigOption('default_cooler_status', True)
    _default_temperature = ConfigOption('default_temperature', -7)
    _default_acquisition_mode = ConfigOption('default_acquisition_mode', 'SINGLE_SCAN')
    _default_read_mode = ConfigOption('default_read_mode', 'IMAGE')
    _default_readout_speed = ConfigOption('default_readout_speed', 50000)
    _default_preamp_gain = ConfigOption('default_preamp_gain', 1)
    _default_trigger_mode = ConfigOption('default_trigger_mode', 'INTERNAL')
    _default_exposure = ConfigOption('default_exposure', 1.0)
    _default_shutter_status = ConfigOption('default_shutter_status', 'CLOSE')
    _default_active_tracks = ConfigOption('default_active_tracks', [246, 266])
    _dll_location = ConfigOption('dll_location', missing='error')

    _camera_name = 'Newton940'

    _cooler_status = _default_cooler_status
    _temperature = _default_temperature
    _max_cooling = -85
    _acquisition_mode = _default_acquisition_mode
    _read_mode = _default_read_mode
    _readout_speed = _default_readout_speed
    _preamp_gain = _default_preamp_gain
    _trigger_mode = _default_trigger_mode

    _exposure = _default_exposure
    _shutter_status = _default_shutter_status
    _shutter_TTL = 1
    _shutter_closing_time = 100 #ms!
    _shutter_opening_time = 100 #ms!

    _gain = 0
    _width = 0
    _height = 0
    _last_acquisition_mode = None  # useful if config changes during acq
    _supported_read_mode = ReadMode  #
    _live = False

    _scans = 1
    _acquiring = False

    _active_tracks = _default_active_tracks
    _number_of_tracks = 1

##############################################################################
#                            Basic module activation/deactivation
##############################################################################
# is working, but not secured and SI

    def on_activate(self):
        """ Initialization performed during activation of the module.

        """

        self.dll = ct.cdll.LoadLibrary(self._dll_location)
        self.errorcode = self._create_errorcode()

        code = self.dll.Initialize()

        if code != 20002:
            self.log.info('Problem during camera (Andor/Newton) initialization')
            self.on_deactivate()

        else:
            #nx_px, ny_px = c_int(), c_int()
            nx_px, ny_px = self.get_image_size()
            self._width, self._height = nx_px, ny_px

        self.set_cooler_status(self._cooler_status)
        self.set_temperature(self._temperature)

        self.set_acquisition_mode(self._acquisition_mode)
        self.set_read_mode(self._read_mode)
        self.set_readout_speed(self._readout_speed)
        self.set_gain(self._preamp_gain)
        self.set_trigger_mode(self._trigger_mode)

        self.set_exposure_time(self._exposure)

        self.set_shutter_status(self._shutter_status)

    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.

        """
        #self.stop_acquisition()

        # à reprendre
        # self._set_shutter(0, 0, 0.1, 0.1)
        self.dll.ShutDown()

##############################################################################
#                                     Error management
##############################################################################
# is working
    def check(self, func_val):
        """ Check routine for the received error codes.
         :return: the dll function error code
        Tested : no
        """

        if not func_val == 20002:
            self.log.error('Error in Newton with errorcode {0}:\n'
                           '{1}'.format(func_val, self.errorcode[func_val]))
        return func_val

    def _create_errorcode(self):
        """ Create a dictionary with the errorcode for the device.
        """
        maindir = get_main_dir()

        filename = os.path.join(maindir, 'hardware', 'camera', 'andor', 'errorcodes_newton.h')
        try:
            with open(filename) as f:
                content = f.readlines()
        except:
            self.log.error('No file "errorcodes_newton.h" could be found in the '
                           'hardware/camera/andor/ directory!')

        errorcode = {}
        for line in content:
            if '#define ' in line:
                errorstring, errorvalue = line.split()[-2:]
                errorcode[int(errorvalue)] = errorstring

        return errorcode

##############################################################################
#                                     Basic functions
##############################################################################

    def get_constraint(self):
        """Returns all the fixed parameters of the hardware which can be used by the logic.

        @return: (dict) constraint dict : {'read_mode_list' : ['FVB', 'MULTI_TRACK'...],
                                    'acquistion_mode_list' : ['SINGLE_SCAN', 'MULTI_SCAN'...],
                                     'trigger_mode_list' : ['INTERNAL', 'EXTERNAL'...],
                                     'shutter_mode_list' : ['CLOSE', 'OPEN'...]
                                     'image_size' : (512, 2048),
                                     'pixiel_size' : (1e-4, 1e-4),
                                     'name' : 'Newton940'}
        """
        dico={}
        dico['read_mode_list'] =['FVB', 'RANDOM_TRACK', 'SINGLE_TRACK', 'IMAGE']
        dico['acquistion_mode_list'] = ['SINGLE_SCAN']
        dico['trigger_mode_list'] =  ['INTERNAL', 'EXTERNAL', 'EXTERNAL_START', 'EXTERNAL_EXPOSURE', 'SOFTWARE_TRIGGER', 'EXTERNAL_CHARGE_SHIFTING']
        dico['shutter_mode_list'] = ['AUTO', 'OPEN', 'CLOSE']
        dico['image_size'] = self.get_image_size()
        dico['pixiel_size'] = self.get_pixel_size()
        dico['name'] = self.get_name()
        dico['Pream Gain'] = [1, 2, 4]

        return dico

    def start_acquisition(self):
        """
        :return: nothing
        Tested : no
        """
        self.check(self.dll.StartAcquisition())
        self.dll.WaitForAcquisition()
        return

    def stop_acquisition(self):
        """
        Stops/aborts live or single acquisition

        @return nothing
        """
        self.check(self.dll.AbortAcquisition())
        return

    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """

        if self._acquisition_mode == 'SINGLE_SCAN':
            if self._read_mode == 'FVB':
                dim = self._width
                h=1

            if self._read_mode == 'RANDOM_TRACK':
                dim = self._width*self._number_of_tracks
                h=self._number_of_tracks

            if self._read_mode == 'SINGLE_TRACK':
                dim = self._width
                h=1

            if self._read_mode == 'IMAGE':
                dim = self._width*self._height
                h=self._height

            dim = int(dim)
            image_array = np.zeros(dim)
            cimage_array = c_int * dim
            cimage = cimage_array()


            error_code = self.dll.GetAcquiredData(pointer(cimage), dim)

            if ERROR_DICT[error_code] != 'DRV_SUCCESS':
                self.log.warning('Couldn\'t retrieve an image. {0}'.format(ERROR_DICT[error_code]))

            else:
                self.log.debug('image length {0}'.format(len(cimage)))
                for i in range(len(cimage)):
                    # could be problematic for 'FVB' or 'SINGLE_TRACK' readmode
                    image_array[i] = cimage[i]

            image_array = np.reshape(image_array, (self._width, h))

            self._cur_image = image_array
            return image_array





##############################################################################
#                           Read mode functions
##############################################################################
# is working, but not secured and SI

    def get_read_mode(self):
        """
        Getter method returning the current read mode used by the camera.

        :return: @str read mode (must be compared to a dict)

        The function GetReadMode does not exist in Andor SDK... surprising !
        We have to use a local variable.
        """

        return self._read_mode

    def set_read_mode(self, read_mode):
        """
        Setter method setting the read mode used by the camera.

        :param read_mode: @str read mode (must be compared to a dict)
        :return: nothing
        """
        if hasattr(ReadMode, read_mode):
            n_mode = c_int(getattr(ReadMode, read_mode).value)
            error_code = self.dll.SetReadMode(n_mode)
            if read_mode == 'IMAGE':
                self.log.debug("width:{0}, height:{1}".format(self._width, self._height))
                self.set_active_image(1, 1, 1, self._width, 1, self._height)
            self._read_mode = read_mode

        return

    def get_readout_speed(self):
        return self._readout_speed

    def set_readout_speed(self, readout_speed):
        if readout_speed in list(READOUT_SPEED_DICT.values()):
            readout_speed_index=list(READOUT_SPEED_DICT.values()).index(readout_speed)
            self.check(self.dll.SetHSSpeed(0,readout_speed_index))
            self._readout_speed = readout_speed
            return
        else:
            self.log.warning('Hardware / Newton940 / set.readout_speed : readout_speed value is not available')


    def get_active_tracks(self):
        """Getter method returning the read mode tracks parameters of the camera.

        @return: (ndarray) active tracks positions [1st track start, 1st track end, ... ]
        """
        if self._read_mode == 'SINGLE_TRACK' or self._read_mode == 'RANDOM_TRACK':
            return self._active_tracks
        else:
            self.log.error('you are not in SINGLE_TRACK or RANDOM_TRACK read_mode')
            return

    def set_active_tracks(self, active_tracks):
        """
        Setter method setting the read mode tracks parameters of the camera.

        @param active_tracks: (numpy array of int32) active tracks positions [1st track start, 1st track end, ... ]
        @return: nothing
        """

        number_of_tracks = int(len(active_tracks)/2)
        self.dll.SetRandomTracks.argtypes = [ct.c_int32, ct.c_void_p]

        if self._read_mode == 'FVB':
            self.log.error('you want to define acquisition track, but current read_mode is FVB')
        elif self._read_mode == 'MULTI_TRACK':
            self.log.error('Please use RANDOM TRACK read mode for multi-track acquisition')
        elif self._read_mode == 'IMAGE':
            self.log.error('you want to define acquisition track, but current read_mode is IMAGE')
        elif self._read_mode == 'SINGLE_TRACK' and number_of_tracks == 1:
            self.check(self.dll.SetRandomTracks(number_of_tracks, active_tracks.ctypes.data))
        elif self._read_mode == 'RANDOM_TRACK':
            self.check(self.dll.SetRandomTracks(number_of_tracks, active_tracks.ctypes.data))
        else:
            self.log.error('problem with active tracks setting')

        self._active_tracks=active_tracks
        self._number_of_tracks=number_of_tracks

        return

    def get_active_image(self):
        """Getter method returning the read mode image parameters of the camera.

        @return: (ndarray) active image parameters [hbin, vbin, hstart, hend, vstart, vend]
        """
        active_image_parameters = [self._hbin, self._vbin, self._hstart, self._hend, self._vstart, self._vend]
        return active_image_parameters

    def set_active_image(self,hbin, vbin, hstart, hend, vstart, vend):
        """Setter method setting the read mode image parameters of the camera.

        @param hbin: (int) horizontal pixel binning
        @param vbin: (int) vertical pixel binning
        @param hstart: (int) image starting row
        @param hend: (int) image ending row
        @param vstart: (int) image starting column
        @param vend: (int) image ending column
        @return: nothing
        """
        hbin, vbin, hstart, hend, vstart, vend = c_int(hbin), c_int(vbin), \
                                                 c_int(hstart), c_int(hend), c_int(vstart), c_int(vend)

        error_code = self.dll.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        msg = ERROR_DICT[error_code]
        if msg == 'DRV_SUCCESS':
            self._hbin = hbin.value
            self._vbin = vbin.value
            self._hstart = hstart.value
            self._hend = hend.value
            self._vstart = vstart.value
            self._vend = vend.value
            self._width = int((self._hend - self._hstart + 1) / self._hbin)
            self._height = int((self._vend - self._vstart + 1) / self._vbin)
        else:
            self.log.error('Call to SetImage went wrong:{0}'.format(msg))
        return

##############################################################################
#                           Acquisition mode functions
##############################################################################
# is working, but not secured and SI

    def get_acquisition_mode(self):
        """
        Getter method returning the current acquisition mode used by the camera.

        :return: @str acquisition mode (must be compared to a dict)
        """
        return self._acquisition_mode

    def set_acquisition_mode(self, acquisition_mode):
        """
        Setter method setting the acquisition mode used by the camera.

        :param acquisition_mode: @str read mode (must be compared to a dict)
        :return: nothing
        """

        if hasattr(AcquisitionMode, acquisition_mode):
            n_mode = c_int(getattr(AcquisitionMode, acquisition_mode).value)
            self.check(self.dll.SetAcquisitionMode(n_mode))
        else:
            self.log.warning('{0} mode is not supported'.format(acquisition_mode))

        self._acquisition_mode = acquisition_mode

        return

    def get_exposure_time(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """

        exposure = c_float()
        accumulate = c_float()
        kinetic = c_float()
        error_code = self.dll.GetAcquisitionTimings(byref(exposure),
                                                    byref(accumulate),
                                                    byref(kinetic))
        self._exposure = exposure.value
        self._accumulate = accumulate.value
        self._kinetic = kinetic.value

        return self._exposure

    def set_exposure_time(self, exposure_time):
        """ Set the exposure time in seconds

        @param float time: desired new exposure time

        @return float: setted new exposure time
        """
        # faire test sur type de exposure time

        # self.dll.SetExposureTime.argtypes = [ct.c_float]

        code = self.check(self.dll.SetExposureTime(c_float(exposure_time)))

        if code == 20002:
            self._exposure = exposure_time
            return True
        else:
            self.log.error('Error during set_exposure_time')

    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        return self._preamp_gain

    def set_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """

        if gain in list(GAIN_DICT.values()):
            gain_index=list(GAIN_DICT.values()).index(gain)
            self.check(self.dll.SetPreAmpGain(gain_index))
            self._preamp_gain = gain
            return
        else:
            self.log.warning('Hardware / Newton940 / set.gain : gain value is not available')

##############################################################################
#                           Trigger mode functions
##############################################################################
# is working, but not secured and SI

    def get_trigger_mode(self):
        """
        Getter method returning the current trigger mode used by the camera.

        :return: @str trigger mode (must be compared to a dict)
        """
        return self._trigger_mode

    def set_trigger_mode(self, trigger_mode):
        """
        Setter method setting the trigger mode used by the camera.

        :param trigger_mode: @str trigger mode (must be compared to a dict)
        :return: nothing
        """
        if hasattr(TriggerMode, trigger_mode):
            n_mode = c_int(getattr(TriggerMode, trigger_mode).value)
            self.check(self.dll.SetTriggerMode(n_mode))
            self._trigger_mode = trigger_mode
        else:
            self.log.warning('{0} mode is not supported'.format(trigger_mode))
        return

##############################################################################
#                           Shutter mode functions
##############################################################################
# is working, but not secured and SI

    def get_shutter_status(self):
        """
        Getter method returning if the shutter is open.

        :return: @bool shutter open ?
        """
        return self._shutter_status

    def set_shutter_status(self, shutter_status):
        """
        Setter method setting if the shutter is open.

        :param shutter_mode: @bool shutter open
        :return: nothing
        """

        if hasattr(ShutterMode, shutter_status):
            mode = c_int(getattr(ShutterMode, shutter_status).value)
            self.dll.SetShutter(self._shutter_TTL, mode, self._shutter_closing_time, self._shutter_opening_time)
            self._shutter_status = shutter_status

        return

##############################################################################
#                           Temperature functions
##############################################################################
# is working, but not secured and SI

    def get_cooler_status(self):
        """
        Getter method returning the cooler status if ON or OFF.

        :return: @bool True if ON or False if OFF or 0 if error
        """
        return self._cooler_status

    def set_cooler_status(self, cooler_status):
        """
        Setter method returning the cooler status if ON or OFF.

        :cooler_ON: @bool True if ON or False if OFF
        :return: nothing
        """
        if cooler_status:
            self.check(self.dll.CoolerON())
            self._cooler_status=True
        else:
            self.check(self.dll.CoolerOFF())
            self._cooler_status=False
        return

    def get_temperature(self):
        """
        Getter method returning the temperature of the camera.

        :return: @float temperature (°C) or 0 if error
        """
        temp = c_int32()
        self.dll.GetTemperature(byref(temp))

        return temp.value

    def set_temperature(self, temperature):
        """
        Getter method returning the temperature of the camera.

        :param temperature: @float temperature (°C) or 0 if error
        :return: nothing
        """
        tempperature = c_int32(temperature)
        self.dll.SetTemperature(temperature)
        return

##############################################################################
#               Internal functions, for constraints preparation
##############################################################################
# is working, but not secured and SI

    def get_name(self):
        """
        :return: string local camera name with serial number

        """
        serial = ct.c_int()
        self.check(self.dll.GetCameraSerialNumber(byref(serial)))
        name = self._camera_name + " serial number " + str(serial.value)
        return name

    def get_image_size(self):
        """
        Returns the sensor size in pixels (x;y)

        :return: tuple (nw_px, ny_px) : int number of pixel along x and y axis

        Tested : no
        SI check : ok
        """
        nx_px = ct.c_int()
        ny_px = ct.c_int()
        self.check(self.dll.GetDetector(byref(nx_px), byref(ny_px)))
        return nx_px.value, ny_px.value

    def get_pixel_size(self):
        """
        :return:
        """
        x_px = ct.c_float()
        y_px = ct.c_float()
        self.check(self.dll.GetPixelSize(byref(x_px), byref(y_px)))
        return x_px.value * 1E-6, y_px.value * 1E-6

    def get_ready_state(self):
        """

        :return:
        """
        code = ct.c_int()
        self.check(self.dll.GetStatus(byref(code)))
        if code.value == 20073:
            return True
        else:
            return False










































