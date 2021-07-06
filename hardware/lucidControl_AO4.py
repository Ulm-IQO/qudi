# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware interface for the DAC LucidControl AO4.

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
import time
from qtpy import QtCore


from lucidIo.LucidControlAO4 import LucidControlAO4
from lucidIo.Values import ValueVOS4 # Value Type for reading an writing of voltages
from lucidIo import IoReturn # return values

from core.module import Base
from core.configoption import ConfigOption


class Lucid_Control_AO4(Base):
    # ConfigOptions need to be outside of any function.
    # They are already initialized as object of the class
    _port = ConfigOption(name='ao4_port', missing='warn')

    def __init__(self, **kwargs):
        print('LucidControlAO4 __init__')
        super().__init__(**kwargs)

    def on_activate(self):
        print('LucidControlAO4 on_activate')

        try:
            # Create AO4 object
            self.ao4 = LucidControlAO4(self._port)
            # open AO4 port
            self.ao4.open()
        except:
            print('Could not open device LucidControlAO4.')

        self.values = (ValueVOS4(), ValueVOS4(), ValueVOS4(), ValueVOS4())
        

    def on_deactivate(self):
        # set all outputs to zero
        self.outputs_off()
        self.ao4.close()
    

    def outputs_off(self):
        """Sets all outputs to zero."""

        for i in range(4):
            self.values[i].setVoltage(0)
        channels = (True, True, True, True)
        self.ao4.setIoGroup(channels, self.values)


    def get_outputs(self):
        """Returns the output value for all channels.

        """
        voltages = np.zeros(4)
        values_read = (ValueVOS4(), ValueVOS4(), ValueVOS4(), ValueVOS4())
        for i in range(4):
            #gets voltage on ch i and writes it into position i of values
            ret = self.ao4.getIo(i, values_read[i])
            voltages[i] = values_read[i].getVoltage()
        print('Voltages are ' + np.array2string(voltages))
        return values_read
    

    def set_outputs(self,output_values=np.zeros(4), channels=(True, True, True, True)):
        """Sets the output for all channels.

        @param output_values: array of values for output.

        @param chanels: array of booleans indicating which channel to change.
        """

        for i in range(4):
            self.values[i].setVoltage(output_values[i])
        self.ao4.setIoGroup(channels, self.values)

    def info(self):
        """Give info about the device.
        
            Was basicially copied form the example file from LucidControl.
        
        """
        ret = self.ao4.identify(0)
    
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            print('Device Class: %s' % self.ao4.getDeviceClassName())
            print('Device Type : %s' % self.ao4.getDeviceTypeName())
            print('Serial No.: %s' % self.ao4.getDeviceSnr())
            print('Firmware Rev.: %s' % self.ao4.getRevisionFw())
            print('Hardware Rev.: %s' % self.ao4.getRevisionHw())   
        else:
            print('Couldnot identify device.')
            self.ao4.close()
    