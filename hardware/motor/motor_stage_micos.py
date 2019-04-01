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
from core.module import Base, ConfigOption
from core.util.mutex import Mutex
from interface.motor_interface import MotorInterface


class MotorStageMicos(Base, MotorInterface):
    """
    Hardware class to define the controls for the Micos stage of PI.

    Example config for copy-paste:

    motorstage_micos:
        module.Class: 'motor.motor_stage_micos.MotorStageMicos'
        com_port_xy: 'COM1'
        baud_rate_xy: 115200
        timeout_xy: 2
        com_port_zphi: 'COM3'
        baud_rate_zphi: 115200
        timeout_zphi: 2

        x_velocity: 1e-3 # in m/s
        y_velocity: 1e-3 # in m/s
        z_velocity: 1e-3 # in m/s
        phi_velocity: 5 # in °/s

        x_position_range: [0, 0.1] # in m
        y_position_range: [0, 0.1] # in m
        z_position_range: [0, 0.1] # in m
        phi_position_range: [0, 360] # in °

        x_velocity_range: [0.1e-6, 5e-2] # in m/s
        y_velocity_range: [0.1e-6, 5e-2] # in m/s
        z_velocity_range: [0.1e-6, 5e-2] # in m/s
        phi_velocity_range: [0.1, 10] # in °/s
    """
    _modclass = 'MotorStageMicos'
    _modtype = 'hardware'

    _max_position_range = {'x': (0, 0.1), 'y': (0, 0.1), 'z': (0, 0.1), 'phi': (0, 360)}
    _max_velocity_range = {'x': (0.1e-6, 5e-2),
                           'y': (0.1e-6, 5e-2),
                           'z': (0.1e-6, 5e-2),
                           'phi': (0.1, 10)}

    _com_port_xy = ConfigOption('com_port_xy', missing='error')
    _baud_rate_xy = ConfigOption('baud_rate_xy', default=115200)
    _timeout_xy = ConfigOption('timeout_xy', default=2)
    _com_port_zphi = ConfigOption('com_port_zphi', missing='error')
    _baud_rate_zphi = ConfigOption('baud_rate_zphi', default=115200)
    _timeout_zphi = ConfigOption('timeout_zphi', default=2)

    _x_velocity = ConfigOption('x_velocity', default=None, missing='warn')
    _y_velocity = ConfigOption('y_velocity', default=None, missing='warn')
    _z_velocity = ConfigOption('z_velocity', default=None, missing='warn')
    _phi_velocity = ConfigOption('phi_velocity', default=None, missing='warn')

    _x_position_range = ConfigOption('x_position_range', default=None, missing='warn')
    _y_position_range = ConfigOption('y_position_range', default=None, missing='warn')
    _z_position_range = ConfigOption('z_position_range', default=None, missing='warn')
    _phi_position_range = ConfigOption('phi_position_range', default=None, missing='warn')

    _x_velocity_range = ConfigOption('x_velocity_range', default=None)
    _y_velocity_range = ConfigOption('y_velocity_range', default=None)
    _z_velocity_range = ConfigOption('z_velocity_range', default=None)
    _phi_velocity_range = ConfigOption('phi_velocity_range', default=None)

    error_codes = {0: 'no error',
                   1: 'internal error',
                   2: 'internal error',
                   3: 'internal error',
                   4: 'internal error',
                   1001: 'wrong parameter type',
                   1002: 'too few parameters on stack for command',
                   1003: 'value ranges of the parameter exceeded',
                   1004: 'tried to step over axis range boundaries',
                   1008: 'too few parameters on stack for command',
                   1009: 'stack overflow',
                   1010: 'out of memory',
                   1015: 'parameter outside of axis range boundaries',
                   2000: 'unknown command'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rm = visa.ResourceManager()
        self._xy_controller = None
        self._zphi_controller = None

        self.axis_ranges = self._max_position_range.copy()
        self.velocity_ranges = self._max_velocity_range.copy()

        self.thread_lock = Mutex()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        @return: error code
        """
        # Open serial connections and configure termination characters
        self._xy_controller = self._rm.open_resource(resource_name=self._com_port_xy,
                                                     baud_rate=self._baud_rate_xy,
                                                     timeout=self._timeout_xy * 1000)
        self._xy_controller.read_termination = '\r\n'
        self._xy_controller.write_termination = ' '
        self._zphi_controller = self._rm.open_resource(resource_name=self._com_port_zphi,
                                                       baud_rate=self._baud_rate_zphi,
                                                       timeout=self._timeout_zphi * 1000)
        self._zphi_controller.read_termination = '\r\n'
        self._zphi_controller.write_termination = ' '

        # Set position unit to mm, velocity to mm/s and acceleration to mm/s^2
        for ax in range(3):
            self.write_xy('2 {0:d} setunit'.format(ax))
            self.write_zphi('2 {0:d} setunit'.format(ax))

        # Set ranges for position and velocity as specified in config
        self.set_position_limit({'x': self._x_position_range,
                                 'y': self._y_position_range,
                                 'z': self._z_position_range,
                                 'phi': self._phi_position_range})
        self.set_velocity_limit({'x': self._x_velocity_range,
                                 'y': self._y_velocity_range,
                                 'z': self._z_velocity_range,
                                 'phi': self._phi_velocity_range})

        # Set velocity if given in config
        vel_dict = dict()
        if self._x_velocity is not None:
            vel_dict['x'] = self._x_velocity
        if self._y_velocity is not None:
            vel_dict['y'] = self._y_velocity
        if self._z_velocity is not None:
            vel_dict['z'] = self._z_velocity
        if self._phi_velocity is not None:
            vel_dict['phi'] = self._phi_velocity
        if vel_dict:
            self.set_velocity(vel_dict)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        @return: error code
        """
        self._xy_controller.close()
        self._zphi_controller.close()
        return

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
        constraints = dict()
        constraints['x'] = {'unit': 'm',
                            'ramp': None,
                            'pos_min': self.axis_ranges['x'][0],
                            'pos_max': self.axis_ranges['x'][1],
                            'pos_step': 1e-7,
                            'vel_min': self._max_velocity_range['x'][0],
                            'vel_max': self._max_velocity_range['x'][1],
                            'vel_step': 1e-5,
                            'acc_min': None,
                            'acc_max': None,
                            'acc_step': None}
        constraints['y'] = {'unit': 'm',
                            'ramp': None,
                            'pos_min': self.axis_ranges['y'][0],
                            'pos_max': self.axis_ranges['y'][1],
                            'pos_step': 1e-7,
                            'vel_min': self._max_velocity_range['y'][0],
                            'vel_max': self._max_velocity_range['y'][1],
                            'vel_step': 1e-5,
                            'acc_min': None,
                            'acc_max': None,
                            'acc_step': None}
        constraints['z'] = {'unit': 'm',
                            'ramp': None,
                            'pos_min': self.axis_ranges['z'][0],
                            'pos_max': self.axis_ranges['z'][1],
                            'pos_step': 1e-7,
                            'vel_min': self._max_velocity_range['z'][0],
                            'vel_max': self._max_velocity_range['z'][1],
                            'vel_step': 1e-5,
                            'acc_min': None,
                            'acc_max': None,
                            'acc_step': None}
        constraints['phi'] = {'unit': '°',
                              'ramp': None,
                              'pos_min': self.axis_ranges['phi'][0],
                              'pos_max': self.axis_ranges['phi'][1],
                              'pos_step': 0.1,
                              'vel_min': self._max_velocity_range['phi'][0],
                              'vel_max': self._max_velocity_range['phi'][1],
                              'vel_step': 1,
                              'acc_min': None,
                              'acc_max': None,
                              'acc_step': None}
        return constraints

    def set_position_limit(self, axis_dict):
        """

        @param axis_dict:
        @return:
        """
        if not isinstance(axis_dict, dict):
            self.log.error('set_position_limit requires a dict as single parameter. '
                           'Keys are axes and items are range tuples.')
            return self.get_position_limit()
        if not set(axis_dict).issubset({'x', 'y', 'z', 'phi'}):
            self.log.error('Invalid axis encountered in axis_dict.')
            return self.get_position_limit()

        if 'x' in axis_dict or 'y' in axis_dict:
            if not ('x' in axis_dict and 'y' in axis_dict):
                curr_limits = self.get_position_limit(('x', 'y'))
            x_lim = axis_dict['x'] * 1000 if 'x' in axis_dict else curr_limits['x'] * 1000
            y_lim = axis_dict['y'] * 1000 if 'y' in axis_dict else curr_limits['y'] * 1000
            if x_lim is None:
                x_lim = self._max_position_range['x']
            if y_lim is None:
                y_lim = self._max_position_range['y']
            min_x = min(x_lim)
            max_x = max(x_lim)
            min_y = min(y_lim)
            max_y = max(y_lim)

            # Check if axis ranges lie within maximum allowed bounds
            if min_x < self._max_position_range['x'][0] or max_x > self._max_position_range['x'][1]:
                self.log.error('X axis position range outside of maximum allowed bounds.')
                return self.get_position_limit()
            if min_y < self._max_position_range['y'][0] or max_y > self._max_position_range['y'][1]:
                self.log.error('Y axis position range outside of maximum allowed bounds.')
                return self.get_position_limit()

            # Check if current axis position is within bounds
            curr_pos = self.get_pos(('x', 'y'))
            if not (min_x <= curr_pos['x'] <= max_x):
                self.log.error('Can not set limits {0} for axis "x". Current axis '
                               'position outside of limits.'.format(x_lim))
                return self.get_position_limit()
            if not (min_y <= curr_pos['y'] <= max_y):
                self.log.error('Can not set limits {0} for axis "y". Current axis '
                               'position outside of limits.'.format(y_lim))
                return self.get_position_limit()

            # Set limits
            self.write_xy(
                '{0} {1} -16383 {2} {3} 16383 setlimit'.format(min_x, min_y, max_x, max_y))

        if 'z' in axis_dict or 'phi' in axis_dict:
            if not ('z' in axis_dict and 'phi' in axis_dict):
                curr_limits = self.get_position_limit(('z', 'phi'))
            z_lim = axis_dict['z'] * 1000 if 'z' in axis_dict else curr_limits['z'] * 1000
            phi_lim = axis_dict['phi'] if 'phi' in axis_dict else curr_limits['phi']
            if z_lim is None:
                z_lim = self._max_position_range['z']
            if phi_lim is None:
                phi_lim = self._max_position_range['phi']
            min_z = min(z_lim)
            max_z = max(z_lim)
            min_phi = min(phi_lim)
            max_phi = max(phi_lim)

            # Check if axis ranges lie within maximum allowed bounds
            if min_z < self._max_position_range['z'][0] or max_z > self._max_position_range['z'][1]:
                self.log.error('Z axis position range outside of maximum allowed bounds.')
                return self.get_position_limit()
            if min_phi < self._max_position_range['phi'][0] or max_phi > self._max_position_range['phi'][1]:
                self.log.error('Phi axis position range outside of maximum allowed bounds.')
                return self.get_position_limit()

            # Check if current axis position is within bounds
            curr_pos = self.get_pos(('z', 'phi'))
            if not (min_z <= curr_pos['z'] <= max_z):
                self.log.error('Can not set limits {0} for axis "z". Current axis '
                               'position outside of limits.'.format(z_lim))
                return self.get_position_limit()
            if not (min_phi <= curr_pos['phi'] <= max_phi):
                self.log.error('Can not set limits {0} for axis "phi". Current axis '
                               'position outside of limits.'.format(phi_lim))
                return self.get_position_limit()

            # Set limits
            self.write_zphi(
                '{0} {1} -16383 {2} {3} 16383 setlimit'.format(min_z, min_phi, max_z, max_phi))
        self._report_errors()
        return self.get_position_limit()

    def get_position_limit(self, axis=None):
        """

        @param axis:
        @return:
        """
        if axis is None:
            axis = ('x', 'y', 'z', 'phi')
        elif isinstance(axis, str):
            axis = [axis]

        return_dict = dict()
        if 'x' in axis or 'y' in axis:
            range_str_tuple = self.query_xy('getlimit', 3)
            if 'x' in axis:
                min_pos, max_pos = (float(s) / 1000 for s in range_str_tuple[0].split())
                min_abs, max_abs = self._max_position_range['x']
                return_dict['x'] = (max(min_pos, min_abs), min(max_pos, max_abs))
            if 'y' in axis:
                min_pos, max_pos = (float(s) / 1000 for s in range_str_tuple[1].split())
                min_abs, max_abs = self._max_position_range['y']
                return_dict['y'] = (max(min_pos, min_abs), min(max_pos, max_abs))
        if 'z' in axis or 'phi' in axis:
            range_str_tuple = self.query_zphi('getlimit', 3)
            if 'z' in axis:
                min_pos, max_pos = (float(s) / 1000 for s in range_str_tuple[0].split())
                min_abs, max_abs = self._max_position_range['z']
                return_dict['z'] = (max(min_pos, min_abs), min(max_pos, max_abs))
            if 'phi' in axis:
                min_pos, max_pos = (float(s) for s in range_str_tuple[1].split())
                min_abs, max_abs = self._max_position_range['phi']
                return_dict['phi'] = (max(min_pos, min_abs), min(max_pos, max_abs))
        self.axis_ranges.update(return_dict)
        self._report_errors()
        return return_dict

    def set_velocity_limit(self, axis_dict):
        """

        @param dict axis_dict:
        @return dict:
        """
        if not isinstance(axis_dict, dict):
            self.log.error('set_velocity_limit requires a dict as single parameter. '
                           'Keys are axes and items are range tuples.')
            return self.get_velocity_limit()
        if not set(axis_dict).issubset({'x', 'y', 'z', 'phi'}):
            self.log.error('Invalid axis encountered in axis_dict.')
            return self.get_velocity_limit()

        for axis, limits in axis_dict.items():
            max_limit = self._max_velocity_range[axis]
            if limits is None:
                min_val = max_limit[0]
                max_val = max_limit[1]
            else:
                min_val = min(limits)
                max_val = max(limits)
            if min_val < max_limit[0] or max_val > max_limit[1]:
                self.log.error('Velocity limits ({0}, {1}) to set for axis "{2}" outside of '
                               'absolute maximum range {3}'
                               ''.format(min_val, max_val, axis, max_limit))
                return self.get_velocity_limit()
            self.velocity_ranges[axis] = (min_val, max_val)
        return self.get_velocity_limit()

    def get_velocity_limit(self, axis=None):
        """

        @param str|iterable axis:
        @return:
        """
        if axis is None:
            axis = ('x', 'y', 'z', 'phi')
        elif isinstance(axis, str):
            axis = [axis]

        return_dict = self.velocity_ranges.copy()
        for ax in ('x', 'y', 'z', 'phi'):
            if ax not in axis:
                del return_dict[ax]
        return return_dict

    def get_pos(self, param_list=None):
        """
        Gets current position of the axes.

        @param list param_list: optional, if the position of a specific axis is desired, then the
                                labels of the desired axes should be passed in the param_list.
                                If nothing is passed, all positions are returned.

        @return dict: Keys is axis label and item the corresponding position.
        """
        if param_list is None:
            param_list = ('x', 'y', 'z', 'phi')

        param_dict = dict()
        if 'x' in param_list or 'y' in param_list:
            pos_str_tuple = self.query_xy('pos').split()
            if 'x' in param_list:
                param_dict['x'] = float(pos_str_tuple[0]) / 1000
            if 'y' in param_list:
                param_dict['y'] = float(pos_str_tuple[1]) / 1000
        if 'z' in param_list or 'phi' in param_list:
            pos_str_tuple = self.query_zphi('pos').split()
            if 'z' in param_list:
                param_dict['z'] = float(pos_str_tuple[0]) / 1000
            if 'phi' in param_list:
                param_dict['phi'] = float(pos_str_tuple[1])
        self._report_errors()
        return param_dict

    def get_error(self, axis):
        """
        Get all error messages from the error pipe of the controller and return them in a list.
        Empty list returned if no error occurred.

        @param str axis: The axis to read the error messages from. If None return all errors.
        @return list: List of error messages.
        """
        axis = axis.lower()
        if axis in 'xy':
            query = self.query_xy
            write = self.write_xy
        elif axis in 'zphi':
            query = self.query_zphi
            write = self.write_zphi
        else:
            self.log.error('Specified axis "{0}" not supported.'.format(axis))
            return list()

        err_list = list()
        while True:
            err_code = int(query('geterror'))
            if err_code == 0:
                break
            err_list.append(self.error_codes.get(err_code, 'unknown error'))

        # Check for unhandled parameters on stack and clear stack if needed
        stack_size = int(query('gsp'))
        if stack_size > 0:
            err_list.append('Unhandled parameters on stack: {0:d}. This can be caused by faulty '
                            'command syntax.'.format(stack_size))
            write('clear')
        return err_list

    def move_rel(self, param_dict):
        """
        Moves stage in given direction (relative movement)

        @param dict param_dict: Usage: {'axis_label': <the-rel-pos-value>}.

        @return dict: dictionary with the current magnet position
        """
        curr_pos = self.get_pos()
        for axis, value in param_dict.items():
            if not self._pos_in_range(axis=axis, pos=curr_pos[axis] + value):
                self.log.error('Resulting position {0:.6e} outside of allowed range for axis "{1}".'
                               ''.format(curr_pos[axis] + value, axis))
                return self.get_pos()

        if 'x' in param_dict or 'y' in param_dict:
            x_move = param_dict['x'] * 1000 if 'x' in param_dict else 0
            y_move = param_dict['y'] * 1000 if 'y' in param_dict else 0
            self.write_xy('{0.6f} {1.6f} 0 r'.format(x_move, y_move))
            self.write_xy('0 0 0 r')
            if self._report_errors('x'):
                return self.get_pos()
        if 'z' in param_dict or 'phi' in param_dict:
            z_move = param_dict['z'] * 1000 if 'z' in param_dict else 0
            phi_move = param_dict['phi'] if 'phi' in param_dict else 0
            self.write_zphi('{0.6f} {1.6f} 0 r'.format(z_move, phi_move))
            self.write_zphi('0 0 0 r')
            if self._report_errors('z'):
                return self.get_pos()
        return self.get_pos()

    def move_abs(self, param_dict):
        """
        Moves stage to absolute position

        @param dict param_dict: Usage: {'axis_label': <the-abs-pos-value>}.

        @return dict pos: dictionary with the current axis position
        """
        for axis, value in param_dict.items():
            if not self._pos_in_range(axis=axis, pos=value):
                self.log.error('Resulting position {0:.6e} outside of allowed range for axis "{1}".'
                               ''.format(value, axis))
                return self.get_pos()

        curr_pos = self.get_pos()
        if 'x' in param_dict or 'y' in param_dict:
            x_move = param_dict['x'] * 1000 if 'x' in param_dict else curr_pos['x']
            y_move = param_dict['y'] * 1000 if 'y' in param_dict else curr_pos['y']
            self.write_xy('{0.6f} {1.6f} 0 m'.format(x_move, y_move))
            self.write_xy('0 0 0 r')
            if self._report_errors('x'):
                return self.get_pos()
        if 'z' in param_dict or 'phi' in param_dict:
            z_move = param_dict['z'] * 1000 if 'z' in param_dict else curr_pos['z']
            phi_move = param_dict['phi'] if 'phi' in param_dict else curr_pos['phi']
            self.write_zphi('{0.6f} {1.6f} 0 m'.format(z_move, phi_move))
            self.write_zphi('0 0 0 r')
            if self._report_errors('z'):
                return self.get_pos()
        return self.get_pos()

    def abort(self):
        """
        Stops current command execution of all axes immediately
        """
        self.write_xy('\x03')
        self.write_zphi('\x03')
        return self.get_status()

    def reset(self):
        self.write_xy('reset')
        self.write_zphi('reset')
        return

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
        if param_list is None:
            param_list = ('x', 'y', 'z', 'phi')
        param_dict = dict()
        if 'x' in param_list:
            param_dict['x'] = int(self.query_xy('st'))
        if 'y' in param_list:
            param_dict['y'] = param_dict['x'] if 'x' in param_dict else int(self.query_xy('st'))
        if 'z' in param_list:
            param_dict['z'] = int(self.query_zphi('st'))
        if 'phi' in param_list:
            param_dict['phi'] = param_dict['z'] if 'z' in param_dict else int(self.query_zphi('st'))
        self._report_errors()
        return param_dict

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
        if param_list is None:
            param_list = ('x', 'z')

        if 'x' in param_list or 'y' in param_list:
            self.write_xy('cal')
            if self._report_errors():
                self.error('Calibration of xy axis controller failed.')
                return self.get_status()
        if 'z' in param_list or 'phi' in param_list:
            self.write_zphi('cal')
            if self._report_errors():
                self.error('Calibration of xy axis controller failed.')
                return self.get_status()
        return self.get_status()

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        if param_list is None:
            param_list = ('x', 'y', 'z', 'phi')

        # TODO: Get velocity for each axis separately
        param_dict = dict()
        if 'x' in param_list:
            param_dict['x'] = float(self.query_xy('gv').split()[0]) / 1000
        if 'y' in param_list:
            if 'x' not in param_dict:
                param_dict['y'] = float(self.query_xy('gv').split()[0]) / 1000
            else:
                param_dict['y'] = param_dict['x']
        if 'z' in param_list:
            param_dict['z'] = float(self.query_zphi('gv').split()[0]) / 1000
        if 'phi' in param_list:
            if 'z' not in param_dict:
                param_dict['phi'] = float(self.query_zphi('gv').split()[0])
            else:
                param_dict['phi'] = param_dict['z']
        self._report_errors()
        return param_dict

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        for axis, vel in param_dict.items():
            if not self._vel_in_range(axis=axis, vel=vel):
                self.log.error('Velocity to set {0:.6e} outside of allowed range for axis "{1}".'
                               ''.format(vel, axis))
                return self.get_velocity()

        if 'x' in param_dict or 'y' in param_dict:
            vel = param_dict['x'] * 1000 if 'x' in param_dict else param_dict['y'] * 1000
            self.write_xy('{0:.6f} sv'.format(vel))
            if self._report_errors('x'):
                return self.get_velocity()
        if 'z' in param_dict or 'phi' in param_dict:
            vel = param_dict['z'] * 1000 if 'z' in param_dict else param_dict['phi'] * 1000
            self.write_zphi('{0:.6f} sv'.format(vel))
            if self._report_errors('z'):
                return self.get_velocity()
        self._report_errors()
        return self.get_velocity()

    def write_xy(self, command):
        """
        This method sends a command to the xy motor controller. No return value.

        @param str command: command string to send
        """
        return self.__write(controller=self._xy_controller, command=command)

    def write_zphi(self, command):
        """
        This method sends a command to the zphi motor controller. No return value.

        @param str command: command string to send
        """
        return self.__write(controller=self._zphi_controller, command=command)

    def query_xy(self, command, answer_lines=1):
        """
        This method sends a command to the xy motor controller. No return value.

        @param str command: command string to send
        @param int answer_lines: Number of lines to read for this answer
        """
        return self.__query(self._xy_controller, command=command, answer_lines=answer_lines)

    def query_zphi(self, command, answer_lines=1):
        """
        This method sends a command to the xy motor controller. No return value.

        @param str command: command string to send
        @param int answer_lines: Number of lines to read for this answer
        """
        return self.__query(self._zphi_controller, command=command, answer_lines=answer_lines)

    def __write(self, controller, command):
        if not isinstance(command, str):
            self.log.error('Command to send must be of type str.')
            return
        with self.thread_lock:
            result = controller.write(command)
        return result

    def __query(self, controller, command, answer_lines=1):
        if not isinstance(command, str):
            self.log.error('Command for query must be of type str.')
            return
        with self.thread_lock:
            answer = controller.query(command)
            if answer_lines > 1:
                answer = [answer]
                for i in range(answer_lines - 1):
                    try:
                        answer.append(controller.read())
                    except visa.VisaIOError:
                        self.log.warning('Number of lines ({0:d}) to read for query command "{1}" '
                                         'probably too many. Visa timeout occurred.'
                                         ''.format(answer_lines, command))
                        break
        return answer

    def _pos_in_range(self, axis, pos):
        """

        @param str axis:
        @param float pos:
        @return bool:
        """
        if axis not in self.axis_ranges:
            self.log.error('Unknown axis: "{0}"'.format(axis))
            return False
        if self.axis_ranges[axis][0] <= pos <= self.axis_ranges[axis][1]:
            return True
        return False

    def _vel_in_range(self, axis, vel):
        """

        @param str axis:
        @param float vel:
        @return bool:
        """
        if axis not in self.velocity_ranges:
            self.log.error('Unknown axis: "{0}"'.format(axis))
            return False
        if self.velocity_ranges[axis][0] <= vel <= self.velocity_ranges[axis][1]:
            return True
        return False

    def _report_errors(self, axis=None):
        err_found = False

        if isinstance(axis, str):
            err = self.get_error(axis)
            if err:
                self.log.error('Error(s) in {0} controller:\n\t{1}'
                               ''.format('xy' if axis in 'xy' else 'zphi', '\n\t'.join(err)))
                err_found = True
        else:
            for axis in ('xy', 'zphi'):
                err = self.get_error(axis)
                if err:
                    self.log.error('Error(s) in {0} controller:\n\t{1}'
                                   ''.format(axis, '\n\t'.join(err)))
                    err_found = True
        return err_found
