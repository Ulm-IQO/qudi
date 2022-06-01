# -*- coding: utf-8 -*-
"""

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

import re
import time
from core.module import Base
from interface.motor_interface import MotorInterface
import serial
from core.configoption import ConfigOption


class StepperMotor(Base, MotorInterface):
    """todo"""
    _com_port = ConfigOption('comport', 'COM4', missing='warn')
    _baud_rate = ConfigOption('baudrate', 9600, missing='warn')
    _resolution = ConfigOption('resolution', 0.625, missing='warn')
    _unit = ConfigOption('unit', default='step')
    _timeout = ConfigOption('timeout', default=10)
    _write_timeout = ConfigOption('write_timeout', default=0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        self._ser = serial.Serial(
            port=self._com_port,
            baudrate=self._baud_rate,
            timeout=self._timeout,
            writeTimeout=self._write_timeout
        )
        time.sleep(1)
        self._ser.read_until()

        return 0

    def on_deactivate(self):
        self._ser.close()

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

        Example of how a return dict with constraints might look like:
        ==============================================================

        constraints = {}

        axis0 = {}
        axis0['label'] = 'x'    # it is very crucial that this label coincides
                                # with the label set in the config.
        axis0['unit'] = 'm'     # the SI units, only possible m or degree
        axis0['ramp'] = ['Sinus','Linear'], # a possible list of ramps
        axis0['pos_min'] = 0,
        axis0['pos_max'] = 100,  # that is basically the traveling range
        axis0['pos_step'] = 100,
        axis0['vel_min'] = 0,
        axis0['vel_max'] = 100,
        axis0['vel_step'] = 0.01,
        axis0['acc_min'] = 0.1
        axis0['acc_max'] = 0.0
        axis0['acc_step'] = 0.0

        axis1 = {}
        axis1['label'] = 'phi'   that axis label should be obtained from config
        axis1['unit'] = 'degree'        # the SI units
        axis1['ramp'] = ['Sinus','Trapez'], # a possible list of ramps
        axis1['pos_min'] = 0,
        axis1['pos_max'] = 360,  # that is basically the traveling range
        axis1['pos_step'] = 100,
        axis1['vel_min'] = 1,
        axis1['vel_max'] = 20,
        axis1['vel_step'] = 0.1,
        axis1['acc_min'] = None
        axis1['acc_max'] = None
        axis1['acc_step'] = None

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        """
        constraints = {}

        axis0 = {'label': 'x', 'vel_min': (0,), 'vel_max': (10000,), 'resolution': self._resolution, 'unit': self._unit}
        axis1 = {'label': 'y', 'vel_min': (0,), 'vel_max': (10000,), 'resolution': self._resolution, 'unit': self._unit}
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1

        return constraints

    def _check_input(self, value):
        if type(value) == int:
            return value
        else:
            raise TypeError

    def move_rel(self, param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        A smart idea would be to ask the position after the movement.

        @return int: error code (0:OK, -1:error)
        """
        try:
            xvalue = param_dict['x']
            xvalue = self._check_input(xvalue)
        except KeyError:
            xvalue = 0
        except TypeError:
            self.log.error('Input must be an integer')
            raise TypeError
        try:
            yvalue = param_dict['y']
            yvalue = self._check_input(yvalue)
        except KeyError:
            yvalue = 0
        except TypeError:
            self.log.error('Input must be an integer')
            return -1
        if xvalue == 0 and yvalue != 0:
            str_to_ser = "YMOVE_{}_\n".format(yvalue)
        elif xvalue != 0 and yvalue == 0:
            str_to_ser = "XMOVE_{}_\n".format(xvalue)
        elif xvalue != 0 and yvalue != 0:
            str_to_ser = "XY_MOVE_{}_{}_\n".format(xvalue, yvalue)
        try:
            self._ser.write(str_to_ser.encode("utf-8"))
            return 0
        except:
            self.log.error('Command could not be sent to arduino')
            raise ValueError
            return -1

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._ser.write("STOP".encode("utf-8"))

            return 0
        except:

            return -1

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        self._ser.write("POSITION?".encode("utf-8"))
        answer = self._ser.readline()
        list_of_states = re.findall(r"\d+", str(answer))

        return {'x': list_of_states[0], 'y': list_of_states[1]}

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        self._ser.write("ISRUNNING?".encode("utf-8"))
        answer = self._ser.readline()
        list_of_states = re.findall(r"\d", str(answer))

        return {'x': list_of_states[0], 'y': list_of_states[1]}

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
        pass

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        self._ser.write("SPEED?".encode("utf-8"))
        answer = self._ser.readline()
        list_of_states = re.findall(r"\d+.\d+", str(answer))

        return {'x': list_of_states[0], 'y': list_of_states[1]}

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
                xspeed = param_dict['x']
                xspeed = self._check_input(xspeed)
                text = "SPEEDX_{}_".format(xspeed)
                self._ser.write(text.encode("utf-8"))
                time.sleep(.1)
            if 'y' in param_dict:
                yspeed = param_dict['y']
                yspeed = self._check_input(yspeed)
                text = "SPEEDY_{}_".format(yspeed)
                self._ser.write(text.encode("utf-8"))
            return 0
        except:
            return -1
