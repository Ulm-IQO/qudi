# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 08:43:56 2015

@author: Felix Benz (fb400)
"""
# TODO: Implement functions for:
# - focus mirror
# - flipper mirror
# - accessoires
# - output slit
# - Shutters


import sys
import time
from ctypes import *
import platform
from .errorcodes import ERROR_CODE

class Spectrograph:
    def __init__(self):
        # for Windows
        #self.dll2 = CDLL("C:\\Program Files\\Andor SDK\\Drivers\\Shamrock64\\atshamrock")
        #self.dll = CDLL("C:\\Program Files\\Andor SDK\\Drivers\\Shamrock64\\ShamrockCIF")

        # Check operating system and load library
        # for Windows
        if platform.system() == "Windows":
            self.dll = CDLL("C:\\Program Files\\Andor SDK\\Drivers\\Shamrock64\\ShamrockCIF")
        #    if platform.architecture()[0] == "32bit":
        #        self.dll = cdll("C:\\Program Files\\Andor SOLIS\\Drivers\\atmcd32d")
        #    else:
        #        self.dll = cdll("C:\\Program Files\\Andor SOLIS\\Drivers\\atmcd64d")
        # for Linux
        if platform.system() == "Linux":
            dllname = "/usr/local/lib/libshamrockcif.so"
            self.dll = cdll.LoadLibrary(dllname)
        else:
            raise RuntimeError("Cannot detect operating system, will now stop")

        tekst = c_char()
        error = self.dll.ShamrockInitialize(byref(tekst))

        self.shamrocks = None
        self.current_shamrock = 0  # for more than one Shamrock this has to be varied, see ShamrockGetNumberDevices
        self.grating = None
        self.current_grating = None
        self.motor_present = None
        self.current_wavelength = None
        self.wavelength_is_zero = None
        self.current_slit = 2
        self.slit_present = None
        self.out_slit_width = None
        self.slit_width = None
        self.pixel_width = None
        self.pixel_number = None
        self.status = ERROR_CODE[error]
        self.verbosity = True
        self.current_grating = None

    # some commands to print out returned errors from the Shamrock
    def verbose(self, error, function=''):
        if self.verbosity is True:
            print("[%s]: %s" % (function, error))

    def SetVerbose(self, state=True):
        self.verbosity = state

    # basic Shamrock features
    def ShamrockInitialize(self):
        error = self.dll.ShamrockInitialize("")
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetNumberDevices(self):
        no_shamrocks = c_int()
        error = self.dll.ShamrockGetNumberDevices(byref(no_shamrocks))
        self.shamrocks = no_shamrocks.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockClose(self):
        error = self.dll.ShamrockClose()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetSerialNumber(self):
        self.ShamrockSN = c_char()
        error = self.dll.ShamrockGetSerialNumber(self.current_shamrock, byref(self.ShamrockSN))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.ShamrockSN

    def ShamrockEepromGetOpticalParams(self):
        self.FocalLength = c_float()
        self.AngularDeviation = c_float()
        self.FocalTilt = c_float()
        error = self.dll.ShamrockEepromGetOpticalParams(self.current_shamrock, byref(self.FocalLength),
                                                        byref(self.AngularDeviation), byref(self.FocalTilt))
        return ERROR_CODE[error]

    # basic Grating features
    def ShamrockGratingIsPresent(self):
        is_present = c_int()
        error = self.dll.ShamrockGratingIsPresent(self.current_shamrock, is_present)
        self.grating = is_present.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.grating

    def ShamrockGetTurret(self):
        self.Turret = c_int()
        error = self.dll.ShamrockGetTurret(self.current_shamrock, byref(self.Turret))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.Turret

    def ShamrockGetNumberGratings(self):
        self.noGratings = c_int()
        error = self.dll.ShamrockGetNumberGratings(self.current_shamrock, byref(self.noGratings))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.noGratings

    def ShamrockGetGrating(self):
        grating = c_int()
        error = self.dll.ShamrockGetGrating(self.current_shamrock, byref(grating))
        self.current_grating = grating.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetGratingInfo(self):
        if self.current_grating is None:
            self.ShamrockGetGrating()
        lines = c_float()
        blaze = c_char()
        home = c_int()
        offset = c_int()
        error = self.dll.ShamrockGetGratingInfo(self.current_shamrock, self.current_grating, byref(lines), byref(blaze),
                                                byref(home), byref(offset))
        self.CurrGratingInfo = [lines.value, blaze.value, home.value, offset.value]
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.CurrGratingInfo

    def ShamrockGetGratingOffset(self):
        if self.current_grating is None:
            self.ShamrockGetGrating()
        self.GratingOffset = c_int()  # not this is in steps, so int
        error = self.dll.ShamrockGetGratingOffset(self.current_shamrock, self.current_grating,
                                                  byref(self.GratingOffset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.GratingOffset

    def ShamrockSetGratingOffset(self, offset):
        error = self.dll.ShamrockSetGratingOffset(self.current_shamrock, self.current_grating, c_int(offset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetDetectorOffset(self):
        self.DetectorOffset = c_int()  # not this is in steps, so int
        error = self.dll.ShamrockGetDetectorOffset(self.current_shamrock, byref(self.DetectorOffset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.DetectorOffset

    def ShamrockSetDetectorOffset(self, offset):
        error = self.dll.ShamrockSetDetectorOffset(self.current_shamrock, self.current_grating, c_int(offset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockSetTurret(self, turret):
        error = self.dll.ShamrockSetTurret(self.current_shamrock, c_int(turret))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    # Wavelength features
    def ShamrockWavelengthIsPresent(self):
        ispresent = c_int()
        error = self.dll.ShamrockWavelengthIsPresent(self.current_shamrock, byref(ispresent))
        self.motor_present = ispresent.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetWavelength(self):
        curr_wave = c_float()
        error = self.dll.ShamrockGetWavelength(self.current_shamrock, byref(curr_wave))
        self.current_wavelength = curr_wave.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.current_wavelength

    def ShamrockAtZeroOrder(self):
        is_at_zero = c_int()
        error = self.dll.ShamrockAtZeroOrder(self.current_shamrock, byref(is_at_zero))
        self.wavelength_is_zero = is_at_zero.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetWavelengthLimits(self):
        min_wl = c_float()
        max_wl = c_float()
        error = self.dll.ShamrockGetWavelengthLimits(self.current_shamrock, self.current_grating, byref(min_wl),
                                                     byref(max_wl))
        self.wl_limits = [min_wl.value, max_wl.value]
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockSetWavelength(self, centre_wl):
        error = self.dll.ShamrockSetWavelength(self.current_shamrock, c_float(centre_wl))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGotoZeroOrder(self):
        error = self.dll.ShamrockGotoZeroOrder(self.current_shamrock)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    # Slit functions
    def ShamrockAutoSlitIsPresent(self):
        present = c_int()
        self.slits = []

        for i in range(1, 5):
            self.dll.ShamrockAutoSlitIsPresent(self.current_shamrock, i, present)
            self.slits.append(present.value)

    # Sets the slit to the default value (10um)
    def ShamrockAutoSlitReset(self, slit):
        error = self.dll.ShamrockAutoSlitReset(self.current_shamrock, self.current_slit)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    # finds if input slit is present
    def ShamrockSlitIsPresent(self):
        slit_present = c_int()
        error = self.dll.ShamrockSlitIsPresent(self.current_shamrock, byref(slit_present))
        self.slit_present = slit_present.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    # Output Slits
    def ShamrockGetAutoSlitWidth(self, slit):
        slitw = c_float()
        error = self.dll.ShamrockGetAutoSlitWidth(self.current_shamrock, slit, byref(slitw))
        self.out_slit_width = slitw.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockSetAutoSlitWidth(self, slit, width):
        slit_w = c_float(width)
        error = self.dll.ShamrockSetAutoSlitWidth(self.current_shamrock, slit, slit_w)
        self.out_slit_width = width
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    # Input Slits
    def ShamrockGetSlit(self):
        slitw = c_float()
        error = self.dll.ShamrockGetSlit(self.current_shamrock, byref(slitw))
        self.slit_width = slitw.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.slit_width

    def ShamrockSetSlit(self, width):
        slit_w = c_float(width)
        error = self.dll.ShamrockSetSlit(self.current_shamrock, slit_w)
        time.sleep(1)
        self.ShamrockGetSlit()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockSlitReset(self):
        error = self.dll.ShamrockSlitReset(self.current_shamrock)
        time.sleep(1)
        self.ShamrockGetSlit()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    # Calibration functions
    def ShamrockSetPixelWidth(self, width):
        error = self.dll.ShamrockSetPixelWidth(self.current_shamrock, c_float(width))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetPixelWidth(self):
        pixelw = c_float()
        error = self.dll.ShamrockGetPixelWidth(self.current_shamrock, byref(pixelw))
        self.pixel_width = pixelw.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetNumberPixels(self):
        numpix = c_int()
        error = self.dll.ShamrockGetNumberPixels(self.current_shamrock, byref(numpix))
        self.pixel_number = numpix.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockSetNumberPixels(self, pixels):
        error = self.dll.ShamrockSetNumberPixels(self.current_shamrock, pixels)
        self.pixel_number = pixels
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def ShamrockGetCalibration(self):
        self.ShamrockGetNumberPixels()
        ccalib = c_float * self.pixel_number
        ccalib_array = ccalib()
        error = self.dll.ShamrockGetCalibration(self.current_shamrock, pointer(ccalib_array), self.pixel_number)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        calib = []

        for i in range(len(ccalib_array)):
            calib.append(ccalib_array[i])

        self.wl_calibration = calib[:]

        return ERROR_CODE[error]

    def ShamrockGetPixelCalibrationCoefficients(self):
        self.ca = c_float()
        self.cb = c_float()
        self.cc = c_float()
        self.cd = c_float()
        error = self.dll.ShamrockGetPixelCalibrationCoefficients(self.current_shamrock, byref(self.ca), byref(self.cb),
                                                                 byref(self.cc), byref(self.cd))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]


