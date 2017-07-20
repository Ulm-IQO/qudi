# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interfuse between Magnet Logic and Motor Hardware.

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
from interface.magnet_interface import MagnetInterface


class MagnetMotorInterfuse(GenericLogic, MagnetInterface):

    _modclass = 'MagnetMotorInterfuse'
    _modtype = 'interfuse'

    # declare connectors, here you can see the interfuse action: the in
    # connector will cope a motor hardware, that means a motor device can
    # connect to the in connector of the logic.
    motorstage = Connector(interface='MotorInterface')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # save the idle state in this class variable, since that is not present
        # in the actual motor hardware device. Use this variable to decide
        # whether movement commands are passed to the hardware.
        self._magnet_idle = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._motor_device = self.get_connector('motorstage')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_constraints(self):
        """ Retrieve the hardware constrains from the magnet driving device.

        @return dict: dict with constraints for the magnet hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.
        """
        return self._motor_device.get_constraints()


    def move_rel(self, param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        A smart idea would be to ask the position after the movement.
        """

        if not self._magnet_idle:
            self._motor_device.move_rel(param_dict)
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "move_rel" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state(False)" '
                    'to have control over its movement.')
        return param_dict


    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        if not self._magnet_idle:
            self._motor_device.move_abs(param_dict)
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "move_abs" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state (False)" '
                    'to have control over its movement.')
        return param_dict


    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self._motor_device.abort()
        return 0


    def get_pos(self, param_list=None):
        """ Gets current position of the stage

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        return self._motor_device.get_pos(param_list)


    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        return self._motor_device.get_status(param_list)


    def calibrate(self, param_list=None):
        """ Calibrates the stage.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.

        @return int: error code (0:OK, -1:error)

        After calibration the stage moves to home position which will be the
        zero point for the passed axis. The calibration procedure will be
        different for each stage.
        """
        if not self._magnet_idle:
            self._motor_device.calibrate(param_list)
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "calibrate" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state(False)" '
                    'to have control over its movement.')

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict: with the axis label as key and the velocity as item.
        """
        return self._motor_device.get_velocity(param_list)


    def set_velocity(self, param_dict=None):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        if not self._magnet_idle:
            self._motor_device.set_velocity(param_list)
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "set_velocity" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state(False)" '
                    'to have control over its movement.')
        return param_dict


    def tell(self, param_dict=None):
        """ Send a command to the magnet.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the command string>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('You can tell the motor dummy as much as you want, it '
                'has always an open ear for you. But do not expect an '
                'answer, it is very shy!')
        return param_dict

    def ask(self, param_dict=None):
        """ Ask the magnet a question.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the question string>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return dict: contains the answer to the specific axis coming from the
                      magnet. Keywords are the axis names, item names are the
                      string answers of the axis.
        """

        self.log.info('The Motor Hardware does not support an "ask" command '
                'and is not be able to answer the questions "{0}" to the '
                'axis "{1}"! If you want to talk to someone ask Siri, maybe '
                'she will listen to you and answer your questions '
                ':P.'.format(list(param_dict.values()), list(param_dict)))

        return_val = {}
        for entry in param_dict:
            return_val[entry] = 'Nothing to say, Motor is quite.'

        return return_val


    def initialize(self):
        """
        Acts as a switch. When all coils of the superconducting magnet are
        heated it cools them, else the coils get heated.
        @return int: (0: Ok, -1:error)
        """
        self.log.info('Motor Hardware does not need initialization for '
                'starting or ending a movement. Nothing will happen.')
        return 0


    def set_magnet_idle_state(self, magnet_idle=True):
        """ Set the magnet to couple/decouple to/from the control.

        @param bool magnet_idle: if True then magnet will be set to idle and
                                 each movement command will be ignored from the
                                 hardware file. If False the magnet will react
                                 on movement changes of any kind.

        @return bool: the actual state which was set in the magnet hardware.
                        True = idle, decoupled from control
                        False = Not Idle, coupled to control
        """

        self._magnet_idle = magnet_idle
        return self._magnet_idle


    def get_magnet_idle_state(self):
        """ Retrieve the current state of the magnet, whether it is idle or not.

        @return bool: the actual state which was set in the magnet hardware.
                        True = idle, decoupled from control
                        False = Not Idle, coupled to control
        """

        return self._magnet_idle



