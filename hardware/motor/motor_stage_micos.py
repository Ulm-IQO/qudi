# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the motorized stage for PI Micos.

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

import visa
import time

from collections import OrderedDict

from core.module import Base, ConfigOption
from interface.motor_interface import MotorInterface

class MotorStageMicos(Base, MotorInterface):
    """unstable: Jochen Scheuer.
    Hardware class to define the controls for the Micos stage of PI.
    """
    _modclass = 'MotorStageMicos'
    _modtype = 'hardware'

    unit_factor = 1000. # This factor converts the values given in m to mm.
    ### !!!!! Attention the units can be changed by setunit

    _com_port_xy = ConfigOption('com_port_xy', 'COM4', missing='warn')
    _baud_rate_xy = ConfigOption('baud_rate_xy', 57600, missing='warn')
    _timeout_xy = ConfigOption('timeout_xy', 1000, missing='warn')
    _term_char_xy = ConfigOption('term_char_xy', '\n', missing='warn')
    _com_port_zphi = ConfigOption('com_port_zphi', 'COM2', missing='warn')
    _baud_rate_zphi = ConfigOption('baud_rate_zphi', 57600, missing='warn')
    _timeout_zphi = ConfigOption('timeout_zphi', 1000, missing='warn')
    _term_char_zphi = ConfigOption('term_char_zphi', '\n', missing='warn')

    _first_axis_label = ConfigOption('first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('second_axis_label', 'y', missing='warn')
    _third_axis_label = ConfigOption('third_axis_label', 'z', missing='warn')
    _fourth_axis_label = ConfigOption('fourth_axis_label', 'phi', missing='warn')
    _first_axis_ID = ConfigOption('first_axis_ID', '0', missing='warn')
    _second_axis_ID = ConfigOption('second_axis_ID', '1', missing='warn')
    _third_axis_ID = ConfigOption('third_axis_ID', '0', missing='warn')
    _fourth_axis_ID = ConfigOption('fourth_axis_ID', '1', missing='warn')

    _min_first = ConfigOption('first_min', -0.1, missing='warn')
    _max_first = ConfigOption('first_max', 0.1, missing='warn')
    _min_second = ConfigOption('second_min', -0.1, missing='warn')
    _max_second = ConfigOption('second_max', 0.1, missing='warn')
    _min_third = ConfigOption('third_min', -0.1, missing='warn')
    _max_third = ConfigOption('third_max', 0.1, missing='warn')
    _min_fourth = ConfigOption('fourth_min', -0.1, missing='warn')
    _max_fourth = ConfigOption('fourth_max', 0.1, missing='warn')

    step_first_axis = ConfigOption('first_axis_step', 1e-7, missing='warn')
    step_second_axis = ConfigOption('second_axis_step', 1e-7, missing='warn')
    step_third_axis = ConfigOption('third_axis_step', 1e-7, missing='warn')
    step_fourth_axis = ConfigOption('fourth_axis_step', 1e-7, missing='warn')

    _vel_min_first = ConfigOption('vel_first_min', 1e-5, missing='warn')
    _vel_max_first = ConfigOption('vel_first_max', 5e-2, missing='warn')
    _vel_min_second = ConfigOption('vel_second_min', 1e-5, missing='warn')
    _vel_max_second = ConfigOption('vel_second_max', 5e-2, missing='warn')
    _vel_min_third = ConfigOption('vel_third_min', 1e-5, missing='warn')
    _vel_max_third = ConfigOption('vel_third_max', 5e-2, missing='warn')
    _vel_min_fourth = ConfigOption('vel_fourth_min', 1e-5, missing='warn')
    _vel_max_fourth = ConfigOption('vel_fourth_max', 5e-2, missing='warn')

    _vel_step_first = ConfigOption('vel_first_axis_step', 1e-5, missing='warn')
    _vel_step_second = ConfigOption('vel_second_axis_step', 1e-5, missing='warn')
    _vel_step_third = ConfigOption('vel_third_axis_step', 1e-5, missing='warn')
    _vel_step_fourth = ConfigOption('vel_fourth_axis_step', 1e-5, missing='warn')
    # _term_chars_xy = ConfigOption('micos_term_chars_xy', '\n', missing='warn')
    # _term_chars_zphi = ConfigOption('micos_term_chars_zphi', '\n', missing='warn')
    # _baud_rate_xy = ConfigOption('micos_baud_rate_xy', 57600, missing='warn')
    # _baud_rate_zphi = ConfigOption('micos_baud_rate_zphi', 57600, missing='warn')



    #Todo: add term_char to visa connection
    def on_activate(self):
        """ Initialisation performed during activation of the module.
        @return: error code
        """
        self.rm = visa.ResourceManager()
        self._serial_connection_xy = self.rm.open_resource(
            resource_name=self._com_port_xy,
            baud_rate=self._baud_rate_xy,
            timeout=self._timeout_xy)
        self._serial_connection_zphi = self.rm.open_resource(
            resource_name=self._com_port_zphi,
            baud_rate=self._baud_rate_zphi,
            timeout=self._timeout_zphi)

        constraints = self.get_constraints()
        all_axis_labels = [axis_label for axis_label in constraints]

        for axis_label in all_axis_labels:
            if int(self._ask(axis_label, '{} getunit'.format(int(constraints[axis_label]['ID'])+1))) == 2:
                self.log.info('As supposed the micos stage axis {} is set to the unit mm! '.format(axis_label))
            else:
                self.log.error('The micos stage is NOT set to the unit mm!!!! '
                               'DANGER of damaging stage or periphery!!!!')

        # Setting hardware limits to the stage. The stage will not move further these limits!
        self._write('x', '{} {} 0 {} {} 0 setlimit'.format(constraints['x']['pos_min']*self.unit_factor,
                                                           constraints['y']['pos_min']*self.unit_factor,
                                                           constraints['x']['pos_max']*self.unit_factor,
                                                           constraints['y']['pos_max']*self.unit_factor,
                                                           ))

        self._write('z', '{} {} 0 {} {} 0 setlimit'.format(constraints['z']['pos_min'] * self.unit_factor,
                                                           constraints['z']['pos_min'] * self.unit_factor,
                                                           constraints['phi']['pos_max'] * self.unit_factor,
                                                           constraints['phi']['pos_max'] * self.unit_factor,
                                                           ))

        self.log.info("Hardware limits were set to micos stage. To change the limits adjust the config file.")

        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        @return: error code
        """
        self._serial_connection_xy.close()
        self._serial_connection_zphi.close()
        self.rm.close()
        return 0

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the motorized stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)

        The possible keys in the constraint are defined here in the interface
        file. If the hardware does not support the values for the constraints,
        then insert just None.
        If you are not sure about the meaning, look in other hardware files
        to get an impression.
        """
        constraints = OrderedDict()

        axis0 = {}
        axis0['label'] = self._first_axis_label
        axis0['ID'] = self._first_axis_ID
        axis0['unit'] = 'm'  # the SI units
        axis0['ramp'] = None  # a possible list of ramps
        axis0['pos_min'] = self._min_first
        axis0['pos_max'] = self._max_first
        axis0['pos_step'] = self.step_first_axis
        axis0['vel_min'] = self._vel_min_first
        axis0['vel_max'] = self._vel_max_first
        axis0['vel_step'] = self._vel_step_first
        axis0['acc_min'] = None
        axis0['acc_max'] = None
        axis0['acc_step'] = None

        axis1 = {}
        axis1['label'] = self._second_axis_label
        axis1['ID'] = self._second_axis_ID
        axis1['unit'] = 'm'  # the SI units
        axis1['ramp'] = None  # a possible list of ramps
        axis1['pos_min'] = self._min_second
        axis1['pos_max'] = self._max_second
        axis1['pos_step'] = self.step_second_axis
        axis1['vel_min'] = self._vel_min_second
        axis1['vel_max'] = self._vel_max_second
        axis1['vel_step'] = self._vel_step_second
        axis1['acc_min'] = None
        axis1['acc_max'] = None
        axis1['acc_step'] = None

        axis2 = {}
        axis2['label'] = self._third_axis_label
        axis2['ID'] = self._third_axis_ID
        axis2['unit'] = 'm'  # the SI units
        axis2['ramp'] = None  # a possible list of ramps
        axis2['pos_min'] = self._min_third
        axis2['pos_max'] = self._max_third
        axis2['pos_step'] = self.step_third_axis
        axis2['vel_min'] = self._vel_min_third
        axis2['vel_max'] = self._vel_max_third
        axis2['vel_step'] = self._vel_step_third
        axis2['acc_min'] = None
        axis2['acc_max'] = None
        axis2['acc_step'] = None

        axis3 = {}
        axis3['label'] = self._fourth_axis_label
        axis3['ID'] = self._fourth_axis_ID
        axis3['unit'] = 'm'  # the SI units
        axis3['ramp'] = None  # a possible list of ramps
        axis3['pos_min'] = self._min_fourth
        axis3['pos_max'] = self._max_fourth
        axis3['pos_step'] = self.step_fourth_axis
        axis3['vel_min'] = self._vel_min_fourth
        axis3['vel_max'] = self._vel_max_fourth
        axis3['vel_step'] = self._vel_step_fourth
        axis3['acc_min'] = None
        axis3['acc_max'] = None
        axis3['acc_step'] = None
        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        constraints[axis3['label']] = axis3

        return constraints

    def move_rel(self, param_dict):
        """Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.


        @return dict pos: dictionary with the current magnet position
        """
        # Todo: check if the move is within the range allowed from config

        # Todo: Check if two parameters are changed such that if they are on one com port they can be
        # changed at the same time

        # There are sometimes connections problems therefore up to 3 attempts are started
        for attempt in range(3):
            try:
                for axis_label in param_dict:
                    step = param_dict[axis_label]
                    self._do_move_rel(axis_label, step*self.unit_factor)
            except:
                self.log.warning('Motor connection problem! Try again...')
            else:  # try worked
                break
        else:  # for ended without break
            self.log.error('Motor cannot move!')

        return self.get_pos()

    def move_abs(self, param_dict):
        """Moves stage to absolute position

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                The values for the axes are in millimeter,
                                the value for the rotation is in degrees.

        @return dict pos: dictionary with the current axis position
        """

        curr_pos = None
        # There are sometimes connections problems therefore up to 3 attempts are started
        for attept in range(3):
            try:
                # x and y are connencted through one com port therefore it is faster if both commands are sent at the
                # same time therefore there is the check if x and y or only one axis is changed
                if 'x' in param_dict and 'y' in param_dict:
                    self._write('x', '{} {} 0 move'.format(param_dict['x']*self.unit_factor,
                                                           param_dict['y']*self.unit_factor))
                elif 'x' in param_dict or 'y' in param_dict:
                    curr_pos = self.get_pos()
                    if 'x' in param_dict:
                        self._write('x', '{} {} 0 move'.format(param_dict['x']*self.unit_factor,
                                                               curr_pos['y']*self.unit_factor))
                    if 'y' in param_dict:
                        self._write('y', '{} {} 0 move'.format(curr_pos['x']*self.unit_factor,
                                                               param_dict['y']*self.unit_factor))

                # z and phi are connencted through one com port therefore it is faster if both commands are sent at the
                # same time therefore there is the check if z and phi or only one axis are changed
                if 'z' in param_dict and 'phi' in param_dict:
                    self._write('z', '{} {} 0 move'.format(param_dict['z']*self.unit_factor,
                                                           param_dict['phi']*self.unit_factor))
                elif 'z' in param_dict or 'phi' in param_dict:
                    if curr_pos is None:
                        curr_pos = self.get_pos()
                    if 'z' in param_dict:
                        self._write('z', '{} {} 0 move'.format(param_dict['z']*self.unit_factor,
                                                               curr_pos['phi']*self.unit_factor))
                    if 'phi' in param_dict:
                        self._write('phi', '{} {} 0 move'.format(curr_pos['z']*self.unit_factor,
                                                                 param_dict['phi']*self.unit_factor))
                while not self._motor_stopped():
                    time.sleep(0.05)
            except:
                self.log.warning('Motor connection problem! Try again...')
            else:
                break
        else:
            self.log.error('Motor cannot move!')
        return self.get_pos()

    #Todo:_ Add constrain checks in move_abs file, this can be seen here in the old commented version
    # def move_abs(self, param_dict):
    #     """ Moves stage to absolute position (absolute movement)
    #
    #     @param dict param_dict: dictionary, which passes all the relevant
    #                             parameters, which should be changed. Usage:
    #                              {'axis_label': <a-value>}.
    #                              'axis_label' must correspond to a label given
    #                              to one of the axis.
    #     A smart idea would be to ask the position after the movement.
    #     """
    #     constraints = self.get_constraints()
    #
    #     # ALEX COMMENT: I am not quite sure whether one has to call each
    #     #               axis, i.e. _micos_a and _micos_b only once, and then
    #     #               wait until they are finished.
    #     #               You have either to restructure the axis call and find
    #     #               out how to block any signal until the stage is not
    #     #               finished with the movement. Maybe you have also to
    #     #               increase the visa timeout number, because if the device
    #     #               does not react on a command after the timeout an error
    #     #               will be raised by the visa protocol itself!
    #
    #     if param_dict.get(self._micos_a.label_x) is not None:
    #         desired_pos = param_dict[self._micos_a.label_x]
    #         constr = constraints[self._micos_a.label_x]
    #
    #         if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
    #             self.log.warning('Cannot make absolute movement of the axis '
    #                 '"{0}" to possition {1}, since it exceeds the limts '
    #                 '[{2},{3}] ! Command is ignored!'
    #                 ''.format(self._micos_a.label_x, desired_pos,
    #                      constr['pos_min'], constr['pos_max']))
    #         else:
    #             self._micos_a.write('{0:f} 0.0 0.0 move'.format(desired_pos) )
    #             self._micos_a.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
    #         try:
    #             statusA = int(self._micos_a.ask('st'))
    #         except:
    #             statusA = 0
    #
    #
    #     if param_dict.get(self._micos_a.label_y) is not None:
    #         desired_pos = param_dict[self._micos_a.label_y]
    #         constr = constraints[self._micos_a.label_y]
    #
    #         if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
    #             self.log.warning('Cannot make absolute movement of the axis '
    #                     '"{0}" to possition {1}, since it exceeds the limts '
    #                     '[{2},{3}] ! Command is ignored!'.format(
    #                         self._micos_a.label_y, desired_pos,
    #                         constr['pos_min'],
    #                         constr['pos_max']))
    #         else:
    #             self._micos_a.write('0.0 {0:f} 0.0 move'.format(desired_pos) )
    #             self._micos_a.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
    #         try:
    #             statusA = int(self._micos_a.ask('st'))
    #         except:
    #             statusA = 0
    #
    #     if param_dict.get(self._micos_b.label_z) is not None:
    #         desired_pos = param_dict[self._micos_b.label_z]
    #         constr = constraints[self._micos_b.label_z]
    #
    #         if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
    #             self.log.warning('Cannot make absolute movement of the axis '
    #                     '"{0}" to possition {1}, since it exceeds the limts '
    #                     '[{2},{3}] ! Command is ignored!'.format(
    #                         self._micos_b.label_z, desired_pos,
    #                         constr['pos_min'],
    #                         constr['pos_max']))
    #         else:
    #             self._micos_b.write('{0:f} 0.0 0.0 move'.format(desired_pos) )
    #             self._micos_b.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
    #         try:
    #             statusB = int(self._micos_b.ask('st'))
    #         except:
    #             statusB = 0
    #
    #     if param_dict.get(self._micos_b.label_phi) is not None:
    #         desired_pos = param_dict[self._micos_b.label_phi]
    #         constr = constraints[self._micos_b.label_phi]
    #
    #         if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
    #             self.log.warning('Cannot make absolute movement of the axis '
    #                     '"{0}" to possition {1}, since it exceeds the limts '
    #                     '[{2},{3}] ! Command is ignored!'.format(
    #                         self._micos_b.label_phi, desired_pos,
    #                         constr['pos_min'],
    #                         constr['pos_max']))
    #         else:
    #             self._micos_b.write('0.0 {0:f} 0.0 move'.format(desired_pos) )
    #             self._micos_b.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
    #         try:
    #             statusB = int(self._micos_b.ask('st'))
    #         except:
    #             statusB = 0
    #
    #
    #     # ALEX COMMENT: Is there not a nicer way for that? If the axis does not
    #     #               reply during the movement, then it is not good to ask
    #     #               all the time the status. Because then the visa timeout
    #     #               would kill your connection to the axis.
    #     #               If the axis replies during movement, then think about
    #     #               a nicer way in waiting until the movement is done,
    #     #               because it will block the whole program.
    #     # while True:
    #     #     try:
    #     #         statusA = int(self._micos_a.ask('st'))
    #     #         statusB = int(self._micos_b.ask('st'))
    #     #     except:
    #     #         statusA = 0
    #     #         statusA = 0
    #     #
    #     #     if statusA ==0 or statusB == 0:
    #     #         time.sleep(0.2)
    #     #
    #     #         break
    #     #     time.sleep(0.2)
    #     # return 0
    #



    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        try:
            # only checking sending command to x and z because these
            # are the two axis and they also abort y and phi
            for axis_label in ['x', 'z']:
                self._write(axis_label, 'Ctrl-C')
            while not self._motor_stopped():
                time.sleep(0.2)
            self.log.warning('MOTOR MOVEMENT STOPPED!!!')

            return 0
        except:
            self.log.error('MOTOR MOVEMENT NOT STOPPED!!!')
            return -1

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.        """

        constraints = self.get_constraints()
        param_dict = {}

        # The information about axes x,y and z,phi are retrieved simultaneously. That is why if one is checked, the
        # information is saved and returned without another _ask.
        already_checked_xy = False
        already_checked_zphi = False

        all_axis_labels = [axis_label for axis_label in constraints]
        if param_list is None:
            param_list = all_axis_labels
        for axis_label in param_list:
            # unfortunately, probably due to connection problems this specific command sometimes failing
            # although it should run.... therefore some retries are added
            for attempt in range(25):
                if constraints[axis_label]['label'] == 'x' or constraints[axis_label]['label'] == 'y':
                    if already_checked_xy is False:
                        pos_xy = self._ask(axis_label, 'pos').split()
                        already_checked_xy = True
                    param_dict[axis_label] = float(pos_xy[int(constraints[axis_label]['ID'])])/self.unit_factor
                elif constraints[axis_label]['label'] == 'z' or constraints[axis_label]['label'] == 'phi':
                    if already_checked_zphi is False:
                        pos_zphi = self._ask(axis_label, 'pos').split()
                        already_checked_zphi = True
                    param_dict[axis_label] = float(pos_zphi[int(constraints[axis_label]['ID'])])/self.unit_factor
                else:
                    self.log.error("Asking question to not defined axis:", axis_label)
                # check if all required parameters are known
                if set(param_dict.keys()).issubset(set(param_list)):
                    break
        return param_dict

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        The meaning of the return value is:
        """
        constraints = self.get_constraints()
        param_dict = {}
        # The information about axes x,y and z,phi are retrieved simultaneously. That is why if one is checked, the
        # information is saved and returned without another _ask.
        already_checked_xy = False
        already_checked_zphi = False
        try:
            if param_list is not None:
                for axis_label in param_list:
                    # the status check takes quite long so if port is checked
                    # there is no need for second check
                    if axis_label == 'x' or axis_label == 'y':
                        if not already_checked_xy:
                            status_xy = self._ask(axis_label, 'st')
                            already_checked_xy = True
                        param_dict[axis_label] = status_xy
                    elif axis_label == 'z' or axis_label == 'phi':
                        if not already_checked_zphi:
                            status_zphi = self._ask(axis_label, 'st')
                            already_checked_zphi = True
                        param_dict[axis_label] = status_zphi
                    else:
                        self.log.error("Asking question to not defined axis:", axis_label)
            else:
                for axis_label in constraints:
                    #the status check takes quite long so if port is checked
                    # there is no need for second check
                    if constraints[axis_label]['label'] == 'x' or constraints[axis_label]['label'] == 'y':
                        if not already_checked_xy:
                            status_xy = self._ask(axis_label, 'st')
                            already_checked_xy = True
                        param_dict[axis_label] = status_xy
                    elif constraints[axis_label]['label'] == 'z' or constraints[axis_label]['label'] == 'phi':
                        if not already_checked_zphi:
                            status_zphi = self._ask(axis_label, 'st')
                            already_checked_zphi = True
                        param_dict[axis_label] = status_zphi
                    else:
                        self.log.error("Asking question to not defined axis:", axis_label)
            return param_dict
        except:
            self.log.error('Status request unsuccessful')
            return -1

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
        constraints = self.get_constraints()

        if param_list is not None:
            for axis_label in constraints:
                if constraints[axis_label]['label'] == 'x' in param_list:
                    self._write('x', '1 ncal')

                if constraints[axis_label]['label'] == 'y' in param_list:
                    self._write('y', '2 ncal')

                if constraints[axis_label]['label'] == 'z' in param_list:
                    self._write('z', '1 ncal')

                if constraints[axis_label]['label'] == 'phi' in param_list:
                    self._write('phi', '2 ncal')

        else:
            # setting axes active
            self._write('x', '1 1 setaxis')
            self._write('y', '1 2 setaxis')
            # execute calibration
            self._write('x', 'cal')

            # setting axes active
            self._write('z', '1 1 setaxis')
            self._write('phi', '1 2 setaxis')
            # setting axes active
            self._write('z', 'cal')


    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        constraints = self.get_constraints()
        vel = {}

        if param_list is None:
            # if no axis is selected set it to all
            param_list = [axis_label for axis_label in constraints]

        #Todo: Set velocity for each axis seperately
        if 'x' in param_list or 'y' in param_list:
            vel['x'] = float(self._ask('x', 'getvel').split()[0])/self.unit_factor
            vel['y'] = vel['x']
            self.log.warning('Velocity set for x and y axis!')

        if 'z' in param_list or 'phi' in param_list:
            vel['z'] = float(self._ask('z', 'getvel').split()[0])/self.unit_factor
            vel['phi'] = vel['z']
            self.log.warning('Velocity set for z and phi axis!')

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

        for axis_label in param_dict:
            desired_vel = param_dict[constraints[axis_label]['label']]
            constr = constraints[constraints[axis_label]['label']]

            if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):
                self.log.warning('Cannot set velocity of the axis '
                        '"{0}" to {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            axis_label, desired_vel,
                            constr['vel_min'],
                            constr['vel_max']))
            else:
                self._write(axis_label, '{0:f} sv'.format(desired_vel*self.unit_factor))
                self.log.info('Velocity set for z and phi  or x and y axis, it is not possible'
                                 'to set the velocity to individual axes!')

########################## internal methods ##################################

    def _write(self, axis, command):
        """this method just sends a command to the motor! DOES NOT RETURN AN ANSWER!
        @param axis string: name of the axis that should be asked

        @param command string: command

        @return error code (0:OK, -1:error)
        """
        constraints = self.get_constraints()
        try:
            if constraints[axis]['label'] == 'x' or constraints[axis]['label'] == 'y':
                self._serial_connection_xy.write(command + '\n')
                trash = self._read_answer(axis)  # deletes possible answers
            elif constraints[axis]['label'] == 'z' or constraints[axis]['label'] == 'phi':
                self._serial_connection_zphi.write(command + '\n')
                trash = self._read_answer(axis)  # deletes possible answers
            else:
                self.log.error("Asking question to not defined axis:", axis)
            return 0
        except:
            self.log.error('Command was not accepted')
            return -1

    def _read_answer(self, axis):
        """this method reads the answer from the motor!
        @return answer string: answer of motor
        """
        constraints = self.get_constraints()

        still_reading = True
        answer = ''
        while still_reading == True:
            try:
                if constraints[axis]['label'] == 'x' or constraints[axis]['label'] == 'y':
                    answer = answer + self._serial_connection_xy.read()[:-2]
                elif constraints[axis]['label'] == 'z' or constraints[axis]['label'] == 'phi':
                    answer = answer + self._serial_connection_zphi.read()[:-2]
                else:
                    self.log.error("Asking question to not defined axis:", axis)
            except:
                still_reading = False
        return answer

    def _ask(self, axis, question):
        """this method combines writing a command and reading the answer
        @param axis string: name of the axis that should be asked

        @param command string: command

        @return answer string: answer of motor
        """
        constraints = self.get_constraints()
        if constraints[axis]['label'] == 'x' or constraints[axis]['label'] == 'y':
            self._serial_connection_xy.write(question+'\n')
            answer = self._read_answer(axis)
        elif constraints[axis]['label'] == 'z' or constraints[axis]['label'] == 'phi':
            self._serial_connection_zphi.write(question+'\n')
            answer = self._read_answer(axis)
        else:
            self.log.error("Asking question to not defined axis:", axis)
        return answer

    def _in_movement(self):
        """
        this method checks if the magnet is still moving and returns
        a dictionary which of the axis are moving.

        @return: dict param_dict: Dictionary displaying if axis are moving:
        0 for immobile and 1 for moving
        """
        constraints = self.get_constraints()
        param_dict = {}
        status = self.get_status()
        for axis_label in constraints:
            param_dict[axis_label] = int(status[axis_label]) % 2
        return param_dict

    def _motor_stopped(self):
        """this method checks if the magnet is still moving and returns
            False if it is moving and True of it is immobile

            @return: bool stopped: False for immobile and True for moving
        """
        param_dict = self._in_movement()
        stopped = True
        for axis_label in param_dict:
            if param_dict[axis_label] != 0:
                self.log.info(axis_label + ' is moving')
                stopped = False
        return stopped

    def _do_move_rel(self, axis, step):
        """internal method for the relative move

        @param axis string: name of the axis that should be moved

        @param float step: step in millimeter

        @return str axis: axis which is moved
                move float: absolute position to move to
        """
        constraints = self.get_constraints()
        if not (abs(constraints[axis]['pos_step']) < abs(step)):
            self.log.warning('Cannot make the movement of the axis "{0}"'
                             'since the step is too small! Ignore command!')
        else:
            if axis == 'x':
                self._write('x', '{} 0 0 rmove'.format(step))
            elif axis == 'y':
                self._write('y', '0 {} 0 rmove'.format(step))
            elif axis == 'z':
                self._write('z', '{} 0 0 rmove'.format(step))
            elif axis == 'phi':
                self._write('phi', '0 {} 0 rmove'.format(step))
        return 0