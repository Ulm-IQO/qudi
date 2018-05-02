# -*- coding: utf-8 -*-

"""
This hardware module implement the camera interface to use an Thorlabs Camera.
It use a dll to inteface with the instruments via USB (only available physical interface)
This module does aim at replacing ThorCam.

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

import platform
import ctypes
from ctypes import *

import numpy as np

from core.module import Base, ConfigOption
from interface.camera_interface import CameraInterface


class SENSORINFO(Structure):
    _fields_ = [
        ("SensorID", c_uint16),
        ("strSensorName", c_char * 32),
        ("nColorMode", c_int8),
        ("nMaxWidth", c_uint32),
        ("nMaxHeight", c_uint32),
        ("bMasterGain", c_int32),  # bool
        ("bRGain", c_int32),  # bool
        ("bGGain", c_int32),  # bool
        ("bBGain", c_int32),  # bool
        ("bGlobShutter", c_int32),  # bool
        ("wPixelSize", c_uint16),  # in nm
        ("nUpperLeftBayerPixel", c_char),
        ("Reserved", c_char * 13)
    ]


class CameraThorlabs(Base, CameraInterface):
    """
    Main class of the module
    """

    _modtype = 'camera'
    _modclass = 'hardware'

    _default_exposure = ConfigOption('default_exposure', 1.0)
    _default_gain = ConfigOption('_default_gain', 1.0)
    _id_camera = ConfigOption('id_camera', 0)  # if more than one camera is present

    _dll = None
    _camera_handle = None
    _exposure = _default_exposure
    _gain = _default_gain
    _width = 0
    _height = 0
    _bit_depth = 0
    _cam = None
    _acquiring = False
    _last_acquisition_mode = None  # useful if config changes during acq
    _sensor_info = None

    _image_memory = None
    _image_pid = None

    def on_activate(self):

        # Load the dll if present
        try:
            if platform.system() == "Windows":
                if platform.architecture()[0] == "64bit":
                    self._dll = ctypes.cdll.uc480_64
                else:
                    self._dll = ctypes.cdll.uc480
            # for Linux
            elif platform.system() == "Linux":
                self._dll = ctypes.cdll.LoadLibrary('libueye_api.so')
            else:
                self.log.error("Can not detect operating system to load Thorlabs DLL.")
        except OSError:
            self.log.error("Can not log Thorlabs DLL.")

        number_of_cameras = ctypes.c_int(0)
        self._dll.is_GetNumberOfCameras(byref(number_of_cameras))
        if number_of_cameras.value < 1:
            self.log.error("No Thorlabs camera detected.")
        elif number_of_cameras.value-1 < self._id_camera:
            self.log.error("A Thorlabs camera has been detected but the id specified above the number of camera(s)")

        self._camera_handle = ctypes.c_int(0)
        self._dll.is_InitCamera(ctypes.pointer(self.filehandle))

        self._sensor_info = SENSORINFO()
        self._dll.is_GetSensorInfo(self._camera_handle, byref(self._sensor_info))
        self._width = self._sensor_info.nMaxWidth
        self._height = self._sensor_infonMaxHeight
        
        if self._sensor_info.nColorMode != 8:
            self.log.error("The current hardware module is not compatible with mor than 8 bits resolution.")
        self._bit_depth = 8

        self._image_pid = ctypes.c_int()
        self._image_memory = ctypes.c_char_p()

        self._dll.is_AllocImageMem(
            self._camera_handle, self._width, self._height,
            self._bit_depth, byref(self._image_memory), byref(self._image_pid))
        self._dll.is_SetImageMem(self._camera_handle, self._image_memory, self._image_pid)

        self.clib.is_EnableAutoExit(self._camera_handle, 1)  # Enable auto-exit

        self.set_exposure(self._exposure)
        self.set_gain(self._gain)

        self._acquiring = False

    def on_deactivate(self):
        self._dll.is_ExitCamera(self._camera_handle)

    def get_name(self):
        return self._sensor_info.strSensorName

    def get_size(self):
        return self._width, self._height

    def start_acquisition(self):
        if self.get_ready_state():
            self._acquiring = True
            self.cam.StartAcquisition()
            wait_time = c_int(10)  # additional time transfer in ms given by the doc
            self._dll.is_FreezeVideo(self._camera_handle, wait_time)
            return 0
        else:
            return -1

    def get_acquired_data(self):
        # Allocate memory for image:
        img_size = self._width * self._height
        c_array = ctypes.c_char * img_size
        c_img = c_array()
        # copy camera memory to accessible memory
        self.clib.is_CopyImageMem(self._camera_handle, self._image_memory, self._image_pid, c_img)
        # Convert to numpy 2d array of float from 0 to 1
        img_array = np.frombuffer(c_img, dtype=ctypes.c_ubyte)
        img_array = img_array.astype(float)
        img_array = img_array/2**self._bit_depth
        img_array.shape = np.array((self._height, self._width))

        self._acquiring = False
        return img_array

    def set_exposure(self, time):

        exp = c_double(time * 1e3)  # in ms
        new_exp = c_double(0)  # in ms

        self._dll.is_SetExposureTime(self._camera_handle, exp, byref(new_exp))
        self._exposure = float(new_exp)/1000

    def get_exposure(self):
        return self._exposure

    def get_ready_state(self):
        return not self._acquiring

    def set_gain(self, gain):
        pass

    def get_gain(self):
        return self._gain