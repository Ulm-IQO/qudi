# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic class for performing polarisation dependence measurements.

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

Copyright (C) 2016 Lachlan J. Rogers lachlan.rogers@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
import numpy as np
import time
import datetime

class PolarisationDepLogic(GenericLogic):
    """This logic module rotates polarisation and records signal as a function of angle.

    """

    _modclass = 'polarisationdeplogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'counter1': 'SlowCounterInterface',
            'savelogic': 'SaveLogic',
            'motor':'MotorInterface'
            }
    _out = {'polarisationdeplogic': 'PolarisationDepLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create CounterLogic object with connectors.

          @param object manager: Manager object thath loaded this module
          @param str name: unique module name
          @param dict config: module configuration
          @param dict kwargs: optional parameters
        """
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

    def activation(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """

        self._counting_device = self.connector['in']['counter1']['object']
#        print("Counting device is", self._counting_device)

        self._save_logic = self.connector['in']['savelogic']['object']

        self._hwpmotor = self.connector['in']['motor']['object']



    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
        return
 
    def measure_polarisation_dependence(self):
        """Do a simple pol dep measurement.
        """

        self._hwpmotor.move_abs(0)
