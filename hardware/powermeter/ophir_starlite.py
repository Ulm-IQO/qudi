# -*- coding: utf-8 -*-
"""

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

import numpy as np

from core.module import Base
from interface.powermeter_interface import PowermeterInterface
from time import sleep, time
try:
    import win32com.client
except:
    pass


class StarLite(Base, PowermeterInterface):
    """ Device driver for Ophir USB interface adapter

	This class provides access to the OphirUSBI ActiveX interface
	The ActiveX control is included by early-binding. It is necessary to run the Com - Makepy Utility found in the PythonWinIDE - Tools - Menu

    """
    _modclass = 'powermeter' #pas trop compris
    _modtype = 'hardware' #PV pour que le fichier config sache que c'est du hardware

    def on_activate(self): #appelle la fonction de connection
        self.USBI_handle = 0
        self.USBI_channel = 0
        self.timeout = 0.1  # timeout in s for measurement
        self.device_ready = False  # True if device has already delivered data; otherwise or after timeout, this is set to False

        self.measurement_mode = 0
        self.MM_Modes = ()
        self.pulse_length = 0
        self.MM_PulseLengths = ()
        self.range = 0
        self.MM_Ranges = ()
        self.wavelength = 0
        self.MM_Wavelengths = ()
        self.measurement_running = False

        # connect to activeX class and store module in adwin_ax
        print("Try to connect to ActiveX component..")
        self.USBI_com = win32com.client.Dispatch("OphirLMMeasurement.CoLMMeasurement")
        print("..success")
        print("COM Version:", self.USBI_com.GetVersion())
        self.set_measurement_mode("power")
        self.connect()

    def on_deactivate(self):
        self.disconnect()

#
#   def getData(self):
#        return [self.get_power()]
#
#   def getChannels(self):
#      time.sleep(0.1)
        #return 3



    def scanUSBI(self):
        # return a list with attached USBI Devices
        return self.USBI_com.ScanUSB()

    def connect(self, devID=0):
        # iterate all connected USB sensors
        devices = self.USBI_com.ScanUSB()
        print("Found", len(devices), "USB Devices..")

        # connect to device devID
        self.USBI_handle = self.USBI_com.OpenUSBDevice(devices[devID])
        print("Connected to Sensor", self.USBI_com.GetSensorInfo(self.USBI_handle, self.USBI_channel))

        # read configuration
        try:
            self.measurement_mode, self.MM_Modes = self.USBI_com.GetMeasurementMode(self.USBI_handle, self.USBI_channel)
            self.pulse_length, self.MM_PulseLengths = self.USBI_com.GetPulseLengths(self.USBI_handle, self.USBI_channel)
            self.range, self.MM_Ranges = self.USBI_com.GetRanges(self.USBI_handle, self.USBI_channel)
            self.wavelength, self.MM_Wavelengths = self.USBI_com.GetWavelengths(self.USBI_handle, self.USBI_channel)
        except:
            pass

    def disconnect(self):
        print("disconnect OphirUSBI")
        # close connection
        if (self.USBI_handle != 0):
            self.USBI_com.Close(self.USBI_handle)
            self.USBI_handle = 0

    def reset(self):
        # reset sensor
        # device must not be in streaming mode
        if (self.USBI_handle != 0):
            self.USBI_com.ResetDevice(self.USBI_handle)

    # get / set methods
    """
    def get_measurement_mode(self):
        return self.measurement_mode

    def set_measurement_mode(self, newmode):
        if (self.USBI_handle == 0):
            return
        if (newmode < 0 or newmode >= len(self.MM_Modes)):
            return
        self.measurement_mode = newmode
        self.USBI_com.SetMeasurementMode(self.USBI_handle, self.USBI_channel, newmode)

    """
    def get_wavelength(self):
        return self.wavelength

    def set_wavelength(self, newmode):
        if (self.USBI_handle == 0):
            return
        if (newmode < 0 or newmode >= len(self.MM_Wavelengths)):
            return
        self.wavelength = newmode
        self.USBI_com.SetWavelength(self.USBI_handle, self.USBI_channel, newmode)

    def get_range(self):
        return self.range

    def set_range(self, newmode):
        if (self.USBI_handle == 0):
            return
        if (newmode < 0 or newmode >= len(self.MM_Ranges)):
            return
        self.range = newmode
        self.USBI_com.SetRange(self.USBI_handle, self.USBI_channel, newmode)

    def get_pulse_length(self):
        return self.pulse_length

    def set_pulse_length(self, newmode):
        if (self.USBI_handle == 0):
            return
        if (newmode < 0 or newmode >= len(self.MM_PulseLengths)):
            return
        self.pulse_length = newmode
        self.USBI_com.SetPulseLength(self.USBI_handle, self.USBI_channel, newmode)

    # measurement functions
    def set_turbo_mode(self, freq):
        if (self.USBI_handle == 0):
            return
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 2, 0)
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 1, freq)
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 0, 1)

    def set_immediate_mode(self):
        if (self.USBI_handle == 0):
            return
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 0, 0)
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 2, 1)

    def set_default_mode(self):
        if (self.USBI_handle == 0):
            return
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 0, 0)
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 2, 0)

    # functions for direct legacy access to the Ophir
    def ask(self, cmd):
        if (self.USBI_handle == 0):
            return
        res = ""
        self.USBI_com.Write(self.USBI_handle, cmd)
        sleep(0.01)  # wait 10ms
        try:
            res = self.USBI_com.Read(self.USBI_handle)
        except:
            print("ERROR: Cannot read response from OphirUSBI")
        return res.strip()

    # read data from powermeter
    # this function is written without using the ActiveX.GetData function, as this blocks the program
    def read_data(self, num_samples):
        if (self.USBI_handle == 0):
            return []
        datax = []
        datay = []
        # poll data as long as n < num_samples
        time0 = time()
        ready = False
        mtime = 0
        while (len(datax) < num_samples):
            data = ""
            ready = self.ask("EF")
            if ready == "*1":
                mtime = time() * 500
                if (self.measurement_mode == 0):  # power
                    data = self.ask("SP")
                    mtime += time() * 500
                else:  # energy
                    data = self.ask("SE")
                    mtime += time() * 500
                self.device_ready = True

            if (data != ""):
                time0 = time()  # reset timeout counter
                datax.append(mtime)
                datay.append(float(data[1:]))

            if time() - time0 > self.timeout:
                self.device_ready = False
                return []

        return [datax, datay]

    def start(self):
        if (self.USBI_handle == 0):
            return
        if (self.measurement_running):
            return
        # start data capture
        self.USBI_com.StartStream(self.USBI_handle, self.USBI_channel)
        # set status variable
        self.measurement_running = True

    def stop(self):
        if (self.USBI_handle == 0):
            return
        # stop data capture
        self.USBI_com.StopStream(self.USBI_handle, self.USBI_channel)
        # set status variable
        self.measurement_running = False

    # be careful with this function as it blocks the app if no data is coming from the measurement head!!
    def get_data(self):
        if (self.USBI_handle == 0):
            return
        if (self.device_ready == False):
            self.read_data(1)  # try to read data.. -> this would reset the device_ready flag
        if (self.device_ready == False):  # print an error if the device is still not operational
            print("ERROR: OphirUSBI Device not ready! Check range settings!")
            return
        data = self.USBI_com.GetData(self.USBI_handle, self.USBI_channel)
        return [list(data[1]), list(data[0]), list(data[2])]

    def get_power(self):
        try:
            power=float(self.ask("SP")[1:]) #on commence au second caractère car Ophir renvoie * pour commencer si tout va bien.
        except:
            power=np.nan
        return power


    def set_measurement_mode(self, modestring):
        if modestring == "power":
            rep = self.ask("FP")
            if rep != "*":
                self.log.warning(rep)
        elif modestring == "energy":
            rep = self.ask("FE")
            if rep != "*":
                self.log.warning(rep)
        else :
            self.log.warning("wrong ophir modestring")
