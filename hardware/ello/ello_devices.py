# -*- coding: utf-8 -*-

import os
from serial import Serial, EIGHTBITS,STOPBITS_ONE,PARITY_NONE
import hardware.ello.ello_flip as ello_flip
import hardware.ello.ello_rotation as ello_rotor
from core.configoption import ConfigOption
from core.module import Base
class ThorlabsElloDevices(Base):
    _flipper_port = ConfigOption('_flipper_port', False, missing='warn')
    _rotor_port = ConfigOption('_rotor_port', False, missing='warn')
	
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        self.ell = self.connect()
        if self._flipper_port:
            self.ello_flip = ello_flip.ThorlabsElloFlipper(port = self._flipper_port, ell=self.ell)
        if self._rotor_port:
            self.ello_rotor = ello_rotor.ThorlabsElloRotation(port = self._rotor_port, ell=self.ell)

    def on_deactivate(self):
        self.disconnect()
    def disconnect(self):
        self.ell.close()
    def connect(self):
        self.ell = Serial('COM5', baudrate=9600, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE,parity= PARITY_NONE, timeout=2)
        return self.ell



		