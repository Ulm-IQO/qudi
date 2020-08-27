# -*- coding: utf-8 -*-

"""
This module controls Newport CONEX-controlled Agilis stages.

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

import serial
from collections import OrderedDict

from core.module import Base
from core.configoption import ConfigOption
from interface.motor_interface import MotorInterface


class MotorNewportConexAGP(Base, MotorInterface):
    """
    Module for the CONEX-AGP controller for Agilis stages sold by Newport.

    The controller takes commands of the form xxAAnn over a serial connection,
    where xx is the controller address and nn can be a value to be set or a question mark
    to get the value or it can be missing.


    Example config for copy-paste:

    newport_conex_agp:
        module.Class: 'motor.motor_newport_conex_agp.MotorNewportConexAGP'
        com_port: 'COM1'
        controller_address: 1
        axis_label: 'phi'

    """

    _com_port = ConfigOption('com_port', missing='error')
    _controller_address = ConfigOption('controller_address', 1, missing='warn')

    _axis_label = ConfigOption('axis_label', 'phi', missing='warn')

    vel_from_model = {
        'AG-PR100P': 1.5,
        'AG-GON-UP': 0.45,
        'AG-GON-LP': 0.33,
        'AG-LS25-27P': 0.4,
    }

    unit_from_model = {
        'AG-PR100P': '°',
        'AG-GON-UP': '°',
        'AG-GON-LP': '°',
        'AG-LS25-27P': 'mm',
    }

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._serial_connection = serial.Serial(
            port=self._com_port,
            baudrate=921600,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=True)

        model, pn, ud = self.query('ID').split('_')
        controller, fw_ver = self.query('VE').split()
        self.log.info('Stage {0} {1} {2} on controller {3} firmware {4}'
                      ''.format(model, pn, ud, controller, fw_ver))
        self._min_pos = float(self.query('SL'))
        self._max_pos = float(self.query('SR'))
        self._velocity = self.vel_from_model[model]
        self._axis_unit = self.unit_from_model[model]
        self._min_step = float(self.query('DB'))
        self.log.info('Limits: {0}{2} to {1}{2}'
                      ''.format(self._min_pos, self._max_pos, self._axis_unit))

        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._serial_connection.close()
        return 0

    def query(self, command):
        """ Get a variable from the controller
            @param command: two-letter command for controller

            @return str: answer from controller
        """
        cmd = '{0:02d}{1:s}?\r\n'.format(self._controller_address, command).encode('ascii')
        self._serial_connection.write(cmd)
        ret = self._serial_connection.read_until(b'\r\n')
        if cmd[0:4] != ret[0:4]:
            self.log.error('Command {0} preamble not equal to reply {1} preamble'
                           ''.format(cmd.decode('ascii'), ret.decode('ascii')))
        return ret[4:].decode('ascii').rstrip()

    def write_value(self, command, value):
        """ Write a value to the controller

        @param command: two-letter command/variable for controller
        @param value: value to write to controller
        """
        cmd = '{0:02d}{1:s}{2}\r\n'.format(self._controller_address, command, value).encode('ascii')
        self._serial_connection.write(cmd)

    def write(self, command):
        """ Write a single command

        @param command: two-letter command for controller
        """
        cmd = '{0:02d}{1:s}\r\n'.format(self._controller_address, command).encode('ascii')
        self._serial_connection.write(cmd)

    def read(self):
        """ Read an answer from the controller

        @return str:
        """
        ret = self._serial_connection.read_until(b'\r\n')
        return ret[4:].decode('ascii').rstrip()

    def read_error(self):
        """

        @return bool, str:
        """
        err = self.query('TE')
        if len(err) > 0 and err[0] != '@':
            self.write_value('TB', err[0])
            err_str = self.read()
            self.log.error('Motor Error {0}'.format(err_str))
            return True, err_str
        return False, ''

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = OrderedDict()

        axis = {
            'label': self._axis_label,
            'ID': None,
            'unit': self._axis_unit,
            'ramp': None,
            'pos_min': self._min_pos,
            'pos_max': self._max_pos,
            'pos_step': self._min_step,
            'vel_min': self._velocity,
            'vel_max': self._velocity,
            'vel_step': self._velocity,
            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }

        # assign the parameter container to a name which will identify it
        constraints[axis['label']] = axis
        return constraints

    def move_rel(self, param_dict):
        """Moves stage by a given angle (relative movement)

        @param dict param_dict: Dictionary with axis name and relative movement in units

        @return dict: Dictionary with axis name and final position in units
        """
        if self._axis_label in param_dict:
            rel = param_dict[self._axis_label]
            self.write_value('PR', rel)
            self.read_error()
            pos = float(self.query('TH'))
            return {self._axis_label: pos}

        return {}

    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        if self._axis_label in param_dict:
            rel = param_dict[self._axis_label]
            self.write_value('PA', rel)
            self.read_error()
            pos = float(self.query('TH'))
            return {self._axis_label: pos}

        return {}

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self.write('ST')
        if self.read_error()[0]:
            return -1
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the rotation stage

        @param list param_list: List with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if param_list is None:
            param_list = [self._axis_label]

        if self._axis_label in param_list:
            pos = float(self.query('TP'))
            self.read_error()
            return {self._axis_label: pos}

        return {}

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict status:
        """
        self.read_error()
        st = self.query('TS')
        err = int(st, 16)
        return {self._axis_label: err}

    def calibrate(self, param_list=None):
        """ Calibrates the rotation motor

        @param list param_list: Dictionary with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if param_list is None:
            param_list = [self._axis_label]

        if self._axis_label in param_list:
            self.write('OR')
            self.read_error()
            pos = float(self.query('TH'))
            return {self._axis_label: pos}

        return {}

    def get_velocity(self, param_list=None):
        """ Asks current value for velocity.

        @param list param_list: Dictionary with axis name

        @return dict velocity: Dictionary with axis name and velocity in deg/s
        """
        if param_list is None:
            param_list = [self._axis_label]

        if self._axis_label in param_list:
            return {self._axis_label: self._velocity}

        return {}

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: Dictionary with axis name and target velocity in deg/s

        @return dict velocity: Dictionary with axis name and target velocity in deg/s
        """
        if self._axis_label in param_dict:
            return {self._axis_label: self._velocity}

        return {}

    def reset(self):
        """ Reset the controller.
            Afterwards, moving to the home position with calibrate() is necessary.
        """
        self.write('RS')
