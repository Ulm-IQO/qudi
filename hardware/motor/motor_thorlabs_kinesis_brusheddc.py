# -*- coding: utf-8 -*-

"""
This module controls Kinesis brushed dc motor actuators made by Thorlabs.

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

import datetime
import clr
import sys

from System import String
from System import Decimal
from System.Collections import *

from collections import OrderedDict

from core.module import Base, ConfigOption
from interface.motor_interface import MotorInterface


class MotorThorlabsKinesisBrushedDC(Base, MotorInterface):
    """
    Module for the Kinesis controller for motors and stages sold by Thorlabs.

    This controller uses the Kinesis .net interface provided by Thorlabs.

    Example config for copy-paste:

    kinesis_motor:
        module.Class: 'motor.motor_thorlabs_kinesis_brusheddc.MotorThorlabsKinesisBrushedDC'
        controller_serial: ''
        axis_label: 'phi'

    """
    _modclass = 'MotorRotation'
    _modtype = 'hardware'

    _kinesis_path = ConfigOption('kinesis_path', r'C:\Program Files\Thorlabs\Kinesis')
    _controller_serial = ConfigOption('controller_serial', missing='error')
    _axis_label = ConfigOption('axis_label', 'x', missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        sys.path.append(self._kinesis_path)
        clr.AddReference("Thorlabs.MotionControl.Controls")
        clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
        clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
        clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
        import Thorlabs.MotionControl.Controls as ctrls
        import Thorlabs.MotionControl.DeviceManagerCLI as dmc
        import Thorlabs.MotionControl.GenericMotorCLI as gmc
        import Thorlabs.MotionControl.KCube.DCServoCLI as dcs
        self._dmc = dmc
        self._gmc = gmc
        self._dcs = dcs

        self._dmc.DeviceManagerCLI.BuildDeviceList()
        self.dev = self._dcs.KCubeDCServo.CreateKCubeDCServo(self._controller_serial)
        self.dev.Connect(self._controller_serial)
        self.dev.IdentifyDevice()

        if not self.dev.IsSettingsInitialized():
            self.dev.WaitForSettingsInitialized(1000)

        motor_configuration = self.dev.LoadMotorConfiguration(self._controller_serial)
        devinfo = self.dev.GetDeviceInfo()

        self.log.info('Name: {} Type: {} Ser: {}  FW: {} HW: {} SW: {}'.format(
            devinfo.Name,
            devinfo.DeviceType,
            devinfo.SerialNumber,
            devinfo.FirmwareVersion,
            devinfo.HardwareVersion,
            devinfo.SoftwareVersion,
        ))

        limits = self.dev.AdvancedMotorLimits
        self.log.info('Motor: {} acc {}{} len {}-{}{} vel {}{} DevUnits {}'.format(
            motor_configuration.DeviceSettingsName,
            limits.AccelerationMaximum,
            limits.AccelerationUnits,
            limits.LengthMinimum,
            limits.LengthMaximum,
            limits.LengthUnits,
            limits.VelocityMaximum,
            limits.VelocityUnits,
            limits.MustUseDeviceUnits
        ))

        self.log.info('Extra {}'.format(
            self.dev.GetBacklash(),
        ))

        self._min_pos = Decimal.ToDouble(limits.LengthMinimum) / 100
        self._max_pos = Decimal.ToDouble(limits.LengthMaximum) / 100

        self._axis_unit = limits.LengthUnits
        self._pos_step = Decimal.ToDouble(limits.LengthStep) / 100

        self._max_velocity = Decimal.ToDouble(limits.VelocityMaximum)
        self._velocity_step = Decimal.ToDouble(limits.VelocityStep)

        self._max_acc = Decimal.ToDouble(limits.AccelerationMaximum)
        self._acc_step = Decimal.ToDouble(limits.AccelerationStep
                                          )
        #self.log.info('Limits: {0}{2} to {1}{2}'
        #              ''.format(self._min_pos, self._max_pos, self._axis_unit))

        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.dev.Disconnect(True)
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

        axis = {
            'label': self._axis_label,
            'ID': self._controller_serial,
            'unit': self._axis_unit,
            'ramp': None,
            'pos_min': self._min_pos,
            'pos_max': self._max_pos,
            'pos_step': self._pos_step,
            'vel_min': 0,
            'vel_max': self._max_velocity,
            'vel_step': self._velocity_step,
            'acc_min': 0,
            'acc_max': self._max_acc,
            'acc_step': self._acc_step,
        }

        # assign the parameter container to a name which will identify it
        constraints[axis['label']] = axis
        return constraints

    def move_rel(self, param_dict):
        """Moves stage by a given angle (relative movement)

        @param dict param_dict: Dictionary with axis name and relative movement in units

        @return dict: Dictionary with axis name and final position in units
        """
        if self._axis_label in param_dict:
            rel = param_dict[self._axis_label]

            if rel > 0:
                direction = self._gmc.MotorDirection.Forward
            else:
                direction = self._gmc.MotorDirection.Backward
            self.dev.MoveRelative(direction, Decimal(abs(rel)), 60000)
            return self.get_pos([self._axis_label])

        return {}

    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        if self._axis_label in param_dict:
            pos = param_dict[self._axis_label]
            self.dev.MoveTo(Decimal(pos), 60000)
            return self.get_pos([self._axis_label])
        return {}

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self.dev.StopImmediate()
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the rotation stage

        @param list param_list: List with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if param_list is None:
            param_list = [self._axis_label]

        if self._axis_label in param_list:
            self.dev.RequestPosition()
            pos = float(Decimal.ToDouble(self.dev.Position))
            return {self._axis_label: pos}

        return {}

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict status:
        """
        self.dev.RequestStatus()
        self.dev.RequestStatusBits()
        s = self.dev.Status
        print(dir(s))
        return {self._axis_label: s}

    def calibrate(self, param_list=None):
        """ Calibrates the rotation motor

        @param list param_list: Dictionary with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if param_list is None:
            param_list = [self._axis_label]

        if self._axis_label in param_list:
            t1 = datetime.datetime.now()
            self.dev.Home(60000)
            self.log.info('Homing for {}'.format(datetime.datetime.now() - t1))
            pos = self.get_pos([self._axis_label])
            return pos

        return {}

    def get_velocity(self, param_list=None):
        """ Asks current value for velocity.

        @param list param_list: Dictionary with axis name

        @return dict velocity: Dictionary with axis name and velocity in deg/s
        """
        if param_list is None:
            param_list = [self._axis_label]

        if self._axis_label in param_list:
            vel_pars = self.dev.GetVelocityParams()
            return {self._axis_label: Decimal.ToDouble(vel_pars.MaxVelocity)}

        return {}

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: Dictionary with axis name and target velocity in deg/s

        @return dict velocity: Dictionary with axis name and target velocity in deg/s
        """
        if self._axis_label in param_dict:
            vel_pars = self.dev.GetVelocityParams()
            vel_pars.MaxVelocity = Decimal(param_dict[self._axis_label])
            self.dev.SetVelocityParams(vel_pars)
            vel_pars = self.dev.GetVelocityParams()
            return {self._axis_label: Decimal.ToDouble(vel_pars.MaxVelocity)}

        return {}

    def reset(self):
        """ Reset the controller.
            Afterwards, moving to the home position with calibrate() is necessary.
        """
        self.dev.ResetStageToDefaults()
