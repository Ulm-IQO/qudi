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
command to talk to a xz motor hardware and a t motor hardware.
"""


from logic.generic_logic import GenericLogic
from interface.magnet_interface import MagnetInterface
from collections import OrderedDict

class MagnetMotorXZYInterfuse(GenericLogic, MagnetInterface):

    _modclass = 'MagnetMotorXZYInterfuse'
    _modtype = 'interfuse'

    # declare connectors, here you can see the interfuse action: the in
    # connector will cope a motor hardware, that means a motor device can
    # connect to the in connector of the logic.
    _in = {'motorstage_xz': 'MotorInterface',
           'motorstage_y': 'MotorInterface'}

    # And as a result, you will have an out connector, which is compatible to a
    # magnet interface, and which can be plug in to an appropriated magnet logic
    _out = {'magnetstage': 'MagnetInterface'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # save the idle state in this class variable, since that is not present
        # in the actual motor hardware device. Use this variable to decide
        # whether movement commands are passed to the hardware.
        self._magnet_idle = False

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._motor_device_xz = self.get_in_connector('motorstage_xz')
        self._motor_device_y = self.get_in_connector('motorstage_y')



    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def get_constraints(self):
        """ Retrieve the hardware constrains from the magnet driving device.

        @return dict: dict with constraints for the magnet hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.
        """
        constraints_xz = self._motor_device_xz.get_constraints()
        constraints_y = self._motor_device_y.get_constraints()
        constraints_xz.update(constraints_y)

        constraints = OrderedDict(sorted(constraints_xz.items(), key=lambda t: t[0]))
        return constraints


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
        move_xz, move_y = self._split_dict(param_dict)
        if not self._magnet_idle:
            if move_xz != {}:
                self._motor_device_xz.move_rel(move_xz)
            if move_y != {}:
                self._motor_device_y.move_rel(move_y)
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
        move_xz, move_y = self._split_dict(param_dict)
        if not self._magnet_idle:
            if move_xz != {}:
                self._motor_device_xz.move_abs(move_xz)
            if move_y != {}:
                self._motor_device_y.move_abs(move_y)
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
        self._motor_device_xz.abort()
        self._motor_device_y.abort()


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
        pos_xz = {}
        pos_y = {}
        # split dictionary
        if param_list==None:
            pos_xz = self._motor_device_xz.get_pos()
            pos_y = self._motor_device_y.get_pos()
        else:
            list_xz, list_y = self._split_list(param_list)
            if list_xz is not None:
                pos_xz.update(self._motor_device_xz.get_pos(list_xz))
            if list_y is not None:
                pos_y.update(self._motor_device_y.get_pos(list_y))
        pos_xz.update(pos_y)
        return pos_xz


    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        status_xz = {}
        status_y = {}
        # split dictionary
        if param_list == None:
            status_xz = self._motor_device_xz.get_status()
            status_y = self._motor_device_y.get_status()
        else:
            list_xz, list_y= self._split_list(param_list)
            if list_xz is not None:
                status_xz.update(self._motor_device_xz.get_status(list_xz))
            if list_y is not None:
                status_y.update(self._motor_device_y.get_status(list_y))

        status_xz.update(status_y)
        return status_xz


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
            if param_list==None:
                pos_xz = self._motor_device_xz.calibrate()
                pos_y = self._motor_device_y.calibrate()
            else:
                list_xz, list_y = self._split_list(param_list)
                if list_xz != []:
                    pos_y = self._motor_device_xz.calibrate(list_xz)
                else:
                    pos_xz = {}
                if list_y != []:
                    pos_y= self._motor_device_ycalibrate(list_y)
                else:
                    pos_y = {}
            pos_xz.update(pos_y)
            return pos_xz
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

        vel_xz = {}
        vel_y = {}
        # split dictionary
        if param_list == None:
            vel_xz = self._motor_device_xz.get_velocity()
            vel_y = self._motor_device_y.get_velocity()
        else:
            list_xz, list_y, = self._split_list(param_list)
            if list_xz is not None:
                vel_xz.update(self._motor_device_xz.get_velocity(list_xz))
            if list_y is not None:
                vel_y.update(self._motor_device_y.get_velocity(list_y))

        vel_xz.update(vel_y)
        return vel_xz


    def set_velocity(self, param_dict=None):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return dict velocity: dictionary with axis and velocity
        """

        vel_xz, vel_y= self._split_dict(param_dict)
        if not self._magnet_idle:
            if vel_xz != {}:
                self._motor_device_xz.set_velocity(vel_xz)
            if vel_y != {}:
                self._motor_device_y.set_velocity(vel_y)

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
        """This function splits a param_list into one for the xz motor and one for the y motor

        @param list param_list: List with parameters

        @return list list_xz: list with parameters for xz motor
        @return list list_y: list with parameters for y motor"""

        list_xz = []
        list_y = []
        keys_xz = self._motor_device_xz.get_constraints()
        keys_y = self._motor_device_y.get_constraints()
        for key in param_list:
            if key in keys_xz:
                list_xz.append(key)
            if key in keys_y:
                list_y.append(key)

        return list_xz, list_y


    def _split_dict(self, param_dict):
        """This function splits a param_dict into one for the xz motor and one for the y motor

        @param list param_dict: dict with parameters and corresponding values

        @return dict dict_xz: dict with parameters for xz motor
        @return dict dict_y: dict with parameters for y motor"""

        dict_xz = {}
        dict_y = {}
        keys_xz = self._motor_device_xz.get_constraints()
        keys_y = self._motor_device_y.get_constraints()
        for key in param_dict:
            if key in keys_xz:
                dict_xz[key] = param_dict[key]
            if key in keys_y:
                dict_y[key] = param_dict[key]

        return dict_xz, dict_y





