import math
import numpy as np
from datetime import datetime as dt
from time import time, sleep
from random import random
from scipy.optimize import minimize

from collections import OrderedDict
import serial

from numpy import arange

import re

import visa
import signal

from core.module import Base, ConfigOption
from interface.motor_interface import MotorInterface


class NanomaxStage(Base, MotorInterface):
    """unstable: Christoph Müller, Simon Schmitt
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    # _modclass = 'MotorStageNanomax'
    # _modtype = 'hardware'

    _com_port_nano_xyz = ConfigOption('com_port_nano_xyz', 'COM10')
    _nano_xyz_baud_rate = ConfigOption('nano_xyz_baud_rate', 115200)
    #_nano_xyz_timeout = ConfigOption('nano_xyz_timeout', 1000)
    _nano_xyz_term_char = ConfigOption('nano_xyz_term_char', '\n')
    _first_axis_label = ConfigOption('nano_first_axis_label', 'x-axis')
    _second_axis_label = ConfigOption('nano_second_axis_label', 'y-axis')
    _third_axis_label = ConfigOption('nano_third_axis_label', 'z-axis')
    _first_axis_ID = ConfigOption('nano_first_axis_ID', 'x')
    _second_axis_ID = ConfigOption('nano_second_axis_ID', 'y')
    _third_axis_ID = ConfigOption('nano_third_axis_ID', 'z')

    constraints = {}
    axis0 = {}
    axis1 = {}
    axis2 = {}

    _min_first = ConfigOption('nano_first_min', -10e-6)  # Values in m
    _max_first = ConfigOption('nano_first_max', 10e-6)
    _min_second = ConfigOption('nano_second_min', -10e-6)
    _max_second = ConfigOption('nano_second_max', 10e-6)
    _min_third = ConfigOption('nano_third_min', -10e-6)
    _max_third = ConfigOption('nano_third_max', 10e-6)

    step_first_axis = ConfigOption('nano_first_axis_step', 1e-7)
    step_second_axis = ConfigOption('nano_second_axis_step', 1e-7)
    step_third_axis = ConfigOption('nano_third_axis_step', 1e-7)

    _vel_min_first = ConfigOption('vel_first_min', 1e-5)
    _vel_max_first = ConfigOption('vel_first_max', 5e-2)
    _vel_min_second = ConfigOption('vel_second_min', 1e-5)
    _vel_max_second = ConfigOption('vel_second_max', 5e-2)
    _vel_min_third = ConfigOption('vel_third_min', 1e-5)
    _vel_max_third = ConfigOption('vel_third_max', 5e-2)

    _vel_step_first = ConfigOption('vel_first_axis_step', 1e-5)
    _vel_step_second = ConfigOption('vel_second_axis_step', 1e-5)
    _vel_step_third = ConfigOption('vel_third_axis_step', 1e-5)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        @return: error code
        """

        self.piezo = SRSController(port = self._com_port_nano_xyz)

        self.vel = {}
        self.vel['x-axis'] = 1e-5
        self.vel['y-axis'] = 1e-5
        self.vel['z-axis'] = 1e-5
        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        @return: error code
        """

        self.piezo.close_connection()

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
        axis0['unit'] = 'm'  # the SI units
        # axis0['ramp'] = None # a possible list of ramps
        axis0['pos_min'] = self._min_first
        axis0['pos_max'] = self._max_first
        axis0['scan_min'] = -10e-6
        axis0['scan_max'] = 10e-6
        # axis0['pos_step'] = self.step_first_axis
        # axis0['vel_min'] = self._vel_min_first
        # axis0['vel_max'] = self._vel_max_first
        # axis0['vel_step'] = self._vel_step_first
        # axis0['acc_min'] = None
        # axis0['acc_max'] = None
        # axis0['acc_step'] = None
        #
        axis1 = {}
        axis1['label'] = self._second_axis_label
        axis1['ID'] = self._second_axis_ID
        # axis1['unit'] = 'm'        # the SI units
        # axis1['ramp'] = None # a possible list of ramps
        axis1['pos_min'] = self._min_second
        axis1['pos_max'] = self._max_second
        axis1['scan_min'] = -10e-6
        axis1['scan_max'] = 10e-6
        # axis1['pos_step'] = self.step_second_axis
        # axis1['vel_min'] = self._vel_min_second
        # axis1['vel_max'] = self._vel_max_second
        # axis1['vel_step'] = self._vel_step_second
        # axis1['acc_min'] = None
        # axis1['acc_max'] = None
        # axis1['acc_step'] = None
        #
        axis2 = {}
        axis2['label'] = self._third_axis_label
        axis2['ID'] = self._third_axis_ID
        # axis2['unit'] = 'm'        # the SI units
        # axis2['ramp'] = None # a possible list of ramps
        axis2['pos_min'] = self._min_third
        axis2['pos_max'] = self._max_third
        axis2['scan_min'] = -10e-6
        axis2['scan_max'] = 10e-6
        # axis2['pos_step'] = self.step_third_axis
        # axis2['vel_min'] = self._vel_min_third
        # axis2['vel_max'] = self._vel_max_third
        # axis2['vel_step'] = self._vel_step_third
        # axis2['acc_min'] = None
        # axis2['acc_max'] = None
        # axis2['acc_step'] = None
        #
        #
        # # assign the parameter container for x to a name which will identify it
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

        for axis_label in param_dict:
            # self.log.info(axis_label)
            step = param_dict[axis_label]
            self._do_move_rel(axis_label, step)

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
        for axis_label in param_dict:
            move = param_dict[axis_label]
            self._do_move_abs(axis_label, move)

        return param_dict

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self.piezo.close_connection()
        return 0

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
            if param_list is not None:
                for axis_label in param_list:
                    for attempt in range(25):
                        # self.log.debug(attempt)
                        try:
                            # self.log.info('here')
                            pos = self._do_get_pos(axis_label)
                            param_dict[axis_label] = pos  # * 1e-7
                            # self.log.info('Position is {}'.format(pos))
                            #print('param passed')
                            #print(axis_label)
                            #print(pos)
                        except:
                            param_dict[axis_label] = 0
                        else:
                            break
            else:
                for axis_label in constraints:
                    for attempt in range(25):
                        # self.log.debug(attempt)
                        try:
                            # self.log.info('now here')
                            #print('from constraints')
                            pos = self._do_get_pos(axis_label)
                            param_dict[axis_label] = pos  # * 1e-7
                            #print(axis_label)
                            #print(pos)
                            # self.log.info('Position is {}'.format(pos))
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
         """
        constraints = self.get_constraints()
        return 0

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

        return 0

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
                    param_dict[axis_label] = self.vel[axis_label]
            else:
                for axis_label in constraints:
                    param_dict[axis_label] = self.vel[axis_label]
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
        # constraints = self.get_constraints()
        try:
            for axis_label in param_dict:
                self.vel[axis_label] = int(param_dict[axis_label])

            return param_dict

        except:
            self.log.error('Could not set axis velocity')
            return -1



            ########################## internal methods ##################################


    def _do_get_pos(self, axis):
        constraints = self.get_constraints()
        voltage = self.piezo.get_voltage(axis)
        #print('voltage ')
        #print(voltage)
        # self.log.info('Voltage is {} V'.format(voltage))
        pos = self._vol2dist(voltage)
        #print(pos)
        return pos

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
            current_pos = self.get_pos(axis)[axis]
            move = current_pos + step
            # self.log.info('Move is {0} '.format(move))
            self._do_move_abs(axis, move)
        return axis, move



    def _dist2volt(self, value):

        """
        Converts the range of the piezo (20 microns ) to voltage (max 10)
        :param value:
        :return:
        """

        volt = (value + 1e-5) / ((20 / 10) * 1e-6)

        return volt

    def _volt2dist(self, value):
        """
        does the opposite
        :param value:
        :return:
        """
        unit = (20 / 10) * 1e-6 * value - 1e-5

        return unit

    def _do_move_abs(self, axis, move):
        """internal method for the absolute move in meter

        @param axis string: name of the axis that should be moved

        @param float move: desired position in millimeter

        @return str axis: axis which is moved
                move float: absolute position to move to
        """

        # get voltage from position in SI units
        move_volt = self._dist2volt(move)
        # move to voltage

        # self.log.info('Move volt is {0}'.format(move_volt))
        constraints = self.get_constraints()
        if not (constraints[axis]['pos_min'] <= move <= constraints[axis]['pos_max']):
            self.log.warning('Cannot make the movement of the axis "{0}" to {1}'
                             'since the border [{2},{3}] would be crossed! Ignore command!'
                             ''.format(axis, move, constraints[axis]['pos_min'], constraints[axis]['pos_max']))
        else:

            self.piezo.set_voltage(axis, move_volt)  # 1e7 to convert meter to SI units
        return axis, move

    def _in_movement_xyz(self):
        '''this method checks if the magnet is still moving and returns
        a dictionary which of the axis are moving.

        @return: dict param_dict: Dictionary displaying if axis are moving:
        0 for immobile and 1 for moving
        '''
        constraints = self.get_constraints()
        param_dict = {}
        for axis_label in constraints:
            tmp0 = 0  # dunno if moving
            param_dict[axis_label] = tmp0 % 2

        return param_dict

    def _motor_stopped(self):
        '''this method checks if the magnet is still moving and returns
            False if it is moving and True of it is immobile

            @return: bool stopped: False for immobile and True for moving
                '''
        param_dict = self._in_movement_xyz()
        stopped = True
        for axis_label in param_dict:
            if param_dict[axis_label] != 0:
                self.log.info('Dunno if the stage is stopped')
                stopped = False
        return stopped








class SRSController(serial.Serial):
    '''
    Python class for controlling voltages to 3-axis ThorLabs MDT693A
    '''

    # Note 75V is the maximum voltage the Nanomax can handle!
    def __init__(self, MAX_VOLTAGE=75.0, port='COM10', baudrate=115200):

        self.MAX_VOLTAGE = MAX_VOLTAGE

        # Initialise the class using super class of (py)serial
        serial.Serial.__init__(self, port, baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE, timeout=0.3)

            # Close any open connections and open a serial connection
            # self.close()
            # self.open()

    def cmd(self, command, verbose=False):
        '''
        Send a command to the MDT693A
        '''
        # logging.info(str(command))
        #tick = time.perf_counter()
        try:
            self.write((bytes(command + '\n', 'utf8')))
        except  serial.serialutil.SerialTimeoutException:
            logging.error('Serial timeout exception when writing')

        # Have a timeout so that writing successive strings does not interrupt
        # the last command
        #logging.info(command)
        num = 1
        while (num < 1):
            num = self.out_waiting()
        #tock = time.perf_counter() - tick
        #logging.info(tock)

    def response(self):
        '''
        Get response and convert to a float if there's a match
        '''

        # resp = self.read()
        # # logging.info(resp)
        # if resp is b'':
        #     return
        #
        # # Loop until we hit the end line character
        # while resp[-1] is not '\r':
        #     r = self.read()
        #     # logging.info(r)
        #     resp.append(r)
        #     if r == b'':
        #         break

        resp = []
        bytesToRead = 1
        while (bytesToRead > 0) :
            bytesToRead = self.inWaiting()
            resp.append( self.read(bytesToRead))

        print(resp)
        # Search the response to extract the number
        regex = r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?'

        found = re.findall(regex, str(resp))
        # print found
        if len(found) > 0:
            result = float(found[0][0])
            return result
        else:
            return 0


    def get_voltage(self, axis):
        '''
        get the voltage for the x,y,z axes
        --------
        axis - (str) x y or z axis to set the voltage
        '''

        lut = ["x-axis", "y-axis", "z-axis"]

        if axis not in lut:
            self.log.error("%s is not in (X,Y,Z)" % axis)
            return

        else:
            index = int(lut.index(axis))
            self.cmd('AUXV? {0}'.format(index))
            time.sleep(0.2)
            voltage = self.response()
            #print('get {0} {1}'.format(axis, voltage))
            return voltage

    def set_voltage(self, axis, voltage, step=2.5):

        lut = ["x-axis", "y-axis", "z-axis"]

        if axis not in lut:
            self.log.error("%s axis is not in (X,Y,Z)" % axis)
        if not 0.0 <= voltage <= 10.1:
            self.log.error("The current voltage (%s V) must be between 0V and 10 V" % voltage)

        else:
            index = lut.index(axis)
            value = round(voltage, 5)
            # sleep(0.01)
            # print("AUXV {0}, {1}".format(index, value))
            self.cmd("AUXV {0}, {1}".format(index, value))

    def jog(self, axis, voltage_increment):
        '''
        Increment/decrement the voltages on a given axis by a voltage
        --------
        axis - (str) x y or z axis to set the voltage
        voltage - (float) voltage to set on the piezo controller
        '''
        if axis not in ["x", "y", "z"]:
            self.close_connection()
            raise RuntimeError("%s axis is not in (x,y,z)" % axis)

        v = self.get_voltage(axis)
        new_voltage = v + voltage_increment

        if not 0.0 <= new_voltage <= self.MAX_VOLTAGE:
            self.close_connection()
            raise RuntimeError(
                "The current voltage (%s V) must be between 0V and %s V" % (new_voltage, self.MAX_VOLTAGE))

        self.set_voltage(axis, new_voltage)

    def set_voltage_rel(self, axis, r):
        '''
        set relative voltage on the piezo controller (i.e. between 0 and
        MAX_VOLTAGE.
        #=======================================================================
        # PLEASE USE Z-AXIS WITH CAUTION WHEN THE VGA IS NEAR THE SURFACE OF THE
        # CHIP
        #=======================================================================
        -------
        axis - (str) x y or z axis to set the voltage
        voltage - (float) number between 0 and 1 for piezo controller where
                0 is zero voltage and 1 is MAX_VOLTAGE
        '''

        if not 0.0 <= r <= 1.0:
            self.close_connection()
            logging.error("The relative voltage must be between 0 and 1")
        self.set_voltage(axis, r * self.MAX_VOLTAGE)

    def half_xy_axes(self):
        '''
        set the voltages on the x, y piezos to half of the max voltage
        '''
        self.set_voltage_rel('x', 0.5)
        self.set_voltage_rel('y', 0.5)

    def zero_all_axes(self):
        '''
        Set all the axis to zero
        #############################################################
        WARNING DO NOT EXECUTE THIS COMMAND WHEN VGA IS NEAR THE CHIP
        #############################################################
        '''
        self.set_voltage("x", 0.0)
        self.set_voltage("y", 0.0)
        self.set_voltage("z", 0.0)

    def close_connection(self):
        self.close()
        #time.sleep(0.2)

    def vol2dist(self, voltage):

        self.dist = (20 / 75) * 1e-6 * voltage - 10e-6

        return self.dist

    def dist2volt(self, dist):

        self.volt = float((dist + 10e-6) / ((20 / 75) * 1e-6))

        # resolution is 3 mV
        #self.volt = round(self.volt, 5)

        return self.volt

    def __del__(self):
        self.close()



