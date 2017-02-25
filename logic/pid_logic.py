# -*- coding: utf-8 -*-

"""
A module for controlling processes via PID regulation.

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
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


class PIDLogic(GenericLogic):
    """
    Controll a process via software PID.
    """
    _modclass = 'pidlogic'
    _modtype = 'logic'
    ## declare connectors
    _connectors = {
        'controller': 'PIDControllerInterface',
        'savelogic': 'SaveLogic'
    }

    sigUpdateDisplay = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

        #number of lines in the matrix plot
        self.NumberOfSecondsLog = 100
        self.threadlock = Mutex()

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.
        """
        self._controller = self.get_connector('controller')
        self._save_logic = self.get_connector('savelogic')

        config = self.getConfiguration()

        # load parameters stored in app state store
        if 'bufferlength' in self._statusVariables:
            self.bufferLength = self._statusVariables['bufferlength']
        else:
            self.bufferLength = 1000

        if 'timestep' in self._statusVariables:
            self.timestep = self._statusVariables['timestep']
        else:
            self.timestep = 100

        self.history = np.zeros([3, self.bufferLength])
        self.savingState = False
        self.enabled = False
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.timestep)
        self.timer.timeout.connect(self.loop)

    def on_deactivate(self, e):
        """ Perform required deactivation. """

        # save parameters stored in ap state store
        self._statusVariables['bufferlength'] = self.bufferLength
        self._statusVariables['timestep'] = self.timestep

    def getBufferLength(self):
        return self.bufferLength

    def startLoop(self):
        self.enabled = True
        self.timer.start(self.timestep)

    def stopLoop(self):
        self.enabled = False

    def loop(self):
        self.history = np.roll(self.history, -1, axis=1)
        self.history[0, -1] = self._controller.get_process_value()
        self.history[1, -1] = self._controller.get_control_value()
        self.history[2, -1] = self._controller.get_setpoint()
        self.sigUpdateDisplay.emit()
        if self.enabled:
            self.timer.start(self.timestep)

    def getSavingState(self):
        return self.savingState

    def startSaving(self):
        pass

    def saveData(self):
        pass

    def setSetpoint(self, newSetpoint):
        self.setpoint = newSetpoint

    def setBufferLength(self, newBufferLength):
        self.bufferLength = newBufferLength
        self.history = np.zeros([3, self.bufferLength])

    def get_kp(self):
        return self._controller.get_kp()

    def set_kp(self, kp):
        return self._controller.set_kp(kp)


    def get_ki(self):
        return self._controller.get_ki()

    def set_ki(self, ki):
        return self._controller.set_ki(ki)

    def get_kd(self):
        return self._controller.get_kd()

    def set_kd(self, kd):
        return self._controller.set_kd(kd)

    def get_setpoint(self):
        return self.history[2, -1]

    def set_setpoint(self, setpoint):
        self._controller.set_setpoint(setpoint)

    def get_manual_value(self):
        return self._controller.get_manual_value()

    def set_manual_value(self, manualvalue):
        return self._controller.set_manual_value(manualvalue)

    def get_enabled(self):
        return self.enabled

    def set_enabled(self, enabled):
        if enabled and not self.enabled:
            self.startLoop()
        if not enabled and self.enabled:
            self.stopLoop()

    def get_control_limits(self):
        return self._controller.get_control_limits()

    def set_control_limits(self, limits):
        return self._controller.set_control_limits(limits)

    def get_pv(self):
        return self.history[0, -1]

    def get_cv(self):
        return self.history[1, -1]
