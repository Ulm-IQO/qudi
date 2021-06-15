# -*- coding: utf-8 -*-

import os
from core.module import Base
from ctypes import CDLL


class ThorlabsRotationMount(Base):
	""" This class implements communication with the Rotation Mount ELL14.

	Example config for copy-paste:

	--- TODO: PUT IT HERE ---

	"""

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def on_activate(self):
		""" Activate module.
		"""
		this_dir = os.path.dirname(__file__) #-dll needs to be in same folder as this file
		prev_dir = os.getcwd()
		# goes to folder of DLL, loads it, goes back
		os.chdir(this_dir)
		self.rotation_mount_dll = CDLL("Thorlabs.Elliptec.ELLO_DLL.dll")
		os.chdir(prev_dir)


	def on_deactivate(self):
		""" Disconnect from hardware on deactivation.
		"""
		pass

	def connect(self):
		""" Connects to the stage.
		"""
		pass

	def disconnect(self):
		""" Disconnects from the stage.
		"""
		pass

	def home(self):
		""" Homes the rotation mount.
		"""
		pass

	def get_pos(self):
		""" Returns the current position of the stage.
		"""
		pass

	def move_abs(self):
		""" Moves stage to absolute position.
		"""
		pass

	def move_rel(self):
		""" Moves stage by relative angle.
		"""
		pass
