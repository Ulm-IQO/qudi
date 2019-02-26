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
import math
import numpy as np
import os
# import tables
import matplotlib.pyplot as plt
from scipy import ndimage  # For gaussian smoothing of data
from scipy.stats import norm  # To fit gaussian average to data

from core.module import Connector, StatusVar, ConfigOption
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


# Todo make a confocal stepper History class for this logic as exists in confocal logic. This is needed for restarting and
# for back and forward movement in images

def round_to_2(x):
    """Rounds to the second significant figure of a number"""
    return round(x, -int(math.floor(math.log10(abs(x)))) + 1)


# Todo: better threading as it can still kill everything as nidaq is unsedd from to many places in a not error checked way.
def truncate(f, n):
    """Truncates/pads a float f to n decimal places without rounding"""
    # necessary to avoid floating point conversion errors
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return float('.'.join([i, (d + '0' * n)[:n]]))


def in_range(x, min, max):
    """Checks if given value is within a range

    @param float x: value to be checked
    @param float min: lower limit
    @param float max: upper limit
    @return bool: true if x lies within [min,max]
    """
    return (min is None or min <= x) and (max is None or max >= x)


class ConfocalStepperLogic(GenericLogic):  # Todo connect to generic logic
    """
    This is the Logic class for confocal stepping.
    """
    _modclass = 'ConfocalStepperLogic'
    _modtype = 'logic'

    # declare connectors
    confocalstepper1 = Connector(interface='ConfocalStepperInterface')
    savelogic = Connector(interface='SaveLogic')
    confocalcounter = Connector(interface='FiniteCounterInterface')
    analoguereader = Connector(interface='AnalogueReaderInterface')
    analogueoutput = Connector(interface='AnalogueOutputInterface')
    cavcontrol = Connector(interface="CavityStabilisationLogic")

    # status vars
    max_history_length = StatusVar(default=10)
    _scan_axes = StatusVar("scan_axes", default="xy")
    _inverted_scan = StatusVar(default=False)
    _off_set_x = StatusVar(default=0.02)
    _off_set_direction = StatusVar(default=True)

    # config
    _ai_counter = ConfigOption("AI_counter", None, missing="warn")

    # 3D
    _ao_channel = ConfigOption("3D_3rd_Axis", None, missing="warn")
    scan_resolution_3D = ConfigOption('3D_scan_resolution', 1e-6, missing="warn")
    start_voltage_3D = ConfigOption('3D_start_voltage', 0, missing="warn")
    end_voltage_3D = ConfigOption('3D_end_voltage', 1, missing="warn")
    _3D_smoothing_steps = ConfigOption('smoothing_parameter', 0, missing="info")

    # Todo: add /check QTCore Signals (not all have functions yet)
    # signals
    signal_start_stepping = QtCore.Signal()
    signal_stop_stepping = QtCore.Signal()
    signal_continue_stepping = QtCore.Signal()
    signal_step_lines_next = QtCore.Signal(bool)
    signal_start_3D_stepping = QtCore.Signal()

    signal_image_updated = QtCore.Signal()
    signal_change_position = QtCore.Signal(str)
    signal_data_saved = QtCore.Signal()
    signal_tilt_correction_active = QtCore.Signal(bool)
    signal_tilt_correction_update = QtCore.Signal()
    signal_draw_figure_completed = QtCore.Signal()
    signal_position_changed = QtCore.Signal()
    signal_step_scan_stopped = QtCore.Signal()

    signal_sort_count_data = QtCore.Signal(tuple, int)
    signal_sort_count_data_3D = QtCore.Signal(tuple, int)

    sigImageInitialized = QtCore.Signal()
    sig_save_to_npz = QtCore.Signal()
    signal_history_event = QtCore.Signal()

    # Todo: For steppers with hardware real-time info like res readout of attocubes clock synchronisation and readout needs to be written
    # Therefore a new interface (ConfocalReadInterface or similar.) needs to be made

    class Axis:
        # Todo: I am not sure fi this inheritance is sensible (Generic logic)
        def __init__(self, name, hardware, log):
            self.name = name
            self.step_amplitude = None
            self.step_freq = None
            self.mode = None
            self.dc_mode = None

            self.steps_direction = 5

            self.hardware = hardware
            self.voltage_range = []
            self.step_range = []
            self.absolute_position = None
            self.feedback_precision_volt = None
            self.feedback_precision_position = None

            self.log = log

            # initialise values
            self.get_position_range_stepper()
            self.get_stepper_frequency()
            self.get_stepper_amplitude()
            self.get_stepper_mode()
            self.closed_loop = self.hardware.get_position_feedback(self.name)

        def _check_freq(self):
            """ Checks if the frequency in te device is the same as set by the program
            If the frequencies are different the frequency in the device is changed to the set
            frequency

            @return int: error code (0:OK, -1:error)
            """
            freq = self.hardware.get_step_freq(self.name)
            if freq == -1:
                return -1
            elif freq != self.step_freq:
                self.log.warning(
                    "The device has different frequency of {} then the set frequency {}. "
                    "The frequency will be changed to the set frequency".format(freq,
                                                                                self.step_freq))
                # checks if stepper is still running
                # if self.module_state() == 'locked':
                #    self.log.warning("The stepper is still running")
                #    return -1
                return self.set_stepper_frequency(self.step_freq)
            return 0

        def _check_amplitude(self):
            """ Checks if the voltage in te device is the same as set by the program
            If the voltages are different the voltage in the device is changed to the set voltage

            @return int: error code (0:OK, -1:error)
            """

            amp = self.hardware.get_step_amplitude(self.name)
            if amp == -1:
                return -1
            elif amp != self.step_amplitude:
                self.log.warning(
                    "The device has different voltage of {} then the set voltage {}. "
                    "The voltage will be changed to the set voltage".format(amp, self.step_amplitude))
                # checks if stepper is still running
                # if self.module_state() == 'locked':
                #    self.log.warning("The stepper is still running")
                #    return -1
                return self.set_stepper_amplitude(self.step_amplitude)
            return 0

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
                if False:  # self.module_state() == 'locked':
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

        def set_stepper_frequency(self, frequency=None):
            """
            Sets the stepping frequency for a specific axis to frequency

            @param float frequency: desired frequency

            @return int: error code (0:OK, -1:error)
            """

            # checks if stepper is still running
            # if self.module_state() == 'locked':
            #    return -1

            if frequency is not None:
                if frequency is not None:
                    range_f = self.get_freq_range()
                    if frequency < range_f[0] or frequency > range_f[1]:
                        self.log.error(
                            'Voltages {0} exceed the limit, the positions have to '
                            'be adjusted to stay in the given range.'.format(frequency))
                        return -1
                    else:
                        self.step_freq = frequency
                        return self.hardware.set_step_freq(self.name, frequency)
                else:
                    self.log.warning("No amplitude given so value can not be changed")
                    return -1
            else:
                self.log.info("No frequency was given so the step frequency was not changed.")
                return 0

        def get_stepper_frequency(self):
            freq = self.hardware.get_step_freq(self.name)
            if freq == -1:
                self.log.warning("The Stepping device could not read out the frequency")
                return self.step_freq
            # Todo. The error handling in the methods in the stepper is not good yet and this needs to be adapted the moment
            # this is better
            self.step_freq = freq
            return freq

        def set_stepper_amplitude(self, amplitude=None):
            """
            Sets the stepping amplitude for a specific axis to amplitude

            @param float amplitude: desired amplitude (V)

            @return int: error code (0:OK, -1:error)
            """
            # checks if stepper is still running
            # if self.module_state() == 'locked':
            #    return -1
            if amplitude is not None:
                range_a = self.get_amplitude_range()
                if amplitude < range_a[0] or amplitude > range_a[1]:
                    self.log.error(
                        'Voltages {0} exceed the limit, the positions have to '
                        'be adjusted to stay in the given range.'.format(amplitude))
                    return -1
                else:
                    self.step_amplitude = amplitude
                    return self.hardware.set_step_amplitude(self.name, amplitude)
            else:
                self.log.info("No amplitude given so value can not be changed")
                return 0

        def get_stepper_amplitude(self):
            amp = self.hardware.get_step_amplitude(self.name)
            if amp == -1:
                self.log.warning("The Stepping device could not read out the amplitude")
                return self.step_amplitude
            # Todo. The error handling in the methods in the stepper is not good yet and this needs to be adapted the moment
            # this is better
            self.step_amplitude = amp
            return amp

        def get_freq_range(self):
            """Returns the current possible frequency range of the stepping device for all axes
            @return list: The range fo possible frequencies (min and max). Empty for error
            """
            range = self.hardware.get_freq_range_stepper()
            if self.name in range.keys():
                return range[self.name]
            else:
                self.log.error("Frequency range is not defined for axis %s", self.name)
                return []

        def get_amplitude_range(self):
            """Returns the current possible stepping voltage range of the stepping device for all axes
            @return list: voltage range of scanner
            """
            return self.hardware.get_amplitude_range_stepper()

        def set_mode_stepping(self):
            """Sets the mode of the stepping device to stepping for the specified axis

            @return int: error code (0:OK, -1:error)
            """
            retval = self.hardware.set_axis_mode(self.name, "stepping")
            if retval < 0:
                return retval
            self.mode = "stepping"
            return retval

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

        def get_position_range_stepper(self):
            """Gets the total possible position range of the device axis

            @ return list: min and max possible voltage in feedback for given axis"""
            self.step_range = self.hardware.get_position_range_stepper(self.name)
            return self.step_range

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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Todo: Add initialisation from _statusVariable

        # Connectors
        self._stepping_device = self.confocalstepper1()
        self._counting_device = self.confocalcounter()
        self._position_feedback_device = self.analoguereader()
        self._analogue_output_device = self.analogueoutput()
        self._save_logic = self.savelogic()
        self._cavitycontrol = self.cavcontrol()

        # Initialises hardware values
        self.axis = self.get_stepper_axes_use()
        # first steps to get a to a better handling of axes parameters

        self.axis_class = dict()

        # Todo: Add Offset dictionary and update all offset uses accordingly.
        for i in self.axis.keys():
            self.axis_class[i] = self.Axis(i, self._stepping_device, self.log)
            # Todo: Add error check here or in method else it tries to write non existing value into itself
            if self.axis_class[i].closed_loop:
                self.axis_class[i].get_position_range_stepper()
                self.axis_class[i].voltage_range = self.get_feedback_voltage_range(i)
                self.get_position([i])
                self.axis_class[i].feedback_precision_volt, self.axis_class[
                    i].feedback_precision_position = self.calculate_precision_feedback(i)

        # Initialise step image constraints
        self.stopRequested = False

        # Initialise for scan_image
        self._step_counter = 0
        self._get_scan_axes()

        self._start_position = []
        self.map_scan_position = True
        self._fast_scan = False

        # For position smoothing
        self._gaussian_smoothing_parameter = 20  # This is used for position feedback smoothing

        if self._ai_counter != None:
            if self._ai_counter in self._counting_device._analogue_input_channels:
                self._ai_scanner = True
            else:
                self._ai_scanner = False
        else:
            self._ai_scanner = False

        # initialize data arrays for stepper
        self._initalize_data_arrays_stepper()

        self.initialize_image()

        # Tilt correction
        self._lines_correct_3rd_axis = 5
        self._3rd_direction_correction = True
        self.correct_third_axis_for_tilt = False
        self._save_positions = True

        # Additional parameter initialisation for 3D step scan measurements
        self._3D_use_maximal_resolution = False
        self._3D_measurement = False
        if self._ao_channel != None:
            if self._ao_channel in self._analogue_output_device._analogue_output_channels:
                self._ao_output = True
            else:
                self._ao_output = False
        else:
            self._ao_output = False
        self.smoothing = True  # defines if smoothing at beginning and end of ramp should be done to protect piezo
        self.ramp = self._3D_generate_voltage_ramp(self.start_voltage_3D, self.end_voltage_3D)
        self._ramp_length = len(self.ramp)

        self._current_output_voltage = 0.0

        self._clock_frequency_3D = self.axis_class[self._first_scan_axis].step_freq * self._ramp_length
        self._initalize_data_arrays_3D_stepper()

        # Step values definitions

        # Sets connections between signals and functions
        self.signal_step_lines_next.connect(self._step_line, QtCore.Qt.QueuedConnection)
        self.signal_start_stepping.connect(self.start_stepper, QtCore.Qt.QueuedConnection)
        self.signal_start_3D_stepping.connect(self._start_3D_step_scan, QtCore.Qt.QueuedConnection)
        self.signal_continue_stepping.connect(self.continue_stepper, QtCore.Qt.QueuedConnection)
        self.signal_sort_count_data.connect(self.sort_counted_data, QtCore.Qt.DirectConnection)
        self.signal_sort_count_data_3D.connect(self.sort_3D_count_data, QtCore.Qt.DirectConnection)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        pass
        # self.switch_hardware(False)  # restarts NIDAQ
        # self.switch_hardware(True)
        # Todo: This method needs to be implemented

    ########################### Stepper Counter Control Methods##################################

    def switch_hardware(self, to_on=False):
        """ Switches the Hardware off or on.

        @param to_on: True switches on, False switched off

        @return int: error code (0:OK, -1:error)
        """
        if to_on:
            return self._counting_device.activation()
        else:
            return self._counting_device.reset_hardware()

    ########################### Stepper Hardware Control Methods##################################

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = int(clock_frequency)
        # checks if stepper is still running
        if self.module_state() == 'locked':
            return -1
        else:
            return 0

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

    ################################# Stepper Position Control Methods #######################################

    def calculate_precision_feedback(self, axis_name):
        """Calculates the position feedback devices precision for a given axis

        @param str axis_name: The name of the axis for which the precision is to be calculated

        @return List(float): precision of the feedback device in (volt, position)  (-1.0 for error)
        """
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1

        voltage_range = self.axis_class[axis_name].voltage_range

        # the NIDAQ has a resolution of res and only use 95% of the range giving the following voltage resolution.
        # If any other device might be used one day this needs to be passed as a variable
        precision_voltage = ((voltage_range[1] - voltage_range[0]) / (
                2 ** self._position_feedback_device.get_analogue_resolution())) * 1.05
        precision_voltage = float(truncate(precision_voltage, 6))
        # Todo: the position voltage should also be calculated depending on the readout and the value given by the
        # stepper. This is only a short time solution
        precision_position = 2e-4
        return precision_voltage, precision_position

    def get_feedback_voltage_range(self, axis_name):
        """Gets the voltage range of the position feedback device that can be converted to positions

        @axis_name The axis for which the voltage range is retrieved

        @ return list: min and max possible voltage in feedback for given axis"""
        return self._position_feedback_device._ai_voltage_range[axis_name]

    def get_position(self, axes, measurement_repetitions=100, clock_freq=1000):
        """Measures the current position of the hardware axes of the stepper.
        It needs a free clock of the measurement device.

        @ List(str) axes: List of strings for which the hardware positions are to be measured
        @ int measurement_repetitions: The amount of measurements over which should be taken and averaged over for each
                                        axis to increase measurement accuracy. Default 1000
        @ float clock_freq: The frequency with which the multiple measurements to increase accuracy should be acquired.
                            This should be chosen depending on the eigenfrequencies of the system and the maximal time
                            allowed for acquisition. Default 1000.

        @ return List (float) : positions the hardware in mm ordered by the axes ordering or error value [-1]
        """
        # test if hardware has absolute position reading
        if not self.axis_class[axes[0]].closed_loop:
            self.log.info(
                "This method can not be used on this hardware and these axis as the hardware has not position feedback")
            return [-1]

        # check passed axes value
        if not isinstance(axes, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('An empty list of axes was given.')
            return [-1]

        if self._position_feedback_device.set_up_analogue_voltage_reader_clock(axes[0], clock_frequency=clock_freq) < 0:
            return [-1]
        # read voltages from resistive read out for position feedback
        if self._position_feedback_device.set_up_analogue_voltage_reader_scanner(
                measurement_repetitions, axes[0]) < 0:
            return [-1]
        try:
            self._position_feedback_device.module_state.lock()
        except:
            self.log.warning("Position feedback device is already in use for another task")
            self._position_feedback_device.close_analogue_voltage_reader(axes[0])
            return -1
        # if more than one axis is read add additional readout channels
        # Todo: only checks if first axis is closed loop and not other ones. Needs to be changed
        if len(axes) > 1:
            if 0 > self._position_feedback_device.add_analogue_reader_channel_to_measurement(axes[0], axes[1:]):
                self._position_feedback_device.module_state.unlock()
                self._position_feedback_device.close_analogue_voltage_reader(axes[0])
                return [-1]
        self._position_feedback_device.start_analogue_voltage_reader(axes[0], True)
        voltage_result = self._position_feedback_device.get_analogue_voltage_reader(axes)
        self._position_feedback_device.module_state.unlock()
        # close position feedback reader
        if 0 > self._position_feedback_device.close_analogue_voltage_reader(axes[0]):
            self.log.error("It was not possible to close the analog voltage reader")
            return [-1]
        if 0 > self._position_feedback_device.close_analogue_voltage_reader_clock(axes[0]):
            return [-1]
        if voltage_result[1] == 0:
            self.log.warning("Reading the voltage for position feedback failed")
            return [-1]

        # convert voltage to position
        position_result = []
        voltages = np.split(voltage_result[0], len(axes))
        for counter in range(len(axes)):
            average_voltage = np.sum(voltages[counter]) / measurement_repetitions
            position = self.convert_voltage_to_position(axes[counter], average_voltage)
            position_result.append(position)
            self.axis_class[axes[counter]].absolute_position = position

        return position_result

    def convert_position_to_voltage(self, axis_name, position):
        """Converts a position to a voltage for a resistive readout of the axis

        @param str axis_name: The axis for which the voltage is to be converted to a position
        @param float position: The position that is to be converted into a voltage

        @return float: voltage (rounded), error for -1.0
        """
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1
        if not isinstance(position, (float, int)):
            type_variable = type(position)
            self.log.error(
                "A wrong variable type was passed. The position must be an integer or float but a %s was given",
                type_variable)
            return -1.0

        voltage_range = self.axis_class[axis_name].voltage_range
        step_range = self.axis_class[axis_name].step_range
        if not in_range(position, step_range[0], step_range[1]):
            self.log.warning(
                "The position (%s) you are trying to convert lies without the physical range of your axis (%s)",
                position, step_range)

        v_range = voltage_range[1] - voltage_range[0]
        s_range = step_range[1] - step_range[0]
        result = ((position - step_range[0]) * v_range / s_range) + voltage_range[0]

        precision = self.axis_class[axis_name].feedback_precision_volt
        # adjust result to possible resolution of analog_input
        return int(result / precision) * precision

    def convert_voltage_to_position(self, axis_name, voltage):
        """Converts a voltage from a resistive readout into a position of the axis

        @param str axis_name: The axis for which the voltage is to be converted to a position
        @param float voltage: The voltage that is to be converted into a position
        @return float: position (in rounded to the fourth digit), error for -1.0
        """
        if not isinstance(voltage, (float, int)):
            type_variable = type(voltage)
            self.log.error(
                "A wrong variable type was passed. The voltage must be an integer or float but a %s was given",
                type_variable)
            return -1.0
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1

        voltage_range = self.axis_class[axis_name].voltage_range
        step_range = self.axis_class[axis_name].step_range
        if not in_range(voltage, voltage_range[0], voltage_range[1]):
            self.log.warning(
                "The voltage (%s) you are trying to convert lies without the physical range (%s) of your axis (%s)",
                voltage, voltage_range, axis_name)

        v_range = voltage_range[1] - voltage_range[0]
        s_range = step_range[1] - step_range[0]
        result = ((voltage - voltage_range[0]) * s_range / v_range) + step_range[0]
        # the precision of readout of the attocubes so far is 200nn (4th digit).
        # Todo: add this precision to config (attocube)
        result = truncate(result, 4)
        return result

    def convert_voltage_to_position_for_image(self):
        # convert voltage to position for all position of a measured image
        if self.map_scan_position:
            self.full_image = np.zeros(
                (self._steps_scan_second_line, self._steps_scan_first_line, 3 + self._ai_scanner))
            if not self._fast_scan:
                self.full_image_back = np.zeros(
                    (self._steps_scan_second_line, self._steps_scan_first_line, 3 + self._ai_scanner))
            for i in range(self._steps_scan_first_line):
                for j in range(self._step_counter):
                    self.full_image[j, i, 0] = self.convert_voltage_to_position(self._first_scan_axis,
                                                                                self.image_raw[j, i, 0])
                    self.full_image[j, i, 1] = self.convert_voltage_to_position(self._second_scan_axis,
                                                                                self.image_raw[j, i, 1])
                    if not self._fast_scan:
                        self.full_image_back[j, i, 0] = self.convert_voltage_to_position(self._first_scan_axis,
                                                                                         self.image_raw_back[j, i, 0])
                        self.full_image_back[j, i, 1] = self.convert_voltage_to_position(self._second_scan_axis,
                                                                                         self.image_raw_back[j, i, 1])
            for n, ch in enumerate(self.get_counter_count_channels()):
                self.full_image[:, :, 2 + n] = self.image_raw[:, :, 2 + n]
                if not self._fast_scan:
                    self.full_image_back[:, :, 2 + n] = self.image_raw_back[:, :, 2 + n]

    def smooth_out_position_data(self):
        """Smooths out noise of position feedback using gaussian filter and averaging.

        """
        # Replace maybe already existing smoothed data with unsmoothed full data set to increase robustness
        self.full_image_smoothed = self.full_image
        self.full_image_back_smoothed = self.full_image_back

        # first axes smoothing using gaussian smoothing filter
        for i in range(self._steps_scan_second_line):
            self.full_image_smoothed[i, :, 0] = ndimage.filters.gaussian_filter(
                self.full_image[i, :, 0], self._gaussian_smoothing_parameter)
            if not self._fast_scan:
                self.full_image_back_smoothed[i, :, 0] = ndimage.filters.gaussian_filter(
                    self.full_image_back[i, :, 0], self._gaussian_smoothing_parameter)

        # second axis smoothing
        # Todo: If possible do gaussian fitting of data, as this is more accurate than mean
        average = []
        average_back = []
        ones_array = np.ones(self._steps_scan_first_line)
        # average the second axis position for every scan of the first axis. It should be constant along
        # the first scan axis
        for i in range(self._steps_scan_second_line):
            average.append(norm.fit(self.full_image[i, :, 1])[0])
            if not self._fast_scan:
                average_back.append(np.mean(self.full_image_back[i, :, 1]))

        # smooth data out along second axis with gaussian filter
        smoothed_average = ndimage.filters.gaussian_filter(average, self._gaussian_smoothing_parameter)
        if not self._fast_scan:
            smoothed_average_back = ndimage.filters.gaussian_filter(average_back, self._gaussian_smoothing_parameter)

        # generate new data of second axis along first axis and fill array
        for i in range(self._steps_scan_second_line):
            self.full_image_smoothed[i, :, 1] = ones_array * smoothed_average[i]
            if not self._fast_scan:
                self.full_image_back_smoothed[i, :, 1] = ones_array * smoothed_average_back[i]

    ################################# Stepper Scan Methods #######################################

    #################### 3D Stepper Scan Methods ####################
    def _start_3D_step_scan(self):
        """This starts a scanning procedure that functions like a normal scan but with the additional measurement of a
        piezo scan during each step of the attocube. For each voltage scan the measured counts and/or AI voltages will
        be recorded such that the behavior  of the sample in z can be recorded."""
        # Todo: Do we need a lock for the stepper as well?
        if not self._ao_output:
            self.log.error("It is not possible to do a 3D map if the 3rd axis analogue output does not exist.")
            return -1

        self._step_counter = 0
        self.module_state.lock()
        self._3D_measurement = True

        if self._get_scan_axes() < 0:
            return -1

        # Set 3rd axis scan resolution maximal if possible and required
        if self._3D_use_maximal_resolution:
            if self._3D_use_maximal_resolution() == -1:
                return -1

        # generate voltage ramp
        self.ramp = self._3D_generate_voltage_ramp(self.start_voltage_3D, self.end_voltage_3D)
        self._ramp_length = len(self.ramp)
        if self.ramp[0] == -11:
            self.log.error("Not possible to initialise scanner as ramp was not generated")
            return 0
        self.down_ramp = self.ramp[::-1]
        self._ramp_length = len(self.ramp)

        self._clock_frequency_3D = self.axis_class[self._first_scan_axis].step_freq * self._ramp_length

        # move piezo to desired start position to go easy on piezo
        self._current_output_voltage = self._cavitycontrol.axis_class[self._cavitycontrol.control_axis].output_voltage
        self.change_analogue_output_voltage(self.start_voltage_3D)
        self._cavitycontrol.axis_class[self._cavitycontrol.control_axis].output_voltage = self.start_voltage_3D
        # Check the parameters of the stepper device
        if self.check_axis_stepper() == -1:
            self.module_state.unlock()
            return -1

        # save starting positions
        self._start_position = []
        self._feedback_axis = []
        if self.axis_class[self._first_scan_axis].closed_loop:
            self._start_position.append(self.get_position([self._first_scan_axis])[0])
            self._feedback_axis.append(self._first_scan_axis)
        if self.axis_class[self._second_scan_axis].closed_loop:
            self._start_position.append(self.get_position([self._second_scan_axis])[0])
            self._feedback_axis.append(self._second_scan_axis)
        axis = np.setdiff1d([*self.axis], [self._first_scan_axis, self._second_scan_axis])[0]

        # check if scan positions should be saved and if it is possible
        self._ai_scan_axes = []
        if self.map_scan_position:
            if self.axis_class[self._first_scan_axis].closed_loop and self.axis_class[
                self._second_scan_axis].closed_loop:
                self._ai_scan_axes.append(self._first_scan_axis)
                self._ai_scan_axes.append(self._second_scan_axis)
            else:
                self.map_scan_position = False
                # initialise position scan
        if self._ai_scanner:
            self._ai_scan_axes.append(self._ai_counter)

        if 0 > self._initalize_measurement(steps=self._steps_scan_first_line * self._ramp_length,
                                           frequency=self._clock_frequency_3D, ai_channels=self._ai_scan_axes):
            return -1

        # Initialize data
        self._initalize_data_arrays_stepper()
        self._initalize_data_arrays_3D_stepper()
        self.initialize_image()
        self.signal_image_updated.emit()

        self.generate_file_path()
        self.signal_step_lines_next.emit(True)

    def _3D_use_maximal_resolution(self):
        """
        Sets the 3rd axis scan resolution to maximum and checks if the values to be set are feasible for the
        given hardwares

        @return int: error code (0:OK, -1:error)        """

        minV = min(self.start_voltage_3D, self.end_voltage_3D)
        maxV = max(self.start_voltage_3D, self.end_voltage_3D)
        self.scan_resolution_3D = self.calculate_resolution(
            self._feedback_device.get_analogue_resolution(), [minV, maxV])
        if self.scan_resolution_3D == -1:
            self.log.error("Calculated scan resolution not possible")
            return -1

        # Todo: Check if scan freq is still resonable.
        else:
            return 0

    def calculate_resolution(self, bit_resolution, my_range):
        """Calculates the resolution in a range for a given bit resolution

         @param str bit_resolution: the bit resolution of the channel

         @param list(float,float) my_range: the minimum and maximum of the range for which the resolution is
                                to be calculated

         @return float: resolution on the given scale  (-1.0 for error)
         """
        if not isinstance(my_range, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('Given range is no array type.')
            return -1

        precision = ((my_range[1] - my_range[0]) / (
                2 ** bit_resolution)) * 1.05
        precision = round_to_2(precision)
        return precision

    def get_analogue_voltage_range(self):
        """
        Get the maximally possible voltage range for the current analogue output axis

        @return List[minimum possible voltage , maximum possible voltage]
        """
        return self._analogue_output_device._ao_voltage_range[self._ao_channel]

    def _3D_generate_voltage_ramp(self, start_voltage, end_voltage):
        """Generate a ramp from start_voltage to end_voltage that
        satisfies the general step resolution and smoothing_steps parameters.
        Smoothing_steps=0 means that the ramp is just linear.

        @param float start_voltage: voltage at start of ramp.

        @param float end_voltage: voltage at end of ramp.

        @return  array(float): the calculated voltage ramp
        """

        voltage_range = self.get_analogue_voltage_range()

        # check if given voltages are allowed:
        if not in_range(start_voltage, voltage_range[0], voltage_range[1]):
            self.log.error("The given start voltage %s is not within the possible output voltages %s", start_voltage,
                           voltage_range)
            return [-11]
        elif not in_range(end_voltage, voltage_range[0], voltage_range[1]):
            self.log.error("The given end voltage %s is not within the possible output voltages %s", end_voltage,
                           voltage_range)
            return [-11]

        # It is much easier to calculate the smoothed ramp for just one direction (upwards),
        # and then to reverse it if a downwards ramp is required.
        v_min = min(start_voltage, end_voltage)
        v_max = max(start_voltage, end_voltage)

        if v_min == v_max:
            ramp = np.array([v_min, v_max])

        else:
            smoothing_range = self._3D_smoothing_steps + 1

            # Sanity check in case the range is too short
            # The voltage range covered while accelerating in the smoothing steps
            v_range_of_accel = sum(n * self.scan_resolution_3D / smoothing_range
                                   for n in range(0, smoothing_range)
                                   )

            # Obtain voltage bounds for the linear part of the ramp
            v_min_linear = v_min + v_range_of_accel
            v_max_linear = v_max - v_range_of_accel

            # calculate smooth ramp if needed and possible
            if self.smoothing and v_min_linear < v_max_linear:

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / self.scan_resolution_3D)
                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array([sum(n * self.scan_resolution_3D / smoothing_range
                                             for n in range(1, N)
                                             )
                                         for N in range(1, smoothing_range)
                                         ]
                                        )
                # generate parts of the smoothed ramp
                accel_part = v_min + smooth_curve
                decel_part = v_max - smooth_curve[::-1]
                # generate linear part of ramp
                linear_part = np.linspace(v_min_linear, v_max_linear, num_of_linear_steps)
                # combine different part of ramp
                ramp = np.hstack((accel_part, linear_part, decel_part))
            else:
                num_of_linear_steps = np.rint((v_max - v_min) / self.scan_resolution_3D)
                ramp = np.linspace(v_min, v_max, num_of_linear_steps)
                if v_min_linear > v_max_linear and self.smoothing:
                    # print out info for use
                    self.log.warning('Voltage ramp too short to apply the '
                                     'configured smoothing_steps. A simple linear ramp '
                                     'was created instead.')
        # Reverse if downwards ramp is required
        if end_voltage < start_voltage:
            ramp = ramp[::-1]

        return ramp

    def change_analogue_output_voltage(self, end_voltage):
        """Sets the analogue voltage for the control axis to desired voltage in a smooth step vice manner
        """

        v_range = self._analogue_output_device._ao_voltage_range[self._ao_channel]
        num_of_linear_steps = np.rint(abs((self._current_output_voltage - end_voltage)) / self.scan_resolution_3D)
        if (num_of_linear_steps == 1):
            num_of_linear_steps = 2
        ramp = np.linspace(self._current_output_voltage, end_voltage, num_of_linear_steps)
        if not in_range(end_voltage, v_range[0], v_range[1]):
            self.log.error("not possible to go to voltage %s outside of voltage range (%s)", end_voltage, v_range)
            return -1
        voltage_difference = abs(self._current_output_voltage - end_voltage)
        if voltage_difference > self.scan_resolution_3D:
            # _clock_frequency = self.maximum_clock_frequency
            _clock_frequency = 10 / self.scan_resolution_3D

            if 0 > self._analogue_output_device.set_up_analogue_output([self._ao_channel]):
                self.log.error("Setting up analogue output for scanning failed.")
                return -1

            if 0 > self._analogue_output_device.set_up_analogue_output_clock(self._ao_channel,
                                                                             clock_frequency=_clock_frequency):
                # Fixme: I do not think this is necessary. However it should be checked.
                # self.set_position('scanner')
                self.log.error("Problems setting up analogue output clock.")
                self._analogue_output_device.close_analogue_output(self._ao_channel)
                return -1

            self._analogue_output_device.configure_analogue_timing(self._ao_channel, len(ramp))

            retval3 = self._analogue_output_device.analogue_scan_line(self._ao_channel, ramp)
            try:
                retval1 = self._analogue_output_device.close_analogue_output_clock(self._ao_channel)
                retval2 = self._analogue_output_device.close_analogue_output(self._ao_channel)
            except:
                self.log.warn("Closing the Analogue scanner did not work")
            if retval3 != -1:
                self._current_output_voltage = end_voltage
            return min(retval1, retval2, retval3)
        else:
            self.log.info("The device was already at required output voltage")
            return 0

    #################### Standart Step Scan Methods ####################

    def check_axis_stepper(self):
        # Check the parameters of the stepper device
        freq_status = self.axis_class[self._first_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.module_state.unlock()
            return -1
        freq_status = self.axis_class[self._second_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            return -1

        # check axis status
        if self.axis_class[self._first_scan_axis].mode != "stepping":
            axis_status1 = self.axis_class[self._first_scan_axis].set_mode_stepping()
        else:
            axis_status1 = self.axis_class[self._first_scan_axis]._check_mode()
        if self.axis_class[self._second_scan_axis].mode != "stepping":
            axis_status2 = self.axis_class[self._second_scan_axis].set_mode_stepping()
        else:
            axis_status2 = self.axis_class[self._second_scan_axis]._check_mode()
        # Todo: This is a dirty fix!!!
        if self.axis_class["z"].mode != "stepping":
            axis_status3 = self.axis_class["z"].set_mode_stepping()
        else:
            axis_status3 = self.axis_class["z"]._check_mode()
        if axis_status1 < 0 or axis_status2 < 0 or axis_status3 < 0:
            # Todo: is this really sensible here?
            self.axis_class[self._first_scan_axis].set_mode_ground()
            self.axis_class[self._second_scan_axis].set_mode_ground()
            # self.module_state.unlock()
            # self.kill_counter()
            return -1

        return 0

    def set_scan_axes(self, scan_axes):
        """"Sets the step scan axes for the stepper to the given direction

        @param str scan_axes: The axes combination(of two exiting axes) along which the stepper should scan
        @return int: error code (0:OK, -1:error)
        """
        if len(scan_axes) != 2:
            self.log.error(
                "A wrong number ({}) of scan axis was given. \n The program needs 2 axes".format(
                    len(self.scan_axes)))
            return -1

        if not isinstance(scan_axes, str):
            self.log.error("The step axes must be strings")
            return -1

        for axis in scan_axes:
            if axis not in self.axis_class.keys():
                self.log.error("The specified scan axis % is not a stepper axis", axis)
                return -1
        self._scan_axes = scan_axes
        return 0

    def _get_scan_axes(self):
        """Checks the current scan axes and initialises the step scan values accordingly

        @return int: error code (0:OK, -1:error)
        """
        if len(self._scan_axes) != 2:
            self.log.error(
                "A wrong number ({}) of scan axis was given. \n The program needs 2 axes".format(
                    len(self._scan_axes)))
            return -1

        a, b = self._scan_axes[0], self._scan_axes[1]
        if a in self.axis_class.keys() and b in self.axis_class.keys():
            if self._inverted_scan:
                self._first_scan_axis = b
                self._second_scan_axis = a
                self._steps_scan_first_line = self.axis_class[b].steps_direction
                self._steps_scan_second_line = self.axis_class[a].steps_direction
            else:
                self._first_scan_axis = a
                self._second_scan_axis = b
                self._steps_scan_first_line = self.axis_class[a].steps_direction
                self._steps_scan_second_line = self.axis_class[b].steps_direction
        else:
            self.log.error(
                "One of the chosen axes {} are not defined for the stepper hardware.".format(
                    self._scan_axes))
            self.module_state.unlock()
            return -1

        return 0

    def _initalize_measurement(self, steps, frequency, ai_channels):
        """Initializes everything but the stepper for a step scan measurement

        @param int steps: the steps that are to be counted/scanned during one part of the measurement
        @param float frequency:the frequency with which the data is to be acquired/generated during
                                one part of the measurement
        @param list(str) ai_channels: the analogue input channels used during the measurement,
                                        eg. analogue input counters

        @return int: error code (0:OK, -1:error)
        """
        # initialize counting device
        clock_status = self._counting_device.set_up_finite_counter_clock(
            clock_frequency=frequency)
        if clock_status < 0:
            self.module_state.unlock()
            return -1
        # Todo: The connection to the GUI amount of samples needs to be made
        # maybe a value given by the function needs to be implemented here
        scanner_status = self._counting_device.set_up_finite_counter(steps)
        if scanner_status < 0:
            # self._counting_device.close_finite_counter_clock()
            # elf._counting_device.module_state.unlock()
            self.module_state.unlock()
            self.stopRequested = True
            return -1

        # setup analogue input if existing
        if len(ai_channels) > 0:
            if 0 > self._position_feedback_device.add_clock_task_to_channel("Scanner_clock", ai_channels):
                self.stopRequested = True
            elif 0 > self._position_feedback_device.set_up_analogue_voltage_reader_scanner(
                    steps, ai_channels[0]):
                self.stopRequested = True
            else:
                if len(ai_channels) > 1:
                    if 0 > self._position_feedback_device.add_analogue_reader_channel_to_measurement(
                            ai_channels[0], self._ai_scan_axes[1:]):
                        self.stopRequested = True

        # setup analogue output if 3rd axis is scanned as well
        if self._3D_measurement:
            if 0 > self._analogue_output_device.set_up_analogue_output([self._ao_channel]):
                self.log.error("Problems setting up analogue out put for 3D step scan on channel (%s)",
                               self._ao_channel)
                self.stopRequested = True

            if 0 > self._analogue_output_device.add_clock_task_to_channel("Scanner_clock", [self._ao_channel]):
                self.log.error("Problems setting up analogue output clock.")
                self.stopRequested = True

            if 0 > self._analogue_output_device.configure_analogue_timing(self._ao_channel, steps):
                self.log.error("Not possible to set appropriate timing for analogue scan.")
                self._output_device.close_analogue_output(self._ao_channel)
                self.stopRequested = True

        if self.stopRequested:
            return -1
        return 0

    def start_stepper(self):
        """Starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """
        # Todo: Do we need a lock for the stepper as well?
        self._step_counter = 0
        self.module_state.lock()

        if self._get_scan_axes() < 0:
            return -1

        # Check the parameters of the stepper device
        if self.check_axis_stepper() == -1:
            self.module_state.unlock()
            return -1

        # save starting positions
        self._feedback_axis = []
        self._start_position = []
        if self.axis_class[self._first_scan_axis].closed_loop:
            self._start_position.append(self.get_position([self._first_scan_axis])[0])
            self._feedback_axis.append(self._first_scan_axis)
        if self.axis_class[self._second_scan_axis].closed_loop:
            self._start_position.append(self.get_position([self._second_scan_axis])[0])
            self._feedback_axis.append(self._second_scan_axis)
        axis = np.setdiff1d([*self.axis], [self._first_scan_axis, self._second_scan_axis])[0]

        # check if scan positions should be saved and if it is possible
        self._ai_scan_axes = []
        if self.map_scan_position:
            if self.axis_class[self._first_scan_axis].closed_loop and self.axis_class[
                self._second_scan_axis].closed_loop:
                self._ai_scan_axes.append(self._first_scan_axis)
                self._ai_scan_axes.append(self._second_scan_axis)
            else:
                self.map_scan_position = False
                # initialise position scan
        if self._ai_scanner:
            self._ai_scan_axes.append(self._ai_counter)

        if 0 > self._initalize_measurement(steps=self._steps_scan_first_line,
                                           frequency=self.axis_class[self._first_scan_axis].step_freq, ai_channels=
                                           self._ai_scan_axes):
            return -1

        self._initalize_data_arrays_stepper()
        self.initialize_image()
        self.signal_image_updated.emit()

        self._3D_measurement = False
        self.generate_file_path()

        self.signal_step_lines_next.emit(True)

    def stop_stepper(self):
        """"Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        # Todo: Make sure attocube axis are set back to ground if deemed sensible
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        self.signal_stop_stepping.emit()
        return 0

    def continue_stepper(self):
        """Continue the stepping procedure

        @return int: error code (0:OK, -1:error)
        """
        self.module_state.lock()
        # Check the parameters of the stepper device
        freq_status = self.axis_class[self._first_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.module_state.unlock()
            return -1
        freq_status = self.axis_class[self._first_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.module_state.unlock()
            return -1

        pass

    def move_to_position(self, position, accuracy=None):
        """Moving the stepping device (approximately) to the desired new position from the GUI.

        @param dict position: Dictionary {axis_name, new_position}. optimisation_accuracy
                                is the lowest first accuracy the algorithm will use for the first optimisation steps.
                                Choosing this big makes the algorithm faster, small makes it move less if new position
                                is close to old one
        @param int accuracy: describes the maximum amount of steps made in one movement to reach desired new position.
                                Default None

        @return int: error code (0:OK, -1:error)
        """
        if accuracy is not None:
            if not isinstance(accuracy, int) or accuracy <= 0:
                self.log.error("The optimisation accuracy must be an integer >0.\n The value passed was %s", accuracy)
        else:
            # Todo: generate a variable that makes accuracy a class variable
            # that is to be set here adn that can be changed from the GUI
            accuracy = 1

        # check passed axes value
        if not isinstance(position, dict):
            self.log.error('A wrong variable type for position was given. It must be a dictionary')
            return -1

        return_value = 0
        for key, value in position.items():
            if key not in self.axis_class.keys():
                self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", key)
                continue
            # test if hardware has absolute position reading
            if not self.axis_class[key].closed_loop:
                self.log.info(
                    "This method can not be used on this hardware and these axis as the hardware has not "
                    "position feedback")
                continue
            if not in_range(value, self.axis_class[key].step_range[0], self.axis_class[key].step_range[1]):
                self.log.error("%s lies without the steppers range for axis %s", value, key)
                continue

            if abs(self.axis_class[key].absolute_position - value) >= self.axis_class[
                key].feedback_precision_position:  # check if position differs from actual hardware position

                # Todo: Maybe it makes sense to open option to change freq and amplitude
                # actually move to the wanted position using an optimisation algorithm
                if 0 > self.optimize_position(key, value, accuracy):
                    self.log.warning("Moving attocube to desired position failed for axis %s.", key)
                    return_value = -1

        # Todo: implement moving for hardware without feedback with amount of steps:
        # self.log.info("Movement of attocubes to an absolute position no possible for steppers.\n"
        #              "The position moved to is the given of amount of steps, not a physical "
        #              "given range away")
        return return_value

    def optimize_position(self, axis_name, position, steps=1):
        """ Algorithms that uses an searching algorithm to move to the given position

        @param axis_name: the name of the axis for which the position is to be changed
        @param position: The position the attocube axis should be moved
        @param int steps: The maximum used amount of steps to reach the desired position in one movement
        @return int: error code (0:OK, -1:error)
        """

        # check if hardware can do optimisation
        if not self.axis_class[axis_name].closed_loop:
            self.log.warning(
                "This algorithm only works with position feedback. Please use another algorithm to get to "
                "the desired position")
            return -1

        # check feasibility of passed values
        if not isinstance(steps, int) or steps <= 0:
            self.log.error("The movement accuracy steps has to be given as an integer!")
            return -1
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1
        if not in_range(position, self.axis_class[axis_name].step_range[0], self.axis_class[axis_name].step_range[1]):
            self.log.error("%s lies without the steppers range", position)
            return -1

        # check if optimisation is necessary
        precision = self.axis_class[axis_name].feedback_precision_position
        if abs(self.axis_class[axis_name].absolute_position - position) <= precision:
            return 0

        direction = self.axis_class[axis_name].absolute_position < position  # find movement direction
        # check freq and amplitude
        status_freq = self.axis_class[axis_name]._check_freq()
        status_amp = self.axis_class[axis_name]._check_amplitude()
        status_mode = self.axis_class[axis_name].set_mode_stepping()
        if status_amp + status_freq + status_mode < 0:
            return -1

        # Initialise position readout:
        if self._position_feedback_device.set_up_analogue_voltage_reader(axis_name) < 0:
            return -1
        self._position_feedback_device.module_state.lock()
        # todo: kill counter
        # --- Do optimisation ---
        # convert to hardware voltage for faster execution.
        desired_voltage = self.convert_position_to_voltage(axis_name, position)
        counter = 0

        # Todo: distance feature
        # distance = 0 This will be necessary to take care of the fact, that the stepper moves not equal steps sizes in
        # up and down direction (Feature for later)
        sleep = steps / self.axis_class[axis_name].step_freq
        while counter < 20:  # do max 5 optimisation cycles per accuracy step
            # move attocubes with given accuracy(steps)
            if 0 > self._stepping_device.move_attocube(axis_name, True, direction, steps=steps):
                self.log.error("Moving the attocubes failed")
                self._position_feedback_device.module_state.unlock()
                self._position_feedback_device.close_analogue_voltage_reader(axis_name)
                return -1
            time.sleep(sleep)
            # compare new position to desired one
            result = self._position_feedback_device.get_analogue_voltage_reader([axis_name])
            if result[1] == 0:
                self._position_feedback_device.module_state.unlock()
                self._position_feedback_device.close_analogue_voltage_reader(axis_name)
                self.log.error("reading the axis voltage failed")
                return -1
            voltage_result = result[0][0]

            # update position and leave algorithm if position was reached.
            if abs(voltage_result - desired_voltage) < precision:  # comparing floats
                error = self.convert_voltage_to_position(axis_name, voltage_result)
                if error != -1.0:
                    self.axis_class[axis_name].absolute_position = error
                    error = 0
                else:
                    error = -1
                self._position_feedback_device.close_analogue_voltage_reader(axis_name)
                self._position_feedback_device.module_state.unlock()
                return error
            # check if direction movement has to changed
            if direction:
                if voltage_result < desired_voltage:
                    continue
            else:
                if voltage_result > desired_voltage:
                    continue
            # half the step size to go back
            if steps > 1:
                steps = int(steps / 2)
                sleep = steps / self.axis_class[axis_name].step_freq
            else:
                counter += 1
            direction = not direction

        position_result = self.convert_voltage_to_position(axis_name, voltage_result)
        self.log.info("The best position that could be reached with the given freq. and voltage of the stepper has"
                      " been reached. \n It is %s, while the desired value was %s. If a higher accuracy is desired"
                      " please reduce the step voltage and redo the process.", position_result, position)
        self.axis_class[axis_name].absolute_position = position_result
        self._position_feedback_device.module_state.unlock()
        self._position_feedback_device.close_analogue_voltage_reader(axis_name)
        return 0

    def _step_line(self, direction):
        """Stepping a line

        @param bool direction: the direction in which the previous line was scanned

        @return bool: If true scan was in up direction, if false scan was in down direction
        """
        # Todo: Make sure how to implement the thread locking here correctly.

        # Todo: Think about the question whether we actually step the same amount of steps as we
        # count or is we might be off by one, as we are not counting when moving up on in "y"

        # If the stepping measurement is not running do nothing
        if self.module_state() != 'locked':
            return

            # stop stepping
        if self.stopRequested:
            with self.threadlock:
                self.kill_counter()
                if self.map_scan_position:
                    self._position_feedback_device.close_analogue_voltage_reader(self._first_scan_axis)
                    self.convert_voltage_to_position_for_image()
                elif self._ai_scanner:
                    self._position_feedback_device.close_analogue_voltage_reader(self._ai_counter)

                if self._3D_measurement:
                    self._current_output_voltage = self.start_voltage_3D
                    self._analogue_output_device.close_analogue_output(self._ao_channel)
                    self.change_analogue_output_voltage(0.0)
                    self._cavitycontrol.axis_class[self._cavitycontrol.control_axis].output_voltage = 0.0
                # it is not necessary to stop the analogue input reader. It is closed after each line scan
                self.stopRequested = False
                self.module_state.unlock()
                # self._stepping_device.module_state.unlock()
                self.update_image_data_line(self._step_counter - 1)
                self.smooth_out_position_data()
                self.signal_image_updated.emit()
                # add new history entry
                # new_history = ConfocalHistoryEntry(self)
                # new_history.snapshot(self)
                # self.history.append(new_history)
                # if len(self.history) > self.max_history_length:
                #    self.history.pop(0)
                # self.history_index = len(self.history) - 1
                self.signal_step_scan_stopped.emit()
                self.log.info("Stepping stopped successfully")
                self.log.info("The stepper stepped %s lines", self._step_counter)

                return
        # self.log.info("start stepping,line %s time: %s", self._step_counter,
        #              datetime.datetime.now().strftime('%M-%S-%f'))
        # move and count
        new_counts = self._step_and_count(self._first_scan_axis, self._second_scan_axis, direction,
                                          steps=self._steps_scan_first_line)
        # self.log.info("acquired data stepping, line %s, time: %s", self._step_counter,
        #              datetime.datetime.now().strftime('%M-%S-%f'))
        data_counter = 0
        if type(new_counts[data_counter]) == int:
            self.stopRequested = True
            self.signal_step_lines_next.emit(direction)
            return
        # check if stepping worked
        if new_counts[data_counter][0] == -1:
            self.stopRequested = True
            self.signal_step_lines_next.emit(direction)
            data_counter += 1
            return
        if not self._fast_scan:
            if new_counts[1][0] == -1:
                self.stopRequested = True
                self.signal_step_lines_next.emit(direction)
                data_counter += 1
                return

        if self.map_scan_position or self._ai_scanner:
            if new_counts[data_counter][0] == -1:
                self.stopRequested = True
                self.signal_step_lines_next.emit(direction)
                data_counter += 1
                return
            if not self._fast_scan:
                if new_counts[data_counter][0] == -1:
                    self.stopRequested = True
                    self.signal_step_lines_next.emit(direction)
                    return

        direction = not direction  # invert direction
        if self._3D_measurement:
            self.signal_sort_count_data_3D.emit(new_counts, self._step_counter)
        else:
            self.signal_sort_count_data.emit(new_counts, self._step_counter)

        if self.axis_class[self._first_scan_axis].closed_loop:
            steps = self._steps_scan_first_line
            frequency = self.axis_class[self._first_scan_axis].step_freq
            if self._3D_measurement:
                steps = steps * self._ramp_length
                frequency = self._clock_frequency_3D
            self.go_to_start_position(steps, clock_frequency=frequency)

        # do z position correction
        # Todo: This is still very crude
        if self.correct_third_axis_for_tilt:
            if self._step_counter % self._lines_correct_3rd_axis == 0:
                self._stepping_device.move_attocube("z", True, self._3rd_direction_correction, steps=1)
        self._step_counter += 1

        # check if at end of scan
        if self._step_counter > self._steps_scan_second_line - 1:
            self.stopRequested = True
            self.log.info("Stepping scan at end position")
        # self.log.info("new line %s time: %s", self._step_counter, datetime.datetime.now().strftime('%M-%S-%f'))

        self.signal_step_lines_next.emit(direction)

    def _step_and_count(self, main_axis, second_axis, direction=True, steps=1):
        """
        @param str main_axis: name of the fast axis of the step scan
        @param str second_axis: name of the slow axis of the step scan
        @param bool direction: direction of stepping (up: True or down: False)
        @param int steps: amount of steps, default 1
        @return np.array: acquired data in counts/s or error value [-1],[]
        """
        # added, that the stepper now scans back and forth
        # Todo: This needs to optional

        # check axis
        if main_axis in self.axis_class.keys():
            if second_axis in self.axis_class.keys():
                if self._stepping_device.move_attocube(main_axis, True, True, steps=steps - 1) < 0:
                    self.log.error("moving of attocube failed")
                    # Todo: repair return values
                    return [-1], []
                if self._counting_device.start_finite_counter(start_clock=not self._3D_measurement) < 0:
                    self.log.error("Starting the counter failed")
                    return [-1], []
                if len(self._ai_scan_axes) > 0:
                    if 0 > self._position_feedback_device.start_analogue_voltage_reader(self._ai_scan_axes[0],
                                                                                        start_clock=False):
                        self.log.error("Starting the counter failed")
                        return [-1], []
                if self._3D_measurement:
                    self._analogue_output_device.analogue_scan_line(self._ao_channel, self._output_voltages_array)

                # move on line up
                # if self._stepping_device.move_attocube(secondaxis, True, True, 1) < 0:
                #    self.log.error("moving of attocube failed")
                #    return -1

                # Todo: Check if there is a better way than this to adjust for the fact that a stepping
                # direction change is necessary for the last count. Maybe different method arrangement
                # sensible
                # self.log.info("moved up,line %s time: %s", self._step_counter,
                #              datetime.datetime.now().strftime('%M-%S-%f'))
                # time.sleep(
                #    steps / self.axis_class[main_axis].step_freq)  # wait till stepping finished for readout
                result = self._counting_device.get_finite_counts()
                if self.map_scan_position and self._ai_scanner:
                    analog_result = self._position_feedback_device.get_analogue_voltage_reader(
                        [self._first_scan_axis, self._second_scan_axis, self._ai_counter])
                elif self.map_scan_position:
                    analog_result = self._position_feedback_device.get_analogue_voltage_reader(
                        [self._first_scan_axis, self._second_scan_axis])
                elif self._ai_scanner:
                    analog_result = self._position_feedback_device.get_analogue_voltage_reader(
                        [self._ai_counter])
                # self.log.info("read data up,line %s time: %s", self._step_counter,
                #              datetime.datetime.now().strftime('%M-%S-%f'))
                retval = 0
                a = self._counting_device.stop_finite_counter()
                if self.map_scan_position:
                    if 0 > self._position_feedback_device.stop_analogue_voltage_reader(self._first_scan_axis):
                        self.log.error("Stopping the analog input failed")
                        retval = [-1], []
                        return retval
                elif self._ai_scanner:
                    if 0 > self._position_feedback_device.stop_analogue_voltage_reader(self._ai_counter):
                        self.log.error("Stopping the analog input counter failed")
                        retval = [-1], []
                        return retval

                if result[0][0] == [-1]:
                    self.log.error("The readout of the counter failed")
                    retval = [-1], []
                    return retval
                elif self.map_scan_position or self._ai_scanner:
                    if analog_result[0][0] == [-1]:
                        self.log.error("The readout of the analog reader failed")
                        retval = [-1], []
                        return retval
                elif result[1] != steps:
                    self.log.error("A different amount of data than necessary was returned.\n "
                                   "Received {} instead of {} bins with counts ".format(result[1], steps))
                    retval = [-1], []
                    return [-1], []
                elif a < 0:
                    retval = [-1], []
                    self.log.error("Stopping the counter failed")
                    return retval
                # else:
                #   retval = result[0]
                if not self._fast_scan:
                    result_back, analog_result_back = self.step_back_line(main_axis, second_axis, steps)
                    if type(result_back[0]) == int:
                        return [-1], []
                    steps_offset = round(self._off_set_x * steps)
                    if steps_offset > 0:
                        if self._stepping_device.move_attocube(main_axis, True, self._off_set_direction,
                                                               steps=steps_offset) < 0:
                            self.log.error("moving of attocube failed (offset)")
                            return [-1], []
                        else:
                            time.sleep(steps_offset / self.axis_class[self._first_scan_axis].step_freq)
                    else:
                        if self._step_counter == 0:
                            self.log.warning("No offset used.")
                    if self.map_scan_position or self._ai_scanner:
                        return result[0], result_back[0], analog_result[0], analog_result_back[0]
                    return result[0], result_back[0]
                if self._stepping_device.move_attocube(second_axis, True, True, 1) < 0:
                    self.log.error("moving of attocube failed")
                    return [-1], []

                if self.map_scan_position or self._ai_scanner:
                    return result[0], analog_result[0]
                else:
                    return result[0]
            else:
                self.log.error(
                    "second axis %s in not  an axis %s of the stepper", second_axis, self.axis)
                return [-1], []

        else:
            self.log.error("main axis %s is not an axis %s of the stepper", main_axis, self.axis)
            return [-1], []

    def step_back_line(self, main_axis, second_axis, steps):
        # redo this now (not forever) in the other direction
        if self._stepping_device.move_attocube(main_axis, True, False, steps=steps - 1) < 0:
            self.log.error("moving of attocube failed")
            return [-1], []
        if self._counting_device.start_finite_counter(start_clock=not self._3D_measurement) < 0:
            self.log.error("Starting the counter failed")
            return [-1], []
        if len(self._ai_scan_axes) > 0:
            if 0 > self._position_feedback_device.start_analogue_voltage_reader(self._ai_scan_axes[0],
                                                                                start_clock=False):
                self.log.error("Starting the counter failed")
                return [-1], []

        if self._3D_measurement:
            if 0 > self._analogue_output_device.analogue_scan_line(self._ao_channel, self._output_voltages_array[::-1]):
                self.log.error("Starting the analogue line scan failed")
                return [-1], []

        # time.sleep(steps * 1.7 / self.axis_class[main_axis].step_freq)
        # self.log.info("moved down,line %s time: %s", self._step_counter,
        #              datetime.datetime.now().strftime('%M-%S-%f'))
        result_back = self._counting_device.get_finite_counts()
        if self.map_scan_position and self._ai_scanner:
            analog_result_back = self._position_feedback_device.get_analogue_voltage_reader(
                [self._first_scan_axis, self._second_scan_axis, self._ai_counter])
        elif self.map_scan_position:
            analog_result_back = self._position_feedback_device.get_analogue_voltage_reader(
                [self._first_scan_axis, self._second_scan_axis])
        elif self._ai_scanner:
            analog_result_back = self._position_feedback_device.get_analogue_voltage_reader(
                [self._ai_counter])
        # self.log.info("read data down,line %s time: %s", self._step_counter,
        #              datetime.datetime.now().strftime('%M-%S-%f'))
        # move on line up
        if self._stepping_device.move_attocube(second_axis, True, True, 1) < 0:
            self.log.error("moving of attocube failed")
            return [-1], []

        a = self._counting_device.stop_finite_counter()
        if self.map_scan_position:
            if 0 > self._position_feedback_device.stop_analogue_voltage_reader(self._first_scan_axis):
                self.log.error("Stopping the analog input failed")
                retval = [-1], []
                return retval
        elif self._ai_scanner:
            if 0 > self._position_feedback_device.stop_analogue_voltage_reader(self._ai_counter):
                self.log.error("Stopping the analog input counter failed")
                retval = [-1], []
                return retval

        if result_back[0][0] == [-1]:
            self.log.error("The readout of the counter(2) failed")
            retval = [-1], []
            return retval
        elif self.map_scan_position or self._ai_scanner:
            if analog_result_back[0][0] == [-1]:
                self.log.error("The readout of the analog reader failed")
                retval = [-1], []
                return retval
        elif result_back[1] != steps:
            self.log.error("A different amount of data than necessary was returned(2).\n "
                           "Received {} instead of {} bins with counts ".format(result_back[1], steps))
            retval = [-1], []
            return retval
        elif a < 0:
            retval = [-1], []
            self.log.error("Stopping the counter failed (2)")
            return retval

        return result_back, analog_result_back

    def sort_counted_data(self, counts, line):
        # self.log.info("2D sorting start, line %s, time: %s", line,
        #              datetime.datetime.now().strftime('%M-%S-%f'))
        data_counter = 0
        self.stepping_raw_data[line] = counts[data_counter]
        self.save_to_npy("SPCM", line, counts[data_counter])
        data_counter += 1
        if not self._fast_scan:
            self.save_to_npy("SPCM_back", line, np.flipud(counts[data_counter]))
            self.stepping_raw_data_back[line] = np.flipud(counts[data_counter])
            data_counter += 1

        if self.map_scan_position or self._ai_counter:
            forward = np.split(counts[data_counter], 2 * self.map_scan_position + self._ai_scanner)
            if not self._fast_scan:
                backward = np.split(counts[data_counter], 2 * self.map_scan_position + self._ai_scanner)

            if self.map_scan_position:
                self.save_to_npy("scan_pos_voltages", line, forward[0:2])
                self._scan_pos_voltages[line, :, 0] = forward[0]
                self._scan_pos_voltages[line, :, 1] = forward[1]
                if not self._fast_scan:
                    self.save_to_npy("scan_pos_voltages_back", line, np.flipud(backward[0:2]))
                    self._scan_pos_voltages_back[line, :, 0] = np.flipud(backward[0])
                    self._scan_pos_voltages_back[line, :, 1] = np.flipud(backward[1])

            if self._ai_scanner:
                self.save_to_npy("APD", line, forward[-1])
                self._ai_counter_voltages[line] = forward[-1]
                if not self._fast_scan:
                    self.save_to_npy("APD_back", line, np.flipud(backward[-1]))
                    self._ai_counter_voltages_back[line] = np.flipud(backward[-1])

        # self.log.info("2D finished sorting, line %s, time: %s", line,
        #                  datetime.datetime.now().strftime('%M-%S-%f'))

        self.update_image_data_line(line)
        self.signal_image_updated.emit()

    def sort_3D_count_data(self, counts, line):
        """Divides the data acquired by a 3D scan into data packages that the program can handle"""
        # self.log.info("3D  sorting, line %s, time: %s", line,
        #              datetime.datetime.now().strftime('%M-%S-%f'))

        new_counts = []
        mean_counts = []
        length_scan = self._steps_scan_first_line
        name_save_addition = "_3D"
        data_counter = 0
        new_counts.append(np.split(counts[data_counter], length_scan))
        self.save_to_npy("SPCM" + name_save_addition, line, new_counts[data_counter])
        mean_counts.append(np.mean(new_counts[data_counter], 1))
        data_counter += 1
        if not self._fast_scan:
            new_counts.append(np.split(counts[data_counter], length_scan))
            self.save_to_npy("SPCM_back" + name_save_addition, line, np.flipud(new_counts[data_counter]))
            mean_counts.append(np.mean(new_counts[data_counter], 1))
            data_counter += 1

        forward_split = []
        backward_split = []
        if self.map_scan_position or self._ai_counter:
            forward = np.split(counts[data_counter], 2 * self.map_scan_position + self._ai_scanner)
            data_counter += 1
            if not self._fast_scan:
                backward = np.split(counts[data_counter], 2 * self.map_scan_position + self._ai_scanner)
                data_counter += 1

        for i in range(2 * self.map_scan_position + self._ai_scanner):
            forward_split.append(np.split(forward[i], length_scan))
            if not self._fast_scan:
                backward_split.append(np.split(backward[i], length_scan))

        if self.map_scan_position or self._ai_counter:
            forward_mean_counts = np.mean(forward_split, 2)
            if not self._fast_scan:
                backward_mean_counts = np.mean(backward_split, 2)
            mean_counts.append(forward_mean_counts.flatten())
            if not self._fast_scan:
                mean_counts.append(backward_mean_counts.flatten())

        # self.log.info("3D finished sorting, start saving, line %s,  time: %s", line,
        #              datetime.datetime.now().strftime('%M-%S-%f'))
        if self.map_scan_position:
            self.save_to_npy("scan_pos_voltages" + name_save_addition, line, forward_split[0:2])
            if not self._fast_scan:
                self.save_to_npy("scan_pos_voltages_back" + name_save_addition, line, np.flip(backward_split[0:2], 1))

        if self._ai_scanner:
            self.save_to_npy("APD" + name_save_addition, line, forward_split[-1])
            if not self._fast_scan:
                self.save_to_npy("APD_back" + name_save_addition, line, np.flipud(backward_split[-1]))
        self.log.info("3D finished saving, line %s,  time: %s", line,
                      datetime.datetime.now().strftime('%M-%S-%f'))
        # self.save_to_npy(forward_split)
        self.sort_counted_data(mean_counts, line)

    def go_to_start_position(self, steps, clock_frequency):
        """Moves stepper to the first position measured for the last line measured.

        @param int steps: the steps that are counted/scanned during one part of the measurement
        @param float frequency: the frequency with which the data is acquired/generated during
                                one part of the measurement
        """
        # check starting position of fast scan direction

        measurement_stopped = False
        if self.map_scan_position:
            # Todo: how is the position data saved for the backward direction?
            if not self._fast_scan:
                new_position = [self.convert_voltage_to_position(self._first_scan_axis,
                                                                 self._scan_pos_voltages_back[
                                                                     self._step_counter, 0, 0])]
            else:
                new_position = [self.convert_voltage_to_position(self._first_scan_axis,
                                                                 self._scan_pos_voltages[
                                                                     self._step_counter, -1, 0])]
            self.axis_class[self._first_scan_axis].absolute_position = new_position[0]
        else:
            if len(self._ai_scan_axes) > 0:
                self.kill_counter()
                self._position_feedback_device.close_analogue_voltage_reader(self._ai_scan_axes[0])
                if self._3D_measurement:
                    self._analogue_output_device.close_analogue_output(self._ao_channel)
                # self.change_analogue_output_voltage(0.0)
                measurement_stopped = True

            new_position = self.get_position([self._first_scan_axis], 1000, 10000)

        # check if end position differs from start position
        if abs(self._start_position[0] - new_position[0]) > self.axis_class[
            self._first_scan_axis].feedback_precision_position:
            if self._fast_scan:
                steps_res = int(self._steps_scan_second_line / 10)
                if steps_res == 0: steps_res = 3
            else:
                steps_res = int(
                    self._steps_scan_first_line * 0.03)  # 3%offset is minimum to be expected so more
            # steps would be over correcting
            # stop readout for scanning so positions can be optimised
            # Todo: Let user choose offset
            if steps_res > 0:
                if len(self._ai_scan_axes) > 0 and not measurement_stopped:
                    self.kill_counter()
                    self._position_feedback_device.close_analogue_voltage_reader(self._ai_scan_axes[0])
                    if self._3D_measurement:
                        self._analogue_output_device.close_analogue_output(self._ao_channel)
                    # self.change_analogue_output_voltage(0.0)
                    measurement_stopped = True

                # go to start position
                if self._fast_scan:
                    step_freq = self.axis_class[self._first_scan_axis].step_freq
                    if step_freq < 300:
                        self.axis_class[self._first_scan_axis].set_stepper_frequency(step_freq * 3)
                if self.optimize_position(self._first_scan_axis, self._start_position[0], steps_res) < 0:
                    self.stopRequested = True
                    self.log.warning('Optimisation of position failed. Step Scan stopped.')
                    # restart position readout for scanning
                    # the second if ensures that the analogue scanner is  s not started when
                    # the stepping scan is already finished

                if self._fast_scan:
                    self.axis_class[self._first_scan_axis].set_stepper_frequency(step_freq)

        if measurement_stopped:
            self._initalize_measurement(steps, clock_frequency, ai_channels=self._ai_scan_axes)

    def measure_end_position_during_scan(self):
        if self.map_scan_position:
            self._position_feedback_device.close_analogue_voltage_reader(self._first_scan_axis)
        position = self.get_position(self._feedback_axis, 100, 1000)
        if self.map_scan_position:
            self._position_feedback_device.set_up_analogue_voltage_reader_scanner(
                self._steps_scan_first_line, self._first_scan_axis)
            self._position_feedback_device.add_analogue_reader_channel_to_measurement(
                self._first_scan_axis, [self._second_scan_axis])
        return position

    ##################################### Acquire Data ###########################################
    def kill_counter(self):
        """Closing the counting device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._counting_device.close_finite_counter()
        except Exception as e:
            self.log.exception('Could not close the scanner.')
        try:
            self._counting_device.close_finite_counter_clock()
        except Exception as e:
            self.log.exception('Could not close the scanner clock.')
        # try:
        #            self._counting_device.module_state.unlock()
        #        except Exception as e:

        return 0

    def get_counter_count_channels(self):
        """ Get lis of counting channels from counting device.
          @return list(str): names of counter channels
        """
        ch = self._counting_device.get_scanner_count_channels()[:1]
        if self._ai_scanner:
            ch.append(self._ai_counter)
        return ch

    def get_step_counter(self):
        """Returns the current line counter of stepper

        :return: the current line number of the stepper
        """
        return self._step_counter

    ##################################### Handle Data ########################################
    def initialize_image(self):
        """Initialization of the image.

        @return int: error code (0:OK, -1:error)
        """
        self._get_scan_axes()
        image_depth = 3 + self._ai_scanner
        image_raw = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line, image_depth))
        image_raw_back = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line, image_depth))
        image_raw[:, :, 2] = self.stepping_raw_data
        if not self._fast_scan:
            image_raw_back[:, :, 2] = self.stepping_raw_data_back
        if not self.map_scan_position:
            first_positions = np.linspace(0, self._steps_scan_first_line - 1, self._steps_scan_first_line)
            second_positions = np.linspace(0, self._steps_scan_second_line - 1, self._steps_scan_second_line)
            first_position_array, second_position_array = np.meshgrid(first_positions, second_positions)
            image_raw[:, :, 1] = second_position_array
            image_raw[:, :, 0] = first_position_array
            if not self._fast_scan:
                image_raw_back[:, :, 1] = second_position_array
                image_raw_back[:, :, 0] = first_position_array
        if self._ai_scanner:
            image_raw[:, :, 3] = self._ai_counter_voltages
            if not self._fast_scan:
                image_raw_back[:, :, 3] = self._ai_counter_voltages_back

        self.image_raw = image_raw
        self.full_image = image_raw
        # for smoothed position feedback image
        self.full_image_smoothed = image_raw

        if not self._fast_scan:
            self.image_raw_back = image_raw_back
            self.full_image_back = image_raw_back
            self.full_image_back_smoothed = image_raw_back

    def _initalize_data_arrays_stepper(self):
        """
        Initialises all numpy data arrays for the current stepper settings
        """
        self.stepping_raw_data = np.zeros(
            (self._steps_scan_second_line, self._steps_scan_first_line))
        if not self._fast_scan:
            self.stepping_raw_data_back = np.zeros(
                (self._steps_scan_second_line, self._steps_scan_first_line))
        if self.map_scan_position:
            if self.axis_class[self._first_scan_axis].closed_loop and self.axis_class[
                self._second_scan_axis].closed_loop:
                self._scan_pos_voltages = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line, 2))
                if not self._fast_scan:
                    self._scan_pos_voltages_back = np.zeros(
                        (self._steps_scan_second_line, self._steps_scan_first_line, 2))

        if self._ai_scanner:
            self._ai_counter_voltages = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line))
            if not self._fast_scan:
                self._ai_counter_voltages_back = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line))

    def _initalize_data_arrays_3D_stepper(self):
        """
        Initialises all numpy data arrays for the current stepper settings
        """
        self._3D_stepping_raw_data = np.zeros(
            (self._steps_scan_second_line, self._steps_scan_first_line, self._ramp_length))
        if not self._fast_scan:
            self._3D_stepping_raw_data_back = np.zeros(
                (self._steps_scan_second_line, self._steps_scan_first_line, self._ramp_length))
        if self.map_scan_position:
            if self.axis_class[self._first_scan_axis].closed_loop and self.axis_class[
                self._second_scan_axis].closed_loop:
                self._3D_scan_pos_voltages = np.zeros(
                    (self._steps_scan_second_line, self._steps_scan_first_line, 2, self._ramp_length))
                if not self._fast_scan:
                    self._3D_scan_pos_voltages_back = np.zeros(
                        (self._steps_scan_second_line, self._steps_scan_first_line, 2, self._ramp_length))
        if self._ai_scanner:
            self._3D_ai_counter_voltages = np.zeros(
                (self._steps_scan_second_line, self._steps_scan_first_line, self._ramp_length))
            if not self._fast_scan:
                self._3D_ai_counter_voltages_back = np.zeros(
                    (self._steps_scan_second_line, self._steps_scan_first_line, self._ramp_length))

        self._output_voltages_array = np.zeros(self._steps_scan_first_line * self._ramp_length)
        for i in range(0, self._steps_scan_first_line - 1, 2):
            self._output_voltages_array[self._ramp_length * i:self._ramp_length * i + self._ramp_length] = self.ramp
            self._output_voltages_array[
            self._ramp_length + self._ramp_length * i:self._ramp_length * i + 2 * self._ramp_length] = self.ramp[::-1]

    def update_image_data(self):
        """Updates the images data
        """
        self.image_raw[:, :, 2] = self.stepping_raw_data
        if not self._fast_scan:
            self.image_raw_back[:, :, 2] = self.stepping_raw_data
        if self.map_scan_position:
            self.image_raw[:, :, :2] = self._scan_pos_voltages
            if not self._fast_scan:
                self.image_raw_back[:, :, :2] = self._scan_pos_voltages_back
        if self._ai_scanner:
            self.image_raw[:, :, 3] = self._ai_counter_voltages
            if not self._fast_scan:
                self.image_raw_back[:, :, 3] = self._ai_counter_voltages_back

    def update_image_data_line(self, line_counter):
        """

        :param line_counter:
        """
        self.image_raw[line_counter, :, 2] = self.stepping_raw_data[line_counter]
        if not self._fast_scan:
            self.image_raw_back[line_counter, :, 2] = self.stepping_raw_data_back[line_counter]
        if self.map_scan_position:
            self.image_raw[line_counter, :, :2] = self._scan_pos_voltages[line_counter]
            if not self._fast_scan:
                self.image_raw_back[line_counter, :, :2] = self._scan_pos_voltages_back[line_counter]
        if self._ai_scanner:
            self.image_raw[line_counter, :, 3] = self._ai_counter_voltages[line_counter]
            if not self._fast_scan:
                self.image_raw_back[line_counter, :, 3] = self._ai_counter_voltages_back[line_counter]

    def generate_save_parameters(self):
        # Prepare the meta data parameters (common to both saved files):
        parameters = OrderedDict()

        self._get_scan_axes()

        parameters['First Axis'] = self._first_scan_axis
        parameters['First Axis Steps'] = self._steps_scan_first_line
        parameters['First Axis Frequency'] = self.axis_class[self._first_scan_axis].step_freq
        parameters['First Axis Amplitude'] = self.axis_class[self._first_scan_axis].step_amplitude
        parameters[
            'First Axis Offset (%)'] = self._off_set_x  # Todo: this needs to be specified specifically for x
        parameters['First Axis Offset steps'] = round(
            self._off_set_x * self._steps_scan_first_line)  # Todo: this needs to be specified specifically for x
        parameters['First Axis Offset Direction'] = \
            self._first_scan_axis if self._off_set_direction else '-' + self._first_scan_axis

        parameters['Second Axis'] = self._second_scan_axis
        parameters['Second Axis Steps'] = self._steps_scan_second_line
        # Todo self._step_freq and self.step_amplitude should be named in a similar fashion
        parameters['Second Axis Frequency'] = self.axis_class[self._second_scan_axis].step_freq
        parameters['Second Axis Amplitude'] = self.axis_class[self._second_scan_axis].step_amplitude
        if self._3rd_direction_correction:
            parameters["Z correction up (attocube axis)"] = self._lines_correct_3rd_axis
        else:
            parameters["z correction down (attocube axis"] = self._lines_correct_3rd_axis
        if self._3D_measurement:
            parameters["Count frequency (Hz)"] = self._clock_frequency_3D
            parameters["Scan resolution (V/step)"] = self.scan_resolution_3D
            parameters["Start Voltage Scan (V)"] = self.start_voltage_3D
            parameters["End Voltage scan (V)"] = self.end_voltage_3D
            parameters["Points per Ramp"] = self._ramp_length
            if self.smoothing:
                parameters["Smoothing Steps"] = self._3D_smoothing_steps

        return parameters

    def save_data(self, colorscale_range=None, percentile_range=None):
        """ Save the current confocal xy data to file.

        Two files are created.  The first is the imagedata, which has a text-matrix of count values
        corresponding to the pixel matrix of the image.  Only count-values are saved here.

        The second file saves the full raw data with x, y, z, and counts at every pixel.

        A figure is also saved.

        @param: list colorscale_range (optional) The range [min, max] of the display colour scale
                    (for the figure)

        @param: list percentile_range (optional) The percentile range [min, max] of the color scale
        """
        filepath = self.filepath
        timestamp = datetime.datetime.now()

        parameters = self.generate_save_parameters()

        # prepare the full raw data in an OrderedDict:
        data = OrderedDict()
        data_back = OrderedDict()
        if self.map_scan_position and self._save_positions:
            data['x position (mm)'] = self.full_image[:, :, 0].flatten()
            data['y position (mm)'] = self.full_image[:, :, 1].flatten()
            full_data = self.full_image  # else it will be none to reduce computiation time = drawing time
            if not self._fast_scan:
                data_back['x position (mm)'] = self.full_image_back[:, :, 0].flatten()
                data_back['y position (mm)'] = self.full_image_back[:, :, 1].flatten()
                full_data_back = self.full_image_back
        else:
            data['x step'] = self.image_raw[:, :, 0].flatten()
            data['y step'] = self.image_raw[:, :, 1].flatten()
            full_data = None
            if not self._fast_scan:
                data_back['x step'] = self.image_raw_back[:, :, 0].flatten()
                data_back['y step'] = self.image_raw_back[:, :, 1].flatten()
                full_data_back = None

        for n, ch in enumerate(self.get_counter_count_channels()):
            data['count rate {0} (Hz)'.format(ch)] = self.image_raw[:, :, 2 + n].flatten()
            if not self._fast_scan:
                data_back['count rate {0} (Hz)'.format(ch)] = self.image_raw_back[:, :, 2 + n].flatten()

        if self._ai_scanner:
            data["count rate AI (V)"] = self._ai_counter_voltages.flatten()
            if not self._fast_scan:
                data_back["count rate AI (V)"] = self._ai_counter_voltages_back.flatten()

        # Save the raw data to file
        filelabel = 'confocal_stepper_data'
        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   fmt='%.6e',
                                   delimiter='\t')
        if not self._fast_scan:
            filelabel = 'confocal_stepper_data_back'
            self._save_logic.save_data(data_back,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t')

        # plot images and save raw data
        axis_list = []
        for axis_name in self.axis_class.keys():
            if self.axis_class[axis_name].closed_loop:
                axis_list.append(axis_name)

        if len(axis_list) > 0:
            position = self.get_position(axis_list)
            if not position[0] == -1:
                parameters['Last Stepper Positions '] = axis_list, position
        if len(self._start_position) > 0:
            counter = 0
            if self.axis_class[self._first_scan_axis].closed_loop:
                parameters["Start position first axis"] = self._start_position[counter]
                counter = 1
            if self.axis_class[self._second_scan_axis].closed_loop:
                parameters['Start position second axis'] = self._start_position[counter]

        figs = {ch: self.draw_figure(data=self.stepping_raw_data,
                                     full_data=full_data,
                                     cbar_range=colorscale_range,
                                     percentile_range=percentile_range,
                                     ch=n)
                for n, ch in enumerate(self.get_counter_count_channels())}

        # Save the image data and figure
        for n, ch in enumerate(self.get_counter_count_channels()):
            # data for the text-array "image":
            image_data = OrderedDict()
            image_data['Confocal pure {}{} scan image data without axis.\n'
                       'The upper left entry represents the signal at the upper left pixel '
                       'position.\nA pixel-line in the image corresponds to a row '
                       'of entries where the Signal is in counts/s:'.format(
                self._first_scan_axis, self._second_scan_axis)] = self.stepping_raw_data

            filelabel = 'confocal_image_{0}'.format(ch.replace('/', ''))
            self._save_logic.save_data(image_data,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       plotfig=figs[ch][0])
            if self.map_scan_position:  # also save image data for positions of steppers
                self._save_logic.save_data(image_data,
                                           filepath=filepath,
                                           timestamp=timestamp,
                                           parameters=parameters,
                                           filelabel=filelabel + "_position",
                                           fmt='%.6e',
                                           delimiter='\t',
                                           plotfig=figs[ch][1])
        if not self._fast_scan:
            figs = {ch: self.draw_figure(data=self.stepping_raw_data_back,
                                         full_data=full_data_back,
                                         cbar_range=colorscale_range,
                                         percentile_range=percentile_range,
                                         ch=n)
                    for n, ch in enumerate(self.get_counter_count_channels())}

            # Save the image data and figure
            for n, ch in enumerate(self.get_counter_count_channels()):
                # data for the text-array "image":
                image_data = OrderedDict()
                image_data['Confocal pure {}{} scan image data without axis.\n'
                           'The upper left entry represents the signal at the upper left pixel '
                           'position.\nA pixel-line in the image corresponds to a row '
                           'of entries where the Signal is in counts/s:'.format(
                    self._first_scan_axis, self._second_scan_axis)] = self.stepping_raw_data_back

                filelabel = 'confocal_image_back_{0}'.format(ch.replace('/', ''))
                self._save_logic.save_data(image_data,
                                           filepath=filepath,
                                           timestamp=timestamp,
                                           parameters=parameters,
                                           filelabel=filelabel,
                                           fmt='%.6e',
                                           delimiter='\t',
                                           plotfig=figs[ch][n])

                if self.map_scan_position:  # also plot image data for positions of steppers
                    self._save_logic.save_data(image_data,
                                               filepath=filepath,
                                               timestamp=timestamp,
                                               parameters=parameters,
                                               filelabel=filelabel + "_position",
                                               fmt='%.6e',
                                               delimiter='\t',
                                               plotfig=figs[ch][n])

        self.log.debug('Confocal Stepper Image saved.')
        # if self._3D_measurement:
        #   self._save_3D_measurement(parameters)

        self.signal_data_saved.emit()
        # Todo Ask if it is possible to write only one save with options for which lines were scanned
        return

    def _save_3D_measurement(self, parameters):
        filepath = self._save_logic.get_path_for_module('ConfocalStepper')
        timestamp = datetime.datetime.now()
        # Prepare the meta data parameters (common to both saved files):
        parameters["ao_ramp_length"] = self._ramp_length
        # prepare the full raw data in an OrderedDict:
        data = OrderedDict()
        data_back = OrderedDict()
        if self.map_scan_position and self._save_positions:
            data['x position (mm)'] = self._3D_scan_pos_voltages[:, :, 0].flatten()
            data['y position (mm)'] = self._3D_scan_pos_voltages[:, :, 1].flatten()
            data_back['y position (mm)'] = self._3D_scan_pos_voltages_back[:, :, 1].flatten()
            if not self._fast_scan:
                data_back['x position (mm)'] = self._3D_scan_pos_voltages_back[:, :, 0].flatten()
                full_data = self.full_image  # else it will be none to reduce computation time = drawing time
                full_data_back = self.full_image_back
        else:
            data['x step'] = self.image_raw[:, :, 0].flatten()
            data['y step'] = self.image_raw[:, :, 1].flatten()
            full_data = None
            if not self._fast_scan:
                data_back['x step'] = self.image_raw_back[:, :, 0].flatten()
                data_back['y step'] = self.image_raw_back[:, :, 1].flatten()
                full_data_back = None

        for n, ch in enumerate(self.get_counter_count_channels()):
            data['count rate {0} (Hz)'.format(ch)] = self._3D_stepping_raw_data.flatten()
            if not self._fast_scan:
                data_back['count rate {0} (Hz)'.format(ch)] = self._3D_stepping_raw_data_back.flatten()

        if self._ai_scanner:
            data["count rate AI (V)"] = self._3D_ai_counter_voltages.flatten()
            if not self._fast_scan:
                data_back["count rate AI (V)"] = self._3D_ai_counter_voltages_back.flatten()

        # Save the raw data to file
        filelabel = 'confocal_stepper_data_3D'
        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   fmt='%.6e',
                                   delimiter='\t')
        if not self._fast_scan:
            filelabel = 'confocal_stepper_data_back_3D'
            self._save_logic.save_data(data_back,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t')

    def draw_figure(self, data, full_data=None, scan_axis=None, cbar_range=None,
                    percentile_range=None, ch=0, suffix="steps"):  # crosshair_pos=None):
        """ Create a 2-D color map figure of the scan image for saving

        @param: array data: The NxM array of count values from a scan with NxM pixels.

        @param: array full_data: The NxMx3 numpy ndarray
                                containing the full image information with counts per position

        @param: list image_extent: The scan range in the form [hor_min, hor_max, ver_min, ver_max]

        @param: list axes: Names of the horizontal and vertical axes in the image

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].  If not supplied
                                    then a default of data_min to data_max will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @param: list crosshair_pos: (optional) crosshair position as [hor, vert] in the chosen
                                    image axes.

        @param: int ch: The channel number that is to be plotted. Default 0

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        # Todo: this is very incomplete. Things like axis etc are missing
        image_data = data

        # If no colorbar range was given, take full range of data
        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = [np.min(image_data), np.max(image_data)]

        # Scale color values using SI prefix
        prefix = ['', 'k', 'M', 'G']
        prefix_count = 0
        draw_cb_range = np.array(cbar_range)

        while draw_cb_range[1] > 1000:
            image_data = image_data / 1000
            draw_cb_range = draw_cb_range / 1000
            prefix_count = prefix_count + 1

        c_prefix = prefix[prefix_count]

        # Scale axes values using SI prefix
        axes_prefix = ['', 'm', r'$\mathrm{\mu}$', 'n']
        x_prefix_count = 0
        y_prefix_count = 0

        cbar_prefix = prefix[prefix_count]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots()

        # Create image plot
        cfimage = ax.imshow(image_data,
                            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
                            origin="lower",
                            vmin=draw_cb_range[0],
                            vmax=draw_cb_range[1],
                            interpolation='none'
                            )

        ax.set_aspect(1)
        ax.set_xlabel(self._first_scan_axis + " " + suffix)
        ax.set_ylabel(self._second_scan_axis + " " + suffix)
        ax.spines['bottom'].set_position(('outward', 10))
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Draw the colorbar
        cbar = plt.colorbar(cfimage, shrink=0.8)  # , fraction=0.046, pad=0.08, shrink=0.75)
        cbar.set_label('Fluorescence (' + c_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        # redo for the full image information if is exists
        if full_data is not None:

            # Adjust data format
            xdata = full_data[:, :, 0]
            ydata = full_data[:, :, 1]
            zdata = full_data[:, :, 2 + ch]

            cbar_range = [np.min(zdata), np.max(zdata)]
            # Create figure
            fig2, ax2 = plt.subplots()
            # Create image plot
            cfimage2 = ax2.tripcolor(np.ndarray.flatten(xdata), np.ndarray.flatten(ydata), np.ndarray.flatten(zdata),
                                     cmap=plt.get_cmap('inferno'),  # reference the right place in qd,
                                     vmin=cbar_range[0],
                                     vmax=cbar_range[1])

            ax2.set_aspect(1)
            ax2.set_xlabel(self._first_scan_axis + ' mm ')
            ax2.set_ylabel(self._second_scan_axis + ' mm ')
            ax2.spines['bottom'].set_position(('outward', 10))
            ax2.spines['left'].set_position(('outward', 10))
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.get_xaxis().tick_bottom()
            ax2.get_yaxis().tick_left()

            # Adjust subplots to make room for colorbar
            fig2.subplots_adjust(right=0.8)

            # Draw the colorbar
            cbar2 = plt.colorbar(cfimage2, shrink=0.8)  # , fraction=0.046, pad=0.08, shrink=0.75)
            cbar2.set_label('Fluorescence (' + c_prefix + 'c/s)')

            # remove ticks from colorbar for cleaner image
            cbar2.ax.tick_params(which=u'both', length=0)
            cbar.ax.tick_params(which=u'both', length=0)

            # If we have percentile information, draw that to the figure
            if percentile_range is not None:
                cbar2.ax.annotate(str(percentile_range[0]),
                                  xy=(-0.3, 0.0),
                                  xycoords='axes fraction',
                                  horizontalalignment='right',
                                  verticalalignment='center',
                                  rotation=90
                                  )
                cbar2.ax.annotate(str(percentile_range[1]),
                                  xy=(-0.3, 1.0),
                                  xycoords='axes fraction',
                                  horizontalalignment='right',
                                  verticalalignment='center',
                                  rotation=90
                                  )
                cbar2.ax.annotate('(percentile)',
                                  xy=(-0.3, 0.5),
                                  xycoords='axes fraction',
                                  horizontalalignment='right',
                                  verticalalignment='center',
                                  rotation=90
                                  )
            # self.signal_draw_figure_completed.emit()
            return fig, fig2

        # self.signal_draw_figure_completed.emit()
        return fig, None
        # Todo Probably the function from confocal logic, that already exists need to be chaned only slightly

    def generate_file_path(self):
        timestamp = datetime.datetime.now()
        if self._3D_measurement:
            path_addition = "_3D"
        else:
            path_addition = ""
        self.filepath = self._save_logic.get_path_for_module(
            'ConfocalStepper' + path_addition + "/" + timestamp.strftime('%Y%m%d-%H%M-%S'))
        self.file_path_raw = self._save_logic.get_path_for_module(self.filepath + "/raw")
        self.filelabel = "confocal_stepper_data" + path_addition
        self.filename = "confocal_stepper_data"

    def generate_file_info(self):
        pass

    def save_to_npy(self, name, line, data):
        if line < 10:
            addition = "00"
        elif line < 100:
            addition = "0"
        else:
            addition = ""
        np.save(self.file_path_raw + "/" + self.filename + "_" + name + "_line_" + addition + str(line), data)

    def generate_npy_file(self, data):
        # Todo: this is very crude

        np.save(self.path_name + '/' + self.filename, data)
        np.save(self.path_name + '/' + self.filename_back, data)

    #################################### Tilt correction ########################################

    @QtCore.Slot()
    def set_tilt_point1(self):
        """ Gets the first reference point for tilt correction."""
        pass
        self.point1 = np.array(self._scanning_device.get_scanner_position()[:3])
        self.signal_tilt_correction_update.emit()

    @QtCore.Slot()
    def set_tilt_point2(self):
        """ Gets the second reference point for tilt correction."""
        pass
        self.point2 = np.array(self._scanning_device.get_scanner_position()[:3])
        self.signal_tilt_correction_update.emit()

    @QtCore.Slot()
    def set_tilt_point3(self):
        """Gets the third reference point for tilt correction."""
        pass
        self.point3 = np.array(self._scanning_device.get_scanner_position()[:3])
        self.signal_tilt_correction_update.emit()

    @QtCore.Slot(bool)
    def set_tilt_correction(self, enabled):
        """ Set tilt correction in tilt interfuse.

            @param bool enabled: whether we want to use tilt correction
        """
        self._scanning_device.tiltcorrection = enabled
        self._scanning_device.tilt_reference_x = self._scanning_device.get_scanner_position()[
            0]
        self._scanning_device.tilt_reference_y = self._scanning_device.get_scanner_position()[
            1]
        self.signal_tilt_correction_active.emit(enabled)

    ################################# Move through History ########################################

    def history_forward(self):
        """ Move forward in confocal image history.
        """
        pass
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.history[self.history_index].restore(self)
            self.signal_image_updated.emit()
            self.signal_depth_image_updated.emit()
            self.signal_tilt_correction_update.emit()
            self.signal_tilt_correction_active.emit(self._scanning_device.tiltcorrection)
            self._change_position('history')
            self.signal_change_position.emit('history')
            self.signal_history_event.emit()

    def history_back(self):
        """ Move backwards in confocal image history.
        """
        pass
        if self.history_index > 0:
            self.history_index -= 1
            self.history[self.history_index].restore(self)
            self.signal_image_updated.emit()
            self.signal_depth_image_updated.emit()
            self.signal_tilt_correction_update.emit()
            self.signal_tilt_correction_active.emit(self._scanning_device.tiltcorrection)
            self._change_position('history')
            self.signal_change_position.emit('history')
            self.signal_history_event.emit()
