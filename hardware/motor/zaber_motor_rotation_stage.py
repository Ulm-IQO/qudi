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

import time
import serial
from collections import OrderedDict

from core.module import Base, ConfigOption
from interface.motor_interface import MotorInterface

class MotorRotationZaber(Base, MotorInterface):
    """unstable: Christoph Müller, Simon Schmitt
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MotorRotation'
    _modtype = 'hardware'

    _com_port_rot = ConfigOption('com_port_zaber', 'ASRL1::INSTR', missing='warn')
    _rot_baud_rate = ConfigOption('zaber_baud_rate', 9600, missing='warn')
    _rot_timeout = ConfigOption('zaber_timeout', 5000, missing='warn')     #TIMEOUT shorter?
    _rot_term_char = ConfigOption('zaber_term_char', '\n', missing='warn')

    _axis_label = ConfigOption('zaber_axis_label', 'phi', missing='warn')
    _min_angle = ConfigOption('zaber_angle_min', -1e5, missing='warn')
    _max_angle = ConfigOption('zaber_angle_max', 1e5, missing='warn')
    _min_step = ConfigOption('zaber_angle_step', 1e-5, missing='warn')

    _min_vel = ConfigOption('zaber_velocity_min', 1e-3, missing='warn')
    _max_vel = ConfigOption('zaber_velocity_max', 10, missing='warn')
    _step_vel = ConfigOption('zaber_velocity_step', 1e-3, missing='warn')

    _micro_step_size = ConfigOption('zaber_micro_step_size', 234.375e-6, missing='warn')
    velocity_conversion = ConfigOption('zaber_speed_conversion', 9.375, missing='warn')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._serial_connection_rot = serial.Serial(
            port=self._com_port_rot,
            baudrate=self._rot_baud_rate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=self._rot_timeout)

        return 0


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._serial_connection_rot.close()
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

        rot = {}
        rot['label'] = self._axis_label
        rot['ID'] = None
        rot['unit'] = '°'
        rot['ramp'] = None
        rot['pos_min'] = self._min_angle
        rot['pos_max'] = self._max_angle
        rot['pos_step'] = self._min_step
        rot['vel_min'] = self._min_vel
        rot['vel_max'] = self._max_vel
        rot['vel_step'] = self._step_vel
        rot['acc_min'] = None
        rot['acc_max'] = None
        rot['acc_step'] = None

        # assign the parameter container to a name which will identify it
        constraints[rot['label']] = rot
        return constraints


    def move_rel(self, param_dict):
        """Moves stage by a given angle (relative movement)

        @param dict param_dict: Dictionary with axis name and relative movement in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        pos={}
        try:
            for axis_label in param_dict:
                angle = param_dict[axis_label]
                if abs(angle) >= self._micro_step_size:
                    data = int(angle / self._micro_step_size)
                    self._write_rot([1,21,data])
                    pos[axis_label] = self._read_answer_rot() * self._micro_step_size # stage sends signal after motion finished
                else:
                    self.log.warning('Desired step "{0}" is too small. Minimum is "{1}"'
                                        .format(angle, self._micro_step_size))
                    pos = self.get_pos(param_dict.keys())
        except:
            self.log.error('relative movement of zaber rotation stage is not possible')
            pos = self.get_pos(param_dict.keys())
        return pos


    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        pos = {}
        try:
            for axis_label in param_dict:
                angle = param_dict[axis_label]
                data = int(self._map_angle(angle) / self._micro_step_size)
                self._write_rot([1,20,data])
                pos[axis_label] = self._read_answer_rot() * self._micro_step_size  # stage sends signal after motion finished
        except:
            self.log.error('absolute movement of zaber rotation stage is not possible')
            pos = self.get_pos(param_dict.keys())
        return pos



    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._write_rot([1, 23, 0])
            while not self._motor_stopped():
                time.sleep(0.2)
            return 0
        except:
            self.log.error('ROTATIONAL MOVEMENT NOT STOPPED!!!)')
            return -1


    def get_pos(self,param_list=None):
        """ Gets current position of the rotation stage

        @param list param_list: List with axis name

        @return dict pos: Dictionary with axis name and pos in deg    """
        constraints = self.get_constraints()
        try:
            pos = {}
            if param_list is not None:
                for axis_label in param_list:
                    answer = self._ask_rot([1, 60, 0])
                    time.sleep(0.2)
                    pos[axis_label] = answer * self._micro_step_size
                    return pos
            else:
                for axis_label in constraints:
                    answer = self._ask_rot([1, 60, 0])
                    time.sleep(0.2)
                    pos[axis_label] = answer * self._micro_step_size
                    return pos
        except:
            self.log.error('Cannot find position of zaber-rotation-stage')
            return -1


    def get_status(self,param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict status:   · 0 - idle, not currently executing any instructions
                        · 1 - executing a home instruction
                        · 10 - executing a manual move (i.e. the manual control knob is turned)
                        · 20 - executing a move absolute instruction
                        · 21 - executing a move relative instruction
                        · 22 - executing a move at constant speed instruction
                        · 23 - executing a stop instruction (i.e. decelerating)
                                """
        constraints = self.get_constraints()
        status = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    status[axis_label] = self._ask_rot([1, 54, 0])
                    time.sleep(0.1)
                    return status
            else:
                for axis_label in constraints:
                    status[axis_label] = self._ask_rot([1, 54, 0])
                    time.sleep(0.1)
                    return status
        except:
            self.log.error('Could not get status')
            return -1



    def calibrate(self, param_list=None):
        """ Calibrates the rotation motor

        @param list param_list: Dictionary with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        constraints = self.get_constraints()
        pos = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    self._write_rot([1, 1, 0])
                    pos[axis_label] = self._read_answer_rot() * self._micro_step_size # stage sends signal after motion finished
            else:
                for axis_label in constraints:
                    self._write_rot([1, 1, 0])
                    pos[axis_label] = self._read_answer_rot() * self._micro_step_size # stage sends signal after motion finished
        except:
            self.log.error('Could not calibrate zaber rotation stage!')
            pos = self.get_pos()
        return pos


    def get_velocity(self, param_list=None):
        """ Asks current value for velocity.

        @param list param_list: Dictionary with axis name

        @return dict velocity: Dictionary with axis name and velocity in deg/s
        """
        constraints = self.get_constraints()
        velocity = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    data = self._ask_rot([1, 53, 42])
                    velocity[axis_label] = data*self.velocity_conversion*self._micro_step_size
            else:
                for axis_label in constraints:
                    data = self._ask_rot([1, 53, 42])
                    velocity[axis_label] = data*self.velocity_conversion*self._micro_step_size
            return velocity
        except:
            self.log.error('Could not set rotational velocity')
            return -1



    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: Dictionary with axis name and target velocity in deg/s

        @return dict velocity: Dictionary with axis name and target velocity in deg/s
        """
        velocity = {}
        try:
            for axis_label in param_dict:
                speed = param_dict[axis_label]
                if speed <= self._max_vel:
                    speed  = int(speed/self.velocity_conversion/self._micro_step_size)
                    self._write_rot([1,42, speed])
                    velocity[axis_label] = self._read_answer_rot()*self.velocity_conversion*self._micro_step_size  # stage sends signal after motion finished
                else:
                    self.log.warning('Desired velocity "{0}" is too high. Maximum is "{1}"'
                                     .format(velocity,self._max_vel))
                    velocity = self.get_velocity()
        except:
            self.log.error('Could not set rotational velocity')
            velocity = self.get_velocity()
        return velocity



########################## internal methods ##################################


    def _write_rot(self, list):
        ''' sending a command encode in a list to the rotation stage,
        requires [1, commandnumber, value]

        @param list list: command in a list form

        @return errorcode'''

        try:
            xx = list[0]
            yy = list[1]
            zz = list[2]
            z4 = 0
            z3 = 0
            z2 = 0
            z1 = 0
            base = 256

            if zz >= 0:
                if zz/base**3 >= 1:
                    z4 = int(zz/base**3)   #since  int(8.9999)=8  !
                    zz -= z4*base**3
                if zz/base**2 >= 1:
                    z3 = int(zz/base**2)
                    zz -= z3*base**2
                if zz/base >= 1:
                    z2 = int(zz/base)
                    zz -= z2*base
                z1 = zz
            else:
                z4 = 255
                zz += base**3
                if zz/base**2 >= 1:
                    z3 =int(zz/base**2)
                    zz -= z3*base**2
                if zz/base >= 1:
                    z2 = int(zz/base)
                    zz -= z2*base
                z1 = zz

            sends = [xx,yy,z1,z2,z3,z4]

            for ii in range (6):
                self._serial_connection_rot.write(chr(sends[ii]).encode('latin'))
            return 0
        except:
            self.log.error('Command was not sent to zaber rotation stage')
            return -1

    def _read_answer_rot(self):
        '''this method reads the answer from the motor!
        return 6 bytes from the receive buffer
        there must be 6 bytes to receive (no error checking)

        @return answer float: answer of motor coded in a single float
        '''


        r = [0, 0, 0, 0, 0, 0]
        for i in range(6):
            r[i] = ord(self._serial_connection_rot.read(1))
        yy = r[1]
        z1 = r[2]
        z2 = r[3]
        z3 = r[4]
        z4 = r[5]
        answer = z1 + z2 * 256 + z3 * 256 ** 2 + z4 * 256 ** 3

        if yy == 255:                        #yy is command number and 255 implies error
            self.log.error('error nr. ' + str(answer))
        return answer


    def _ask_rot(self,list):
        '''this method combines writing a command and reading the answer
        @param list list: list encoded command

        @return answer float: answer of motor coded in a single float
        '''
        self._write_rot(list)
        time.sleep(0.1)
        answer=self._read_answer_rot()
        return answer

    def _motor_stopped(self):
        '''checks if the rotation stage is still moving
        @return: bool stopped: True if motor is not moving, False otherwise'''

        stopped=True
        status = self.get_status()
        if status:
            stopped=False
        return stopped

    def _map_angle(self, init_angle):
        '''maps the angle if larger or lower than 360° to inbetween 0° and 360°

        @params init_angle: initial angle, possible not element of {0°,360°}

        @return: float angle: Angle between 0° and 360°'''

        angle = init_angle%360

        return angle




      #########################################################################################
#########################################################################################
#########################################################################################



