# -*- coding: utf-8 -*-
"""
For Zaber linear stages that support the Zaber motion library.

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


from collections import OrderedDict

from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption, MissingOption

from zaber_motion import Library as zlib
from zaber_motion.ascii import Connection as zcon
from zaber_motion import Units


class ZaberAxis(Base):

    def __init__(self, axis_handle, device_parent, label=''):
        """
        Initializer called from a ZaberStage that manages the connection
        """
        self._axis = axis_handle
        self._contr_device = device_parent

        self.label = label
        self._wait_until_done_default = False
        self._constraints = {}

        self._backlash_correction = False
        self._backlash_correction_offset = 0e-9

    def get_constrains(self):
        default_constr = {
            'pos_min': None,
            'pos_max': None,
             # todo: actually used in any way or wait until raise from Zaber?
            'vel_min': None,
            'vel_max': None,
            'acc_min': None,
            'acc_max': None
        }

        # update constraints by the ones loaded from config by ZaberStage
        for key, val in self._constraints.items():
            if key in default_constr:
                default_constr.update({key: val})
            else:
                self.log.warning(f"Found key {key} in constraints "
                                 f"that is not defined in get_constarints()")

        return default_constr

    def set_constraints(self, contraints_dict):
        for key, val in contraints_dict.items():
            self._constraints[key] = val

    def get_hardware_info(self):
        """ Get information from the hardware"""

        return self._contr_device.identity()

    def get_velocity(self):
        """ Get the current velocity setting
        """
        self._axis.settings.get("maxspeed", Units.VELOCITY_METERS_PER_SECOND)

    def set_acceleration(self, acceleration):
        # todo: check whether we have to check against contrasint values manually
        self._axis.settings.set("accel", acceleration, Units.ACCELERATION_METRES_PER_SECOND_SQUARED)

    def get_acceleration(self):

        return self._axis.settings.get("accel",  Units.ACCELERATION_METRES_PER_SECOND_SQUARED)

    def set_velocity(self, velocity):
        """ Set the maximal velocity for the motor movement.

        @param float maxVel: maximal velocity of the stage in m/s.
        """
        # todo: check whether we have to check against contrasint values manually
        self._axis.settings.set("maxspeed", velocity, Units.VELOCITY_METERS_PER_SECOND)

    def get_closed_loop_settings(self):
        info_dict = {"enabled": self._axis.settings.get('cloop.enable'),
                     "continuous": self._axis.settings.get('cloop.continuous.enable'),
                     "displace.tolerance": self._axis.settings.get('cloop.displace.tolerance'),
                     "settle.period": self._axis.settings.get('cloop.settle.period'),
                     "timeout": self._axis.settings.get(' cloop.timeout'),
                     "settle.tolerance": self._axis.settings.get('cloop.settle.tolerance'),
                     "recovery.enable": self._axis.settings.get('cloop.recovery.enable')}

        return info_dict

    def set_closed_loop(self):
        raise NotImplementedError

    def get_pos(self):
        """ Obtain the current absolute position of the stage.

        @return float: the value of the axis either in m.
        """

        self._axis.get_position()

    def move_rel(self, distance, wait_until_done=False, force_no_backslash_corr=False):
        """ Moves the motor a relative distance specified.
        If backlash correction is activated, movements in negative direction are over-shot
        and the target position is approached (always) in positive direction.


        @param float relDistance: Relative position desired, in m.
        """

        wait_until_done = self.get_wait_until_done(wait_until_done)

        if not self._backlash_correction or force_no_backslash_corr:
            self._axis.move_relative(distance, Units.LENGTH_METRES,
                                     wait_until_idle=wait_until_done)
        else:
            if distance > 0:
                # move normally in positive direction
                self.move_rel(distance, wait_until_done=wait_until_done,
                              force_no_backslash_corr=True)
            else:
                self._axis.move_relative(distance - self._backlash_correction_offset,
                                        Units.LENGTH_METRES,
                                        wait_until_done=wait_until_done)
                self._axis.move_relative(self._backlash_correction_offset,
                                        Units.LENGTH_METRES,
                                        wait_until_done=wait_until_done)

    def move_abs(self, position, wait_until_done=None, force_no_backslash_corr=False):
        """ Moves the motor to the absolute position specified.
        If backlash correction is activated, movements in negative direction are over-shot
        and the target position is approached (always) in positive direction.

        @param float position: absolute Position desired, in m.
        """

        wait_until_done = self.get_wait_until_done(wait_until_done)

        if not self._backlash_correction or force_no_backslash_corr:
            self._axis.move_absolute(position, Units.LENGTH_METRES, wait_until_idle=wait_until_done)

        else:
            current_pos = self._axis.get_position()
            if current_pos < position:
                # move normally in positive direction
                self.move_abs(position, wait_until_done=wait_until_done,
                              force_no_backslash_corr=True)
            else:
                self._axis.move_absolute(position - self._backlash_correction_offset,
                                         Units.LENGTH_METRES,
                                         wait_until_done=wait_until_done)
                self._axis.move_relative(self._backlash_correction_offset,
                                         Units.LENGTH_METRES,
                                         wait_until_done=wait_until_done)

    def get_wait_until_done(self, wait_until_done=None):
        # argument overwrites axis setting
        if wait_until_done != None:
            return wait_until_done
        else:
            return self._wait_until_done_default

    def toggle_wait_until_done(self, wait_until_done):
        self._wait_until_done_default = wait_until_done

    def _wait_until_idle(self):
        self._axis.wait_until_idle()

    def toggle_backlash(self, set_on=True, backlash_offset=None):
        self._backlash_correction = set_on

        if backlash_offset:
            self._backlash_correction_offset = backlash_offset

    def get_status(self):
        info_dict = {'busy': self._axis.is_busy(),
                     'parked': self._axis.is_parked(),
                     'warnings': self._contr_device.warnings.get_flags()}

        return info_dict

    def identify(self):
        """ Causes the motor to blink the Active LED. """
        raise NotImplemented

    def go_home(self, wait_until_done=None):

        wait_until_done = self.get_wait_until_done(wait_until_done)

        self._axis.home(wait_until_done=wait_until_done)


class ZaberStage(Base, MotorInterface):

    """ Control class for an arbitrary collection of ZaberMotor axes.

    The required config file entries are based around a few key ideas:
      - There needs to be a list of axes, so that everything can be "iterated" across this list.
      - There are some config options for each axis that are all in sub-dictionary of the config file.
        The key is the axis label.

    A config file entry for a linear xy-axis stage would look like:

    zaber_motor:
        module.Class: 'motor.zaber_motion.ZaberStage'
        axis_labels: [x, y]
        port: 'COM3'
        axes:
            x:
                serial_num: 00000000
                backlash_correction: False
                backlash_offset: 50e-6
                wait_until_done: False
                constraints:
                    pos_min: 0
                    pos_max: 2
                    vel_min: 1.0
                    vel_max: 10.0
                    acc_min: 4.0
                    acc_max: 10.0
            y:
                serial_num: 00000001
                backlash_correction: False
                backlash_offset: 50e-6
                wait_until_done: False
                constraints:
                    pos_min: -1
                    pos_max: 1
                    vel_min: 1.0
                    vel_max: 10.0
                    acc_min: 4.0
                    acc_max: 10.0

    """

    _serial_port = ConfigOption('port', missing='error')
    _axes_configs = ConfigOption(name='axes', default=dict(), missing='warn')
    _axis_label_list = ConfigOption('axis_labels', default=list(), missing='error')
    _required_hw_params = ['serial_num']
    _optional_hw_params = [ConfigOption('backlash_correction', default=False, missing='nothing'),
                           ConfigOption('backlash_offset', default=50e-6, missing='nothing'),
                           ConfigOption('wait_until_done', default=False, missing='warn')]

    def on_activate(self):
        """ Initialize instance variables and connect to hardware as configured.
        """

        # get and store device info from internet
        zlib.enable_device_db_store()

        self._axis_dict = OrderedDict()
        self._device_list, self._connection = [], None
        hw_conf_dict = self.get_hardware_config_per_axis()

        try:
            self._connection = zcon.open_serial_port(self._serial_port)
            device_list = self._connection.detect_devices()
            self.log.debug(f"Found {len(device_list)} devices on port {self._serial_port}")

            for axis_label in self._axis_label_list:
                serialnumber = hw_conf_dict[axis_label]['serial_num']
                device = [dev for dev in device_list if dev.serial_number == serialnumber]
                if device:
                    device = device[0]
                    label = axis_label

                    if device.axis_count == 1:
                        axis = device[0].get_axis(1)
                        self._axis_dict[axis_label] = ZaberAxis(axis, device, label)
                        self._device_list.append(device)
                    else:
                        self.log.error("Found {}, but expected a daisy-chained topology daisy-chained topology"
                                       " where every stage is a device with exactly one axis")
                else:
                    self.log.warning(f"Couldn't find device with serial {serialnumber}")

            self.log.debug(f"Successfully connected to devices {self._device_list}")
            self.check_and_unpark_on_startup()

        except BaseException:
            self.log.error(f"Couldn't connect to Zaber stage on port {self._serial_port}")

        finally:
            if self._connection:
                self._connection.close()

        for axis_label in self._axis_dict.keys():
            self._axis_dict[axis_label].set_constraints(hw_conf_dict[axis_label]['constraints'])
            # approach positions always from same side to mitigate backlash hysterisis
            self._axis_dict[axis_label].toggle_backlash(hw_conf_dict[axis_label]['backlash_correction'],
                                                        backlash_offset=hw_conf_dict[axis_label]['backlash_offset'])
            self._axis_dict[axis_label].toggle_wait_until_done(hw_conf_dict[axis_label]['wait_until_done'])

    def on_deactivate(self):
        """ Disconnect from hardware and clean up.
        """
        if self._connection:

            self.toggle_park(True)
            self.log.info(f"Parking stage at {self.get_pos()} in preparation of power-off. "
                          f"Don't mechanically force movement to ensure accurate position after power cycle.")

            try:
                self._connection.close()
            except BaseException:
                self.log.exception(f"Failed to close serial connection {self._serial_port}: ")

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the motor stage hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      can be made.

        Provides all the constraints for each axis of a motorized stage
        (like total travel distance, velocity, ...)
        Each axis has its own dictionary, where the label is used as the
        identifier throughout the whole module. The dictionaries for each axis
        are again grouped together in a constraints dictionary in the form

            {'<label_axis0>': axis0 }

        where axis0 is again a dict with the possible values defined below. The
        possible keys in the constraint are defined in the interface file.
        If the hardware does not support the values for the constraints, then
        insert just None. If you are not sure about the meaning, look in other
        hardware files to get an impression.
        """
        constraints = {}
        config = self._axes_configs

        for axis_label in config.keys():

            this_axis = self._axis_dict[axis_label].get_constrains()

            # todo: needed?
            """
            this_axis['ramp'] = ['Trapez']  # a possible list of ramps
        
            this_axis['pos_step'] = 0.01  # in °
            this_axis['vel_step'] = 0.1  # in °/s (a rather arbitrary number)
            this_axis['acc_step'] = 0.01  # in °/s^2 (a rather arbitrary number)
            """
            constraints[axis_label] = this_axis

        return constraints

    def move_rel(self,  param_dict, wait_until_done=False):
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

                if (curr_pos + move > constraints[label_axis]['pos_max']) or\
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
                                         constraints[label_axis]['pos_max']
                                     )
                                     )
                else:
                    self._axis_dict[label_axis].move_rel(move)

        if wait_until_done:
            for label, axis in self._axis_dict.items():
                axis.wait_until_idle()

    def move_abs(self, param_dict, wait_until_done=False):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        constraints = self.get_constraints()

        for label_axis in self._axis_dict:
            if param_dict.get(label_axis) is not None:
                desired_pos = param_dict[label_axis]

                constr = constraints[label_axis]
                if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):

                    self.log.warning(
                        'Cannot make absolute movement of the '
                        'axis "{0}" to position {1}, since it exceeds '
                        'the limts [{2},{3}]. Movement is ignored!'
                        ''.format(label_axis, desired_pos, constr['pos_min'], constr['pos_max'])
                    )
                else:
                    # move all axes simultanously
                    self._axis_dict[label_axis].move_abs(desired_pos, wait_until_done=False)

        if wait_until_done:
            for label, axis in self._axis_dict.items():
                axis.wait_until_idle()

    def abort(self):
        """ Stops movement of the stage. """

        for dev in self._device_list:
            dev.all_axes.stop()

        self.log.warning('Movement of all the axis aborted! Stage stopped.')

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list:
            optional, if a specific position of an axis
            is desired, then the labels of the needed
            axis should be passed as the param_list.
            If nothing is passed, then from each axis the
            position is asked.

        @return
            dict with keys being the axis labels and item the current
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


        After calibration the stage moves to home position which will be the
        zero point for the passed axis. The calibration procedure will be
        different for each stage.
        """

        self.log.info("Starting homing... Make sure the stage can move freely within the needed travel range!")

        if param_list is not None:
            for label_axis in param_list:
                if label_axis in self._axis_dict:
                    self._axis_dict[label_axis].go_home()
        else:
            for label_axis in self._axis_dict:
                self._axis_dict[label_axis].go_home()

    def get_hardware_config_per_axis(self):
        hw_conf_dict = {}

        for ax_name, ax_cfg in self._axes_configs.items():
            self.log.debug(f"Found cfg for ax: {ax_name}: {ax_cfg}")
            hw_conf_dict[ax_name] = ax_cfg
            if not all([k in ax_cfg.keys() for k in self._required_hw_params]):
                self.log.error(f"Didn't find all required parameters {self._required_hw_params} "
                               f"in config for stage {ax_name}")
            for cfg_opt in self._optional_hw_params:
                if cfg_opt.name not in ax_cfg.keys():
                    hw_conf_dict[ax_name][cfg_opt.name] = cfg_opt.default
                    msg = f"Didn't find >> {cfg_opt.name} << for stage axis {ax_name} in configuration. " \
                          f"Setting default {cfg_opt.default}"
                    if cfg_opt.missing == MissingOption.warn:
                        self.log.warning(msg)
                    elif cfg_opt.missing == MissingOption.info:
                        self.log.info(msg)
                    elif cfg_opt.missing == MissingOption.error:
                        raise Exception(msg)

        return hw_conf_dict

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
                if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):

                    self.log.warning(
                        'Cannot set velocity of the axis "{0}" '
                        'to the desired velocity of "{1}", since it '
                        'exceeds the limts [{2},{3}] ! Command is ignored!'
                        ''.format(label_axis, desired_vel, constr['vel_min'], constr['vel_max'])
                    )
            else:
                self._axis_dict[label_axis].set_velocity(desired_vel)

    def toggle_park(self, set_parked):
        for dev in self._device_list:
            if set_parked:
                dev.all_axes.park()
                self.log.info("Parking all axes. Won't move until unparked.")
            else:
                dev.all_axes.unpark()

    def get_parked(self):

        parked = {}

        for label_axis in self._axis_dict:
            parked[label_axis] = self._axis_dict[label_axis]._axis.is_parked()

        if all(value == True for value in parked.values()):
            return True
        elif all(value == False for value in parked.values()):
            return False
        else:
            self.log.error(f"Unexpectedly, not all axes have same park status: {parked}")

    def check_and_unpark_on_startup(self):

        if not self._device_list:
            self.log.warning("Didn't find any connceted stages to unpark.")
            return

        if not self.get_parked():
            self.log.warning("Found an unparked stage after startup. Position may be inaccurate until homing!")
        else:
            self.toggle_park(False)
            self.log.debug(f"Unparking on startup from recovered position: {self.get_pos()}")

