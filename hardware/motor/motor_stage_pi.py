# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the motorized stage for PI.

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

from core.base import Base
from interface.motor_interface import MotorInterface

class MotorStagePI(Base, MotorInterface):
    """unstable: Christoph Müller, Simon Schmitt
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MotorStagePI'
    _modtype = 'hardware'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        @return: error code
        """
        # Read configs from config-file
        config = self.getConfiguration()

        # get the right com-ports from config
        if 'com_port_pi_xyz' in config.keys():
            self._com_port_pi_xyz = config['com_port_pi_xyz']
        else:
            self.log.error('No parameter "com_port_pi_xyz" found in config.\n'
                    'Cannot connect to motorized stage!')

        # get the the right baud rates from config
        if 'pi_xyz_baud_rate' in config.keys():
            self._pi_xyz_baud_rate = config['pi_xyz_baud_rate']
        else:
            self._pi_xyz_baud_rate = 9600
            self.log.warning('No parameter "pi_xyz_baud_rate" found in '
                    'config!\nTaking the baud rate {0} ')

        # get the the right timeouts from config
        if 'pi_xyz_timeout' in config.keys():
            self._pi_xyz_timeout = config['pi_xyz_timeout']
        else:
            self._pi_xyz_timeout = 1000    # timeouts are given in millisecond in new pyvisa version
            self.log.warning('No parameter "pi_xyz_timeout" found in '
                    'config!\n'
                    'Setting the timeout to {0} '
                    'instead.'.format(self._pi_xyz_timeout))


        # get the the right term_chars from config
        if 'pi_xyz_term_char' in config.keys():
            self._pi_xyz_term_char = config['pi_xyz_term_char']
        else:
            self._pi_xyz_term_char = '\n'
            self.log.warning('No parameter "pi_xyz_term_char" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._pi_xyz_term_char))

        #axis definition:
        if 'pi_first_axis_label' in config.keys():
            self._first_axis_label = config['pi_first_axis_label']
        else:
            self._first_axis_label = 'x'
            self.log.warning('No parameter "pi_first_axis_label" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._first_axis_label))
        if 'pi_second_axis_label' in config.keys():
            self._second_axis_label = config['pi_second_axis_label']
        else:
            self._second_axis_label = 'y'
            self.log.warning('No parameter "pi_second_axis_label" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._second_axis_label))
        if 'pi_third_axis_label' in config.keys():
            self._third_axis_label = config['pi_third_axis_label']
        else:
            self._third_axis_label = 'z'
            self.log.warning('No parameter "pi_third_axis_label" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._third_axis_label))

        if 'pi_first_axis_ID' in config.keys():
            self._first_axis_ID = config['pi_first_axis_ID']
        else:
            self._first_axis_ID = '1'
            self.log.warning('No parameter "pi_first_axis_ID" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._first_axis_ID))
        if 'pi_second_axis_ID' in config.keys():
            self._second_axis_ID = config['pi_second_axis_ID']
        else:
            self._second_axis_ID = '2'
            self.log.warning('No parameter "pi_second_axis_ID" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._second_axis_ID))
        if 'pi_third_axis_ID' in config.keys():
            self._third_axis_ID = config['pi_third_axis_ID']
        else:
            self._third_axis_ID = '3'
            self.log.warning('No parameter "pi_third_axis_ID" found in '
                    'config!\nTaking the term_char {0} '
                    'instead.'.format(self._third_axis_ID))


        self.rm = visa.ResourceManager()
        self._serial_connection_xyz = self.rm.open_resource(resource_name=self._com_port_pi_xyz,
                                                            baud_rate=self._pi_xyz_baud_rate,
                                                            timeout=self._pi_xyz_timeout)

        # Should be in config I guess

        # setting the ranges of the axes - PI uses units of 10nm. Thus in order to convert to meters
        # a multiplication with 1e7 is necessary
        if 'pi_first_min' in config.keys():
            self._min_first = config['pi_first_min']
        else:
            self._min_first = -0.1
            self.log.warning('No parameter "pi_first_min" found in config!\n'
                    'Taking -0.1m instead.')
        if 'pi_first_max' in config.keys():
            self._max_first = config['pi_first_max']
        else:
            self._max_first = 0.1
            self.log.warning('No parameter "pi_first_max" found in config!\n'
                    'Taking 0.1m instead.')
        if 'pi_second_min' in config.keys():
            self._min_second = config['pi_second_min']
        else:
            self._min_second = -0.1
            self.log.warning('No parameter "pi_second_min" found in config!\n'
                    'Taking -0.1m instead.')
        if 'pi_second_max' in config.keys():
            self._max_second = config['pi_second_max']
        else:
            self._max_second = 0.1
            self.log.warning('No parameter "pi_second_max" found in config!\n'
                    'Taking 0.1m instead.')
        if 'pi_third_min' in config.keys():
            self._min_third = config['pi_third_min']
        else:
            self._min_z = -0.1
            self.log.warning('No parameter "pi_third_min" found in config!\n'
                    'Taking -0.1m instead.')
        if 'pi_third_max' in config.keys():
            self._max_third = config['pi_third_max']
        else:
            self._max_third = 0.1
            self.log.warning('No parameter "pi_third_max" found in config!\n'
                    'Taking 0.1m instead.')

        if 'pi_first_axis_step' in config.keys():
            self.step_first_axis = config['pi_first_axis_step']
        else:
            self.step_first_axis = 1e-7
            self.log.warning('No parameter "pi_first_axis_step" found in config!\n'
                    'Taking 10nm instead.')

        if 'pi_second_axis_step' in config.keys():
            self.step_second_axis = config['pi_second_axis_step']
        else:
            self.step_second_axis = 1e-7
            self.log.warning('No parameter "pi_second_axis_step" found in config!\n'
                    'Taking 10nm instead.')

        if 'pi_third_axis_step' in config.keys():
            self.step_third_axis = config['pi_third_axis_step']
        else:
            self.step_third_axis = 1e-7
            self.log.warning('No parameter "pi_third_axis_step" found in config!\n'
                    'Taking 10nm instead.')


        if 'vel_first_min' in config.keys():
            self._vel_min_first = config['vel_first_min']
        else:
            self._vel_min_first = 1e-5
            self.log.warning('No parameter "vel_first_min" found in config!\n'
                             'Taking 1e-5m/s instead.')
        if 'vel_first_max' in config.keys():
            self._vel_max_first = config['vel_first_max']
        else:
            self._vel_max_first = 5e-2
            self.log.warning('No parameter "vel_first_max" found in config!\n'
                             'Taking 5e-2m/s instead.')
        if 'vel_second_min' in config.keys():
            self._vel_min_second = config['vel_second_min']
        else:
            self._vel_min_second = 1e-5
            self.log.warning('No parameter "vel_second_min" found in config!\n'
                             'Taking 1e-5m/s instead.')
        if 'vel_second_max' in config.keys():
            self._vel_max_second = config['vel_second_max']
        else:
            self._vel_max_second = 5e-2
            self.log.warning('No parameter "vel_second_max" found in config!\n'
                             'Taking 5e-2m/s instead.')
        if 'vel_third_min' in config.keys():
            self._vel_min_third = config['vel_third_min']
        else:
            self._vel_min_z = 1e-5
            self.log.warning('No parameter "vel_third_min" found in config!\n'
                             'Taking 1e-5m instead.')
        if 'vel_third_max' in config.keys():
            self._vel_max_third = config['vel_third_max']
        else:
            self._vel_max_third = 5e-2
            self.log.warning('No parameter "vel_third_max" found in config!\n'
                             'Taking 5e-2m/s instead.')

        if 'vel_first_axis_step' in config.keys():
            self._vel_step_first = config['vel_first_axis_step']
        else:
            self._vel_step_first = 1e-5
            self.log.warning('No parameter "vel_first_axis_step" found in config!\n'
                             'Taking 1e-5m/s instead.')

        if 'vel_second_axis_step' in config.keys():
            self._vel_step_second = config['vel_second_axis_step']
        else:
            self._vel_step_second = 1e-5
            self.log.warning('No parameter "vel_second_axis_step" found in config!\n'
                             'Taking 1e-5m/s instead.')

        if 'vel_third_axis_step' in config.keys():
            self._vel_step_third = config['vel_third_axis_step']
        else:
            self._vel_step_third = 1e-5
            self.log.warning('No parameter "vel_third_axis_step" found in config!\n'
                             'Taking 1e-5m/s instead.')
        return 0


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        @return: error code
        """
        self._serial_connection_xyz.close()
        self.rm.close()
        return 0


    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = OrderedDict()

        axis0 = {}
        axis0['label'] = self._first_axis_label
        axis0['ID'] = self._first_axis_ID
        axis0['unit'] = 'm'                 # the SI units
        axis0['ramp'] = None # a possible list of ramps
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
        axis1['unit'] = 'm'        # the SI units
        axis1['ramp'] = None # a possible list of ramps
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
        axis2['unit'] = 'm'        # the SI units
        axis2['ramp'] = None # a possible list of ramps
        axis2['pos_min'] = self._min_third
        axis2['pos_max'] = self._max_third
        axis2['pos_step'] = self.step_third_axis
        axis2['vel_min'] = self._vel_min_third
        axis2['vel_max'] = self._vel_max_third
        axis2['vel_step'] = self._vel_step_third
        axis2['acc_min'] = None
        axis2['acc_max'] = None
        axis2['acc_step'] = None


        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2

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

        # There are sometimes connections problems therefore up to 3 attempts are started
        for attempt in range(3):
            try:
                for axis_label in param_dict:
                    step = param_dict[axis_label]
                    self._do_move_rel(axis_label, step)
            except:
                self.log.warning('Motor connection problem! Try again...')
            else:
                break
        else:
            self.log.error('Motor cannot move!')

        #The following two lines have been commented out to speed up
        #pos = self.get_pos()
        #return pos
        return param_dict

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
        # There are sometimes connections problems therefore up to 3 attempts are started
        for attept in range(3):
            try:
                for axis_label in param_dict:
                    move = param_dict[axis_label]
                    self._do_move_abs(axis_label, move)
                while not self._motor_stopped():
                    time.sleep(0.02)

            except:
                self.log.warning('Motor connection problem! Try again...')
            else:
                break
        else:
            self.log.error('Motor cannot move!')

        #The following two lines have been commented out to speed up
        #pos = self.get_pos()
        #return pos
        return param_dict


    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        constraints = self.get_constraints()
        try:
            for axis_label in constraints:
                self._write_xyz(axis_label,'AB')
            while not self._motor_stopped():
                time.sleep(0.2)
            return 0
        except:
            self.log.error('MOTOR MOVEMENT NOT STOPPED!!!)')
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
        # unfortunately, probably due to connection problems this specific command sometimes failing
        # although it should run.... therefore some retries are added

        try:
            if param_list is not None:
                for axis_label in param_list:
                    for attempt in range(25):
                        # self.log.debug(attempt)
                        try:
                            pos = int(self._ask_xyz(axis_label,'TT')[8:])
                            param_dict[axis_label] = pos * 1e-7
                        except:
                            continue
                        else:
                            break
            else:
                for axis_label in constraints:
                    for attempt in range(25):
                        #self.log.debug(attempt)
                        try:
                            pos = int(self._ask_xyz(axis_label,'TT')[8:])
                            param_dict[axis_label] = pos * 1e-7
                        except:
                            continue
                        else:
                            break
            return param_dict
        except:
            self.log.error('Could not find current xyz motor position')
            return -1

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        The meaning of the return value is:
        Bit 0: Ready Bit 1: On target Bit 2: Reference drive active Bit 3: Joystick ON
        Bit 4: Macro running Bit 5: Motor OFF Bit 6: Brake ON Bit 7: Drive current active
        """
        constraints = self.get_constraints()
        param_dict = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    status = self._ask_xyz(axis_label,'TS')[8:]
                    param_dict[axis_label] = status
            else:
                for axis_label in constraints:
                    status = self._ask_xyz(axis_label, 'TS')[8:]
                    param_dict[axis_label] = status
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

        After calibration the stage moves to home position which will be the
        zero point for the passed axis.

        @return dict pos: dictionary with the current position of the ac#xis
        """


        #constraints = self.get_constraints()
        param_dict = {}
        try:
            for axis_label in param_list:
                self._write_xyz(axis_label,'FE2')
            while not self._motor_stopped():
                time.sleep(0.2)
            for axis_label in param_list:
                self._write_xyz(axis_label,'DH')
        except:
            self.log.error('Calibration did not work')

        for axis_label in param_list:
            param_dict[axis_label] = 0.0
        self.move_abs(param_dict)

        pos = self.get_pos()
        return pos

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes in m/s.

        @param list param_list: optional, if a specific velocity of an axis
                                    is desired, then the labels of the needed
                                    axis should be passed as the param_list.
                                    If nothing is passed, then from each axis the
                                    velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
            """
        constraints = self.get_constraints()
        param_dict = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    vel = int(self._ask_xyz(axis_label, 'TY')[8:])
                    param_dict[axis_label] = vel * 1e-7
            else:
                for axis_label in constraints:
                    vel = int(self._ask_xyz(axis_label, 'TY')[8:])
                    param_dict[axis_label] = vel * 1e-7
            return param_dict
        except:
            self.log.error('Could not find current axis velocity')
            return -1

    def set_velocity(self, param_dict):
        """ Write new value for velocity in m/s.

        @param dict param_dict: dictionary, which passes all the relevant
                                    parameters, which should be changed. Usage:
                                     {'axis_label': <the-velocity-value>}.
                                     'axis_label' must correspond to a label given
                                     to one of the axis.

        @return dict param_dict2: dictionary with the updated axis velocity
        """
        #constraints = self.get_constraints()
        try:
            for axis_label in param_dict:
                vel = int(param_dict[axis_label] * 1.0e7)
                self._write_xyz(axis_label, 'SV{0:d}'.format((vel)))

            #The following two lines have been commented out to speed up
            #param_dict2 = self.get_velocity()
            #retrun param_dict2
            return param_dict

        except:
            self.log.error('Could not set axis velocity')
            return -1



########################## internal methods ##################################


    def _write_xyz(self,axis,command):
        '''this method just sends a command to the motor! DOES NOT RETURN AN ANSWER!
        @param axis string: name of the axis that should be asked

        @param command string: command

        @return error code (0:OK, -1:error)
        '''
        constraints = self.get_constraints()
        try:
            #self.log.info(constraints[axis]['ID'] + command + '\n')
            self._serial_connection_xyz.write(constraints[axis]['ID'] + command + '\n')
            trash=self._read_answer_xyz()   # deletes possible answers
            return 0
        except:
            self.log.error('Command was no accepted')
            return -1

    def _read_answer_xyz(self):
        '''this method reads the answer from the motor!
        @return answer string: answer of motor
        '''

        still_reading = True
        answer=''
        while still_reading == True:
            try:
                answer = answer + self._serial_connection_xyz.read()[:-1]
            except:
                still_reading = False
        #self.log.info(answer)
        return answer

    def _ask_xyz(self,axis,question):
        '''this method combines writing a command and reading the answer
        @param axis string: name of the axis that should be asked

        @param command string: command

        @return answer string: answer of motor
        '''
        constraints = self.get_constraints()
        self._serial_connection_xyz.write(constraints[axis]['ID']+question+'\n')
        answer=self._read_answer_xyz()
        return answer



    def _do_move_rel(self, axis, step):
        """internal method for the relative move

        @param axis string: name of the axis that should be moved

        @param float step: step in millimeter

        @return str axis: axis which is moved
                move float: absolute position to move to
        """
        constraints = self.get_constraints()
        if not(abs(constraints[axis]['pos_step']) < abs(step)):
            self.log.warning('Cannot make the movement of the axis "{0}"'
                'since the step is too small! Ignore command!')
        else:
            current_pos = self.get_pos(axis)[axis]
            move = current_pos + step
            self._do_move_abs(axis, move)
        return axis,move

    def _do_move_abs(self, axis, move):
        """internal method for the absolute move in meter

        @param axis string: name of the axis that should be moved

        @param float move: desired position in millimeter

        @return str axis: axis which is moved
                move float: absolute position to move to
        """
        constraints = self.get_constraints()
        #self.log.info(axis + 'MA{0}'.format(int(move*1e8)))
        if not(constraints[axis]['pos_min'] <= move <= constraints[axis]['pos_max']):
            self.log.warning('Cannot make the movement of the axis "{0}"'
                'since the border [{1},{2}] would be crossed! Ignore command!'
                ''.format(axis, constraints[axis]['pos_min'], constraints[axis]['pos_max']))
        else:
            self._write_xyz(axis,'MA{0}'.format(int(move*1e7)))  # 1e7 to convert meter to SI units
            #self._write_xyz(axis, 'MP')
        return axis, move



    def _in_movement_xyz(self):
        '''this method checks if the magnet is still moving and returns
        a dictionary which of the axis are moving.

        @return: dict param_dict: Dictionary displaying if axis are moving:
        0 for immobile and 1 for moving
        '''
        constraints=self.get_constraints()
        param_dict = {}
        for axis_label in constraints:
            tmp0 = int(self._ask_xyz(constraints[axis_label]['label'],'TS')[8:])
            param_dict[axis_label] = tmp0%2

        return param_dict

    def _motor_stopped(self):
        '''this method checks if the magnet is still moving and returns
            False if it is moving and True of it is immobile

            @return: bool stopped: False for immobile and True for moving
                '''
        param_dict=self._in_movement_xyz()
        stopped=True
        for axis_label in param_dict:
            if param_dict[axis_label] != 0:
                self.log.info(axis_label + ' is moving')
                stopped=False
        return stopped



            #########################################################################################
#########################################################################################
#########################################################################################



