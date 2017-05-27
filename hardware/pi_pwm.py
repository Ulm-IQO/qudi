# -*- coding: utf-8 -*-
"""
A module to control the QO Raspberry Pi based H-Bridge hardware.

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


from core.module import Base, ConfigOption
from interface.process_control_interface import ProcessControlInterface
from core.util.mutex import Mutex

import RPi.GPIO as GPIO


class PiPWM(Base, ProcessControlInterface):
    """ Hardware module for Raspberry Pi-based PWM controller.
    """

    _modclass = 'ProcessControlInterface'
    _modtype = 'hardware'

    channel = ConfigOption('channel', 0, missing='warn')
    freq = ConfigOption('frequency', 100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Activate module.
        """
        # pin mapping
        if self.channel == 0:
            self.inapin = 5
            self.inbpin = 22
            self.pwmpin = 24
            self.enapin = 25
            self.enbpin = 23
            self.diapin = 17
            self.dibpin = 18
            self.fanpin = 27
        else:
            self.inapin = 16
            self.inbpin = 19
            self.pwmpin = 21
            self.enapin = 20
            self.enbpin = 26
            self.diapin = 12
            self.dibpin = 6
            self.fanpin = 13

        self.setupPins()
        self.startPWM()

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.stopPWM()

    def setupPins(self):
        """ Set Raspberry Pi GPIO pins to the right mode.
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.enapin, GPIO.OUT)
        GPIO.setup(self.enbpin, GPIO.OUT)
        GPIO.setup(self.inapin, GPIO.OUT)
        GPIO.setup(self.inbpin, GPIO.OUT)
        GPIO.setup(self.pwmpin, GPIO.OUT)
        GPIO.setup(self.fanpin, GPIO.OUT)
        GPIO.setup(self.diapin, GPIO.IN)
        GPIO.setup(self.dibpin, GPIO.IN)
        self.p = GPIO.PWM(self.pwmpin, self.freq)

    def startPWM(self):
        """ Start the PWM output.
        """
        GPIO.output(self.fanpin, True)
        GPIO.output(self.enapin, True)
        GPIO.output(self.enbpin, True)
        GPIO.output(self.inapin, True)
        GPIO.output(self.inbpin, False)

        # Setup PWM and DMA channel 0
        self.p.start(0)
        self.dutycycle = 0

    def stopPWM(self):
        """ Stop the PWM output.
        """
        # Stop PWM
        self.p.stop()
        GPIO.output(self.enapin, False)
        GPIO.output(self.enbpin, False)
        GPIO.output(self.inapin, False)
        GPIO.output(self.inbpin, False)
        GPIO.output(self.fanpin, False)

    def changeDutyCycle(self, duty):
        """ Set the PWM duty cycle in percent.

            @param float duty: PWM duty cycle 0 < duty < 100
        """
        self.dutycycle = 0
        if duty >= 0:
            GPIO.output(self.inapin, True)
            GPIO.output(self.inbpin, False)
        else:
            GPIO.output(self.inapin, False)
            GPIO.output(self.inbpin, True)
        self.p.ChangeDutyCycle(abs(duty))

    def setControlValue(self, value):
        """ Set control value for this controller.

            @param float value: control value, in this case duty cycle in percent
        """
        with self.threadlock:
            self.changeDutyCycle(value)

    def getControlValue(self):
        """ Get control value for this controller.

            @return float: control value, in this case duty cycle in percent
        """
        return self.dutycycle

    def getControlUnit(self):
        """ Get unit for control value.

            @return tuple(str, str): short and text form of unit
        """
        return ('%', 'percent')

    def getControlLimits(self):
        """ Get minimum and maxuimum value for control value.

            @return tuple(float, float): min and max control value
        """
        return (-100, 100)


class PiPWMHalf(PiPWM):
    """ PWM controller restricted to positive values.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #locking for thread safety
        self.threadlock = Mutex()

    def getControlLimits(self):
        """ Get minimum and maxuimum value for control value.

            @return tuple(float, float): min and max control value
        """
        return (0, 100)
