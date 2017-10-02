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

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


# Todo make a confocal stepper History class for this logic as exists in confocal logic. This is needed for restarting and
# for back and forward movement in images


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

    _connectors = {
        'confocalstepper1': 'ConfocalStepperInterface',
        'savelogic': 'SaveLogic',
        'confocalcounter': 'FiniteCounterInterface',
        'analoguereader': 'AnalogReaderInterface'
    }

    # Todo: add connectors and QTCore Signals
    # signals
    signal_start_stepping = QtCore.Signal()
    signal_stop_stepping = QtCore.Signal()
    signal_continue_stepping = QtCore.Signal()
    signal_step_lines_next = QtCore.Signal(bool)

    # signals
    signal_image_updated = QtCore.Signal()
    signal_change_position = QtCore.Signal(str)
    signal_data_saved = QtCore.Signal()
    signal_tilt_correction_active = QtCore.Signal(bool)
    signal_tilt_correction_update = QtCore.Signal()
    signal_draw_figure_completed = QtCore.Signal()
    signal_position_changed = QtCore.Signal()

    sigImageInitialized = QtCore.Signal()

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
            self.steps_direction = 50
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
                # if self.getState() == 'locked':
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
                # if self.getState() == 'locked':
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

        def set_stepper_frequency(self, frequency=None):
            """
            Sets the stepping frequency for a specific axis to frequency

            @param float frequency: desired frequency

            @return int: error code (0:OK, -1:error)
            """

            # checks if stepper is still running
            # if self.getState() == 'locked':
            #    return -1

            if frequency is not None:
                if frequency is not None:
                    range_f = self.get_freq_range()[self.name]
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
            # if self.getState() == 'locked':
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
            @return dict: key[axis], value[list of range]
            """
            return self.hardware.get_freq_range_stepper()

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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Todo: Add initialisation from _statusVariable

        # Connectors
        self._stepping_device = self.get_connector('confocalstepper1')
        self._counting_device = self.get_connector('confocalcounter')
        self._position_feedback_device = self.get_connector('analoguereader')
        self._save_logic = self.get_connector('savelogic')

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
        self._scan_axes = "xy"
        self._inverted_scan = False
        self.stopRequested = False
        self._off_set_x = 0.02
        self._off_set_direction = True
        self.steps_direction = dict()
        for i in self.axis:
            self.steps_direction[i] = 50

        # Initialise for scan_image
        self._step_counter = 0
        self._get_scan_axes()
        self.stepping_raw_data = np.zeros(
            (self._steps_scan_first_line, self._steps_scan_first_line))
        self.stepping_raw_data_back = np.zeros(
            (self._steps_scan_first_line, self._steps_scan_first_line))
        self._start_position = []
        self.map_scan_position = True
        self._scan_positions = np.zeros(
            (self._steps_scan_first_line, self._steps_scan_first_line))
        self._scan_positions_back = np.zeros(
            (self._steps_scan_first_line, self._steps_scan_first_line))
        self.initialize_image()

        # Step values definitions


        # Sets connections between signals and functions
        self.signal_step_lines_next.connect(self._step_line, QtCore.Qt.QueuedConnection)
        self.signal_start_stepping.connect(self.start_stepper, QtCore.Qt.QueuedConnection)
        self.signal_continue_stepping.connect(self.continue_stepper, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        pass

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
        if self.getState() == 'locked':
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
            2 ** self._position_feedback_device.get_ai_resolution())) * 1.05
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

    def get_position(self, axes):
        """Measures the current position of the hardware axes of the stepper

        @ List(str) axes: List of strings for which the hardware positions are to be measured

        @ return List : positions the hardware in mm ordered by the axes ordering or error value [-1]
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

        # read voltages from resistive read out for position feedback
        if self._position_feedback_device.set_up_analogue_voltage_reader(axes[0]) < 0:
            return [-1]
        try:
            self._position_feedback_device.lock()
        except:
            self.log.warning("Position feedback device is already in use for another task")
            self._position_feedback_device.close_analogue_voltage_reader(axes[0])
            return -1
        # if more than one axis is read add additional readout channels
        # Todo: only checks if first axis is closed loop and not other ones. Needs to be changed
        if len(axes) > 1:
            if 0 > self._position_feedback_device.add_analogue_reader_channel_to_measurement(axes[0], axes[1:]):
                self._position_feedback_device.unlock()
                self._position_feedback_device.close_analogue_voltage_reader(axes[0])
                return [-1]

        voltage_result = self._position_feedback_device.get_analogue_voltage_reader(axes)
        self._position_feedback_device.unlock()
        # close position feedback reader
        if 0 > self._position_feedback_device.close_analogue_voltage_reader(axes[0]):
            self.log.error("It was not possible to close the analog voltage reader")
            return [-1]
        if voltage_result[1] == 0:
            self.log.warning("Reading the voltage for position feedback failed")
            return [-1]

        # convert voltage to position
        position_result = []
        for counter in range(len(axes)):
            position = self.convert_voltage_to_position(axes[counter], voltage_result[0][counter])
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
                "The voltage (%s) you are trying to convert lies without the physical range of your axis (%s)",
                voltage, voltage_range)

        v_range = voltage_range[1] - voltage_range[0]
        s_range = step_range[1] - step_range[0]
        result = ((voltage - voltage_range[0]) * s_range / v_range) + step_range[0]
        # the precision of readout of the attocubes so far is 200nn (4th digit).
        # Todo: add this precision to config (attocube)
        result = truncate(result, 4)
        return result

    ################################# Stepper Scan Methods #######################################

    def set_scan_axes(self, scan_axes):
        """"
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
            if axis not in self.axis_class.keys:
                self.log.error("The specified scan axis {} is not a stepper axis".format(axis))
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
                self._steps_scan_first_line = self.steps_direction[a]
                self._steps_scan_second_line = self.steps_direction[b]
            else:
                self._first_scan_axis = a
                self._second_scan_axis = b
                self._steps_scan_first_line = self.steps_direction[b]
                self._steps_scan_second_line = self.steps_direction[a]
        else:
            self.log.error(
                "One of the chosen axes {} are not defined for the stepper hardware.".format(
                    self._scan_axes))
            self.unlock()
            return -1

        return 0

    def start_stepper(self):
        """Starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """
        # Todo: Do we need a lock for the stepper as well?
        self._step_counter = 0
        self.lock()

        # Todo: to be done when GUI is done
        # if self.initialize_image() < 0:
        #    self.unlock()
        #    return -1

        if self._get_scan_axes() < 0:
            return -1

        # Check the parameters of the stepper device
        freq_status = self.axis_class[self._first_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1
        freq_status = self.axis_class[self._second_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1

        # initialize counting device
        clock_status = self._counting_device.set_up_finite_counter_clock(
            clock_frequency=self.axis_class[self._first_scan_axis].step_freq)
        if clock_status < 0:
            self.unlock()
            return -1

        # Todo: The connection to the GUI amount of samples needs to be made
        # maybe a value given by the function needs to be implemented here
        scanner_status = self._counting_device.set_up_finite_counter(self._steps_scan_first_line)
        if scanner_status < 0:
            self._counting_device.close_finite_counter_clock()
            self._counting_device.unlock()
            self.unlock()
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
        if axis_status1 < 0 or axis_status2 < 0:
            # Todo: is this really sensible here?
            self.axis_class[self._first_scan_axis].set_mode_ground()
            self.axis_class[self._second_scan_axis].set_mode_ground()
            self.unlock()
            self.kill_counter()
            return -1
        self._stepping_device.lock()
        self.stepping_raw_data = np.zeros(
            (self._steps_scan_second_line, self._steps_scan_first_line))
        self.stepping_raw_data_back = np.zeros(
            (self._steps_scan_second_line, self._steps_scan_first_line))
        self.time = np.zeros((self._steps_scan_second_line, 2))
        self.time_back = np.zeros((self._steps_scan_second_line, 2))

        # save starting positions
        self._start_position = []
        if self.axis_class[self._first_scan_axis].closed_loop:
            self._start_position.append(self.get_position([self._first_scan_axis])[0])
        if self.axis_class[self._second_scan_axis].closed_loop:
            self._start_position.append(self.get_position([self._second_scan_axis])[0])

        # check if scan positions should be saved and if it is possible
        if self.map_scan_position:
            if self.axis_class[self._steps_scan_first_line].closed_loop and self.axis_class[
                self._second_scan_axis].closed_loop:
                # initialise arrays
                self._scan_positions = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line, 2))
                self._scan_positions_back = np.zeros((self._steps_scan_second_line, self._steps_scan_first_line, 2))
                # initialise position scan
                if 0 > self._position_feedback_device.set_up_analogue_voltage_reader_scanner(
                        self._steps_scan_first_line, self._first_scan_axis):
                    self.stopRequested = True
                else:
                    if 0 > self._position_feedback_device.add_analogue_reader_channel_to_measurement(
                            self._first_scan_axis, [self._second_scan_axis]):
                        self.stopRequested = True
            else:
                self.map_scan_position = False

        self.initialize_image()

        self.signal_step_lines_next.emit(True)

        return 0

    def stop_stepper(self):
        """"Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        # Todo: Make sure attocube axis are set back to ground if deemed sensible
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        self.signal_stop_stepping.emit()
        return 0

    def continue_stepper(self):
        """Continue the stepping procedure

        @return int: error code (0:OK, -1:error)
        """
        self.lock()
        # Check the parameters of the stepper device
        freq_status = self.axis_class[self._first_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1
        freq_status = self.axis_class[self._first_scan_axis]._check_freq()
        amp_status = self.axis_class[self._second_scan_axis]._check_amplitude()
        if freq_status < 0 or amp_status < 0:
            self.unlock()
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
        self._position_feedback_device.lock()
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
                self._position_feedback_device.unlock()
                self._position_feedback_device.close_analogue_voltage_reader(axis_name)
                return -1
            time.sleep(sleep)
            # compare new position to desired one
            result = self._position_feedback_device.get_analogue_voltage_reader([axis_name])
            if result[1] == 0:
                self._position_feedback_device.unlock()
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
                self._position_feedback_device.unlock()
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
        self._position_feedback_device.unlock()
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
        if self.getState() != 'locked':
            return

            # stop stepping
        if self.stopRequested:
            with self.threadlock:
                self.kill_counter()
                self.stopRequested = False
                self.unlock()
                self._stepping_device.unlock()
                # self.signal_xy_image_updated.emit()
                # self.signal_depth_image_updated.emit()

                # if self._zscan:
                #    self._depth_line_pos = self._scan_counter
                # else:
                #    self._xy_line_pos = self._scan_counter
                # add new history entry
                # new_history = ConfocalHistoryEntry(self)
                # new_history.snapshot(self)
                # self.history.append(new_history)
                # if len(self.history) > self.max_history_length:
                #    self.history.pop(0)
                # self.history_index = len(self.history) - 1
                # self.log.info("Stepping stopped successfully")
                # self.log.info("The stepper stepped {} lines".format(self._step_counter))
                return

        # move and count
        new_counts = self._step_and_count(self._first_scan_axis, self._second_scan_axis, direction,
                                          steps=self._steps_scan_first_line)
        if new_counts[0][0] == -1:
            self.stopRequested = True
            self.signal_step_lines_next.emit(direction)
            return
        if new_counts[1][0] == -1:
            self.stopRequested = True
            self.signal_step_lines_next.emit(direction)
            return

            # if not direction:  # flip the count direction
            # new_counts = np.flipud(new_counts)
        if self.map_scan_position:
            if new_counts[2][0] == -1:
                self.stopRequested = True
                self.signal_step_lines_next.emit(direction)
                return
            if new_counts[3][0] == -1:
                self.stopRequested = True
                self.signal_step_lines_next.emit(direction)
                return

        direction = not direction  # invert direction
        self.stepping_raw_data[self._step_counter] = new_counts[0]
        self.stepping_raw_data_back[self._step_counter] = np.flipud(new_counts[1])
        if self.map_scan_position:
            self._scan_positions[self._step_counter] = new_counts[2]
            self._scan_positions_back[self._step_counter] = np.flipud(new_counts[3])
        self.signal_image_updated.emit()
        self.update_image_data_line(self._step_counter)
        self._step_counter += 1

        # check starting position of fast scan direction
        if self.axis_class[self._first_scan_axis].closed_loop:
            if self.map_scan_position:
                # Todo: how is the position data saved for the backward direction?
                new_position = self._scan_positions_back[self._step_counter, -1, 0]
            else:
                new_position = self.get_position([self._first_scan_axis])
            if abs(self._start_position[0] - new_position) > self.axis_class[
                self._first_scan_axis].feedback_precision_position:
                steps_res = int(
                    self._steps_scan_first_line * 0.03)  # 3%offset is minimum to be expected so more
                # steps would be over correcting
                # stop readout for scanning so positions can be optimised
                if self.map_scan_position:
                    self._position_feedback_device.close_analogue_voltage_reader(self._first_scan_axis)
                if self.optimize_position(self._first_scan_axis, self._start_position[0], steps_res) < 0:
                    self.stopRequested = True
                    self.log.warning('Optimisation of position failed. Step Scan stopped.')
                # restart position readout for scanning
                if self.map_scan_position:
                    self._position_feedback_device.set_up_analogue_voltage_reader_scanner(self._steps_scan_first_line,
                                                                                          self._first_scan_axis)
                    self._position_feedback_device.add_analogue_reader_channel_to_measurement(self._first_scan_axis,
                                                                                              [self._second_scan_axis])
        if self._step_counter > self._steps_scan_second_line - 1:
            self.stopRequested = True
            self.log.info("Stepping scan at end position")

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
                time1 = time.time()
                if self.map_scan_position:
                    if 0 > self._position_feedback_device.start_ai_counter_reader(self._first_scan_axis):
                        self.log.error("Starting the counter failed")
                        return [-1], []
                else:
                    if self._counting_device.start_finite_counter() < 0:
                        self.log.error("Starting the counter failed")
                        return [-1], []
                time2 = time.time()
                if self._stepping_device.move_attocube(main_axis, True, True, steps=steps - 1) < 0:
                    self.log.error("moving of attocube failed")
                    # Todo: repair return values
                    return [-1], []
                time3 = time.time()

                # move on line up
                # if self._stepping_device.move_attocube(secondaxis, True, True, 1) < 0:
                #    self.log.error("moving of attocube failed")
                #    return -1

                # Todo: Check if there is a better way than this to adjust for the fact that a stepping
                # direction change is necessary for the last count. Maybe different method arrangement
                # sensible

                time.sleep(
                    steps / self.axis_class[main_axis].step_freq)  # wait till stepping finished for readout
                result = self._counting_device.get_finite_counts()
                if self.map_scan_position:
                    analog_result = self._position_feedback_device.get_analogue_voltage_reader(
                        [self._first_scan_axis, self._second_scan_axis])
                retval = 0
                a = self._counting_device.stop_finite_counter()
                if self.map_scan_position:
                    if 0 > self._position_feedback_device.stop_analogue_voltage_reader(self._first_scan_axis):
                        self.log.error("Stopping the analog input failed")
                        retval = [-1], []
                if result[0][0] == [-1]:
                    self.log.error("The readout of the counter failed")
                    retval = [-1], []
                    return retval
                elif self.map_scan_position:
                    if analog_result[0][0] == [-1]:
                        self.log.error("The readout of the analog reader failed")
                        retval = [-1], []
                        return retval
                elif result[1] != steps:
                    self.log.error("A different amount of data than necessary was returned.\n "
                                   "Received {} instead of {} bins with counts ".format(result[1],
                                                                                        steps))
                    retval = [-1], []
                    return [-1], []
                elif a < 0:
                    retval = [-1], []
                    self.log.error("Stopping the counter failed")
                    return retval
                # else:
                #   retval = result[0]

                # redo this now (not forever) in the other direction
                time_back1 = time.time()
                if self.map_scan_position:
                    if 0 > self._position_feedback_device.start_ai_counter_reader(self._first_scan_axis):
                        self.log.error("Starting the counter failed")
                        return [-1], []
                else:
                    if self._counting_device.start_finite_counter() < 0:
                        self.log.error("Starting the counter failed")
                        return [-1], []
                time_back2 = time.time()

                if self._stepping_device.move_attocube(main_axis, True, False, steps=steps - 1) < 0:
                    self.log.error("moving of attocube failed")
                    return [-1], []
                time_back3 = time.time()
                time.sleep(steps / self.axis_class[main_axis].step_freq)
                result_back = self._counting_device.get_finite_counts()
                if self.map_scan_position:
                    analog_result_back = self._position_feedback_device.get_analogue_voltage_reader(
                        [self._first_scan_axis, self._second_scan_axis])

                # move on line up
                if self._stepping_device.move_attocube(second_axis, True, True, 1) < 0:
                    self.log.error("moving of attocube failed")
                    return [-1], []
                a = self._counting_device.stop_finite_counter()
                if self.map_scan_position:
                    if 0 > self._position_feedback_device.stop_analogue_voltage_reader(self._first_scan_axis):
                        self.log.error("Stopping the analog input failed (2)")
                        retval = [-1]

                if result_back[0][0] == [-1]:
                    self.log.error("The readout of the counter(2) failed")
                    retval = [-1], []
                elif self.map_scan_position:
                    if analog_result_back[0][0] == [-1]:
                        self.log.error("The readout of the analog reader failed")
                        retval = [-1], []
                        return retval
                elif result_back[1] != steps:
                    self.log.error("A different amount of data than necessary was returned(2).\n "
                                   "Received {} instead of {} bins with counts ".format(result[1],
                                                                                        steps))
                    retval = [-1], []
                elif a < 0:
                    retval = [-1], []
                    self.log.error("Stopping the counter failed (2)")
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
                if self.map_scan_position:
                    return result[0], result_back[0], analog_result[0], analog_result_back[0]
                return result[0], result_back[0]
            else:
                self.log.error(
                    "second axis %s in not  an axis %s of the stepper", second_axis, self.axis)
                return [-1], []

        else:
            self.log.error("main axis %s is not an axis %s of the stepper", main_axis, self.axis)
            return [-1], []

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
        try:
            self._counting_device.unlock()
        except Exception as e:
            self.log.exception('Could not unlock scanning device.')

        return 0

    def get_counter_count_channels(self):
        """ Get lis of counting channels from counting device.
          @return list(str): names of counter channels
        """
        return self._counting_device.get_scanner_count_channels()

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
        image_raw = np.zeros((self._steps_scan_first_line, self._steps_scan_second_line, 3))
        image_raw_back = np.zeros((self._steps_scan_first_line, self._steps_scan_first_line, 3))
        image_raw[:, :, 2] = self.stepping_raw_data
        image_raw_back[:, :, 2] = self.stepping_raw_data_back
        if not self.map_scan_position:
            first_positions = np.linspace(0, self._steps_scan_first_line - 1, self._steps_scan_first_line)
            second_positions = np.linspace(0, self._steps_scan_second_line - 1, self._steps_scan_second_line)
            first_position_array, second_position_array = np.meshgrid(first_positions, second_positions)
            image_raw[:, :, 1] = second_position_array
            image_raw_back[:, :, 0] = first_position_array

        self.image = image_raw
        self.image_back = image_raw_back

    def update_image_data(self):
        """Updates the images data
        """
        self.image[:, :, 2] = self.stepping_raw_data
        self.image_back[:, :, 2] = self.stepping_raw_data
        if self.map_scan_position:
            self.image[:, :, 2] = self._scan_positions
            self.image_back[:, :, :2] = self._scan_positions_back

    def update_image_data_line(self, line_counter):
        """

        :param line_counter:
        """
        self.image[line_counter, :, 2] = self.stepping_raw_data[line_counter]
        self.image_back[line_counter, :, 2] = self.stepping_raw_data_back[line_counter]
        if self.map_scan_position:
            self.image[line_counter, :, :2] = self._scan_positions[line_counter]
            self.image_back[line_counter, :, :2] = self._scan_positions_back[line_counter]

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
        filepath = self._save_logic.get_path_for_module('ConfocalStepper')
        timestamp = datetime.datetime.now()
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

        axis_list = []
        for axis_name in self.axis_class.keys():
            if self.axis_class[axis_name].closed_loop:
                axis_list.append(axis_name)
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
                                     cbar_range=colorscale_range,
                                     percentile_range=percentile_range)
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

            filelabel = 'confocal_xy_image_{0}'.format(ch.replace('/', ''))
            self._save_logic.save_data(image_data,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       plotfig=figs[ch])
        figs = {ch: self.draw_figure(data=self.stepping_raw_data_back,
                                     cbar_range=colorscale_range,
                                     percentile_range=percentile_range)
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
                                       plotfig=figs[ch])

            # prepare the full raw data in an OrderedDict:
        data = OrderedDict()
        data_back = OrderedDict()
        if self.map_scan_position:
            data['x position (mm)'] = self.image[:, :, 0].flatten()
            data['y position (mm)'] = self.image[:, :, 1].flatten()
            data_back['x position (mm)'] = self.image_back[:, :, 0].flatten()
            data_back['y position (mm)'] = self.image_back[:, :, 1].flatten()
        else:
            data['x step'] = self.image[:, :, 0].flatten()
            data['y step'] = self.image[:, :, 1].flatten()
            data_back['x step'] = self.image_back[:, :, 0].flatten()
            data_back['y step'] = self.image_back[:, :, 1].flatten()


            # Todo: for this both counters must actually be implemented
        #        for n, ch in enumerate(self.get_scanner_count_channels()):
        #            data['count rate {0} (Hz)'.format(ch)] = self.xy_image[:, :, 3 + n].flatten()
        data['count rate (Hz)'] = self.image[:, :, 2].flatten()
        data_back['count rate (Hz)'] = self.image_back[:, :, 2].flatten()

        # Save the raw data to file
        filelabel = 'confocal_stepper_data'
        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   fmt='%.6e',
                                   delimiter='\t')

        filelabel = 'confocal_stepper_data_back'
        self._save_logic.save_data(data_back,
                                   filepath=filepath,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   fmt='%.6e',
                                   delimiter='\t')

        self.log.debug('Confocal Stepper Image saved.')
        self.signal_data_saved.emit()
        # Todo Ask if it is possible to write only one save with options for which lines were scanned
        return

    def draw_figure(self, data, scan_axis=None, cbar_range=None,
                    percentile_range=None):  # crosshair_pos=None):
        """ Create a 2-D color map figure of the scan image for saving

        @param: array data: The NxM array of count values from a scan with NxM pixels.

        @param: list image_extent: The scan range in the form [hor_min, hor_max, ver_min, ver_max]

        @param: list axes: Names of the horizontal and vertical axes in the image

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].  If not supplied
                                    then a default of data_min to data_max will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @param: list crosshair_pos: (optional) crosshair position as [hor, vert] in the chosen
                                    image axes.

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
        image_data = data
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
                            interpolation='none',
                            )

        ax.set_aspect(1)
        ax.set_xlabel(self._first_scan_axis + ' steps (')
        ax.set_ylabel(self._second_scan_axis + ' steps ')
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
        self.signal_draw_figure_completed.emit()
        return fig
        # Todo Probably the function from confocal logic, that already exists need to be chaned only slightly

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
