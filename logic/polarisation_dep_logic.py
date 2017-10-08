# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class for performing polarisation dependence measurements.

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

from core.module import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class PolarisationDepLogic(GenericLogic):
    """This logic module rotates polarisation and records signal as a function of angle.

    """

    _modclass = 'polarisationdeplogic'
    _modtype = 'logic'

    ## declare connectors
    counterlogic = Connector(interface='CounterLogic')
    savelogic = Connector(interface='SaveLogic')
    motor = Connector(interface='MotorInterface')

    signal_rotation_finished = QtCore.Signal()
    signal_start_rotation = QtCore.Signal()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._counter_logic = self.get_connector('counterlogic')
#        print("Counting device is", self._counting_device)

        self._save_logic = self.get_connector('savelogic')

        self._hwpmotor = self.get_connector('motor')

        # Initialise measurement parameters
        self.scan_length = 360
        self.scan_speed = 10 #not yet used

        # Connect signals
        self.signal_rotation_finished.connect(self.finish_scan, QtCore.Qt.QueuedConnection)
        self.signal_start_rotation.connect(self.rotate_polarisation, QtCore.Qt.QueuedConnection)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
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
