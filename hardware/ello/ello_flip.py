# -*- coding: utf-8 -*-

import os
from serial import Serial, EIGHTBITS,STOPBITS_ONE,PARITY_NONE


class ThorlabsElloFlipper():
	
	def __init__(self, port, ell=None):
		if ell is None:
			self.connect()
		else:
			self.ell = ell

	def disconnect(self):
		self.ell.close()

	def connect(self):
		""" Connects to the stage.
		"""
		self.ell = Serial('COM5', baudrate=9600, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE,parity= PARITY_NONE, timeout=2)

	def move_forward(self):
		self.ell.write(bytes(f"{self._port}fw", 'ascii'))
		return self.ell.read(32)

	def get_info(self):
		self.ell.write(bytes(f"{self._port}in", 'ascii'))
		return self.ell.read(32)

	def home(self):
		""" Homes the rotation mount.
		"""
		self.ell.write(bytes(f"{self._port}ho0", 'ascii'))
		self.ell.read(32)

	def get_pos(self):
		""" Returns the current position of the stage. In degree angle
		"""
		ell.write(bytes(f"{_port}gp", 'ascii'))
		pos16 = ell.read(32)
		pos10 = int("".join(filter(lambda x: x not in "brn\\'", str(pos16)))[3:], 16)
		return 1 if pos16 > 0 else 0