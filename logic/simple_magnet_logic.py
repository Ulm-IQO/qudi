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


class AlignmentParameters:
    """

    """
    parameters = dict()

    def to_dict(self):
        param_dict = self.__dict__.copy()
        for key in self.__dict__:
            if key not in self.parameters:
                del param_dict[key]
        return param_dict


class OdmrFrequencyAlignmentParameters(AlignmentParameters):
    """

    """

    parameters = dict()
    parameters['low_start_freq'] = {'unit': 'Hz', 'default': 2.6e9, 'min': 0, 'max': np.inf,
                                    'type': float}
    parameters['low_stop_freq'] = {'unit': 'Hz', 'default': 2.8e9, 'min': 0, 'max': np.inf,
                                   'type': float}
    parameters['low_power'] = {'unit': 'dBm', 'default': -30, 'min': -np.inf, 'max': np.inf,
                               'type': float}
    parameters['low_points'] = {'unit': '', 'default': 50, 'min': 3, 'max': np.inf, 'type': int}
    parameters['high_start_freq'] = {'unit': 'Hz', 'default': 2.94e9, 'min': 0, 'max': np.inf,
                                     'type': float}
    parameters['high_stop_freq'] = {'unit': 'Hz', 'default': 3.14e9, 'min': 0, 'max': np.inf,
                                    'type': float}
    parameters['high_power'] = {'unit': 'dBm', 'default': -30, 'min': -np.inf, 'max': np.inf,
                                'type': float}
    parameters['high_points'] = {'unit': '', 'default': 50, 'min': 3, 'max': np.inf, 'type': int}

    def __init__(self, low_start_freq=None, low_stop_freq=None, low_power=None, low_points=None,
                 high_start_freq=None, high_stop_freq=None, high_power=None, high_points=None):
        super().__init__()
        if low_start_freq is None:
            self.low_start_freq = self.parameters['low_start_freq']['default']
        else:
            self.low_start_freq = float(low_start_freq)

        if low_stop_freq is None:
            self.low_stop_freq = self.parameters['low_stop_freq']['default']
        else:
            self.low_stop_freq = float(low_stop_freq)

        if low_power is None:
            self.low_power = self.parameters['low_power']['default']
        else:
            self.low_power = float(low_power)

        if low_points is None:
            self.low_points = self.parameters['low_points']['default']
        else:
            self.low_points = int(low_points)

        if high_start_freq is None:
            self.high_start_freq = self.parameters['high_start_freq']['default']
        else:
            self.high_start_freq = float(high_start_freq)

        if high_stop_freq is None:
            self.high_stop_freq = self.parameters['high_stop_freq']['default']
        else:
            self.high_stop_freq = float(high_stop_freq)

        if high_power is None:
            self.high_power = self.parameters['high_power']['default']
        else:
            self.high_power = float(high_power)

        if high_points is None:
            self.high_points = self.parameters['high_points']['default']
        else:
            self.high_points = int(high_points)
        return


class OdmrContrastAlignmentParameters(AlignmentParameters):
    """

    """

    parameters = dict()
    parameters['start_freq'] = {'unit': 'Hz', 'default': 2.77e9, 'min': 0, 'max': np.inf,
                                'type': float}
    parameters['stop_freq'] = {'unit': 'Hz', 'default': 2.97e9, 'min': 0, 'max': np.inf,
                               'type': float}
    parameters['power'] = {'unit': 'dBm', 'default': -30, 'min': -np.inf, 'max': np.inf,
                           'type': float}
    parameters['points'] = {'unit': '', 'default': 50, 'min': 3, 'max': np.inf, 'type': int}

    def __init__(self, start_freq=None, stop_freq=None, power=None, points=None):
        super().__init__()
        if start_freq is None:
            self.start_freq = self.parameters['start_freq']['default']
        else:
            self.start_freq = float(start_freq)

        if stop_freq is None:
            self.stop_freq = self.parameters['stop_freq']['default']
        else:
            self.stop_freq = float(stop_freq)

        if power is None:
            self.power = self.parameters['power']['default']
        else:
            self.power = float(power)

        if points is None:
            self.points = self.parameters['points']['default']
        else:
            self.points = int(points)
        return


class FluorescenceAlignmentParameters(AlignmentParameters):
    """

    """
    pass


class MagnetLogic(GenericLogic):
    """
    A general magnet logic to control an magnetic stage with an arbitrary set of axis.
    """

    _modclass = 'MagnetLogic'
    _modtype = 'logic'

    # Declare connectors
    magnetstage = Connector(interface='MagnetInterface')
    optimizerlogic = Connector(interface='OptimizerLogic')
    counterlogic = Connector(interface='CounterLogic')
    odmrlogic = Connector(interface='ODMRLogic')
    savelogic = Connector(interface='SaveLogic')
    scannerlogic = Connector(interface='ScannerLogic')

    # Declare status variables
    _align_axis_names = StatusVar(name='align_axis_names', default=list())
    _align_axis_ranges = StatusVar(name='align_axis_ranges', default=list())
    _align_axis_points = StatusVar(name='align_axis_points', default=list())
    _align_pathway_mode = StatusVar(name='align_pathway_mode', default='meander')
    _align_method = StatusVar(name='alignment_method', default='fluorescence')
    _align_measurement_time = StatusVar(name='alignment_measurement_time', default=10)
    _align_save_measurements = StatusVar(name='alignment_save_measurements', default=True)
    _align_data = StatusVar(name='alignment_data', default=None)

    _align_parameters = StatusVar(name='alignment_parameters', default=dict())

    # Declare signals
    sigAlignmentParametersUpdated = QtCore.Signal(str, dict)
    sigGeneralParametersUpdated = QtCore.Signal(dict)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sigDataUpdated = QtCore.Signal(np.ndarray, tuple)
    sigMagnetMoving = QtCore.Signal(bool)
    sigMagnetPositionUpdated = QtCore.Signal(dict)
    sigMagnetVelocityUpdated = QtCore.Signal(dict)

    _sigMeasurementLoop = QtCore.Signal()

    # Other class variables/constants
    _available_path_modes = ('meander', 'diagonal-meander', 'spiral-in', 'spiral-out')
    _available_alignment_methods = ('fluorescence', 'odmr_frequency', 'odmr_contrast')

    def __init__(self, config, **kwargs):
        """

        """
        super().__init__(config=config, **kwargs)
        self.thread_lock = Mutex()

        self._measurement_paused = False
        self._stop_requested = True
        self._pause_continue_requested = False
        self.__in_loop = False

        self._move_path = None
        self._path_index = 0
        return

    def on_activate(self):
        """
        Actions performed upon loading/activating this module go here.
        """
        self._measurement_paused = False
        self._stop_requested = True
        self._pause_continue_requested = False

        # Initialize undefined variables
        constr = self.magnet_constraints
        if not self._align_axis_names:
            self._align_axis_names = [self.available_axes_names[0], self.available_axes_names[1]]
        if not self._align_axis_ranges:
            self._align_axis_ranges = [(constr[self._align_axis_names[0]]['pos_min'],
                                        constr[self._align_axis_names[0]]['pos_max']),
                                       (constr[self._align_axis_names[1]]['pos_min'],
                                        constr[self._align_axis_names[1]]['pos_max'])]
        if not self._align_axis_points:
            self._align_axis_points = [10, 10]
        if self._align_method not in self.available_alignment_methods:
            self._align_method = self.available_alignment_methods[0]
        if self._align_pathway_mode not in self.available_path_modes:
            self._align_pathway_mode = self.available_path_modes[0]

        if self._align_data is None:
            self._align_data = np.zeros(self._align_axis_points, dtype=float)

        self._sigMeasurementLoop.connect(self._measurement_loop, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """
        Deactivate the module properly.
        """
        if self.module_state() == 'locked':
            self.stop_measurement()
            start = time.time()
            while self.module_state() != 'idle':
                time.sleep(0.5)
                if (time.time() - start) > self._align_measurement_time * 1.1:
                    break

        self._sigMeasurementLoop.disconnect()
        return

    @_align_parameters.representer
    def parameters_to_dict(self, param_dict):
        for method in param_dict:
            param_dict[method] = param_dict[method].to_dict()
        return param_dict

    @_align_parameters.constructor
    def dict_to_parameters(self, param_dict):
        for method in param_dict:
            if method not in self.available_alignment_methods:
                continue

            if method == 'fluorescence':
                param_dict[method] = FluorescenceAlignmentParameters(**param_dict[method])
            elif method == 'odmr_frequency':
                param_dict[method] = OdmrFrequencyAlignmentParameters(**param_dict[method])
            elif method == 'odmr_contrast':
                param_dict[method] = OdmrContrastAlignmentParameters(**param_dict[method])

        if 'fluorescence' not in param_dict:
            param_dict['fluorescence'] = FluorescenceAlignmentParameters()
        if 'odmr_frequency' not in param_dict:
            param_dict['odmr_frequency'] = OdmrFrequencyAlignmentParameters()
        if 'odmr_contrast' not in param_dict:
            param_dict['odmr_contrast'] = OdmrContrastAlignmentParameters()
        return param_dict

    @property
    def available_path_modes(self):
        return tuple(self._available_path_modes)

    @property
    def available_alignment_methods(self):
        return tuple(self._available_alignment_methods)

    @property
    def available_axes_names(self):
        return tuple(self.magnet_constraints)

    @property
    def align_path_mode(self):
        return self._align_pathway_mode

    @property
    def align_method(self):
        return self._align_method

    @property
    def align_axes_names(self):
        return tuple(self._align_axis_names)

    @property
    def align_ranges(self):
        return tuple(self._align_axis_ranges)

    @property
    def align_points(self):
        return tuple(self._align_axis_points)

    @property
    def align_data(self):
        return self._align_data

    @property
    def magnet_constraints(self):
        return self.magnetstage().get_constraints()

    @property
    def magnet_position(self):
        return self.magnetstage().get_pos()

    @property
    def magnet_velocity(self):
        return self.magnetstage().get_velocity()

    @property
    def magnet_status(self):
        return self.magnetstage().get_status()

    @property
    def alignment_parameters(self):
        return {method: param.to_dict() for method, param in self._align_parameters.items()}

    @property
    def alignment_parameter_signatures(self):
        return {method: param.parameters for method, param in self._align_parameters.items()}

    @property
    def is_paused(self):
        return self._measurement_paused

    @property
    def general_parameters(self):
        param_dict = dict()
        param_dict['axis_names'] = self._align_axis_names
        param_dict['axis_ranges'] = self._align_axis_ranges
        param_dict['axis_points'] = self._align_axis_points
        param_dict['pathway_mode'] = self._align_pathway_mode
        param_dict['alignment_method'] = self._align_method
        param_dict['measurement_time'] = self._align_measurement_time
        param_dict['save_measurements'] = self._align_save_measurements
        return param_dict

    @QtCore.Slot()
    def update_magnet_position(self):
        with self.thread_lock:
            self.sigMagnetPositionUpdated.emit(self.magnet_position)
        return

    @QtCore.Slot(dict)
    def set_general_parameters(self, param_dict):
        if self.module_state() != 'idle':
            self.sigGeneralParametersUpdated.emit(self.general_parameters)
            return

        if 'axis_names' in param_dict:
            self._align_axis_names = tuple(param_dict['axis_names'])
        if 'axis_ranges' in param_dict:
            self._align_axis_ranges = tuple(param_dict['axis_ranges'])
        if 'axis_points' in param_dict:
            self._align_axis_points = tuple(param_dict['axis_points'])
        if 'pathway_mode' in param_dict:
            if param_dict['pathway_mode'] in self.available_path_modes:
                self._align_pathway_mode = str(param_dict['pathway_mode'])
            else:
                self.log.error('Unknown alignment pathway mode "{0}"'
                               ''.format(param_dict['pathway_mode']))
        if 'alignment_method' in param_dict:
            if param_dict['alignment_method'] in self.available_alignment_methods:
                self._align_method = str(param_dict['alignment_method'])
            else:
                self.log.error('Unknown alignment method "{0}"'
                               ''.format(param_dict['alignment_method']))
        if 'measurement_time' in param_dict:
            self._align_measurement_time = float(param_dict['measurement_time'])
        if 'save_measurements' in param_dict:
            self._align_save_measurements = bool(param_dict['save_measurements'])

        self.sigGeneralParametersUpdated.emit(self.general_parameters)
        return

    @QtCore.Slot(str, dict)
    def set_alignment_parameters(self, method, param_dict):
        if self.module_state() != 'idle':
            self.sigAlignmentParametersUpdated.emit(method,
                                                    self._align_parameters[method].to_dict())
            return

        if method not in self.available_alignment_methods:
            self.log.error('Unknown alignment method "{0}"'.format(method))
            return

        for param, value in param_dict.items():
            if not hasattr(self._align_parameters[method], param):
                self.log.error('Unknown alignment parameter "{0}" for alignment method "{1}".'
                               ''.format(param, method))
            else:
                setattr(self._align_parameters[method], param, value)
        self.sigAlignmentParametersUpdated.emit(method, self._align_parameters[method].to_dict())
        return

    @QtCore.Slot(dict)
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
        self.sigMagnetMoving.emit(True)
        pos = self.magnetstage().move_rel(param_dict)
        self.sigMagnetPositionUpdated.emit(pos)
        self.sigMagnetMoving.emit(False)
        return pos

    @QtCore.Slot(dict)
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
        self.sigMagnetMoving.emit(True)
        pos = self.magnetstage().move_abs(param_dict)
        self.sigMagnetPositionUpdated.emit(pos)
        self.sigMagnetMoving.emit(False)
        return pos

    @QtCore.Slot()
    def abort_movement(self):
        """ Stops movement of the stage. """
        self.magnetstage().abort()
        self.sigMagnetMoving.emit(False)
        if self.module_state() == 'locked':
            self.stop_measurement()
        return

    @QtCore.Slot(dict)
    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        if self.module_state() != 'idle':
            self.log.error('Unable to change magnet velocity while measurement is running.')
            return
        with self.thread_lock:
            vel = self.magnetstage().set_velocity(param_dict)
        self.sigMagnetVelocityUpdated.emit(vel)
        return vel

    def _create_alignment_pathway(self):
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

        if self._align_pathway_mode not in self.available_path_modes:
            self.log.error('Unknown 2D alignment pathway mode.')
            return pathway

        # TODO: create all path modes
        if self._align_pathway_mode == 'meander':
            # create a meandering stepping procedure through the matrix
            # calculate coordinates for each axis
            x_values = np.linspace(self._align_axis_ranges[0][0],
                                   self._align_axis_ranges[0][1],
                                   self._align_axis_points[0],
                                   dtype=float)
            y_values = np.linspace(self._align_axis_ranges[1][0],
                                   self._align_axis_ranges[1][1],
                                   self._align_axis_points[1],
                                   dtype=float)
            for dim2_index, dim2_val in enumerate(y_values):
                if dim2_index % 2 == 0:
                    for dim1_index, dim1_val in enumerate(x_values):
                        pathway.append({'index': (dim1_index, dim2_index),
                                        'pos': {self._align_axis_names[0]: dim1_val,
                                                self._align_axis_names[1]: dim2_val}})
                else:
                    for dim1_rev_index, dim1_val in enumerate(reversed(x_values)):
                        dim1_index = len(x_values) - 1 - dim1_rev_index
                        pathway.append({'index': (dim1_index, dim2_index),
                                        'pos': {self._align_axis_names[0]: dim1_val,
                                                self._align_axis_names[1]: dim2_val}})
        else:
            self.log.error('2D alignment pathway method "{0}" not implemented yet.'
                           ''.format(self._align_pathway_mode))
        return pathway

    @QtCore.Slot(bool)
    def toggle_measurement(self, start):
        if start:
            self.start_measurement()
        else:
            self.stop_measurement()
        return

    @QtCore.Slot(bool)
    def toggle_measurement_pause(self, start):
        if start:
            self.pause_measurement()
        else:
            self.continue_measurement()
        return

    def start_measurement(self):
        """

        @return:
        """
        with self.thread_lock:
            if self._check_measurement_start_conditions():
                self.sigMeasurementStatusUpdated.emit(
                    self.module_state() == 'locked', self._measurement_paused)
                return

            self.module_state.lock()
            self._measurement_paused = False
            self._pause_continue_requested = False
            self._stop_requested = False
            self.sigMeasurementStatusUpdated.emit(True, False)

            self._move_path = self._create_alignment_pathway()
            self._path_index = 0
            self._align_data = np.zeros(self._align_axis_points, dtype=float)
            self.sigDataUpdated.emit(self._align_data, self.align_ranges)
        self._sigMeasurementLoop.emit()
        return

    def _check_measurement_start_conditions(self):
        if self.module_state() != 'idle':
            self.log.error('Can not start new measurement. Measurement still in progress.')
            return True

        if self.magnet_status & 1:
            self.log.error('Can not start measurement procedure. Magnet already moving.')
            return True

        if self._align_method not in self._available_alignment_methods:
            self.log.error('Can not start measurement. Unknown alignment method "{0}".'
                           ''.format(self._alignment_method))
            return True

        if self._align_method == 'fluorescence':
            pass  # Can not check for idle
        elif self._align_method == 'odmr_frequency':
            if self.odmrlogic().module_state() != 'idle':
                self.log.error('OdmrLogic still busy. Unable to start ODMR magnet alignment.')
                return True
        elif self._align_method == 'odmr_contrast':
            if self.odmrlogic().module_state() != 'idle':
                self.log.error('OdmrLogic still busy. Unable to start ODMR magnet alignment.')
                return True
        else:
            self.log.error('Alignment method "{0}" present in available_alignment_methods but not '
                           'handled in _check_measurement_start_conditions.'
                           ''.format(self._align_method))
            return True
        return False

    def stop_measurement(self):
        with self.thread_lock:
            if self.module_state() != 'locked':
                self.log.error('Unable to stop measurement. No measurement running.')
                return

            self._stop_requested = True
        return

    @QtCore.Slot()
    def _measurement_loop(self):
        with self.thread_lock:
            if self.module_state() != 'locked' or self.__in_loop:
                return

            # Stop if requested
            if self._stop_requested:
                self._measurement_paused = False
                self._pause_continue_requested = False
                self.sigMeasurementStatusUpdated.emit(False, False)
                self.module_state.unlock()
                return

            self.__in_loop = True

            if self._pause_continue_requested:
                if self._measurement_paused:
                    self._pause_continue_requested = False
                    self._measurement_paused = False
                    self.sigMeasurementStatusUpdated.emit(True, False)
                else:
                    self._pause_continue_requested = False
                    self._measurement_paused = True
                    self.sigMeasurementStatusUpdated.emit(True, True)

            if not self._measurement_paused:
                path_entry = self._move_path[self._path_index]
                magnet_pos = self.move_magnet_abs(path_entry['pos'])
                self.sigMagnetPositionUpdated.emit(magnet_pos)

                self._optimize_position()

                x_ind, y_ind = path_entry['index']
                data = self.measure_alignment()
                self._align_data[x_ind, y_ind] = data
                self.sigDataUpdated.emit(self._align_data, self.align_ranges)

                self._path_index += 1
                if self._path_index == len(self._move_path):
                    self._stop_requested = True
        self.__in_loop = False
        self._sigMeasurementLoop.emit()
        return

    def pause_measurement(self):
        with self.thread_lock:
            if self.module_state() != 'locked':
                self.log.error('Unable to pause measurement. No measurement running.')
                self._measurement_paused = False
                self._pause_continue_requested = False
                self.sigMeasurementStatusUpdated.emit(False, False)
            elif self._measurement_paused:
                self.log.warning('Unable to pause measurement. Measurement is already paused.')
                self.sigMeasurementStatusUpdated.emit(True, True)
            else:
                self._pause_continue_requested = True
        return

    def continue_measurement(self):
        with self.thread_lock:
            if self.module_state() != 'locked':
                self.log.error('Unable to continue measurement. No measurement running.')
                self._measurement_paused = False
                self._pause_continue_requested = False
                self.sigMeasurementStatusUpdated.emit(False, False)
            elif not self._measurement_paused:
                self.log.warning('Unable to continue measurement. Measurement is not paused.')
                self.sigMeasurementStatusUpdated.emit(True, False)
            else:
                self._pause_continue_requested = True
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
                                         self.optimizerlogic().optim_pos_x,
                                         self.optimizerlogic().optim_pos_y,
                                         self.optimizerlogic().optim_pos_z)
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
        if self._align_method == 'fluorescence':
            data = self._measure_fluorescence()
        elif self._align_method == 'odmr_frequency':
            data = self._measure_odmr_frequency()
        elif self._align_method == 'odmr_contrast':
            data = self._measure_odmr_contrast()
        else:
            self.log.error('Unknown alignment method "{0}".'.format(self._align_method))
            data = np.nan
        return data

    def _measure_fluorescence(self):
        """

        @return float:
        """
        if self.counterlogic().get_counting_mode() != CountingMode.CONTINUOUS:
            self.counterlogic().set_counting_mode(mode=CountingMode.CONTINUOUS)

        self.counterlogic().start_saving()
        time.sleep(self._align_measurement_time)
        curr_pos = self._move_path[self._path_index]['pos']
        tag = 'magnetalign_{0:.3e}_{1:.3e}'.format(curr_pos[self._align_axis_names[0]],
                                                   curr_pos[self._align_axis_names[1]])
        data_array, dummy = self.counterlogic().save_data(to_file=self._align_save_measurements,
                                                          postfix=tag)

        data_array = np.array(data_array)[:, 1]
        return data_array.mean()

    def _measure_odmr_frequency(self):
        """

        @return float:
        """
        params = self._align_parameters['odmr_frequency']
        curr_pos = self._move_path[self._path_index]['pos']

        # Measure low frequency
        # Set up measurement in OdmrLogic
        step = (params.low_stop_freq - params.low_start_freq) / (params.low_points - 1)
        self.odmrlogic().set_sweep_parameters(start=params.low_start_freq,
                                              stop=params.low_stop_freq,
                                              step=step,
                                              power=params.low_power)
        self.odmrlogic().set_runtime(runtime=self._align_measurement_time)
        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(0.5)
        self.odmrlogic().do_fit('Lorentzian dip')
        low_freq = self.odmrlogic().fc.current_fit_param['center'].value
        if self._align_save_measurements:
            tag = 'magnetalign_{0:.3e}_{1:.3e}_low'.format(curr_pos[self._align_axis_names[0]],
                                                           curr_pos[self._align_axis_names[1]])
            self.odmrlogic().save_odmr_data(tag=tag)
        self.odmrlogic().do_fit('No Fit')

        # Adjust center frequency for next measurement
        freq_shift = low_freq - (params.low_start_freq + params.low_stop_freq) / 2
        self._align_parameters['odmr_frequency'].low_start_freq += freq_shift
        self._align_parameters['odmr_frequency'].low_stop_freq += freq_shift
        self.sigAlignmentParametersUpdated.emit(
            'odmr_frequency', {
                'low_start_freq': self._align_parameters['odmr_frequency'].low_start_freq,
                'low_stop_freq': self._align_parameters['odmr_frequency'].low_stop_freq})

        # Measure high frequency
        # Set up measurement in OdmrLogic
        step = (params.high_stop_freq - params.high_start_freq) / (params.high_points - 1)
        self.odmrlogic().set_sweep_parameters(start=params.high_start_freq,
                                              stop=params.high_stop_freq,
                                              step=step,
                                              power=params.high_power)
        self.odmrlogic().set_runtime(runtime=self._align_measurement_time)
        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(0.5)
        self.odmrlogic().do_fit('Lorentzian dip')
        high_freq = self.odmrlogic().fc.current_fit_param['center'].value
        if self._align_save_measurements:
            tag = 'magnetalign_{0:.3e}_{1:.3e}_high'.format(curr_pos[self._align_axis_names[0]],
                                                            curr_pos[self._align_axis_names[1]])
            self.odmrlogic().save_odmr_data(tag=tag)
        self.odmrlogic().do_fit('No Fit')

        # Adjust center frequency for next measurement
        freq_shift = high_freq - (params.high_start_freq + params.high_stop_freq) / 2
        self._align_parameters['odmr_frequency'].high_start_freq += freq_shift
        self._align_parameters['odmr_frequency'].high_stop_freq += freq_shift
        self.sigAlignmentParametersUpdated.emit(
            'odmr_frequency', {
                'high_start_freq': self._align_parameters['odmr_frequency'].high_start_freq,
                'high_stop_freq': self._align_parameters['odmr_frequency'].high_stop_freq})

        # Calculate the magnetic field strength and the angle to the quantization axis.
        b_field, angle = self.calculate_field_alignment(low_freq, high_freq)
        if np.isnan(angle):
            self.log.warning('NaN value encountered during odmr frequency alignment at position '
                             '{0}={1:.3e}, {2}={3:.3e}.\nB-field angle returned set to zero.\n'
                             'B={4:.3e}G, angle={5:.3e}°'
                             ''.format(self._align_axis_names[0],
                                       curr_pos[self._align_axis_names[0]],
                                       self._align_axis_names[1],
                                       curr_pos[self._align_axis_names[1]], b_field, angle))
            angle = 0.0
        return angle

    def _measure_odmr_contrast(self):
        """

        @return float:
        """
        params = self._align_parameters['odmr_contrast']
        curr_pos = self._move_path[self._path_index]['pos']

        # Set up measurement in OdmrLogic
        step = (params.stop_freq - params.start_freq) / (params.points - 1)
        self.odmrlogic().set_sweep_parameters(start=params.start_freq,
                                              stop=params.stop_freq,
                                              step=step,
                                              power=params.power)
        self.odmrlogic().set_runtime(runtime=self._align_measurement_time)
        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(0.5)
        self.odmrlogic().do_fit('Lorentzian dip')
        odmr_freq = self.odmrlogic().fc.current_fit_param['center'].value
        odmr_contrast = self.odmrlogic().fc.current_fit_param['contrast'].value
        if self._align_save_measurements:
            tag = 'magnetalign_{0:.3e}_{1:.3e}'.format(curr_pos[self._align_axis_names[0]],
                                                       curr_pos[self._align_axis_names[1]])
            self.odmrlogic().save_odmr_data(tag=tag)
        self.odmrlogic().do_fit('No Fit')

        # Adjust center frequency for next measurement
        freq_shift = odmr_freq - (params.start_freq + params.stop_freq) / 2
        self._align_parameters['odmr_contrast'].start_freq += freq_shift
        self._align_parameters['odmr_contrast'].stop_freq += freq_shift
        self.sigAlignmentParametersUpdated.emit('odmr_contrast', {
            'start_freq': self._align_parameters['odmr_contrast'].start_freq,
            'stop_freq': self._align_parameters['odmr_contrast'].stop_freq})
        return odmr_contrast

    @QtCore.Slot()
    @QtCore.Slot(str)
    def save_data(self, tag=None, timestamp=None):
        """ Save the data of the """
        filepath = self.savelogic().get_path_for_module(module_name='Magnet')

        if timestamp is None:
            timestamp = datetime.datetime.now()
        filelabel = tag + '_magnet_alignment_data' if tag else 'magnet_alignment_data'

        # here is the matrix saved
        data_header = '{0},{1}\talignment values'.format(self._align_axis_names[0],
                                                         self._align_axis_names[1])
        matrix_data = {data_header: self._align_data}

        parameters = OrderedDict()
        parameters.update(self.general_parameters)
        parameters.update(self.alignment_parameters[self.align_method])

        self.savelogic().save_data(matrix_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   timestamp=timestamp)
        return

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