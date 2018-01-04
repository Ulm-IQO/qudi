# -*- coding: utf-8 -*-
"""
This module operates a confocal microscope based on a stepping hardware.

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

from qtpy import QtCore
from collections import OrderedDict
import time
import datetime
import numpy as np
import matplotlib.pyplot as plt

from core.module import Connector, ConfigOption, StatusVar
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


# info: I hardcoded the clock channel in the logic as i do not know how to set a config option like this for the
# logic module
# Todo: This needs to be fixed in time as it is unflexible for non programming users

def truncate(f, n):
    """Truncates/pads a float f to n decimal places without rounding"""
    # necessary to avoid floating point conversion errors
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return float('.'.join([i, (d + '0' * n)[:n]]))


class CavityStabilisationLogic(GenericLogic):  # Todo connect to generic logic
    """
    This is the Logic class for software driven cavity length stabilisation, both in reflection and transmission .
    """
    _modclass = 'CavityStabilisationLogic'
    _modtype = 'logic'

    # declare connectors
    analoguereader = Connector(interface='AnalogReaderInterface')
    stepper = Connector(interface='ConfocalStepperInterface')

    # Todo: add connectors and QTCore Signals
    # signals
    signal_start_stepping = QtCore.Signal()
    signal_stop_stepping = QtCore.Signal()
    signal_continue_stepping = QtCore.Signal()

    # signals
    signal_stabilise_cavity = QtCore.Signal()
    signal_optimize_length = QtCore.Signal(float, bool)

    class Axis:  # Todo this needs a better name here as it also applies for the APD and the NIDAQ output
        # Todo: I am not sure fi this inheritance is sensible (Generic logic)
        def __init__(self, name, hardware, log):
            self.name = name
            self.mode = None
            self.dc_mode = None

            self.steps_direction = 5

            self.hardware = hardware
            self.voltage_range = []
            self.feedback_precision_volt = None

            self.log = log

            # initialise values
            self.get_stepper_mode()
            self.get_dc_mode()
            self.closed_loop = self.hardware.get_position_feedback(self.name)

        def _check_mode(self):
            """ Checks if the voltage in the device is the same as set by the program
            If the voltages are different the voltage in the device is changed to the set voltage

            @return int: error code (0:OK, -1:error)
            """
            mode = self.hardware.get_axis_mode(self.name)
            if mode == -1:
                return -1
            elif mode != self.mode:
                self.log.warning(
                    "The device has different mode ({}) compared the assumed mode {}. "
                    "The mode of the device will be changed to the programs mode".format(mode, self.mode))
                # checks if stepper is still running
                if False:  # self.getState() == 'locked':
                    #    self.log.warning("The stepper is still running")
                    return -1
                else:
                    if self.mode == "ground":
                        retval = self.set_mode_ground()
                    elif self.mode == "stepping":
                        retval = self.set_mode_stepping()
                    else:
                        self.log.error(
                            "The mode set by the program %s does not exist or can not be accessed by this program.\n"
                            "Please change it to one of the possible modes", self.mode)
                        retval = -1
                    return retval
            return 0

        def set_mode_ground(self):
            """Sets the mode of the stepping device to grounded for the specified axis

            @return int: error code (0:OK, -1:error)
            """
            retval = self.hardware.set_axis_mode(self.name, "ground")
            if retval < 0:
                return retval
            self.mode = "ground"
            return retval

        def get_stepper_mode(self):
            """Gets the mode of the stepping device for the specified axis

            @return int: error code (0:OK, -1:error)
            """
            mode = self.hardware.get_axis_mode(self.name)
            if mode == -1:
                return mode
            else:
                self.mode = mode
                return mode

        def get_dc_mode(self):
            """Reads the DC input status from the stepper hardware
            @return bool: True for on, False for off or error
            """
            self.dc_mode = self.hardware.get_DC_in(self.name)
            return self.dc_mode

        def set_dc_mode(self, On=False):
            """Set the DC input status of the stepper hardware

            @param bool On: if True is turned on, False is turned off, default False
            @return int: error code (0: OK, -1:error)
            """
            return self.hardware.set_DC_in(self.name, On)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Todo: Add initialisation from _statusVariable
        # Connectors
        self._stepping_device = self.get_connector('stepper')
        self._position_feedback_device = self.get_connector('analoguereader')

        # Initialises hardware values
        self.axis = self.get_stepper_axes_use()
        self.axis["APD"] = "APD"
        # first steps to get a to a better handling of axes parameters

        self.axis_class = dict()

        # Todo: Add Offset dictionary and update all offset uses accordingly.
        for name in self.axis.keys():
            self.axis_class[name] = self.Axis(name, self._stepping_device, self.log)
            # Todo: Add error check here or in method else it tries to write non existing value into itself
            if self.axis_class[name].closed_loop:
                self.axis_class[name].voltage_range = self.get_feedback_voltage_range(name)
                self.axis_class[name].feedback_precision_volt = self.calculate_precision_feedback(name)

        self.stabilisation_axes = "z"  # The axis  along which the cavity is to be stabilised
        self.input_axis = "APD"  # The "axis", that is the channel, which give the feedback for the stabilisation
        self.stabilistation_frequency = 1000  # Hz #Todo: This needs to have a better name
        self._stabilisation_clock_channel = self._position_feedback_device._clock_channel
        self.threshold = 0.01  # in V
        self.truncate(self.threshold, self.axis_class[self.input_axis].feedback_precision_voltage)
        self.stopRequested = False
        self.reflection = True

        if self.input_axis not in self.axis_class.keys():
            self.log.error("The given stabilisation axis is not defined. Program will fatally fail using this axis")

        # Sets connections between signals and functions
        self.signal_stabilise_cavity.connect(self._stabilise_cavity_length, QtCore.Qt.QueuedConnection)
        self.signal_optimize_length.connect(self._optimize_cavity_length, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        pass
        # Todo: This method nees to be implemented

    def initialise_readout(self):
        """Sets up the continuous analogue input reader

        @return int: error code (0:OK, -1:error)
        """
        return self._position_feedback_device.set_up_analogue_voltage_reader(self.input_axis)

    def close_readout(self):
        """Closes the continuous analogue input reader

        @return int: error code (0:OK, -1:error)
        """
        if 0 > self._position_feedback_device.close_analogue_voltage_reader(axes[0]):
            self.log.error("It was not possible to close the analog voltage reader")
            return -1
        return 0

    def initialise_analog_stabilisation(self):
        """Sets up the analog output channel used to stabilise the length of the cavity

        @return int: error code (0:OK, -1:error)"""
        pass
        # Todo: The corresponding NIDAQ methods do not exist yet. Maybe I also need a  new interface for this

    def close_analog_stabilisation(self):
        """Closes up the analog output channel used to stabilise the length of the cavity

        @return int: error code (0:OK, -1:error)"""
        pass

    def start_cavity_stabilisation(self):
        """Starts the process of cavity stabilisation"""
        if self.initialise_readout() < 0:
            self.log.error(
                "initialising the cavity stabilisation process failed.\ The analog input could not be initialised")
            return -1
        if self.initialise_analog_stabilisation() < 0:
            self.log.error(
                "initialising the cavity stabilisation process failed.\ The analog output could not be initialised")
            return -1

        self._stabilise_cavity_length()

    def _stabilise_cavity_length(self):
        """Stabilises the cavity length via a software feedback loop"""
        if self.stopRequested:
            try:
                self.close_analog_stabilisation()
            except Exception as e:
                self.log.exception('Could not close the analogue output.')
            try:
                self.close_readout()
            except Exception as e:
                self.log.exception('Could not close the analogue input reader.')
                self.stopRequested = False
            self.log.info("Cavity stabilisation stopped successfully")
            return

        result = self._position_feedback_device.get_analogue_voltage_reader(self.input_axis)
        if result[1] == 0:
            self.stopRequested = True
            self.log.error("reading the axis voltage failed")
            return -1
        voltage_result = result[0][0]

        # checks if the measured values lie outside the threshold
        if self.reflection:
            if voltage_result > self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.input_axis].feedback_precision_voltage:
                self._optimize_cavity_length(voltage_result)
                # Todo: it might make sense to make an intelligent optimisation algorithm, that remembers the direction
                # that worked at the last optimisation. this is especially sensible for drift ins one direction,
                # but not helpful for random fluctuations or non directional vibrations. Might help for length changes
                # during step scanning due to tilted samples. Here we assume now moving in the same direction
                # will be enough
        else:
            if voltage_result < self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.input_axis].feedback_precision_voltage:
                self._optimize_cavity_length(voltage_result)

        # if a maximum speed of the readout should be wanted a time.sleep can be added.
        # for this one should measure the time the operation requires. The difference between the minimum time between
        # steps and the time elapsed can then be stayed in the sleep state by the program

        self.signal_stabilise_cavity.emit()

    def _optimize_cavity_length(self, previous_voltage, direction=True):
        """ Changes cavity length by a PID loop kind of function to get the voltage value below the threshold again

        @return int:  not clear yet
        """
        precision = self.axis_class[self.input_axis].feedback_precision_position
        new_voltage = 0  # Todo: put realistic value

        # Todo: Maybe it is sensible to make a safety net of: it can only be repeated 500 times or something
        # before it has to stop
        if self.stopRequested:
            return 0

        voltage_result = self.change_and_measure(self.input_axis, voltage=new_voltage, direction=direction)
        if voltage_result < 0:
            self.stopRequested = True
            return -1

        # update position and leave algorithm if position was reached.
        if abs(voltage_result - previous_voltage) < precision:  # comparing floats
            # redo stepping. If nothing happens again we are either on resonance or completely off resonance
            # or the values were chosen wrong.
            # In any case this has to be optimised by user
            voltage_result = self.change_and_measure(self.input_axis, voltage=new_voltage, direction=direction)
            if voltage_result < 0:
                self.stopRequested = True
                return -1
            if abs(voltage_result - previous_voltage) < precision:  # comparing floats
                # move back to previous position. This is a safety precaution
                voltage_result = self.change_and_measure(self.input_axis, voltage=new_voltage,
                                                         direction=not direction)
                if voltage_result < 0:
                    self.stopRequested = True
                    return -1
                return 0

        if self.reflection:
            if voltage_result > previous_voltage:
                if voltage_result > self.threshold and abs(self.threshold - voltage_result) > \
                        self.axis_class[self.input_axis].feedback_precision_voltage:
                    # the optimisation has been successful. Stop method
                    return 0
                # change direction
                direction = not direction
                # else: keep direction
        else:
            if voltage_result > previous_voltage:
                if voltage_result < self.threshold and abs(self.threshold - voltage_result) > \
                        self.axis_class[self.input_axis].feedback_precision_voltage:
                    return 0
                # change direction
                direction = not direction
                # else: keep direction
        self.signal_optimize_length.emit(voltage_result, direction)

    def stop_cavity_stabilisation(self):
        """Stops the process of cavity stabilisation"""
        self.stopRequested = True

    def change_cavity_length(self, axis, voltage, direction=True):
        pass

    def change_and_measure(self, axis, voltage, direction=True):
        self.change_cavity_length(axis, voltage, direction=direction)
        time.sleep(0.00001)  # 10mus. This is very long compared to the NIDAQ clock rate
        # Todo: Do we even need this here?

        # compare new voltage to threshold
        result = self._position_feedback_device.get_analogue_voltage_reader([axis])
        if result[1] == 0:
            self.stopRequested = True
            self.log.error("reading the axis voltage failed")
            return -1
        return result[0][0]

    def get_feedback_voltage_range(self, axis_name):
        """Gets the voltage range of the position feedback device that can be converted to positions

        @axis_name The axis for which the voltage range is retrieved

        @ return list: min and max possible voltage in feedback for given axis"""
        return self._position_feedback_device._ai_voltage_range[axis_name]

    def calculate_precision_feedback(self, axis_name):
        """Calculates the position feedback devices precision for a given axis

        @param str axis_name: The name of the axis for which the precision is to be calculated

        @return float: precision of the feedback device volt  (-1.0 for error)
        """
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1

        voltage_range = self.axis_class[axis_name].voltage_range

        # the NIDAQ has a resolution of res and only use 95% of the range giving the following voltage resolution.
        # If any other device might be used one day this needs to be passed as a variable
        precision_voltage = ((voltage_range[1] - voltage_range[0]) / (
                2 ** self._position_feedback_device.get_ai_resolution())) * 1.05
        precision_voltage = float(truncate(precision_voltage, 6))
        return precision_voltage

    def get_stepper_axes_use(self):
        """ Find out how the axes of the stepping device are named.

        @return dict: {axis_name:axis_id}

        Example:
          For 3D confocal microscopy in Cartesian coordinates, ['x':1, 'y':2, 'z':3] is a sensible
          value.
          If you only care about the number of axes and not the assignment and names
          use get_stepper_axes
        """
        return self._stepping_device.get_stepper_axes_use()
