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


"""
An interfuse file is indented to fuse/combine a logic with a hardware, which
was not indented to be used with the logic. The interfuse file extend the
ability of a hardware file by converting the logic calls (from a different
interface) to the interface commands, which suits the hardware.
In order to be addressed by the (magnet) logic it should inherit the (magnet)
interface, and given the fact that it will convert a magnet logic call to a
motor hardware call, that 'interfuse' file has to stick to the interfaces
methods of the motor interface.

Reimplement each call from the magnet interface and use only the motor interface
command to talk to a xyz motor hardware and a rotational motor hardware.
"""

from core.module import Connector
from logic.generic_logic import GenericLogic
from interface.magnet_interface import MagnetInterface


class MagnetMotorXYZROTInterfuse(GenericLogic, MagnetInterface):

    _modclass = 'MagnetMotorXYZROTInterfuse'
    _modtype = 'interfuse'

    # declare connectors, here you can see the interfuse action: the in
    # connector will cope a motor hardware, that means a motor device can
    # connect to the in connector of the logic.
    motorstage_xyz = Connector(interface='MotorInterface')
    motorstage_rot = Connector(interface='MotorInterface')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # save the idle state in this class variable, since that is not present
        # in the actual motor hardware device. Use this variable to decide
        # whether movement commands are passed to the hardware.
        self._magnet_idle = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._motor_device_rot = self.get_connector('motorstage_rot')
        self._motor_device_xyz = self.get_connector('motorstage_xyz')

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
        constraints_xyz = self._motor_device_xyz.get_constraints()
        constraints_rot = self._motor_device_rot.get_constraints()
        constraints_xyz.update(constraints_rot)
        return constraints_xyz


    def move_rel(self, param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        A smart idea would be to ask the position after the movement.
        @return dict pos: dictionary with changed axis and positions
        """
        # split dictionary
        move_xyz, move_rot = self._split_dict(param_dict)
        if not self._magnet_idle:
            if move_xyz != {}:
                self._motor_device_xyz.move_rel(move_xyz)
            if move_rot != {}:
                self._motor_device_rot.move_rel(move_rot)
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "move_rel" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state(False)" '
                    'to have control over its movement.')
        return self.get_pos(list(param_dict))


    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        @return dict pos: dictionary with changed axis and positions
        """
        move_xyz, move_rot = self._split_dict(param_dict)
        if not self._magnet_idle:
            if move_xyz != {}:
                self._motor_device_xyz.move_abs(move_xyz)
            if move_rot != {}:
                self._motor_device_rot.move_abs(move_rot)
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "move_abs" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state (False)" '
                    'to have control over its movement.')
        return self.get_pos(list(param_dict))


    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self._motor_device_xyz.abort()
        self._motor_device_rot.abort()


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
        # split dictionary
        if param_list is None:
            pos_xyz = self._motor_device_xyz.get_pos()
            pos_rot = self._motor_device_rot.get_pos()
        else:
            list_xyz, list_rot = self._split_list(param_list)
            if list_xyz != []:
                pos_xyz = self._motor_device_xyz.get_pos(list_xyz)
            else:
                pos_xyz = {}
            if list_rot != []:
                pos_rot = self._motor_device_rot.get_pos(list_rot)
            else:
                pos_rot={}
        pos_xyz.update(pos_rot)
        return pos_xyz


    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        if param_list is None:
            status_xyz = self._motor_device_xyz.get_status()
            status_rot = self._motor_device_rot.get_status()
            #self.log.debug(status_rot)
        else:
            list_xyz, list_rot = self._split_list(param_list)
            if list_xyz != []:
                status_xyz = self._motor_device_xyz.get_status(list_xyz)
            else:
                status_xyz = {}
            if list_rot != []:
                status_rot = self._motor_device_rot.get_status(list_rot)
            else:
                status_rot = {}
        status_xyz.update(status_rot)
        return status_xyz


    def calibrate(self, param_list=None):
        """ Calibrates the stage.

        @param list param_list: param_list: optional, if a specific calibration
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
            if param_list is None:
                pos_xyz = self._motor_device_xyz.calibrate()
                pos_rot = self._motor_device_rot.calibrate()
            else:
                list_xyz, list_rot = self._split_list(param_list)
                if list_xyz != []:
                    pos_xyz = self._motor_device_xyz.calibrate(list_xyz)
                else:
                    pos_xyz = {}
                if list_rot != []:
                    pos_rot = self._motor_device_rot.calibrate(list_rot)
                else:
                    pos_rot = {}
            pos_xyz.update(pos_rot)
            return pos_xyz
        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "calibrate" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state(False)" '
                    'to have control over its movement.')
            return self.get_pos()

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param list param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict: with the axis label as key and the velocity as item.
        """

        if param_list is None:
            vel_xyz = self._motor_device_xyz.get_velocity()
            vel_rot = self._motor_device_rot.get_velocity()
        else:
            list_xyz, list_rot = self._split_list(param_list)
            if list_xyz != []:
                vel_xyz = self._motor_device_xyz.get_velocity(list_xyz)
            else:
                vel_xyz = {}
            if list_rot != []:
                vel_rot = self._motor_device_rot.get_velocity(list_rot)
            else:
                vel_rot = {}

        vel_xyz.update(vel_rot)
        return vel_xyz




    def set_velocity(self, param_dict=None):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return dict velocity: dictionary with axis and velocity
        """

        vel_xyz, vel_rot = self._split_dict(param_dict)
        if not self._magnet_idle:
            if vel_xyz != {}:
                self._motor_device_xyz.set_velocity(vel_xyz)
            if vel_rot != {}:
                self._motor_device_rot.set_velocity(vel_rot)

        else:
            self.log.warning('Motor Device is in Idle state and cannot '
                    'perform "set_velocity" commands. Couple the Motor to '
                    'control via the command "set_magnet_idle_state(False)" '
                    'to have control over its movement.')
        return self.get_velocity(list(param_dict))


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
        return -1

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
        return -1


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

    def _split_list(self,param_list):
        """This function splits a param_list into one for the xyz motor and one for the rot motor

        @param list param_list: List with parameters

        @return list list_xyz: list with parameters for xyz motor
        @return list list_rot: list with parameters for rotation motor"""

        list_xyz = []
        list_rot = []
        keys_xyz = self._motor_device_xyz.get_constraints()
        keys_rot = self._motor_device_rot.get_constraints()
        for key in param_list:
            if key in keys_xyz:
                list_xyz.append(key)
            if key in keys_rot:
                list_rot.append(key)

        return list_xyz, list_rot


    def _split_dict(self, param_dict):
        """This function splits a param_dict into one for the xyz motor and one for the rot motor

        @param list param_dict: dict with parameters and corresponding values

        @return dict dict_xyz: dict with parameters for xyz motor
        @return dict dict_rot: dict with parameters for rotation motor"""

        dict_xyz = {}
        dict_rot = {}
        keys_xyz = self._motor_device_xyz.get_constraints()
        keys_rot = self._motor_device_rot.get_constraints()
        for key in param_dict:
            if key in keys_xyz:
                dict_xyz[key]=param_dict[key]
            if key in keys_rot:
                dict_rot[key]=param_dict[key]
        #self.log.debug(dict_xyz)
        #self.log.debug(dict_rot)
        return dict_xyz, dict_rot





