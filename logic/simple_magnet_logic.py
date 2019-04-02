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

from scipy.constants import physical_constants
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

    def __init__(self, low_freq_range=(2.6e9, 2.8e9), high_freq_range=(2.94e9, 3.14e9),
                 low_power=-10, high_power=-8, low_points=50, high_points=50,
                 fit_name='Lorentzian dip', low_result_param='', high_result_param='', **kwargs):
        super().__init__(**kwargs)
        self.low_freq_range = (float(min(low_freq_range)), float(max(low_freq_range)))
        self.high_freq_range = (float(min(high_freq_range)), float(max(high_freq_range)))
        self.low_power = float(low_power)
        self.high_power = float(high_power)
        self.low_points = int(low_points)
        self.high_points = int(high_points)
        self.fit_name = str(fit_name)
        self.low_result_param = str(low_result_param)
        self.high_result_param = str(high_result_param)
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

    @_odmr_frequency_alignment.representer
    @_odmr_contrast_alignment.representer
    @_fluorescence_alignment.representer
    def parameters_to_dict(self, param_class_inst):
        return param_class_inst.parameters

    @_fluorescence_alignment.constructor
    def dict_to_parameters(self, param_dict):
        return FluorescenceAlignment(**param_dict)

    @_odmr_contrast_alignment.constructor
    def dict_to_parameters(self, param_dict):
        return OdmrContrastAlignment(**param_dict)

    @_odmr_frequency_alignment.constructor
    def dict_to_parameters(self, param_dict):
        return OdmrFrequencyAlignment(**param_dict)

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

    def set_general_parameters(self, param_dict):
        for param, value in param_dict.items():
            setattr(self._fluorescence_alignment, param, value)
            setattr(self._odmr_frequency_alignment, param, value)
            setattr(self._odmr_contrast_alignment, param, value)
        return

    def set_odmr_frequency_parameters(self, param_dict):
        for param, value in param_dict.items():
            setattr(self._odmr_frequency_alignment, param, value)
        return

    def set_odmr_contrast_parameters(self, param_dict):
        for param, value in param_dict.items():
            setattr(self._odmr_contrast_alignment, param, value)
        return

    def set_alignment_method(self, method):
        if method not in self.available_alignment_methods:
            self.log.error('Unknwon alignment method "{0}".'.format(method))
            return
        self._alignment_method = method
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
                                                           path_pos[self.align_2d_axis0_name[1]],
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
        """

        @return float:
        """
        params = self._odmr_frequency_alignment
        curr_pos = self._2d_path[self._2d_path_index]

        # Measure low frequency
        # Set up measurement in OdmrLogic
        step = (params.low_freq_range[1] - params.low_freq_range[0]) / (params.low_points - 1)
        self.odmrlogic().set_sweep_parameters(start=params.low_freq_range[0],
                                              stop=params.low_freq_range[1],
                                              step=step,
                                              power=params.low_power)
        self.odmrlogic().set_runtime(runtime=params.measurement_time)
        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(0.5)
        self.odmrlogic().do_fit(params.fit_name)
        low_freq = self.odmrlogic().fc.current_fit_param[params.low_result_param].value
        if params.save_after_measure:
            tag = 'magnetalign_{0:.3e}_{1:.3e}_low'.format(curr_pos[self.align_2d_axis0_name[0]],
                                                            curr_pos[self.align_2d_axis0_name[1]])
            self.odmrlogic().save_odmr_data(tag=tag)
        self.odmrlogic().do_fit('No Fit')

        # Adjust center frequency for next measurement
        freq_shift = low_freq - (params.low_frequ_range[0] + params.low_freq_range[1]) / 2
        self._odmr_frequency_alignment.low_freq_range = (params.low_freq_range[0] + freq_shift,
                                                         params.low_freq_range[1] + freq_shift)

        # Measure high frequency
        # Set up measurement in OdmrLogic
        step = (params.high_freq_range[1] - params.high_freq_range[0]) / (params.high_points - 1)
        self.odmrlogic().set_sweep_parameters(start=params.high_freq_range[0],
                                              stop=params.high_freq_range[1],
                                              step=step,
                                              power=params.high_power)
        self.odmrlogic().set_runtime(runtime=params.measurement_time)
        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(0.5)
        self.odmrlogic().do_fit(params.fit_name)
        high_freq = self.odmrlogic().fc.current_fit_param[params.high_result_param].value
        if params.save_after_measure:
            tag = 'magnetalign_{0:.3e}_{1:.3e}_high'.format(curr_pos[self.align_2d_axis0_name[0]],
                                                            curr_pos[self.align_2d_axis0_name[1]])
            self.odmrlogic().save_odmr_data(tag=tag)
        self.odmrlogic().do_fit('No Fit')

        # Adjust center frequency for next measurement
        freq_shift = high_freq - (params.high_freq_range[0] + params.high_freq_range[1]) / 2
        self._odmr_frequency_alignment.high_freq_range = (params.high_freq_range[0] + freq_shift,
                                                          params.high_freq_range[1] + freq_shift)

        # Calculate the magnetic field strength and the angle to the quantization axis.
        b_field, angle = self.calculate_field_alignment(low_freq, high_freq)
        if np.isnan(angle):
            self.log.warning('NaN value encountered during odmr frequency alignment at position '
                             '{0}={1:.3e}, {2}={3:.3e}.\nB-field angle returned set to zero.\n'
                             'B={4:.3e}G, angle={5:.3e}°'
                             ''.format(self.align_2d_axis0_name[0],
                                       curr_pos[self.align_2d_axis0_name[0]],
                                       self.align_2d_axis0_name[1],
                                       curr_pos[self.align_2d_axis0_name[1]], b_field, angle))
            angle = 0.0
        return angle

    def _measure_odmr_contrast(self):
        """

        @return float:
        """
        params = self._odmr_contrast_alignment
        curr_pos = self._2d_path[self._2d_path_index]

        # Set up measurement in OdmrLogic
        step = (params.freq_range[1] - params.freq_range[0]) / (params.points - 1)
        self.odmrlogic().set_sweep_parameters(start=params.freq_range[0],
                                              stop=params.freq_range[1],
                                              step=step,
                                              power=params.power)
        self.odmrlogic().set_runtime(runtime=params.measurement_time)
        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(0.5)
        self.odmrlogic().do_fit(params.fit_name)
        odmr_freq = self.odmrlogic().fc.current_fit_param['center'].value
        odmr_contrast = self.odmrlogic().fc.current_fit_param[params.result_param].value
        if params.save_after_measure:
            tag = 'magnetalign_{0:.3e}_{1:.3e}'.format(curr_pos[self.align_2d_axis0_name[0]],
                                                       curr_pos[self.align_2d_axis0_name[1]])
            self.odmrlogic().save_odmr_data(tag=tag)
        self.odmrlogic().do_fit('No Fit')

        # Adjust center frequency for next measurement
        freq_shift = odmr_freq - (params.freq_range[0] + params.freq_range[1]) / 2
        self._odmr_contrast_alignment.freq_range = (params.freq_range[0] + freq_shift,
                                                    params.freq_range[1] + freq_shift)
        return odmr_contrast

    def save_2d_data(self, tag=None, timestamp=None):
        """ Save the data of the """
        filepath = self._save_logic.get_path_for_module(module_name='Magnet')

        if timestamp is None:
            timestamp = datetime.datetime.now()
        filelabel = tag + '_magnet_alignment_data' if tag else 'magnet_alignment_data'

        # here is the matrix saved
        if self._alignment_method == 'fluorescence':
            data_header = '{0}(m)\t{1}(m)\tcounts(1/s)'.format(self._align_2d_axis_names[0],
                                                               self._align_2d_axis_names[1])
        elif self._alignment_method == 'odmr_frequency':
            data_header = '{0}(m)\t{1}(m)\tangle(deg)'.format(self._align_2d_axis_names[0],
                                                              self._align_2d_axis_names[1])
        elif self._alignment_method == 'odmr_frequency':
            data_header = '{0}(m)\t{1}(m)\tcontrast'.format(self._align_2d_axis_names[0],
                                                            self._align_2d_axis_names[1])
        else:
            data_header = '{0}(m)\t{1}(m)\tvalue'.format(self._align_2d_axis_names[0],
                                                         self._align_2d_axis_names[1])
        matrix_data = {data_header: self._2d_data}

        parameters = OrderedDict()
        parameters['Pathway method'] = self._align_2d_pathway_mode
        parameters['Alignment method'] = self._alignment_method

        self._save_logic.save_data(matrix_data, filepath=filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp)

    @staticmethod
    def calculate_field_alignment(freq1, freq2):
        """

        @param float freq1: ms=-1 transition frequency in Hz
        @param float freq2: ms=+1 transition frequency in Hz
        @return (float, float): Field strength in Gauss, angle to quantization axis in deg
        """
        # Convert to MHz
        freq1 /= 1e6
        freq2 /= 1e6

        D_zerofield = 2870.
        zeroField_E = 0.

        delta = ((7 * D_zerofield ** 3 + 2 * (freq1 + freq2) * (2 * (
                    freq1 ** 2 + freq2 ** 2) - 5 * freq1 * freq2 - 9 * zeroField_E ** 2) - 3 * D_zerofield * (
                              freq1 ** 2 + freq2 ** 2 - freq1 * freq2 + 9 * zeroField_E ** 2)) / (
                             9 * (
                                 freq1 ** 2 + freq2 ** 2 - freq1 * freq2 - D_zerofield ** 2 - 3 * zeroField_E ** 2)))

        angle = np.arccos(delta / D_zerofield - 1e-9) / 2. / np.pi * 180.
        beta = np.sqrt(
            (freq1 ** 2 + freq2 ** 2 - freq1 * freq2 - D_zerofield ** 2) / 3. - zeroField_E ** 2.)

        b_field = beta / physical_constants['Bohr magneton in Hz/T'][0] / (
                    -1 * physical_constants['electron g factor'][0]) * 1e10

        print('Estimated magnetic field B: %.1f Gauss with an angle of %.2f degree.' % (b_field, angle))
        return b_field, angle