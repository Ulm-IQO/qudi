# -*- coding: utf-8 -*-
"""
This module contains a POI Manager core class which gives capability to mark 
points of interest, re-optimise their position, and keep track of sample drift 
over time.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Kay D. Jahnke  kay.jahnke@alumni.uni-ulm.de
"""

from core.base import Base
from hardware.process_interface import ProcessInterface
from collections import OrderedDict
from core.util.mutex import Mutex

from pyqtgraph.Qt import QtCore

import spidev
import struct
import time

class TSYS01SPI(Base, ProcessInterface):
    _modclass = 'TSYS01'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'temperature': 'ProcessInterface'}

    # commands to chip (constants)
    READ_ADC  = 0x00
    RESET     = 0x1E
    START_ADC = 0x48
    READ_ROM0 = 0xA0
    
    def __init__(self, manager, name, config = {}, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict, **kwargs)
        
        #locking for thread safety
        self.threadlock = Mutex()
        
    def activation(self, e):
        config = self.getConfiguration()
        self.bus = config['bus']
        self.device = config['device']
        self.rom = []
        self.spi = spidev.SpiDev()
        self.spi.open(self.bus, self.device)
        self.reset()
        self.readROM()

    def deactivation(self, e):
        self.spi.close()

    def diag(self):
        print('==== SPI Diagnostics ====')
        print('Bits per word: {:>10}'.format(self.spi.bits_per_word))
        print('CS is active high: {!s:>6}'.format(self.spi.cshigh))
        print('Loopback: {!s:>15}'.format(self.spi.loop))
        print('LSB first: {!s:>14}'.format(self.spi.lsbfirst))
        print('Max clock speed: {:>8}'.format(self.spi.max_speed_hz))
        print('Clock mode: {:>13}'.format(self.spi.mode))
        print('SI/SO shared: {!s:>11}'.format(self.spi.threewire))
        print('=========================')

    def reset(self):
        rbuf = self.spi.xfer( [self.RESET], 8000, 3000 )
        time.sleep(0.003)

    def readRomAddr(self, addr):
        bytes = self.READ_ROM0 | 0x0F & ( addr << 1)
        rbuf = self.spi.xfer( [bytes, 0x00, 0x00] )
        return 2**8*rbuf[1] + rbuf[2]

    def readROM(self):
        self.rom = []
        for i in range(8):
            self.rom.append(self.readRomAddr(i))
        
    def startADC(self):
        try:
            rbuf = self.spi.xfer([self.START_ADC])
        except OSError:
            pass
        time.sleep(0.010)

    def readADC(self):
        rbuf = self.spi.xfer([self.READ_ADC, 0x00, 0x00, 0x00] )
        return struct.unpack('>I', b'\0' + bytes(rbuf[1:]))[0]

    def temperatureCelsius(self, adcValue):
        if len(self.rom) < 8:
            self.readROM()
        adc16 = adcValue / 2**8
        return (-2.0 * self.rom[1] * 10**-21 * adc16**4
              +  4.0 * self.rom[2] * 10**-16 * adc16**3
              + -2.0 * self.rom[3] * 10**-11 * adc16**2
              +  1.0 * self.rom[4] * 10**-6  * adc16
              + -1.5 * self.rom[5] * 10**-2 );

    def temperatureKelvin(self, adcValue):
        return 273.15 + self.temperatureCelsius(adcValue)

    def getProcessValue(self):
        with self.threadlock:
            return self.temperatureKelvin(self.readADC())

    def getProcessUnit(self):
        return ('K', 'kelvin')
