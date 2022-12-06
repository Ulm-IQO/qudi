# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control motorized stages.

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

import serial
from collections import OrderedDict

from core.module import Base
from core.configoption import ConfigOption
from interface.motor_interface import MotorInterface
from core.statusvariable import StatusVar


# class NewportConexLTAAxis:
#
#     def __init__(self, axis_label, com_port):
#         self.axis_label = axis_label
#         self.com = com_port+'Hi'

class NewportConexLTAAxis:
    def __init__(self, axis_label, com_port):
        self._com_port = com_port
        self._serial_connection = serial.Serial(
            port=self._com_port,
            baudrate=921600,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=True)

        self._controller_address = 1

        self.axis_label = axis_label

        # self._velocity = self.vel_from_model[model]
        # self._axis_unit = self.unit_from_model[model] # User defined units?

        self._min_position = float(self.query('SL'))*1.e-3
        self._max_position = float(self.query('SR'))*1.e-3

    @property
    def min_position(self):
        return self._min_position

    @property
    def max_position(self):
        return self._max_position

    @property
    def position(self):
        return float(self.query('TP'))*1.e-3

    @property
    def min_velocity(self):
        return 1.e-6

    @property
    def max_velocity(self):
        return 5.e-3

    @property
    def velocity(self):
        return float(self.query('VA'))*1e-3

    @velocity.setter
    def velocity(self, velo):
        assert self.min_velocity <= velo <= self.max_velocity,\
            f'Velocity {velo} not in range from ({self.min_velocity}, {self.max_velocity})'
        self.write_value('VA', velo*1e3)
        self.read_error()

    def _set_position_limits(self, lower=None, upper=None):
        if lower is not None and upper is not None:
            assert lower < upper, f'Lower limit higher or equal to upper limit'

        if lower is not None:
            self.write_value('SL', float(lower)*1e3)
            self.read_error()
            self._min_position = float(self.query('SL'))/1e3
            self.read_error()

        if upper is not None:
            self.write_value('SR', float(upper)*1e3)
            self.read_error()
            self._max_position = float(self.query('SR'))/1e3
            self.read_error()

    def get_constraints(self):
        constraints = dict()
        constraints['label'] = self.axis_label
        constraints['unit'] = 'm'
        constraints['pos_step'] = float(self.query('SU'))
        constraints['min_pos'] = self.min_position
        constraints['max_pos'] = self.max_position
        constraints['min_vel'] = self.min_velocity
        constraints['max_vel'] = self.max_velocity

        return constraints

    def stop_motion(self):
        self.write('ST')
        self.read_error()  # Somehow I always get an Error "C" when asking the Controller after the stop ...

    def move_relative(self, distance):
        # pos = self.position
        # assert self._min_position < pos + distance < self.max_position, \
        #     f'Relative move would be out of software limits'
        self.write_value('PR', distance*1.e3)
        self.read_error()

    def move_absolut(self, position):
        self.write_value('PA', position*1.e3)
        self.read_error()

    @property
    def is_moving(self):
        self.read_error()
        err_and_state = self.query('TS')
        if err_and_state[:4] != '0000':
            raise RuntimeError(f'Command TS gave an error {err_and_state[:4]} in state {err_and_state[-2:]}')
        if err_and_state[-2:] == '28':
            return True
        elif err_and_state[-2:] in ('32', '33', '34'):
            return False
        else:
            raise ValueError(f'Unknown state {err_and_state[-2:]} encountered')

    # @property
    # def is_moving(self):
    #     self.query('TS')[-2]  # This would also clear the error buffer ... should not do like that

    def query(self, command):
        """ Get a variable from the controller
            @param command: two-letter command for controller

            @return str: answer from controller
        """
        cmd = '{0:02d}{1:s}?\r\n'.format(self._controller_address, command).encode('ascii')
        self._serial_connection.write(cmd)
        ret = self._serial_connection.read_until(b'\r\n')
        if cmd[0:4] != ret[0:4]:
            raise ValueError('Command {0} preamble not equal to reply {1} preamble'
                             .format(cmd.decode('ascii'), ret.decode('ascii')))
        return ret[4:].decode('ascii').rstrip()

    def write_value(self, command, value):
        """ Write a value to the controller

        @param command: two-letter command/variable for controller
        @param value: value to write to controller
        """
        cmd = '{0:02d}{1:s}{2}\r\n'.format(self._controller_address, command, value).encode('ascii')
        self._serial_connection.write(cmd)

    def write(self, command):
        """ Write a single command

        @param command: two-letter command for controller
        """
        cmd = '{0:02d}{1:s}\r\n'.format(self._controller_address, command).encode('ascii')
        self._serial_connection.write(cmd)

    def read(self):
        """ Read an answer from the controller

        @return str:
        """
        ret = self._serial_connection.read_until(b'\r\n')
        return ret[4:].decode('ascii').rstrip()

    def read_error(self):
        """

        @return bool, str:
        """
        err = self.query('TE')
        if len(err) > 0 and err[0] != '@':
            self.write_value('TB', err[0])
            err_str = self.read()
            raise ValueError('Motor Error occurred with error string: {0}'.format(err_str))

    def disconnect(self):
        self._serial_connection.close()

    def disable(self):
        self.write('MM0')

    def enable(self):
        self.write('MM1')


class NewportConexLTA(Base, MotorInterface):
    """ This is the Interface class to define the controls for the simple
        step motor device. The actual hardware implementation might have a
        different amount of axis. Implement each single axis as 'private'
        methods for the hardware class, which get called by the general method.
    """

    _axes_conn = ConfigOption('axes')

    _limits = StatusVar(default=dict())

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._axes = OrderedDict({ax: NewportConexLTAAxis(ax, com) for ax, com in self._axes_conn.items()})

        if len(self._limits) == 0:
            self.log.error('Limits are empty. Set the position limits.')
        else:
            cstr = self.get_constraints()
            for ax in cstr:
                if cstr[ax]['min_pos'] == 0.0 or cstr[ax]['max_pos'] == 50.e-3:
                    self._axes[ax]._set_position_limits(**self._limits[ax])
                    self.log.warning(f'Position limits updated on module activation '
                                     f'for axes {ax} and limits {self._limits[ax]}')

    def on_deactivate(self):
        """ Initialisation performed during activation of the module.
        """
        #
        cstr = self.get_constraints()
        for ax_name in self._axes:
            self._limits[ax_name] = dict(lower=cstr[ax_name]['min_pos'], upper=cstr[ax_name]['max_pos'])

        for ax in self._axes.values():
            ax.disconnect()

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
        return {ax.axis_label: ax.get_constraints() for ax in self._axes.values()}

    def move_rel(self,  param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        A smart idea would be to ask the position after the movement.

        @return int: error code (0:OK, -1:error)
        """
        assert all([elem in self._axes for elem in param_dict.keys()]), f'Invalid axes in param_dict {param_dict}.' \
                                                                        f'Should be in {self._axes.keys()}'
        for ax, dist in param_dict.items():
            try:
                self._axes[ax].move_relative(dist)
            except AssertionError as e:
                self.log.error(f'Could not move_rel for axes {ax} due to {e}')
            except ValueError as e:
                if ' M ' not in str(e):  # if M in error, one tried to move, while still moving the same axis.
                    self.log.warning(f'Ignoring error {e} while move on axis {ax}')

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        assert all([elem in self._axes for elem in param_dict.keys()]), f'Invalid axes in param_dict {param_dict}.' \
                                                                        f'Should be in {self._axes.keys()}'
        for ax, dist in param_dict.items():
            try:
                self._axes[ax].move_absolut(dist)
            except AssertionError as e:
                self.log.error(f'Could not move_abs axes {ax} due to {e}')
            except ValueError as e:
                if ' M ' not in str(e):  # if M in error, one tried to move, while still moving the same axis.
                    self.log.warning(f'Ignoring error {e} while move on axis {ax}')

    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        for ax in self._axes.values():
            try:
                ax.stop_motion()
            except ValueError as e:
                if ' C ' not in str(e):  # Somehow I always get an Error "C" when asking the Controller after the stop.
                    self.log.warning(f'Ignoring error {e} on stop of axis {ax}')

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
        if param_list is not None:
            assert all([elem in self._axes for elem in param_list]), f'Invalid axes in param_list {param_list}.' \
                                                                     f'Should be in {self._axes.keys()}'
            return {key: self._axes[key].position for key in param_list}
        else:
            return {key: ax.position for key, ax in self._axes.items()}

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
            d = {}
            for ax, hw_ax in self._axes.items():
                d[ax] = {'moving': hw_ax.is_moving}
            return d
        else:
            d = {}
            assert isinstance(param_list, list) or isinstance(param_list, tuple)
            for ax in param_list:
                d[ax] = {'moving': self._axes[ax].is_moving}
            return d




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
        if param_list is not None:
            assert all([elem in self._axes for elem in param_list]), f'Invalid axes in param_list {param_list}.' \
                                                                     f'Should be in {self._axes.keys()}'
            return {key: self._axes[key].velocity for key in param_list}
        else:
            return {key: ax.velocity for key, ax in self._axes.items()}

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        assert all([elem in self._axes for elem in param_dict.keys()]), f'Invalid axes in param_dict {param_dict}.' \
                                                                        f'Should be in {self._axes.keys()}'
        for ax, velo in param_dict.items():
            try:
                self._axes[ax].velocity = velo
            except AssertionError as e:
                self.log.error(f'Could not set velocity for axes {ax} due to {e}')

    @property
    def x(self):
        return self._axes['conex_x']

    @property
    def y(self):
        return self._axes['conex_y']

    def disable(self):
        for ax in self._axes.values():
            ax.disable()

    def enable(self):
        for ax in self._axes.values():
            ax.enable()
