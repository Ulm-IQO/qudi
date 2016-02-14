# -*- coding: utf-8 -*-

"""
This file contains the dummy for a motorized stage interface.

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

Copyright (C) 2015 Christoph Mueller christoph-1.mueller@uni-ulm.de
Copyright (C) 2015 Jochen Scheuer jochen.scheuer@uni-ulm.de
Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from core.base import Base
from interface.motor_interface import MotorInterface

class MotorAxisDummy(object):
    """ Generic dummy motor representing one axis. """
    def __init__(self, label):
        self.label = label


class MotorInterfaceDummy(Base, MotorInterface):
    """ This is the dummy class to simulate a motorized stage. """

    _modclass = 'MotorInterfaceDummy'
    _modtype = 'hardware'

    # connectors
    _out = {'magnet': 'MotorInterface'}


    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        # these label should be actually set by the config.
        self._x_axis = MotorAxisDummy('x')
        self._y_axis = MotorAxisDummy('y')
        self._z_axis = MotorAxisDummy('z')
        self._phi_axis = MotorAxisDummy('phi')

    #TODO: Checks if configuration is set and is reasonable

    def activation(self, e):

        # PLEASE REMEMBER: DO NOT CALL THE POSITION SIMPLY self.x SINCE IT IS
        # EXTREMLY DIFFICULT TO SEARCH FOR x GLOBALLY IN A FILE!
        # Same applies to all other axis. I.e. choose more descriptive names.

        self._x_axis.pos = 0.0
        self._y_axis.pos = 0.0
        self._z_axis.pos = 0.0
        self._phi_axis.pos = 0.0

        self._x_axis.vel = 1.0
        self._y_axis.vel = 1.0
        self._z_axis.vel = 1.0
        self._phi_axis.vel = 1.0

        self._x_axis.status = 0
        self._y_axis.status = 0
        self._z_axis.status = 0
        self._phi_axis.status = 0

    def deactivation(self, e):
        pass


    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the magnet hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.

        Provides all the constraints for each axis of a motorized stage
        (like total travel distance, velocity, ...)
        Each axis has its own dictionary, where the label is used as the
        identifier throughout the whole module. The dictionaries for each axis
        are again grouped together in a constraints dictionary in the form

            {'<label_axis0>': axis0 }

        where axis0 is again a dict with the possible values defined below. The
        possible keys in the constraint are defined here in the interface file.
        If the hardware does not support the values for the constraints, then
        insert just None. If you are not sure about the meaning, look in other
        hardware files to get an impression.
        """
        constraints = {}

        axis0 = {}
        axis0['label'] = self._x_axis.label # name is just as a sanity included
        axis0['unit'] = 'm'                 # the SI units
        axis0['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min'] = 0
        axis0['pos_max'] = 100  # that is basically the traveling range
        axis0['pos_step'] = 100
        axis0['vel_min'] = 0
        axis0['vel_max'] = 100
        axis0['vel_step'] = 0.01
        axis0['acc_min'] = 0.1
        axis0['acc_max'] = 0.0
        axis0['acc_step'] = 0.0

        axis1 = {}
        axis1['label'] = self._y_axis.label        # that axis label should be obtained from config
        axis1['unit'] = 'm'        # the SI units
        axis1['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis1['pos_min'] = 0
        axis1['pos_max'] = 100  # that is basically the traveling range
        axis1['pos_step'] = 100
        axis1['vel_min'] = 0
        axis1['vel_max'] = 100
        axis1['vel_step'] = 0.01
        axis1['acc_min'] = 0.1
        axis1['acc_max'] = 0.0
        axis1['acc_step'] = 0.0

        axis2 = {}
        axis2['label'] = self._z_axis.label        # that axis label should be obtained from config
        axis2['unit'] = 'm'        # the SI units
        axis2['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis2['pos_min'] = 0
        axis2['pos_max'] = 100  # that is basically the traveling range
        axis2['pos_step'] = 100
        axis2['vel_min'] = 0
        axis2['vel_max'] = 100
        axis2['vel_step'] = 0.01
        axis2['acc_min'] = 0.1
        axis2['acc_max'] = 0.0
        axis2['acc_step'] = 0.0

        axis3 = {}
        axis3['label'] = self._phi_axis.label      # that axis label should be obtained from config
        axis3['unit'] = '°'        # the SI units
        axis3['ramp'] = ['Sinus','Trapez'] # a possible list of ramps
        axis3['pos_min'] = 0
        axis3['pos_max'] = 360  # that is basically the traveling range
        axis3['pos_step'] = 100
        axis3['vel_min'] = 1
        axis3['vel_max'] = 20
        axis3['vel_step'] = 0.1
        axis3['acc_min'] = None
        axis3['acc_max'] = None
        axis3['acc_step'] = None

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        constraints[axis3['label']] = axis3

        return constraints

    def move_rel(self,  param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed.
                                With get_constraints() you can obtain all
                                possible parameters of that stage. According to
                                this parameter set you have to pass a dictionary
                                with keys that are called like the parameters
                                from get_constraints() and assign a SI value to
                                that. For a movement in x the dict should e.g.
                                have the form:
                                    dict = { 'x' : 23 }
                                where the label 'x' corresponds to the chosen
                                axis label.

        A smart idea would be to ask the position after the movement.
        """
        curr_pos_dict = self.get_pos()
        constraints = self.get_constraints()

        if param_dict.get(self._x_axis.label) is not None:
            move_x = param_dict[self._x_axis.label]
            curr_pos_x = curr_pos_dict[self._x_axis.label]

            if  (curr_pos_x + move_x > constraints[self._x_axis.label]['pos_max'] ) or\
                (curr_pos_x + move_x < constraints[self._x_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._x_axis.label, move_x,
                                    constraints[self._x_axis.label]['pos_min'],
                                    constraints[self._x_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._x_axis.pos = self._x_axis.pos + move_x

        if param_dict.get(self._y_axis.label) is not None:
            move_y = param_dict[self._y_axis.label]
            curr_pos_y = curr_pos_dict[self._y_axis.label]

            if  (curr_pos_y + move_y > constraints[self._y_axis.label]['pos_max'] ) or\
                (curr_pos_y + move_y < constraints[self._y_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._y_axis.label, move_y,
                                    constraints[self._y_axis.label]['pos_min'],
                                    constraints[self._y_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._y_axis.pos = self._y_axis.pos + move_y

        if param_dict.get(self._z_axis.label) is not None:
            move_z = param_dict[self._z_axis.label]
            curr_pos_z = curr_pos_dict[self._z_axis.label]

            if  (curr_pos_z + move_z > constraints[self._z_axis.label]['pos_max'] ) or\
                (curr_pos_z + move_z < constraints[self._z_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._z_axis.label, move_z,
                                    constraints[self._z_axis.label]['pos_min'],
                                    constraints[self._z_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._z_axis.pos = self._z_axis.pos + move_z

        if param_dict.get(self._phi_axis.label) is not None:
            move_phi = param_dict[self._phi_axis.label]
            curr_pos_phi = curr_pos_dict[self._phi_axis.label]

            if  (curr_pos_phi + move_phi > constraints[self._phi_axis.label]['pos_max'] ) or\
                (curr_pos_phi + move_phi < constraints[self._phi_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._phi_axis.label, move_phi,
                                    constraints[self._phi_axis.label]['pos_min'],
                                    constraints[self._phi_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._phi_axis.pos = self._phi_axis.pos + move_phi

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        A smart idea would be to ask the position after the movement.
        """
        constraints = self.get_constraints()

        if param_dict.get(self._x_axis.label) is not None:
            desired_pos = param_dict[self._x_axis.label]

            if  (desired_pos > constraints[self._x_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._x_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._x_axis.label, desired_pos,
                                    constraints[self._x_axis.label]['pos_min'],
                                    constraints[self._x_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._x_axis.pos = desired_pos

        if param_dict.get(self._y_axis.label) is not None:
            desired_pos = param_dict[self._y_axis.label]

            if  (desired_pos > constraints[self._y_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._y_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._y_axis.label, desired_pos,
                                    constraints[self._y_axis.label]['pos_min'],
                                    constraints[self._y_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._y_axis.pos = desired_pos

        if param_dict.get(self._z_axis.label) is not None:
            desired_pos = param_dict[self._z_axis.label]

            if  (desired_pos > constraints[self._z_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._z_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._z_axis.label, desired_pos,
                                    constraints[self._z_axis.label]['pos_min'],
                                    constraints[self._z_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._z_axis.pos = desired_pos

        if param_dict.get(self._phi_axis.label) is not None:
            desired_pos = param_dict[self._phi_axis.label]

            if  (desired_pos > constraints[self._phi_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._phi_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._phi_axis.label, desired_pos,
                                    constraints[self._phi_axis.label]['pos_min'],
                                    constraints[self._phi_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._phi_axis.pos = desired_pos


    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self.logMsg('MotorInterfaceDummy: Movement stopped!', msgType='status')
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        pos = {}
        if param_list is not None:
            if self._x_axis.label in param_list:
                pos[self._x_axis.label] = self._x_axis.pos

            if self._y_axis.label in param_list:
                pos[self._y_axis.label] = self._y_axis.pos

            if self._z_axis.label in param_list:
                pos[self._z_axis.label] = self._z_axis.pos

            if self._phi_axis.label in param_list:
                pos[self._phi_axis.label] = self._phi_axis.pos

        else:
            pos[self._x_axis.label] = self._x_axis.pos
            pos[self._y_axis.label] = self._y_axis.pos
            pos[self._z_axis.label] = self._z_axis.pos
            pos[self._phi_axis.label] = self._phi_axis.pos

        return pos

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """

        status = {}
        if param_list is not None:
            if self._x_axis.label in param_list:
                status[self._x_axis.label] = self._x_axis.status

            if self._y_axis.label in param_list:
                status[self._y_axis.label] = self._y_axis.status

            if self._z_axis.label in param_list:
                status[self._z_axis.label] = self._z_axis.status

            if self._phi_axis.label in param_list:
                status[self._phi_axis.label] = self._phi_axis.status

        else:
            status[self._x_axis.label] = self._x_axis.status
            status[self._y_axis.label] = self._y_axis.status
            status[self._z_axis.label] = self._z_axis.status
            status[self._phi_axis.label] = self._phi_axis.status

        return status


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
        if param_list is not None:
            if self._x_axis.label in param_list:
                self._x_axis.pos = 0.0

            if self._y_axis.label in param_list:
                self._y_axis.pos = 0.0

            if self._z_axis.label in param_list:
                self._z_axis.pos = 0.0

            if self._phi_axis.label in param_list:
                self._phi_axis.pos = 0.0

        else:
            self._x_axis.pos = 0.0
            self._y_axis.pos = 0.0
            self._z_axis.pos = 0.0
            self._phi_axis.pos = 0.0

        return 0

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        vel = {}
        if param_list is not None:
            if self._x_axis.label in param_list:
                vel[self._x_axis.label] = self._x_axis.vel
            if self._y_axis.label in param_list:
                vel[self._x_axis.label] = self._y_axis.vel
            if self._z_axis.label in param_list:
                vel[self._x_axis.label] = self._z_axis.vel
            if self._phi_axis.label in param_list:
                vel[self._phi_axis.label] = self._phi_axis.vel

        else:
            vel[self._x_axis.label] = self._x_axis.get_vel
            vel[self._y_axis.label] = self._y_axis.get_vel
            vel[self._z_axis.label] = self._z_axis.get_vel
            vel[self._phi_axis.label] = self._phi_axis.vel

        return vel

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        constraints = self.get_constraints()

        if param_dict.get(self._x_axis.label) is not None:
            desired_vel = param_dict[self._x_axis.label]

            if  (desired_vel > constraints[self._x_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._x_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._x_axis.label, desired_vel,
                                    constraints[self._x_axis.label]['vel_min'],
                                    constraints[self._x_axis.label]['vel_max']),
                            msgType='warning')
            else:
                self._x_axis.vel = desired_vel

        if param_dict.get(self._y_axis.label) is not None:
            desired_vel = param_dict[self._y_axis.label]

            if  (desired_vel > constraints[self._y_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._y_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._y_axis.label, desired_vel,
                                    constraints[self._y_axis.label]['vel_min'],
                                    constraints[self._y_axis.label]['vel_max']),
                            msgType='warning')
            else:
                self._y_axis.vel = desired_vel

        if param_dict.get(self._z_axis.label) is not None:
            desired_vel = param_dict[self._z_axis.label]

            if  (desired_vel > constraints[self._z_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._z_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._z_axis.label, desired_vel,
                                    constraints[self._z_axis.label]['pos_min'],
                                    constraints[self._z_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._z_axis.vel = desired_vel

        if param_dict.get(self._phi_axis.label) is not None:
            desired_vel = param_dict[self._phi_axis.label]

            if  (desired_vel > constraints[self._phi_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._phi_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._phi_axis.label, desired_vel,
                                    constraints[self._phi_axis.label]['pos_min'],
                                    constraints[self._phi_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._phi_axis.vel = desired_vel


