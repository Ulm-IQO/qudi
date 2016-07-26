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

class PIDLogic(GenericLogic, PIDControllerInterface):
    """
    Controll a process via software PID.
    """
    _modclass = 'pidlogic'
    _modtype = 'logic'
    ## declare connectors
    _in = {
        'process': 'ProcessInterface',
        'control': 'ProcessControlInterface',
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
        self._process = self.connector['in']['process']['object']
        self._control = self.connector['in']['control']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self.previousdelta = 0
        self.cv = self._control.getControlValue()

        config = self.getConfiguration()
        if 'timestep' in config:
            self.timestep = config['timestep']
        else:
            self.timestep = 0.1
            self.log.warning('No time step configured, using 100ms.')

        # load parameters stored in app state store
        if 'kP' in self._statusVariables:
            self.kP = self._statusVariables['kP']
        else:
            self.kP = 1
        if 'kI' in self._statusVariables:
            self.kI = self._statusVariables['kI']
        else:
            self.kI = 1
        if 'kD' in self._statusVariables:
            self.kD = self._statusVariables['kD']
        else:
            self.kD = 1
        if 'setpoint' in self._statusVariables:
            self.setpoint = self._statusVariables['setpoint']
        else:
            self.setpoint = 273.15
        #if 'enable' in self._statusVariables:
        #    self.enable = self._statusVariables['enable']
        #else:
        #    self.enable = False
        if 'manualvalue' in self._statusVariables:
            self.manualvalue = self._statusVariables['manualvalue']
        else:
            self.manualvalue = 0
        if 'bufferLength' in self._statusVariables:
            self.bufferLength = self._statusVariables['bufferLength']
        else:
            self.bufferLength = 1000
        self.sigNextStep.connect(self._calcNextStep, QtCore.Qt.QueuedConnection)
        self.sigNewValue.connect(self._control.setControlValue)
        self.history = np.zeros([3, self.bufferLength])
        self.savingState = False
        self.enable = False
        self.integrated = 0
        self.countdown = 2

        self.sigNextStep.emit()

    def deactivation(self, e):
        """ Perform required deactivation. """

        # save parameters stored in app state store
        self._statusVariables['kP'] = self.kP
        self._statusVariables['kI'] = self.kI
        self._statusVariables['kD'] = self.kD
        self._statusVariables['setpoint'] = self.setpoint
        self._statusVariables['enable'] = self.enable
        self._statusVariables['bufferLength'] = self.bufferLength

    def _calcNextStep(self):
        """ This function implements the Takahashi Type C PID
            controller: the P and D term are no longer dependent
             on the set-point, only on PV (which is Thlt).
             The D term is NOT low-pass filtered.
             This function should be called once every TS seconds.
        """
        self.pv = self._process.getProcessValue()

        if self.countdown > 0:
            self.countdown -= 1
            self.previousdelta = self.setpoint - self.pv
            print('Countdown: ', self.countdown)
        elif self.countdown == 0:
            self.countdown = -1
            self.integrated = 0
            self.enable = True

        if (self.enable):
            delta = self.setpoint - self.pv
            self.integrated += delta
            ## Calculate PID controller:
            self.P = self.kP * delta
            self.I = self.kI * self.timestep * self.integrated
            self.D = self.kD / self.timestep * (delta - self.previousdelta)

            self.cv += self.P + self.I + self.D
            self.previousdelta = delta

            ## limit contol output to maximum permissible limits
            limits = self._control.getControlLimits()
            if (self.cv > limits[1]):
                self.cv = limits[1]
            if (self.cv < limits[0]):
                self.cv = limits[0]

            self.history = np.roll(self.history, -1, axis=1)
            self.history[0, -1] = self.pv
            self.history[1, -1] = self.cv
            self.history[2, -1] = self.setpoint
            self.sigNewValue.emit(self.cv)
        else:
            self.cv = self.manualvalue
            limits = self._control.getControlLimits()
            if (self.cv > limits[1]):
                self.cv = limits[1]
            if (self.cv < limits[0]):
                self.cv = limits[0]
            self.sigNewValue.emit(self.cv)

        time.sleep(self.timestep)
        self.sigNextStep.emit()

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

