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
# from copy import copy
import time
import datetime
import numpy as np
# import matplotlib as mpl
# import matplotlib.pyplot as plt
# from io import BytesIO

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


# Todo make a confocal stepper History class for this logic as exists in confocal logic. This is neede for restarting and
# for back and forward movement in images

class ConfocalStepperLogic(GenericLogic):  # Todo connect to generic logic
    """
    This is the Logic class for confocal stepping.
    """
    _modclass = 'ConfocalStepperLogic'
    _modtype = 'logic'

    _connectors = {
        'confocalstepper1': 'ConfocalStepperInterface',
        'savelogic': 'SaveLogic',
        'confocalcounter': 'FiniteCounterInterface'
    }

    # Todo: add connectors and QTCore Signals
    # signals
    signal_start_stepping = QtCore.Signal()
    signal_step_lines_next = QtCore.Signal(bool)
    signal_stop_stepping = QtCore.Signal()
    signal_continue_stepping = QtCore.Signal()

    # Todo: For steppers with hardware realtime info like res readout of attocubes clock synchronisation and readout needs to be written
    # Therefore a new interface (ConfocalReadInterface o.ä.) needs to be made



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # counter for scan_image
        self._step_counter = 0
        self._scan_axes = "xy"
        self._inverted_scan = False
        self.stopRequested = False
        self.depth_scan_dir_is_xz = True
        self._steps_scan_line = 50

        # Todo: Add initialisation from _statusVariable

        # Connectors
        self._stepping_device = self.get_connector('confocalstepper1')
        self._counting_device = self.get_connector('confocalcounter')
        self._save_logic = self.get_connector('savelogic')

        self.axis = self.get_stepper_axes_use()
        self.step_amplitude = dict()
        self._step_freq = dict()
        self._stepper_mode = dict()
        for i in self.axis:
            # Todo: Add error check here or in method else it tries to write non existing value into itself
            self.step_amplitude[i] = self.get_stepper_amplitude(i)
            self._step_freq[i] = self.get_stepper_frequency(i)
            # Todo: write method that enquires stepping device mode
            self._stepper_mode[i] = self.get_stepper_mode(i)
        self._stepping_raw_data = np.zeros((self._steps_scan_line, self._steps_scan_line))

        # Sets connections between signals and functions
        self.signal_step_lines_next.connect(self._step_line, QtCore.Qt.QueuedConnection)
        self.signal_start_stepping.connect(self.start_stepper, QtCore.Qt.QueuedConnection)
        self.signal_continue_stepping.connect(self.continue_stepper, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        pass

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

    def set_stepper_frequency(self, axis, frequency):
        """
        Sets the stepping frequency for a specific axis to frequency

        :param axis: The axis for the desired frequency
        :param frequency: desired frequency

        :return int: error code (0:OK, -1:error)
        """
        self._step_freq[axis] = frequency

        # checks if stepper is still running
        if self.getState() == 'locked':
            return -1
        return self._stepping_device.set_step_freq(axis, frequency)

    def get_stepper_frequency(self, axis):
        freq = self._stepping_device.get_step_freq(axis)
        if freq == -1:
            self.log.warning("The Stepping device could not read out the frequency")
            return self._step_freq
        # Todo. The error handling in the methods in the stepper is not good yet and this needs to be adapted the moment
        # this is better
        self._step_freq[axis] = freq
        return freq

    def set_stepper_amplitude(self, axis, amplitude):
        """
        Sets the stepping amplitude for a specific axis to amplitude

        :param axis: The axis for the desired frequency
        :param amplitude: desired amplitude (V)

        :return int: error code (0:OK, -1:error)
        """
        self.step_amplitude[axis] = amplitude
        # checks if stepper is still running
        if self.getState() == 'locked':
            return -1
        return self._stepping_device.set_step_amplitude(axis, amplitude)

    def get_stepper_amplitude(self, axis):
        amp = self._stepping_device.get_step_amplitude(axis)
        if amp == -1:
            self.log.warning("The Stepping device could not read out the amplitude")
            return self.step_amplitude
        # Todo. The error handling in the methods in the stepper is not good yet and this needs to be adapted the moment
        # this is better
        self.step_amplitude[axis] = amp
        return amp

    def set_mode_stepping(self, axis):
        """Sets the mode of the stepping device to stepping for the specified axis

        :param axis: The axis for which the mode is to be set
        :return int: error code (0:OK, -1:error)
        """
        self._stepper_mode[axis] = "stepping"
        return self._stepping_device.set_axis_mode(axis, "stepping")

    def set_mode_ground(self, axis):
        """Sets the mode of the stepping device to grounded for the specified axis

        :param axis: The axis for which the mode is to be set
        :return int: error code (0:OK, -1:error)
        """
        self._stepper_mode[axis] = "ground"
        return self._stepping_device.set_axis_mode(axis, "ground")

    def get_stepper_mode(self, axis):
        """Gets the mode of the stepping device for the specified axis

        :param axis: The axis for which the mode is to be set
        :return int: error code (0:OK, -1:error)
        """
        mode = self._stepping_device.get_axis_mode(axis)
        if mode == -1:
            return mode
        else:
            self._stepper_mode[axis] = mode
            return mode

    def _check_freq(self, axis):
        """ Checks if the frequency in te device is the same as set by the program
        If the frequencies are different the frequency in the device is changed to the set
        frequency

        @return int: error code (0:OK, -1:error)
        """
        freq = self._stepping_device.get_step_freq(axis)
        if freq == -1:
            return -1
        elif freq != self._step_freq[axis]:
            self.log.warning(
                "The device has different frequency of {} then the set frequency {}. "
                "The frequency will be changed to the set frequency".format(freq,
                                                                            self._step_freq[axis]))
            # checks if stepper is still running
            if self.getState() == 'locked':
                self.log.warning("The stepper is still running")
                return -1
            return self.set_stepper_frequency(axis, self._step_freq[axis])
        return 0

    def _check_amplitude(self, axis):
        """ Checks if the voltage in te device is the same as set by the program
        If the voltages are different the voltage in the device is changed to the set voltage

        @return int: error code (0:OK, -1:error)
        """
        amp = self._stepping_device.get_step_amplitude(axis)
        if amp == -1:
            return -1
        elif amp != self.step_amplitude[axis]:
            self.log.warning(
                "The device has different voltage of {} then the set voltage {}. "
                "The voltage will be changed to the set voltage".format(amp,
                                                                        self.step_amplitude[axis]))
            # checks if stepper is still running
            if self.getState() == 'locked':
                self.log.warning("The stepper is still running")
                return -1
            return self.set_stepper_amplitude(axis, self.step_amplitude[axis])
        return 0

    def _check_mode(self, axis):
        """ Checks if the voltage in te device is the same as set by the program
        If the voltages are different the voltage in the device is changed to the set voltage

        @return int: error code (0:OK, -1:error)
        """
        mode = self._stepping_device.get_axis_mode(axis)
        if mode == -1:
            return -1
        elif mode != self._stepper_mode[axis]:
            self.log.warning(
                "The device has different mode ({}) compared the assumed mode {}. "
                "The mode of the device will be changed to the programs mode".format(mode,
                                                                                     self._stepper_mode[axis]))
            # checks if stepper is still running
            if self.getState() == 'locked':
                self.log.warning("The stepper is still running")
                return -1
            else:
                if self._stepper_mode[axis] == "ground":
                    retval = self.set_mode_ground(axis)
                elif self._stepper_mode[axis] == "stepping":
                    retval = self.set_mode_stepping(axis)
                else:
                    self.log.error(
                        "The mode set by the program {} does not exist or can not be accessed by this program.\n"
                        "Please change it to one of the possible modes".format(self._stepper_mode[axis]))
                    retval = -1
                return retval
        return 0

    def get_stepper_axes_use(self):
        """ Find out how the axes of the stepping device are named.

        @return list(str): list of axis dictionary

        Example:
          For 3D confocal microscopy in cartesian coordinates, ['x':1, 'y':2, 'z':3] is a sensible
          value.
          If you only care about the number of axes and not the assignment and names
          use get_stepper_axes
          On error, return an empty list.
        """
        return self._stepping_device.get_stepper_axes_use()

    ################################### Control Stepper ########################################

    def _get_scan_axes(self):
        """

        @return int: error code (0:OK, -1:error)
        """
        if (len(self._scan_axes) != 2):
            self.log.error(
                "A wrong number ({}) of scan axis was given. \n The program needs 2 axes".format(len(self._scan_axes)))
            return -1
        a, b = self._scan_axes[0], self._scan_axes[1]
        if a in self.axis.keys() and b in self.axis.keys():
            if self._inverted_scan:
                self._first_scan_axis = b
                self._second_scan_axis = a
            else:
                self._first_scan_axis = a
                self._second_scan_axis = b
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
        freq_status = self._check_freq(self._first_scan_axis)
        amp_status = self._check_amplitude(self._second_scan_axis)
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1
        freq_status = self._check_freq(self._first_scan_axis)
        amp_status = self._check_amplitude(self._second_scan_axis)
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1

        # initialize counting device
        self._counting_device.lock()
        clock_status = self._counting_device.set_up_finite_counter_clock(
            clock_frequency=self._step_freq[self._first_scan_axis])
        if clock_status < 0:
            self._counting_device.unlock()
            self.unlock()
            return -1

        # Todo: The connection to the GUI amount of samples needs to be made
        # maybe a value given by the function needs to be implemented here
        scanner_status = self._counting_device.set_up_finite_counter(self._steps_scan_line)
        if scanner_status < 0:
            self._counting_device.close_finite_counter_clock()
            self._counting_device.unlock()
            self.unlock()
            return -1

        # check axis status
        if self._stepper_mode[self._first_scan_axis] != "stepping":
            axis_status1 = self.set_mode_stepping(self._first_scan_axis)
        else:
            axis_status1 = self._check_mode(self._first_scan_axis)
        if self._stepper_mode[self._second_scan_axis] != "stepping":
            axis_status2 = self.set_mode_stepping(self._second_scan_axis)
        else:
            axis_status2 = self._check_mode(self._second_scan_axis)
        if axis_status1 < 0 or axis_status2 < 0:
            # Todo: is this really sensible here?
            self.set_mode_ground(self._first_scan_axis)
            self.set_mode_ground(self._second_scan_axis)
            self.unlock()
            self._counting_device.unlock()
            return -1
        self._stepping_device.lock()

        self.signal_step_lines_next.emit(True)

        return 0

    def stop_stepper(self):
        """"Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        # Todo: Make sure attocube axis are set back to gnd if deemed sensible
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
        freq_status = self._check_freq(self._first_scan_axis)
        amp_status = self._check_amplitude(self._second_scan_axis)
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1
        freq_status = self._check_freq(self._first_scan_axis)
        amp_status = self._check_amplitude(self._second_scan_axis)
        if freq_status < 0 or amp_status < 0:
            self.unlock()
            return -1

        pass

    def move_to_position(self, x=None, y=None, z=None):
        """Moving the stepping device (approximately) to the desired new position from the GUI.

        @param int x: if defined, position in x-direction (steps)
        @param int y: if defined, position in y-direction (steps)
        @param int z: if defined, position in z-direction (steps)

        @return int: error code (0:OK, -1:error)
        """

        self.log.info("Movement of attocubes to an absolute position no possible for steppers.\n"
                      "The position moved to is the given of amount of steps, not a physical "
                      "given range away")
        # Check if freq and voltage are set as set in GUI

        if x is not None and int(x) != self._current_x:
            # check freq and amplitude
            status_freq = self._check_freq("x")
            status_amp = self._check_amplitude("x")
            if status_amp < 0:
                self.log.error("A stepping is not possible, as the amplitude in the system and "
                               "the amp. in the gui are different for the x axis.Please check")
                return -1
            if status_freq < 0:
                self.log.error("A stepping is not possible, as the frequency in the system and "
                               "the freq. in the gui are different for the x axis.Please check")
                return -1

            x = int(x)
            # check the direction of the movement
            out = True
            x_steps = x - self._current_x
            if x_steps < 0:
                out = False
            return_value = self._stepping_device.move_attocube("x", True, out, steps=abs(x_steps))
            self._current_x = x
            if return_value == -1:
                return return_value

        if y is not None and int(y) != self._current_y:
            # check freq and amplitude
            status_freq = self._check_freq("y")
            status_amp = self._check_amplitude("y")
            if status_amp < 0:
                self.log.error("A stepping is not possible, as the amplitude in the system and "
                               "the amp. in the gui are different for the y axis.Please check")
                return -1
            if status_freq < 0:
                self.log.error("A stepping is not possible, as the frequency in the system and "
                               "the freq. in the gui are different for the y axis.Please check")
                return -1

            y = int(y)
            # check the direction of the movement
            out = True
            y_steps = y - self._current_y
            if y_steps < 0:
                out = False
            return_value = self._stepping_device.move_attocube("y", True, out, steps=abs(y_steps))
            self._current_y = y
            if return_value == -1:
                return return_value

        if z is not None and int(z) != self._current_z:
            # check freq and amplitude
            status_freq = self._check_freq("z")
            status_amp = self._check_amplitude("z")
            if status_amp < 0:
                self.log.error("A stepping is not possible, as the amplitude in the system and "
                               "the amp. in the gui are different for the z axis.Please check")
                return -1
            if status_freq < 0:
                self.log.error("A stepping is not possible, as the frequency in the system and "
                               "the freq. in the gui are different for the z axis.Please check")
                return -1

            z = int(z)
            # check the direction of the movement
            out = True
            z_steps = z - self._current_z
            if z_steps < 0:
                out = False
            return_value = self._stepping_device.move_attocube("z", True, out, steps=abs(z_steps))
            self._current_z = z
            return return_value
        self.log.warning("No movement was defined or necessary")
        return 0

    def get_position(self):
        """ Get position from stepping device.

        @return list: with three entries x, y and z denoting the current
                      position in meters
        """
        pass
        # Todo this only works with position feedback hardware. Not sure if should be kept, as not possible for half the steppers

    def _step_line(self, direction):
        """Stepping a line

        @param bool direction: the direction in which the previous line was scanned

        @return bool: If true scan was in up direction, if false scan was in down direction
        """
        # Todo: Make sure how to implement the threadlocking here correctly.

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
                return

        if self._step_counter == 0:
            # Todo: Right now only square images possible. Needs to be update.
            self._stepping_raw_data = np.zeros((self._steps_scan_line, self._steps_scan_line))

        # move and count
        new_counts = self._step_and_count(self._first_scan_axis, self._second_scan_axis, direction,
                                          steps=self._steps_scan_line)
        if new_counts[0] == -1:
            self.stopRequested = True
            self.signal_step_lines_next.emit(direction)
            return

        if not direction:  # flip the count direction
            new_counts = np.flipud(new_counts)
        direction = not direction  # invert direction
        self._stepping_raw_data[self._step_counter] = new_counts

        self._step_counter += 1
        if self._step_counter > self._steps_scan_line - 1:
            self.stopRequested = True

        self.signal_step_lines_next.emit(direction)


        # Todo This needs to do the following things: scan a line with the given amount of steps and th

    def _step_and_count(self, mainaxis, secondaxis, direction=True, steps=1):
        """

        @param str axis: Axis for which the stepping should take place
        @param bool direction: direction of stepping (up: True or down: False)
        @param int steps: amount of steps, default 1
        @return np.array: acquired data in counts/s or error value -1
        """
        # check axis
        if mainaxis in self.axis.keys():
            if secondaxis in self.axis.keys():
                if self._counting_device.start_finite_counter() < 0:
                    self.log.error("Starting the counter failed")
                    return -1

                if self._stepping_device.move_attocube(mainaxis, True, direction, steps=steps - 1) < 0:
                    self.log.error("moving of attocube failed")
                    return -1

                # move on line up
                if self._stepping_device.move_attocube(secondaxis, True, True, 1) < 0:
                    self.log.error("moving of attocube failed")
                    return -1

                # Todo: Check if there is a better way than this to adjust for the fact that a stepping
                # direction change is necessary for the last count. Maybe different method arrangement
                # sensible

                time.sleep(steps / self._step_freq[mainaxis])  # wait till stepping finished for readout
                result = self._counting_device.get_finite_counts()
                retval = 0
                a = self._counting_device.stop_finite_counter()
                if result[0][0] == [-1]:
                    self.log.error("The readout of the counter failed")
                    retval = -1
                elif result[1] != steps:
                    self.log.error("A different amount of data than necessary was returned.\n "
                                   "Received {} instead of {} bins with counts ".format(result[1], steps))
                    retval = -1
                elif a < 0:
                    retval = -1
                    self.log.error("Stopping the counter failed")
                else:
                    retval = result[0]

                return retval
            else:
                self.log.error("second axis {} in not  an axis {} of the stepper".format_map(secondaxis, self.axis))
                return -1
        else:
            self.log.error("main axis {} is not an axis {} of the stepper".format_map(mainaxis, self.axis))
            return -1

    ##################################### Acquire Data ###########################################

    def _initalize_stepping(self):
        """"

        return
        """
        pass

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

    ##################################### Handle Data ########################################

    def initialize_image(self):
        """Initalization of the image.

        @return int: error code (0:OK, -1:error)
        """
        pass

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
        # Prepare the metadata parameters (common to both saved files):
        parameters = OrderedDict()

        self._get_scan_axes()
        parameters['First Axis'] = self._first_scan_axis
        parameters['First Axis Steps'] = self._steps_scan_line
        parameters['First Axis Frequency'] = self._step_freq[self._second_scan_axis]
        parameters['First Axis Amplitude'] = self.step_amplitude[self._second_scan_axis]

        parameters['Second Axis'] = self._second_scan_axis
        # Todo: Update when square images are not necessary anymore
        parameters['Second Axis Steps'] = self._steps_scan_line
        # Todo self._step_freq and self.step_amplitude should be named in a similar fashion
        parameters['Second Axis Frequency'] = self._step_freq[self._second_scan_axis]
        parameters['Second Axis Amplitude'] = self.step_amplitude[self._second_scan_axis]

        # parameters['XY Image at z position (m)'] = self._current_z
        # Todo: add starting "x" "y" position

        # Prepare a figure to be saved
        # figure_data = self.xy_image[:, :, 3]
        # image_extent = [0,
        #                self._steps_scan_line,
        #                0,
        #                self._steps_scan_line]
        # axes = [self._first_scan_axis, self._second_scan_axis]
        # crosshair_pos = [self.get_position()[0], self.get_position()[1]]

        # figs = {ch: self.draw_figure(data=self.xy_image[:, :, 3 + n],
        #                             image_extent=image_extent,
        #                             scan_axis=axes,
        #                             cbar_range=colorscale_range,
        #                             percentile_range=percentile_range)
        #        for n, ch in enumerate(self.get_scanner_count_channels())}

        # Save the image data and figure
        for n, ch in enumerate(self.get_counter_count_channels()):
            # data for the text-array "image":
            image_data = OrderedDict()
            image_data['Confocal pure {}{} scan image data without axis.\n'
                       'The upper left entry represents the signal at the upper left pixel '
                       'position.\nA pixel-line in the image corresponds to a row '
                       'of entries where the Signal is in counts/s:'.format(
                self._first_scan_axis, self._second_scan_axis)] = self._stepping_raw_data

            filelabel = 'confocal_xy_image_{0}'.format(ch.replace('/', ''))
            self._save_logic.save_data(image_data,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       plotfig=None)

        # prepare the full raw data in an OrderedDict:
        # data = OrderedDict()
        # data['{} steps'.format(self._first_scan_axis)] = self.xy_image[:, :, 0].flatten()
        # data['{} steps'.format(self._second_scan_axis)] = self.xy_image[:, :, 1].flatten()

        # for n, ch in enumerate(self.get_scanner_count_channels()):
        #    data['count rate {0} (Hz)'.format(ch)] = self.xy_image[:, :, 3 + n].flatten()

        # Save the raw data to file
        # filelabel = 'confocal_xy_data'
        # self._save_logic.save_data(data,
        #                           filepath=filepath,
        #                           timestamp=timestamp,
        #                           parameters=parameters,
        #                           filelabel=filelabel,
        #                           fmt='%.6e',
        #                           delimiter='\t')

        self.log.debug('Confocal Stepper Image saved.')
        # self.signal_xy_data_saved.emit()
        # Todo Ask if it is possible to write only one save with options for which lines were scanned
        return

    def draw_figure(self, data, image_extent, scan_axis=None, cbar_range=None,
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

        # Todo Probably the function from confocal logic, that already exists need to be chaned only slightly
        return None

    ##################################### Tilt correction ########################################

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

    ##################################### Move through History ########################################

    def history_forward(self):
        """ Move forward in confocal image history.
        """
        pass
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.history[self.history_index].restore(self)
            self.signal_xy_image_updated.emit()
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
            self.signal_xy_image_updated.emit()
            self.signal_depth_image_updated.emit()
            self.signal_tilt_correction_update.emit()
            self.signal_tilt_correction_active.emit(self._scanning_device.tiltcorrection)
            self._change_position('history')
            self.signal_change_position.emit('history')
            self.signal_history_event.emit()
