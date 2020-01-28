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
from core.util.mutex import Mutex
import numpy as np

from logic.generic_logic import GenericLogic
from interface.pid_controller_interface import PIDControllerInterface
from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar


class SoftPIDController(GenericLogic, PIDControllerInterface):
    """
    Control a process via software PID.
    """

    # declare connectors
    process = Connector(interface='ProcessInterface')
    control = Connector(interface='ProcessControlInterface')

    # config opt
    timestep = ConfigOption(default=100)

    # status vars
    kP = StatusVar(default=1)
    kI = StatusVar(default=1)
    kD = StatusVar(default=1)
    setpoint = StatusVar(default=273.15)
    manualvalue = StatusVar(default=0)

    sigNewValue = QtCore.Signal(float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key,config[key]))

        #number of lines in the matrix plot
        self.NumberOfSecondsLog = 100
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._process = self.process()
        self._control = self.control()

        self.previousdelta = 0
        self.cv = self._control.get_control_value()

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.timestep)

        self.timer.timeout.connect(self._calcNextStep, QtCore.Qt.QueuedConnection)
        self.sigNewValue.connect(self._control.set_control_value)

        self.history = np.zeros([3, 5])
        self.savingState = False
        self.enable = False
        self.integrated = 0
        self.countdown = 2

        self.timer.start(self.timestep)

    def on_deactivate(self):
        """ Perform required deactivation.
        """
        pass

    def _calcNextStep(self):
        """ This function implements the Takahashi Type C PID
            controller: the P and D term are no longer dependent
             on the set-point, only on PV (which is Thlt).
             The D term is NOT low-pass filtered.
             This function should be called once every TS seconds.
        """
        self.pv = self._process.get_process_value()

        if self.countdown > 0:
            self.countdown -= 1
            self.previousdelta = self.setpoint - self.pv
            print('Countdown: ', self.countdown)
        elif self.countdown == 0:
            self.countdown = -1
            self.integrated = 0
            self.enable = True

        if self.enable:
            delta = self.setpoint - self.pv
            self.integrated += delta
            ## Calculate PID controller:
            self.P = self.kP * delta
            self.I = self.kI * self.timestep * self.integrated
            self.D = self.kD / self.timestep * (delta - self.previousdelta)

            self.cv += self.P + self.I + self.D
            self.previousdelta = delta

            ## limit contol output to maximum permissible limits
            limits = self._control.get_control_limit()
            if self.cv > limits[1]:
                self.cv = limits[1]
            if self.cv < limits[0]:
                self.cv = limits[0]

            self.history = np.roll(self.history, -1, axis=1)
            self.history[0, -1] = self.pv
            self.history[1, -1] = self.cv
            self.history[2, -1] = self.setpoint
            self.sigNewValue.emit(self.cv)
        else:
            self.cv = self.manualvalue
            limits = self._control.get_control_limit()
            if self.cv > limits[1]:
                self.cv = limits[1]
            if self.cv < limits[0]:
                self.cv = limits[0]
            self.sigNewValue.emit(self.cv)

        self.timer.start(self.timestep)

    def startLoop(self):
        """ Start the control loop. """
        self.countdown = 2

    def stopLoop(self):
        """ Stop the control loop. """
        self.countdown = -1
        self.enable = False

    def getSavingState(self):
        """ Find out if we are keeping data for saving later.

            @return bool: whether module is saving process and control data
        """
        return self.savingState

    def startSaving(self):
        """ Start saving process and control data.

            Does not do anything right now.
        """
        pass

    def saveData(self):
        """ Write process and control data to file.

            Does not do anything right now.
        """
        pass

    def get_kp(self):
        """ Return the proportional constant.

            @return float: proportional constant of PID controller
        """
        return self.kP

    def set_kp(self, kp):
        """ Set the proportional constant of the PID controller.

            @prarm float kp: proportional constant of PID controller
        """
        self.kP = kp

    def get_ki(self):
        """ Get the integration constant of the PID controller

            @return float: integration constant of the PID controller
        """
        return self.kI

    def set_ki(self, ki):
        """ Set the integration constant of the PID controller.

            @param float ki: integration constant of the PID controller
        """
        self.kI = ki

    def get_kd(self):
        """ Get the derivative constant of the PID controller

            @return float: the derivative constant of the PID controller
        """
        return self.kD

    def set_kd(self, kd):
        """ Set the derivative constant of the PID controller

            @param float kd: the derivative constant of the PID controller
        """
        self.kD = kd

    def get_setpoint(self):
        """ Get the current setpoint of the PID controller.

            @return float: current set point of the PID controller
        """
        return self.setpoint

    def set_setpoint(self, setpoint):
        """ Set the current setpoint of the PID controller.

            @param float setpoint: new set point of the PID controller
        """
        self.setpoint = setpoint

    def get_manual_value(self):
        """ Return the control value for manual mode.

            @return float: control value for manual mode
        """
        return self.manualvalue

    def set_manual_value(self, manualvalue):
        """ Set the control value for manual mode.

            @param float manualvalue: control value for manual mode of controller
        """
        self.manualvalue = manualvalue
        limits = self._control.get_control_limit()
        if self.manualvalue > limits[1]:
            self.manualvalue = limits[1]
        if self.manualvalue < limits[0]:
            self.manualvalue = limits[0]

    def get_enabled(self):
        """ See if the PID controller is controlling a process.

            @return bool: whether the PID controller is preparing to or conreolling a process
        """
        return self.enable or self.countdown >= 0

    def set_enabled(self, enabled):
        """ Set the state of the PID controller.

            @param bool enabled: desired state of PID controller
        """
        if enabled and not self.enable and self.countdown == -1:
            self.startLoop()
        if not enabled and self.enable:
            self.stopLoop()

    def get_control_limits(self):
        """ Get the minimum and maximum value of the control actuator.

            @return list(float): (minimum, maximum) values of the control actuator
        """
        return self._control.get_control_limit()

    def set_control_limits(self, limits):
        """ Set the minimum and maximum value of the control actuator.

            @param list(float) limits: (minimum, maximum) values of the control actuator

            This function does nothing, control limits are handled by the control module
        """
        pass

    def get_control_value(self):
        """ Get current control output value.

            @return float: control output value
        """
        return self.cv

    def get_control_unit(self):
        return self._control.get_control_unit()

    def get_process_value(self):
        """ Get current process input value.

            @return float: current process input value
        """
        return self.pv

    def get_process_unit(self):
        return self._control.get_process_unit()

    def get_extra(self):
        """ Extra information about the controller state.

            @return dict: extra informatin about internal controller state

            Do not depend on the output of this function, not every field
            exists for every PID controller.
        """
        return {
            'P': self.P,
            'I': self.I,
            'D': self.D
        }
