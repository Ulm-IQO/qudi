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
import visa

from core.module import Base
from core.configoption import ConfigOption
from interface.simple_data_interface import SimpleDataInterface
from datetime import datetime
from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
import time
try:
    from TLPM import TLPM
except ImportError:
    raise ImportError('TLPM module not found')


class PM16120(Base, SimpleDataInterface):
    """ Hardware module for Thorlabs PM100D powermeter.

    Example config :
    powermeter:
        module.Class: 'powermeter.PM16-120.PM16120'
        address: 'USB0::0x1313::0x807B::220707321::INSTR'

    This module is rewritten from an example file provided by Thorlabs, which can be found in
    "C:\Program Files (x86)\IVI Foundation\VISA\WinNT\TLPM\Example\Python\PowermeterSample.py"
    """

    _address = ConfigOption('address', missing='error')
    _timeout = ConfigOption('timeout', 1)
    _power_meter = None

    def on_activate(self):
        """ Startup the module """

        tlPM = TLPM()
        deviceCount = c_uint32()
        tlPM.findRsrc(byref(deviceCount))
        resourceName = create_string_buffer(1024)
        if deviceCount.value > 1:
            for i in range(0, deviceCount.value):
                tlPM.getRsrcName(c_int(i), resourceName)
                break
            self.log.info(
                f"Found multiple powermeters. Using the powermeter found at {c_char_p(resourceName.raw).value}"
            )
        tlPM.close()

        resourceName = create_string_buffer(self._address.encode())
        self._inst = TLPM()
        self._inst.open(resourceName, c_bool(True), c_bool(True))

    def on_deactivate(self):
        """ Stops the module """
        self._inst.close()

    def getData(self):
        """ SimpleDataInterface function to get the power from the powermeter """
        return np.array([self.get_power()])

    def getChannels(self):
        """ SimpleDataInterface function to know how many data channel the device has, here 1. """
        return 1

    def get_power(self):
        """ Return the power read from the ThorlabsPM100 package """
        power = c_double()
        self._inst.measPower(byref(power))
        return power.value

    def set_wavelength(self, wavelength):
        c_wavelength = c_double(wavelength)
        self._inst.getWavelength(c_wavelength)