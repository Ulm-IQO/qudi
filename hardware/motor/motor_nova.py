# -*- coding: utf-8 -*-
"""
NOVA Motor Controller for NDMS1.

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

"""
This module was developed from PyAPT, written originally by Michael Leung
(mcleung@stanford.edu). Have a look in:
    https://github.com/HaeffnerLab/Haeffner-Lab-LabRAD-Tools/blob/master/cdllservers/APTMotor/APTMotorServer.py
APT.dll and APT.lib were provided to PyAPT thanks to SeanTanner@ThorLabs .
All the specific error and status code are taken from:
    https://github.com/UniNE-CHYN/thorpy
The rest of the documentation is based on the Thorlabs APT Server documentation
which can be obtained directly from
    https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=APT
"""

from collections import OrderedDict
from core.base import Base
from ctypes import *
from interface.motor_interface import MotorInterface
import os
import platform
import logging

class NOVAMotor:
    """ Class to read/write to the NOVA controller. This class wraps the low level
        commands from a dll library in python methods.
    """

    # all the possible hardware types that are available to be controlled by
    # the dll
    hwtype_dict = {}
    hwtype_dict['HWTYPE_NDMS1'] = 1016  # 1 Ch motor driver
    hwtype_dict['HWTYPE NDS40'] = 1011  # 1 Ch stepper driver

    # the error code is also comparable to the NOVA server documentation.
    error_code = {}
    error_code[0] = 'IPC valid'
    error_code[1] = 'IPC error - is there another connection still running?'
    error_code[2] = 'Not connected'
    error_code[3] = 'Client DLL not valid, check 64 bit'
    error_code[4] = 'Hardware not found'
    error_code[5] = 'Server start timeout'
    error_code[6] = 'Server just started'
    error_code[7] = 'Server is running'
    error_code[8] = 'EEID not valid'
    error_code[9] = 'Server started'
    error_code[10] = 'Already closed'
    error_code[11] = 'Server start error'
    error_code[12] = 'Bad DLL image'

    command_dict = {}
    command_dict['GETPOSITION'] = 51
    command_dict['ABSMOVE'] = 7
    command_dict['VELZERO'] = 13
    command_dict['SERVOMODE'] = 50
    command_dict['STOP'] = 16

    eeid_dict = {}
    eeid_dict['XAXIS'] = 1
    eeid_dict['ZAXIS'] = 0

    def __init__(self, dll_object, hwtype, label=''):
        """
        @param str path_dll: the absolute path to the dll of the current
                             operating system
        @param int serialnumber: serial number of the stage
        @param str hwtype: name for the type of the hardware device you want to
                           control. The name must be available in hwtype_dict!
        @param str label: a label which identifies the axis and gives
                          it a meaning.
        @param str unit: the unit of this axis, possible entries are m, ° or
                         degree
        """

        self.novadll = dll_object
        self.eepromid = c_uint()

        default_hw = 1016
        self.deviceid = c_uint(self.hwtype_dict.get(hwtype, default_hw))

        self.verbose = False

        try:
            self.eeid = c_uint(self.eeid_dict.get(label))
        except KeyError:
            self.log.error('Cannot find label in dictionary')

        self.velocity = c_int16()
        self._wait_until_done = True
        self.count = c_ushort()
        self.flags = c_ubyte()
        self.error = c_uint()
        self.id = c_uint()
        self.command = c_uint()
        self.nreads = c_short()
        self.time = c_double()
        self.nbytes = c_ubyte()
        self.b0 = c_ubyte()
        self.b1 = c_ubyte()
        self.b2 = c_ubyte()
        self.b3 = c_ubyte()
        self.b4 = c_ubyte()
        self.b5 = c_ubyte()
        self.b6 = c_ubyte()
        self.b7 = c_ubyte()
        self.rx_tx_no = c_int()
        self.timeout = c_int()

        self.log = logging.getLogger(__name__)
        #self.log.info('test')

    def twos_comp(self, val, bits):
        """compute the 2's compliment of int value val"""
        if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << bits)  # compute negative value
        return val  # return positive value as i

    def write_to_server(self):
        self.novadll.write(self.eepromid, self.deviceid, self.eeid, self.command, byref(self.rx_tx_no), self.nbytes,
                           self.b0, self.b1, self.b2,
                           self.b3, self.b4, self.b5, self.b6, self.b7, self.timeout, byref(self.error))

    def read_from_server(self):
        self.novadll.read(self.eepromid, self.deviceid, self.eeid, self.command, byref(self.count), byref(self.flags),
                          byref(self.id),
                          byref(self.nbytes), byref(self.nreads), byref(self.time), byref(self.b0), byref(self.b1),
                          byref(self.b2), byref(self.b3),
                          byref(self.b4), byref(self.b5), byref(self.b6), byref(self.b7), self.timeout,
                          byref(self.error))

    def clear_bits(self):
        self.b0 = c_ubyte()
        self.b1 = c_ubyte()
        self.b2 = c_ubyte()
        self.b3 = c_ubyte()
        self.b4 = c_ubyte()
        self.b5 = c_ubyte()
        self.b6 = c_ubyte()
        self.b7 = c_ubyte()


    def get_velocity(self):
        """ Get the current velocity by querying position using command 51 and only converting the velocity bits
        """
        self.command = self.command_dict.get('GETPOSITION')

        self.write_to_server()

        self.read_from_server()

        self.velocity = self.twos_comp((self.b1.value << 8) | self.b0.value,16)

        return self.velocity

    def set_velocity(self, vel):
        """ Set the maximal velocity for the motor movement.

        @param float vel: velocity of the stage in m/s.
        """
        i16StepVelSoll = int(vel)
        self.b0 = (i16StepVelSoll & 0xff);
        self.b1 = ((i16StepVelSoll >> 8) & 0xff);

    def get_home_parameter(self):
        """ Get the home parameter"""
        home_direction = c_long()
        limit_switch = c_long()
        home_velocity = c_float()
        zero_offset = c_float()
        # self.aptdll.MOT_GetHomeParams(self.SerialNum, pointer(home_direction),
        #                               pointer(limit_switch),
        #                               pointer(home_velocity),
        #                               pointer(zero_offset))

        home_param = [home_direction.value, limit_switch.value,
                      home_velocity.value, zero_offset.value]

        return home_param

    def set_home_parameter(self, home_dir, switch_dir, home_vel, zero_offset):
        """ Set the home parameters.
        @param int home_dir: direction to the home position,
                                1 = Move forward
                                2 = Move backward
        @param int switch_dir: Direction of the switch limit:
                                 4 = Use forward limit switch for home datum
                                 1 = Use forward limit switch for home datum.
        @param float home_vel = default velocity
        @param float zero_offset: the distance or offset (in mm or degrees) of
                                  the limit switch from the Home position.

        """
        home_dir_c = c_long(home_dir)
        switch_dir_c = c_long(switch_dir)
        home_vel_c = c_float(home_vel)
        zero_offset_c = c_float(zero_offset)
        # self.aptdll.MOT_SetHomeParams(self.SerialNum, home_dir_c, switch_dir_c,
        #                               home_vel_c, zero_offset_c)

        return True

    def get_pos(self):
        """ Obtain the current absolute position of the stage.

        @return float: the value of the axis either in m or in degree.
        """
        self.command = self.command_dict.get('GETPOSITION')
        # self.log.info('hi there')
        self.write_to_server()
        # if self.error.value != 0:
        #     self.log.error(self.error_code[self.error.value])

        self.read_from_server()
        # if self.error.value != 0:
        #     self.log.error(self.error_code[self.error.value])
        #position = 4
        # read the position off the stack
        position = self.twos_comp(self.b5.value << 24) | (self.b4.value << 16) | (self.b3.value << 8) | self.b2.value,32)

        # self.log.info(position)

        return position / 1000000000.0


    def move_rel(self, relDistance):
        """ Moves the motor a relative distance specified

        @param float relDistance: Relative position desired, in m or in degree.
        """
        if self.verbose:
            print('move_rel ', relDistance, c_float(relDistance))
        if not self.Connected:
            # TODO: This should use our error message system
            print('Please connect first! Use initializeHardwareDevice')

        if self._unit == 'm':
            relativeDistance = c_float(relDistance * 1000.0)
        else:
            relativeDistance = c_float(relDistance)

        # self.aptdll.MOT_MoveRelativeEx(self.SerialNum, relativeDistance, self._wait_until_done)
        if self.verbose:
            print('move_rel SUCESS')


    def move_abs(self, i32PosSoll):
        """ Moves the motor to the Absolute position specified using servo mode

        @param float absPosition: absolute Position desired, in m or degree.
        """
        i32PosSoll = int(i32PosSoll*100000000)
        self.b2.value = (i32PosSoll & 0xff)
        self.b3.value = ((i32PosSoll >> 8) & 0xff)
        self.b4.value = ((i32PosSoll >> 16) & 0xff)
        self.b5.value = ((i32PosSoll >> 24) & 0xff)
        #position = self.twos_comp(((self.b5.value << 24) | (self.b4.value << 16) | (self.b3.value << 8) | self.b2.value), 32)
        self.command = self.command_dict.get('SERVOMODE')
        self.log.info(position)
        self.write_to_server()

        return True

    # --------------------------- Miscellaneous --------------------------------

    def _create_status_dict(self):
        """ Extract from the status integer all possible states.
        "return:
        """
        status = {}
        status[0] = 'magnet stopped'
        status[1] = 'magnet moves forward'
        status[2] = 'magnet moves backward'

        return status

    def get_status(self):
        """ Get the status bits of the current axis.

        @return tuple(int, dict): the current status as an integer and the
                                  dictionary explaining the current status.
        """

        status_bits = c_long()
        #self.aptdll.MOT_GetStatusBits(self.SerialNum, pointer(status_bits))

        # Check at least whether magnet is moving:

        if self._test_bit(status_bits.value, 4):
            return 1, self._create_status_dict()
        elif self._test_bit(status_bits.value, 5):
            return 2, self._create_status_dict()
        else:
            return 0, self._create_status_dict()

    def abort(self):
        """ Abort the movement. """
        self.command = self.command_dict.get('STOP')
        self.clear_bits()
        self.b0 = c_ubyte(1)
        self.write_to_server()

    def go_home(self):

        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')

        # TODO: a proper home position has to be set, not just zero.
        self.move_abs(0.0)

    def _test_bit(self, int_val, offset):
        """ Check a bit in an integer number at position offset.

        @param int int_val: an integer value, which is checked
        @param int offset: the position which should be checked whether in
                           int_val for a bit of 1 is set.

        @return bool: Check in an integer representation, whether the bin at the
                      position offset is set to 0 or to 1. If bit is set True
                      will be returned else False.
        """
        mask = 1 << offset
        return (int_val & mask) != 0

    def set_backlash(self, backlash):
        """ Set the provided backlash for the apt motor.

        @param float backlash: the backlash in m or degree for the used stage.
        """

        if self._unit == 'm':
            # controller needs values in mm:
            c_backlash = c_float(backlash * 1000)
        else:
            c_backlash = c_float(backlash)

        #self.aptdll.MOT_SetBLashDist(self.SerialNum, c_backlash)

        self._backlash = backlash
        return backlash

    def get_backlash(self):
        """ Ask for the currently set backlash in the controller for the axis.

        @return float: backlash in m or degree, depending on the axis config.
        """
        backlash = c_float()
        #self.aptdll.MOT_GetBLashDist(self.SerialNum, pointer(backlash))

        if self._unit == 'm':
            self._backlash = backlash.value / 1000
        else:
            self._backlash = backlash.value

        return self._backlash


# ==============================================================================

class NOVAStage(Base, MotorInterface):
    """ Control class for an arbitrary collection of axis. Do not use this
        Class directly but inherit this class to a new Class, where also the
        method get_constraints() is specified for that specific set of a
        hardware.
        If it is really necessary to change an already existing interface
        module, then overwrite it in the class, which inherited that class.
     """
    hwtype_dict = {}
    hwtype_dict['HWTYPE_NDMS1'] = 1016  # 1 Ch motor driver
    hwtype_dict['HWTYPE NDS40'] = 1011  # 1 Ch stepper driver

    # the error code is also comparable to the NOVA server documentation.
    error_code = {}
    error_code[0] = 'IPC valid'
    error_code[1] = 'IPC error - is there another connection still running?'
    error_code[2] = 'Not connected'
    error_code[3] = 'Client DLL not valid, check 64 bit'
    error_code[4] = 'Hardware not found'
    error_code[5] = 'Server start timeout'
    error_code[6] = 'Server just started'
    error_code[7] = 'Server is running'
    error_code[8] = 'EEID not valid'
    error_code[9] = 'Server started'
    error_code[10] = 'Already closed'
    error_code[11] = 'Server start error'
    error_code[12] = 'Bad DLL image'

    def on_activate(self, e):
        """ Initialize instance variables and connect to hardware as configured.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """

        # create the magnet dump folder
        self._magnet_dump_folder = self._get_magnet_dump()

        # Load DLL
        if platform.architecture()[0] == '64bit':
            path_dll = os.path.join(self.get_main_dir(), 'thirdparty',
                                    'nova',
                                    'win64',
                                    'CClientdll_64.dll')
        elif platform.architecture()[0] == '32bit':
            path_dll = os.path.join(self.get_main_dir(), 'thirdparty',
                                    'nova',
                                    'win32',
                                    'CClientdll.dll')
        else:
            self.log.error('Unknown platform, cannot load the NOVA dll.')

        # Read HW from config
        config = self.getConfiguration()
        self.novadll = WinDLL(path_dll)
        self.eepromid = c_int()
        self.serverprocessid = c_int()  # this is passed back but never used
        self.error = c_uint()
        self.novadll.open(self.eepromid, byref(self.serverprocessid), byref(self.error))

        if self.error.value == 0:
            self.log.info('Setup connection to NOVA server')
        elif self.error.value == 1:
            self.log.error(self.error_code[self.error.value])
            self.novadll.close(self.eepromid, byref(self.error))
            self.log.error(self.error_code[self.error.value])
            self.novadll.open(self.eepromid, byref(self.serverprocessid), byref(self.error))
        else:
            self.log.error('Was unable to open connection')
            self.log.error(self.error_code[self.error.value])


        if 'motor_type_label' in config.keys():
            self.log.info(config['motor_type_label'])
            self._motor_type_label = config['motor_type_label']
        else:
            self.log.error('Motor Hardware-controller-type, serial-number '
                           'and label for x axis not found in the configuration.\n'
                           'Each axis has to be chosen like:\n'
                           '[("<hw_type>", "<axis_label>"), '
                           '("<hw_type>",  "<axis_label>"), ...]\n'
                           'and assigned to the attribute '
                           'motor_type_label.')

        # here are all the references to the different axis are stored:
        self._axis_dict = OrderedDict()

        limits_dict = self.get_constraints()

        # the variable self._motor_type_serial_label is a list, which contains
        # the information about each axis. Three information about each axis
        # have to be present:
        #   1. hw_type: hardware type of the controller, it must be one entry
        #      from the dict hwtype_dict of the generic class APTMotor
        #   2. serial_num: the serial number assigned to that axis
        #   3. label: the label you give that axis. Note that this label should
        #      coincide with the label defined in the get_constraints methods.
        #
        # Therefore self._motor_type_serial_label is looking like:
        #   [(hw_type, serial_num, label), (hw_type, serial_num, label), ...]

        for (hw_type, label) in self._motor_type_label:
            if limits_dict.get(label) is not None:
                self._axis_dict[label] = NOVAMotor(self.novadll,
                                                   hw_type, label)

            else:
                self.log.error('The following label "{0}" cannot be found in '
                               'the constraints method!\nCheck whether label '
                               'coincide with the label given in the config!\n'
                               'Restart the program!')

        self.custom_activation(e)

    def custom_activation(self, e):
        """ That activation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def on_deactivate(self, e):
        """ Disconnect from hardware and clean up.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """

        for label_axis in self._axis_dict:
            #set velocity to 0
            self._axis_dict[label_axis].abort()
        self.novadll.close(self.eepromid, byref(self.error))
        self.custom_deactivation(e)

    def custom_deactivation(self, e):
        """ That deactivation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def move_rel(self, param_dict):
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
        """
        curr_pos_dict = self.get_pos()
        constraints = self.get_constraints()

        for label_axis in self._axis_dict:

            if param_dict.get(label_axis) is not None:
                move = param_dict[label_axis]
                curr_pos = curr_pos_dict[label_axis]

                if (curr_pos + move > constraints[label_axis]['pos_max']) or \
                        (curr_pos + move < constraints[label_axis]['pos_min']):

                    self.log.warning('Cannot make further relative movement '
                                     'of the axis "{0}" since the motor is at '
                                     'position {1} and with the step of {2} it would '
                                     'exceed the allowed border [{3},{4}]! Movement '
                                     'is ignored!'.format(
                        label_axis,
                        move,
                        curr_pos,
                        constraints[label_axis]['pos_min'],
                        constraints[label_axis]['pos_max']))
                else:
                    self._save_pos({label_axis: curr_pos + move})
                    self._axis_dict[label_axis].move_rel(move)

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        A smart idea would be to ask the position after the movement.
        """
        constraints = self.get_constraints()

        for label_axis in self._axis_dict:
            if param_dict.get(label_axis) is not None:
                desired_pos = param_dict[label_axis]

                constr = constraints[label_axis]
                if not (constr['pos_min'] <= desired_pos <= constr['pos_max']):

                    self.log.warning('Cannot make absolute movement of the '
                                     'axis "{0}" to position {1}, since it exceeds '
                                     'the limits [{2},{3}]. Movement is ignored!'
                                     ''.format(label_axis, desired_pos, constr['pos_min'], constr['pos_max']))
                else:
                    self._save_pos({label_axis: desired_pos})
                    self._axis_dict[label_axis].move_abs(desired_pos)

    def abort(self):
        """ Stops movement of the stage. """

        for label_axis in self._axis_dict:
            self._axis_dict[label_axis].abort()

        self.log.warning('Movement of all the axis aborted! Stage stopped.')

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
            self.log.info(param_list)
            for label_axis in param_list:
                if label_axis in self._axis_dict:
                    pos[label_axis] = self._axis_dict[label_axis].get_pos()
        else:
            for label_axis in self._axis_dict:
                pos[label_axis] = self._axis_dict[label_axis].get_pos()

        return pos

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.


        """

        status = {}
        if param_list is not None:
            for label_axis in param_list:
                if label_axis in self._axis_dict:
                    status[label_axis] = self._axis_dict[label_axis].get_status()
        else:
            for label_axis in self._axis_dict:
                status[label_axis] = self._axis_dict[label_axis].get_status()

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
        raise InterfaceImplementationError('MagnetStageInterface>calibrate')

        # TODO: read out a saved home position in file and compare that with the
        #      last position saved also in file. The difference between these
        #      values will determine the absolute home position.
        #
        if param_list is not None:
            for label_axis in param_list:
                if label_axis in self._axis_dict:
                    self._axis_dict[label_axis].go_home()
        else:
            for label_axis in self._axis_dict:
                self._axis_dict[label_axis].go_home()

    def _save_pos(self, param_dict):
        """ Save after each move the parameters to file, since the motor stage
        looses any information if it is initialized. That might be a way to
        store and retrieve the current position.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed.
        """

        for label_axis in param_dict:
            if label_axis in self._axis_dict:
                pos = param_dict[label_axis]
                filename = os.path.join(self._magnet_dump_folder,
                                        label_axis + '.dat')
                with open(filename, 'w') as f:
                    f.write(str(pos))

    def _get_magnet_dump(self):
        """ Create the folder where the position file is saved, and check
        whether it exists.

        @return str: the path to the created folder."""

        path = self.get_home_dir()
        magnet_path = os.path.join(path, 'magnet')

        if not os.path.exists(magnet_path):
            os.makedirs(magnet_path)
            self.log.info('Magnet dump was created in:\n'
                          '{}'.format(magnet_path))
        return magnet_path

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
            for label_axis in param_list:
                if label_axis in self._axis_dict:
                    vel[label_axis] = self._axis_dict[label_axis].get_velocity()
        else:
            for label_axis in self._axis_dict:
                vel[label_axis] = self._axis_dict[label_axis].get_velocity()

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

        for label_axis in param_dict:
            if label_axis in self._axis_dict:
                desired_vel = param_dict[label_axis]
                constr = constraints[label_axis]
                if not (constr['vel_min'] <= desired_vel <= constr['vel_max']):
                    self.log.warning('Cannot set velocity of the axis "{0}" '
                                     'to the desired velocity of "{1}", since it '
                                     'exceeds the limits [{2},{3}] ! Command is ignored!'
                                     ''.format(label_axis, desired_vel, constr['vel_min'], constr['vel_max']))
            else:
                self._axis_dict[label_axis].set_velocity(desired_vel)


class NOVAOneAxisStage(NOVAStage):
    _modclass = 'NovaOneAxis'
    _modtype = 'hardware'

    # connectors
    _out = {'novamotor': 'MotorInterface'}

    def custom_activation(self, e):
        """ That activation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation of the
                         parent class APTStage.

        """
        # my specific settings for the stage can be set here.
        # remember to set the units to degree if you want to use it as a
        # rotation stage, like that:
        #   min_pos, max_pos, unit_read, pinch = self.get_stage_axis_info()
        #   self._axis_dict[label].set_stage_axis_info(min_pos, max_pos, unit, pinch)


        # # my specific settings for the stage:
        # limits_dict = self.get_constraints()
        #
        # for label_axis in self._axis_dict:
        #
        #     # adapt the hardware controller to the proper unit set:
        #     if limits_dict[label_axis]['unit'] == '°' or limits_dict[label_axis]['unit'] == 'degree':
        #         unit = 2  # for rotation movement
        #         # FIXME: the backlash parameter has to be taken from the config and
        #         #       should not be hardcoded here!!
        #         #pitch = 7.5
        #         #backlash_correction = 0.2
        #     else:
        #         unit = 1  # default value for linear movement
        #         #pitch = 1
        #         #backlash_correction = 0.10e-3
        #
        #     self._axis_dict[label_axis].set_stage_axis_info(
        #         limits_dict[label_axis]['pos_min'],
        #         limits_dict[label_axis]['pos_max'],
        #         pitch=pitch, unit=unit)
        #     self._axis_dict[label_axis].setVelocityParameters(
        #         limits_dict[label_axis]['vel_min'],
        #         limits_dict[label_axis]['acc_max'],
        #         limits_dict[label_axis]['vel_max'])
        #     self._axis_dict[label_axis].set_velocity(limits_dict[label_axis]['vel_max'])
        #     self._axis_dict[label_axis].setHardwareLimitSwitches(2, 2)
        #     self._axis_dict[label_axis]._wait_until_done = False
        #     # set the backlach correction in m since the forward movement is
        #     # preciser than the backward:
        #     self._axis_dict[label_axis].set_backlash(backlash_correction)

    def custom_deactivation(self, e):
        """ That deactivation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation of the
                         parent class APTStage.
        """
        pass

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
        constraints = {}

        # be careful, if the pinch is not set correctly, the units are not the
        # write ones! Check the pinch for the used traveling unit in the file
        # MG17APTServer.ini

        # FIXME: the numbers for the constraints should be obtained from the
        #       configuration and should be not hardcoded here into this file!

        # constraints for the axis of type CR1-Z7:
        # set the constraints for the phi axis:
        axis0 = {}
        axis0['label'] = 'XAXIS'  # That name must coincide with the given
        # name in the config. Otherwise there is no
        # way of identifying the used axes.
        axis0['unit'] = 'm'  # the SI units, only possible mm or degree
        axis0['ramp'] = ['Trapez']  # a possible list of ramps
        axis0['pos_min'] = 0  # in °
        axis0['pos_max'] = 360  # that is basically the traveling range
        axis0['pos_step'] = 0.01  # in °
        axis0['vel_min'] = 0.1  # in °/s
        axis0['vel_max'] = 4.5  # in °/s
        axis0['vel_step'] = 0.1  # in °/s (a rather arbitrary number)
        axis0['acc_min'] = 4.0  # in °/s^2
        axis0['acc_max'] = 5.0  # in °/s^2
        axis0['acc_step'] = 0.01  # in °/s^2 (a rather arbitrary number)

        constraints[axis0['label']] = axis0

        return constraints


class NOVATwoAxisStage(NOVAStage):
    """ The module controls two StepperStage56=NRT150 Enc Stage 150mm
    """

    _modclass = 'NOVATwoAxis'
    _modtype = 'hardware'

    # connectors
    _out = {'novamotor': 'MotorInterface'}

    def custom_activation(self, e):
        """ That activation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation of the
                         parent class APTStage.

        """

        # # my specific settings for the stage:
        # limits_dict = self.get_constraints()
        #
        # for label_axis in self._axis_dict:
        #
        #     # adapt the hardware controller to the proper unit set:
        #     if limits_dict[label_axis]['unit'] == '°' or limits_dict[label_axis]['unit'] == 'degree':
        #         unit = 2  # for rotation movement
        #         # FIXME: the backlash parameter has to be taken from the config and
        #         #       should not be hardcoded here!!
        #         #pitch = 7.5
        #         #backlash_correction = 0.2
        #     else:
        #         unit = 1  # default value for linear movement
        #         #pitch = 1
        #         #backlash_correction = 0.10e-3
        #
        #     self._axis_dict[label_axis].set_stage_axis_info(
        #         limits_dict[label_axis]['pos_min'],
        #         limits_dict[label_axis]['pos_max'],
        #         pitch=pitch, unit=unit)
        #     self._axis_dict[label_axis].setVelocityParameters(
        #         limits_dict[label_axis]['vel_min'],
        #         limits_dict[label_axis]['acc_max'],
        #         limits_dict[label_axis]['vel_max'])
        #     self._axis_dict[label_axis].set_velocity(limits_dict[label_axis]['vel_max'])
        #     self._axis_dict[label_axis].setHardwareLimitSwitches(2, 2)
        #     self._axis_dict[label_axis]._wait_until_done = False
        #
        #     # set the backlach correction in m since the forward movement is
        #     # preciser than the backward:
        #     self._axis_dict[label_axis].set_backlash(backlash_correction)

    def custom_deactivation(self, e):
        """ That deactivation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation of the
                         parent class APTStage.
        """
        pass

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

        # FIXME: the numbers for the constraints should be obtained from the
        #       configuration and should be not hardcoded here into this file!

        constraints = OrderedDict()

        # set the constraints for the x axis:
        axis0 = {}
        axis0['label'] = 'XAXIS'  # That name must coincide with the given
        # name in the config. Otherwise there is no
        # way of identifying the used axes.
        axis0['unit'] = 'm'  # the SI units, only possible mm or degree
        axis0['ramp'] = ['Trapez']  # a possible list of ramps
        axis0['pos_min'] = -65e-3  # in m
        axis0['pos_max'] = 65e-3  # that is basically the traveling range
        axis0['pos_step'] = 3.0e-6  # in m (a rather arbitrary number)
        axis0['vel_min'] = 0.1e-3  # in m/s
        axis0['vel_max'] = 2.0e-3  # in m/s
        axis0['vel_step'] = 1.0e-6  # in m/s (a rather arbitrary number)
        axis0['acc_min'] = 10e-6  # in m/s^2
        axis0['acc_max'] = 500e-6  # in m/s^2
        axis0['acc_step'] = 1.0e-6  # in m/s^2 (a rather arbitrary number)

        # set the constraints for the y axis:
        axis1 = {}
        axis1['label'] = 'ZAXIS'  # That name must coincide with the given
        # name in the config. Otherwise there is no
        # way of identifying the used axes.
        axis1['unit'] = 'm'  # the SI units, only possible mm or degree
        axis1['ramp'] = ['Trapez']  # a possible list of ramps
        axis1['pos_min'] = -65e-3  # in m
        axis1['pos_max'] = 65e-3  # that is basically the traveling range
        axis1['pos_step'] = 3.0e-6  # in m (a rather arbitrary number)
        axis1['vel_min'] = 0.1e-3  # in m/s
        axis1['vel_max'] = 2.0e-3  # in m/s
        axis1['vel_step'] = 1.0e-6  # in m/s (a rather arbitrary number)
        axis1['acc_min'] = 10e-6  # in m/s^2
        axis1['acc_max'] = 500e-6  # in m/s^2
        axis1['acc_step'] = 1.0e-6  # in m/s^2 (a rather arbitrary number)

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1

        return constraints
