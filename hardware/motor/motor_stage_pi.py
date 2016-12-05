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
import serial

from core.base import Base
from interface.motor_interface import MotorInterface

class MotorStagePI(Base, MotorInterface):
    """unstable: Christoph Müller, Simon Schmitt
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MotorStagePI'
    _modtype = 'hardware'
    # connectors
    _out = {'motorstage': 'MotorInterface'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # should be in config I guess

        #axis definition:
        self._x_axis_label = 'x'
        self._y_axis_label = 'y'
        self._z_axis_label = 'z'

        self._x_axis_ID = '1'
        self._y_axis_ID = '3'
        self._z_axis_ID = '2'


#FIXME:  vielleicht sollte überall .ask anstatt .write genommen werden,
#        da die stage glaube ich immer was zurückgibt....


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


        self.rm = visa.ResourceManager()
        self._serial_connection_xyz = self.rm.open_resource(resource_name=self._com_port_pi_xyz,
                                                            baud_rate=self._pi_xyz_baud_rate,
                                                            timeout=self._pi_xyz_timeout)

        # Should be in config I guess

        # setting the ranges of the axes - factor 10000. needed to have everything in millimeters
        if 'pi_x_min' in config.keys():
            self._min_x = config['pi_x_min'] * 10000.
        else:
            self._min_x = -100. * 10000.
            self.log.warning('No parameter "pi_x_min" found in config!\n'
                    'Taking -100mm instead.')
        if 'pi_x_max' in config.keys():
            self._max_x = config['pi_x_max'] * 10000.
        else:
            self._max_x = 100. * 10000.
            self.log.warning('No parameter "pi_x_max" found in config!\n'
                    'Taking 100mm instead.')
        if 'pi_y_min' in config.keys():
            self._min_y = config['pi_y_min'] * 10000.
        else:
            self._min_y = -100. * 10000.
            self.log.warning('No parameter "pi_y_min" found in config!\n'
                    'Taking -100mm instead.')
        if 'pi_y_max' in config.keys():
            self._max_y = config['pi_y_max'] * 10000.
        else:
            self._max_y = 100. * 10000.
            self.log.warning('No parameter "pi_y_max" found in config!\n'
                    'Taking 100mm instead.')
        if 'pi_z_min' in config.keys():
            self._min_z = config['pi_z_min'] * 10000.
        else:
            self._min_z = -100. * 10000.
            self.log.warning('No parameter "pi_z_min" found in config!\n'
                    'Taking -100mm instead.')
        if 'pi_z_max' in config.keys():
            self._max_z = config['pi_z_max'] * 10000.
        else:
            self._max_z = 100. * 10000.
            self.log.warning('No parameter "pi_z_max" found in config!\n'
                    'Taking 100mm instead.')


    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self._serial_connection_xyz.close()
        self.rm.close()


    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = {}

        axis0 = {}
        axis0['label'] = self._x_axis_label # '1'
        axis0['ID'] = self._x_axis_ID
        axis0['unit'] = 'mm'                 # the SI units
        axis0['ramp'] = None # a possible list of ramps
        axis0['pos_min'] = self._min_x
        axis0['pos_max'] = self._max_x
        axis0['pos_step'] = 0.001
        axis0['vel_min'] = None
        axis0['vel_max'] = None
        axis0['vel_step'] = None
        axis0['acc_min'] = None
        axis0['acc_max'] = None
        axis0['acc_step'] = None

        axis1 = {}
        axis1['label'] = self._y_axis_label # '3'
        axis1['ID'] = self._y_axis_ID
        axis1['unit'] = 'mm'        # the SI units
        axis1['ramp'] = None # a possible list of ramps
        axis1['pos_min'] = self._min_y
        axis1['pos_max'] = self._max_y
        axis1['pos_step'] = 0.001
        axis1['vel_min'] = None
        axis1['vel_max'] = None
        axis1['vel_step'] = None
        axis1['acc_min'] = None
        axis1['acc_max'] = None
        axis1['acc_step'] = None

        axis2 = {}
        axis2['label'] = self._z_axis_label # '2'
        axis2['ID'] = self._z_axis_ID
        axis2['unit'] = 'mm'        # the SI units
        axis2['ramp'] = None # a possible list of ramps
        axis2['pos_min'] = self._min_z
        axis2['pos_max'] = self._max_z
        axis2['pos_step'] = 0.001
        axis2['vel_min'] = None
        axis2['vel_max'] = None
        axis2['vel_step'] = None
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
                                The values for the axes are in millimeter.

        @return int: error code (0:OK, -1:error)
        """
        try:
            if 'x' in param_dict:
                step = int(param_dict['x']*10000)
                self._do_move_rel('x', step)
            if 'y' in param_dict:
                step = int(param_dict['y']*10000)
                self._do_move_rel('y', step)
            if 'z' in param_dict:
                step = int(param_dict['z']*10000)
                self._do_move_rel('z', step)
            return 0
        except:
            return -1


    def _do_move_rel(self, axis, step):
        """internal method for the relative move

        @param axis string: name of the axis that should be moved

        @param float step: step in millimeter
        """
        current_pos = self._internal_get_pos('z')
        move = current_pos + step
        self._do_move_abs(axis, move)


    def move_abs(self, param_dict):
        """Moves stage to absolute position

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                The values for the axes are in millimeter,
                                the value for the rotation is in degrees.

        @return int: error code (0:OK, -1:error)
        """
        try:
            if 'x' in param_dict:
                move = int(param_dict['x']*10000)
                self._do_move_abs('x', move)
            if 'y' in param_dict:
                move = int(param_dict['y']*10000)
                self._do_move_abs('y', move)
            if 'z' in param_dict:
                move = int(param_dict['z']*10000)
                self._do_move_abs('z', move)

            [a, b, c] = self._in_movement_xyz()
            while a != 0 or b != 0 or c != 0:
                print('xyz-stage moving...')
                [a, b, c] = self._in_movement_xyz()
                time.sleep(0.2)

            print('stage ready')
            return 0
        except:
            return -1


    def _do_move_abs(self, axis, move):
        """internal method for the absolute move

        @param axis string: name of the axis that should be moved

        @param float move: desired position in millimeter
        """
        #constraints = self.get_constraints()
        self.log.info(axis + 'MA{0!s}'.format(move))
        # if not(constraints[axis]['pos_min'] <= move <= constraints[axis]['pos_max']):
        #     self.log.warning('Cannot make the movement of the axis "{0}"'
        #         'since the border [{1},{2}] would be crossed! Ignore command!'
        #         ''.format(axis, constraints[axis]['pos_min'], constraints[axis]['pos_max']))
        #else:
        self._write_xyz(axis,'MA{0!s}'.format(move))




    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        constraints = self.get_constraints()
        try:
            self._write_xyz('x','AB')
            self._write_xyz('y', 'AB')
            self._write_xyz('z', 'AB')
            return 0
        except:
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
        zero point for the passed axis.
        """
        #TODO: implement calibration x, y and z
        try:
            if param_list is not None and set(['x','y','z']) <= set(param_list) or param_list is None:
                self._calibrate_xyz()
            if param_list is not None and 'x' in param_list or param_list is None:
                self._calibrate_axis('x')
            if param_list is not None and 'y' in param_list or param_list is None:
                self._calibrate_axis('y')
            if param_list is not None and 'z' in param_list or param_list is None:
                self._calibrate_axis('z')
            return 0
        except:
            return -1 #maybe return the new position here?



    def _calibrate_xyz(self):
        """ internal method to calibrate xyz simultaneously """

        self._serial_connection_xyz.write('123MA-2500000\n')

        [a, b, c] = self._in_movement_xyz()
        while a != 0 or b != 0 or c != 0:
            self.log.info('moving to the corner...')
            [a, b, c] = self._in_movement_xyz()
            self.log.info('moving on x-Axis: ', a)
            self.log.info('moving on y-Axis: ', b)
            self.log.info('moving on z-Axis: ', c,'\n')
            time.sleep(0.5)
            self.log.info('in edge')

        self._serial_connection_xyz.write('123DH\n')
        self._serial_connection_xyz.write('123MA900000\n')
        time.sleep(.1)
        self.log.info(str(self._serial_connection_xyz.read(17)))
        self.log.info('define the tmps')
        [a, b, c] = self._in_movement_xyz()
        while a != 0 or b != 0 or c != 0:
            self.log.info('moving to the center...')
            [a, b, c] = self._in_movement_xyz()
            self.log.info('moving on x-Axis: ', a)
            self.log.info('moving on y-Axis: ', b)
            self.log.info('moving on z-Axis: ', c,'\n')
            time.sleep(0.5)
            self.log.info('fast movement finished')

        time.sleep(0.1)
        self._serial_connection_xyz.write('13FE1\n')
        self.log.info(self._read_xyz())
        [a, b, c] = self._in_movement_xyz()
        while a != 0 or b != 0 or c != 0:
            self.log.info('find centerposition...')
            [a, b, c] = self._in_movement_xyz()
            self.log.info('moving on x-Axis: ', a)
            self.log.info('moving on y-Axis: ', b)
            self.log.info('moving on z-Axis: ', c,'\n')
            time.sleep(0.5)

        self._serial_connection_xyz.write('123DH\n')
        self.log.info('calibration finished')


    def _calibrate_axis(self, axis):
        """ internal method to calibrate individual axis

        @param axis string: name of the axis that should be calibrated
        """
        constraints = self.get_constraints()

        self._serial_connection_xyz.write(constraints[axis]['ID']+'MA-2500000\n')

        [a, b, c] = self._in_movement_xyz()
        while a != 0 or b != 0 or c != 0:
            self.log.info('moving to the corner...')
            [a, b, c] = self._in_movement_xyz()
            time.sleep(0.5)
        self.log.info('in edge')

        self._serial_connection_xyz.write(constraints[axis]['ID']+'DH\n')
        self._serial_connection_xyz.write(constraints[axis]['ID']+'MA900000\n')
        time.sleep(.1)
        self.log.info(str(self._read_answer_xyz()))
        self.log.info('define the tmps')
        [a, b, c] = self._in_movement_xyz()
        while a != 0 or b != 0 or c != 0:
            self.log.info('moving to the center...')
            [a, b, c] = self._in_movement_xyz()
            time.sleep(0.5)
        self.log.info('fast movement finished')

        time.sleep(0.1)
        if axis in ('x', 'y'):
            self._serial_connection_xyz.write(constraints[axis]['ID']+'FE1\n')
            self.log.info(self._serial_connection_xyz._read_answer_xyz())
            [a, b, c] = self._in_movement_xyz()
            while a != 0 or b != 0 or c != 0:
                self.log.info('find centerposition...')
                [a, b, c] = self._in_movement_xyz()

        self._serial_connection_xyz.write(constraints[axis]['ID']+'DH\n')
        self.log.info('calibration finished')





    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        try:
            if 'x' in param_dict:
                vel = int(param_dict['x']*10000)
                self._write_xyz('x','SV{0:d}'.format((vel)))
            if 'y' in param_dict:
                vel = int(param_dict['y']*10000)
                self._write_xyz('y', 'SV{0:d}'.format((vel)))
            if 'z' in param_dict:
                vel = int(param_dict['z']*10000)
                self._write_xyz('z', 'SV{0:d}'.format((vel)))
            return 0
        except:
            return -1



########################## internal methods ##################################


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
        try:
            if param_list is not None and 'x' in param_list or param_list is None:
                x_value = int(self._ask_xyz('x','TT')[8:])
                param_dict['x'] = x_value
            if param_list is not None and 'y' in param_list or param_list is None:
                y_value = int(self._ask_xyz('y', 'TT')[8:])
                param_dict['y'] = y_value
            if param_list is not None and 'z' in param_list or param_list is None:
                z_value = int(self._ask_xyz('z', 'TT')[8:])
                param_dict['z'] = z_value
            return param_dict
        except:
            self.log.error('Could not find current magnet position')
            return -1

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
        param_dict = {}
        try:
            if param_list is not None and 'x' in param_list or param_list is None:
                x_vel = int(self._ask_xyz('x','TY')[8:])
                param_dict['x'] = x_vel/10000.
            if param_list is not None and 'y' in param_list or param_list is None:
                y_vel = int(self._ask_xyz('y','TY')[8:])
                param_dict['y'] = y_vel/10000.
            if param_list is not None and 'z' in param_list or param_list is None:
                z_vel = int(self._ask_xyz('z','TY')[8:])
                param_dict['z'] = z_vel/10000.
            return param_dict
        except:
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
            if param_list is not None and 'x' in param_list or param_list is None:
                x_status = self._ask_xyz('x','TS')[8:]
                time.sleep(0.1)
                param_dict['x'] = x_status
            if param_list is not None and 'y' in param_list or param_list is None:
                y_status = self._ask_xyz('y','TS')[8:]
                time.sleep(0.1)
                param_dict['y'] = y_status
            if param_list is not None and 'z' in param_list or param_list is None:
                z_status = self._ask_xyz('z','TS')[8:]
                time.sleep(0.1)
                param_dict['z'] = z_status
            return param_dict
        except:
            return -1



    def _in_movement_xyz(self):
        '''this method checks if the magnet is still moving and returns
        a list which of the axis are moving.
        Ex: return is [1,1,0]-> x and y ax are moving and z axis is imobile.
        '''
        tmpx = int(self._ask_xyz('x','TS')[8:])
        self.log.warning(tmpx%2)
        time.sleep(0.1)
        tmpy = int(self._ask_xyz('y','TS')[8:])
        self.log.warning(tmpy)
        time.sleep(0.1)
        tmpz = int(self._ask_xyz('z','TS')[8:])
        self.log.warning(tmpz)
        time.sleep(0.1)
        return [tmpx%2, tmpy%2, tmpz%2]

    def _read_answer_xyz(self):
        still_reading = True
        answer=''
        while still_reading == True:
            try:
                answer = answer + self._serial_connection_xyz.read()[:-1]
            except:
                still_reading = False
        self.log.info(answer)
        return answer

    def _ask_xyz(self,axis,question):
        constraints = self.get_constraints()
        self.log.warning(constraints[axis]['ID']+question+'\n')
        self._serial_connection_xyz.write(constraints[axis]['ID']+question+'\n')
        answer=self._read_answer_xyz()
        return answer

    def _write_xyz(self,axis,command):
        constraints = self.get_constraints()
        try:
            self._serial_connection_xyz.write(constraints[axis]['ID'] + command + '\n')
            trash=self._read_answer_xyz()
            return 0
        except:
            self.log.error('Command was no accepted')
            return -1

      #########################################################################################
#########################################################################################
#########################################################################################



