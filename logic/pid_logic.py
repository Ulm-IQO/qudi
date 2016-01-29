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

Copyright (C) 2015 - 2016 Jan M. Binder  <jan.binder@uni-ulm.de>
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime
import statistics

class PIDLogic(GenericLogic):
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

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), msgType='status')

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
        self.smoothpv = np.zeros(5)

        config = self.getConfiguration()
        if 'timestep' in config:
            self.timestep = config['timestep']
        else:
            self.timestep = 0.1
            self.logMsg('No time step configured, using 100ms', msgType='warn')

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
        self.countdown = 5

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
        self.smoothpv = np.roll(self.smoothpv, -1)
        self.smoothpv[-1] = self._process.getProcessValue()
        pv = statistics.mean(self.smoothpv)

        if self.countdown > 0:
            self.countdown -= 1
            self.previousdelta = self.setpoint - pv
            print('Countdown: ', self.countdown)
        elif self.countdown == 0:
            self.countdown = -1
            self.integrated = 0
            self.enable = True
        
        if (self.enable):
            delta = self.setpoint - pv
            self.integrated += delta 
            if self.integrated > 100:
                self.integrated = 100
            if self.integrated < -100:
                self.integrated = -100
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
            self.history[0, -1] = pv
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
        self.enable = False

    def getSavingState(self):
        return self.savingState

    def startSaving(self):
        pass

    def saveData(self):
        pass

    def getControlLimits(self):
        return self._control.getControlLimits()

    def setSetpoint(self, newSetpoint):
        self.setpoint = newSetpoint

    def setBufferLength(self, newBufferLength):
        self.bufferLength = newBufferLength
        self.history = np.zeros([3, self.bufferLength])

    def setManualValue(self, newManualValue):
        self.manualvalue = newManualValue
        limits = self._control.getControlLimits()
        if (self.manualvalue > limits[1]):
            self.manualvalue = limits[1]
        if (self.manualvalue < limits[0]):
            self.manualvalue = limits[0]

