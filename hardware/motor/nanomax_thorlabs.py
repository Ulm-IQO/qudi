# import math
# import numpy as np
# from datetime import datetime as dt
from time import time, sleep
import re
# from random import random
# from scipy.optimize import minimize

from collections import OrderedDict
import serial

from core.module import Base, ConfigOption
from interface.motor_interface import MotorInterface


class NanomaxStage(Base, MotorInterface):
    """unstable: Christoph Müller, Simon Schmitt
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MotorStageNanomax'
    _modtype = 'hardware'

    _com_port_nano_xyz = ConfigOption('com_port_nano_xyz', 'COM4', missing='warn')
    _nano_xyz_baud_rate = ConfigOption('nano_xyz_baud_rate', 115200, missing='warn')
    _nano_xyz_timeout = ConfigOption('nano_xyz_timeout', 0.1, missing='warn')
    _nano_xyz_term_char = ConfigOption('nano_xyz_term_char', '\n', missing='warn')
    _first_axis_label = ConfigOption('nano_first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('nano_second_axis_label', 'y', missing='warn')
    _third_axis_label = ConfigOption('nano_third_axis_label', 'z', missing='warn')
    _first_axis_ID = ConfigOption('nano_first_axis_ID', '1', missing='warn')
    _second_axis_ID = ConfigOption('nano_second_axis_ID', '2', missing='warn')
    _third_axis_ID = ConfigOption('nano_third_axis_ID', '3', missing='warn')


    _min_first = ConfigOption('nano_first_min', -10, missing='warn') #Values in microns
    _max_first = ConfigOption('nano_first_max', 10, missing='warn')
    _min_second = ConfigOption('nano_second_min', -10, missing='warn')
    _max_second = ConfigOption('nano_second_max', 10, missing='warn')
    _min_third = ConfigOption('nano_third_min', -10, missing='warn')
    _max_third = ConfigOption('nano_third_max', 10, missing='warn')

    step_first_axis = ConfigOption('nano_first_axis_step', 0.02, missing='warn') #Values in microns
    step_second_axis = ConfigOption('nano_second_axis_step', 0.02, missing='warn')
    step_third_axis = ConfigOption('nano_third_axis_step', 0.02, missing='warn')

    # _vel_min_first = ConfigOption('vel_first_min', 1e-5, missing='warn')
    # _vel_max_first = ConfigOption('vel_first_max', 5e-2, missing='warn')
    # _vel_min_second = ConfigOption('vel_second_min', 1e-5, missing='warn')
    # _vel_max_second = ConfigOption('vel_second_max', 5e-2, missing='warn')
    # _vel_min_third = ConfigOption('vel_third_min', 1e-5, missing='warn')
    # _vel_max_third = ConfigOption('vel_third_max', 5e-2, missing='warn')

    # _vel_step_first = ConfigOption('vel_first_axis_step', 1e-5, missing='warn')
    # _vel_step_second = ConfigOption('vel_second_axis_step', 1e-5, missing='warn')
    # _vel_step_third = ConfigOption('vel_third_axis_step', 1e-5, missing='warn')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        @return: error code
        """
        # self.log.info(self._com_port_nano_xyz)
        # print('will_test')
        self._serial_connection_xyz = serial.Serial(self._com_port_nano_xyz, self._nano_xyz_baud_rate, timeout=self._nano_xyz_timeout)
        # Close any open connections and open a serial connection
        self._serial_connection_xyz.close()
        self._serial_connection_xyz.open()

        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        @return: error code
        """
        self._serial_connection_xyz.close()
        # self.rm.close()
        return 0


    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = {}
        # constraints = OrderedDict()

        axis0 = {}
        axis0['label'] = self._first_axis_label
        axis0['ID'] = self._first_axis_ID
        axis0['unit'] = 'um'                 # the SI units
        axis0['ramp'] = None # a possible list of ramps
        axis0['pos_min'] = self._min_first
        axis0['pos_max'] = self._max_first
        axis0['pos_step'] = self.step_first_axis
        axis0['vel_min'] = None
        axis0['vel_max'] = None
        axis0['vel_step'] = None
        axis0['acc_min'] = None
        axis0['acc_max'] = None
        axis0['acc_step'] = None
        #
        axis1 = {}
        axis1['label'] = self._second_axis_label
        axis1['ID'] = self._second_axis_ID
        axis1['unit'] = 'um'        # the SI units
        axis1['ramp'] = None # a possible list of ramps
        axis1['pos_min'] = self._min_second
        axis1['pos_max'] = self._max_second
        axis1['pos_step'] = self.step_second_axis
        axis1['vel_min'] = None
        axis1['vel_max'] = None
        axis1['vel_step'] = None
        axis1['acc_min'] = None
        axis1['acc_max'] = None
        axis1['acc_step'] = None
        #
        axis2 = {}
        axis2['label'] = self._third_axis_label
        axis2['ID'] = self._third_axis_ID
        axis2['unit'] = 'um'        # the SI units
        axis2['ramp'] = None # a possible list of ramps
        axis2['pos_min'] = self._min_third
        axis2['pos_max'] = self._max_third
        axis2['pos_step'] = self.step_third_axis
        axis2['vel_min'] = None
        axis2['vel_max'] = None
        axis2['vel_step'] = None
        axis2['acc_min'] = None
        axis2['acc_max'] = None
        axis2['acc_step'] = None
        #
        #
        # # assign the parameter container for x, y, and z to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2

        return constraints

    def move_rel(self, param_dict):


        return param_dict

    def move_abs(self, param_dict):
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

    # def get_pos(self, param_list=None):
    def get_pos(self, axis):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """

        pos = self._get_voltage(axis)
        # pos = self._do_convert_SI(voltvar)

        # pos = {}
        # try:
        #     pos_str = self._micos.query('pos')
        #     self.pos = float(pos_str) / 1000 - 24e-3
        #
        # except visa.VisaIOError:
        #     self.log.error(visa.VisaIOError)
        #
        # pos[self._micos.label] = self.pos

        return pos

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

            # constraints = self.get_constraints()

    def get_velocity(self, param_list=None):
            """ Gets the current velocity for all connected axes in m/s.

            @param list param_list: optional, if a specific velocity of an axis
                                        is desired, then the labels of the needed
                                        axis should be passed as the param_list.
                                        If nothing is passed, then from each axis the
                                        velocity is asked.

            @return dict : with the axis label as key and the velocity as item.
                """

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

########################## internal methods ##################################


    def _cmd(self, command):
        '''
        Send a command to the MDT693A
        '''
        self._serial_connection_xyz.write((str(command)+'\n').encode('utf-8'))
        # Have a timeout so that writing successive strings does not interrupt
        # the last command
        sleep(0.03)
    def _response(self):
        '''
        Get response and convert to a float if there's a match
        '''
        resp = self._serial_connection_xyz.read()
        if resp == b'':
            return

        # # Loop until we hit the end line character
        # while resp[-1] != '\r':
        #     r = self._serial_connection_xyz.read()
        #     resp = resp + r
        #     if r == b'':
        #         break

        # Search the response to extract the number
        match = re.search('\[(.*)\]', str(resp))
        if match:
            # If the match has square brackets then we convert this to a float
            result = float(match.group(1))
            return result
        else:
            return

    def _get_voltage(self, axis):
        '''
        get the voltage for the x,y,z axes
        --------
        axis - (str) x y or z axis to set the voltage
        '''
        if axis not in ["x", "y", "z"]:
            # self.close_connection()
            raise RuntimeError("%s axis is not in (x,y,z)" % axis)

        self._cmd((str(axis)+'voltage?'))
        voltage = self._response()
        return voltage
    def _do_convert_SI(self, value):
        """
        Converts from voltage to position in microns
        :param value: Voltage in the piezo driver

        """
        unit = (value * (20/75))-10

        return unit