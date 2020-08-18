# -*- coding: utf-8 -*-
"""
This module operates a 3D Microscope.

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
import datetime
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import math
from io import BytesIO

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.module import Connector, ConfigOption, StatusVar


def round_to_2(x):
    """Rounds to the second significant figure of a number"""
    return round(x, -int(math.floor(math.log10(abs(x)))) + 1)


def in_range(x, min, max):
    """Checks if given value is within a range

    @param float x: value to be checked
    @param float min: lower limit
    @param float max: upper limit
    @return bool: true if x lies within [min,max]
    """
    return (min is None or min <= x) and (max is None or max >= x)


# Todo: rename analog input into something less ambiguous: input might be input into the hardware,
#  or what this logic puts into the hardware
class Scanner3DLogic(GenericLogic):
    """
    This is the Logic class for confocal scanning.
    """
    _modclass = 'Scanner3Dlogic'
    _modtype = 'logic'

    # declare connectors
    scanner1 = Connector(interface='ConfocalScannerInterface')
    savelogic = Connector(interface='SaveLogic')
    digitalcounter = Connector(interface='FiniteCounterInterface')
    analoguereader = Connector(interface='AnalogueReaderInterface')
    analogueoutput = Connector(interface='AnalogueOutputInterface')
    stepperlogic = Connector(interface='ConfocalStepperLogic')

    # status vars
    _clock_frequency = StatusVar('clock_frequency', 500)
    return_frequency = StatusVar(default=500)

    # config
    scan_resolution_fast_axis = ConfigOption('3D_scan_resolution', 1e-6, missing="warn")
    _ai_counter = ConfigOption("AI_counter", None, missing="warn")
    _scan_freq_per_m = ConfigOption("position_movement_scan_speed", 1, missing="warn")
    # Todo: Add to config. This decides if the scanner does a work around for scan systems that have a maximum step size
    _min_steps = ConfigOption('min_steps_per_m', 1, missing="warn")

    # signals
    signal_start_scanning = QtCore.Signal(str)
    signal_continue_scanning = QtCore.Signal(str)
    signal_stop_scanning = QtCore.Signal()
    signal_scan_line_next = QtCore.Signal()
    signal_image_updated = QtCore.Signal()
    signal_change_position = QtCore.Signal(str)
    signal_data_saved = QtCore.Signal()
    signal_draw_figure_completed = QtCore.Signal()
    signal_position_changed = QtCore.Signal()
    signal_sort_count_data = QtCore.Signal(tuple, int)

    sigImageInitialized = QtCore.Signal()

    # Todo: Move to starting position at beginning of scan/at end of scan

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        # counter for scan_image
        self._scan_counter = 0
        self.stopRequested = False
        self.permanent_scan = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Connectors
        self._counting_device = self.digitalcounter()
        self._analog_counting_device = self.analoguereader()
        self._scanning_device = self.analogueoutput()
        self._stepper_logic = self.stepperlogic()
        self._save_logic = self.savelogic()

        # Sets connections between signals and functions
        self.signal_scan_line_next.connect(self._scan_line_3D, QtCore.Qt.QueuedConnection)
        self.signal_start_scanning.connect(self.start_3D_scan, QtCore.Qt.QueuedConnection)
        self.signal_continue_scanning.connect(self.continue_3D_scan, QtCore.Qt.QueuedConnection)

        self.signal_sort_count_data.connect(self._sort_data, QtCore.Qt.DirectConnection)

        # self._change_position('activation')

        # Reads in the maximal scanning range. The unit of that scan range is meters!
        self._scanning_axes_ranges = OrderedDict()
        self._scanning_axes_ranges["x"] = self._scanning_device.get_position_range()[0]
        self._scanning_axes_ranges["y"] = self._scanning_device.get_position_range()[1]
        self._scanning_axes_ranges["z"] = self._scanning_device.get_position_range()[2]
        self._ao_channels = list(self._scanning_axes_ranges.keys())

        # Sets the current position to the center of the maximal scanning range
        # Todo: In general these should be defined by the config and
        #  it should be checked if they havent already been set
        # by another program
        self._current_position = OrderedDict()
        self._current_position["x"] = self._scanning_axes_ranges["x"][0]
        self._current_position["y"] = self._scanning_axes_ranges["y"][0]
        self._current_position["z"] = self._scanning_axes_ranges["z"][0]
        self._current_position["a"] = 0.0

        # Sets the size of the image to the maximal scanning range
        self.image_ranges = OrderedDict()
        self.image_ranges["x"] = self._scanning_axes_ranges["x"]
        self.image_ranges["y"] = self._scanning_axes_ranges["y"]
        self.image_ranges["z"] = self._scanning_axes_ranges["z"]

        # Default values for the resolution of the scan
        # Todo: it is very problematic that this is done in points per scan range,
        #  whereas the third axis is done in mum resolution
        self.xy_resolution = 20
        self.dim_addition = 0
        # Todo: there must be an option to define this for every axis
        self._max_scan_speed_single_axis = 10  # (Hz/V)
        self._min_scan_resolution = 0.005  # (V)

        # Variable to check if a scan is continuable
        self.scan_counter = 0
        self._scan_continuable = False

        self._analog_counting = True
        self.go_to_start_positions = False

        self.scan_freq_fast_axis = 5.0  # Hz, the freq. to scan the whole measurement range of the fast axis

        self._double_3rd_axis_scan = False
        self._use_maximal_resolution_fast_axis = False
        self.smoothing = False
        self._fast_axis_smoothing_steps = 10
        # Todo:this needs to be calculated after everything else is set
        self._clock_frequency_3D_scan = 10000

        # Position_feedback
        # Todo: Define sensible axes
        self._ai_position_feedback_axes = []
        self.map_scan_positions = True
        # Todo: shouldnt this be dependent on the analogue reader ?
        if self._ai_counter != None:
            if self._ai_counter in self._counting_device._analogue_input_channels:
                self._ai_scanner = True
            else:
                self._ai_scanner = False
        else:
            self._ai_scanner = False
        self._ai_axes = {"x": "x_pos_voltages", "y": "y_pos_voltages", "z": "z_pos_voltages",
                         self._ai_counter: "AI_counter_" + str(self._ai_counter)}
        self.current_ai_axes = []
        if self._ai_scanner:
            self.current_ai_axes.append(self._ai_counter)

        if self.map_scan_positions:
            # Todo: This is too simple as it assumes that the scan axes are always named like this and sorted like this
            self.current_ai_axes.append("x")
            self.current_ai_axes.append("y")
            self.current_ai_axes.append("z")

        self._save_positions = True

        # change scan direction variables
        self._inverted_scan = False

        self._get_scanner_count_channels()
        self.initialize_image()
        self.generate_file_path()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def _use_maximal_resolution(self):
        """
        Sets the 3rd axis scan resolution to maximum and checks if the values to be set are feasible for the
        given hardware

        @return int: error code (0:OK, -1:error)        """
        # Todo: integrate this function into scan

        # Todo: This needs to be flexible: the 3rd axis

        self.scan_resolution_fast_axis = self.calculate_resolution(
            self._analog_counting_device.get_analogue_resolution(),
            self._scanning_axes_ranges["z"])
        if self.scan_resolution_fast_axis == -1:
            self.log.error("Calculated scan resolution not possible")
            return -1

        # Todo: Check if scan freq is still reasonable.
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

    def _convert_v_to_pos(self, voltage, axis):
        """
        Converts a voltage to a position for a given axes
        @param float voltage: The voltage to be converted
        @param str axis: The axis for which the voltage is to be converted
        @return: the position
        """
        # Todo: The ranges should be defined by a dict and then this should be calculated using the dic
        # With the if and list it is only a fast work around and not error safe

        v_range = self._scanning_device._a_o_ranges[axis]
        pos_range = self._scanning_axes_ranges[axis]
        pos = (pos_range[1] - pos_range[0]) / (v_range[1] - v_range[0]) * (voltage - pos_range[0]) + pos_range[0]
        return pos

    def convert_pos_to_v(self, pos, axis):
        """Converts a position value to a voltage value
        @param float pos: The position to be converted
        @param str axis: The axes for which the voltage is to be converted
        @return float: the calculated voltage
        """
        # todo: this only works for the fast axis
        v_range = self._scanning_device._a_o_ranges[axis]
        pos_range = self._scanning_axes_ranges[axis]
        voltage = (v_range[1] - v_range[0]) / (pos_range[1] - pos_range[0]) * (
                pos - pos_range[0]) + v_range[0]

        return voltage

    def _check_if_pos_in_range(self, position, axis):
        """Checks if a selected position is allowed by checking if it lies within the possible range of positions
            @param float position: The voltage to be checked
            @param str axis:  The axis for which is checked if given position lies within range
            @return int: error code (0:OK, -1:error)
        """
        # Todo: check if parameters full fill conditions (str,float)
        if not in_range(position, self._scanning_axes_ranges[axis][0], self._scanning_axes_ranges[axis][1]):
            self.log.error("The given position %s is not within the range of possible positions %s", position,
                           self._scanning_axes_ranges[axis])
            return -1
        else:
            return 0

    ################################### Main Scan Functions ################################
    def _initialize_measurement(self, steps, frequency, ai_channels):
        """Setups the hardware.
        After calling this function parts of the hardware might be "blocked" by this logic

        @param int steps: the steps that are to be scanned for one line of the measurement (fast*medium axes steps)
        @param float frequency:the frequency with which  each data point  is to be acquired
        @param list [str] ai_channels: the analogue input channels used during the measurement,
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
            self.module_state.unlock()
            self.stopRequested = True
            return -1

        # Todo: These setups need to take place in the hardware in someway. this is to specific for a logic

        # setup analogue output
        if 0 > self._scanning_device.set_up_analogue_output(self._ao_channels):
            self.log.error("Problems setting up analogue out put for 3D step scan on channel (%s)",
                           self._ao_channels)
            self.stopRequested = True
        clock_channels = ai_channels.copy()
        for channel in self._ao_channels:
            if channel not in clock_channels:
                clock_channels.append(channel)

        if 0 > self._analog_counting_device.add_clock_task_to_channel("Scanner_clock", clock_channels):
            self.log.error("Problems setting up analogue input and output clock.")
            self.stopRequested = True

        if 0 > self._scanning_device.configure_analogue_timing(self._ao_channels[0], steps):
            self.log.error("Not possible to set appropriate timing for analogue scan.")
            self._output_device.close_analogue_output(self._ao_channels[0])
            self.stopRequested = True

        # setup analogue input if existing
        if ai_channels:  # checks if list is not empty
            if 0 > self._analog_counting_device.set_up_analogue_voltage_reader_scanner(
                    steps, ai_channels[0]):
                self.stopRequested = True
            else:
                if len(ai_channels) > 1:
                    if 0 > self._analog_counting_device.add_analogue_reader_channel_to_measurement(
                            ai_channels[0], ai_channels[1:]):
                        self.stopRequested = True

        # Todo: kill the running task in NIDAQ (hardware) if something goes wrong setting up
        if self.stopRequested:
            return -1
        return 0

    def start_3D_scan(self):
        """
        Sets up all hardware functions necessary for the 3D Scan and starts measurement procedure.

        This is a 3D measurement where the scanner moves 3 axis simultaneously.
        The first axis is scanned up/down or (up and down) and down for every step of the  second axis,
        while the third axis is changed at the end of each line scan.

        """

        # Todo: Do we need a lock?
        self._scan_counter = 0
        self.module_state.lock()

        # check if scan positions should be saved and if it is possible
        self.current_ai_axes = []
        if self._ai_scanner:
            self.current_ai_axes.append(self._ai_counter)

        if self.map_scan_positions:
            # Todo: This is too simple as it assumes that the scan axes are always named like this and sorted like this
            self.current_ai_axes.append("x")
            self.current_ai_axes.append("y")
            self.current_ai_axes.append("z")

        # Todo: Maybe something to implement later: Check axis and how they are to be scanned
        # (which one is first, second, third axis)
        if self._use_maximal_resolution_fast_axis:
            if 0 > self._use_maximal_resolution():
                self.log.error("Error setting resolution for 3rd axis to maximum")
                return -1

        # Initialize data
        if self.initialize_image() < 0:
            self.log.error("Initialisation of image failed. Scan stopped")
            return -1
        self.signal_image_updated.emit()
        first_new_scan_position = self._image_scanner[self._scan_counter, 0, 0]
        self.move_to_position(
            {"x": first_new_scan_position[0], "y": first_new_scan_position[1], "z": first_new_scan_position[2]},
            tag="scan")

        # The clock freq for each point is given by the freq used to scan one whole line on the fast axis
        self._clock_frequency_3D_scan = int(self.scan_freq_fast_axis * self._dim_fast_axis)

        # Todo: take care of hardware conflict with other logics
        # move piezo to desired start position to go easy on piezo
        # save starting positions
        self._start_position = [self._current_position["x"], self._current_position["y"], self._current_position["z"]]

        if 0 > self._initialize_measurement(steps=(self._dim_fast_axis + self.dim_addition) * self._dim_medium_axis,
                                            frequency=self._clock_frequency_3D_scan, ai_channels=
                                            self.current_ai_axes):
            self.module_state.unlock()
            return -1

        self.generate_file_path()
        self.generate_file_info()
        self._scan_continuable = True
        self.signal_scan_line_next.emit()
        self.save_to_npy("scanner_positions", self._image_scanner)

    def continue_3D_scan(self):
        """Continue scanning

        @return int: error code (0:OK, -1:error)
        """
        if not self._scan_continuable:
            self.log.warning("It is not possible to continue this scan")
            return -1
        if self._scan_counter == 0:
            self.start_3D_scan()
            return 0
        first_new_scan_position = self._image_scanner[self._scan_counter, 0, 0]
        self.move_to_position(
            {"x": first_new_scan_position[0], "y": first_new_scan_position[1], "z": first_new_scan_position[2]},
            tag="scan")
        if 0 > self._initialize_measurement(steps=(self._dim_fast_axis + self.dim_addition) * self._dim_medium_axis,
                                            frequency=self._clock_frequency_3D_scan, ai_channels=
                                            self.current_ai_axes):
            self._scan_continuable = False
            self.signal_stop_scanning.emit()
            return -1
        self.signal_scan_line_next.emit()
        # Todo: Use tags and signals to disable parts fo gui when program is scanning
        # self.signal_continue_scanning.emit(tag)

        return 0

    def stop_3D_scan(self):
        """Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        #self.signal_stop_scanning.emit()
        return 0

    def _scan_line_3D(self):
        """
            Steps a line of a 2D picture where for every point and additional 3rd axis is scanned.
            Listens for stop or end signal.
            Sorts data acquired during scan.
            Calls itself until end of measurement
            """

        # Todo: Make sure how to implement the thread locking here correctly.

        # If the scanning measurement is not running do nothing
        if self.module_state() != 'locked':
            return

        # stop scanning
        if self.stopRequested:
            with self.threadlock:
                self.kill_counter()
                if self.current_ai_axes:
                    self._analog_counting_device.close_analogue_voltage_reader(self.current_ai_axes[0])
                # if self.map_scan_positions:
                # Todo: Translate the voltage result from position voltage readout into positions
                # self.convert_voltage_to_position_for_image()
                # self.smooth_out_position_data()
                # Todo: Update current positions
                # if self.go_to_start_positions:
                #    self._change_position()
                self._scanning_device.close_analogue_output(self._ao_channels[0])

                self.stopRequested = False
                self.signal_image_updated.emit()
                self.signal_stop_scanning.emit()
                self.signal_change_position.emit("")
                self.log.info("3D Scanning stopped successfully")
                self.log.info("The scanner scanned %s lines", self._scan_counter)
                self.module_state.unlock()
                return

        # move and count
        new_counts = self._scan_and_count_3D(self._image_scanner[self._scan_counter], self.current_ai_axes)
        if type(new_counts) == int:
            self.stopRequested = True
            self.signal_scan_line_next.emit()
            self._scan_continuable = False
            return
        # Todo:
        # this might be a better way to catch errors:
        # new_counts = self._scan_and_count_3D(self.image[self._scan_counter, :, :, :3], self.current_ai_axes)
        # if np.any(new_counts == -1):
        #    self.stopRequested = True
        #    self.signal_scan_line_next.emit()
        #    return

        self.signal_sort_count_data.emit(new_counts, self._scan_counter)

        self._scan_counter += 1

        # check if at end of scan
        if self._scan_counter > self._dim_slow_axis - 1:
            self.stopRequested = True
            self._scan_continuable = False
            self.log.debug("3D Scan at end position")

        self.signal_scan_line_next.emit()

    def _scan_and_count_3D(self, scan_trajectory, ai_axes=[]):
        """
            Calls the hardware functions to step a line and checks if data required is sensible.

            @param List[][] scan_trajectory: The scan trajectory of all axis for this specfic part of the scan
                                            (eg. one line)
            @param list[] ai_axes: names of the analog input axes (eg. analog counter, position feedback)

            scan_trajectory for one line could look the following (for x,y,z axes):
                [   [[y_n, x_n1, z_n1],[ y_n, x_n1, z_n2],[y_n, x_n1, z_n3],[....],...],
                    [[y_n, x_n2, z_n1],[ ... ],[....],...],
                    ....]

            @return [np.array]: acquired data in counts/s or error value -1
                """

        # added, that the stepper now scans back and forth
        # Todo: This needs to optional
        retval = -1
        end_pos = scan_trajectory[-1, -1]
        # bring scan_trajectory into correct format:
        scan_trajectory_format = [scan_trajectory[:, :, 0].flatten(), scan_trajectory[:, :, 1].flatten(),
                                  scan_trajectory[:, :, 2].flatten()]
        # Todo: Check how c
        if self._counting_device.start_finite_counter(start_clock=False) < 0:
            self.log.error("Starting the counter failed")
            return [-1], []
        if ai_axes:
            if 0 > self._analog_counting_device.start_analogue_voltage_reader(ai_axes[0], start_clock=False):
                self.log.error("Starting the analogue input failed")
                return [-1], []

        if not np.array_equal(
                self._scanning_device.analogue_scan_line_positions(self._ao_channels, scan_trajectory_format),
                scan_trajectory_format):
            self.log.error("the scanning went wrong during line scan %s", self._scan_counter)
            return retval

        # get data
        count_result = self._counting_device.get_finite_counts()
        if ai_axes:
            analog_result = self._analog_counting_device.get_analogue_voltage_reader(ai_axes)

        error = self._counting_device.stop_finite_counter()
        self.update_current_position({"x": end_pos[0], "y": end_pos[1], "z": end_pos[2]})
        if ai_axes:
            if 0 > self._analog_counting_device.stop_analogue_voltage_reader(ai_axes[0]):
                self.log.error("Stopping the analog input failed")
                return retval

        if count_result[0][0] == [-1]:
            self.log.error("The readout of the counter failed")
            return retval
        elif error < 0:
            self.log.error("Stopping the counter failed")
            return retval
        elif ai_axes:
            if analog_result[0][0] == [-1]:
                self.log.error("The readout of the analog reader failed")
                return retval
            analog_counts = analog_result[0]

        digital_counts = count_result[0]

        if ai_axes:
            return digital_counts, analog_counts
        else:
            return [digital_counts]

    ################################### Supporting Scan Functions ##########################
    def _sort_data(self, counts, line_number):
        """
        Brings the data measured by the hardware into data packages that the program can handle

        @param np.array [m][n] counts: The data acquired for the 2D scan. length of m: amount of data channels acquired,
                                        length n points of data acquired
        @param int line: The line number of the slow axis for which the data was acquired
        """
        # TODO: This needs to also work if data is scanned up and down in one medium pixel. So far only up or down
        #  per medium pixel works
        # Todo: This only woks for one digital counter and one analog counter (not position feedback) so far. Fix!
        new_counts = []
        length_scan = self._dim_medium_axis
        name_save_addition = ""
        data_counter = 0

        # Digital Counter Data
        counts_digital = np.split(counts[data_counter], len(self._counts_ch))
        for i in range(len(self._counts_ch)):
            # sort data
            new_counts_uo = np.split(counts_digital[i], length_scan)  # split into single line pixel of medium axis
            new_counts_uo[1::2] = np.flip(new_counts_uo[1::2], 1)  # flip fast axis of every second pixel
            if line_number % 2 != 0:  # every second line scans the opposite direction so the data has to be inverted
                new_counts_uo = np.flip(new_counts_uo, 0)
            new_counts.append(np.concatenate(new_counts_uo))

            # save data
            self.save_to_npy("SPCM" + '_{0}'.format(self._counts_ch[i].replace('/', '')) + name_save_addition,
                             np.split(new_counts[i], length_scan), line_number)
            # make data available
            self.image_results[self._scan_counter, :, :, i] = np.split(new_counts[i], self._dim_medium_axis)
            self.image_2D[self._scan_counter, :, 3 + i] = np.mean(new_counts_uo, 1)
        data_counter += 1

        # Analog Counter Data
        new_counts_analog = {}
        if self.current_ai_axes:
            counts_analog_ch = np.split(counts[data_counter], len(self.current_ai_axes))
            # go through all analog channels
            for i in range(len(self.current_ai_axes)):
                # sort through analog input data
                new_counts_a = np.split(counts_analog_ch[i], length_scan)  # split into single line pixel of medium axis
                new_counts_a[1::2] = np.flip(new_counts_a[1::2], 1)  # flip fast axis of every second pixel
                # every second line scans the opposite direction so the data has to be inverted
                if line_number % 2 != 0:
                    new_counts_a = np.flip(new_counts_a,0)
                new_counts_analog[self.current_ai_axes[i]] = np.concatenate(new_counts_a)

            for key, value in new_counts_analog.items():
                # save data
                self.save_to_npy(self._ai_axes[key] + name_save_addition,
                                 np.split(value, length_scan), line_number)
                # make data available
                index_ai = self.current_ai_axes.index(key)
                self.image_results[self._scan_counter, :, :, len(self._counts_ch) + index_ai] = np.split(value,
                                                                                                         length_scan)
                self.image_2D[self._scan_counter, :, 3 + len(self._counts_ch) + index_ai] = np.mean(
                    np.split(value, length_scan), 1)

        self.signal_image_updated.emit()

    def find_change_in_coupling(self, array):
        """find the maximum change between minimum value and maximum value for each point for a given array
        """
        shape = np.shape(array)
        new_array = np.zeros(shape[:2])
        for i in range(shape[0]):
            for j in range(shape[1]):
                new_array[i, j] = np.ndarray.max(array[i, j]) - np.ndarray.min(array[i, j])
        return new_array

    def initialize_image(self):
        """Initialization of the image.

        @return int: error code (0:OK, -1:error)
        """
        # x1: x-start-value, x2: x-end-value
        x1, x2 = self.image_ranges["x"][0], self.image_ranges["x"][1]
        # y1: x-start-value, y2: x-end-value
        y1, y2 = self.image_ranges["y"][0], self.image_ranges["y"][1]
        # z1: x-start-value, z2: x-end-value
        z1, z2 = self.image_ranges["z"][0], self.image_ranges["z"][1]

        if self._check_if_pos_in_range(x1, "x") != 0 and \
                self._check_if_pos_in_range(x2, "x") != 0 and \
                self._check_if_pos_in_range(y1, "y") != 0 and \
                self._check_if_pos_in_range(y2, "y") != 0 and \
                self._check_if_pos_in_range(z1, "z") != 0 and \
                self._check_if_pos_in_range(z2, "z") != 0:
            return -1

        # Checks if the x-start and x-end value are ok
        if x2 < x1:
            self.log.error(
                'x1 must be smaller than x2, but they are '
                '({0:.3f},{1:.3f}).'.format(x1, x2))
            return -1

        # Checks if the y-start and y-end value are ok
        if y2 < y1:
            self.log.error(
                'y1 must be smaller than y2, but they are '
                '({0:.3f},{1:.3f}).'.format(y1, y2))
            return -1

        # generate x and y scan axis
        # prevents distortion of the image
        if (x2 - x1) >= (y2 - y1):
            self._X_Axis = np.linspace(x1, x2, max(self.xy_resolution, 2))
            self._Y_Axis = np.linspace(y1, y2, max(int(self.xy_resolution * (y2 - y1) / (x2 - x1)), 2))
        else:
            self._Y_Axis = np.linspace(y1, y2, max(self.xy_resolution, 2))
            self._X_Axis = np.linspace(x1, x2, max(int(self.xy_resolution * (x2 - x1) / (y2 - y1)), 2))

        # generate z scan axis (fast axis)
        self._Z_Axis = self._generate_voltage_ramp_3D(z1, z2)

        # axis dimensions
        self._dim_medium_axis = len(self._X_Axis)  # medium axis ("x")
        self._dim_slow_axis = len(self._Y_Axis)  # slow axis ("y")
        self._dim_fast_axis = len(self._Z_Axis)  # fast axis ("z")

        # check both axis and use then axes that needs a longer addition as the
        add_dim_medium = 0
        min_step_medium = int(self._min_steps * abs(self.image_ranges["x"][1] - self.image_ranges["x"][0]))
        if min_step_medium > self._dim_medium_axis:
            add_dim_medium = (math.ceil(min_step_medium / self._dim_medium_axis) - 1) * self._dim_medium_axis

        add_dim_slow = 0
        min_step_slow = int(self._min_steps * abs(self.image_ranges["y"][1] - self.image_ranges["y"][0]))
        if min_step_slow > self._dim_slow_axis:
            add_dim_slow = (math.ceil(min_step_slow / self._dim_slow_axis) - 1) * self._dim_slow_axis
        self.dim_addition = max(add_dim_medium, add_dim_slow)

        # the value which needs more additional steps decides how many more positions are scanned at the "end" of each
        # fast axis scan. This way one does not need to start new task at the end of each line scan (medium dimension)
        # if more extra steps are needed for the slow dimension.
        # Todo: it should be tested if this  (see above) is really faster
        #  than simply setting up, starting, stopping, deleting and resetting up original task

        # The dimensions arrangement of the array:
        # The outer dimension is y because it is the axis least often changed (slow axis),
        # the second one is x (horizontal), the medium fast axis),
        # and third the inner one that is changed with every step
        # The inner part of the matrix are the values, x,y,z, than the count channels, first digital then analog
        # self.image_results = [..[y_value, x_value, z_value, count_value1, ..., analog_counts_value].. ]

        # generate empty image for the scanner
        _dim_fast_axis_scanner = self._dim_fast_axis + self.dim_addition
        self._image_scanner = np.zeros((self._dim_slow_axis, self._dim_medium_axis, _dim_fast_axis_scanner, 3))

        digital_count_ch = self._get_scanner_count_channels()
        # generate empty image for the measured results
        self.image_results = np.zeros((self._dim_slow_axis, self._dim_medium_axis, _dim_fast_axis_scanner,
                                       len(digital_count_ch) + len(self.current_ai_axes)))

        # generate sub images for the scanner image
        x_axis = np.full((self._dim_fast_axis, self._dim_medium_axis), self._X_Axis).transpose()
        z_axis = np.full((self._dim_medium_axis, self._dim_fast_axis), self._Z_Axis)
        z_axis[1::2] = np.flip(z_axis[1::2], 1)  # every second value is scanned the opposite direction

        xz_axis = np.zeros((self._dim_medium_axis, _dim_fast_axis_scanner, 2))  # make matrix for x and z values
        # fill up array as if dim addition = 0
        xz_axis[:, :self._dim_fast_axis, 0] = x_axis
        xz_axis[:, :self._dim_fast_axis, 1] = z_axis

        if self.dim_addition > 0:  # this isn't necessary but saves computation time
            # make new scanning positions for x axis
            new_medium = []
            for i in range(self._dim_medium_axis):
                if i < self._dim_medium_axis - 1:
                    x_line = np.linspace(x_axis[i, 0], x_axis[i + 1, 0], self.dim_addition + 2)
                else:
                    x_line = np.array([x_axis[i, 0]] * (self.dim_addition + 2))
                new_medium.append(x_line[1:-1])
            xz_axis[:, self._dim_fast_axis:, 0] = np.array(new_medium)
            xz_axis[:, self._dim_fast_axis:, 1] = np.full((self.dim_addition, self._dim_medium_axis),
                                                          z_axis[:, -1]).transpose()

        xz_axis_full = np.full((self._dim_slow_axis, self._dim_medium_axis, _dim_fast_axis_scanner, 2), xz_axis)
        # Todo: resuse next code line when numpy version 1.15 is added for qudi
        # xz_axis[1::2] = np.flip(xz_axis[1::2], (1, 2))  # every second line is scanned the opposite direction
        xz_axis_full[1::2] = np.flip(np.flip(xz_axis_full[1::2], 1), 2)

        # fill image_results positions
        self._image_scanner[:, :, :, 0] = xz_axis_full[:, :, :, 0]  # x
        # for y flip around axis length of matrix to form matrix using linspace and than reflip using transpose
        self._image_scanner[:, :, :, 1] = np.full((_dim_fast_axis_scanner, self._dim_medium_axis,
                                                   self._dim_slow_axis), self._Y_Axis).transpose()  # y
        self._image_scanner[:, :, :, 2] = xz_axis_full[:, :, :, 1]  # z

        if self.dim_addition > 0:
            # make new scanning positions for y axis
            # this part :_image_scanner2[:,-1,:,1] now needs to be updated.
            # It should not stay constant for each line and point but be scanned
            new_slow = []
            for i in range(self._dim_slow_axis):
                if i < self._dim_slow_axis - 1:
                    y_line = np.linspace(self._Y_Axis[i], self._Y_Axis[i + 1], self.dim_addition + 2)
                else:
                    y_line = np.array([self._Y_Axis[i]] * (self.dim_addition + 2))
                new_slow.append(y_line[1:-1])
            new_slow = np.array(new_slow)
            self._image_scanner[:, -1, self._dim_fast_axis:, 1] = new_slow
            # flip such that the additional position change in the slow axis happens
            # while the other axes are not scanned
            self._image_scanner[1::2, :, :, 1] = np.flip(self._image_scanner[1::2, :, :, 1], 1)
            self._image_scanner[1::2, 0, :, 1] = np.flip(self._image_scanner[1::2, 0, :, 1], 1)

        # This image is used to display data (as only 2d possible).
        self.image_2D = np.zeros((self._dim_slow_axis, self._dim_medium_axis,
                                  3 + len(digital_count_ch) + len(self.current_ai_axes)))
        # make array anew, as it is easier this way than going back from removing the additional positions.
        self.image_2D[:, :, 0] = np.full((self._dim_slow_axis, self._dim_medium_axis), self._X_Axis)
        self.image_2D[:, :, 1] = np.full((self._dim_medium_axis, self._dim_slow_axis), self._Y_Axis).transpose()
        self.image_2D[:, :, 2] = np.full((self._dim_slow_axis, self._dim_medium_axis), np.mean(self._Z_Axis))

        self.sigImageInitialized.emit()
        return 0

    # Todo: Define function for moving scanner to different position
    def _generate_voltage_ramp_3D(self, start_voltage, end_voltage):
        """Generate a ramp from start_voltage to end_voltage that
        satisfies the general step resolution and smoothing_steps parameters.
        Smoothing_steps=0 means that the ramp is just linear.

        @param float start_voltage: voltage at start of ramp.
        @param float end_voltage: voltage at end of ramp.

        @return  array(float): the calculated voltage ramp
        """

        # It is much easier to calculate the smoothed ramp for just one direction (upwards),
        # and then to reverse it if a downwards ramp is required.
        v_min = min(start_voltage, end_voltage)
        v_max = max(start_voltage, end_voltage)

        if v_min == v_max:
            ramp = np.array([v_min, v_max])

        else:
            smoothing_range = self._fast_axis_smoothing_steps + 1

            # Sanity check in case the range is too short
            # The voltage range covered while accelerating in the smoothing steps
            v_range_of_accel = sum(n * self._fast_axis_smoothing_steps / smoothing_range
                                   for n in range(0, smoothing_range)
                                   )

            # Obtain voltage bounds for the linear part of the ramp
            v_min_linear = v_min + v_range_of_accel
            v_max_linear = v_max - v_range_of_accel

            # calculate smooth ramp if needed and possible
            if self.smoothing and v_min_linear < v_max_linear:

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / self.scan_resolution_fast_axis)
                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array([sum(n * self.scan_resolution_fast_axis / smoothing_range
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
                num_of_linear_steps = np.rint((v_max - v_min) / self.scan_resolution_fast_axis)
                ramp = np.linspace(v_min, v_max, num_of_linear_steps)
                if v_min_linear > v_max_linear and self.smoothing:
                    # print out info for use
                    self.log.warning('Voltage ramp too short to apply the '
                                     'configured smoothing steps. A simple linear ramp was created instead.')
        # Reverse if downwards ramp is required
        if end_voltage < start_voltage:
            ramp = ramp[::-1]

        return ramp

    ################################### Control Scanner Functions ##########################
    def switch_hardware(self, to_on=False):
        """ Switches the Scanning Hardware off or on.

        @param to_on: True switches on, False switched off

        @return int: error code (0:OK, -1:error)
        """
        if to_on:
            return self._scanning_device.activation()
        else:
            return self._scanning_device.reset_hardware()

    def _get_scanner_ao_channels(self):
        """ Returns the current scanning axes/channels of the scanner
        @return List[]: Name of the current scanning axes on the hardware
        """
        self._ao_channels = self._scanning_device._scanner_ao_channels
        return self._ao_channels

    def _get_scanner_count_channels(self):
        """ Returns the current counters of the digital counting hardware
        @return List[]: Name of the current counting channels
        """
        self._counts_ch = self._scanning_device._counter_channels[:]
        return self._counts_ch

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

    def update_current_position(self, position_dict):
        """
        Updates the current position of the scanner (in the memory) to positions given in the dictionary
        @param dict position_dict:

        @return int: error code (0:OK, -1:error)
        """
        # Todo: The current positions should be saved in a dict not as single values! this is not flexible!
        for key in position_dict.keys():
            if key in self._current_position:
                self._current_position[key] = position_dict[key]
            else:
                self.log.error(
                    "The axis (%s) for which the position was to be updated does not exist for the scanner (%s)", key,
                    self._current_position.keys())

    def move_to_position(self, position_dict, tag=""):
        """
        Changes the current position of the scanner to the given position
        @param dict position_dict:
        @param str tag: the tag shows which function called this function

        @return int: error code (0:OK, -1:error)
        """
        # check if given position is current position
        for key, value in position_dict.items():
            if key in self._current_position:
                if value != self._current_position[key]:
                    if in_range(value, self._scanning_axes_ranges[key][0], self._scanning_axes_ranges[key][1]):
                        if 0 < self.change_single_output_position(key, value):
                            self.log.error("Moving scanner to new position failed for axis %s", key)
                            return -1
                        self._current_position[key] = value
                    else:
                        self.log.error("The new position (%s) lies without the possible range (%s) of the axis (%s)",
                                       value, self._scanning_axes_ranges, key)
            else:
                self.log.error(
                    "The axis (%s) for which the position was to be changed does not exist for the scanner (%s)", key,
                    self._current_position.keys())
        self.signal_change_position.emit(tag)
        return 0

    def change_single_output_position(self, axis, new_pos):
        """Moves a scanner axis from the current position to a new position

        @param key axis: The axis which is to be moved
        @param float new_pos: The new position that the axis is to be moved to

        @return int: error code (0:OK, -1:error)
        """
        # Todo: Error checks if given values are existing in dicts and if they are float/str
        pos_range = self._scanning_axes_ranges[axis]
        if not in_range(new_pos, pos_range[0], pos_range[1]):
            self.log.error(
                "The position %s to which the scanner is to be changed does not "
                "lie within the range of possible positions %s",
                new_pos, pos_range)
        current_pos = self._current_position[axis]
        if current_pos == new_pos:
            self.log.info("The device was already at required output voltage")
            return 0
        scan_res = abs(self.calculate_resolution(
            # self._scanning_device.get_analogue_resolution(), pos_range)
            4, [current_pos, new_pos]))
        # Todo: The scan resolution used should be done much more sensibly. This could possibly very slow
        max_scan_res = self.calculate_resolution(16, self._scanning_axes_ranges[axis])
        if scan_res < max_scan_res:
            scan_res = max_scan_res

        num_of_linear_steps = np.rint(abs((current_pos - new_pos) / scan_res))
        if (num_of_linear_steps < 1):
            num_of_linear_steps = 2
        # convert speed of movement per m into clock freq per moved point
        _clock_frequency = self._scan_freq_per_m / abs(current_pos - new_pos) * num_of_linear_steps
        ramp = np.linspace(current_pos, new_pos, num_of_linear_steps)
        voltage_difference = abs(current_pos - new_pos)
        if voltage_difference > scan_res:
            if 0 > self._scanning_device.set_up_analogue_output([axis]):
                self.log.error("Setting up scanner for  channel %s failed", axis)
                return -1

            if 0 > self._scanning_device.set_up_analogue_output_clock(axis, clock_frequency=_clock_frequency):
                # Fixme: I do not think this is necessary. However it should be checked.
                # self.set_position('scanner')
                self.log.error("Problems setting up scanner clock.")
                if 0 > self._scanning_device.close_analogue_output(axis):
                    self.log.error("Closing scanner failed. Giving up")
                return -1

            self._scanning_device.configure_analogue_timing(axis, len(ramp))

            retval3 = np.array_equal(self._scanning_device.analogue_scan_line_positions([axis], ramp), ramp)

            try:
                retval1 = self._scanning_device.close_analogue_output_clock(axis)
                retval2 = self._scanning_device.close_analogue_output(axis)
            except:
                self.log.warn("Closing the scanner did not work")
            if retval3 != -1:
                self._current_position[axis] = new_pos
            return min(retval1, retval2, retval3)
        else:
            self.log.info("The device was already at required output voltage")
            return 0

    def get_position_from_feedback(self, axes):
        return self._stepper_logic.get_position(axes)

    ################################### Save Functions ###############################

    def generate_save_parameters(self):
        # Prepare the meta data parameters (common to both saved files):
        parameters = OrderedDict()

        parameters["Count frequency (Hz)"] = self._clock_frequency_3D_scan
        parameters["Scan Freq complete fast axis (Hz)"] = self.scan_freq_fast_axis
        parameters["Scan resolution (m/step)"] = self.scan_resolution_fast_axis

        parameters['Fast Axis'] = "z"
        parameters['Fast Axis Steps'] = self._dim_fast_axis

        parameters["Start Position fast axis(m)"] = self.image_ranges["z"][0]
        parameters["End Position fast axis (m)"] = self.image_ranges["z"][1]
        parameters["Start Voltage fast axis(V)"] = self.convert_pos_to_v(self.image_ranges["z"][0], "z")
        parameters["End Voltage fast axis (V)"] = self.convert_pos_to_v(self.image_ranges["z"][1], "z")

        parameters['Medium Axis'] = "x"
        parameters['Medium Axis Steps'] = self._dim_medium_axis
        parameters['X image min (m)'] = self.image_ranges["x"][0]
        parameters['X image max (m)'] = self.image_ranges["x"][1]
        parameters['X image range (m)'] = self.image_ranges["x"][1] - self.image_ranges["x"][0]

        parameters['Slow Axis'] = "y"
        parameters['Slow Axis Steps'] = self._dim_slow_axis
        parameters['Y image min'] = self.image_ranges["y"][0]
        parameters['Y image max'] = self.image_ranges["y"][1]
        parameters['Y image range'] = self.image_ranges["y"][1] - self.image_ranges["y"][0]

        parameters['XY resolution (samples per range)'] = self.xy_resolution
        if self.dim_addition > 0:
            parameters["Fast Axis Additional Steps to increase XY resolution"] = self.dim_addition
        if self.smoothing:
            parameters["Smoothing Steps"] = self._fast_axis_smoothing_steps

        return parameters

    def generate_file_path(self):
        """Generate the file path for the step scan measurement based on the time the measurement is started."""
        timestamp = datetime.datetime.now()

        self.filepath = self._save_logic.get_path_for_module(
            'Piezo_scan_3D' + "/" + timestamp.strftime('%Y%m%d-%H%M-%S'))
        self.file_path_raw = self._save_logic.get_path_for_module(self.filepath + "/raw")
        self.filename = "Piezo_scan_3d"

    def generate_file_info(self):
        """Saves the scan parameters set at the beginning of the scan"""

        file_info = self.generate_save_parameters()
        fake_data = OrderedDict()
        fake_data["no data, as this is an info file"] = [0]

        self._save_logic.save_data(fake_data, filepath=self.filepath, parameters=file_info,
                                   filelabel=self.filename + "_experiment_parameters", delimiter='\t')

    def save_to_npy(self, name, data, line=None):
        """ saves data passed into a numpy file using the past name and line number to name the file
            filename in which data is stored: intrinsicfilename+ _name_line_str(line)

            @param str name: the name which can be given to the file additionally to the naming convention
            @param numpy array data: the data to be saved, has to be given in form of a np array
            @param int line: the line number of the measurement for which the data is to be saved.
                            If the line is given, it is saved as part of the filename
        """
        if line == None:
            np.save(self.file_path_raw + "/" + self.filename + "_" + name, data)
            return
        elif line < 10:
            addition = "000"
        elif line < 100:
            addition = "00"
        elif line < 1000:
            addition = "0"
        else:
            addition = ""
        np.save(self.file_path_raw + "/" + self.filename + "_" + name + "_line_" + addition + str(line), data)

    def generate_npy_file(self, data):
        # Todo: this is very crude

        np.save(self.path_name + '/' + self.filename, data)
        np.save(self.path_name + '/' + self.filename_back, data)

    def save_data(self, colorscale_range=None, percentile_range=None):
        """ Save the current confocal data to a file.

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
        digital_count_ch = self._get_scanner_count_channels()

        # Todo:Save feedback position data in meaning full way(as positions or with voltage boundaries)
        for i in range(len(self.current_ai_axes)):
            name_suffix = "V"
            if self.current_ai_axes[i] != self._ai_counter and self._save_positions:
                data[self._ai_axes[self.current_ai_axes[i]] + name_suffix] = self.image_results[:, :, :,
                                                                             len(digital_count_ch) + i].flatten()
            else:
                data[self._ai_axes[self.current_ai_axes[i]] + name_suffix] = self.image_results[:, :, :,
                                                                             len(digital_count_ch) + i].flatten()
        if not self._save_positions:
            data['x step'] = self._image_scanner[:, :, :, 0].flatten()
            data['y step'] = self._image_scanner[:, :, :, 1].flatten()
            data['z step'] = self._image_scanner[:, :, :, 2].flatten()

        for n, ch in enumerate(self._counts_ch):
            data['count rate {0} (Hz)'.format(ch)] = self.image_results[:, :, :, n].flatten()

        # Todo: update for variable axis
        image_extent = [self.image_ranges["x"][0],
                        self.image_ranges["x"][1],
                        self.image_ranges["y"][0],
                        self.image_ranges["y"][1]]

        # Todo: This needs to be implemented in this logic, as this way only works for steppers as underlying hardware!
        feedback_axis = []
        for i in self.current_ai_axes:
            if i != self._ai_scanner:
                feedback_axis.append(i)

        # if feedback_axis:
        #    position = self.get_position_from_feedback(feedback_axis)
        #    if not position[0] == -1:
        #        parameters['Last Positions '] = feedback_axis, position

        figs = {ch: self.draw_figure(data=self.image_2D[:, :, 3 + n],
                                     image_extent=image_extent,
                                     cbar_range=colorscale_range,
                                     percentile_range=percentile_range)
                for n, ch in enumerate(self._counts_ch)}

        # Save the raw data and plotted figure to file
        filelabel = 'scanner_3D_data'
        for n, ch in enumerate(self.get_scanner_count_channels()):
            self._save_logic.save_data(data,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel + str(ch),
                                       fmt='%.6e',
                                       delimiter='\t',
                                       plotfig=figs[ch])

        self.log.debug('Scan 3D Image saved.')

        self.signal_data_saved.emit()
        # Todo Ask if it is possible to write only one save with options for which lines were scanned
        return

    def draw_figure(self, data, image_extent, scan_axis=None, cbar_range=None, percentile_range=None,
                    crosshair_pos=None):
        """ Create a 2-D color map figure of the scan image.

        @param: array data: The NxM array of count values from a scan with NxM pixels.

        @param: list image_extent: The scan range in the form [hor_min, hor_max, ver_min, ver_max]

        @param: list axes: Names of the horizontal and vertical axes in the image

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].  If not supplied then a default of
                                 data_min to data_max will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @param: list crosshair_pos: (optional) crosshair position as [hor, vert] in the chosen image axes.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        if scan_axis is None:
            scan_axis = ['X', 'Y']

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = [np.min(data), np.max(data)]

        # Scale color values using SI prefix
        prefix = ['', 'k', 'M', 'G']
        prefix_count = 0
        image_data = data
        draw_cb_range = np.array(cbar_range)
        image_dimension = image_extent.copy()

        while draw_cb_range[1] > 1000:
            image_data = image_data / 1000
            draw_cb_range = draw_cb_range / 1000
            prefix_count = prefix_count + 1

        c_prefix = prefix[prefix_count]

        # Scale axes values using SI prefix
        axes_prefix = ['', 'm', r'$\mathrm{\mu}$', 'n']
        x_prefix_count = 0
        y_prefix_count = 0

        while np.abs(image_dimension[1] - image_dimension[0]) < 1:
            image_dimension[0] = image_dimension[0] * 1000.
            image_dimension[1] = image_dimension[1] * 1000.
            x_prefix_count = x_prefix_count + 1

        while np.abs(image_dimension[3] - image_dimension[2]) < 1:
            image_dimension[2] = image_dimension[2] * 1000.
            image_dimension[3] = image_dimension[3] * 1000.
            y_prefix_count = y_prefix_count + 1

        x_prefix = axes_prefix[x_prefix_count]
        y_prefix = axes_prefix[y_prefix_count]

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
                            extent=image_dimension
                            )

        ax.set_aspect(1)
        ax.set_xlabel(scan_axis[0] + ' position (' + x_prefix + 'm)')
        ax.set_ylabel(scan_axis[1] + ' position (' + y_prefix + 'm)')
        ax.spines['bottom'].set_position(('outward', 10))
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()

        # draw the crosshair position if defined
        if crosshair_pos is not None:
            trans_xmark = mpl.transforms.blended_transform_factory(
                ax.transData,
                ax.transAxes)

            trans_ymark = mpl.transforms.blended_transform_factory(
                ax.transAxes,
                ax.transData)

            ax.annotate('', xy=(crosshair_pos[0] * np.power(1000, x_prefix_count), 0),
                        xytext=(crosshair_pos[0] * np.power(1000, x_prefix_count), -0.01), xycoords=trans_xmark,
                        arrowprops=dict(facecolor='#17becf', shrink=0.05),
                        )

            ax.annotate('', xy=(0, crosshair_pos[1] * np.power(1000, y_prefix_count)),
                        xytext=(-0.01, crosshair_pos[1] * np.power(1000, y_prefix_count)), xycoords=trans_ymark,
                        arrowprops=dict(facecolor='#17becf', shrink=0.05),
                        )

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
        self.signal_draw_figure_completed.emit()
        return fig
