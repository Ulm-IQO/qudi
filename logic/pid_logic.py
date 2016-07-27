# -*- coding: utf-8 -*-

"""
A module for controlling processes via PID regulation.

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
from interface.pid_controller_interface import PIDControllerInterface
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime

class PIDLogic(GenericLogic):
    """
    Controll a process via software PID.
    """
    _modclass = 'pidlogic'
    _modtype = 'logic'
    ## declare connectors
    _in = {
        'controller': 'PIDControllerInterface',
        'savelogic': 'SaveLogic'
        }
    _out = {'pidlogic': 'PIDLogic'}

    sigNextStep = QtCore.Signal()
    sigNewValue = QtCore.Signal(float)

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

        #number of lines in the matrix plot
        self.NumberOfSecondsLog = 100
        self.threadlock = Mutex()

    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self._controller = self.connector['in']['controller']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self.previousdelta = 0
        self.cv = self._control.getControlValue()

        config = self.getConfiguration()
        # load parameters stored in app state store
        if 'bufferLength' in self._statusVariables:
            self.bufferLength = self._statusVariables['bufferLength']
        else:
            self.bufferLength = 1000
        self.history = np.zeros([3, self.bufferLength])
        self.savingState = False

    def deactivation(self, e):
        """ Perform required deactivation. """

        # save parameters stored in app state store
        self._statusVariables['bufferLength'] = self.bufferLength

    def getBufferLength(self):
        return self.bufferLength

    def startLoop(self):
        self.countdown = 2

    def stopLoop(self):
        self.countdown = -1
        self.enable = False

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
        return self.kP

    def set_kp(self, kp):
        self.kP = kp

    def get_ki(self):
        return self.kI

    def set_ki(self, ki):
        self.kI = ki

    def get_kd(self):
        return self.kD

    def set_kd(self, kd):
        self.kD = kd

    def get_setpoint(self):
        return self.setpoint

    def set_setpoint(self, setpoint):
        self.setpoint = setpoint

    def get_manual_value(self):
        return self.manualvalue

    def set_manual_value(self, manualvalue):
        self.manualvalue = manualvalue
        limits = self._control.getControlLimits()
        if (self.manualvalue > limits[1]):
            self.manualvalue = limits[1]
        if (self.manualvalue < limits[0]):
            self.manualvalue = limits[0]

    def get_enabled(self):
        return self.enable

    def set_enabled(self, enabled):
        if enabled and not self.enable and self.countdown == -1:
            self.startLoop()
        if not enabled and self.enable:
            self.stopLoop()

    def get_control_limits(self):
        return self._control.getControlLimits()

    def set_control_limits(self, limits):
        pass

