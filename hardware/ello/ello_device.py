# -*- coding: utf-8 -*-

import os
from serial import Serial, EIGHTBITS,STOPBITS_ONE,PARITY_NONE
import hardware.ello.ello_flip as ello_flip
import hardware.ello.ello_rotation as ello_rotor
from core.configoption import ConfigOption

class ThorlabsElloDevices(Base):
	""" This class implements communication with the Rotation Mount ELL14.

	Example config for copy-paste:

	--- TODO: PUT IT HERE ---

	"""
    _flipper_port = ConfigOption('flipper_port', False, missing='warn')
    _rotor_port = ConfigOption('rotor_port', False, missing='warn')
	
    def __init__(self, *args, **kwargs):
        if _flipper_port:
		    self.ello_flip = ello_flip.ThorlabsElloFlipper(self._flipper_port)
        if _rotor_port:
            self.ello_rotor = ello_rotor.ThorlabsElloRotation(self._rotor_port)

	def on_activate(self):
		""" Activate module.
		"""
		self.connect()

	def on_deactivate(self):
		""" Disconnect from hardware on deactivation.
		"""
		self.disconnect()
    def disconnect(self):
		""" Disconnects from the stage.
		"""
		self.ell.close()

	def connect(self):
		""" Connects to the stage.
		"""
		self.ell = Serial('COM5', baudrate=9600, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE,parity= PARITY_NONE, timeout=2)




		