# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class control spectrometer camera.

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

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt

from core.module import Connector
from core.util.mutex import Mutex
from core.util.network import netobtain
from logic.generic_logic import GenericLogic


class SpectroCameraLogic(GenericLogic):

    """This logic module interact with the a camera, and is design for spectrometer camera.
    """

    _modclass = 'spectrocameralogic'
    _modtype = 'logic'

    # declare connectors
    camera = Connector(interface='SpectrometerCameraInterface')
    savelogic = Connector(interface='SaveLogic')

    def __init__(self, **kwargs):
        """ Create object with connectors.
          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._data_FVB = np.array([])
        self._data_FHB = np.array([])
        self._data_image = np.array([])

        self._camera = self.spectro_camera()
        self._save_logic = self.savelogic()

        self.camera_name = self._camera.get_name()


        self.log.debug('Logic connected to camera '+self.camera_name)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            pass


    def get_constraints(self):
        self._camera.get_constraints()

    def set_read_mode(self, mode):
        return self._camera.set_read_mode(mode)

    def get_read_mode(self):
        return self._camera.get_read_mode()

    def set_exposure(self, time):
        return self._camera.set_exposure(time)
    def get_exposure(self):
        return self._camera.get_exposure()

    def set_cooler_on_state(self, on_state):
        return self._camera.set_cooler_on_state(on_state)
    def get_cooler_on_state(self):
        return self._camera.get_cooler_on_state()

    def get_measured_temperature(self):
        return self._camera.get_measured_temperature()

    def set_setpoint_temperature(self, temperature):
        return self._camera.set_setpoint_temperature(temperature)

    def get_setpoint_temperature(self):
        return self._camera.get_setpoint_temperature()

    def get_ready_state(self):
        return self._camera.get_ready_state()

