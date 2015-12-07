# -*- coding: utf-8 -*-
# unstable: Christoph Müller

"""
This file contains the QuDi Logic module base class.

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

Copyright (C) 2015 Christoph Müller christoph-2.mueller@uni-ulm.de
Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
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
        'process': 'ProcessInterface',
        'control': 'ProcessControlInterface',
        'savelogic': 'SaveLogic'
        }
    _out = {'pidlogic': 'ODMRLogic'}

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
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #number of lines in the matrix plot
        self.NumberOfSecondsLog = 100
        self.threadlock = Mutex()

    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self._process = self.connector['in']['process']['object']
        self._control = self.connector['in']['control']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self.previous = [0, 0]
        self.cv = self._control.getControlValue()

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
        if 'enable' in self._statusVariables:
            self.enable = self._statusVariables['enable']
        else:
            self.enable = False

        self.sigNextStep.connect(self._calcNextStep, QtCore.Qt.QueuedConnection)
        self.sigNewValue.connect(self._control.setControlValue)
        self.sigNextStep.emit()

    def deactivation(self, e):
        """ Perform required deactivation. """

        # save parameters stored in app state store
        self._statusVariables['kP'] = self.kP
        self._statusVariables['kI'] = self.kI
        self._statusVariables['kD'] = self.kD
        self._statusVariables['setpoint'] = self.setpoint
        self._statusVariables['enable'] = self.enable

    def _calcNextStep(self):
        """ This function implements the Takahashi Type C PID
            controller: the P and D term are no longer dependent
             on the set-point, only on PV (which is Thlt).
             The D term is NOT low-pass filtered.
             This function should be called once every TS seconds.
        """
        pv = self._process.getProcessValue()
        
        if (self.enable):
            # calculate e[k] = SP[k] - PV[k]
            delta = self.setpoint - pv
            ## Calculate PID controller:
            ## y[k] = y[k-1] + kc * (PV[k-1] - PV[k] + Ts*e[k]/Ti + Td/Ts * (2*PV[k-1] - PV[k] - PV[k-2]))

            self.P = self.kP / self.timestep * (self.previous[0] - pv)
            self.I = self.kI / self.timestep * delta
            self.D = self.kD / self.timestep * (2.0 * self.previous[0] - self.previous[1] - pv)

            self.cv += self.P + self.I + self.D
            self.previous[1] = self.previous[0]
            self.previous[0] = pv

            ## limit contol output to maximum permissible limits
            limits = self._control.getControlLimits()
            if (self.cv > limits[1]):
                self.cv = limits[1]
            if (self.cv < limits[0]):
                self.cv = limits[0]

            self.sigNewValue.emit(self.cv)

        else:
            self.cv = 0.0
            self.P = 0.0
            self.I = 0.0
            self.D = 0.0
            self.previous = [0, 0]

        time.sleep(self.timestep)
        self.sigNextStep.emit()

