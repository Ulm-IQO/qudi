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


class Scanner3DLogic(GenericLogic):
    """
    This is the Logic class for confocal scanning.
    """
    _modclass = 'scanner3Dlogic'
    _modtype = 'logic'

    # declare connectors
    scanner1 = Connector(interface='ConfocalScannerInterface')
    savelogic = Connector(interface='SaveLogic')
    digitalcounter = Connector(interface='FiniteCounterInterface')
    analoguereader = Connector(interface='AnalogueReaderInterface')
    analogueoutput = Connector(interface='AnalogueOutputInterface')
    cavcontrol = Connector(interface="CavityStabilisationLogic")

    # status vars
    _clock_frequency = StatusVar('clock_frequency', 500)
    return_frequency = StatusVar(default=500)

    # config
    scan_resolution_3rd_axis = ConfigOption('3D_scan_resolution', 1e-6, missing="warn")
    _ai_counter = ConfigOption("AI_counter", None, missing="warn")

    # signals
    signal_start_scanning = QtCore.Signal(str)
    signal_continue_scanning = QtCore.Signal(str)
    signal_stop_scanning = QtCore.Signal()
    signal_scan_lines_next = QtCore.Signal()
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
        self._analog_input_device = self.analoguereader()
        self._scanning_device = self.analogueoutput()
        self._save_logic = self.savelogic()
        self._cavitycontrol = self.cavcontrol()

        # Sets connections between signals and functions
        self.signal_scan_line_next.connect(self._scan_line_3D, QtCore.Qt.QueuedConnection)
        self.signal_start_scanning.connect(self.start_scanner_3D, QtCore.Qt.QueuedConnection)
        self.signal_continue_scanning.connect(self.continue_scanner_3D, QtCore.Qt.QueuedConnection)

        self.signal_sort_count_data_3D.connect(self._sort_data, QtCore.Qt.DirectConnection)

        self._change_position('activation')

        # Reads in the maximal scanning range. The unit of that scan range is meters!
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]

        # Sets the current position to the center of the maximal scanning range
        # Todo: In general these should be defined by the config and it should be checked if they havent already been set
        # by another program
        self.current_x = self.x_range[0]
        self.current_y = self.y_range[0]
        self.current_z = self.z_range[0]
        self.current_a = 0.0

        # Sets the size of the image to the maximal scanning range
        self.image_x_range = self.x_range
        self.image_y_range = self.y_range
        self.image_z_range = self.z_range

        # Default values for the resolution of the scan
        self.xy_resolution = 100

        # Variable to check if a scan is continuable
        self.scan_counter = 0


        self._analog_counting = True
        self.go_to_start_positions = False
        self.current_ai_axes = []
        self.fast_axis_scan_freq = 1.0  # Hz, the freq. to scan the whole measurement range of the fast axis

        self._ao_channels = []

        self._double_3rd_axis_scan = False
        self._use_maximal_resolution_3rd_axis = False
        self.smoothing = True
        self._3rd_axis_smoothing_steps = 10

        # Position_feedback
        # Todo: Define sensible axes
        self._ai_position_feedback_axes = []
        self.map_scan_positions = False
        # Todo: shouldnt this be dependent on the analogue reader ?
        if self._ai_counter != None:
            if self._ai_counter in self._counting_device._analogue_input_channels:
                self._ai_scanner = True
            else:
                self._ai_scanner = False
        else:
            self._ai_scanner = False
        self._ai_axes = {"x": "x_pos_voltages", "y": "y_post_voltages", "z": "z_pos_voltages",
                         self._ai_counter: "APD counter: " + self._ai_counter}

        self.get_scanner_count_channels()

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

        self.scan_resolution_3rd_axis = self.calculate_resolution(
            self._analog_input_device.get_analogue_resolution(), [self._min_z, self._max_z])
        if self.scan_resolution_3rd_axis == -1:
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

    def _check_if_voltage_in_range(self, voltage, range):
        """Checks if a selected voltage is allowed by checking if it lies within the possible range of voltages
            @param float voltage: The voltage to be checked
            @param list range:  a list with two entries with the minimum and maximum allowed voltage
            @return int: error code (0:OK, -1:error)
        """
        if not in_range(voltage, range[0], range[1]):
            self.log.error("The given start voltage %s is not within the possible output voltages %s", voltage,
                           range)
            return -1
        else:
            return 0

    ################################### Main Scan Functions ################################
    def _initalize_measurement(self, steps, frequency, ai_channels):
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
            # self._counting_device.close_finite_counter_clock()
            # self._counting_device.module_state.unlock()
            self.module_state.unlock()
            self.stopRequested = True
            return -1

        # setup analogue input if existing
        if ai_channels:  # checks if list is not empty
            if 0 > self._analog_input_device.add_clock_task_to_channel("Scanner_clock", ai_channels):
                self.stopRequested = True
            elif 0 > self._analog_input_device.set_up_analogue_voltage_reader_scanner(
                    steps, ai_channels[0]):
                self.stopRequested = True
            else:
                if len(ai_channels) > 1:
                    if 0 > self._analog_input_device.add_analogue_reader_channel_to_measurement(
                            ai_channels[0], self._ai_scan_axes[1:]):
                        self.stopRequested = True

        # Todo: These setups need to take place in the hardware in someway. this is to specific for a logic

        # setup analogue output
        if 0 > self._scanning_device.set_up_analogue_output([self._ao_channels]):
            self.log.error("Problems setting up analogue out put for 3D step scan on channel (%s)",
                           self._ao_channels)
            self.stopRequested = True

        if 0 > self._scanning_device.add_clock_task_to_channel("Scanner_clock", [self._ao_channels]):
            self.log.error("Problems setting up analogue output clock.")
            self.stopRequested = True

        if 0 > self._scanning_device.configure_analogue_timing(self._ao_channels, steps):
            self.log.error("Not possible to set appropriate timing for analogue scan.")
            self._output_device.close_analogue_output(self._ao_channels)
            self.stopRequested = True

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

        # Todo: Maybe something to implement later. Check axis and how they are to be scanned
        # (which one is first, second, third axis)

        # Initialize data
        if self.initialize_image() < 0:
            self.log.error("Initialisation of image failed. Scan stopped")
            return -1
        self.signal_image_updated.emit()

        # The clock freq for each point is given by the freq used to scan one whole line on the fast axis
        self._clock_frequency_3D_scan = int(self.fast_axis_scan_freq * self._dim_fast_axis)

        # Todo: This needs to be done. But it needs to be done by the hardware to remove conflicts!
        # move piezo to desired start position to go easy on piezo
        # self.change_analogue_output_voltage(self.start_voltage_3D)
        # self._cavitycontrol.axis_class[self._cavitycontrol.control_axis].output_voltage = self.start_voltage_3D

        # save starting positions
        self._start_position = [self._current_x, self._current_y, self._current_z]

        # check if scan positions should be saved and if it is possible
        self.current_ai_axes = []
        if self._ai_scanner:
            self.current_ai_axes.append(self._ai_counter)

        if self.map_scan_position:
            # Todo: This is too simple as it assumes that the scan axes are always named like this and sorted like this
            self.current_ai_axes.append("x")
            self.current_ai_axes.append("y")
            self.current_ai_axes.append("z")

        if 0 > self._initalize_measurement(steps=self._dim_fast_axis * self._dim_medium_axis,
                                           frequency=self._clock_frequency_3D, ai_channels=
                                           self.current_ai_axes):
            return -1

        self.generate_file_path()
        self.generate_file_info()
        self.signal_scan_lines_next.emit()

    def continue_3D_scan(self):
        """Continue scanning

        @return int: error code (0:OK, -1:error)
        """

        self._scan_counter = self._line_pos
        if self._scan_counter == 0:
            self.start_3D_scan()
            return 0
        if 0 > self._initalize_measurement(steps=self._dim_fast_axis * self._dim_medium_axis,
                                           frequency=self._clock_frequency_3D, ai_channels=
                                           self.current_ai_axes):
            return -1
        self.signal_scan_lines_next.emit()
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
        self.signal_stop_scanning.emit()
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
                    self._analog_input_device.close_analogue_voltage_reader(self.current_ai_axes[0])
                if self.map_scan_position:
                    self.convert_voltage_to_position_for_image()
                    self.smooth_out_position_data()
                # Todo: Update current positions
                # if self.go_to_start_positions:
                #    self._change_position()

                self._analogue_output_device.close_analogue_output(self._ao_channels[0])

                self.stopRequested = False
                self.module_state.unlock()

                self.update_image_data_line(self._scan_counter - 1)
                self.signal_image_updated.emit()
                self.signal_scan_3D_stopped.emit()
                self.log.info("3D Scanning stopped successfully")
                self.log.info("The scanner scanned %s lines", self._scan_counter)

                return

        # move and count
        new_counts = self._scan_and_count_3D(self.image[self._scan_counter, :, :, :3], self.current_ai_axes)
        if type(new_counts) == int:
            self.stopRequested = True
            self.signal_scan_line_next.emit()
            return
        # Todo:
        # this might be a better way to catch errors:
        # new_counts = self._scan_and_count_3D(self.image[self._scan_counter, :, :, :3], self.current_ai_axes)
        # if np.any(new_counts == -1):
        #    self.stopRequested = True
        #    self.signal_scan_lines_next.emit()
        #    return

        # Todo: There need to be a method implemented here for the 3D case
        self.signal_sort_count_data.emit(new_counts, self._scan_counter)

        # Todo: Tilt correction?

        self._scan_counter += 1

        # check if at end of scan
        if self._scan_counter > self._dim_slow_axis - 1:
            self.stopRequested = True
            self.log.info("3D Scan at end position")
        # self.log.info("new line %s time: %s", self._scan_counter, datetime.datetime.now().strftime('%M-%S-%f'))

        self.signal_scan_lines_next.emit()

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

        # Todo: Check how clock needs to be set
        if self._counting_device.start_finite_counter(start_clock=not self._3D_measurement) < 0:
            self.log.error("Starting the counter failed")
            return [-1], []
        if ai_axes:
            if 0 > self._analog_input_device.start_analogue_voltage_reader(ai_axes[0],
                                                                           start_clock=False):
                self.log.error("Starting the analogue input failed")
                return [-1], []
        self._scanning_device.analogue_scan_line(self._ao_channels[0], scan_trajectory)

        # get data
        count_result = self._counting_device.get_finite_counts()
        if ai_axes:
            analog_result = self._analog_input_device.get_analogue_voltage_reader(ai_axes)

        error = self._counting_device.stop_finite_counter()
        if ai_axes:
            if 0 > self._analog_input_device.stop_analogue_voltage_reader(ai_axes[0]):
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
        mean_counts = []
        new_counts = []
        length_scan = self._dim_medium_axis
        name_save_addition = "_3D_scan"
        data_counter = 0

        # Digital Counter Data
        counts_digital = np.split(counts[data_counter], len(self._counts_ch))
        for i in range(len(self._counts_ch)):
            new_counts_uo = np.split(counts_digital[i], length_scan)  # split into single line pixel of medium axis
            new_counts_uo[1::2] = np.flip(new_counts_uo[1::2], 1)  # flip fast axis of every second pixel
            new_counts.append(np.concatenate(new_counts_uo))
            self.save_to_npy("SPCM_" + self._counts_ch[i] + "_" + name_save_addition, line_number,
                             new_counts[i])
            self.image[self._scan_counter, :, :, 3 + i] = np.split(new_counts[i], self._dim_medium_axis)
            self.image_2D[self._scan_counter, :, 3 + i] = np.mean(new_counts_uo, 1)

        data_counter += 1
        # Analog Counter Data
        forward_split = []
        new_counts_analog = {}
        if self.current_ai_axes:
            counts_analog_ch = np.split(counts[data_counter], len(self.current_ai_axes))
            # go through all analog channels
            for i in range(len(self.current_ai_axes)):
                new_counts_a = np.split(counts_analog_ch[i], length_scan)  # split into single line pixel of medium axis
                new_counts_a[1::2] = np.flip(new_counts_a[1::2], 1)  # flip fast axis of every second pixel
                new_counts_analog[self.current_ai_axes[i]] = np.concatenate(new_counts_a)
            for key, value in new_counts_analog:
                self.save_to_npy(self._ai_axes[key] + "_" + name_save_addition, line_number,
                                 value)
                if key == self._ai_counter:
                    self.image[self._scan_counter, :, :, 3 + len(self._counts_ch) + 1] = np.split(value, length_scan)
                    self.image_2D[self._scan_counter, :, 3 + len(self._counts_ch) + 1] = np.mean(
                        np.split(value, length_scan), 1)

            if self._ai_scanner:
                self.save_to_npy("APD" + name_save_addition, line_number, forward_split[-1])
            data_counter += 1

        self.log.info("3D Scan finished saving, line %s,  time: %s", line_number,
                      datetime.datetime.now().strftime('%M-%S-%f'))

        self.sort_counted_data(mean_counts, line_number)

    def initialize_image(self):
        """Initalization of the image.

        @return int: error code (0:OK, -1:error)
        """
        # x1: x-start-value, x2: x-end-value
        x1, x2 = self.image_x_range[0], self.image_x_range[1]
        # y1: x-start-value, y2: x-end-value
        y1, y2 = self.image_y_range[0], self.image_y_range[1]
        # z1: x-start-value, z2: x-end-value
        z1, z2 = self.image_z_range[0], self.image_z_range[1]

        if self._check_if_voltage_in_range(x1, self.x_range) != 0 and \
                self._check_if_voltage_in_range(x2, self.x_range) != 0 and \
                self._check_if_voltage_in_range(y1, self.y_range) != 0 and \
                self._check_if_voltage_in_range(y2, self.y_range) != 0 and \
                self._check_if_voltage_in_range(z1, self.z_range) != 0 and \
                self._check_if_voltage_in_range(z2, self.z_range) != 0:
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
        self._Z_Axis = self._3D_generate_voltage_ramp(z1, z2)

        # axis dimensions
        self._dim_medium_axis = len(self._X_Axis)  # medium axis ("x")
        self._dim_slow_axis = len(self._Y_Axis)  # slow axis ("y")
        self._dim_fast_axis = len(self._Z_Axis)  # fast axis ("z")

        # The dimensions arrangement of the array:
        # The outer dimension is y because it is the axis least often changed (slow axis),
        # the second one is x (horizontal), the medium fast axis),
        # and third the inner one that is changed with every step
        # The inner part of the matrix are the values, x,y,z, than the count channels, first digital then analog
        # self.image = [..[y_value, x_value, z_value, count_value1, ..., analog_counts_value].. ]

        self._counts_ch = self._scanning_device.get_scanner_count_channels()
        # generate empty image
        self.image = np.zeros((self._dim_slow_axis, self._dim_medium_axis, self._dim_fast_axis,
                               3 + len(self._counts_ch) + self._analog_counting))
        # generate sub images
        x_axis = np.full((self._dim_fast_axis, self._dim_medium_axis), self._X_Axis).transpose()
        z_axis = np.full((self._dim_medium_axis, self._dim_fast_axis), self._Z_Axis)
        z_axis[1::2] = np.flip(z_axis[1::2])  # every second value is scanned the opposite direction
        xz_axis = np.zeros((self._dim_medium_axis, self._dim_fast_axis, 2))  # make matrix for x and z values
        xz_axis[:, :, 0] = x_axis
        xz_axis[:, :, 1] = z_axis
        xz_axis = np.full((self._dim_slow_axis, self._dim_medium_axis, self._dim_fast_axis, 2), xz_axis)
        xz_axis[1::2] = np.flip(xz_axis[1::2], (1, 2))  # every second line is scanned the opposite direction

        # fill image positions
        self.image[:, :, :, 0] = xz_axis[:, :, :, 0]  # x
        # for y flip around axis length of matrix to form matrix using linspace and than reflip using transpose
        self.image[:, :, :, 1] = np.full((self._dim_fast_axis, self._dim_medium_axis, self._dim_slow_axis),
                                         np.linspace(1, 7, 7)).transpose()  # y
        self.image[:, :, :, 2] = xz_axis[:, :, :, 1]  # z

        # This image is used to display data (as only 2d possible).
        # The fast axis is analysed and the displayed in this image

        self.image_2D = np.copy(
            self.image[:, :, 0])  # Any value instead of 0 in the range of the fast axis would be possible

        self.sigImageInitialized.emit()
        return 0

    # Todo: Define function for moving scanner to different position
    def _3D_generate_voltage_ramp(self, start_voltage, end_voltage):
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
            smoothing_range = self._3rd_axis_smoothing_steps + 1

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

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / self.scan_resolution_3rd_axis)
                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array([sum(n * self.scan_resolution_3rd_axis / smoothing_range
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
                num_of_linear_steps = np.rint((v_max - v_min) / self.scan_resolution_3rd_axis)
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

    ################################### Save Functions ###############################

    def generate_save_parameters(self):
        # Prepare the meta data parameters (common to both saved files):
        parameters = OrderedDict()

        self._get_scan_axes()

        parameters['First Axis'] = "z"
        parameters['First Axis Steps'] = self._dim_fast_axis

        parameters['Second Axis'] = "x"
        parameters['Second Axis Steps'] = self._dim_medium_axis

        parameters['Third Axis'] = "y"
        parameters['Third Axis Steps'] = self._dim_slow_axis
        # Todo self._step_freq and self.step_amplitude should be named in a similar fashion

        parameters["Count frequency (Hz)"] = self._clock_frequency_3D
        parameters["Scan Freq complete fast axis (Hz)"] = self.fast_axis_scan_freq
        parameters["Scan resolution (V/step)"] = self.scan_resolution_3rd_axis
        parameters["Start Voltage fast axis(V)"] = self.image_z_range[0]
        parameters["End Voltage fast axis (V)"] = self.image_z_range[1]

        if self.smoothing:
            parameters["Smoothing Steps"] = self._3rd_axis_smoothing_steps

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

    def save_to_npy(self, name, line, data):
        """ saves data passed into a numpy file using the past name and line number to name the file
            filename in which data is stored: intrinsicfilename+ _name_line_str(line)

            @param str name: the name which can be given to the file additionally to the naming convention
            @param int line: the line number of the measurement for which the data is to be saved. It is part of the file name☻
            @param numpy array data: the data to be saved, has to be given in form of a np array
        """

        if line < 10:
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

