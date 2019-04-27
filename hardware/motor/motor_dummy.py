# -*- coding: utf-8 -*-

"""
This file contains the dummy for a motorized stage interface.

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

from collections import OrderedDict
import time

from core.module import Base, ConfigOption
from interface.motor_interface import MotorInterface

class MotorAxisDummy:
    """ Generic dummy motor representing one axis. """
    def __init__(self, label):
        self.label = label


class MotorDummy(Base, MotorInterface):
    """ This is the dummy class to simulate a motorized stage.

    Example config for copy-paste:

    motor_dummy:
        module.Class: 'motor.motor_dummy.MotorDummy'
        wait_after_movement: '0.001' #in seconds

    """

    _modclass = 'MotorDummy'
    _modtype = 'hardware'

    unit_factor = 1. # This factor converts the values given in m to m.
    ### !!!!! Attention the units can be changed by setunit

    _wait_after_movement = ConfigOption('wait_after_movement', 0., missing='warn')

    _first_axis_label = ConfigOption('first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('second_axis_label', 'y', missing='warn')
    _third_axis_label = ConfigOption('third_axis_label', 'z', missing='warn')
    _fourth_axis_label = ConfigOption('fourth_axis_label', 'phi', missing='warn')

    _min_first = ConfigOption('first_min', 0e-6, missing='warn')
    _max_first = ConfigOption('first_max', 100e-6, missing='warn')
    _min_second = ConfigOption('second_min', 0e-6, missing='warn')
    _max_second = ConfigOption('second_max', 100e-6, missing='warn')
    _min_third = ConfigOption('third_min', 0e-6, missing='warn')
    _max_third = ConfigOption('third_max', 100e-6, missing='warn')
    _min_fourth = ConfigOption('fourth_min', 0e-6, missing='warn')
    _max_fourth = ConfigOption('fourth_max', 0e-6, missing='warn')

    step_first_axis = ConfigOption('first_axis_step', 1e-9, missing='warn')
    step_second_axis = ConfigOption('second_axis_step', 1e-9, missing='warn')
    step_third_axis = ConfigOption('third_axis_step', 1e-9, missing='warn')
    step_fourth_axis = ConfigOption('fourth_axis_step', 1e-9, missing='warn')


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        try:
            self._configured_constraints = self.get_constraints()
            #FIXME: not used as threshold...
        except:
            self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
           self.log.info('{0}: {1}'.format(key,config[key]))

        # these label should be actually set by the config.
        self._x_axis = MotorAxisDummy(label=self._first_axis_label)
        self._y_axis = MotorAxisDummy(label=self._second_axis_label)
        self._z_axis = MotorAxisDummy(label=self._third_axis_label)
        self._phi_axis = MotorAxisDummy(label=self._fourth_axis_label)
        #self._wait_after_movement = 1 #in seconds

    #TODO: Checks if configuration is set and is reasonable

    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        # PLEASE REMEMBER: DO NOT CALL THE POSITION SIMPLY self.x SINCE IT IS
        # EXTREMLY DIFFICULT TO SEARCH FOR x GLOBALLY IN A FILE!
        # Same applies to all other axis. I.e. choose more descriptive names.

        self._x_axis.pos = 0.0
        self._y_axis.pos = 0.0
        self._z_axis.pos = 0.0
        self._phi_axis.pos = 0.0

        self._x_axis.vel = 0.1
        self._y_axis.vel = 0.1
        self._z_axis.vel = 0.1
        self._phi_axis.vel = 0.1

        self._x_axis.status = 0
        self._y_axis.status = 0
        self._z_axis.status = 0
        self._phi_axis.status = 0

        return 0

    def on_deactivate(self):
        """ Deinitialise and deactivate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        return 0


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
        constraints = OrderedDict()

        axis0 = {'label': self._first_axis_label,
                 'unit': 'm',
                 'ramp': ['Sinus', 'Linear'],
                 'pos_min': self._min_first,
                 'pos_max': self._max_first,
                 'pos_step': self.step_first_axis,
                 'vel_min': 0,
                 'vel_max': 100,
                 'vel_step': 0.01,
                 'acc_min': 0.1,
                 'acc_max': 0.0,
                 'acc_step': 0.0}

        axis1 = {'label': self._second_axis_label,
                 'unit': 'm',
                 'ramp': ['Sinus', 'Linear'],
                 'pos_min': self._min_second,
                 'pos_max': self._max_second,
                 'pos_step': self.step_second_axis,
                 'vel_min': 0,
                 'vel_max': 100,
                 'vel_step': 0.01,
                 'acc_min': 0.1,
                 'acc_max': 0.0,
                 'acc_step': 0.0}

        axis2 = {'label': self._third_axis_label,
                 'unit': 'm', 
                 'ramp': ['Sinus', 'Linear'],
                 'pos_min': self._min_third,
                 'pos_max': self._max_third,
                 'pos_step': self.step_third_axis,
                 'vel_min': 0,
                 'vel_max': 100,
                 'vel_step': 0.01,
                 'acc_min': 0.1,
                 'acc_max': 0.0,
                 'acc_step': 0.0}

        axis3 = {'label': self._fourth_axis_label,
                 'unit': '°',
                 'ramp': ['Sinus', 'Trapez'],
                 'pos_min': self._min_fourth,
                 'pos_max': self._max_fourth,
                 'pos_step': self.step_fourth_axis,
                 'vel_min': 1,
                 'vel_max': 20,
                 'vel_step': 0.1,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

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

        @return dict param_dict : dictionary with the current magnet position
        """
        curr_pos_dict = self.get_pos()
        constraints = self.get_constraints()

        if param_dict.get(self._x_axis.label) is not None:
            move_x = param_dict[self._x_axis.label]
            curr_pos_x = curr_pos_dict[self._x_axis.label]

            if  (curr_pos_x + move_x > constraints[self._x_axis.label]['pos_max'] ) or\
                (curr_pos_x + move_x < constraints[self._x_axis.label]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._x_axis.label, move_x,
                            constraints[self._x_axis.label]['pos_min'],
                            constraints[self._x_axis.label]['pos_max']))
            else:
                self._make_wait_after_movement()
                self._x_axis.pos = self._x_axis.pos + move_x

        if param_dict.get(self._y_axis.label) is not None:
            move_y = param_dict[self._y_axis.label]
            curr_pos_y = curr_pos_dict[self._y_axis.label]

            if  (curr_pos_y + move_y > constraints[self._y_axis.label]['pos_max'] ) or\
                (curr_pos_y + move_y < constraints[self._y_axis.label]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._y_axis.label, move_y,
                            constraints[self._y_axis.label]['pos_min'],
                            constraints[self._y_axis.label]['pos_max']))
            else:
                self._make_wait_after_movement()
                self._y_axis.pos = self._y_axis.pos + move_y

        if param_dict.get(self._z_axis.label) is not None:
            move_z = param_dict[self._z_axis.label]
            curr_pos_z = curr_pos_dict[self._z_axis.label]

            if  (curr_pos_z + move_z > constraints[self._z_axis.label]['pos_max'] ) or\
                (curr_pos_z + move_z < constraints[self._z_axis.label]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._z_axis.label, move_z,
                            constraints[self._z_axis.label]['pos_min'],
                            constraints[self._z_axis.label]['pos_max']))
            else:
                self._make_wait_after_movement()
                self._z_axis.pos = self._z_axis.pos + move_z


        if param_dict.get(self._phi_axis.label) is not None:
            move_phi = param_dict[self._phi_axis.label]
            curr_pos_phi = curr_pos_dict[self._phi_axis.label]

            if  (curr_pos_phi + move_phi > constraints[self._phi_axis.label]['pos_max'] ) or\
                (curr_pos_phi + move_phi < constraints[self._phi_axis.label]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._phi_axis.label, move_phi,
                            constraints[self._phi_axis.label]['pos_min'],
                            constraints[self._phi_axis.label]['pos_max']))
            else:
                self._make_wait_after_movement()
                self._phi_axis.pos = self._phi_axis.pos + move_phi

        pos = {}
        pos = self.get_pos([param_dict.keys()])
        return pos


    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        A smart idea would be to ask the position after the movement.

        @return dict param_dict : dictionary with the current axis position

        """
        constraints = self.get_constraints()

        if param_dict.get(self._x_axis.label) is not None:
            desired_pos = param_dict[self._x_axis.label]
            constr = constraints[self._x_axis.label]

            if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._x_axis.label, desired_pos,
                            constr['pos_min'],
                            constr['pos_max']))
            else:
                self._make_wait_after_movement()
                self._x_axis.pos = desired_pos


        if param_dict.get(self._y_axis.label) is not None:
            desired_pos = param_dict[self._y_axis.label]
            constr = constraints[self._y_axis.label]

            if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._y_axis.label, desired_pos,
                            constr['pos_min'],
                            constr['pos_max']))
            else:
                self._make_wait_after_movement()
                self._y_axis.pos = desired_pos


        if param_dict.get(self._z_axis.label) is not None:
            desired_pos = param_dict[self._z_axis.label]
            constr = constraints[self._z_axis.label]

            if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._z_axis.label, desired_pos,
                            constr['pos_min'],
                            constr['pos_max']))
            else:
                self._make_wait_after_movement()
                self._z_axis.pos = desired_pos


        if param_dict.get(self._phi_axis.label) is not None:
            desired_pos = param_dict[self._phi_axis.label]
            constr = constraints[self._phi_axis.label]

            if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._phi_axis.label, desired_pos,
                            constr['pos_min'],
                            constr['pos_max']))
            else:
                self._make_wait_after_movement()
                self._phi_axis.pos = desired_pos

        return param_dict


    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MotorDummy: Movement stopped!')
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

        #self.log.warning("moter_dummy_get pos: " + str(pos))
        return pos

    def on_target(self, param_list=None):
        """ Stage will move all axes to targets 
        and waits until the motion has finished.
        Maybe useful in scan line began.

        @param list param_list : optional, if a specific status of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then from each axis the
                                 status is asked.

        @return int: error code (0:OK, -1:error)
        """
        #time.sleep(0.001)
        return 0

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
            vel[self._x_axis.label] = self._x_axis.vel
            vel[self._y_axis.label] = self._y_axis.vel
            vel[self._z_axis.label] = self._z_axis.vel
            vel[self._phi_axis.label] = self._phi_axis.vel

        return vel

    def set_velocity(self, param_dict=None):
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
            constr = constraints[self._x_axis.label]

            if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._x_axis.label, desired_vel,
                            constr['vel_min'],
                            constr['vel_max']))
            else:
                self._x_axis.vel = desired_vel

        if param_dict.get(self._y_axis.label) is not None:
            desired_vel = param_dict[self._y_axis.label]
            constr = constraints[self._y_axis.label]

            if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._y_axis.label, desired_vel,
                            constr['vel_min'],
                            constr['vel_max']))
            else:
                self._y_axis.vel = desired_vel

        if param_dict.get(self._z_axis.label) is not None:
            desired_vel = param_dict[self._z_axis.label]
            constr = constraints[self._z_axis.label]

            if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._z_axis.label, desired_vel,
                            constr['pos_min'],
                            constr['pos_max']))
            else:
                self._z_axis.vel = desired_vel

        if param_dict.get(self._phi_axis.label) is not None:
            desired_vel = param_dict[self._phi_axis.label]
            constr = constraints[self._phi_axis.label]

            if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limits '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._phi_axis.label, desired_vel,
                            constr['pos_min'],
                            constr['pos_max']))
            else:
                self._phi_axis.vel = desired_vel


    def _make_wait_after_movement(self):
        """ Define a time which the dummy should wait after each movement. """
        i_t = float(self._wait_after_movement)
        if i_t <= 1e9:
            pass
        else:
            time.sleep()

