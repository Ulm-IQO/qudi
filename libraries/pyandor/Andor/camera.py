# -*- coding: utf-8 -*-
#   AndoriDus - A Python wrapper for Andor's scientific cameras
#
#   Original code by
#   Copyright (C) 2009  Hamid Ohadi
#
#   Adapted for iDus, qtlab and Windows XP
#   2010 Martijn Schaafsma
#
#   Reworked by Simon Dickreuter 2016
#
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
This module offers basic functionality for the Andor Cameras
'''

# Modules for Andor functionality
import platform
import sys
import time
from ctypes import *
from PIL import Image
from .errorcodes import ERROR_CODE


class Camera():
    """
    Camera class which is meant to provide the Python version of the same
    functions that are defined in the Andor's SDK. Extensive documentation
    on the functions used and error codes can be
    found in the Andor SDK Users Guide
    """

    def __init__(self):
        '''
        Loads and initializes the hardware driver.
        Initializes local parameters
        '''

        # Check operating system and load library
        # for Windows
        if platform.system() == "Windows":
            if platform.architecture()[0] == "64bit":
                self._init_path = "C:\\Program Files\\Andor SOLIS\\"
                self._dll = cdll.LoadLibrary("C:\\Program Files\\Andor SOLIS\\atmcd64d_legacy")
            else:
                raise RuntimeError("Only 64bit Version is supported")
        # for Linux
        elif platform.system() == "Linux":
            #self._init_path = "/usr/local/etc/andor"
            self._init_path = ""
            dllname = "/usr/local/lib/libandor.so"
            self._dll = cdll.LoadLibrary(dllname)
        else:
            raise RuntimeError("Cannot detect operating system, will now stop")

        self._verbosity = True

       # Initiate parameters

        self._temperature  = None
        self._set_T        = None
        self._gain         = None
        self._gainRange    = None
        self._verbosity    = True
        self._preampgain   = None
        self._channel      = None
        self._outamp       = None
        self._hsspeed      = None
        self._vsspeed      = None
        self._serial       = None
        self._exposure     = None
        self._accumulate   = None
        self._kinetic      = None
        self._bitDepths    = []
        self._preAmpGain   = []
        self._VSSpeeds     = []
        self._noGains      = None
        self._imageArray   = []
        self._noVSSpeeds   = None
        self._HSSpeeds     = []
        self._noADChannels = None
        self._noHSSpeeds   = None
        self._ReadMode     = None
        self._cooling      = False

        # Initialize the device
        error = self.Initialize(self._init_path)
        if error == 20002:
            self.GetCameraSerialNumber()
            print("Camera %s initalized" % (self._serial))
        else:
            raise RuntimeError("Camera could not be initialized, aborting.")

        self._status       = ERROR_CODE[error]

        cw = c_int()
        ch = c_int()
        self._dll.GetDetector(byref(cw), byref(ch))

        self._width        = cw.value
        self._height       = ch.value


    def __del__(self):
        if self._cooling :
            self.SetTemperature(0)
            warm = False
            while not warm:
                time.sleep(0.5)
                temp = self.GetTemperature()
                if temp > 0:
                    warm = True
            self.CoolerOFF()
        error = self._dll.ShutDown()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

    def verbose(self, error, function=''):
        if self._verbosity is True:
            print("[%s]: %s" % (function, error))

    def SetVerbose(self, state=True):
        self._verbosity = state

    def AbortAcquisition(self):
        error = self._dll.AbortAcquisition()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def Initialize(self, path):
        error = self._dll.Initialize(path)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return error

    def ShutDown(self):
        error = self._dll.ShutDown()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetCameraSerialNumber(self):
        serial = c_int()
        error = self._dll.GetCameraSerialNumber(byref(serial))
        self._serial = serial.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetReadMode(self, mode):
        # 0: Full vertical binning
        # 1: multi track
        # 2: random track
        # 3: single track
        # 4: image
        error = self._dll.SetReadMode(mode)
        self._ReadMode = mode
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetAcquisitionMode(self, mode):
        # 1: Single scan
        # 3: Kinetic scan
        error = self._dll.SetAcquisitionMode(mode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._AcquisitionMode = mode
        return ERROR_CODE[error]

    def SetNumberKinetics(self, numKin):
        error = self._dll.SetNumberKinetics(numKin)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._scans = numKin
        return ERROR_CODE[error]

    def SetNumberAccumulations(self, number):
        error = self._dll.SetNumberAccumulations(number)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetAccumulationCycleTime(self, time):
        error = self._dll.SetAccumulationCycleTime(c_float(time))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetKineticCycleTime(self, time):
        error = self._dll.SetKineticCycleTime(c_float(time))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetShutter(self, typ, mode, closingtime, openingtime):
        error = self._dll.SetShutter(typ, mode, closingtime, openingtime)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetImage(self, hbin, vbin, hstart, hend, vstart, vend):
        self._hbin = hbin
        self._vbin = vbin
        self._hstart = hstart
        self._hend = hend
        self._vstart = vstart
        self._vend = vend

        error = self._dll.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def StartAcquisition(self):
        error = self._dll.StartAcquisition()
        self._dll.WaitForAcquisition()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetAcquiredData(self, imageArray):
        if (self._ReadMode == 4):
            if (self._AcquisitionMode == 1):
                dim = self._width * self._height / self._hbin / self._vbin
            elif (self._AcquisitionMode == 3):
                dim = self._width * self._height / self._hbin / self._vbin * self._scans
        elif (self._ReadMode == 3 or self._ReadMode == 0):
            if (self._AcquisitionMode == 1):
                dim = self._width
            elif (self._AcquisitionMode == 3):
                dim = self._width * self._scans

        dim = int(dim)
        dim_c = c_int(int(dim))
        cimageArray = c_int * dim
        cimage = cimageArray()
        error = self._dll.GetAcquiredData(pointer(cimage), dim_c)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

        for i in range(len(cimage)):
            imageArray.append(cimage[i])

        self._imageArray = imageArray[:]
        # self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetExposureTime(self, seconds):
        error = self._dll.SetExposureTime(c_float(seconds))
        self._exposure = seconds
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetAcquisitionTimings(self):
        exposure = c_float()
        accumulate = c_float()
        kinetic = c_float()
        error = self._dll.GetAcquisitionTimings(byref(exposure), byref(accumulate), byref(kinetic))
        self._exposure = exposure.value
        self._accumulate = accumulate.value
        self._kinetic = kinetic.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetSingleScan(self):
        self.SetReadMode(4)
        self.SetAcquisitionMode(1)
        self.SetImage(1, 1, 1, self._width, 1, self._height)

    def SetCoolerMode(self, mode):
        error = self._dll.SetCoolerMode(mode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SaveAsBmp(self, path):
        im = Image.new("RGB", (self._width, self._height), "white")
        pix = im.load()

        for i in range(len(self._imageArray)):
            (row, col) = divmod(i, self._width)
            picvalue = int(round(self._imageArray[i] * 255.0 / 65535))
            pix[col, row] = (picvalue, picvalue, picvalue)

        im.save(path, "BMP")

    def SaveAsTxt(self, path):
        file = open(path, 'w')

        for line in self._imageArray:
            file.write("%g\n" % line)

        file.close()

    def SetImageRotate(self, iRotate):
        error = self._dll.SetImageRotate(iRotate)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

    def SaveAsBmpNormalised(self, path):

        im = Image.new("RGB", (self._width, self._height), "white")
        pix = im.load()

        maxIntensity = max(self._imageArray)

        for i in range(len(self._imageArray)):
            (row, col) = divmod(i, self._width)
            picvalue = int(round(self._imageArray[i] * 255.0 / maxIntensity))
            pix[col, row] = (picvalue, picvalue, picvalue)

        im.save(path, "BMP")

    def SaveAsFITS(self, filename, type):
        error = self._dll.SaveAsFITS(filename, type)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def CoolerON(self):
        error = self._dll.CoolerON()
        self._cooling = True
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def CoolerOFF(self):
        error = self._dll.CoolerOFF()
        self._cooling = False
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def IsCoolerOn(self):
        iCoolerStatus = c_int()
        error = self._dll.IsCoolerOn(byref(iCoolerStatus))
        self._cooling = iCoolerStatus
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return iCoolerStatus.value

    def GetTemperature(self):
        ctemperature = c_int()
        error = self._dll.GetTemperature(byref(ctemperature))
        self._temperature = ctemperature.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetTemperature(self, temperature):
        # ctemperature = c_int(temperature)
        # error = self.dll.SetTemperature(byref(ctemperature))
        error = self._dll.SetTemperature(temperature)
        self._set_T = temperature
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetEMCCDGain(self):
        gain = c_int()
        error = self._dll.GetEMCCDGain(byref(gain))
        self._gain = gain.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetEMCCDGainMode(self, gainMode):
        error = self._dll.SetEMCCDGainMode(gainMode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetEMCCDGain(self, gain):
        error = self._dll.SetEMCCDGain(gain)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetEMAdvanced(self, gainAdvanced):
        error = self._dll.SetEMAdvanced(gainAdvanced)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetEMGainRange(self):
        low = c_int()
        high = c_int()
        error = self._dll.GetEMGainRange(byref(low), byref(high))
        self._gainRange = (low.value, high.value)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetNumberADChannels(self):
        noADChannels = c_int()
        error = self._dll.GetNumberADChannels(byref(noADChannels))
        self._noADChannels = noADChannels.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetBitDepth(self):
        bitDepth = c_int()

        self._bitDepths = []

        for i in range(self._noADChannels):
            self._dll.GetBitDepth(i, byref(bitDepth))
            self._bitDepths.append(bitDepth.value)

    def SetADChannel(self, index):
        error = self._dll.SetADChannel(index)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._channel = index
        return ERROR_CODE[error]

    def SetOutputAmplifier(self, index):
        error = self._dll.SetOutputAmplifier(index)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._outamp = index
        return ERROR_CODE[error]

    def GetNumberHSSpeeds(self):
        noHSSpeeds = c_int()
        error = self._dll.GetNumberHSSpeeds(self.channel, self.outamp, byref(noHSSpeeds))
        self._noHSSpeeds = noHSSpeeds.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetHSSpeed(self):
        HSSpeed = c_float()

        self._HSSpeeds = []

        for i in range(self.noHSSpeeds):
            self._dll.GetHSSpeed(self.channel, self.outamp, i, byref(HSSpeed))
            self._HSSpeeds.append(HSSpeed.value)

    def SetHSSpeed(self, itype, index):
        error = self._dll.SetHSSpeed(itype, index)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._hsspeed = index
        return ERROR_CODE[error]

    def GetNumberVSSpeeds(self):
        noVSSpeeds = c_int()
        error = self._dll.GetNumberVSSpeeds(byref(noVSSpeeds))
        self._noVSSpeeds = noVSSpeeds.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetVSSpeed(self):
        VSSpeed = c_float()

        self._VSSpeeds = []

        for i in range(self._noVSSpeeds):
            self._dll.GetVSSpeed(i, byref(VSSpeed))
            self._preVSpeeds.append(VSSpeed.value)

    def SetVSSpeed(self, index):
        error = self._dll.SetVSSpeed(index)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._vsspeed = index
        return ERROR_CODE[error]

    def GetNumberPreAmpGains(self):
        noGains = c_int()
        error = self._dll.GetNumberPreAmpGains(byref(noGains))
        self._noGains = noGains.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetPreAmpGain(self):
        gain = c_float()

        self._preAmpGain = []

        for i in range(self._noGains):
            self._dll.GetPreAmpGain(i, byref(gain))
            self._preAmpGain.append(gain.value)

    def SetPreAmpGain(self, index):
        error = self._dll.SetPreAmpGain(index)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self._preampgain = index
        return ERROR_CODE[error]

    def SetTriggerMode(self, mode):
        error = self._dll.SetTriggerMode(mode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetStatus(self):
        status = c_int()
        error = self._dll.GetStatus(byref(status))
        self._status = ERROR_CODE[status.value]
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self._status

    def GetSeriesProgress(self):
        acc = c_long()
        series = c_long()
        error = self._dll.GetAcquisitionProgress(byref(acc), byref(series))
        if ERROR_CODE[error] == "DRV_SUCCESS":
            return series.value
        else:
            return None

    def GetAccumulationProgress(self):
        acc = c_long()
        series = c_long()
        error = self._dll.GetAcquisitionProgress(byref(acc), byref(series))
        if ERROR_CODE[error] == "DRV_SUCCESS":
            return acc.value
        else:
            return None

    def SetFrameTransferMode(self, frameTransfer):
        error = self._dll.SetFrameTransferMode(frameTransfer)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetShutterEx(self, typ, mode, closingtime, openingtime, extmode):
        error = self._dll.SetShutterEx(typ, mode, closingtime, openingtime, extmode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetSpool(self, active, method, path, framebuffersize):
        error = self._dll.SetSpool(active, method, c_char_p(path), framebuffersize)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetSingleTrack(self, centre, height):
        error = self._dll.SetSingleTrack(centre, height)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetDemoReady(self):
        error = self.SetSingleScan()
        error = self.SetTriggerMode(0)
        error = self.SetShutter(1, 0, 50, 50)
        error = self.SetExposureTime(5.0)
        return error

    def SetBinning(self, binningmode):
        if (binningmode == 1):
            self.SetImage(1, 1, 1, self._width, 1, self._height)
        elif (binningmode == 2):
            self.SetImage(2, 2, 1, self._width, 1, self._height)
        elif (binningmode == 4):
            self.SetImage(4, 4, 1, self._width, 1, self._height)
        else:
            self.verbose("Binning mode not found")

    def qChange(self, pvname=None, value=None, char_value=None):
        self._qVal = value
        if self._qVal > 25:
            self.GetEMCCDGain()
            if self._gain > 1:
                self.SetEMCCDGain(1)
                print('Charge above 25 pC, setting gain to 1')

