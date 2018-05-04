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

import numpy as np

from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class PIDLogic(GenericLogic):
    """
    Control a process via software PID.
    """
    _modclass = 'pidlogic'
    _modtype = 'logic'

    ## declare connectors
    controller = Connector(interface='PIDControllerInterface')
    savelogic = Connector(interface='SaveLogic')
    _features = ConfigOption('features', ['PID_CONTROLLER'])
    # can include 'PID_CONTROLLER', 'SETPOINT_CONTROLLER', 'SETPOINT', 'PROCESS_VARIABLE' or 'PROCESS_CONTROL'
    # depending on what is available

    # status vars
    bufferLength = StatusVar('bufferlength', 1000)
    # TODO: Maybe the logic should keep everything (this should not be correlated with the GUI)
    
    _timestep = StatusVar(default=100)
    _loop_enabled = False

    # signals
    sigUpdateDisplay = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # number of lines in the matrix plot
        self.NumberOfSecondsLog = 100  # This breaks logic/GUI compartmentalisation
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._controller = self.controller()
        self._save_logic = self.savelogic()

        self.history = np.zeros([3, self.bufferLength])
        self.savingState = False

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self._timestep)
        self.timer.timeout.connect(self.loop)

        self.start_loop()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def getBufferLength(self):  #TODO: This breaks logic/GUI compartmentalisation (and naming conventions)
        """ Get the current data buffer length.
        """
        return self.bufferLength

    def setBufferLength(self, newBufferLength): #TODO: This breaks logic/GUI compartmentalisation (and naming conventions)
        """ Change buffer length to new value.

            @param int newBufferLength: new buffer length
        """
        self.bufferLength = newBufferLength
        self.history = np.zeros([3, self.bufferLength])

    def start_loop(self):
        """ Start the data acquisition loop.
        """
        self._loop_enabled = True
        self.timer.start(self._timestep)

    def stop_loop(self):
        """ Stop the data acquisition loop.
        """
        self._loop_enabled = False

    def loop(self):
        """ Execute step in the data acquisition loop: save one of each control and process values
        """
        self.history = np.roll(self.history, -1, axis=1)  # TODO : What is the efficiency of "roll storing" method on large array ?

        #TODO: only store activated info, hybrid for now
        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER', 'PROCESS_VARIABLE']).intersection(set(self._features)):
            self.history[0, -1] = self._controller.get_process_value()
        else:
            self.history[0, -1] = 0

        if set(['PID_CONTROLLER', 'PROCESS_VARIABLE']).intersection(set(self._features)):
            self.history[1, -1] = self._controller.get_control_value()
        else:
            self.history[1, -1] = 0

        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER', 'SETPOINT']).intersection(set(self._features)):
            self.history[2, -1] = self._controller.get_setpoint()
        else:
            self.history[2, -1] = 0

        self.sigUpdateDisplay.emit()
        if self._loop_enabled:
            self.timer.start(self._timestep)

    # TODO: to make the GUI happy for now, this could vary so this need to be redesigned
    def get_timestep(self):
        return self._timestep

    def get_features(self):
        return self._features

    def get_saving_state(self):
        """ Return whether we are saving data

            @return bool: whether we are saving data right now
        """
        return self.savingState

    def start_saving(self):
        """ Start saving data.

            Function does nothing right now.
        """
        pass

    def save_sata(self):
        """ Stop saving data and write data to file.

            Function does nothing right now.
        """
        pass

    # Beginning of features dependent methods :

    def get_kp(self):
        """ Return the proportional constant.

            @return float: proportional constant of PID controller
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.get_kp()
        else:
            return 0

    def set_kp(self, kp):
        """ Set the proportional constant of the PID controller.

            @prarm float kp: proportional constant of PID controller
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.set_kp(kp)
        else:
            return 0

    def get_ki(self):
        """ Get the integration constant of the PID controller

            @return float: integration constant of the PID controller
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.get_ki()
        else:
            return 0

    def set_ki(self, ki):
        """ Set the integration constant of the PID controller.

            @param float ki: integration constant of the PID controller
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.set_ki(ki)
        else:
            return 0

    def get_kd(self):
        """ Get the derivative constant of the PID controller

            @return float: the derivative constant of the PID controller
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.get_kd()
        else:
            return 0

    def set_kd(self, kd):
        """ Set the derivative constant of the PID controller

            @param float kd: the derivative constant of the PID controller
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.set_kd(kd)
        else:
            return 0

    def get_setpoint(self):
        """ Get the current setpoint of the controller.

            @return float: current set point of the controller
        """
        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER', 'SETPOINT']).intersection(set(self._features)):
            return self.history[2, -1]
        else:
            return 0

    def set_setpoint(self, setpoint):
        """ Set the current setpoint of the PID controller.

            @param float setpoint: new set point of the controller
        """
        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER', 'SETPOINT']).intersection(set(self._features)):
            return self._controller.set_setpoint(setpoint)
        else:
            return 0

    def get_enabled(self):
        """ See if the PID controller is controlling a process.

            @return bool: whether the PID controller is preparing to or conreolling a process
        """
        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER']).intersection(set(self._features)):
            return self._controller.get_enabled()
        else:
            return 0

    def set_enabled(self, enabled):
        """ Set the state of the PID controller.

            @param bool enabled: desired state of PID controller
        """
        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER']).intersection(set(self._features)):
            return self._controller.set_enabled(enabled)
        else:
            return 0

    def get_control_limits(self):
        """ Get the minimum and maximum value of the control actuator.

            @return list(float): (minimum, maximum) values of the control actuator
        """
        if set(['PID_CONTROLLER', 'PROCESS_CONTROL']).intersection(set(self._features)):
            return self._controller.get_control_limits()
        else:
            return 0

    def set_control_limits(self, limits):  # TODO: Should this be ok ?
        """ Set the minimum and maximum value of the control actuator.

            @param list(float) limits: (minimum, maximum) values of the control actuator

            This function does nothing, control limits are handled by the control module
        """
        if 'PID_CONTROLLER' in self._features:
            return self._controller.set_control_limits(limits)
        else:
            return 0

    def get_pv(self):
        """ Get current process input value.

            @return float: current process input value
        """
        if set(['PID_CONTROLLER', 'SETPOINT_CONTROLLER', 'PROCESS_VARIABLE']).intersection(set(self._features)):
            return self.history[0, -1]
        else:
            return 0

    def get_cv(self):
        """ Get current control output value.

            @return float: control output value
        """
        if set(['PID_CONTROLLER', 'PROCESS_CONTROL']).intersection(set(self._features)):
            return self.history[1, -1]
        else:
            return 0

    # TODO : What is that exactly ?
    def get_extra(self):
        if set(['PID_CONTROLLER']).intersection(set(self._features)):
            return self._controller.get_extra()
        else:
            return []

    # TODO: How does manual fit into all this ?
    def get_manual_value(self):
        """ Return the control value for manual mode.

            @return float: control value for manual mode
        """

        if 'PID_CONTROLLER' in self._features:
            return self._controller.get_manual_value()
        else:
            return 0

    def set_manual_value(self, manualvalue):
        """ Set the control value for manual mode.

            @param float manualvalue: control value for manual mode of controller
        """
        if self._type == 'PID_CONTROLLER':
            return self._controller.set_manual_value(manualvalue)
        else:
            return 0