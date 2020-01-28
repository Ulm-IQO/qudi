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
import time

from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class PIDLogic(GenericLogic):
    """
    Control a process via software PID.
    """

    # declare connectors
    controller = Connector(interface='PIDControllerInterface')
    savelogic = Connector(interface='SaveLogic')

    pid_name = ConfigOption('pid_name', 'process')
    save_to_metadata = ConfigOption('save_to_metadata', True)

    # status vars
    buffer_length = StatusVar('buffer_length', 1000)
    timestep = StatusVar(default=1)

    history = None

    # signals
    sigUpdateDisplay = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.history = np.zeros([3, self.buffer_length])
        self.saving_state = False
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.timestep*1e3)
        self.timer.timeout.connect(self.loop)
        self.loop()  # Get initial value without delay for GUI
        self.start_loop()

    def on_deactivate(self):
        """ Perform required deactivation. """
        if self.save_to_metadata:
            self.savelogic().remove_additional_parameter('{}'.format(self.pid_name))
            self.savelogic().remove_additional_parameter('{}_measured'.format(self.pid_name))
            self.savelogic().remove_additional_parameter('{}_control_variable'.format(self.pid_name))
            self.savelogic().remove_additional_parameter('{}_last_update'.format(self.pid_name))

    def get_buffer_length(self):
        """ Get the current data buffer length.
        """
        return self.buffer_length

    def set_buffer_length(self, value):
        """ Change buffer length to new value.

            @param int value: new buffer length
        """
        self.buffer_length = value
        self.history = np.zeros([3, self.buffer_length])

    def start_loop(self):
        """ Start the data recording loop.
        """
        self.module_state.run()
        self.timer.start(self.timestep*1e3)

    def stop_loop(self):
        """ Stop the data recording loop.
        """
        self.log.debug(self.module_state())
        self.module_state.stop()

    def loop(self):
        """ Execute step in the data recording loop: save one of each control and process values
        """
        self.history = np.roll(self.history, -1, axis=1)
        self.history[0, -1] = self.controller().get_process_value()
        self.history[1, -1] = self.controller().get_control_value()
        self.history[2, -1] = self.controller().get_setpoint()
        self.sigUpdateDisplay.emit()
        if self.module_state() == 'running':
            self.timer.start(self.timestep*1e3)
        if self.save_to_metadata:
            self.savelogic().update_additional_parameters({'{}'.format(self.pid_name): self.controller().get_setpoint()})
            self.savelogic().update_additional_parameters({'{}_measured'.format(self.pid_name):
                                                           self.controller().get_process_value()})
            self.savelogic().update_additional_parameters({'{}_control_variable'.format(self.pid_name):
                                                           self.controller().get_control_value()})
            self.savelogic().update_additional_parameters({'{}_last_update'.format(self.pid_name): time.time()})



    def get_saving_state(self):
        """ Return whether we are saving data

            @return bool: whether we are saving data right now
        """
        return self.saving_state

    def start_saving(self):
        """ Start saving data.

            Function does nothing right now.
        """
        pass

    def save_data(self):
        """ Stop saving data and write data to file.

            Function does nothing right now.
        """
        pass

    def get_extra(self):
        extra = self.controller().get_extra()
        extra = extra if extra is not None else {}
        return extra

    def get_kp(self):
        """ Return the proportional constant.

            @return float: proportional constant of PID controller
        """
        return self.controller().get_kp()

    def set_kp(self, kp):
        """ Set the proportional constant of the PID controller.

            @prarm float kp: proportional constant of PID controller
        """
        return self.controller().set_kp(kp)

    def get_ki(self):
        """ Get the integration constant of the PID controller

            @return float: integration constant of the PID controller
        """
        return self.controller().get_ki()

    def set_ki(self, ki):
        """ Set the integration constant of the PID controller.

            @param float ki: integration constant of the PID controller
        """
        return self.controller().set_ki(ki)

    def get_kd(self):
        """ Get the derivative constant of the PID controller

            @return float: the derivative constant of the PID controller
        """
        return self.controller().get_kd()

    def set_kd(self, kd):
        """ Set the derivative constant of the PID controller

            @param float kd: the derivative constant of the PID controller
        """
        return self.controller().set_kd(kd)

    def get_setpoint(self):
        """ Get the current setpoint of the PID controller.

            @return float: current set point of the PID controller
        """
        return self.history[2, -1]

    def set_setpoint(self, setpoint):
        """ Set the current setpoint of the PID controller.

            @param float setpoint: new set point of the PID controller
        """
        self.controller().set_setpoint(setpoint)

    def get_manual_value(self):
        """ Return the control value for manual mode.

            @return float: control value for manual mode
        """
        return self.controller().get_manual_value()

    def set_manual_value(self, manualvalue):
        """ Set the control value for manual mode.

            @param float manualvalue: control value for manual mode of controller
        """
        return self.controller().set_manual_value(manualvalue)

    def get_enabled(self):
        """ See if the PID controller is controlling a process.

            @return bool: whether the PID controller is preparing to or conreolling a process
        """
        return self.controller().get_enabled()

    def set_enabled(self, enabled):
        """ Set the state of the PID controller.

            @param bool enabled: desired state of PID controller
        """
        self.controller().set_enabled(enabled)

    def get_control_limits(self):
        """ Get the minimum and maximum value of the control actuator.

            @return list(float): (minimum, maximum) values of the control actuator
        """
        return self.controller().get_control_limits()

    def set_control_limits(self, limits):
        """ Set the minimum and maximum value of the control actuator.

            @param list(float) limits: (minimum, maximum) values of the control actuator

            This function does nothing, control limits are handled by the control module
        """
        return self.controller().set_control_limits(limits)

    def get_pv(self):
        """ Get current process input value.

            @return float: current process input value
        """
        return self.history[0, -1]

    def get_cv(self):
        """ Get current control output value.

            @return float: control output value
        """
        return self.history[1, -1]

    def get_process_unit(self):
        return self.controller().get_process_unit()

    def get_control_unit(self):
        return self.controller().get_control_unit()
