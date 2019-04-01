# -*- coding: utf-8 -*-

"""
This file contains the general logic for magnet control/alignment.

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
import numpy as np
import time

from collections import OrderedDict
from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from interface.slow_counter_interface import CountingMode


class AlignmentMethod:
    """

    """
    def __init__(self, **kwargs):
        if 'save_after_measure' in kwargs:
            self.save_after_measure = bool(kwargs['save_after_measure'])
        else:
            self.save_after_measure = True
        self.measurement_time = kwargs.get('measurement_time')

    @property
    def parameters(self):
        return self.__dict__.copy()


class OdmrFrequencyAlignment(AlignmentMethod):
    """

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.low_freq_range = kwargs.get('low_freq_range')
        self.high_freq_range = kwargs.get('high_freq_range')
        self.low_power = kwargs.get('low_power')
        self.high_power = kwargs.get('high_power')
        self.low_points = kwargs.get('low_points')
        self.high_points = kwargs.get('high_points')
        self.fit_name = kwargs.get('fit_name')
        self.low_result_param = kwargs.get(
            'result_param') if 'result_param' in kwargs else kwargs.get('low_result_param')
        self.high_result_param = kwargs.get(
            'result_param') if 'result_param' in kwargs else kwargs.get('high_result_param')
        return


class OdmrContrastAlignment(AlignmentMethod):
    """

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.freq_range = kwargs.get('freq_range')
        self.power = kwargs.get('power')
        self.points = kwargs.get('points')
        self.fit_name = kwargs.get('fit_name')
        self.result_param = kwargs.get('result_param')
        return


class FluorescenceAlignment(AlignmentMethod):
    """

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration_time = kwargs.get('integration_time')
        return


class MagnetLogic(GenericLogic):
    """
    A general magnet logic to control an magnetic stage with an arbitrary set of axis.
    """

    _modclass = 'MagnetLogic'
    _modtype = 'logic'

    # declare connectors
    magnetstage = Connector(interface='MagnetInterface')
    optimizerlogic = Connector(interface='OptimizerLogic')
    counterlogic = Connector(interface='CounterLogic')
    odmrlogic = Connector(interface='ODMRLogic')
    savelogic = Connector(interface='SaveLogic')
    scannerlogic = Connector(interface='ScannerLogic')
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')

    # Declare status variables
    _align_2d_axis_names = StatusVar(name='align_2d_axis_names', default=tuple())
    _align_2d_axis_ranges = StatusVar(name='align_2d_axis_ranges', default=dict())
    _align_2d_axis_points = StatusVar(name='align_2d_axis_points', default=dict())
    _align_2d_axis_velocities = StatusVar(name='align_2d_axis_velocities', default=dict())
    _align_2d_pathway_mode = StatusVar(name='align_2d_pathway_mode', default='meander')
    _alignment_method = StatusVar('alignment_method', 'fluorescence')

    _2d_data = StatusVar(name='2d_data_matrix', default=np.zeros((2, 2), dtype=float))
    # _2d_dim1_values = StatusVar(name='2d_dim1_values', default=np.zeros(2, dtype=float))
    # _2d_dim2_values = StatusVar(name='2d_dim1_values', default=np.zeros(2, dtype=float))

    _odmr_frequency_alignment = StatusVar(name='odmr_frequency_alignment', default=dict())
    _odmr_contrast_alignment = StatusVar(name='odmr_contrast_alignment', default=dict())
    _fluorescence_alignment = StatusVar(name='fluorescence_alignment', default=dict())

    # Declare signals
    sigAlignmentParametersChanged = QtCore.Signal(dict)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sig2dDataUpdated = QtCore.Signal(np.ndarray)
    sigMagnetPositionUpdated = QtCore.Signal(dict)
    sigMagnetVelocityUpdated = QtCore.Signal(dict)

    _sigMeasurementLoop = QtCore.Signal()

    _available_path_modes = ('diagonal-meander', 'meander', 'spiral-in', 'spiral-out')
    _available_alignment_methods = ('fluorescence', 'odmr_frequency', 'odmr_contrast')

    def __init__(self, config, **kwargs):
        """

        """
        super().__init__(config=config, **kwargs)
        self._thread_lock = Mutex()

        self._measurement_paused = False
        self._stop_requested = True

        self._2d_path = None
        self._2d_path_index = 0
        return

    def on_activate(self):
        """
        Actions performed upon loading/activating this module go here.
        """
        self._measurement_paused = False
        self._stop_requested = True

        self._sigMeasurementLoop.connect(self._measurement_loop, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """
        Deactivate the module properly.
        """
        self._sigMeasurementLoop.disconnect()
        return

    @property
    def available_path_modes(self):
        return self._available_path_modes

    @property
    def available_alignment_methods(self):
        return self._available_alignment_methods

    @property
    def magnet_constraints(self):
        return self.magnetstage().get_constraints()

    @property
    def magnet_position(self):
        return self.magnetstage().get_pos()

    @property
    def magnet_status(self):
        return self.magnetstage().get_status()

    @QtCore.Slot()
    def update_magnet_position(self):
        self.sigMagnetPositionUpdated.emit(self.magnet_position)
        return

    def move_magnet_rel(self, param_dict):
        """ Move the specified axis in the param_dict relative with an assigned
            value.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters. E.g., for a movement of an axis
                                labeled with 'x' by 23 the dict should have the
                                form:
                                    param_dict = { 'x' : 23 }
        @return param dict: dictionary, which passes all the relevant
                                parameters. E.g., for a movement of an axis
                                labeled with 'x' by 23 the dict should have the
                                form:
                                    param_dict = { 'x' : 23 }
        """
        pos = self.magnetstage().move_rel(param_dict)
        self.sigMagnetPositionUpdated.emit(pos)
        return pos

    def move_magnet_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return param dict: dictionary, which passes all the relevant
                                parameters. E.g., for a movement of an axis
                                labeled with 'x' by 23 the dict should have the
                                form:
                                    param_dict = { 'x' : 23 }
        """
        pos = self.magnetstage().move_abs(param_dict)
        self.sigMagnetPositionUpdated.emit(pos)
        return pos

    def abort_movement(self):
        """ Stops movement of the stage. """
        self.magnetstage().abort()
        if self.module_state() == 'locked':
            self.stop_measurement()
        return

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        vel = self.magnetstage().set_velocity(param_dict)
        self.sigMagnetVelocityUpdated.emit(vel)
        return vel

    def _create_2d_pathway(self, axes_names, axes_ranges, axes_points):
        """
        Create a path along with the magnet should move.

        @param str[2] axes_names:
        @param float[2] axes_ranges:
        @param int[2] axes_points:

        @return list: Each list item is a dict with the positions for each axis at this step

        The returned list has the following structure:
            [ pos1_dict, pos2_dict, pos3_dict, ...]

        Each dictionary in the list has two keys:
             pos1_dict[axes_names[0]] = <first_coordinate_for_step1>
             pos1_dict[axes_names[1]] = <second_coordinate_for_step1>
             pos2_dict[axes_names[0]] = <first_coordinate_for_step2>
             pos2_dict[axes_names[1]] = <second_coordinate_for_step2>
        """
        pathway = list()

        if self._align_2d_pathway_mode not in self.available_2d_path_modes:
            self.log.error('Unknown 2D alignment pathway mode.')
            return pathway

        # TODO: create all path modes
        if self._align_2d_pathway_mode == 'meander':
            # create a meandering stepping procedure through the matrix
            # calculate coordinates for each axis
            positions = (
                np.linspace(axes_ranges[0][0], axes_ranges[0][0], axes_points[0], dtype=float),
                np.linspace(axes_ranges[1][0], axes_ranges[1][0], axes_points[1], dtype=float))
            for dim2_val in positions[1]:
                for dim1_val in positions[0]:
                    pathway.append({axes_names[0]: dim1_val, axes_names[1]: dim2_val})
        else:
            self.log.error('2D alignment pathway method "{0}" not implemented yet.'
                           ''.format(self._align_2d_pathway_mode))
        return pathway

    @QtCore.Slot(bool)
    def toggle_measurement(self, start):
        if start:
            self.start_measurement()
        else:
            self.stop_measurement()
        return

    def start_measurement(self):
        """

        @return:
        """
        with self._thread_lock:
            if self._check_measurement_start_conditions():
                self.sigMeasurementStatusUpdated.emit(
                    self.module_state() == 'locked', self._measurement_paused)
                return

            self.module_state.lock()
            self._measurement_paused = False
            self._stop_requested = False
            self.sigMeasurementStatusUpdated.emit(True, False)
            self._2d_path = self._create_2d_pathway(axes_names=self._align_2d_axis_names,
                                                    axes_ranges=self._align_2d_axis_ranges,
                                                    axes_points=self._align_2d_axis_points)
            self._2d_path_index = 0
            self._2d_data = np.zeros((len(self._2d_path), 3), dtype=float)
            self._sigMeasurementLoop.emit()
        return

    def _check_measurement_start_conditions(self):
        if self.module_state() != 'idle':
            self.log.error('Can not start new measurement. Measurement still in progress.')
            return True

        if self.magnet_status & 1:
            self.log.error('Can not start measurement procedure. Magnet already moving.')
            return True

        if self._alignment_method not in self._available_alignment_methods:
            self.log.error('Can not start measurement. Unknown alignment method "{0}".'
                           ''.format(self._alignment_method))
            return True

        if self._alignment_method == 'fluorescence':
            if self.counterlogic().module_state() != 'idle':
                self.log.error('CounterLogic still busy. '
                               'Unable to start fluorescence magnet alignment.')
                return True
        elif self._alignment_method == 'odmr_frequency':
            if self.odmrlogic().module_state() != 'idle':
                self.log.error('OdmrLogic still busy. Unable to start ODMR magnet alignment.')
                return True
        elif self._alignment_method == 'odmr_contrast':
            if self.odmrlogic().module_state() != 'idle':
                self.log.error('OdmrLogic still busy. Unable to start ODMR magnet alignment.')
                return True
        else:
            self.log.error('Alignment method "{0}" present in available_alignment_methods but not '
                           'handled in _check_measurement_start_conditions.'
                           ''.format(self._alignment_method))
            return True
        return False

    def stop_measurement(self):
        with self._thread_lock:
            if self.module_state() != 'locked':
                self.log.error('Unable to stop measurement. No measurement running.')
                return

            self._stop_requested = True
        return

    @QtCore.Slot()
    def _measurement_loop(self):
        if self.module_state() != 'locked':
            return

        with self._thread_lock:
            # Stop if requested
            if self._stop_requested:
                self._measurement_paused = False
                self.sigMeasurementStatusUpdated.emit(False, False)
                self.module_state.unlock()
                return

            path_pos = self._2d_path[self._2d_path_index]
            magnet_pos = self.move_magnet_abs(path_pos)
            self.sigMagnetPositionUpdated.emit(magnet_pos)

            self._optimize_position()

            self._2d_data[self._2d_path_index] = np.array((path_pos[self.align_2d_axis0_name[0]],
                                                           path_pos[self.align_2d_axis0_name[0]],
                                                           self.measure_alignment()), dtype=float)
            self.sig2dDataUpdated.emit(self._2d_data)

            self._2d_path_index += 1
            if self._2d_path_index == len(self._2d_path):
                self._stop_requested = True
        self._sigMeasurementLoop.emit()
        return

    def _optimize_position(self):
        if self.optimizerlogic().module_state() != 'idle':
            return

        curr_pos = self.scannerlogic().get_position()
        self.optimizerlogic().start_refocus(curr_pos, caller_tag='magnet_logic')

        # check just the state of the optimizer
        while self.optimizerlogic().module_state() != 'idle':
            if self._stop_requested:
                return
            time.sleep(0.5)

        # use the position to move the scanner
        self.scannerlogic().set_position('magnet_logic',
                                         self._optimizer_logic.optim_pos_x,
                                         self._optimizer_logic.optim_pos_y,
                                         self._optimizer_logic.optim_pos_z)
        return

    def measure_alignment(self):
        """ That is the main method which contains all functions with measurement routines.

        Each measurement routine has to output the measurement value, but can
        also provide a dictionary with additional measurement parameters, which
        have been measured either as a pre-requisition for the measurement or
        are results of the measurement.

        Save each measured value as an item to a keyword string, i.e.
            {'ODMR frequency (MHz)': <the_parameter>, ...}
        The save routine will handle the additional information and save them
        properly.


        @return tuple(float, dict): the measured value is of type float and the
                                    additional parameters are saved in a
                                    dictionary form.
        """
        if self._alignment_method == 'fluorescence':
            data = self._measure_fluorescence()
        elif self._alignment_method == 'odmr_frequency':
            data = self._measure_odmr_frequency()
        elif self._alignment_method == 'odmr_contrast':
            data = self._measure_odmr_contrast()
        else:
            self.log.error('Unknown alignment method "{0}".'.format(self._alignment_method))
            data = np.nan
        return data

    def _measure_fluorescence(self):
        """

        @return float:
        """
        if self.counterlogic().get_counting_mode() != CountingMode.CONTINUOUS:
            self.counterlogic().set_counting_mode(mode=CountingMode.CONTINUOUS)

        self.counterlogic().start_saving()
        time.sleep(self._fluorescence_alignment.measurement_time)
        data_array, dummy = self.counterlogic().save_data(to_file=False)
        if self._fluorescence_alignment.save_after_measure:
            self.counterlogic().save_data()

        data_array = np.array(data_array)[:, 1]
        return data_array.mean()

    def _measure_odmr_frequency(self):
        """ Perform the odmr measurement.

        @return:
        """

        store_dict = {}

        # optimize at first the position:
        self._do_optimize_pos()

        # correct the ODMR alignment the shift of the ODMR lines due to movement
        # in axis0 and axis1, therefore find out how much you will move in each
        # distance:
        if self._pathway_index == 0:
            axis0_pos_start = self._saved_pos_before_align[self._axis0_name]
            axis0_pos_stop = self._backmap[self._pathway_index][self._axis0_name]

            axis1_pos_start = self._saved_pos_before_align[self._axis1_name]
            axis1_pos_stop = self._backmap[self._pathway_index][self._axis1_name]
        else:
            axis0_pos_start = self._backmap[self._pathway_index - 1][self._axis0_name]
            axis0_pos_stop = self._backmap[self._pathway_index][self._axis0_name]

            axis1_pos_start = self._backmap[self._pathway_index - 1][self._axis1_name]
            axis1_pos_stop = self._backmap[self._pathway_index][self._axis1_name]

        # that is the current distance the magnet has moved:
        axis0_move = axis0_pos_stop - axis0_pos_start
        axis1_move = axis1_pos_stop - axis1_pos_start
        print('axis0_move', axis0_move, 'axis1_move', axis1_move)

        # in essence, get the last measurement value for odmr freq and calculate
        # the odmr peak shift for axis0 and axis1 based on the already measured
        # peaks and update the values odmr_2d_peak_axis0_move_ratio and
        # odmr_2d_peak_axis1_move_ratio:
        if self._pathway_index > 1:
            # in essence, get the last measurement value for odmr freq:
            if self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']].get(
                    'low_freq_Frequency') is not None:
                low_odmr_freq1 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']]['low_freq_Frequency'][
                    'value'] * 1e6
                low_odmr_freq2 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 2]['index']]['low_freq_Frequency'][
                    'value'] * 1e6
            elif self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']].get(
                    'low_freq_Freq. 1') is not None:
                low_odmr_freq1 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']]['low_freq_Freq. 1'][
                    'value'] * 1e6
                low_odmr_freq2 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 2]['index']]['low_freq_Freq. 1'][
                    'value'] * 1e6
            else:
                self.log.error('No previous saved lower odmr freq found in '
                               'ODMR alignment data! Cannot do the ODMR Alignment!')

            if self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']].get(
                    'high_freq_Frequency') is not None:
                high_odmr_freq1 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']]['high_freq_Frequency'][
                    'value'] * 1e6
                high_odmr_freq2 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 2]['index']]['high_freq_Frequency'][
                    'value'] * 1e6
            elif self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']].get(
                    'high_freq_Freq. 1') is not None:
                high_odmr_freq1 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']]['high_freq_Freq. 1'][
                    'value'] * 1e6
                high_odmr_freq2 = \
                self._2D_add_data_matrix[self._backmap[self._pathway_index - 2]['index']]['high_freq_Freq. 1'][
                    'value'] * 1e6
            else:
                self.log.error('No previous saved higher odmr freq found in '
                               'ODMR alignment data! Cannot do the ODMR Alignment!')

            # only if there was a non zero movement, the if make sense to
            # calculate the shift for either the axis0 or axis1.
            # BE AWARE THAT FOR A MOVEMENT IN AXIS0 AND AXIS1 AT THE SAME TIME
            # NO PROPER CALCULATION OF THE OMDR LINES CAN BE PROVIDED!
            if not np.isclose(axis0_move, 0.0):
                # update the correction ratio:
                low_peak_axis0_move_ratio = (low_odmr_freq1 - low_odmr_freq2) / axis0_move
                high_peak_axis0_move_ratio = (high_odmr_freq1 - high_odmr_freq2) / axis0_move

                # print('low_odmr_freq2', low_odmr_freq2, 'low_odmr_freq1', low_odmr_freq1)
                # print('high_odmr_freq2', high_odmr_freq2, 'high_odmr_freq1', high_odmr_freq1)

                # calculate the average shift of the odmr lines for the lower
                # and the upper transition:
                self.odmr_2d_peak_axis0_move_ratio = (low_peak_axis0_move_ratio + high_peak_axis0_move_ratio) / 2

                # print('new odmr_2d_peak_axis0_move_ratio', self.odmr_2d_peak_axis0_move_ratio/1e12)
            if not np.isclose(axis1_move, 0.0):
                # update the correction ratio:
                low_peak_axis1_move_ratio = (low_odmr_freq1 - low_odmr_freq2) / axis1_move
                high_peak_axis1_move_ratio = (high_odmr_freq1 - high_odmr_freq2) / axis1_move

                # calculate the average shift of the odmr lines for the lower
                # and the upper transition:
                self.odmr_2d_peak_axis1_move_ratio = (low_peak_axis1_move_ratio + high_peak_axis1_move_ratio) / 2

                # print('new odmr_2d_peak_axis1_move_ratio', self.odmr_2d_peak_axis1_move_ratio/1e12)

        # Measurement of the lower transition:
        # -------------------------------------

        freq_shift_low_axis0 = axis0_move * self.odmr_2d_peak_axis0_move_ratio
        freq_shift_low_axis1 = axis1_move * self.odmr_2d_peak_axis1_move_ratio

        # correct here the center freq with the estimated corrections:
        self.odmr_2d_low_center_freq += (freq_shift_low_axis0 + freq_shift_low_axis1)
        # print('self.odmr_2d_low_center_freq',self.odmr_2d_low_center_freq)

        # create a unique nametag for the current measurement:
        name_tag = 'low_trans_index_' + str(self._backmap[self._pathway_index]['index'][0]) \
                   + '_' + str(self._backmap[self._pathway_index]['index'][1])

        # of course the shift of the ODMR peak is not linear for a movement in
        # axis0 and axis1, but we need just an estimate how to set the boundary
        # conditions for the first scan, since the first scan will move to a
        # start position and then it need to know where to search for the ODMR
        # peak(s).

        # calculate the parameters for the odmr scan:
        low_start_freq = self.odmr_2d_low_center_freq - self.odmr_2d_low_range_freq / 2
        low_step_freq = self.odmr_2d_low_step_freq
        low_stop_freq = self.odmr_2d_low_center_freq + self.odmr_2d_low_range_freq / 2

        param = self._odmr_logic.perform_odmr_measurement(low_start_freq,
                                                          low_step_freq,
                                                          low_stop_freq,
                                                          self.odmr_2d_low_power,
                                                          self.odmr_2d_low_runtime,
                                                          self.odmr_2d_low_fitfunction,
                                                          self.odmr_2d_save_after_measure,
                                                          name_tag)

        # restructure the output parameters:
        for entry in param:
            store_dict['low_freq_' + str(entry)] = param[entry]

        # extract the frequency meausure:
        if param.get('Frequency') is not None:
            odmr_low_freq_meas = param['Frequency']['value'] * 1e6
        elif param.get('Freq. 1') is not None:
            odmr_low_freq_meas = param['Freq. 1']['value'] * 1e6
        else:
            # a default value for testing and debugging:
            odmr_low_freq_meas = 1000e6

        self.odmr_2d_low_center_freq = odmr_low_freq_meas
        # Measurement of the higher transition:
        # -------------------------------------


        freq_shift_high_axis0 = axis0_move * self.odmr_2d_peak_axis0_move_ratio
        freq_shift_high_axis1 = axis1_move * self.odmr_2d_peak_axis1_move_ratio

        # correct here the center freq with the estimated corrections:
        self.odmr_2d_high_center_freq += (freq_shift_high_axis0 + freq_shift_high_axis1)

        # create a unique nametag for the current measurement:
        name_tag = 'high_trans_index_' + str(self._backmap[self._pathway_index]['index'][0]) \
                   + '_' + str(self._backmap[self._pathway_index]['index'][1])

        # of course the shift of the ODMR peak is not linear for a movement in
        # axis0 and axis1, but we need just an estimate how to set the boundary
        # conditions for the first scan, since the first scan will move to a
        # start position and then it need to know where to search for the ODMR
        # peak(s).

        # calculate the parameters for the odmr scan:
        high_start_freq = self.odmr_2d_high_center_freq - self.odmr_2d_high_range_freq / 2
        high_step_freq = self.odmr_2d_high_step_freq
        high_stop_freq = self.odmr_2d_high_center_freq + self.odmr_2d_high_range_freq / 2

        param = self._odmr_logic.perform_odmr_measurement(high_start_freq,
                                                          high_step_freq,
                                                          high_stop_freq,
                                                          self.odmr_2d_high_power,
                                                          self.odmr_2d_high_runtime,
                                                          self.odmr_2d_high_fitfunction,
                                                          self.odmr_2d_save_after_measure,
                                                          name_tag)
        # restructure the output parameters:
        for entry in param:
            store_dict['high_freq_' + str(entry)] = param[entry]

        # extract the frequency meausure:
        if param.get('Frequency') is not None:
            odmr_high_freq_meas = param['Frequency']['value'] * 1e6
        elif param.get('Freq. 1') is not None:
            odmr_high_freq_meas = param['Freq. 1']['value'] * 1e6
        else:
            # a default value for testing and debugging:
            odmr_high_freq_meas = 2000e6

        # correct the estimated center frequency by the actual measured one.
        self.odmr_2d_high_center_freq = odmr_high_freq_meas

        # FIXME: the normalization is just done for the display to view the
        #       value properly! There is right now a bug in the colorbad
        #       display, which need to be solved.
        diff = (abs(odmr_high_freq_meas - odmr_low_freq_meas) / 2) / self.norm

        while self._odmr_logic.module_state() != 'idle' and not self._stop_measure:
            time.sleep(0.5)

        return diff, store_dict

    def _measure_odmr_contrast(self):
        """ Make an ODMR measurement on one single transition and use the
            contrast as a measure.
        """

        store_dict = {}

        # optimize at first the position:
        self._do_optimize_pos()

        # correct the ODMR alignment the shift of the ODMR lines due to movement
        # in axis0 and axis1, therefore find out how much you will move in each
        # distance:
        if self._pathway_index == 0:
            axis0_pos_start = self._saved_pos_before_align[self._axis0_name]
            axis0_pos_stop = self._backmap[self._pathway_index][self._axis0_name]

            axis1_pos_start = self._saved_pos_before_align[self._axis1_name]
            axis1_pos_stop = self._backmap[self._pathway_index][self._axis1_name]
        else:
            axis0_pos_start = self._backmap[self._pathway_index - 1][self._axis0_name]
            axis0_pos_stop = self._backmap[self._pathway_index][self._axis0_name]

            axis1_pos_start = self._backmap[self._pathway_index - 1][self._axis1_name]
            axis1_pos_stop = self._backmap[self._pathway_index][self._axis1_name]

        # that is the current distance the magnet has moved:
        axis0_move = axis0_pos_stop - axis0_pos_start
        axis1_move = axis1_pos_stop - axis1_pos_start
        # print('axis0_move', axis0_move, 'axis1_move', axis1_move)

        # in essence, get the last measurement value for odmr freq and calculate
        # the odmr peak shift for axis0 and axis1 based on the already measured
        # peaks and update the values odmr_2d_peak_axis0_move_ratio and
        # odmr_2d_peak_axis1_move_ratio:
        if self._pathway_index > 1:
            # in essence, get the last measurement value for odmr freq:
            if self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']].get('Frequency') is not None:
                odmr_freq1 = self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']]['Frequency'][
                                 'value'] * 1e6
                odmr_freq2 = self._2D_add_data_matrix[self._backmap[self._pathway_index - 2]['index']]['Frequency'][
                                 'value'] * 1e6
            elif self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']].get('Freq. 1') is not None:
                odmr_freq1 = self._2D_add_data_matrix[self._backmap[self._pathway_index - 1]['index']]['Freq. 1'][
                                 'value'] * 1e6
                odmr_freq2 = self._2D_add_data_matrix[self._backmap[self._pathway_index - 2]['index']]['Freq. 1'][
                                 'value'] * 1e6
            else:
                self.log.error('No previous saved lower odmr freq found in '
                               'ODMR alignment data! Cannot do the ODMR '
                               'Alignment!')

            # only if there was a non zero movement, the if make sense to
            # calculate the shift for either the axis0 or axis1.
            # BE AWARE THAT FOR A MOVEMENT IN AXIS0 AND AXIS1 AT THE SAME TIME
            # NO PROPER CALCULATION OF THE OMDR LINES CAN BE PROVIDED!
            if not np.isclose(axis0_move, 0.0):
                # update the correction ratio:
                peak_axis0_move_ratio = (odmr_freq1 - odmr_freq2) / axis0_move

                # calculate the average shift of the odmr lines for the lower
                # and the upper transition:
                self.odmr_2d_peak_axis0_move_ratio = peak_axis0_move_ratio

                print('new odmr_2d_peak_axis0_move_ratio', self.odmr_2d_peak_axis0_move_ratio / 1e12)
            if not np.isclose(axis1_move, 0.0):
                # update the correction ratio:
                peak_axis1_move_ratio = (odmr_freq1 - odmr_freq2) / axis1_move

                # calculate the shift of the odmr lines for the transition:
                self.odmr_2d_peak_axis1_move_ratio = peak_axis1_move_ratio

        # Measurement of one transition:
        # -------------------------------------

        freq_shift_axis0 = axis0_move * self.odmr_2d_peak_axis0_move_ratio
        freq_shift_axis1 = axis1_move * self.odmr_2d_peak_axis1_move_ratio

        # correct here the center freq with the estimated corrections:
        self.odmr_2d_low_center_freq += (freq_shift_axis0 + freq_shift_axis1)
        # print('self.odmr_2d_low_center_freq',self.odmr_2d_low_center_freq)

        # create a unique nametag for the current measurement:
        name_tag = 'trans_index_' + str(self._backmap[self._pathway_index]['index'][0]) \
                   + '_' + str(self._backmap[self._pathway_index]['index'][1])

        # of course the shift of the ODMR peak is not linear for a movement in
        # axis0 and axis1, but we need just an estimate how to set the boundary
        # conditions for the first scan, since the first scan will move to a
        # start position and then it need to know where to search for the ODMR
        # peak(s).

        # calculate the parameters for the odmr scan:
        start_freq = self.odmr_2d_low_center_freq - self.odmr_2d_low_range_freq / 2
        step_freq = self.odmr_2d_low_step_freq
        stop_freq = self.odmr_2d_low_center_freq + self.odmr_2d_low_range_freq / 2

        param = self._odmr_logic.perform_odmr_measurement(start_freq,
                                                          step_freq,
                                                          stop_freq,
                                                          self.odmr_2d_low_power,
                                                          self.odmr_2d_low_runtime,
                                                          self.odmr_2d_low_fitfunction,
                                                          self.odmr_2d_save_after_measure,
                                                          name_tag)

        param['ODMR peak/Magnet move ratio axis0'] = self.odmr_2d_peak_axis0_move_ratio
        param['ODMR peak/Magnet move ratio axis1'] = self.odmr_2d_peak_axis1_move_ratio

        # extract the frequency meausure:
        if param.get('Frequency') is not None:
            odmr_freq_meas = param['Frequency']['value'] * 1e6
            cont_meas = param['Contrast']['value']
        elif param.get('Freq. 1') is not None:
            odmr_freq_meas = param['Freq. 1']['value'] * 1e6
            cont_meas = param['Contrast 0']['value'] + param['Contrast 1']['value'] + param['Contrast 2']['value']
        else:
            # a default value for testing and debugging:
            odmr_freq_meas = 1000e6
            cont_meas = 0.0

        self.odmr_2d_low_center_freq = odmr_freq_meas

        while self._odmr_logic.module_state() != 'idle' and not self._stop_measure:
            time.sleep(0.5)

        return cont_meas, param

    def save_2d_data(self, tag=None, timestamp=None):
        """ Save the data of the  """

        filepath = self._save_logic.get_path_for_module(module_name='Magnet')

        if timestamp is None:
            timestamp = datetime.datetime.now()

        # if tag is not None and len(tag) > 0:
        #     filelabel = tag + '_magnet_alignment_data'
        #     filelabel2 = tag + '_magnet_alignment_add_data'
        # else:
        #     filelabel = 'magnet_alignment_data'
        #     filelabel2 = 'magnet_alignment_add_data'

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_magnet_alignment_data'
            filelabel2 = tag + '_magnet_alignment_add_data'
            filelabel3 = tag + '_magnet_alignment_data_table'
            filelabel4 = tag + '_intended_field_values'
            filelabel5 = tag + '_reached_field_values'
            filelabel6 = tag + '_error_in_field'
        else:
            filelabel = 'magnet_alignment_data'
            filelabel2 = 'magnet_alignment_add_data'
            filelabel3 = 'magnet_alignment_data_table'
            filelabel4 = 'intended_field_values'
            filelabel5 = 'reached_field_values'
            filelabel6 = 'error_in_field'

        # prepare the data in a dict or in an OrderedDict:

        # here is the matrix saved
        matrix_data = OrderedDict()

        # here are all the parameters, which are saved for a certain matrix
        # entry, mainly coming from all the other logic modules except the magnet logic:
        add_matrix_data = OrderedDict()

        # here are all supplementary information about the measurement, mainly
        # from the magnet logic
        supplementary_data = OrderedDict()

        axes_names = list(self._saved_pos_before_align)

        matrix_data['Alignment Matrix'] = self._2D_data_matrix

        parameters = OrderedDict()
        parameters['Measurement start time'] = self._start_measurement_time
        if self._stop_measurement_time is not None:
            parameters['Measurement stop time'] = self._stop_measurement_time
        parameters['Time at Data save'] = timestamp
        parameters['Pathway of the magnet alignment'] = 'Snake-wise steps'

        for index, entry in enumerate(self._pathway):
            parameters['index_' + str(index)] = entry

        parameters['Backmap of the magnet alignment'] = 'Index wise display'

        for entry in self._backmap:
            parameters['related_intex_' + str(entry)] = self._backmap[entry]

        self._save_logic.save_data(matrix_data, filepath=filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp)

        self.log.debug('Magnet 2D data saved to:\n{0}'.format(filepath))

        # prepare the data in a dict or in an OrderedDict:
        add_data = OrderedDict()
        axis0_data = np.zeros(len(self._backmap))
        axis1_data = np.zeros(len(self._backmap))
        param_data = np.zeros(len(self._backmap), dtype='object')

        for backmap_index in self._backmap:
            axis0_data[backmap_index] = self._backmap[backmap_index][self._axis0_name]
            axis1_data[backmap_index] = self._backmap[backmap_index][self._axis1_name]
            param_data[backmap_index] = str(self._2D_add_data_matrix[self._backmap[backmap_index]['index']])

        constr = self.get_hardware_constraints()
        units_axis0 = constr[self._axis0_name]['unit']
        units_axis1 = constr[self._axis1_name]['unit']

        add_data['{0} values ({1})'.format(self._axis0_name, units_axis0)] = axis0_data
        add_data['{0} values ({1})'.format(self._axis1_name, units_axis1)] = axis1_data
        add_data['all measured additional parameter'] = param_data

        self._save_logic.save_data(add_data, filepath=filepath, filelabel=filelabel2,
                                   timestamp=timestamp)
        # save the data table

        count_data = self._2D_data_matrix
        x_val = self._2D_axis0_data
        y_val = self._2D_axis1_data
        save_dict = OrderedDict()
        axis0_key = '{0} values ({1})'.format(self._axis0_name, units_axis0)
        axis1_key = '{0} values ({1})'.format(self._axis1_name, units_axis1)
        counts_key = 'counts (c/s)'
        save_dict[axis0_key] = []
        save_dict[axis1_key] = []
        save_dict[counts_key] = []

        for ii, columns in enumerate(count_data):
            for jj, col_counts in enumerate(columns):
                # x_list = [x_val[ii]] * len(countlist)
                save_dict[axis0_key].append(x_val[ii])
                save_dict[axis1_key].append(y_val[jj])
                save_dict[counts_key].append(col_counts)
        save_dict[axis0_key] = np.array(save_dict[axis0_key])
        save_dict[axis1_key] = np.array(save_dict[axis1_key])
        save_dict[counts_key] = np.array(save_dict[counts_key])

        # making saveable dictionaries

        self._save_logic.save_data(save_dict, filepath=filepath, filelabel=filelabel3,
                                   timestamp=timestamp, fmt='%.6e')
        keys = self._2d_intended_fields[0].keys()
        intended_fields = OrderedDict()
        for key in keys:
            field_values = [coord_dict[key] for coord_dict in self._2d_intended_fields]
            intended_fields[key] = field_values

        self._save_logic.save_data(intended_fields, filepath=filepath, filelabel=filelabel4,
                                   timestamp=timestamp)

        measured_fields = OrderedDict()
        for key in keys:
            field_values = [coord_dict[key] for coord_dict in self._2d_measured_fields]
            measured_fields[key] = field_values

        self._save_logic.save_data(measured_fields, filepath=filepath, filelabel=filelabel5,
                                   timestamp=timestamp)

        error = OrderedDict()
        error['quadratic error'] = self._2d_error

        self._save_logic.save_data(error, filepath=filepath, filelabel=filelabel6,
                                   timestamp=timestamp)
