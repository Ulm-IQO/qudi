#!/usr/bin/env python

__author__ = "Vinicius Mariani Lenart"
__copyright__ = "Copyright 2015"
__credits__ = "Lenart&Mariani Research Foundation"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "VMLenart"
__email__ = "vmlenart@gmail.com"
__status__ = "Development"

'''
Remender allow write and read if you use linux:
$ cd /dev/ttyUSB0
$ sudo chmod 777 ttyUSB0
ttyUSB0 was a example, you can use other port as you wish
'''

import serial

def ask_lockin(cmd):
    lok = serial.Serial('COM10', baudrate=115200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1) # I set my lockin for a baudrate = 19200, the defaut usully is 9600, if is the case change timeout=3.
    lok.write(b"*IDN?\n")
    lok.flush()
    idn = lok.readline()
    lok.close()
    print(idn)
    return idn

ask_lockin('*IDN?')
