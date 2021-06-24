# -*- coding: utf-8 -*-

import os
from core.module import Base
from serial import Serial, EIGHTBITS,STOPBITS_ONE,PARITY_NONE


class ThorlabsRotationMount(Base):
	""" This class implements communication with the Rotation Mount ELL14.

	Example config for copy-paste:

	--- TODO: PUT IT HERE ---

	"""
	revelation = 262144
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def on_activate(self):
		""" Activate module.
		"""
		pass

	def on_deactivate(self):
		""" Disconnect from hardware on deactivation.
		"""
		pass

	def connect(self):
		""" Connects to the stage.
		"""
		self.ell = Serial('COM5', baudrate=9600, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE,parity= PARITY_NONE, timeout=2)pass

	def move_forward(self):
		self.ell.write(b'0fw')
		return self.ell.read(32)

	def get_info(self):
		self.ell.write(b'0in')
		return self.ell.read(32)

	def disconnect(self):
		""" Disconnects from the stage.
		"""
		pass

	def home(self):
		""" Homes the rotation mount.
		"""
		self.ell.write(b'0ho0')
		self.ell.read(32)

	def get_pos(self):
		""" Returns the current position of the stage. In degree angle
		"""
		self.ell.write(b'0gp')
		pos16 = self.ell.read(32)
		pos10 = int("".join(filter(lambda x: x not in "brn\\'", str(pos16)))[3:], 16)
		#revelation = 262144
		angle = 360 * pos10 / self.revelation
		return angle


	def move_abs(self, to_angle):
		""" Moves stage to absolute position.
		"""
		to_pos10 = int(to_angle * (self.revelation/ 360))
		to_pos16 = str(hex(to_pos10))[2:].upper().zfill(8)
		command = ("0ma" + to_pos16).encode('ascii')
		self.ell.write(command)

	def move_rel(self, angle):
		""" Moves stage by relative angle.
		"""
		to_pos10 = int(angle * (self.revelation/ 360))
		to_pos16 = str(hex(to_pos10))[2:].upper().zfill(8)
		command = ("0mr" + to_pos16).encode('ascii')
		self.ell.write(command)

	def get_jog_size(self):
		self.ell.write(b'0gj')
		return self.ell.read(32)

	def set_jog_size(self, angle):
		to_pos10 = int(angle * (self.revelation/ 360))
		to_pos16 = str(hex(to_pos10))[2:].upper().zfill(8)
		command = ("0sj" + to_pos16).encode('ascii')
		self.ell.write(command)