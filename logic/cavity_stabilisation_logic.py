# -*- coding: utf-8 -*-
"""
This module operates a cavity length stabilisation.
It is based on analogue input that serves as feedback about the cavity
and analogue output that is used to change the length of the cavity.

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

import time
import numpy as np
import math
import datetime
from collections import OrderedDict

from core.module import Connector, ConfigOption, StatusVar
from logic.generic_logic import GenericLogic


def round_to_2(x):
    """Rounds to the second significant figure of a number"""
    return round(x, -int(math.floor(math.log10(abs(x)))) + 1)


def truncate(f, n):
    """Truncates/pads a float f to n decimal places without rounding"""
    # necessary to avoid floating point conversion errors
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return float('.'.join([i, (d + '0' * n)[:n]]))


def float_rounding(rounded_number, divisor):
    """"This methods rounds values n to the nearest multiple of b (floor)
    @param float rounded_number: The number to be rounded
    @param float divisor: The number which multiple it should be rounded
    """
    return rounded_number - math.fmod(rounded_number, divisor)


def in_range(x, min, max):
    """Checks if given value is within a range

    @param float x: value to be checked
    @param float min: lower limit
    @param float max: upper limit
    @return bool: true if x lies within [min,max]
    """
    return (min is None or min <= x) and (max is None or max >= x)


class CavityStabilisationLogic(GenericLogic):  # Todo connect to generic logic
    """
    This is the Logic class for software driven cavity length stabilisation, both in reflection and transmission .
    """
    _modclass = 'CavityStabilisationLogic'
    _modtype = 'logic'

    # declare connectors
    analoguereader = Connector(interface='AnalogueReaderInterface')
    analogueoutput = Connector(interface='AnalogueOutputInterface')
    savelogic = Connector(interface='SaveLogic')

    voltage_adjustment_steps = ConfigOption('voltage_adjustment_steps', 1, missing='warn')
    reflection = ConfigOption('cavitymode_reflection', True, missing='warn')
    _average_number = ConfigOption('averages_over_feedback', 1, missing='warn')
    threshold = ConfigOption('threshold', 0.1, missing='error')
    _axis = ConfigOption('axis', "APD", missing='error')
    feedback_axis = ConfigOption('feedback', 'APD', missing='error')
    control_axis = ConfigOption('control', 'z', missing='error')
    _scan_frequency = ConfigOption('scan_frequency', 1, missing="warn")
    _scan_resolution = ConfigOption('scan_resolution', 1e-6, missing="warn")
    _smoothing_steps = ConfigOption('smoothing_parameter', 0, missing="info")
    number_of_lines = StatusVar('number_of_lines', 50)

    # signals
    signal_stabilise_cavity = QtCore.Signal()
    signal_optimize_length = QtCore.Signal(float, bool)
    signal_scan_next_line = QtCore.Signal()

    class Axis:  # Todo this needs a better name here as it also applies for the APD and the NIDAQ output
        # Todo: I am not sure fi this inheritance is sensible (Generic logic)
        def __init__(self, name, feedback_device, output_device, log):
            self.name = name

            self.feedback_device = feedback_device
            self.output_device = output_device
            self.input_voltage_range = []
            self.output_voltage_range = []
            self.feedback_precision_volt = None
            self.output_precision_volt = None
            self.output_voltage = 0
            self.voltage_adjustment_steps = 1  # in mV

            self.log = log

            # initialise values
            if name in self.output_device._analogue_output_channels.keys():
                self.output = True
            else:
                self.output = False
            if name in self.feedback_device._analogue_input_channels.keys():
                self.feedback = True
            else:
                self.feedback = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Todo: Add initialisation from _statusVariable
        # Connectors
        self._feedback_device = self.get_connector('analoguereader')
        self._output_device = self.get_connector('analogueoutput')
        self._save_logic = self.get_connector('savelogic')

        # Fixme: This is very specific
        # first steps to get a to a better handling of axes parameters
        if self.control_axis not in self._axis:
            self.log.error("The given control %s axis is not a axis of the initialised module.",
                           self.control_axis)
            raise Exception('Failed to initialise cavity scanner module due to analogue output failure.')

        if self.control_axis not in self._axis:
            self.log.error("The given feedback %s axis is not a axis of the initialised module.",
                           self.feedback_axis)
            raise Exception('Failed to initialise cavity scanner module due to analogue output failure.')

        self.axis_class = dict()

        for name in self._axis:
            self.axis_class[name] = self.Axis(name, self._feedback_device,
                                              self._output_device, self.log)
            # Todo: Add error check here or in method else it tries to write non existing value into itself
            if self.axis_class[name].feedback:
                self.axis_class[name].input_voltage_range = self._get_feedback_voltage_range(name)
                self.axis_class[name].feedback_precision_volt = self.calculate_feedback_precision(name)
            if self.axis_class[name].output:
                self.axis_class[name].output_voltage_range = self._get_output_voltage_range(name)
                self.axis_class[name].output_precision_volt = self.calculate_control_precision(name)

        if not self.axis_class[self.control_axis].output:
            self.log.error(
                "The chosen stabilisation axis has not analogue output channel. The axis can not be stabilised")
        if self.feedback_axis not in self.axis_class.keys():
            self.log.error("The given stabilisation axis is not defined. Program will fatally fail using this axis")
        if not self.axis_class[self.feedback_axis].feedback:
            self.log.error(
                "The chosen feedback axis has not feedback read. The feedback axis is not possible")

        # This is done in order to have a sensible threshold and step_size
        self.threshold = float_rounding(self.threshold, self.axis_class[self.feedback_axis].feedback_precision_volt)
        self.voltage_adjustment_steps = float_rounding(self.voltage_adjustment_steps,
                                                       self.axis_class[self.control_axis].output_precision_volt)
        self.stopRequested = False

        # Sets connections between signals and functions
        self.signal_stabilise_cavity.connect(self._stabilise_cavity_length, QtCore.Qt.QueuedConnection)
        self.signal_optimize_length.connect(self._optimize_cavity_length, QtCore.Qt.QueuedConnection)
        self.signal_scan_next_line.connect(self._do_next_line, QtCore.Qt.QueuedConnection)

        # Cavity_scanning
        self.smoothing = False  # defines if smoothing at beginning and end of ramp should be done to protect piezo
        self._start_voltage = 0.0
        self._end_voltage = 1.0
        self.ramp = self._generate_ramp(self._start_voltage, self._end_voltage)
        self.scan_direction = True
        self._clock_frequency = self._scan_frequency * len(self.ramp)
        self.input = 0
        self.scan_raw_data = np.zeros([self.number_of_lines, len(self.ramp)])
        self.elapsed_sweeps = 0
        self.start_time = time.time()
        self.stop_time = time.time()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        pass
        # Todo: This method nees to be implemented

    # =============================== start cavity stabilisation Commands  =======================
    def initialise_readout(self):
        """Sets up the continuous analogue input reader

        @return int: error code (0:OK, -1:error)
        """
        return self._feedback_device.set_up_analogue_voltage_reader(self.feedback_axis)

    def close_readout(self):
        """Closes the continuous analogue input reader

        @return int: error code (0:OK, -1:error)
        """
        if 0 > self._feedback_device.close_analogue_voltage_reader(self.feedback_axis):
            self.log.error("It was not possible to close the analog voltage reader")
            return -1
        return 0

    def initialise_analogue_stabilisation(self):
        """Sets up the analog output channel used to stabilise the length of the cavity

        @return int: error code (0:OK, -1:error)"""
        return self._output_device.set_up_analogue_output([self.control_axis])

    def close_analogue_stabilisation(self):
        """Closes up the analog output channel used to stabilise the length of the cavity

        @return int: error code (0:OK, -1:error)"""
        return self._output_device.close_analogue_output(self.control_axis)

    def start_cavity_stabilisation(self):
        """Starts the process of cavity stabilisation"""
        if self.initialise_readout() < 0:
            self.log.error(
                "initialising the cavity stabilisation process failed.\ The analog input could not be initialised")
            return -1
        if self.initialise_analogue_stabilisation() < 0:
            self.log.error(
                "initialising the cavity stabilisation process failed.\ The analog output could not be initialised")
            return -1

        self.signal_stabilise_cavity.emit()

    def _stabilise_cavity_length(self):
        """Stabilises the cavity length via a software feedback loop"""
        if self.stopRequested:
            try:
                self.close_analogue_stabilisation()
            except Exception as e:
                self.log.exception('Could not close the analogue output.')
            try:
                self.close_readout()
            except Exception as e:
                self.log.exception('Could not close the analogue input reader.')
            self.stopRequested = False
            self.log.info("Cavity stabilisation stopped successfully")
            return

        # fixme: This needs to be dione with analogue voltage scanner. this is only a quick fix
        voltage_list = []
        for i in range(self._average_number):
            result = self._feedback_device.get_analogue_voltage_reader([self.feedback_axis], read_samples=1)
            if result[1] == 0:
                self.stopRequested = True
                self.log.error("reading the axis voltage failed")
                return -1
            voltage_list.append(result[0][0])
        voltage_result = sum(voltage_list) / self._average_number

        # checks if the measured values lie outside the threshold
        if self.reflection:
            if voltage_result > self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.feedback_axis].feedback_precision_volt:
                self._optimize_cavity_length(voltage_result)
                # Todo: it might make sense to make an intelligent optimisation algorithm, that remembers the direction
                # that worked at the last optimisation. this is especially sensible for drift ins one direction,
                # but not helpful for random fluctuations or non directional vibrations. Might help for length changes
                # during step scanning due to tilted samples. Here we assume now moving in the same direction
                # will be enough
        else:
            if voltage_result < self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.feedback_axis].feedback_precision_voltage:
                self._optimize_cavity_length(voltage_result)

        # if a maximum speed of the readout should be wanted a time.sleep can be added.
        # for this one should measure the time the operation requires. The difference between the minimum time between
        # steps and the time elapsed can then be stayed in the sleep state by the program

        self.signal_stabilise_cavity.emit()

    def _optimize_cavity_length(self, previous_voltage, direction=True):
        """ Changes cavity length by a PID loop kind of function to get the voltage value below the threshold again

        @return int:  not clear yet
        """
        precision = self.axis_class[self.feedback_axis].feedback_precision_volt

        # Todo: Maybe it is sensible to make a safety net of: it can only be repeated 500 times or something
        # before it has to stop
        if self.stopRequested:
            return 0

        voltage_result = self.change_and_measure(self.feedback_axis, self.control_axis,
                                                 voltage=self.voltage_adjustment_steps,
                                                 direction=direction)
        if voltage_result < 0:
            self.stopRequested = True
            return -1

        if self.reflection:
            # check if resonances has been reached
            if voltage_result < self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.feedback_axis].feedback_precision_volt:
                # the optimisation has been successful. Stop method
                return 0
        else:
            # check if resonances has been reached
            if voltage_result > self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.feedback_axis].feedback_precision_volt:
                return 0

        # update position and leave algorithm if position was reached.
        if abs(voltage_result - previous_voltage) < precision:  # comparing floats
            # redo stepping. If nothing happens again we are either on resonance or completely off resonance
            # or the values were chosen wrong.
            # In any case this has to be optimised by user
            voltage_result = self.change_and_measure(self.feedback_axis, self.control_axis,
                                                     voltage=self.voltage_adjustment_steps,
                                                     direction=direction)
            if voltage_result < 0:
                self.stopRequested = True
                return -1
            if abs(voltage_result - previous_voltage) < precision:  # comparing floats
                # move back to previous position. This is a safety precaution
                voltage_result = self.change_and_measure(self.feedback_axis, self.control_axis,
                                                         voltage=self.voltage_adjustment_steps,
                                                         direction=not direction)
                if voltage_result < 0:
                    self.stopRequested = True
                    return -1
                return 0

        if self.reflection:
            # check if resonances has been reached
            if voltage_result < self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.feedback_axis].feedback_precision_volt:
                # the optimisation has been successful. Stop method
                return 0
            # else check if stepping direction was sensible
            if voltage_result > previous_voltage:
                # change direction
                direction = not direction
                # else: keep direction
        else:
            # check if resonances has been reached
            if voltage_result > self.threshold and abs(self.threshold - voltage_result) > \
                    self.axis_class[self.feedback_axis].feedback_precision_volt:
                return 0
            # else check if stepping direction was sensible
            if voltage_result > previous_voltage:
                # change direction
                direction = not direction
                # else: keep direction

        self.signal_optimize_length.emit(voltage_result, direction)

    def stop_cavity_stabilisation(self):
        """Stops the process of cavity stabilisation"""
        self.stopRequested = True

    def change_cavity_length(self, axis_name, voltage, direction=True):
        """Changes cavity length by changing voltage at analogue output

        :param str axis_name: The name of the axis for which the voltage is to be changed
        :param float voltage: The relative voltage change
        :param bool direction: The direction in which the voltage is to be changed. True: voltage is added relative,
                                False: voltage is subtracted

        :return int: error code (0:OK, -1:error)"""

        if not self.axis_class[axis_name].output:
            self.log.error("Axis %s of cavity can not be changed in length as it can not be accessed."
                           " \n No output for axis defined.", axis_name)
            return -1

        if direction:
            new_voltage = self.axis_class[axis_name].output_voltage + voltage
        else:
            new_voltage = self.axis_class[axis_name].output_voltage - voltage
        # fixme: the method doesn't check yet if this voltage change will have any effect as it might be below resolution
        if in_range(new_voltage, self.axis_class[axis_name].output_voltage_range[0],
                    self.axis_class[axis_name].output_voltage_range[1]):
            self._output_device.write_ao(axis_name, np.array(new_voltage), length=1, start=True)
            self.axis_class[axis_name].output_voltage = new_voltage
            return 0
        return -1

    def change_and_measure(self, feedback_axis, controlled_axis, voltage, direction=True):
        """Changes cavity length and measures effect on the cavity afterwards.

        :param str feedback_axis: The name of the axis which gives feedback on the cavity length/ resonance position
        :param str controlled_axis: The name of the axis that is used to controlled the cavity length
        :param float voltage: The relative voltage change
        :param bool direction: The direction in which the voltage is to be changed. True: voltage is added relative,
                                False: voltage is subtracted

        :return float: feedback result of the cavity axis in V, -1 for error"""

        self.change_cavity_length(controlled_axis, voltage, direction=direction)
        time.sleep(0.00001)  # 10mus. This is very long compared to the NIDAQ clock rate
        # Todo: Do we even need this here?

        # compare new voltage to threshold
        voltage_list = []
        for i in range(self._average_number):
            result = self._feedback_device.get_analogue_voltage_reader([feedback_axis], read_samples=1)
            if result[1] == 0:
                self.stopRequested = True
                self.log.error("reading the axis voltage failed")
                return -1
            voltage_list.append(result[0][0])
        voltage_result = sum(voltage_list) / self._average_number
        return voltage_result

    def _get_feedback_voltage_range(self, axis_name):
        """Gets the voltage range of the position feedback device for a specific axis that can be converted to positions

        @axis_name The axis for which the voltage range is retrieved

        @ return list: min and max possible voltage in feedback for given axis"""
        return self._feedback_device._ai_voltage_range[axis_name]

    def _get_output_voltage_range(self, axis_name):
        """Gets the voltage range of the output device for a specific axis

        @axis_name The axis for which the voltage range is retrieved

        @ return list: min and max possible voltage in feedback for given axis"""
        return self._output_device._ao_voltage_range[axis_name]

    def calculate_control_precision(self, axis_name):
        """Calculates the position feedback devices precision for a given axis

        @param str axis_name: The name of the axis for which the precision is to be calculated

        @return float: precision of the feedback device volt  (-1.0 for error)
        """
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1

        return self.calculate_resolution(self._output_device.get_analogue_resolution(),
                                         self.axis_class[axis_name].output_voltage_range)

    def calculate_feedback_precision(self, axis_name):
        """Calculates the position feedback devices precision for a given axis

        @param str axis_name: The name of the axis for which the precision is to be calculated

        @return float: precision of the feedback device volt  (-1.0 for error)
        """
        if axis_name not in self.axis_class.keys():
            self.log.error("%s is not a possible axis. Therefore it is not possible to change its position", axis_name)
            return -1

        return self.calculate_resolution(self._feedback_device.get_analogue_resolution(),
                                         self.axis_class[axis_name].input_voltage_range)

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

    def change_analogue_output_voltage(self, end_voltage):
        """Sets the analogue voltage for the control axis to desired voltage in a smooth step vice manner
        """
        start_voltage = self.axis_class[self.control_axis].output_voltage
        v_range = self.axis_class[self.control_axis].output_voltage_range
        num_of_linear_steps = np.rint(abs((start_voltage - end_voltage)) / self._scan_resolution)
        ramp = np.linspace(start_voltage, end_voltage, num_of_linear_steps)
        if not in_range(end_voltage, v_range[0], v_range[1]):
            self.log.error("not possible to go to voltage %s outside of voltage range (%s)", end_voltage, v_range)
            return -1
        if abs(start_voltage - end_voltage) > self._scan_resolution:
            _clock_frequency = self._scan_frequency * len(ramp)
            if 0 > self.initialise_analogue_stabilisation():
                self.log.error("Setting up analogue output for scanning failed.")
                return -1

            if 0 > self._output_device.set_up_analogue_output_clock(clock_frequency=_clock_frequency):
                # Fixme: I do not think this is necessary. However it should be checked.
                # self.set_position('scanner')
                self.log.error("Problems setting up analogue output clock.")
                return -1

            self._output_device.configure_analogue_timing(self.control_axis, len(ramp))

            retval3 = self._output_device.analogue_scan_line(self.control_axis, ramp)
            try:
                retval1 = self._output_device.close_analogue_output_clock()
                retval2 = self._output_device.close_analogue_output(self.control_axis)
            except:
                self.log.warn("Closing the Analogue scanner did not work")
            if retval3 != -1:
                self.axis_class[self.control_axis].output_voltage = end_voltage
            return min(retval1, retval2, retval3)
        else:
            self.log.info("The device was already at required output voltage")
            return 0

    def change_voltage_adjustment_steps(self, step_size):
        """Changes the adjustment step size of the algorithm setting it to a value compatible with the hardware

        @return: The actual new adjustment step size
        """
        self.voltage_adjustment_steps = float_rounding(step_size,
                                                       self.axis_class[self.control_axis].output_precision_volt)
        return self.voltage_adjustment_steps

    # =============================== stop cavity stabilisation Commands  =======================

    # =============================== start cavity scanning Commands  =======================
    def _initialise_scanner(self):
        """Initialise the clock and locks for a scan"""
        # Fixme: Do error catch/test

        # generate voltage ramp
        self.ramp = self._generate_ramp(self._start_voltage, self._end_voltage)
        if self.ramp[0] == -1:
            self.log.error("Not possible to initialise scanner as ramp was not generated")
            return 0
        self.down_ramp = self.ramp[::-1]

        # move piezo to desired start position to go easy on piezo
        self.change_analogue_output_voltage(self._start_voltage)

        # do the actual initialisation of the scanner
        self._clock_frequency = self._scan_frequency * len(self.ramp)
        if 0 > self.initialise_analogue_stabilisation():
            self.log.error("Setting up analogue output for scanning failed.")
            return -1

        if 0 > self._output_device.set_up_analogue_output_clock(clock_frequency=self._clock_frequency):
            # Fixme: I do not think this is necessary. However it should be checked.
            # self.set_position('scanner')
            self.log.error("Problems setting up analogue output clock.")
            self.close_analogue_stabilisation()
            return -1

        if 0 > self._output_device.configure_analogue_timing(self.control_axis, len(self.ramp)):
            self.log.error("Not possible to set appropriate timing for analogue scan.")
            self.close_analogue_stabilisation()
            self._output_device.close_analogue_output_clock()
            return -1

        # Initialise analogue input readout
        # Fixme: This needs still to be verified
        # The clock needs half speed because internally only halve the clock speed is taken
        if 0 < self._feedback_device.set_up_analogue_voltage_reader_clock(clock_frequency=self._clock_frequency / 2,
                                                                          set_up=False):
            self.log.error("Setting up analogue input clock for scanning failed.")
            self._close_scanner()
            return -1
        if 0 < self._feedback_device.set_up_analogue_voltage_reader_scanner(len(self.ramp),
                                                                            self.feedback_axis,
                                                                            clock_channel=None):
            self.log.error("Setting up analogue input for scanning failed.")
            self._close_scanner()
            return -1

        # initialise data recording
        self.elapsed_sweeps = 0
        self.histo_count = 0
        self._initialise_data_matrix()

        return 0

    def _close_scanner(self):
        try:
            retval1 = self._output_device.close_analogue_output_clock()
            retval2 = self._output_device.close_analogue_output(self.control_axis)
            retval3 = self._feedback_device.close_analogue_voltage_reader(self.feedback_axis)
        except:
            self.log.warn("Closing the Scanner did not work")
        return min(retval1, retval2, retval3)

    def _generate_ramp(self, start_voltage, end_voltage):
        """Generate a ramp from start_voltage to end_voltage that
        satisfies the general step resolution and smoothing_steps parameters.
        Smoothing_steps=0 means that the ramp is just linear.

        @param float start_voltage: voltage at start of ramp.

        @param float end_voltage: voltage at end of ramp.

        @return  array(float): the calculated voltage ramp
        """

        voltage_range = self.axis_class[self.control_axis].output_voltage_range
        # check if given voltages are allowed:
        if not in_range(start_voltage, self.axis_class[self.control_axis].output_voltage_range[0],
                        self.axis_class[self.control_axis].output_voltage_range[1]):
            self.log.error("The given start voltage %s is not within the possible output voltages %s", start_voltage,
                           voltage_range)
            return [-1]
        elif not in_range(start_voltage, self.axis_class[self.control_axis].output_voltage_range[0],
                          self.axis_class[self.control_axis].output_voltage_range[1]):
            self.log.error("The given end voltage %s is not within the possible output voltages %s", end_voltage,
                           voltage_range)
            return [-1]
        # It is much easier to calculate the smoothed ramp for just one direction (upwards),
        # and then to reverse it if a downwards ramp is required.
        v_min = min(start_voltage, end_voltage)
        v_max = max(start_voltage, end_voltage)

        if v_min == v_max:
            ramp = np.array([v_min, v_max])

        else:
            smoothing_range = self._smoothing_steps + 1

            # Sanity check in case the range is too short
            # The voltage range covered while accelerating in the smoothing steps
            v_range_of_accel = sum(n * self._scan_resolution / smoothing_range
                                   for n in range(0, smoothing_range)
                                   )

            # Obtain voltage bounds for the linear part of the ramp
            v_min_linear = v_min + v_range_of_accel
            v_max_linear = v_max - v_range_of_accel

            # calculate smooth ramp if needed and possible
            if self.smoothing and v_min_linear < v_max_linear:

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / self._scan_resolution)
                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array([sum(n * self._scan_resolution / smoothing_range
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
                num_of_linear_steps = np.rint((v_max - v_min) / self._scan_resolution)
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

    def _scan_line(self, voltages):
        try:
            if 0 < self._feedback_device.start_analogue_voltage_reader(self.feedback_axis):
                return [-1]
            self._output_device.analogue_scan_line(self.control_axis, voltages)
            self.input = self._feedback_device.get_analogue_voltage_reader([self.feedback_axis])
            if 0 < self._feedback_device.stop_analogue_voltage_reader(self.feedback_axis):
                return [-1]
            return self.input[0]

        except Exception as e:
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_scanning()
            # if self.hold_max is True:
            #   self.signal_scan_next_line.emit()
            raise e

    def _do_next_line(self):
        """If stopRequested then finish the scan, otherwise perform next repeat of the scan line

        """

        if self.stopRequested:
            self._close_scanner()
            #     self._scan_counter = 0
            #     self.number_of_repeats = 1
            #     self.stop_histo_time = time.time()
            self.stopRequested = False
            if self.scan_direction:
                final_voltage = self._start_voltage
            else:
                final_voltage = self._end_voltage
            self.axis_class[self.control_axis].output_voltage = final_voltage
            self.scan_direction = True
            return 0

        if self.elapsed_sweeps == 0:
            # move from current voltage to start of scan range.
            self.start_histo_time = time.time()
            # self._goto_during_scan(self.scan_range[0])

        if self.scan_direction:
            self.start_time = time.time()
            counts = self._scan_line(self.ramp)
            # self.scan_matrix[1] = np.add(self.scan_matrix[1], counts)
            self.stop_time = time.time()
        else:
            self.start_time = time.time()
            counts = self._scan_line(self.down_ramp)
            # self.scan_matrix[1] = np.add(self.scan_matrix[1], counts[::-1])
            # counts = counts[::-1]n
            self.stop_time = time.time()
        if len(counts) != len(self.ramp):
            self.log.error("Something didn't work in the cavity scan. Stopping procedure")
            self.stopRequested = True
            return

        if self.elapsed_sweeps == (self.scan_raw_data.shape[0] - 1):
            expanded_array = np.zeros([self.scan_raw_data.shape[0] + self.number_of_lines,
                                       self.scan_raw_data.shape[1]])
            expanded_array[:self.elapsed_sweeps, :] = self.scan_raw_data[
                                                      :self.elapsed_sweeps, :]
            self.scan_raw_data = expanded_array
            self.log.warning('raw data array in CavityScannerLogic was not big enough for the entire '
                             'measurement. Array will be expanded.\nOld array shape was '
                             '(%s, %s), new shape is (%s, %s).'
                             , self.scan_raw_data.shape[0] - self.number_of_lines,
                             self.scan_raw_data.shape[1],
                             self.scan_raw_data.shape[0],
                             self.scan_raw_data.shape[1])
        self.scan_direction = not self.scan_direction

        self.scan_raw_data[1:self.elapsed_sweeps + 1, :] = self.scan_raw_data[
                                                           :self.elapsed_sweeps, :]
        self.scan_raw_data[0, :] = counts

        # self.scan_matrix[0] = counts
        # self.data_to_save = True
        # self.histo_save = True
        self.elapsed_sweeps += 1
        self.histo_count += 1
        # self.sigCounterUpdated.emit()
        # self.sigHistoUpdated.emit()
        self.signal_scan_next_line.emit()

    def _initialise_data_matrix(self):
        """ Initializing the ODMR matrix plot. """
        estimated_number_of_lines = int(1.5 * self.number_of_lines)  # Safety
        self.log.debug('Estimated number of raw data lines: %s'
                       '', estimated_number_of_lines)
        self.scan_raw_data = np.zeros([estimated_number_of_lines, len(self.ramp)])

    def save_data(self):
        """ Save the counter trace data and writes it to a file.

        @return int: error code (0:OK, -1:error)
        """

        filepath = self._save_logic.get_path_for_module(module_name='CavityScan')
        filelabel = 'cavity_scan'
        # filelabel2 = 'pi_scan_histo'
        timestamp = datetime.datetime.now()

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        ramp_data = np.tile(np.append(self.ramp, self.down_ramp), int(self.elapsed_sweeps / 2))
        # if odd # of scans one more ramp needs to be added
        if (self.elapsed_sweeps % 2) == 1:
            np.append(ramp_data, self.ramp)

        scan_data = self.scan_raw_data[:self.elapsed_sweeps, :]
        data['Voltage (V)'] = ramp_data.flatten()
        data['Analogue input (Voltage/bin)'] = scan_data.flatten()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start (m)'] = self._start_voltage
        parameters['Stop (m)'] = self._end_voltage
        parameters['Steps per ramp(#)'] = len(self.ramp)
        parameters['Ramps executed (#)'] = self.elapsed_sweeps
        parameters['Clock Frequency (Hz)'] = self._clock_frequency
        parameters['ScanSpeed (Hz)'] = self._scan_frequency
        parameters['Volts per meter (V/m)'] = abs(self._start_voltage - self._end_voltage) / self._scan_frequency
        parameters['Start Time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self.start_time))
        parameters['Stop Time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self.stop_time))

        # fig = self.draw_figure([self.scan_matrix[0], self.ramp])

        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   fmt='%.6e',
                                   delimiter='\t')  # ,
        # plotfig=fig)
        return 0
