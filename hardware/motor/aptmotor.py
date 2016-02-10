# -*- coding: utf-8 -*-
"""
APT Motor Controller for Thorlabs

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


class APTMotor(Base, MotorInterface):

    """Class to control Thorlabs APT motor.

        Available HW Types are:
        HWTYPE_BSC001		11	// 1 Ch benchtop stepper driver
        HWTYPE_BSC101		12	// 1 Ch benchtop stepper driver
        HWTYPE_BSC002		13	// 2 Ch benchtop stepper driver
        HWTYPE_BDC101		14	// 1 Ch benchtop DC servo driver
        HWTYPE_SCC001		21	// 1 Ch stepper driver card (used within BSC102,103 units)
        HWTYPE_DCC001		22	// 1 Ch DC servo driver card (used within BDC102,103 units)
        HWTYPE_ODC001		24	// 1 Ch DC servo driver cube
        HWTYPE_OST001		25	// 1 Ch stepper driver cube
        HWTYPE_MST601		26	// 2 Ch modular stepper driver module
        HWTYPE_TST001		29	// 1 Ch Stepper driver T-Cube
        HWTYPE_TDC001		31	// 1 Ch DC servo driver T-Cube
        HWTYPE_LTSXXX		42	// LTS300/LTS150 Long Travel Integrated Driver/Stages
        HWTYPE_L490MZ		43	// L490MZ Integrated Driver/Labjack
        HWTYPE_BBD10X		44	// 1/2/3 Ch benchtop brushless DC servo driver
    """

    _modclass = 'APTMotor'
    _modtype = 'hardware'

    # connectors
    _out = {'aptmotor': 'MotorInterface'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)

    def activation(self, e):
        """ Initialize instance variables and connect to hardware as configured.
        """
        self.Connected = False
        self.verbose = False

        self.HWType = c_long()
        self.SerialNum = c_long()

        self.blCorr = 0.10  # 100um backlash correction

        # Load DLL
        if platform.architecture()[0] == '64bit':
            self.aptdll = windll.LoadLibrary(os.path.join(self.get_main_dir(), 'thirdparty', 'thorlabs', 'win64', 'APT.dll'))
        elif platform.architecture()[0] == '32bit':
            self.aptdll = windll.LoadLibrary(os.path.join(self.get_main_dir(), 'thirdparty', 'thorlabs', 'win64', 'APT.dll'))
        else:
            self.logMsg('Unknown platform, cannot load the Thorlabs dll.', msgType='error')

        self.aptdll.EnableEventDlg(True)
        self.aptdll.APTInit()

        # Read HW from config
        config = self.getConfiguration()

        if 'motor_hw_type' in config.keys():
            self.HWType = c_long(config['motor_hw_type'])
        else:
            self.logMsg('Motor HW Type not found in the configuration, '
                        'searching for motors will not work', msgType='error')

        if 'motor_serial_number' in config.keys():
            self.SerialNum = c_long(config['motor_serial_number'])
            self.initializeHardwareDevice()
            # TODO : Error reporting to know if initialisation went sucessfully or not.
        else:
            self.logMsg('Motor serial number not found in the configuration.\n'
                        'This number is essential, without it no proper '
                        'communication can be established!\n'
                        'The Serial number can be found at the back of the '
                        'Step Motor controller.', msgType='error')

    def deactivation(self, e):
        """ Disconnect from hardware and clean up """
        self.cleanUpAPT()

    def getNumberOfHardwareUnits(self):
        '''
        Returns the number of HW units connected that are available to be interfaced
        '''
        numUnits = c_long()
        self.aptdll.GetNumHWUnitsEx(self.HWType, pointer(numUnits))
        return numUnits.value

    def getSerialNumberByIdx(self, index):
        '''
        Returns the Serial Number of the specified index
        '''
        HWSerialNum = c_long()
        hardwareIndex = c_long(index)
        self.aptdll.GetHWSerialNumEx(self.HWType, hardwareIndex, pointer(HWSerialNum))
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
        You can only get the position of the motor and move the motor after it has been initialised.
        Once initiallised, it will not respond to other objects trying to control it, until released.
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

    def getStageAxisInformation(self):
        minimumPosition = c_float()
        maximumPosition = c_float()
        units = c_long()
        pitch = c_float()
        self.aptdll.MOT_GetStageAxisInfo(self.SerialNum, pointer(minimumPosition), pointer(maximumPosition), pointer(units), pointer(pitch))
        stageAxisInformation = [minimumPosition.value, maximumPosition.value, units.value, pitch.value]
        return stageAxisInformation

    def setStageAxisInformation(self, minimumPosition, maximumPosition):
        minimumPosition = c_float(minimumPosition)
        maximumPosition = c_float(maximumPosition)
        units = c_long(1)  # units of mm
        # Get different pitches of lead screw for moving stages for different stages.
        pitch = c_float(self.config.get_pitch())
        self.aptdll.MOT_SetStageAxisInfo(self.SerialNum, minimumPosition, maximumPosition, units, pitch)
        return True

    def getHardwareLimitSwitches(self):
        reverseLimitSwitch = c_long()
        forwardLimitSwitch = c_long()
        self.aptdll.MOT_GetHWLimSwitches(self.SerialNum, pointer(reverseLimitSwitch), pointer(forwardLimitSwitch))
        hardwareLimitSwitches = [reverseLimitSwitch.value, forwardLimitSwitch.value]
        return hardwareLimitSwitches

    def getVelocityParameters(self):

        minimumVelocity = c_float()
        acceleration = c_float()
        maximumVelocity = c_float()
        self.aptdll.MOT_GetVelParams(self.SerialNum, pointer(minimumVelocity), pointer(acceleration), pointer(maximumVelocity))
        velocityParameters = [minimumVelocity.value, acceleration.value, maximumVelocity.value]
        return velocityParameters

    def getVel(self):
        """ Get the current velocity setting
        """
        if self.verbose:
            print('getVel probing...')
        minVel, acc, maxVel = self.getVelocityParameters()
        if self.verbose:
            print('getVel maxVel')
        return maxVel

    def setVelocityParameters(self, minVel, acc, maxVel):
        minimumVelocity = c_float(minVel)
        acceleration = c_float(acc)
        maximumVelocity = c_float(maxVel)
        self.aptdll.MOT_SetVelParams(self.SerialNum, minimumVelocity, acceleration, maximumVelocity)
        return True

    def setVel(self, maxVel):
        """set the velocity
        """
        if self.verbose:
            print('setVel', maxVel)
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

    def getPos(self):
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
        @param relDistance    float     Relative position desired
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
        absPosition    float     Position desired
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
        maxVel = self.getVels()
        # Set new desired max velocity
        self.setVel(moveVel)
        self.move_rel(relDistance)
        self.setVel(maxVel)
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
        self.setVel(moveVel)
        self.move_rel(absPosition)
        self.setVel(maxVel)
        if self.verbose:
            print('mcAbs SUCESS')
        return True

    def mbRel(self, relDistance):
        '''
        Moves the motor a relative distance specified
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

        ''' Miscelaneous '''

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

        self.logMsg('The APT motor cannot abort!\n'
                    'Please wait for it to finish moving.',
                    msgType='warning')
