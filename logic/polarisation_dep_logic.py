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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
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
    _in = { 'counterlogic': 'CounterLogic',
            'savelogic': 'SaveLogic',
            'motor':'MotorInterface'
            }
    _out = {'polarisationdeplogic': 'PolarisationDepLogic'}

    signal_rotation_finished = QtCore.Signal()
    signal_start_rotation = QtCore.Signal()

    def on_activate(self,e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """

        self._counter_logic = self.connector['in']['counterlogic']['object']
#        print("Counting device is", self._counting_device)

        self._save_logic = self.connector['in']['savelogic']['object']

        self._hwpmotor = self.connector['in']['motor']['object']

        # Initialise measurement parameters
        self.scan_length = 360
        self.scan_speed = 10 #not yet used

        # Connect signals
        self.signal_rotation_finished.connect(self.finish_scan, QtCore.Qt.QueuedConnection)
        self.signal_start_rotation.connect(self.rotate_polarisation, QtCore.Qt.QueuedConnection)


    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
        return

    def measure_polarisation_dependence(self):
        """Do a simple pol dep measurement.
        """

        # Set up measurement
        self._hwpmotor.move_abs(0)

        # configure the countergui


        self._counter_logic.start_saving()
        self.signal_start_rotation.emit()

    def rotate_polarisation(self):
        self._hwpmotor.move_rel(self.scan_length)
        self.log.info('rotation finished, saving data')
        self.signal_rotation_finished.emit()

    def finish_scan(self):
        self._counter_logic.save_data()
#        self._counter_logic.stopCount()
