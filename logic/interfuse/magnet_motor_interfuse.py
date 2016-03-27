# -*- coding: utf-8 -*-

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
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

Reimplement each call
"""

from logic.generic_logic import GenericLogic
from interface.magnet_interface import MagnetInterface


class MagnetMotorInterfuse(GenericLogic, MagnetInterface):

    _modclass = 'MagnetMotorInterfuse'
    _modtype = 'interfuse'

    # declare connectors, here you can see the interfuse action: the in
    # connector will cope a motor hardware, that means a motor device can
    # connect to the in connector of the logic.
    _in = {'motor': 'MotorInterface'}

    # And as a result, you will have an out connector, which is compatible to a
    # magnet interface, and which can be plug in to an appropriated magnet logic
    _out = {'magnet': 'MagnetInterface'}

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}

        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)

        # save the idle state in this class variable, since that is not present
        # in the actual motor hardware device. Use this variable to decide
        # whether movement commands are passed to the hardware.
        self._magnet_idle = True



    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._motor_device = self.connector['in']['motor']['object']


    def deactivation(self, e):
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
            self.logMsg('Motor Device is in Idle state and cannot perform '
                        '"move_rel" commands. Couple the Motor to control via '
                        'the command "set_magnet_idle(False)" to have control '
                        'over its movement.', msgType='warning')


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
            self.logMsg('Motor Device is in Idle state and cannot perform '
                        '"move_abs" commands. Couple the Motor to control via '
                        'the command "set_magnet_idle(False)" to have control '
                        'over its movement.', msgType='warning')


    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self._motor_device.abort()


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
        return self._motor_devic.get_pos(param_list)


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
            self.logMsg('Motor Device is in Idle state and cannot perform '
                        '"calibrate" commands. Couple the Motor to control via '
                        'the command "set_magnet_idle(False)" to have control '
                        'over its movement.', msgType='warning')

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


    def set_velocity(self, param_list=None):
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
            self.logMsg('Motor Device is in Idle state and cannot perform '
                        '"set_velocity" commands. Couple the Motor to control '
                        'via the command "set_magnet_idle(False)" to have '
                        'control over its movement.', msgType='warning')


    def tell(self, param_dict=None):
        """ Send a command to the magnet.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the command string>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.



        @return int: error code (0:OK, -1:error)
        """
        self._motor_device.tell(param_dict)


    def ask(self, param_dict=None):
        """ Ask the magnet a question.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the question string>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return string: contains the answer coming from the magnet
        """
        return self._motor_device.ask(param_dict)


    def initialize(self):
        """
        Acts as a switch. When all coils of the superconducting magnet are
        heated it cools them, else the coils get heated.
        @return int: (0: Ok, -1:error)
        """
        self.logMsg('Motor Hardware does not need initialization for starting '
                    'or ending a movement. Nothing will happen.',
                    msgType='status')


    def set_magnet_idle(self, magnet_idle=True):
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


    def is_magnet_idle(self):
        """ Retrieve the current state of the magnet, whether it is idle or not.

        @return bool: the actual state which was set in the magnet hardware.
                        True = idle, decoupled from control
                        False = Not Idle, coupled to control
        """

        return self._magnet_idle



