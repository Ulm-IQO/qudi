# -*- coding: utf-8 -*-
"""
APT Motor Controller for Thorlabs.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Lachlan J. Rogers lachlan.rogers@uni-ulm.de
Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

"""
This module was developed from PyAPT, written originally by Michael Leung
(mcleung@stanford.edu). Have a look in:
    https://github.com/HaeffnerLab/Haeffner-Lab-LabRAD-Tools/blob/master/cdllservers/APTMotor/APTMotorServer.py
APT.dll and APT.lib were provided to PyAPT thanks to SeanTanner@ThorLabs .
All the specific error and status code are taken from:
    https://github.com/UniNE-CHYN/thorpy

"""

from collections import OrderedDict

from core.base import Base
from ctypes import c_long, c_buffer, c_float, windll, pointer
from interface.motor_interface import MotorInterface
import os
import platform


class APTMotor():
    """ Class to control Thorlabs APT motor. This class wrapps the low level
        commands from a dll library in python methods.
    """

    # all the possible hardware types that are available to be controlled by
    # the apt.dll
    hwtype_dict ={}
    hwtype_dict['HWTYPE_BSC001'] = 11   # 1 Ch benchtop stepper driver
    hwtype_dict['HWTYPE_BSC101'] = 12   # 1 Ch benchtop stepper driver
    hwtype_dict['HWTYPE_BSC002'] = 13   # 2 Ch benchtop stepper driver
    hwtype_dict['HWTYPE_BDC101'] = 14   # 1 Ch benchtop DC servo driver
    hwtype_dict['HWTYPE_SCC001'] = 21   # 1 Ch stepper driver card (used within BSC102,103 units)
    hwtype_dict['HWTYPE_DCC001'] = 22   # 1 Ch DC servo driver card (used within BDC102,103 units)
    hwtype_dict['HWTYPE_ODC001'] = 24   # 1 Ch DC servo driver cube
    hwtype_dict['HWTYPE_OST001'] = 25   # 1 Ch stepper driver cube
    hwtype_dict['HWTYPE_MST601'] = 26   # 2 Ch modular stepper driver module
    hwtype_dict['HWTYPE_TST001'] = 29   # 1 Ch Stepper driver T-Cube
    hwtype_dict['HWTYPE_TDC001'] = 31   # 1 Ch DC servo driver T-Cube
    hwtype_dict['HWTYPE_LTSXXX'] = 42   # LTS300/LTS150 Long Travel Integrated Driver/Stages
    hwtype_dict['HWTYPE_L490MZ'] = 43   # L490MZ Integrated Driver/Labjack
    hwtype_dict['HWTYPE_BBD10X'] = 44   # 1/2/3 Ch benchtop brushless DC servo driver

    error_code= {}
    error_code[10000] = 'Unknown error'
    error_code[10001] = 'Internal error'
    error_code[10002] = 'Call has failed'
    error_code[10003] = 'Invalid or out-of-range parameter'
    error_code[10051] = 'Error while accessing hard disk'
    error_code[10052] = 'Error while accessing registry'
    error_code[10053] = 'Internal memory allocation or de-allocation error'
    error_code[10054] = 'COM system error'
    error_code[10055] = 'USB communication error'
    error_code[10100] = 'Unknown serial number'
    error_code[10101] = 'Duplicate Serial Number'
    error_code[10102] = 'Duplicate Device Identifier'
    error_code[10103] = 'Invalid message source'
    error_code[10104] = 'Message received with unknown identifier'
    error_code[10106] = 'Invalid serial number'
    error_code[10107] = 'Invalid message destination ident'
    error_code[10108] = 'Invalid index'
    error_code[10109] = 'Control is currently not communicating'
    error_code[10110] = 'Hardware fault or illegal command or parameter has been sent to hardware'
    error_code[10111] = 'Time out while waiting for hardware unit to respond'
    error_code[10112] = 'Incorrect firmware version'
    error_code[10115] = 'Your hardware is not compatible'
    error_code[10150] = 'No stage has been assigned'
    error_code[10151] = 'Internal error when using an encoded stage'
    error_code[10152] = 'Internal error when using an encoded stage'
    error_code[10153] = 'Call only applicable to encoded stages'

    # The status is encodes in a 32bit word. Some bits in that word have no
    # assigned meaning, or their meaning could not be deduced from the manual.
    # The known status bits are stated below. The current status can also be a
    # combination of status bits. Therefore you have to check with an AND
    # bitwise comparison, which status your device has.
    status_code = {}
    status_code[1] = '0x00000001: forward hardware limit switch is active'
    status_code[2] = '0x00000002: reverse hardware limit switch is active'
    status_code[16] = '0x00000010: in motion, moving forward'
    status_code[32] = '0x00000020: in motion, moving reverse'
    status_code[64] = '0x00000040: in motion, jogging forward'
    status_code[128] = '0x00000080: in motion, jogging reverse'
    status_code[512] = '0x00000200: in motion, homing'
    status_code[1024] = '0x00000400: homed (homing has been completed)'
    status_code[4096] = '0x00001000: tracking'
    status_code[8192] = '0x00002000: settled'
    status_code[16384] = '0x00004000: motion error (excessive position error)'
    status_code[16777216] = '0x01000000: motor current limit reached'
    status_code[2147483648] = '0x80000000: channel is enabled'



    def __init__(self, path_dll, serialnumber, hwtype, label=''):
        """
        @param str path_dll: the absolute path to the dll of the current
                             operating system
        @param int serialnumber: serial number of the stage
        @param str hwtype: name for the type of the hardware device you want to
                           control. The name must be available in hwtype_dict!
        @param str label: optional, a label which identifies the axis and gives
                          it a meaning.
        """

        self.aptdll = windll.LoadLibrary(path_dll)
        self.aptdll.EnableEventDlg(True)
        self.aptdll.APTInit()
        self._HWType = c_long(self.hwtype_dict[hwtype])
        self.Connected = False
        self.verbose = False
        self.label = label
        self.setSerialNumber(serialnumber)
        self._wait_until_done = True

    def getNumberOfHardwareUnits(self):
        """ Returns the number of connected external hardware (HW) units that
            are available to be interfaced.
        """
        numUnits = c_long()
        self.aptdll.GetNumHWUnitsEx(self._HWType, pointer(numUnits))
        return numUnits.value

    def getSerialNumberByIdx(self, index):
        """ Returns the Serial Number of the specified index """
        HWSerialNum = c_long()
        hardwareIndex = c_long(index)
        self.aptdll.GetHWSerialNumEx(self._HWType, hardwareIndex, pointer(HWSerialNum))
        return HWSerialNum

    def setSerialNumber(self, SerialNum):
        '''
        Sets the Serial Number of the specified index
        '''
        if self.verbose:
            print("Serial is", SerialNum)
        self.SerialNum = c_long(SerialNum)
        return self.SerialNum.value

    def initializeHardwareDevice(self):
        '''
        Initialises the motor.
        You can only get the position of the motor and move the motor after it
        has been initialised. Once initiallised, it will not respond to other
        objects trying to control it, until released.
        '''
        if self.verbose:
            print('initializeHardwareDevice serial', self.SerialNum)
        result = self.aptdll.InitHWDevice(self.SerialNum)
        if result == 0:
            self.Connected = True
            if self.verbose:
                print('initializeHardwareDevice connection SUCESS')
        # need some kind of error reporting here
        else:
            raise Exception('Connection Failed. Check Serial Number!')
        return True

        ''' Interfacing with the motor settings '''

    def getHardwareInformation(self):
        ''' Get information from the hardware'''
        model = c_buffer(255)
        softwareVersion = c_buffer(255)
        hardwareNotes = c_buffer(255)
        self.aptdll.GetHWInfo(self.SerialNum, model, 255, softwareVersion, 255, hardwareNotes, 255)
        hwinfo = [model.value, softwareVersion.value, hardwareNotes.value]
        return hwinfo

    def get_stage_axis_info(self):
        """ Get parameter configuration of the stage """
        minimumPosition = c_float()
        maximumPosition = c_float()
        units = c_long()
        pitch = c_float()
        self.aptdll.MOT_GetStageAxisInfo(self.SerialNum, pointer(minimumPosition), pointer(maximumPosition), pointer(units), pointer(pitch))
        stageAxisInformation = [minimumPosition.value, maximumPosition.value, units.value, pitch.value]
        return stageAxisInformation

    def set_stage_axis_info(self, pos_min , pos_max, pitch, unit=1 ):
        """ Set parameter configuration of the stage.

        @param float pos_min: minimal position of the axis.
        @param float pos_max: maximal position of the axis.
        @param float pitch: the pitch determines the full step angle of a
                            stepper magnet motor. That is the resolution of the
                            stepper motor.
        @param int unit: unit of the axis, possible values:
                            1 = mm
                            2 = degree
        """
        pos_min_c = c_float(pos_min)
        pos_max_c = c_float(pos_max)
        unit_c = c_long(unit)  # units of mm
        # Get different pitches of lead screw for moving stages for different stages.
        pitch_c = c_float(pitch)
        self.aptdll.MOT_SetStageAxisInfo(self.SerialNum, pos_min_c, pos_max_c,
                                         unit_c, pitch_c)
        return True

    def getHardwareLimitSwitches(self):
        reverseLimitSwitch = c_long()
        forwardLimitSwitch = c_long()
        self.aptdll.MOT_GetHWLimSwitches(self.SerialNum, pointer(reverseLimitSwitch), pointer(forwardLimitSwitch))
        hardwareLimitSwitches = [reverseLimitSwitch.value, forwardLimitSwitch.value]
        return hardwareLimitSwitches

    def setHardwareLimitSwitches(self, switch_reverse, switch_forward):
        """ Set the Switch Configuration of the axis.

        @param int switch_reverse: sets the switch in reverse movement
        @param int switch_forward: sets the switch in forward movement

        The following values are allowed:
        0x01 or 1: Ignore switch or switch not present.
        0x02 or 2: Switch makes on contact.
        0x03 or 3: Switch breaks on contact.
        0x04 or 4: Switch makes on contact - only used for homes (e.g. limit switched rotation stages).
        0x05 or 5: Switch breaks on contact - only used for homes (e.g. limit switched rotations stages).
        0x06 or 6: For PMD based brushless servo controllers only - uses index mark for homing.
        """
        reverseLimitSwitch = c_long(switch_reverse)
        forwardLimitSwitch = c_long(switch_forward)
        self.aptdll.MOT_SetHWLimSwitches(self.SerialNum, reverseLimitSwitch, forwardLimitSwitch)
        hardwareLimitSwitches = [reverseLimitSwitch.value, forwardLimitSwitch.value]
        return hardwareLimitSwitches


    def getVelocityParameters(self):
        """ TODO docstring
        """
        minimumVelocity = c_float()
        acceleration = c_float()
        maximumVelocity = c_float()
        self.aptdll.MOT_GetVelParams(self.SerialNum, pointer(minimumVelocity), pointer(acceleration), pointer(maximumVelocity))
        velocityParameters = [minimumVelocity.value, acceleration.value, maximumVelocity.value]
        return velocityParameters

    def get_velocity(self):
        """ Get the current velocity setting
        """
        if self.verbose:
            print('get_velocity probing...')
        minVel, acc, maxVel = self.getVelocityParameters()
        if self.verbose:
            print('get_velocity maxVel')
        return maxVel

    def setVelocityParameters(self, minVel, acc, maxVel):
        minimumVelocity = c_float(minVel)
        acceleration = c_float(acc)
        maximumVelocity = c_float(maxVel)
        self.aptdll.MOT_SetVelParams(self.SerialNum, minimumVelocity, acceleration, maximumVelocity)
        return True

    def set_velocity(self, maxVel):
        """set the velocity for the motor movement
        """
        if self.verbose:
            print('set_velocity', maxVel)
        minVel, acc, oldVel = self.getVelocityParameters()
        self.setVelocityParameters(minVel, acc, maxVel)
        return True

    def getVelocityParameterLimits(self):
        maximumAcceleration = c_float()
        maximumVelocity = c_float()
        self.aptdll.MOT_GetVelParamLimits(self.SerialNum, pointer(maximumAcceleration), pointer(maximumVelocity))
        velocityParameterLimits = [maximumAcceleration.value, maximumVelocity.value]
        return velocityParameterLimits

        '''
        Controlling the motors
        m = move
        c = controlled velocity
        b = backlash correction

        Rel = relative distance from current position.
        Abs = absolute position
        '''

    def get_home_parameter(self):
        """ Get the home parameter"""
        home_direction = c_long()
        limit_switch = c_long()
        home_velocity = c_float()
        zero_offset = c_float()
        self.aptdll.MOT_GetHomeParams(self.SerialNum, pointer(home_direction),
                                      pointer(limit_switch),
                                      pointer(home_velocity),
                                      pointer(zero_offset))

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
        @param float zero_offset: Offset from the home position.

        """
        home_dir_c = c_long(home_dir)
        switch_dir_c = c_long(switch_dir)
        home_vel_c = c_float(home_vel)
        zero_offset_c = c_float(zero_offset)
        self.aptdll.MOT_SetHomeParams(self.SerialNum, home_dir_c, switch_dir_c,
                                      home_vel_c, zero_offset_c)

        return True

    def get_pos(self):
        '''
        Obtain the current absolute position of the stage
        '''
        if self.verbose:
            print('getPos probing...')
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')

        position = c_float()
        self.aptdll.MOT_GetPosition(self.SerialNum, pointer(position))
        if self.verbose:
            print('getPos ', position.value)
        return position.value

    def move_rel(self, relDistance):
        '''
        Moves the motor a relative distance specified
        @param relDistance    float     Relative position desired, in mm
        '''
        if self.verbose:
            print('move_rel ', relDistance, c_float(relDistance))
        if not self.Connected:
            # TODO: This should use our error message system
            print('Please connect first! Use initializeHardwareDevice')
        relativeDistance = c_float(relDistance)
        self.aptdll.MOT_MoveRelativeEx(self.SerialNum, relativeDistance, self._wait_until_done)
        if self.verbose:
            print('move_rel SUCESS')
        return True

    def move_abs(self, absPosition):
        '''
        Moves the motor to the Absolute position specified
        absPosition    float     Position desired, in mm
        '''
        if self.verbose:
            print('move_abs ', absPosition, c_float(absPosition))
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        absolutePosition = c_float(absPosition)
        self.aptdll.MOT_MoveAbsoluteEx(self.SerialNum, absolutePosition, self._wait_until_done)
        if self.verbose:
            print('move_abs SUCESS')
        return True

    def mcRel(self, relDistance, moveVel=0.5):
        '''
        Moves the motor a relative distance specified at a controlled velocity
        relDistance    float     Relative position desired
        moveVel        float     Motor velocity, mm/sec
        '''
        if self.verbose:
            print('mcRel ', relDistance, c_float(relDistance), 'mVel', moveVel)
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        # Save velocities to reset after move
        maxVel = self.get_velocity()
        # Set new desired max velocity
        self.set_velocity(moveVel)
        self.move_rel(relDistance)
        self.set_velocity(maxVel)
        if self.verbose:
            print('mcRel SUCESS')
        return True

    def mcAbs(self, absPosition, moveVel=0.5):
        '''
        Moves the motor to the Absolute position specified at a controlled velocity
        absPosition    float     Position desired
        moveVel        float     Motor velocity, mm/sec
        '''
        if self.verbose:
            print('mcAbs ', absPosition, c_float(absPosition), 'mVel', moveVel)
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        # Save velocities to reset after move
        minVel, acc, maxVel = self.getVelocityParameters()
        # Set new desired max velocity
        self.set_velocity(moveVel)
        self.move_rel(absPosition)
        self.set_velocity(maxVel)
        if self.verbose:
            print('mcAbs SUCESS')
        return True

    def move_bc_rel(self, relDistance):
        '''
        Moves the motor a relative distance specified, correcting for backlash
        @param relDistance    float     Relative position desired
        '''
        if self.verbose:
            print('mbRel ', relDistance, c_float(relDistance))
        if not self.Connected:
            # TODO: This should use our error message system
            print('Please connect first! Use initializeHardwareDevice')
        self.move_rel(relDistance - self.blCorr)
        self.move_rel(self.blCorr)
        if self.verbose:
            print('mbRel SUCESS')
        return True

    def mbAbs(self, absPosition):
        '''
        Moves the motor to the Absolute position specified
        @param absPosition    float     Position desired
        '''
        if self.verbose:
            print('mbAbs ', absPosition, c_float(absPosition))
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        if (absPosition < self.getPos()):
            if self.verbose:
                print('backlash move_rel', absPosition - self.blCorr)
            self.move_rel(absPosition - self.blCorr)
        self.move_rel(absPosition)
        if self.verbose:
            print('mbAbs SUCESS')
        return True

    # --------------------------- Miscelaneous ---------------------------------

    def get_status(self):
        """ Get the status bits of the current axis. """

        status_bits = c_long()
        self.aptdll.MOT_GetStatusBits(self.SerialNum, pointer(status_bits))

        return status_bits.value

    def identify(self):
        '''
        Causes the motor to blink the Active LED
        '''
        self.aptdll.MOT_Identify(self.SerialNum)
        return True

    def cleanUpAPT(self):
        """ Releases the APT object. Use when exiting the program.
        """
        self.aptdll.APTCleanUp()
        if self.verbose:
            print('APT cleaned up')
        self.Connected = False

    def abort(self):
        """ Abort the movement. """
        self.aptdll.MOT_StopProfiled(self.SerialNum)

    def go_home(self):

        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')

        #TODO: a proper home position has to be set, not just zero.
        self.move_abs(0.0)

# ==============================================================================

class APTStage(Base, MotorInterface):
    """ Control class for an arbitrary collection of axis. Do not use this
        Class directly but inherit this class to a new Class, where also the
        method get_constraints() is specified for that specific set of a
        hardware.
        If it is really necessary to change an already existing interface
        module, then overwrite it in the class, which inherited that class.
     """

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)

    def activation(self, e):
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
            path_dll = os.path.join(self.get_main_dir(),  'thirdparty',
                                                          'thorlabs',
                                                          'win64',
                                                          'APT.dll')
        elif platform.architecture()[0] == '32bit':
            path_dll = os.path.join(self.get_main_dir(),  'thirdparty',
                                                          'thorlabs',
                                                          'win64',
                                                          'APT.dll')
        else:
            self.logMsg('Unknown platform, cannot load the Thorlabs dll.',
                        msgType='error')

        # Read HW from config
        config = self.getConfiguration()

        if 'motor_type_serial_label' in config.keys():
            self._motor_type_serial_label = config['motor_type_serial_label']
        else:
            self.logMsg('Motor Hardware-controller-type, serial-number and '
                        'label for x axis not found in the configuration.\n'
                        'This numbers are essential, without them no proper '
                        'communication can be established!\n'
                        'The Hardware-controller-type depends on the used '
                        'microcontroller, Serial number can be found at the '
                        'back of the Step Motor controller and a label for '
                        'each axis has to be chosen like:\n'
                        '[("<hw_type>", <serial_num>, "<axis_label>"), '
                        '("<hw_type>", <serial_num>, "<axis_label>"), ...]\n'
                        'and assigned to the attribute '
                        'motor_serial_number_label.', msgType='error')

        self._axis_dict = OrderedDict()

        limits_dict = self.get_constraints()


        # the variable self._motor_type_serial_label is a list, which contains
        # the information about each axis. Three information about each axis
        # have to be present:
        #   1. hw_type: hardware type of the controller, it must be one entry
        #      from the dict hwtype_dict of the generic class APTMotor
        #   2. serial_num: the serial number assiged to that axis
        #   3. label: the label you give that axis. Note that this lable should
        #      coincide with the label defined in the get_constraints methods.
        #
        # Therefore self._motor_type_serial_label is looking like:
        #   [(hw_type, serial_num, label), (hw_type, serial_num, label), ...]

        for (hw_type, serialnummer, label) in self._motor_type_serial_label:
            if limits_dict.get(label) is not None:
                self._axis_dict[label] = APTMotor(path_dll, serialnummer,
                                                  hw_type, label)
                self._axis_dict[label].initializeHardwareDevice()

            else:
                self.logMsg('The following label "{0}" cannot be found in the '
                            'constraints method!\nCheck whether label coincide '
                            'with the label given in the config!\n'
                            'Restart the program!', msgType='error')

        self.custom_activation(e)


    def custom_activation(self, e):
        """ That activation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def deactivation(self, e):
        """ Disconnect from hardware and clean up.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """

        for label_axis in self._axis_dict:
            self._axis_dict[label_axis].cleanUpAPT()

        self.custom_deactivation(e)


    def custom_deactivation(self, e):
        """ That deactivation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def move_rel(self,  param_dict):
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

        A smart idea would be to ask the position after the movement.
        """
        curr_pos_dict = self.get_pos()
        constraints = self.get_constraints()

        for label_axis in self._axis_dict:

            if param_dict.get(label_axis) is not None:
                move = param_dict[label_axis]
                curr_pos = curr_pos_dict[label_axis]

                if  (curr_pos + move > constraints[label_axis]['pos_max'] ) or\
                    (curr_pos + move < constraints[label_axis]['pos_min']):

                    self.logMsg('Cannot make further relative movement of the '
                                'axis "{0}" since the motor is at position '
                                '{1} and with the step of {2} it would exceed '
                                'the allowed border [{3},{4}]! Movement is '
                                'ignored!'.format(
                                        label_axis,
                                        move,
                                        curr_pos,
                                        constraints[label_axis]['pos_min'],
                                        constraints[label_axis]['pos_max']),
                                msgType='warning')
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


                if  (desired_pos > constraints[label_axis]['pos_max'] ) or\
                    (desired_pos < constraints[label_axis]['pos_min']):

                    self.logMsg('Cannot make absolute movement of the axis'
                                '"{0}" to position {1}, since it exceeds the '
                                'limts [{2},{3}]. Movement is '
                                'ignored!'.format(
                                        label_axis,
                                        desired_pos,
                                        constraints[label_axis]['pos_min'],
                                        constraints[label_axis]['pos_max']),
                                msgType='warning')
                else:
                    self._save_pos({label_axis:desired_pos})
                    self._axis_dict[label_axis].move_abs(desired_pos)


    def abort(self):
        """ Stops movement of the stage. """

        for label_axis in self._axis_dict:
            self._axis_dict[label_axis].abort()

        self.logMsg('Movement of all the axis aborted! Stage stopped.',
                    msgType='warning')

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

        @return dict: with the axis label as key and the status number as item.
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

        #TODO: read out a saved home position in file and compare that with the
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
                filename =  os.path.join(self._magnet_dump_folder,
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
            self.logMsg('Magnet dump was created in:\n'
                        '{}'.format(magnet_path), msgType='status',
                        importance=1)
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

                if  (desired_vel > constraints[label_axis]['vel_max'] ) or\
                    (desired_vel < constraints[label_axis]['vel_min']):

                    self.logMsg('Cannot set velocity of the axis "{0}" to the'
                                'desired velocity of "{1}", since it exceeds '
                                'the limts [{2},{3}] ! Command is '
                                'ignored!'.format(
                                        label_axis,
                                        desired_vel,
                                        constraints[label_axis]['vel_min'],
                                        constraints[label_axis]['vel_max']),
                                msgType='warning')
            else:
                self._axis_dict[label_axis].set_velocity(desired_vel)



class APTOneAxisStage(APTStage):

    _modclass = 'APTOneAxis'
    _modtype = 'hardware'

    # connectors
    _out = {'aptmotor': 'MotorInterface'}


    def __init__(self, manager, name, config, **kwargs):
        # pass the init to the inherited class APTStage and run its init:
        super().__init__(manager, name, config, **kwargs)

        for label_axis in self._axis_dict:
            self._axis_dict[label_axis].blCorr = 0.10    # set the backlach
                                                    # correction since the
                                                    # forward movement is
                                                    # preciser than backwards

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


        # my specific settings for the stage:
        limits_dict = self.get_constraints()

        for label_axis in self._axis_dict:

            # adapt the hardware controller to the proper unit set:
            if limits_dict[label_axis]['unit'] == '°' or limits_dict[label_axis]['unit'] == 'degree':
                unit = 2    # for rotation movement
            else:
                unit = 1    # default value for linear movement

            self._axis_dict[label_axis].set_stage_axis_info(
                                                limits_dict[label_axis]['pos_min'],
                                                limits_dict[label_axis]['pos_max'],
                                                pitch=1,
                                                unit=unit)
            self._axis_dict[label_axis].setVelocityParameters(
                                                limits_dict[label_axis]['vel_min'],
                                                limits_dict[label_axis]['acc_max'],
                                                limits_dict[label_axis]['vel_max'])
            self._axis_dict[label_axis].set_velocity(limits_dict[label_axis]['vel_max'])
            self._axis_dict[label_axis].setHardwareLimitSwitches(2,2)
            self._axis_dict[label_axis]._wait_until_done = False

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

        # set the constraints for the x axis:
        axis0 = {}
        axis0['name']     = 'x'     # That name must coincide with the given
                                    # name in the config. Otherwise there is no
                                    # way of identifying the used axes.
        axis0['unit']     = 'mm'    # the SI units, only possible mm or degree
        axis0['ramp']     = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min']  = 0       # in mm
        axis0['pos_max']  = 100     # that is basically the traveling range
        axis0['pos_step'] = 0.001   # in mm (a rather arbitrary number)
        axis0['vel_min']  = 0.0     # in mm/s
        axis0['vel_max']  = 4.0     # in mm/s
        axis0['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis0['acc_min']  = 0.01    # in mm/s^2
        axis0['acc_max']  = 0.5     # in mm/s^2
        axis0['acc_step'] = 0.0001  # in mm/s^2 (a rather arbitrary number)

        constraints[axis0['label']] = axis0

        return constraints


class APTThreeAxisStage(APTStage):
    """ The module controlles three StepperStage56=NRT150 Enc Stage 150mm
    """

    _modclass = 'APTThreeAxis'
    _modtype = 'hardware'

    # connectors
    _out = {'aptmotor': 'MotorInterface'}


    def __init__(self, manager, name, config, **kwargs):
        # pass the init to the inherited class APTStage and run its init:
        super().__init__(manager, name, config, **kwargs)

    def custom_activation(self, e):
        """ That activation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation of the
                         parent class APTStage.

        """

        # my specific settings for the stage:
        limits_dict = self.get_constraints()

        for label_axis in self._axis_dict:
            self._axis_dict[label_axis].set_stage_axis_info(
                                                limits_dict[label_axis]['pos_min'],
                                                limits_dict[label_axis]['pos_max'],
                                                pitch=1)
            self._axis_dict[label_axis].setVelocityParameters(
                                                limits_dict[label_axis]['vel_min'],
                                                limits_dict[label_axis]['acc_max'],
                                                limits_dict[label_axis]['vel_max'])
            self._axis_dict[label_axis].set_velocity(limits_dict[label_axis]['vel_max'])
            self._axis_dict[label_axis].setHardwareLimitSwitches(2,2)
            self._axis_dict[label_axis]._wait_until_done = False
            self._axis_dict[label_axis].blCorr = 0.10    # set the backlach
                                                    # correction since the
                                                    # forward movement is
                                                    # preciser than the backward

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
        constraints = OrderedDict()

        # set the constraints for the x axis:
        axis0 = {}
        axis0['label']    = 'x'     # That name must coincide with the given
                                    # name in the config. Otherwise there is no
                                    # way of identifying the used axes.
        axis0['unit']     = 'mm'    # the SI units, only possible mm or degree
        axis0['ramp']     = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min']  = -65     # in mm
        axis0['pos_max']  = 65      # that is basically the traveling range
        axis0['pos_step'] = 0.001   # in mm (a rather arbitrary number)
        axis0['vel_min']  = 0.1     # in mm/s
        axis0['vel_max']  = 2.0     # in mm/s
        axis0['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis0['acc_min']  = 0.01    # in mm/s^2
        axis0['acc_max']  = 0.5     # in mm/s^2
        axis0['acc_step'] = 0.0001  # in mm/s^2 (a rather arbitrary number)

        # set the constraints for the y axis:
        axis1 = {}
        axis1['label']    = 'y'     # That name must coincide with the given
                                    # name in the config. Otherwise there is no
                                    # way of identifying the used axes.
        axis0['unit']     = 'mm'    # the SI units, only possible mm or degree
        axis1['ramp']     = ['Sinus','Linear'] # a possible list of ramps
        axis1['pos_min']  = -65     # in mm
        axis1['pos_max']  = 65      # that is basically the traveling range
        axis1['pos_step'] = 0.001   # in mm
        axis1['vel_min']  = 0.1     # in mm/s
        axis1['vel_max']  = 2.0     # in mm/s
        axis1['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis1['acc_min']  = 0.01    # in mm/s^2
        axis1['acc_max']  = 0.5     # in mm/s^2
        axis1['acc_step'] = 0.001   # in mm/s^2 (a rather arbitrary number)

        # set the constraints for the z axis:
        axis2 = {}
        axis2['label'] = 'z'        # name is just as a sanity included
        axis2['unit'] = 'mm'        # the SI units
        axis2['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis2['pos_min'] = -65      # in mm
        axis2['pos_max'] = 65       # that is basically the traveling range
        axis2['pos_step'] = 0.001   # in mm
        axis2['vel_min'] = 0.1      # in mm/s
        axis2['vel_max'] = 2.0      # in mm/s
        axis2['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis2['acc_min'] = 0.01     # in mm/s^2
        axis2['acc_max'] = 0.5      # in mm/s^2
        axis2['acc_step'] = 0.001   # in mm/s^2 (a rather arbitrary number)

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2


        return constraints


class APTFourAxisStage(APTStage):
    """ The module controls three StepperStage56=NRT150 Enc Stage 150mm
    together with CR1-Z7 rotation stage.
    """

    _modclass = 'APTThreeAxis'
    _modtype = 'hardware'

    # connectors
    _out = {'aptmotor': 'MotorInterface'}


    def __init__(self, manager, name, config, **kwargs):
        # pass the init to the inherited class APTStage and run its init:
        super().__init__(manager, name, config, **kwargs)

    def custom_activation(self, e):
        """ That activation method can be overwritten in the sub-classed file.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation of the
                         parent class APTStage.

        """

        # my specific settings for the stage:
        limits_dict = self.get_constraints()

        for label_axis in self._axis_dict:

            # adapt the hardware controller to the proper unit set:
            if (limits_dict[label_axis]['unit'] == '°') or (limits_dict[label_axis]['unit'] == 'degree'):
                unit = 2    # for rotation movement
                pitch = 7.5
                blCorr = 0.2
            else:
                unit = 1    # default value for linear movement
                pitch = 1
                blCorr = 0.10
            self._axis_dict[label_axis].set_stage_axis_info(
                                                limits_dict[label_axis]['pos_min'],
                                                limits_dict[label_axis]['pos_max'],
                                                pitch=pitch,
                                                unit=unit)
            self._axis_dict[label_axis].setVelocityParameters(
                                                limits_dict[label_axis]['vel_min'],
                                                limits_dict[label_axis]['acc_max'],
                                                limits_dict[label_axis]['vel_max'])
            self._axis_dict[label_axis].set_velocity(limits_dict[label_axis]['vel_max'])
            self._axis_dict[label_axis].setHardwareLimitSwitches(2,2)
            self._axis_dict[label_axis]._wait_until_done = False
            self._axis_dict[label_axis].blCorr = 0.10    # set the backlach
                                                    # correction since the
                                                    # forward movement is
                                                    # preciser than the backward

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
        constraints = OrderedDict()

        # set the constraints for the x axis:
        axis0 = {}
        axis0['label']    = 'x'     # That name must coincide with the given
                                    # name in the config. Otherwise there is no
                                    # way of identifying the used axes.
        axis0['unit']     = 'mm'    # the SI units, only possible mm or degree
        axis0['ramp']     = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min']  = -65     # in mm
        axis0['pos_max']  = 65      # that is basically the traveling range
        axis0['pos_step'] = 0.001   # in mm (a rather arbitrary number)
        axis0['vel_min']  = 0.1     # in mm/s
        axis0['vel_max']  = 2.0     # in mm/s
        axis0['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis0['acc_min']  = 0.01    # in mm/s^2
        axis0['acc_max']  = 0.5     # in mm/s^2
        axis0['acc_step'] = 0.0001  # in mm/s^2 (a rather arbitrary number)

        # set the constraints for the y axis:
        axis1 = {}
        axis1['label']    = 'y'     # That name must coincide with the given
                                    # name in the config. Otherwise there is no
                                    # way of identifying the used axes.
        axis1['unit']     = 'mm'    # the SI units, only possible mm or degree
        axis1['ramp']     = ['Sinus','Linear'] # a possible list of ramps
        axis1['pos_min']  = -65     # in mm
        axis1['pos_max']  = 65      # that is basically the traveling range
        axis1['pos_step'] = 0.001   # in mm
        axis1['vel_min']  = 0.1     # in mm/s
        axis1['vel_max']  = 2.0     # in mm/s
        axis1['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis1['acc_min']  = 0.01    # in mm/s^2
        axis1['acc_max']  = 0.5     # in mm/s^2
        axis1['acc_step'] = 0.001   # in mm/s^2 (a rather arbitrary number)

        # set the constraints for the z axis:
        axis2 = {}
        axis2['label'] = 'z'        # name is just as a sanity included
        axis2['unit'] = 'mm'        # the SI units
        axis2['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis2['pos_min'] = -65      # in mm
        axis2['pos_max'] = 65       # that is basically the traveling range
        axis2['pos_step'] = 0.001   # in mm
        axis2['vel_min'] = 0.1      # in mm/s
        axis2['vel_max'] = 2.0      # in mm/s
        axis2['vel_step'] = 0.001   # in mm/s (a rather arbitrary number)
        axis2['acc_min'] = 0.01     # in mm/s^2
        axis2['acc_max'] = 0.5      # in mm/s^2
        axis2['acc_step'] = 0.001   # in mm/s^2 (a rather arbitrary number)

        axis3 = {}
        axis3['label'] = 'phi'        # name is just as a sanity included
        axis3['unit'] = '°'        # the SI units
        axis3['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis3['pos_min'] = 0     # in mm
        axis3['pos_max'] = 360       # that is basically the traveling range
        axis3['pos_step'] = 0.01   # in mm
        axis3['vel_min'] = 4.0      # in mm/s
        axis3['vel_max'] = 6.0      # in mm/s
        axis3['vel_step'] = 0.1   # in mm/s (a rather arbitrary number)
        axis3['acc_min'] = 4.0     # in mm/s^2
        axis3['acc_max'] = 5.0      # in mm/s^2
        axis3['acc_step'] = 0.01   # in mm/s^2 (a rather arbitrary number)

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        constraints[axis3['label']] = axis3

        return constraints