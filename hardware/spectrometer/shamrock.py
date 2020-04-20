# -*- coding: utf-8 -*-
"""
This module contains the hardware module of the Shamrock 500
spectrometer from Andor.

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
na=not applicable
"""

from core.module import Base
from interface.spectrometer_complete_interface import SpectrometerInterface
from core.configoption import ConfigOption
from core.util.modules import get_main_dir
import os

import numpy as np

import ctypes as ct
import time

ERROR_CODE = {
    20201: "SHAMROCK_COMMUNICATION_ERROR",
    20202: "SHAMROCK_SUCCESS",
    20266: "SHAMROCK_P1INVALID",
    20267: "SHAMROCK_P2INVALID",
    20268: "SHAMROCK_P3INVALID",
    20269: "SHAMROCK_P4INVALID",
    20270: "SHAMROCK_P5INVALID",
    20275: "SHAMROCK_NOT_INITIALIZED"
}

class Shamrock(Base,SpectrometerInterface):

# default values
    _dll_location = ConfigOption('dll_location', missing='error')

    _width = 2048       #number of pixels along dispersion axis
    _height = 512       #number of pixels (perpendicular to dispersion axis)
    _pixelwidth = 13E-6    #unit is meter
    _pixelheight = 13E-6  #unit is meter

    MAX_SLITS=4
    MAX_GRATINGS=3
    SLIT_MIN_WIDTH=10E-6
    SLIT_MAX_WIDTH=2500E-6

    def get_constraint(self):
        number_of_gratings = self.get_number_gratings()
        wavelength_limits = np.array([[self.get_wavelength_limit(i)] for i in range(number_of_gratings)])
        auto_slit_installed = np.array([[self.auto_slit_is_present('input',0), self.auto_slit_is_present('input',1)],
                                        [self.auto_slit_is_present('output',0), self.auto_slit_is_present('output',1)]])
        flipper_mirror_installed = np.array([self.flipper_mirror_is_present('input'), self.flipper_mirror_is_present('output')])
        constraint_dict = {'number_of_gratings':number_of_gratings,
                           'wavelength_limits':wavelength_limits,
                           'auto_slit_installed':auto_slit_installed,
                           'flipper_mirror_installed':flipper_mirror_installed}

##############################################################################
#                            Basic functions
##############################################################################

    def on_activate(self):
        """ Activate module.
        """
        self.spectrometer_status = 0
        self.errorcode = self._create_errorcode()

        #self.dll = ct.cdll.LoadLibrary('C:/temp/ShamrockCIF.dll')

        self.dll = ct.cdll.LoadLibrary(self._dll_location)

        code = self.dll.ShamrockInitialize()

        if code != 20202:
            self.log.info('Problem during spectrometer initialization')
            self.on_deactivate()
        else:
            self.spectrometer_status = 1
            nd = ct.c_int()
            self.dll.ShamrockGetNumberDevices(ct.byref(nd))
            #self.nd = nd.value
            self.deviceID = 0 #hard coding : whatever the number of devices... we work with the first. Fix me ?
            self.gratingID = self.get_grating()
            self.set_number_of_pixels(self._width)
            self.set_pixel_width(self._pixelwidth)

    def on_deactivate(self):
        return self.dll.ShamrockClose()

    def check(self, func_val):
        """ Check routine for the received error codes.
        """

        if not func_val == 20202:
            self.log.error('Error in Shamrock with errorcode {0}:\n'
                           '{1}'.format(func_val, self.errorcode[func_val]))
        return func_val

    def _create_errorcode(self):
        """ Create a dictionary with the errorcode for the device.
        """

        maindir = get_main_dir()

        filename = os.path.join(maindir, 'hardware', 'spectrometer', 'errorcodes_shamrock.h')
        try:
            with open(filename) as f:
                content = f.readlines()
        except:
            self.log.error('No file "errorcodes_shamrock.h" could be found in the '
                        'hardware/spectrometer directory!')
        errorcode = {}
        for line in content:
            if '#define SHAMROCK' in line:
                errorstring, errorvalue = line.split()[-2:]
                errorcode[int(errorvalue)] = errorstring

        return errorcode

    def get_number_device(self):
        """
        Returns the number of devices
        Tested : yes
        """
        number_of_devices = ct.c_int()
        self.check(self.dll.ShamrockGetNumberDevices(self.deviceID, ct.byref(number_of_devices)))
        return number_of_devices.value

    def get_optical_parameters(self):
        """
        Returns the spectrometer optical parameters

        @return dictionnary { 'focal length (m)': float (m),
                     'angular deviation (rad)': float (rad)
                     'focal tilt (rad)': float (rad)}
        Tested :  yes
        SI check : yes

        """
        focal_length = ct.c_float()
        angular_deviation = ct.c_float()
        focal_tilt = ct.c_float()
        dico={}
        self.check(self.dll.ShamrockEepromGetOpticalParams(self.deviceID,
                                                           ct.byref(focal_length),
                                                           ct.byref(angular_deviation),
                                                           ct.byref(focal_tilt)))
        dico['focal length (m)'] = focal_length.value
        dico['angular deviation (rad)'] = angular_deviation.value*np.pi/180
        dico['focal tilt (rad)'] = focal_tilt.value*np.pi/180

        return dico

##############################################################################
#                            Gratings functions
##############################################################################
# All functions in this section have been tested (03/04/2020)
# Comments have to be homogenized
# SI check is OK
# parameters validity is secured
##############################################################################

    def get_grating(self):
        """
        Returns the current grating identification (0 to self.get_number_gratings-1)

        Tested : yes
        SI check :  na
        """
        grating = ct.c_int()
        self.check(self.dll.ShamrockGetGrating(self.deviceID, ct.byref(grating)))
        return grating.value-1

    def set_grating(self, grating):
        """
        Sets the required grating (0 to self.get_number_gratings-1)

        @param int grating: grating identification number
        @return: void

        Tested : yes
        SI check : na
        """
        if not (0 <= grating <= (self.get_number_gratings()-1)):
            self.log.error('grating number is not in the validity range')
            return

        if isinstance (grating, int):
            self.check(self.dll.ShamrockSetGrating(self.deviceID, grating+1))
        else:
            self.log.error('set_grating function "grating" parameter needs to be int type')

    def get_number_gratings(self):
        """
        Returns the number of gratings in the spectrometer

        @return int number_of_gratings

        Tested : yes
        SI check : na

        """
        number_of_gratings = ct.c_int()
        self.check(self.dll.ShamrockGetNumberGratings(self.deviceID, ct.byref(number_of_gratings)))
        return number_of_gratings.value

    def get_grating_info(self, grating):
        """
        Returns grating informations

        @param int grating: grating id
        @return dictionnary { 'ruling': float (line/m),
                     'blaze wavelength': string (nm)
                     'home': int (steps)
                     'offset': int (steps)}


        Tested : yes
        SI check : yes

        """
        line = ct.c_float()
        blaze = ct.create_string_buffer(32)
        home = ct.c_int()
        offset = ct.c_int()
        dico = {}

        if not (0 <= grating <= (self.get_number_gratings()-1)):
            self.log.error('grating number is not in the validity range')
            return

        if isinstance (grating, int):
            self.check(self.dll.ShamrockGetGratingInfo(self.deviceID, grating+1,
                                                   ct.byref(line),
                                                   ct.byref(blaze),
                                                   ct.byref(home),
                                                   ct.byref(offset)))
            dico['ruling'] = line.value*1E3
            dico['blaze wavelength (nm)'] = blaze.value
            dico['home'] = home.value
            dico['offset'] = offset.value
            return dico
        else:
            self.log.error('set_grating_info function "grating" parameter needs to be int type')

    def get_grating_offset(self, grating):
        """
        Returns the grating offset (unit is motor steps)

        @param int grating (between 0 and number_of_gratings)
        @return int grating offset (step)

        Tested : yes
        SI check : na

        """
        if not (0 <= grating <= (self.get_number_gratings()-1)):
            self.log.error('grating number is not in the validity range')
            return

        if isinstance (grating, int):
            grating_offset = ct.c_int()
            self.check(self.dll.ShamrockGetGratingOffset(self.deviceID, grating+1, ct.byref(grating_offset)))
            return grating_offset.value
        else:
            self.log.error('get_grating_offset function "grating" parameter needs to be int type')

    def set_grating_offset(self, grating, offset):
        """
        Sets the grating offset (unit is motor step)
        @param int grating : grating id (0..self.get_number_gratings()
                int offset : grating offset (step)

        Tested : yes
        SI check : na

        """
        if not (0 <= grating <= (self.get_number_gratings()-1)):
            self.log.error('grating number is not in the validity range')
            return

        if isinstance (grating, int):
            if isinstance(offset, int):
                self.check(self.dll.ShamrockSetGratingOffset(self.deviceID, grating+1, offset))
            else:
                self.log.error('set_grating_offset function "offset" parameter needs to be int type')
        else:
            self.log.error('set_grating_offset function "grating" parameter needs to be int type')

##############################################################################
#                            Wavelength functions
##############################################################################
# All functions in this section have been tested (03/04/2020)
# Comments have to be homogenized
# SI check is OK
# parameters validity is secured
##############################################################################

    def get_wavelength(self):
        """
        Returns the central current wavelength (m)
        @return float wavelength (m)

        Tested : yes
        SI check : yes
        """
        wavelength = ct.c_float()
        self.check(self.dll.ShamrockGetWavelength(self.deviceID, ct.byref(wavelength)))
        return wavelength.value*1E-9

    def set_wavelength(self, wavelength):
        """
        Sets the new central wavelength
        @params float wavelength (m)

        Tested : yes
        SI check : yes

        """

        minwl, maxwl = self.get_wavelength_limit(self.get_grating())

        if not (minwl <= wavelength <= maxwl):
            self.log.error('the wavelength you ask ({0} nm) is not in the range '
                           'of the current grating ( [{1} ; {2}] nm)'.format(wavelength*1E9, minwl*1E9, maxwl*1E9))
            return

        self.dll.ShamrockSetWavelength.argtypes = [ct.c_int32, ct.c_float]
        self.check(self.dll.ShamrockSetWavelength(self.deviceID, wavelength*1e9))
        #self._wl = self.get_calibration(self.get_number_of_pixels())

        return

    def get_wavelength_limit(self, grating):
        """
        Returns the wavelength limits (m) of the grating (0-self.get_number_gratings)
        @params int grating

        Tested : yes
        SI check : yes

        """
        wavelength_min = ct.c_float()
        wavelength_max = ct.c_float()

        if not (0 <= grating <= (self.get_number_gratings()-1)):
            self.log.error('grating number is not in the validity range')
            return

        if isinstance (grating, int):
            self.check(self.dll.ShamrockGetWavelengthLimits(self.deviceID, grating+1, ct.byref(wavelength_min)
                                                     , ct.byref(wavelength_max)))
            return wavelength_min.value*1E-9, wavelength_max.value*1E-9
        else :
            self.log.error('get_wavelength_limit function "grating" parameter needs to be int type')

    def set_number_of_pixels(self, number_of_pixels):
        """
        Sets the number of pixels of the detector (to prepare for calibration)
        :param number_of_pixels: int
        :return: nothing

        Tested : yes
        SI check : na
        """
        if isinstance (number_of_pixels, int):
            self.check(self.dll.ShamrockSetNumberPixels(self.deviceID, number_of_pixels))
        else:
            self.log.error('set_number_of_pixels function "number_of_pixels" parameter needs to be int type')
        return

    def set_pixel_width(self, width):
        """
        Sets the pixel width along the dispersion axis (to prepare for calibration)
        :param width: float unit is m
        :return: nothing

        Tested : yes
        SI check : yes
        """
        if not (1e-6 <= width <= 100E-6):
            self.log.error('the pixel width you ask ({0} um) is not in a '
                           'reasonable range ( [{1} ; {2}] um)'.format(width*1E6, 1, 100))
            return

        self.dll.ShamrockSetPixelWidth.argtypes = [ct.c_int32, ct.c_float]
        self.check(self.dll.ShamrockSetPixelWidth(self.deviceID, width*1E6))
        return

    def get_number_of_pixels(self):
        """
        Returns the number of pixel that has to be previously set with self.set_number_of_pixels()
        :return: int pixel number

        Tested : yes
        SI check : na
        """
        pixel_number = ct.c_int()
        self.check(self.dll.ShamrockGetNumberPixels(self.deviceID, ct.byref(pixel_number)))
        return pixel_number.value

    def get_pixel_width(self):
        """
        Returns the pixel width along dispersion axis.
        Note that pixel width has to be previously set with self.set_pixel_width(width)
        :return: int pixel number

        Tested : yes
        SI check : yes

        """

        pixel_width = ct.c_float()
        self.check(self.dll.ShamrockGetPixelWidth(self.deviceID, ct.byref(pixel_width)))
        return pixel_width.value*1E-6

##############################################################################
#                            Calibration functions
##############################################################################

    def get_calibration(self):
        """
        Returns the wavelength calibration of each pixel (m)
        @params int number_pixels

        Tested : yes
        SI check : yes

        Important Note : ShamrockSetNumberPixels and ShamrockSetPixelWidth must have been called
        otherwise this function will return -1
        """
        number_pixels = self.get_number_of_pixels()
        wl_array = np.ones((number_pixels,), dtype=np.float32)
        self.dll.ShamrockGetCalibration.argtypes = [ct.c_int32, ct.c_void_p, ct.c_int32]
        self.check(self.dll.ShamrockGetCalibration(self.deviceID, wl_array.ctypes.data, number_pixels))
        return wl_array*1E-9

    def set_calibration(self, number_of_pixels, pixel_width, tracks_offset):

        self.set_number_of_pixels(number_of_pixels)
        self.set_pixel_width(pixel_width)
        self.set_detector_offset(tracks_offset)

##############################################################################
#                            Detector functions
##############################################################################
# All functions in this section have been tested (03/04/2020)
# Comments have to be homogenized
# SI check is OK
# parameters validity is secured
##############################################################################

    def get_detector_offset(self):
        """
        Returns the detector offset in pixels
        :return: int offset

        Tested : yes
        SI check : yes

        """
        offset = ct.c_int()
        self.check(self.dll.ShamrockGetDetectorOffset(self.deviceID, ct.byref(offset)))
        return offset.value

    def set_detector_offset(self, offset):
        """
        Sets the detecotor offset in pixels
        :param offset : int
        :return: nothing

        Tested : yes
        SI check : yes

        """
        if isinstance (offset, int):
            self.check(self.dll.ShamrockSetDetectorOffset(self.deviceID, offset))
        else :
            self.log.error('set_detector_offset function "offset" parameter needs to be int type')

##############################################################################
#                        Ports and Slits functions
##############################################################################
#Important note : slits are adressed with an index.
#Index definition can be found here :
#https://pylablib.readthedocs.io/en/latest/_modules/pylablib/aux_libs/devices/AndorShamrock.html
# 1=input_side - 2=input direct - 3=output side - 4=output direct
# IT HAS TO BE TESTED ON SITE because of the lack of Andor official documentation
##############################################################################
# All functions in this section have been tested (03/04/2020)
# Comments have to be homogenized
# SI check is OK
# parameters validity is secured
##############################################################################

    def flipper_mirror_is_present(self, flipper):
        """
        Returns 1 if flipper mirror is present, 0 if not

        :param flipper: int 1 is for input, 2 is for output
        :return: 1 or 0

        Test
        SI check

        """

        present = ct.c_int()
        if flipper in [1, 2]:
            self.check(self.dll.ShamrockFlipperMirrorIsPresent(self.deviceID, flipper, ct.byref(present)))
        else:
            self.log.error('flipper_mirror_is_present : flipper parameter should be 1 for input port and 2 for output port')
        return present.value

    def get_input_port(self):
        """
        Returns the current port for the input flipper mirror.
        0 is for front port, 1 is for side port
        in case of no flipper mirror, front port (0) is used

        Tested : yes
        SI check : na

        """
        input_port = ct.c_int()
        if self.flipper_mirror_is_present(1) == 1:
            self.check(self.dll.ShamrockGetFlipperMirror(self.deviceID, 1, ct.byref(input_port)))
            return input_port.value
        else:
            input_port.value=0
            self.log.error('there is no flipper mirror on input port')
            return input_port.value

    def get_output_port(self):
        """
        Returns the current port for the output flipper mirror.
        0 is for front port, 1 is for side port
        in case of no flipper mirror, front port (0) is used

        Tested : yes
        SI check : na

        """
        output_port = ct.c_int()
        if self.flipper_mirror_is_present(2)==1:
            self.check(self.dll.ShamrockGetFlipperMirror(self.deviceID, 2, ct.byref(output_port)))
            return output_port.value
        else:
            output_port.value=0
            self.log.error('there is no flipper mirror on output port')
            return output_port.value

    def set_input_port(self, input_port):
        """
        Sets the input port - 0 is for front port, 1 is for side port

        :param input_port: int. has to be in [0, 1]
        :return: nothing

        Tested : yes
        SI check : yes

        """
        if self.flipper_mirror_is_present(1)==1:
            if input_port in [0,1] :
                self.check(self.dll.ShamrockSetFlipperMirror(self.deviceID, 1, input_port))
            else:
                self.log.error('set_input_port function : input port should be 0 (front) or 1 (side)')
        else:
            self.log.error('there is no flipper mirror on input port')

    def set_output_port(self, output_port):
        """
        Sets the input port - 0 is for front port, 1 is for side port

        :param input_port: int. has to be in [0, 1]
        :return: nothing

        Tested : yes
        SI check : yes

        """
        if self.flipper_mirror_is_present(2) == 1:
            if output_port in [0, 1]:
                self.check(self.dll.ShamrockSetFlipperMirror(self.deviceID, 2, output_port))
            else:
                self.log.error('set_output_port function : output port should be 0 (front) or 1 (side)')
        else:
            self.log.error('there is no flipper mirror on output port')

    def slit_index(self, flipper, port):
        """
        Returns the slit index whether there is a slit or not
        :param flipper: string flipper - within ['input', 'output']
        :param port: int - within[0,1] for front or side port
        :return: int slit_index as defined by Andor convention

        Note : just a local function for ease
        """
        if flipper=='input':
            if port==1: slit_index=1
            elif port==0: slit_index=2
            else: slit_index=0
        elif flipper=='output':
            if port==1:slit_index=3
            elif port==0:slit_index=4
            else: slit_index=0
        else: slit_index=0

        return slit_index

    def get_auto_slit_width(self, flipper, port):
        """
        Returns the input slit width (um) in case of a motorized slit,
        :param  string flipper - within ['input', 'output']
                int port - within[0,1] for front or side port
        :return  int offset - slit width, unit is meter (SI)

        Tested : yes
        SI check : yes

        """

        slit_index=self.slit_index(flipper, port)
        if slit_index==0:
            self.log.error('slit parameters are not valid. parameter should be within ([input, output],[0,1]')
            return

        slit_width = ct.c_float()

        if self.auto_slit_is_present(flipper, port) == 1:
            self.check(self.dll.ShamrockGetAutoSlitWidth(self.deviceID, slit_index, ct.byref(slit_width)))
            return slit_width.value*1E-6
        else:
            self.log.error('there is no slit on this port !')

    def set_auto_slit_width(self, flipper, port, slit_width):
        """
        Sets the new slit width for the required slit
        :param flipper: string flipper - within ['input', 'output']
        :param port: int - within[0,1] for front or side port
        :param slit_width: float - unit is meter (SI)
        :return: nothing

        Tested : yes
        SI check : yes
        """
        slit_index = self.slit_index(flipper, port)
        if slit_index == 0:
            self.log.error('slit parameters are not valid. parameter should be within ([input, output],[0,1]')
            return
        self.dll.ShamrockSetAutoSlitWidth.argtypes = [ct.c_int32, ct.c_int32, ct.c_float]
        if self.auto_slit_is_present(flipper, port):
            if (self.SLIT_MIN_WIDTH <= slit_width <=self.SLIT_MAX_WIDTH):
                self.check(self.dll.ShamrockSetAutoSlitWidth(self.deviceID, slit_index, slit_width*1E6))
            else:
                self.log.error('slit_width should be in range [{0}, {1}]  m.'.format(self.SLIT_MIN_WIDTH, self.SLIT_MAX_WIDTH))
        else:
            self.log.error('there is no slit on this port')
        return

    def auto_slit_is_present(self, flipper, port):
        """
        Return whether the required slit is present or not
        :param flipper: string flipper - within ['input', 'output']
        :param port: int - within[0,1] for front or side port
        :return: 1 if present, 0 if not

        Tested : yes
        SI check : yes
        """
        slit_index = self.slit_index(flipper, port)
        if slit_index == 0:
            self.log.error('slit parameters are not valid. parameter should be within ([input, output],[0,1]')
            return
        present = ct.c_int()
        self.check(self.dll.ShamrockAutoSlitIsPresent(self.deviceID, slit_index, ct.byref(present)))
        return present.value


##############################################################################
#                            Shamrock wrapper
##############################################################################
# sdk basic functions

    def shamrock_initialize(self):
        self.check(self.dll.ShamrockInitialize())
        return

    def shamrock_close(self):
        self.check(self.dll.ShamrockClose())
        return

    def goto_zero_order(self):
        """
        Strange function. No documentation from Andor. Seems to be equivalent to self.set_wavelength(0) ?
        """
        self.check(self.dll.ShamrockGotoZeroOrder(self.deviceID))
        return

    def at_zero_order(self):
        pass

    def shamrock_grating_is_present(self):
        """
        Finds if grating is present

        @returns int 1 if present 0 if not

        Tested : yes
        """
        present = ct.c_int()
        self.check(self.dll.ShamrockGratingIsPresent(self.deviceID, ct.byref(present)))
        return present.value





