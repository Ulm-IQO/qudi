# -*- coding: utf-8 -*
"""
This file contains the Qudi logic class for optimizing scanner position.

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
import numpy as np
import time

from logic.generic_logic import GenericLogic
from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex


class OptimizerLogic(GenericLogic):

    """This is the Logic class for optimizing scanner position on bright features.
    """

    # declare connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    fitlogic = Connector(interface='FitLogic')

    # declare status vars
    _clock_frequency = StatusVar('clock_frequency', 50)
    return_slowness = StatusVar(default=20)
    refocus_XY_size = StatusVar('xy_size', 0.6e-6)
    optimizer_XY_res = StatusVar('xy_resolution', 10)
    refocus_Z_size = StatusVar('z_size', 2e-6)
    optimizer_Z_res = StatusVar('z_resolution', 30)
    hw_settle_time = StatusVar('settle_time', 0.1)
    optimization_sequence = StatusVar(default=['XY', 'Z'])
    do_surface_subtraction = StatusVar('surface_subtraction', False)
    surface_subtr_scan_offset = StatusVar('surface_subtraction_offset', 1e-6)
    opt_channel = StatusVar('optimization_channel', 0)

    # "private" signals to keep track of activities here in the optimizer logic
    _sigScanNextXyLine = QtCore.Signal()
    _sigScanZLine = QtCore.Signal()
    _sigCompletedXyOptimizerScan = QtCore.Signal()
    _sigDoNextOptimizationStep = QtCore.Signal()
    _sigFinishedAllOptimizationSteps = QtCore.Signal()

    # public signals
    sigImageUpdated = QtCore.Signal()
    sigRefocusStarted = QtCore.Signal(str)
    sigRefocusXySizeChanged = QtCore.Signal()
    sigRefocusZSizeChanged = QtCore.Signal()
    sigRefocusFinished = QtCore.Signal(str, list)
    sigClockFrequencyChanged = QtCore.Signal(int)
    sigPositionChanged = QtCore.Signal(float, float, float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        self.stopRequested = False
        self.is_crosshair = True

        # Keep track of who called the refocus
        self._caller_tag = ''

    def on_activate(self):
        """ Initialisation performed during activation of the module.

        @return int: error code (0:OK, -1:error)
        """
        self._scanning_device = self.confocalscanner1()
        self._fit_logic = self.fitlogic()

        # Reads in the maximal scanning range. The unit of that scan range is micrometer!
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]

        self._initial_pos_x = 0.
        self._initial_pos_y = 0.
        self._initial_pos_z = 0.
        self.optim_pos_x = self._initial_pos_x
        self.optim_pos_y = self._initial_pos_y
        self.optim_pos_z = self._initial_pos_z
        self.optim_sigma_x = 0.
        self.optim_sigma_y = 0.
        self.optim_sigma_z = 0.

        self._max_offset = 3.

        # Sets the current position to the center of the maximal scanning range
        self._current_x = (self.x_range[0] + self.x_range[1]) / 2
        self._current_y = (self.y_range[0] + self.y_range[1]) / 2
        self._current_z = (self.z_range[0] + self.z_range[1]) / 2
        self._current_a = 0.0

        ###########################
        # Fit Params and Settings #
        model, params = self._fit_logic.make_gaussianlinearoffset_model()
        self.z_params = params
        self.use_custom_params = {name: False for name, param in params.items()}

        # Initialization of internal counter for scanning
        self._xy_scan_line_count = 0

        # Initialization of optimization sequence step counter
        self._optimization_step = 0

        # Sets connections between signals and functions
        self._sigScanNextXyLine.connect(self._refocus_xy_line, QtCore.Qt.QueuedConnection)
        self._sigScanZLine.connect(self.do_z_optimization, QtCore.Qt.QueuedConnection)
        self._sigCompletedXyOptimizerScan.connect(self._set_optimized_xy_from_fit, QtCore.Qt.QueuedConnection)

        self._sigDoNextOptimizationStep.connect(self._do_next_optimization_step, QtCore.Qt.QueuedConnection)
        self._sigFinishedAllOptimizationSteps.connect(self.finish_refocus)
        self._initialize_xy_refocus_image()
        self._initialize_z_refocus_image()
        return 0

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def check_optimization_sequence(self):
        """ Check the sequence of scan events for the optimization.
        """

        # Check the supplied optimization sequence only contains 'XY' and 'Z'
        if len(set(self.optimization_sequence).difference({'XY', 'Z'})) > 0:
            self.log.error('Requested optimization sequence contains unknown steps. Please provide '
                           'a sequence containing only \'XY\' and \'Z\' strings. '
                           'The default [\'XY\', \'Z\'] will be used.')
            self.optimization_sequence = ['XY', 'Z']

    def get_scanner_count_channels(self):
        """ Get lis of counting channels from scanning device.
          @return list(str): names of counter channels
        """
        return self._scanning_device.get_scanner_count_channels()

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        # checks if scanner is still running
        if self.module_state() == 'locked':
            return -1
        else:
            self._clock_frequency = int(clock_frequency)
        self.sigClockFrequencyChanged.emit(self._clock_frequency)
        return 0

    def set_refocus_XY_size(self, size):
        """ Set the number of pixels in the refocus image for X and Y directions

            @param int size: XY image size in pixels
        """
        self.refocus_XY_size = size
        self.sigRefocusXySizeChanged.emit()

    def set_refocus_Z_size(self, size):
        """ Set the number of values for Z refocus

            @param int size: number of values for Z refocus
        """
        self.refocus_Z_size = size
        self.sigRefocusZSizeChanged.emit()

    def start_refocus(self, initial_pos=None, caller_tag='unknown', tag='logic'):
        """ Starts the optimization scan around initial_pos

            @param list initial_pos: with the structure [float, float, float]
            @param str caller_tag:
            @param str tag:
        """
        # checking if refocus corresponding to crosshair or corresponding to initial_pos


        if isinstance(initial_pos, (np.ndarray,)) and initial_pos.size >= 3:
            self._initial_pos_x, self._initial_pos_y, self._initial_pos_z = initial_pos[0:3]
        elif isinstance(initial_pos, (list, tuple)) and len(initial_pos) >= 3:
            self._initial_pos_x, self._initial_pos_y, self._initial_pos_z = initial_pos[0:3]
        elif initial_pos is None:
            scpos = self._scanning_device.get_scanner_position()[0:3]
            self._initial_pos_x, self._initial_pos_y, self._initial_pos_z = scpos
        else:
            pass  # TODO: throw error

        # Keep track of where the start_refocus was initiated
        self._caller_tag = caller_tag

        # Set the optim_pos values to match the initial_pos values.
        # This means we can use optim_pos in subsequent steps and ensure
        # that we benefit from any completed optimization step.
        self.optim_pos_x = self._initial_pos_x
        self.optim_pos_y = self._initial_pos_y
        self.optim_pos_z = self._initial_pos_z
        self.optim_sigma_x = 0.
        self.optim_sigma_y = 0.
        self.optim_sigma_z = 0.
        #
        self._xy_scan_line_count = 0
        self._optimization_step = 0
        self.check_optimization_sequence()

        scanner_status = self.start_scanner()
        if scanner_status < 0:
            self.sigRefocusFinished.emit(
                self._caller_tag,
                [self.optim_pos_x, self.optim_pos_y, self.optim_pos_z, 0])
            return
        self.sigRefocusStarted.emit(tag)
        self._sigDoNextOptimizationStep.emit()

    def stop_refocus(self):
        """Stops refocus."""
        with self.threadlock:
            self.stopRequested = True

    def _initialize_xy_refocus_image(self):
        """Initialisation of the xy refocus image."""
        self._xy_scan_line_count = 0

        # Take optim pos as center of refocus image, to benefit from any previous
        # optimization steps that have occurred.
        x0 = self.optim_pos_x
        y0 = self.optim_pos_y

        # defining position intervals for refocushttp://www.spiegel.de/
        xmin = np.clip(x0 - 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        xmax = np.clip(x0 + 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        ymin = np.clip(y0 - 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        ymax = np.clip(y0 + 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])

        self._X_values = np.linspace(xmin, xmax, num=self.optimizer_XY_res)
        self._Y_values = np.linspace(ymin, ymax, num=self.optimizer_XY_res)
        self._Z_values = self.optim_pos_z * np.ones(self._X_values.shape)
        self._A_values = np.zeros(self._X_values.shape)
        self._return_X_values = np.linspace(xmax, xmin, num=self.optimizer_XY_res)
        self._return_A_values = np.zeros(self._return_X_values.shape)

        self.xy_refocus_image = np.zeros((
            len(self._Y_values),
            len(self._X_values),
            3 + len(self.get_scanner_count_channels())))
        self.xy_refocus_image[:, :, 0] = np.full((len(self._Y_values), len(self._X_values)), self._X_values)
        y_value_matrix = np.full((len(self._X_values), len(self._Y_values)), self._Y_values)
        self.xy_refocus_image[:, :, 1] = y_value_matrix.transpose()
        self.xy_refocus_image[:, :, 2] = self.optim_pos_z * np.ones((len(self._Y_values), len(self._X_values)))

    def _initialize_z_refocus_image(self):
        """Initialisation of the z refocus image."""
        self._xy_scan_line_count = 0

        # Take optim pos as center of refocus image, to benefit from any previous
        # optimization steps that have occurred.
        z0 = self.optim_pos_z

        zmin = np.clip(z0 - 0.5 * self.refocus_Z_size, self.z_range[0], self.z_range[1])
        zmax = np.clip(z0 + 0.5 * self.refocus_Z_size, self.z_range[0], self.z_range[1])

        self._zimage_Z_values = np.linspace(zmin, zmax, num=self.optimizer_Z_res)
        self._fit_zimage_Z_values = np.linspace(zmin, zmax, num=self.optimizer_Z_res)
        self._zimage_A_values = np.zeros(self._zimage_Z_values.shape)
        self.z_refocus_line = np.zeros((
            len(self._zimage_Z_values),
            len(self.get_scanner_count_channels())))
        self.z_fit_data = np.zeros(len(self._fit_zimage_Z_values))

    def _move_to_start_pos(self, start_pos):
        """Moves the scanner from its current position to the start position of the optimizer scan.

        @param start_pos float[]: 3-point vector giving x, y, z position to go to.
        """
        n_ch = len(self._scanning_device.get_scanner_axes())
        scanner_pos = self._scanning_device.get_scanner_position()
        lsx = np.linspace(scanner_pos[0], start_pos[0], self.return_slowness)
        lsy = np.linspace(scanner_pos[1], start_pos[1], self.return_slowness)
        lsz = np.linspace(scanner_pos[2], start_pos[2], self.return_slowness)
        if n_ch <= 3:
            move_to_start_line = np.vstack((lsx, lsy, lsz)[0:n_ch])
        else:
            move_to_start_line = np.vstack((lsx, lsy, lsz, np.ones(lsx.shape) * scanner_pos[3]))

        counts = self._scanning_device.scan_line(move_to_start_line)
        if np.any(counts == -1):
            return -1

        time.sleep(self.hw_settle_time)
        return 0

    def _refocus_xy_line(self):
        """Scanning a line of the xy optimization image.
        This method repeats itself using the _sigScanNextXyLine
        until the xy optimization image is complete.
        """
        n_ch = len(self._scanning_device.get_scanner_axes())
        # stop scanning if instructed
        if self.stopRequested:
            with self.threadlock:
                self.stopRequested = False
                self.finish_refocus()
                self.sigImageUpdated.emit()
                self.sigRefocusFinished.emit(
                    self._caller_tag,
                    [self.optim_pos_x, self.optim_pos_y, self.optim_pos_z, 0][0:n_ch])
                return

        # move to the start of the first line
        if self._xy_scan_line_count == 0:
            status = self._move_to_start_pos([self.xy_refocus_image[0, 0, 0],
                                              self.xy_refocus_image[0, 0, 1],
                                              self.xy_refocus_image[0, 0, 2]])
            if status < 0:
                self.log.error('Error during move to starting point.')
                self.stop_refocus()
                self._sigScanNextXyLine.emit()
                return

        lsx = self.xy_refocus_image[self._xy_scan_line_count, :, 0]
        lsy = self.xy_refocus_image[self._xy_scan_line_count, :, 1]
        lsz = self.xy_refocus_image[self._xy_scan_line_count, :, 2]

        # scan a line of the xy optimization image
        if n_ch <= 3:
            line = np.vstack((lsx, lsy, lsz)[0:n_ch])
        else:
            line = np.vstack((lsx, lsy, lsz, np.zeros(lsx.shape)))

        line_counts = self._scanning_device.scan_line(line)
        if np.any(line_counts == -1):
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_refocus()
            self._sigScanNextXyLine.emit()
            return

        lsx = self._return_X_values
        lsy = self.xy_refocus_image[self._xy_scan_line_count, 0, 1] * np.ones(lsx.shape)
        lsz = self.xy_refocus_image[self._xy_scan_line_count, 0, 2] * np.ones(lsx.shape)
        if n_ch <= 3:
            return_line = np.vstack((lsx, lsy, lsz))
        else:
            return_line = np.vstack((lsx, lsy, lsz, np.zeros(lsx.shape)))

        return_line_counts = self._scanning_device.scan_line(return_line)
        if np.any(return_line_counts == -1):
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_refocus()
            self._sigScanNextXyLine.emit()
            return

        s_ch = len(self.get_scanner_count_channels())
        self.xy_refocus_image[self._xy_scan_line_count, :, 3:3 + s_ch] = line_counts
        self.sigImageUpdated.emit()

        self._xy_scan_line_count += 1

        if self._xy_scan_line_count < np.size(self._Y_values):
            self._sigScanNextXyLine.emit()
        else:
            self._sigCompletedXyOptimizerScan.emit()

    def _set_optimized_xy_from_fit(self):
        """Fit the completed xy optimizer scan and set the optimized xy position."""
        fit_x, fit_y = np.meshgrid(self._X_values, self._Y_values)
        xy_fit_data = self.xy_refocus_image[:, :, 3+self.opt_channel].ravel()
        axes = np.empty((len(self._X_values) * len(self._Y_values), 2))
        axes = (fit_x.flatten(), fit_y.flatten())
        result_2D_gaus = self._fit_logic.make_twoDgaussian_fit(
            xy_axes=axes,
            data=xy_fit_data,
            estimator=self._fit_logic.estimate_twoDgaussian_MLE
        )
        # print(result_2D_gaus.fit_report())

        if result_2D_gaus.success is False:
            self.log.error('Error: 2D Gaussian Fit was not successfull!.')
            print('2D gaussian fit not successfull')
            self.optim_pos_x = self._initial_pos_x
            self.optim_pos_y = self._initial_pos_y
            self.optim_sigma_x = 0.
            self.optim_sigma_y = 0.
        else:
            #                @reviewer: Do we need this. With constraints not one of these cases will be possible....
            if abs(self._initial_pos_x - result_2D_gaus.best_values['center_x']) < self._max_offset and abs(self._initial_pos_x - result_2D_gaus.best_values['center_x']) < self._max_offset:
                if self.x_range[0] <= result_2D_gaus.best_values['center_x'] <= self.x_range[1]:
                    if self.y_range[0] <= result_2D_gaus.best_values['center_y'] <= self.y_range[1]:
                        self.optim_pos_x = result_2D_gaus.best_values['center_x']
                        self.optim_pos_y = result_2D_gaus.best_values['center_y']
                        self.optim_sigma_x = result_2D_gaus.best_values['sigma_x']
                        self.optim_sigma_y = result_2D_gaus.best_values['sigma_y']
            else:
                self.optim_pos_x = self._initial_pos_x
                self.optim_pos_y = self._initial_pos_y
                self.optim_sigma_x = 0.
                self.optim_sigma_y = 0.

        # emit image updated signal so crosshair can be updated from this fit
        self.sigImageUpdated.emit()
        self._sigDoNextOptimizationStep.emit()

    def do_z_optimization(self):
        """ Do the z axis optimization."""
        # z scaning
        self._scan_z_line()

        # z-fit
        # If subtracting surface, then data can go negative and the gaussian fit offset constraints need to be adjusted
        if self.do_surface_subtraction:
            adjusted_param = {'offset': {
                'value': 1e-12,
                'min': -self.z_refocus_line[:, self.opt_channel].max(),
                'max': self.z_refocus_line[:, self.opt_channel].max()
            }}
            result = self._fit_logic.make_gausspeaklinearoffset_fit(
                x_axis=self._zimage_Z_values,
                data=self.z_refocus_line[:, self.opt_channel],
                add_params=adjusted_param)
        else:
            if any(self.use_custom_params.values()):
                result = self._fit_logic.make_gausspeaklinearoffset_fit(
                    x_axis=self._zimage_Z_values,
                    data=self.z_refocus_line[:, self.opt_channel],
                    # Todo: It is required that the changed parameters are given as a dictionary or parameter object
                    add_params=None)
            else:
                result = self._fit_logic.make_gaussianlinearoffset_fit(
                    x_axis=self._zimage_Z_values,
                    data=self.z_refocus_line[:, self.opt_channel],
                    units='m',
                    estimator=self._fit_logic.estimate_gaussianlinearoffset_peak
                    )
        self.z_params = result.params

        if result.success is False:
            self.log.error('error in 1D Gaussian Fit.')
            self.optim_pos_z = self._initial_pos_z
            self.optim_sigma_z = 0.
            # interrupt here?
        else:  # move to new position
            #                @reviewer: Do we need this. With constraints not one of these cases will be possible....
            # checks if new pos is too far away
            if abs(self._initial_pos_z - result.best_values['center']) < self._max_offset:
                # checks if new pos is within the scanner range
                if self.z_range[0] <= result.best_values['center'] <= self.z_range[1]:
                    self.optim_pos_z = result.best_values['center']
                    self.optim_sigma_z = result.best_values['sigma']
                    gauss, params = self._fit_logic.make_gaussianlinearoffset_model()
                    self.z_fit_data = gauss.eval(
                        x=self._fit_zimage_Z_values, params=result.params)
                else:  # new pos is too far away
                    # checks if new pos is too high
                    self.optim_sigma_z = 0.
                    if result.best_values['center'] > self._initial_pos_z:
                        if self._initial_pos_z + 0.5 * self.refocus_Z_size <= self.z_range[1]:
                            # moves to higher edge of scan range
                            self.optim_pos_z = self._initial_pos_z + 0.5 * self.refocus_Z_size
                        else:
                            self.optim_pos_z = self.z_range[1]  # moves to highest possible value
                    else:
                        if self._initial_pos_z + 0.5 * self.refocus_Z_size >= self.z_range[0]:
                            # moves to lower edge of scan range
                            self.optim_pos_z = self._initial_pos_z + 0.5 * self.refocus_Z_size
                        else:
                            self.optim_pos_z = self.z_range[0]  # moves to lowest possible value

        self.sigImageUpdated.emit()
        self._sigDoNextOptimizationStep.emit()

    def finish_refocus(self):
        """ Finishes up and releases hardware after the optimizer scans."""
        self.kill_scanner()

        self.log.info(
                'Optimised from ({0:.3e},{1:.3e},{2:.3e}) to local '
                'maximum at ({3:.3e},{4:.3e},{5:.3e}).'.format(
                    self._initial_pos_x,
                    self._initial_pos_y,
                    self._initial_pos_z,
                    self.optim_pos_x,
                    self.optim_pos_y,
                    self.optim_pos_z))

        # Signal that the optimization has finished, and "return" the optimal position along with
        # caller_tag
        self.sigRefocusFinished.emit(
            self._caller_tag,
            [self.optim_pos_x, self.optim_pos_y, self.optim_pos_z, 0])

    def _scan_z_line(self):
        """Scans the z line for refocus."""

        # Moves to the start value of the z-scan
        status = self._move_to_start_pos(
            [self.optim_pos_x, self.optim_pos_y, self._zimage_Z_values[0]])
        if status < 0:
            self.log.error('Error during move to starting point.')
            self.stop_refocus()
            return

        n_ch = len(self._scanning_device.get_scanner_axes())

        # defining trace of positions for z-refocus
        scan_z_line = self._zimage_Z_values
        scan_x_line = self.optim_pos_x * np.ones(self._zimage_Z_values.shape)
        scan_y_line = self.optim_pos_y * np.ones(self._zimage_Z_values.shape)

        if n_ch <= 3:
            line = np.vstack((scan_x_line, scan_y_line, scan_z_line)[0:n_ch])
        else:
            line = np.vstack((scan_x_line, scan_y_line, scan_z_line, np.zeros(scan_x_line.shape)))

        # Perform scan
        line_counts = self._scanning_device.scan_line(line)
        if np.any(line_counts == -1):
            self.log.error('Z scan went wrong, killing the scanner.')
            self.stop_refocus()
            return

        # Set the data
        self.z_refocus_line = line_counts

        # If subtracting surface, perform a displaced depth line scan
        if self.do_surface_subtraction:
            # Move to start of z-scan
            status = self._move_to_start_pos([
                self.optim_pos_x + self.surface_subtr_scan_offset,
                self.optim_pos_y,
                self._zimage_Z_values[0]])
            if status < 0:
                self.log.error('Error during move to starting point.')
                self.stop_refocus()
                return

            # define an offset line to measure "background"
            if n_ch <= 3:
                line_bg = np.vstack(
                    (scan_x_line + self.surface_subtr_scan_offset, scan_y_line, scan_z_line)[0:n_ch])
            else:
                line_bg = np.vstack(
                    (scan_x_line + self.surface_subtr_scan_offset,
                     scan_y_line,
                     scan_z_line,
                     np.zeros(scan_x_line.shape)))

            line_bg_counts = self._scanning_device.scan_line(line_bg)
            if np.any(line_bg_counts[0] == -1):
                self.log.error('The scan went wrong, killing the scanner.')
                self.stop_refocus()
                return

            # surface-subtracted line scan data is the difference
            self.z_refocus_line = line_counts - line_bg_counts

    def start_scanner(self):
        """Setting up the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        self.module_state.lock()
        clock_status = self._scanning_device.set_up_scanner_clock(
            clock_frequency=self._clock_frequency)
        if clock_status < 0:
            self.module_state.unlock()
            return -1

        scanner_status = self._scanning_device.set_up_scanner()
        if scanner_status < 0:
            self._scanning_device.close_scanner_clock()
            self.module_state.unlock()
            return -1

        return 0

    def kill_scanner(self):
        """Closing the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            rv = self._scanning_device.close_scanner()
        except:
            self.log.exception('Closing refocus scanner failed.')
            return -1
        try:
            rv2 = self._scanning_device.close_scanner_clock()
        except:
            self.log.exception('Closing refocus scanner clock failed.')
            return -1
        self.module_state.unlock()
        return rv + rv2

    def _do_next_optimization_step(self):
        """Handle the steps through the specified optimization sequence
        """

        # At the end fo the sequence, finish the optimization
        if self._optimization_step == len(self.optimization_sequence):
            self._sigFinishedAllOptimizationSteps.emit()
            return

        # Read the next step in the optimization sequence
        this_step = self.optimization_sequence[self._optimization_step]

        # Increment the step counter
        self._optimization_step += 1

        # Launch the next step
        if this_step == 'XY':
            self._initialize_xy_refocus_image()
            self._sigScanNextXyLine.emit()
        elif this_step == 'Z':
            self._initialize_z_refocus_image()
            self._sigScanZLine.emit()

    def set_position(self, tag, x=None, y=None, z=None, a=None):
        """ Set focus position.

            @param str tag: sting indicating who caused position change
            @param float x: x axis position in m
            @param float y: y axis position in m
            @param float z: z axis position in m
            @param float a: a axis position in m
        """
        if x is not None:
            self._current_x = x
        if y is not None:
            self._current_y = y
        if z is not None:
            self._current_z = z
        self.sigPositionChanged.emit(self._current_x, self._current_y, self._current_z)

