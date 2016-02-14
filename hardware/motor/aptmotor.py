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
"""

"""
This module was developed from PyAPT, written originally by Michael Leung
(mcleung@stanford.edu). Have a look in:
    https://github.com/HaeffnerLab/Haeffner-Lab-LabRAD-Tools/blob/master/cdllservers/APTMotor/APTMotorServer.py
APT.dll and APT.lib were provided to PyAPT thanks to SeanTanner@ThorLabs .
"""

from core.base import Base
from ctypes import c_long, c_buffer, c_float, windll, pointer
from interface.motor_interface import MotorInterface
import os
import platform


class APTMotor():
    """Class to control Thorlabs APT motor. """

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
        @param int unit: unit of the axis, possible values:
                            1 = mm
                            2 = degree
        @param float pitch: the pitch determines the full step angle of a
                            stepper magnet motor. That is the resolution of the
                            stepper motor.
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

    def setHardwareLimitSwitches(self, switchr, switchf):
        reverseLimitSwitch = c_long(switchr)
        forwardLimitSwitch = c_long(switchf)
        self.aptdll.MOT_SetHWLimSwitches(self.SerialNum, reverseLimitSwitch, forwardLimitSwitch)
        hardwareLimitSwitches = [reverseLimitSwitch.value, forwardLimitSwitch.value]
        return hardwareLimitSwitches


    def getVelocityParameters(self):
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
        self.aptdll.MOT_MoveRelativeEx(self.SerialNum, relativeDistance, True)
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
        self.aptdll.MOT_MoveAbsoluteEx(self.SerialNum, absolutePosition, True)
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



class APTOneAxisStage(Base, MotorInterface):
    """ Control a one axis stage """

    _modclass = 'APTOneAxisStage'
    _modtype = 'hardware'

    # connectors
    _out = {'aptmotor': 'MotorInterface'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)

    def activation(self, e):
        """ Initialize instance variables and connect to hardware as configured.
        """

        self.blCorr = 0.10  # 100um backlash correction


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

        if 'motor_hw_type' in config.keys():

            self._HWType = config['motor_hw_type']
        else:
            self.logMsg('Motor HW Type not found in the configuration, '
                        'searching for motors will not work', msgType='error')

        if 'motor_serial_number' in config.keys():
            self._serialnum_axis, label_axis = config['motor_serial_number']
        else:
            self.logMsg('Motor serial number not found in the configuration.\n'
                        'This number is essential, without it no proper '
                        'communication can be established!\n'
                        'The Serial number can be found at the back of the '
                        'Step Motor controller.', msgType='error')

        self._axis = APTMotor(path_dll, self._serialnum_axis, self._HWType,label_axis)
        self._axis.initializeHardwareDevice()


    def deactivation(self, e):
        """ Disconnect from hardware and clean up """
        self._axis.cleanUpAPT()

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
        constraints = {}

        # get the constraints for the x axis:
        label_axis = self._axis.label
        axis0 = {}
        axis0['name'] = label_axis          # name is just as a sanity included
        axis0['unit'] = 'm'                 # the SI units
        axis0['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min'] = 0
        axis0['pos_max'] = 100            # that is basically the traveling range
        axis0['pos_step'] = 100
        axis0['vel_min'] = 0
        axis0['vel_max'] = 100
        axis0['vel_step'] = 0.01

        constraints[axis0['label']] = axis0

        return constraints

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

        if param_dict.get(self._axis.label) is not None:
            move = param_dict[self._axis.label]
            curr_pos = curr_pos_dict[self._axis.label]

            if  (curr_pos + move > constraints[self._axis.label]['pos_max'] ) or\
                (curr_pos + move < constraints[self._axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._axis.label, move,
                                    constraints[self._axis.label]['pos_min'],
                                    constraints[self._axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._axis.move_rel(move)

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

        if param_dict.get(self._axis.label) is not None:
            desired_pos = param_dict[self._axis.label]

            if  (desired_pos > constraints[self._axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._axis.label, desired_pos,
                                    constraints[self._axis.label]['pos_min'],
                                    constraints[self._axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._axis.move_abs(desired_pos)

    def abort(self):
        """ Stops movement of the stage. """

        self._axis.abort()

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
            if self._axis.label in param_list:
                pos[self._axis.label] = self._axis.get_pos()

        else:
            pos[self._axis.label] = self._axis.get_pos()


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
            if self._axis.label in param_list:
                status[self._axis.label] = self._axis.get_status()

        else:
            status[self._axis.label] = self._axis.get_status()

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
            if self._axis.label in param_list:
                self._axis.go_home()
        else:
            self._axis.go_home()

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
            if self._axis.label in param_list:
                vel[self._axis.label] = self._axis.get_velocity()

        else:
            vel[self._axis.label] = self._axis.get_velocity()

        return vel

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """

        if param_dict.get(self._axis.label) is not None:
            desired_vel = param_dict[self._axis.label]

            self._axis.set_velocity(desired_vel)


# ==============================================================================

class APTThreeAxisStage(Base, MotorInterface):
    """ Control a three axis stage. Since the three axis stage can have only
        one hardware controller type, we choose in the implementation of the
        different axis directly the axis name like _x_axis, _y_axis, _z_axis.
        In all other cases, where a possibility occurs that these three axis
        might be assigned differently, one has to stick to neutral name like
        axis0, axis1, axis2, because then all the axis can have arbitrary
        directions of movement. In that special file there can only exist one
        possible movement. """

    _modclass = 'APTOneAxisStage'
    _modtype = 'hardware'

    # connectors
    _out = {'aptmotor': 'MotorInterface'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)

    def activation(self, e):
        """ Initialize instance variables and connect to hardware as configured.
        """

        self.blCorr = 0.10  # 100um backlash correction

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

        # actually there is only one supported hardware type. Just check it
        # whether it coincide:


        if 'motor_hw_type' in config.keys():
            self._HWType = config['motor_hw_type']
#
#            if HWType == 'HWTYPE_BBD10X':
#                self._HWType = hwtype_dict['HWTYPE_BBD10X']
#            else:
#                self.logMsg('Motor HW Type cannot be used for that model!\n'
#                            'Only the HW model "HWTYPE_BBD10X" is possible, '
#                            'use that!', msgType='error')

        else:
            self.logMsg('Motor HW Type not found in the configuration, '
                        'searching for motors will not work', msgType='error')

        if 'motor_serial_number_x_axis' in config.keys():
            self._serialnum_x_axis, label_x = config['motor_serial_number_x_axis']
        else:
            self.logMsg('Motor serial number and label for x axis not found '
                        'in the configuration.\n'
                        'This number is essential, without it no proper '
                        'communication can be established!\n'
                        'The Serial number can be found at the back of the '
                        'Step Motor controller.', msgType='error')

        if 'motor_serial_number_y_axis' in config.keys():
            self._serialnum_y_axis, label_y = config['motor_serial_number_y_axis']
        else:
            self.logMsg('Motor serial number and label for y axis not found '
                        'in the configuration.\n'
                        'This number is essential, without it no proper '
                        'communication can be established!\n'
                        'The Serial number can be found at the back of the '
                        'Step Motor controller.', msgType='error')

        if 'motor_serial_number_z_axis' in config.keys():
            self._serialnum_z_axis, label_z = config['motor_serial_number_z_axis']
        else:
            self.logMsg('Motor serial number and label for z axis not found '
                        'in the configuration.\n'
                        'This number is essential, without it no proper '
                        'communication can be established!\n'
                        'The Serial number can be found at the back of the '
                        'Step Motor controller.', msgType='error')

        self._x_axis = APTMotor(path_dll, self._serialnum_x_axis, self._HWType,label_x)
        self._x_axis.initializeHardwareDevice()
        self._y_axis = APTMotor(path_dll, self._serialnum_y_axis, self._HWType,label_y)
        self._y_axis.initializeHardwareDevice()
        self._z_axis = APTMotor(path_dll, self._serialnum_z_axis, self._HWType,label_z)
        self._z_axis.initializeHardwareDevice()

    def deactivation(self, e):
        """ Disconnect from hardware and clean up """
        self._x_axis.cleanUpAPT()
        self._y_axis.cleanUpAPT()
        self._z_axis.cleanUpAPT()

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
        constraints = {}

        # get the constraints for the x axis:
        label_x = self._x_axis.label
        axis0 = {}
        axis0['label'] = label_x        # name is just as a sanity included
        axis0['unit'] = 'm'        # the SI units
        axis0['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min'] = 0
        axis0['pos_max'] = 100  # that is basically the traveling range
        axis0['pos_step'] = 100
        axis0['vel_min'] = 0
        axis0['vel_max'] = 100
        axis0['vel_step'] = 0.01

        # get the constraints for the x axis:
        label_y = self._y_axis.label
        axis1 = {}
        axis1['label'] = label_y        # name is just as a sanity included
        axis1['unit'] = 'm'        # the SI units
        axis1['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis1['pos_min'] = 0
        axis1['pos_max'] = 100  # that is basically the traveling range
        axis1['pos_step'] = 100
        axis1['vel_min'] = 0
        axis1['vel_max'] = 100
        axis1['vel_step'] = 0.01

        # get the constraints for the x axis:
        label_z = self._z_axis.label
        axis2 = {}
        axis2['label'] = label_z        # name is just as a sanity included
        axis2['unit'] = 'm'        # the SI units
        axis2['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis2['pos_min'] = 0
        axis2['pos_max'] = 1000  # that is basically the traveling range
        axis2['pos_step'] = 1      # right now unit is millimeter.
        axis2['vel_min'] = 0
        axis2['vel_max'] = 100
        axis2['vel_step'] = 0.01

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2

        return constraints

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

        if param_dict.get(self._x_axis.label) is not None:
            move_x = param_dict[self._x_axis.label]
            curr_pos_x = curr_pos_dict[self._x_axis.label]

            if  (curr_pos_x + move_x > constraints[self._x_axis.label]['pos_max'] ) or\
                (curr_pos_x + move_x < constraints[self._x_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._x_axis.label, move_x,
                                    constraints[self._x_axis.label]['pos_min'],
                                    constraints[self._x_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._save_pos({self._x_axis.label: curr_pos_x + move_x})
                self._x_axis.move_rel(move_x)

        if param_dict.get(self._y_axis.label) is not None:
            move_y = param_dict[self._y_axis.label]
            curr_pos_y = curr_pos_dict[self._y_axis.label]

            if  (curr_pos_y + move_y > constraints[self._y_axis.label]['pos_max'] ) or\
                (curr_pos_y + move_y < constraints[self._y_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._y_axis.label, move_y,
                                    constraints[self._y_axis.label]['pos_min'],
                                    constraints[self._y_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._save_pos({self._y_axis.label: curr_pos_y + move_y})
                self._y_axis.move_rel(move_y)

        if param_dict.get(self._z_axis.label) is not None:
            move_z = param_dict[self._z_axis.label]
            curr_pos_z = curr_pos_dict[self._z_axis.label]

            if  (curr_pos_z + move_z > constraints[self._z_axis.label]['pos_max'] ) or\
                (curr_pos_z + move_z < constraints[self._z_axis.label]['pos_min']):

                self.logMsg('Cannot make further movement of the axis "{0}"'
                            'with the step {1}, since the border [{2},{3}] '
                            'was reached! Ignore '
                            'command!'.format(self._z_axis.label, move_z,
                                    constraints[self._z_axis.label]['pos_min'],
                                    constraints[self._z_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._save_pos({self._z_axis.label: curr_pos_z + move_z})
                self._z_axis.move_rel(move_z)

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

        if param_dict.get(self._x_axis.label) is not None:
            desired_pos = param_dict[self._x_axis.label]


            if  (desired_pos > constraints[self._x_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._x_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._x_axis.label, desired_pos,
                                    constraints[self._x_axis.label]['pos_min'],
                                    constraints[self._x_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._save_pos({self._x_axis.label:desired_pos})
                self._x_axis.move_abs(desired_pos)

        if param_dict.get(self._y_axis.label) is not None:
            desired_pos = param_dict[self._y_axis.label]


            if  (desired_pos > constraints[self._y_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._y_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._y_axis.label, desired_pos,
                                    constraints[self._y_axis.label]['pos_min'],
                                    constraints[self._y_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._save_pos({self._y_axis.label:desired_pos})
                self._y_axis.move_abs(desired_pos)

        if param_dict.get(self._z_axis.label) is not None:
            desired_pos = param_dict[self._z_axis.label]

            if  (desired_pos > constraints[self._z_axis.label]['pos_max'] ) or\
                (desired_pos < constraints[self._z_axis.label]['pos_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._z_axis.label, desired_pos,
                                    constraints[self._z_axis.label]['pos_min'],
                                    constraints[self._z_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._save_pos({self._z_axis.label:desired_pos})
                self._z_axis.move_abs(desired_pos)


    def abort(self):
        """ Stops movement of the stage. """

        self._x_axis.abort()
        self._y_axis.abort()
        self._z_axis.abort()


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
            if self._x_axis.label in param_list:
                pos[self._x_axis.label] = self._x_axis.get_pos()

            if self._y_axis.label in param_list:
                pos[self._y_axis.label] = self._y_axis.get_pos()

            if self._z_axis.label in param_list:
                pos[self._z_axis.label] = self._z_axis.get_pos()

        else:
            pos[self._x_axis.label] = self._x_axis.get_pos()
            pos[self._y_axis.label] = self._y_axis.get_pos()
            pos[self._z_axis.label] = self._z_axis.get_pos()

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
            if self._x_axis.label in param_list:
                status[self._x_axis.label] = self._x_axis.get_status()

            if self._y_axis.label in param_list:
                status[self._y_axis.label] = self._y_axis.get_status()

            if self._z_axis.label in param_list:
                status[self._z_axis.label] = self._z_axis.get_status()

        else:
            status[self._x_axis.label] = self._x_axis.get_status()
            status[self._y_axis.label] = self._y_axis.get_status()
            status[self._z_axis.label] = self._z_axis.get_status()

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
            if self._x_axis.label in param_list:
                self._x_axis.go_home()
            if self._y_axis.label in param_list:
                self._y_axis.go_home()
            if self._z_axis.label in param_list:
                self._z_axis.go_home()
        else:
            self._x_axis.go_home()
            self._y_axis.go_home()
            self._z_axis.go_home()


    def _save_pos(self, param_dict):
        """ Save after each move the parameters to file, since the motor stage
        looses any information if it is initialized. That might be a way to
        store and retrieve the current position.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed.
        """

        if param_dict.get(self._x_axis.label) is not None:
            pos_x = param_dict[self._x_axis.label]
            filename =  os.path.join(self._magnet_dump_folder, self._x_axis.label + '.dat')
            with open(filename, 'w') as f:
                f.write(str(pos_x))

        if param_dict.get(self._y_axis.label) is not None:
            pos_y = param_dict[self._y_axis.label]
            filename =  os.path.join(self._magnet_dump_folder, self._y_axis.label + '.dat')
            with open(filename, 'w') as f:
                f.write(str(pos_y))

        if param_dict.get(self._z_axis.label) is not None:
            pos_z = param_dict[self._z_axis.label]
            filename =  os.path.join(self._magnet_dump_folder, self._z_axis.label + '.dat')
            with open(filename, 'w') as f:
                f.write(str(pos_z))


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
            if self._x_axis.label in param_list:
                vel[self._x_axis.label] = self._x_axis.get_velocity()
            if self._y_axis.label in param_list:
                vel[self._x_axis.label] = self._y_axis.get_velocity()
            if self._z_axis.label in param_list:
                vel[self._x_axis.label] = self._z_axis.get_velocity()

        else:
            vel[self._x_axis.label] = self._x_axis.get_velocity()
            vel[self._y_axis.label] = self._y_axis.get_velocity()
            vel[self._z_axis.label] = self._z_axis.get_velocity()

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

        if param_dict.get(self._x_axis.label) is not None:
            desired_vel = param_dict[self._x_axis.label]

            if  (desired_vel > constraints[self._x_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._x_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._x_axis.label, desired_vel,
                                    constraints[self._x_axis.label]['vel_min'],
                                    constraints[self._x_axis.label]['vel_max']),
                            msgType='warning')
            else:
                self._x_axis.set_velocity(desired_vel)

        if param_dict.get(self._y_axis.label) is not None:
            desired_vel = param_dict[self._y_axis.label]

            if  (desired_vel > constraints[self._y_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._y_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._y_axis.label, desired_vel,
                                    constraints[self._y_axis.label]['vel_min'],
                                    constraints[self._y_axis.label]['vel_max']),
                            msgType='warning')
            else:
                self._y_axis.set_velocity(desired_vel)

        if param_dict.get(self._z_axis.label) is not None:
            desired_vel = param_dict[self._z_axis.label]

            if  (desired_vel > constraints[self._z_axis.label]['vel_max'] ) or\
                (desired_vel < constraints[self._z_axis.label]['vel_min']):

                self.logMsg('Cannot make absolute movement of the axis "{0}"'
                            'to possition {1}, since it exceeds the limts '
                            '[{2},{3}] ! Command is '
                            'ignored!'.format(self._z_axis.label, desired_vel,
                                    constraints[self._z_axis.label]['pos_min'],
                                    constraints[self._z_axis.label]['pos_max']),
                            msgType='warning')
            else:
                self._z_axis.set_velocity(desired_vel)



