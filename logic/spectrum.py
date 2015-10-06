# -*- coding: utf-8 -*-
"""
This file contains the QuDi couner logic class.

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

Copyright (C) 2015 Kay D. Jahnke
Copyright (C) 2015 Alexander Stark
Copyright (C) 2015 Jan M. Binder
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime


class SpectrumLogic(GenericLogic):
    """This logic module gathers data from the spectrometer.
    """

    sig_data_updated = QtCore.Signal()
    sig_update_spectrum_plot = QtCore.Signal(bool)

    _modclass = 'spectrumlogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'spectrometer': 'SpectrometerInterface'
            }
    _out = {'spectrumlogic': 'SpectrumLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create SpectrometerLogic object with connectors.

          @param object manager: Manager object that loaded this module
          @param str name: unique module name
          @param dict config: module configuration
          @param dict kwargs: optional parameters
        """
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()



    def activation(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """
        self.spectrum_data = np.array([])

        self._spectrometer_device = self.connector['in']['spectrometer']['object']

        #self._save_logic = self.connector['in']['savelogic']['object']



    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
        if self.getState() != 'idle' and self.getState() != 'deactivated':
            pass
        

    def get_spectrum(self):
         self.spectrum_data = self._spectrometer_device.recordSpectrum()

    def save_raw_spectrometer_file(self, path = '', postfix = '' ):
        """Ask the hardware device to save its own raw file.
        """
        #TODO: sanity check the passed parameters.

        self._spectrometer_device.saveSpectrum( path, postfix = postfix )
