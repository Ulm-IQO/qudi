# -*- coding: utf-8 -*-

"""
This file contains the general logic for magnet control.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from pyqtgraph.Qt import QtCore
import numpy as np
import time
import os
import pyqtgraph as pg
import pyqtgraph.exporters
import datetime
from collections import OrderedDict

from logic.generic_logic import GenericLogic


class MagnetLogic(GenericLogic):
    """ A general magnet logic to control an magnetic stage with an arbitrary
        set of axis.

    DISCLAIMER:
    ===========

    The current status of the magnet logic is highly experimental and not well
    tested. The implementation has some considerable imperfections. The state of
    this module is considered to be UNSTABLE.

    This module has two major issues:
        - a lack of proper documentation of all the methods
        - usage of tasks is not implemented and therefore direct connection to
          all the modules is used (I tried to compress as good as possible all
          the part, where access to other modules occurs so that a later
          replacement would be easier and one does not have to search throughout
          the whole file.)

    However, the 'high-level state maschine' for the alignment should be rather
    general and very powerful to use. The different state were divided in
    several consecutive methods, where each method can be implemented
    separately and can be extended for custom needs. (I have drawn a diagram,
    which is much more telling then the documentation I can write down here.)

    I am currently working on that and will from time to time improve the status
    of this module. So if you want to use it, be aware that there might appear
    drastic changes.

    ---
    Alexander Stark
    """


    _modclass = 'MagnetLogic'
    _modtype = 'logic'

    ## declare connectors
    _in = {'magnetstage': 'MagnetInterface',
           'optimizerlogic': 'OptimizerLogic',
           'counterlogic': 'CounterLogic',
           'odmrlogic': 'ODMRLogic',
           'savelogic': 'SaveLogic',
           'scannerlogic':'ScannerLogic'}
    _out = {'magnetlogic': 'MagnetLogic'}

    # General Signals, used everywhere:
    sigIdleStateChanged = QtCore.Signal(bool)
    sigPosChanged = QtCore.Signal(dict)
    sigVelChanged = QtCore.Signal(dict)

    sigMeasurementStarted = QtCore.Signal()
    sigMeasurementContinued = QtCore.Signal()
    sigMeasurementStopped = QtCore.Signal()
    sigMeasurementFinished = QtCore.Signal()

    # Signals for making the move_abs, move_rel and abort independent:
    sigMoveAbs = QtCore.Signal(dict)
    sigMoveRel = QtCore.Signal(dict)
    sigAbort = QtCore.Signal()

    # Alignment Signals, remember do not touch or connect from outer logic or
    # GUI to the leading underscore signals!
    _sigStepwiseAlignmentNext = QtCore.Signal()
    _sigContinuousAlignmentNext = QtCore.Signal()
    _sigInitializeMeasPos = QtCore.Signal(bool) # signal to go to the initial measurement position
    sigPosReached = QtCore.Signal()

    # signals if new data are writen to the data arrays (during measurement):
    sig1DMatrixChanged = QtCore.Signal()
    sig2DMatrixChanged = QtCore.Signal()
    sig3DMatrixChanged = QtCore.Signal()

    # signals if the axis for the alignment are changed/renewed (before a measurement):
    sig1DAxisChanged = QtCore.Signal()
    sig2DAxisChanged = QtCore.Signal()
    sig3DAxisChanged = QtCore.Signal()

    # signal for ODMR alignment
    sigODMRLowFreqChanged = QtCore.Signal()
    sigODMRHighFreqChanged = QtCore.Signal()

    sigTest = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        self.pathway_modes = ['spiral-in', 'spiral-out', 'snake-wise', 'diagonal-snake-wise']
        self.curr_2d_pathway_mode = 'snake-wise'    # choose that as default
        self._checktime = 0.5 # in seconds


        # The data matrices and arrays. For the 1D case, self._axis0_data
        # is the actual data trace. Create also arrays for the additional
        # data, which was measured during the alignment.

        # for each axis, make a default value:
        self._1D_axis0_data = np.zeros(2)

        self._2D_axis0_data = np.zeros(2)
        self._2D_axis1_data = np.zeros(2)

        self._3D_axis0_data = np.zeros(2)
        self._3D_axis1_data = np.zeros(2)
        self._3D_axis2_data = np.zeros(2)

        self._1D_add_data_matrix = np.zeros(shape=np.shape(self._1D_axis0_data), dtype=object)

        self._2D_data_matrix = np.zeros((2, 2))
        self._2D_add_data_matrix = np.zeros(shape=np.shape(self._2D_data_matrix), dtype=object)

        self._3D_data_matrix = np.zeros((2, 2, 2))
        self._3D_add_data_matrix = np.zeros(shape=np.shape(self._3D_data_matrix), dtype=object)

        self._stop_measure = False

        #FIXME: I am right now not quite sure how to combine the passed
        #       parameters in an elegant way, therefore all the different values
        #       are stored.

        # put all the alignment methods together
        self.curr_alignment_method = '2d_fluorescence'
        self.alignment_methods = ['2d_fluorescence', '2d_odmr', '2d_nuclear']


    def activation(self, e):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._magnet_device = self.connector['in']['magnetstage']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        #FIXME: THAT IS JUST A TEMPORARY SOLUTION! Implement the access on the
        #       needed methods via the TaskRunner!
        self._optimizer_logic = self.connector['in']['optimizerlogic']['object']
        self._confocal_logic = self.connector['in']['scannerlogic']['object']
        self._counter_logic = self.connector['in']['counterlogic']['object']
        self._odmr_logic = self.connector['in']['odmrlogic']['object']


        # EXPERIMENTAL:
        # connect now directly signals to the interface methods, so that
        # the logic object will be not blocks and can react on changes or abort
        self.sigMoveAbs.connect(self._magnet_device.move_abs)
        self.sigMoveRel.connect(self._magnet_device.move_rel)
        self.sigAbort.connect(self._magnet_device.abort)


        # signal connect for alignment:

        self._sigInitializeMeasPos.connect(self._move_to_curr_pathway_index)
        self._sigStepwiseAlignmentNext.connect(self._stepwise_loop_body,
                                               QtCore.Qt.QueuedConnection)


        # connect the optimizer signals:

        self.sigTest.connect(self._do_premeasurement_proc)

        # Fluorescence alignment settings:
        self._optimize_pos = False
        self.fluorescence_integration_time = 5  # integration time in s

        # ODMR alignment settings (ALL IN SI!!!):
        self.odmr_2d_low_center_freq = 11028e6
        self.odmr_2d_low_step_freq = 0.15e6
        self.odmr_2d_low_range_freq = 25e6
        self.odmr_2d_low_power = 4
        self.odmr_2d_low_runtime = 40
        self.odmr_2d_low_fitfunction_list = self._odmr_logic.get_fit_functions()
        self.odmr_2d_low_fitfunction = self.odmr_2d_low_fitfunction_list[1]

        self.odmr_2d_high_center_freq = 16768e6
        self.odmr_2d_high_step_freq = 0.15e6
        self.odmr_2d_high_range_freq = 25e6
        self.odmr_2d_high_power = 2
        self.odmr_2d_high_runtime = 40
        self.odmr_2d_high_fitfunction_list = self._odmr_logic.get_fit_functions()
        self.odmr_2d_high_fitfunction = self.odmr_2d_high_fitfunction_list[1]

        self.odmr_2d_save_after_measure = True
        self.odmr_2d_peak_axis0_move_ratio = 0 # -13e6/ 0.01e-3    # in Hz/m
        self.odmr_2d_peak_axis1_move_ratio = 0 # -6e6/0.05e-3     # in Hz/m

        # that is just a normalization value, which is needed for the ODMR
        # alignment, since the colorbar cannot display values greater (2**32)/2.
        # A solution has to found for that!
        self.norm = 1000

        # single shot alignment on nuclear spin settings (ALL IN SI!!!):
        self.nuclear_2d_rabi_periode = 1000e-9
        self.nuclear_2d_mw_freq = 100e6
        self.nuclear_2d_mw_channel = -1
        self.nuclear_2d_mw_power = -30
        self.nuclear_2d_laser_time = 900e-9
        self.nuclear_2d_laser_channel = 2
        self.nuclear_2d_detect_channel = 1
        self.nuclear_2d_idle_time = 1500e-9
        self.nuclear_2d_reps_within_ssr = 1000
        self.nuclear_2d_num_ssr = 3000


    def deactivation(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """
        pass

    def get_hardware_constraints(self):
        """ Retrieve the hardware constraints.

        @return dict: dict with constraints for the magnet hardware. The keys
                      are the labels for the axis and the items are again dicts
                      which contain all the limiting parameters.
        """

        return self._magnet_device.get_constraints()

    def move_rel(self, param_dict):
        """ Move the specified axis in the param_dict relative with an assigned
            value.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters. E.g., for a movement of an axis
                                labeled with 'x' by 23 the dict should have the
                                form:
                                    param_dict = { 'x' : 23 }
        """

        # self._magnet_device.move_rel(param_dict)
        # start_pos = self.get_pos(list(param_dict))
        # end_pos = dict()
        #
        # for axis_name in param_dict:
        #     end_pos[axis_name] = start_pos[axis_name] + param_dict[axis_name]

        # if the magnet is moving, then the move_rel command will be neglected.
        status_dict = self.get_status(list(param_dict))
        for axis_name in status_dict:
            if status_dict[axis_name][0] != 0:
                return

        self.sigMoveRel.emit(param_dict)
        # self._check_position_reached_loop(start_pos, end_pos)
        self.sigPosChanged.emit(param_dict)


    def get_pos(self, param_list=None):
        """ Gets current position of the stage.

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """

        pos_dict = self._magnet_device.get_pos(param_list)
        return pos_dict

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and  a tuple of a status
                     number and a status dict as the item.
        """
        status = self._magnet_device.get_status(param_list)
        return status

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        # self._magnet_device.move_abs(param_dict)
        start_pos = self.get_pos(list(param_dict))
        self.sigMoveAbs.emit(param_dict)

        # self._check_position_reached_loop(start_pos, param_dict)

        self.sigPosChanged.emit(param_dict)

    def stop_movement(self):
        """ Stops movement of the stage. """
        self._stop_measure = True
        self.sigAbort.emit()
        # self._magnet_device.abort()


    def set_velocity(self, param_dict=None):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        self._magnet_device.set_velocity(param_dict)



    def _create_1d_pathway(self, axis_name, axis_range, axis_step, axis_vel):
        """  Create a path along with the magnet should move with one axis

        @param str axis_name:
        @param float axis_range:
        @param float axis_step:

        @return:

        Here you can also create fancy 1D pathways, not only linear but also
        in any kind on nonlinear fashion.
        """
        pass

    def _create_2d_pathway(self, axis0_name, axis0_range, axis0_step,
                           axis1_name, axis1_range, axis1_step, init_pos,
                           axis0_vel=None, axis1_vel=None):
        """ Create a path along with the magnet should move.

        @param str axis0_name:
        @param float axis0_range:
        @param float axis0_step:
        @param str axis1_name:
        @param float axis1_range:
        @param float axis1_step:

        @return array: 1D np.array, which has dictionary as entries. In this
                       dictionary, it will be specified, how the magnet is going
                       from the present point to the next.

        That should be quite a general function, which maps from a given matrix
        and axes information a 2D array into a 1D path with steps being the
        relative movements.

        All kind of standard and fancy pathways through the array should be
        implemented here!
        The movement is not restricted to relative movements!
        The entry dicts have the following structure:

           pathway =  [ dict1, dict2, dict3, ...]

        whereas the dictionary can only have one or two key entries:
             dict1[axis0_name] = {'move_rel': 123, 'move_vel': 3 }
             dict1[axis1_name] = {'move_abs': 29.5}

        Note that the entries may either have a relative OR an absolute movement!
        Never both! Absolute movement will be taken always before relative
        movement. Moreover you can specify in each movement step the velocity
        and the acceleration of the movement.
        E.g. if no velocity is specified, then nothing will be changed in terms
        of speed during the move.
        """

        # calculate number of steps (those are NOT the number of points!)
        axis0_num_of_steps = int(axis0_range//axis0_step)
        axis1_num_of_steps = int(axis1_range//axis1_step)

        # make an array of movement steps
        axis0_steparray = [axis0_step] * axis0_num_of_steps
        axis1_steparray = [axis1_step] * axis1_num_of_steps

        pathway = []

        #FIXME: create these path modes:
        if self.curr_2d_pathway_mode == 'spiral-in':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.curr_2d_pathway_mode),
                        msgType='error')
            return [], []

        elif self.curr_2d_pathway_mode == 'spiral-out':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.curr_2d_pathway_mode),
                        msgType='error')
            return [], []

        elif self.curr_2d_pathway_mode == 'diagonal-snake-wise':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.current_2d_pathway_mode),
                        msgType='error')
            return [], []

        elif self.curr_2d_pathway_mode == 'selected-points':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.current_2d_pathway_mode),
                        msgType='error')
            return [], []

        # choose the snake-wise as default for now.
        else:

            # create a snake-wise stepping procedure through the matrix:
            axis0_pos = round(init_pos[axis0_name] - axis0_range/2, 7)
            axis1_pos = round(init_pos[axis1_name] - axis1_range/2, 7)

            # append again so that the for loop later will run once again
            # through the axis0 array but the last value of axis1_steparray will
            # not be performed.
            axis1_steparray.append(axis1_num_of_steps)

            # step_config is the dict containing the commands for one pathway
            # entry. Move at first to start position:
            step_config = dict()

            if axis0_vel is None:
                step_config[axis0_name] = {'move_abs': axis0_pos}
            else:
                step_config[axis0_name] = {'move_abs': axis0_pos, 'move_vel': axis0_vel}

            if axis1_vel is None:
                step_config[axis1_name] = {'move_abs': axis1_pos}
            else:
                step_config[axis1_name] = {'move_abs': axis1_pos, 'move_vel': axis1_vel}

            pathway.append(step_config)

            path_index = 0

            # these indices should be used to facilitate the mapping to a 2D
            # array, since the
            axis0_index = 0
            axis1_index = 0

            # that is a map to transform a pathway index value back to an
            # absolute position and index. That will be important for saving the
            # data corresponding to a certain path_index value.
            back_map = dict()
            back_map[path_index] = {axis0_name: axis0_pos,
                                    axis1_name: axis1_pos,
                                    'index': (axis0_index, axis1_index)}

            path_index += 1
            # axis0_index += 1

            go_pos_dir = True
            for step_in_axis1 in axis1_steparray:

                if go_pos_dir:
                    go_pos_dir = False
                    direction = +1
                else:
                    go_pos_dir = True
                    direction = -1

                for step_in_axis0 in axis0_steparray:

                    axis0_index += direction
                    # make move along axis0:
                    step_config = dict()

                    # relative movement:
                    # step_config[axis0_name] = {'move_rel': direction*step_in_axis0}

                    # absolute movement:
                    axis0_pos =round(axis0_pos + direction*step_in_axis0, 7)

                    # if axis0_vel is None:
                    #     step_config[axis0_name] = {'move_abs': axis0_pos}
                    #     step_config[axis1_name] = {'move_abs': axis1_pos}
                    # else:
                    #     step_config[axis0_name] = {'move_abs': axis0_pos,
                    #                                'move_vel': axis0_vel}
                    if axis1_vel is None and axis0_vel is None:
                        step_config[axis0_name] = {'move_abs': axis0_pos}
                        step_config[axis1_name] = {'move_abs': axis1_pos}
                    else:
                        step_config[axis0_name] = {'move_abs': axis0_pos}
                        step_config[axis1_name] = {'move_abs': axis1_pos}

                        if axis0_vel is not None:
                            step_config[axis0_name] = {'move_abs': axis0_pos, 'move_vel': axis0_vel}

                        if axis1_vel is not None:
                            step_config[axis1_name] = {'move_abs': axis1_pos, 'move_vel': axis1_vel}

                    # append to the pathway
                    pathway.append(step_config)
                    back_map[path_index] = {axis0_name: axis0_pos,
                                            axis1_name: axis1_pos,
                                            'index': (axis0_index, axis1_index)}
                    path_index += 1

                if (axis1_index+1) >= len(axis1_steparray):
                    break

                # make a move along axis1:
                step_config = dict()

                # relative movement:
                # step_config[axis1_name] = {'move_rel' : step_in_axis1}

                # absolute movement:
                axis1_pos = round(axis1_pos + step_in_axis1, 7)

                if axis1_vel is None and axis0_vel is None:
                    step_config[axis0_name] = {'move_abs': axis0_pos}
                    step_config[axis1_name] = {'move_abs': axis1_pos}
                else:
                    step_config[axis0_name] = {'move_abs': axis0_pos}
                    step_config[axis1_name] = {'move_abs': axis1_pos}

                    if axis0_vel is not None:
                        step_config[axis0_name] = {'move_abs': axis0_pos, 'move_vel': axis0_vel}

                    if axis1_vel is not None:
                        step_config[axis1_name] = {'move_abs': axis1_pos, 'move_vel': axis1_vel}

                pathway.append(step_config)
                axis1_index += 1
                back_map[path_index] = {axis0_name: axis0_pos,
                                        axis1_name: axis1_pos,
                                        'index': (axis0_index, axis1_index)}
                path_index += 1



        return pathway, back_map


    def _create_2d_cont_pathway(self, pathway):

        # go through the passed 1D path and reduce the whole movement just to
        # corner points

        pathway_cont = dict()

        return pathway_cont

    def _prepare_2d_graph(self, axis0_start, axis0_range, axis0_step,
                          axis1_start, axis1_range, axis1_step):
        # set up a matrix where measurement points are save to
        # general method to prepare 2d images, and their axes.

        # that is for the matrix image. +1 because number of points and not
        # number of steps are needed:
        num_points_axis0 = (axis0_range//axis0_step) + 1
        num_points_axis1 = (axis1_range//axis1_step) + 1
        matrix = np.zeros((num_points_axis0, num_points_axis1))

        # data axis0:

        data_axis0 = np.arange(axis0_start, axis0_start + ((axis0_range//axis0_step)+1)*axis0_step, axis0_step)

        # data axis1:
        data_axis1 = np.arange(axis1_start, axis1_start + ((axis1_range//axis1_step)+1)*axis1_step, axis1_step)

        return matrix, data_axis0, data_axis1




    def _prepare_1d_graph(self, axis_range, axis_step):
        pass





    def start_1d_alignment(self, axis_name, axis_range, axis_step, axis_vel,
                                 stepwise_meas=True, continue_meas=False):


        # actual measurement routine, which is called to start the measurement


        if not continue_meas:

            # to perform the '_do_measure_after_stop' routine from the beginning
            # (which means e.g. an optimize pos)

            self._prepare_1d_graph()

            self._pathway = self._create_1d_pathway()

            if stepwise_meas:
                # just make it to an empty dict
                self._pathway_cont = dict()

            else:
                # create from the path_points the continoues points
                self._pathway_cont = self._create_1d_cont_pathway(self._pathway)

        else:
            # tell all the connected instances that measurement is continuing:
            self.sigMeasurementContinued.emit()

        # run at first the _move_to_curr_pathway_index method to go to the
        # index position:
        self._sigInitializeMeasPos.emit(stepwise_meas)



    def start_2d_alignment(self, axis0_name, axis0_range, axis0_step,
                                 axis1_name, axis1_range, axis1_step,
                                 axis0_vel=None, axis1_vel=None,
                                 stepwise_meas=True, continue_meas=False):

        # before starting the measurement you should convince yourself that the
        # passed traveling range is possible. Otherwise the measurement will be
        # aborted and an error is raised.
        #
        # actual measurement routine, which is called to start the measurement

        self._start_measurement_time = datetime.datetime.now()
        self._stop_measurement_time = None

        self._stop_measure = False

        self._axis0_name = axis0_name
        self._axis1_name = axis1_name

        # save only the position of the axis, which are going to be moved
        # during alignment, the return will be a dict!
        self._saved_pos_before_align = self.get_pos([axis0_name, axis1_name])


        if not continue_meas:

            self.sigMeasurementStarted.emit()

            # the index, which run through the _pathway list and selects the
            # current measurement point
            self._pathway_index = 0

            self._pathway, self._backmap = self._create_2d_pathway(axis0_name, axis0_range,
                                                                   axis0_step, axis1_name, axis1_range,
                                                                   axis1_step, self._saved_pos_before_align,
                                                                   axis0_vel, axis1_vel)

            # determine the start point, either relative or absolute!
            # Now the absolute position will be used:
            axis0_start = self._backmap[0][axis0_name]
            axis1_start = self._backmap[0][axis1_name]

            self._2D_data_matrix, \
            self._2D_axis0_data,\
            self._2D_axis1_data = self._prepare_2d_graph(axis0_start, axis0_range,
                                                      axis0_step, axis1_start,
                                                      axis1_range, axis1_step)

            self._2D_add_data_matrix = np.zeros(shape=np.shape(self._2D_data_matrix), dtype=object)


            if stepwise_meas:
                # just make it to an empty dict
                self._pathway_cont = dict()

            else:
                # create from the path_points the continuous points
                self._pathway_cont = self._create_2d_cont_pathway(self._pathway)

        # TODO: include here another mode, where a new defined pathway can be
        #       created, along which the measurement should be repeated.
        #       You have to follow the procedure:
        #           - Create for continuing the measurement just a proper
        #             pathway and a proper back_map in self._create_2d_pathway,
        #       => Then the whole measurement can be just run with the new
        #          pathway and back_map, and you do not have to adjust other
        #          things.

        else:
            # tell all the connected instances that measurement is continuing:
            self.sigMeasurementContinued.emit()

        # run at first the _move_to_curr_pathway_index method to go to the
        # index position:
        self._sigInitializeMeasPos.emit(stepwise_meas)


    def _move_to_curr_pathway_index(self, stepwise_meas):

        # move to the passed pathway index in the list _pathway and start the
        # proper loop for that:

        # move absolute to the index position, which is currently given

        move_dict_vel, \
        move_dict_abs, \
        move_dict_rel = self._move_to_index(self._pathway_index, self._pathway)

        self.set_velocity(move_dict_vel)
        self.move_abs(move_dict_abs)
        self.move_rel(move_dict_rel)

        # this function will return to this function if position is reached:
        start_pos = self._saved_pos_before_align
        end_pos = dict()
        for axis_name in self._saved_pos_before_align:
            end_pos[axis_name] = self._backmap[self._pathway_index][axis_name]

        self._check_position_reached_loop(start_pos_dict=start_pos,
                                          end_pos_dict=end_pos)


        if stepwise_meas:
            # start the Stepwise alignment loop body self._stepwise_loop_body:
            self._sigStepwiseAlignmentNext.emit()
        else:
            # start the continuous alignment loop body self._continuous_loop_body:
            self._sigContinuousAlignmentNext.emit()




    def _stepwise_loop_body(self):
        """ Go one by one through the created path

        @return:

        The loop body goes through the 1D array
        """


        if self._stop_measure:
            return

        self._do_premeasurement_proc()


        # perform here one of the chosen alignment measurements
        meas_val, add_meas_val = self._do_alignment_measurement()

        # set the measurement point to the proper array and the proper position:
        # save also all additional measurement information, which have been
        # done during the measurement in add_meas_val.
        self._set_meas_point(meas_val, add_meas_val, self._pathway_index, self._backmap)

        # increase the index
        self._pathway_index += 1


        if (self._pathway_index) < len(self._pathway):

            #
            self._do_postmeasurement_proc()
            move_dict_vel, \
            move_dict_abs, \
            move_dict_rel = self._move_to_index(self._pathway_index, self._pathway)

            self.set_velocity(move_dict_vel)
            self.move_abs(move_dict_abs)
            self.move_rel(move_dict_rel)


            # this function will return to this function if position is reached:
            start_pos = dict()
            end_pos = dict()
            for axis_name in self._saved_pos_before_align:
                start_pos[axis_name] = self._backmap[self._pathway_index-1][axis_name]
                end_pos[axis_name] = self._backmap[self._pathway_index][axis_name]

            self._check_position_reached_loop(start_pos_dict=start_pos,
                                              end_pos_dict=end_pos)

            # rerun this loop again
            self._sigStepwiseAlignmentNext.emit()

        else:

            self._end_alignment_procedure()


    def _continuous_loop_body(self):
        """ Go as much as possible in one direction

        @return:

        The loop body goes through the 1D array
        """
        pass



    def stop_alignment(self):
        """ Stops any kind of ongoing alignment measurement by setting a flag.
        """

        self._stop_measure = True

        # abort the movement or check whether immediate abortion of measurement
        # was needed.

        # check whether an alignment measurement is currently going on and send
        # a signal to stop that.

    def _end_alignment_procedure(self):

        # 1 check if magnet is moving and stop it

        # move back to the first position before the alignment has started:
        #
        constraints = self.get_hardware_constraints()

        last_pos = dict()
        for axis_name in self._saved_pos_before_align:
            last_pos[axis_name] = self._backmap[self._pathway_index-1][axis_name]

        self.move_abs(self._saved_pos_before_align)

        self._check_position_reached_loop(last_pos, self._saved_pos_before_align)

        self.sigMeasurementFinished.emit()

        self._pathway_index = 0
        self._stop_measurement_time = datetime.datetime.now()

        self.logMsg('Alignment Complete!', msgType='status')

        pass


    def _check_position_reached_loop(self, start_pos_dict, end_pos_dict):
        """ Perform just a while loop, which checks everytime the conditions

        @param dict start_pos_dict: the position in this dictionary must be
                                    absolute positions!
        @param dict end_pos_dict:
        @param float checktime: the checktime in seconds

        @return:

        Whenever the magnet has passed 95% of the way, the method will return.

        Check also whether the difference in position increases again, and if so
        stop the measurement and raise an error, since either the velocity was
        too fast or the magnet does not move further.
        """


        distance_init = 0.0
        constraints = self.get_hardware_constraints()
        minimal_distance = 0.0
        for axis_label in start_pos_dict:
            distance_init = (end_pos_dict[axis_label] - start_pos_dict[axis_label])**2
            minimal_distance = minimal_distance + (constraints[axis_label]['pos_step'])**2
        distance_init = np.sqrt(distance_init)
        minimal_distance = np.sqrt(minimal_distance)

        # take 97% distance tolerance:
        distance_tolerance = 0.03 * distance_init

        current_dist = 0.0

        while True:
            time.sleep(self._checktime)

            curr_pos = self.get_pos(list(end_pos_dict))

            for axis_label in start_pos_dict:
                current_dist = (end_pos_dict[axis_label] - curr_pos[axis_label])**2

            current_dist = np.sqrt(current_dist)

            self.sigPosChanged.emit(curr_pos)

            if (current_dist <= distance_tolerance) or (current_dist <= minimal_distance) or self._stop_measure:
                self.sigPosReached.emit()

                break

        #return either pos reached signal of check position


    def _set_meas_point(self, meas_val, add_meas_val, pathway_index, back_map):

        # is it point for 1d meas or 2d meas?

        # map the point back to the position in the measurement array
        index_array = back_map[pathway_index]['index']

        # then index_array is actually no array, but just a number. That is the
        # 1D case:
        if np.shape(index_array) == ():

            #FIXME: Implement the 1D save

            self.sig1DMatrixChanged.emit()

        elif np.shape(index_array)[0] == 2:

            self._2D_data_matrix[index_array] = meas_val
            self._2D_add_data_matrix[index_array] = add_meas_val

            # self.logMsg('Data "{0}", saved at intex "{1}"'.format(meas_val, index_array), msgType='status')

            self.sig2DMatrixChanged.emit()

        elif np.shape(index_array)[0] == 3:


            #FIXME: Implement the 3D save
            self.sig3DMatrixChanged.emit()
        else:
            self.logMsg('The measurement point "{0}" could not be set in the '
                        '_set_meas_point routine, since either a 1D, a 2D or a '
                        '3D index array was expected, but an index array "{1}" '
                        'was given in the passed back_map. Correct the '
                        'back_map creation in the routine '
                        '_create_2d_pathway!'.format(meas_val, index_array),
                        msgType='error')




        pass

    def _do_premeasurement_proc(self):
        # do a selected pre measurement procedure, like e.g. optimize position.


        # first attempt of an optimizer usage:
        if self._optimize_pos:
            self._do_optimize_pos()

        return

    def _do_optimize_pos(self):

        curr_pos = self._confocal_logic.get_position()

        self._optimizer_logic.start_refocus(curr_pos, caller_tag='magnet_logic')

        # check just the state of the optimizer
        while self._optimizer_logic.getState() != 'idle' and not self._stop_measure:
            time.sleep(0.5)

        # use the position to move the scanner
        self._confocal_logic.set_position('magnet_logic',
                                          self._optimizer_logic.optim_pos_x,
                                          self._optimizer_logic.optim_pos_y,
                                          self._optimizer_logic.optim_pos_z)

    def _do_alignment_measurement(self):
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

        # perform here one of the selected alignment measurements and return to
        # the loop body the measured values.


        # self.alignment_methods = ['fluorescence_pointwise',
        #                           'fluorescence_continuous',
        #                           'odmr_splitting',
        #                           'odmr_hyperfine_splitting',
        #                           'nuclear_spin_measurement']

        if self.curr_alignment_method == '2d_fluorescence':
            data, add_data = self._perform_fluorescence_measure()

        elif self.curr_alignment_method == '2d_odmr':
            data, add_data = self._perform_odmr_measure()

        elif self.curr_alignment_method == '2d_nuclear':
            data, add_data = self._perform_nuclear_measure()
        # data, add_data = self._perform_odmr_measure(11100e6, 1e6, 11200e6, 5, 10, 'Lorentzian', False,'')


        return data, add_data


    def _perform_fluorescence_measure(self):

        #FIXME: that should be run through the TaskRunner! Implement the call
        #       by not using this connection!

        self._counter_logic.start_saving()
        time.sleep(self.fluorescence_integration_time)
        data_array, parameters = self._counter_logic.save_data(to_file=False)

        data_array = np.array(data_array)[:, 1]

        return data_array.mean(), parameters

    def _perform_odmr_measure(self):
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
            axis0_pos_start = self._backmap[self._pathway_index-1][self._axis0_name]
            axis0_pos_stop = self._backmap[self._pathway_index][self._axis0_name]

            axis1_pos_start = self._backmap[self._pathway_index-1][self._axis1_name]
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
            if self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']].get('low_freq_Frequency') is not None:
                low_odmr_freq1 = self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']]['low_freq_Frequency']['value']*1e6
                low_odmr_freq2 = self._2D_add_data_matrix[self._backmap[self._pathway_index-2]['index']]['low_freq_Frequency']['value']*1e6
            elif self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']].get('low_freq_Freq. 1') is not None:
                low_odmr_freq1 = self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']]['low_freq_Freq. 1']['value']*1e6
                low_odmr_freq2 = self._2D_add_data_matrix[self._backmap[self._pathway_index-2]['index']]['low_freq_Freq. 1']['value']*1e6
            else:
                self.logMsg('No previous saved lower odmr freq found in '
                            'ODMR alignment data! Cannot do the ODMR '
                            'Alignment!', msgType='error')

            if self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']].get('high_freq_Frequency') is not None:
                high_odmr_freq1 = self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']]['high_freq_Frequency']['value']*1e6
                high_odmr_freq2 = self._2D_add_data_matrix[self._backmap[self._pathway_index-2]['index']]['high_freq_Frequency']['value']*1e6
            elif self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']].get('high_freq_Freq. 1') is not None:
                high_odmr_freq1 = self._2D_add_data_matrix[self._backmap[self._pathway_index-1]['index']]['high_freq_Freq. 1']['value']*1e6
                high_odmr_freq2 = self._2D_add_data_matrix[self._backmap[self._pathway_index-2]['index']]['high_freq_Freq. 1']['value']*1e6
            else:
                self.logMsg('No previous saved higher odmr freq found in '
                            'ODMR alignment data! Cannot do the ODMR '
                            'Alignment!', msgType='error')

            # only if there was a non zero movement, the if make sense to
            # calculate the shift for either the axis0 or axis1.
            # BE AWARE THAT FOR A MOVEMENT IN AXIS0 AND AXIS1 AT THE SAME TIME
            # NO PROPER CALCULATION OF THE OMDR LINES CAN BE PROVIDED!
            if not np.isclose(axis0_move, 0.0):
                # update the correction ratio:
                low_peak_axis0_move_ratio = (low_odmr_freq1 - low_odmr_freq2)/axis0_move
                high_peak_axis0_move_ratio = (high_odmr_freq1 - high_odmr_freq2)/axis0_move

                # print('low_odmr_freq2', low_odmr_freq2, 'low_odmr_freq1', low_odmr_freq1)
                # print('high_odmr_freq2', high_odmr_freq2, 'high_odmr_freq1', high_odmr_freq1)

                # calculate the average shift of the odmr lines for the lower
                # and the upper transition:
                self.odmr_2d_peak_axis0_move_ratio = (low_peak_axis0_move_ratio +high_peak_axis0_move_ratio)/2

                # print('new odmr_2d_peak_axis0_move_ratio', self.odmr_2d_peak_axis0_move_ratio/1e12)
            if not np.isclose(axis1_move, 0.0):
                # update the correction ratio:
                low_peak_axis1_move_ratio = (low_odmr_freq1 - low_odmr_freq2)/axis1_move
                high_peak_axis1_move_ratio = (high_odmr_freq1 - high_odmr_freq2)/axis1_move

                # calculate the average shift of the odmr lines for the lower
                # and the upper transition:
                self.odmr_2d_peak_axis1_move_ratio = (low_peak_axis1_move_ratio + high_peak_axis1_move_ratio)/2

                # print('new odmr_2d_peak_axis1_move_ratio', self.odmr_2d_peak_axis1_move_ratio/1e12)

        # Measurement of the lower transition:
        # -------------------------------------

        freq_shift_low_axis0 = axis0_move * self.odmr_2d_peak_axis0_move_ratio
        freq_shift_low_axis1 = axis1_move * self.odmr_2d_peak_axis1_move_ratio

        # correct here the center freq with the estimated corrections:
        self.odmr_2d_low_center_freq += (freq_shift_low_axis0 + freq_shift_low_axis1)
        # print('self.odmr_2d_low_center_freq',self.odmr_2d_low_center_freq)

        # create a unique nametag for the current measurement:
        name_tag = 'low_trans_index_'+str(self._backmap[self._pathway_index]['index'][0]) \
                   +'_'+ str(self._backmap[self._pathway_index]['index'][1])

        # of course the shift of the ODMR peak is not linear for a movement in
        # axis0 and axis1, but we need just an estimate how to set the boundary
        # conditions for the first scan, since the first scan will move to a
        # start position and then it need to know where to search for the ODMR
        # peak(s).

        # calculate the parameters for the odmr scan:
        low_start_freq = self.odmr_2d_low_center_freq - self.odmr_2d_low_range_freq/2
        low_step_freq = self.odmr_2d_low_step_freq
        low_stop_freq = self.odmr_2d_low_center_freq + self.odmr_2d_low_range_freq/2

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
            store_dict['low_freq_'+str(entry)] = param[entry]

        # extract the frequency meausure:
        if param.get('Frequency') is not None:
            odmr_low_freq_meas = param['Frequency']['value']*1e6
        elif param.get('Freq. 1') is not None:
            odmr_low_freq_meas = param['Freq. 1']['value']*1e6
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
        name_tag = 'high_trans_index_'+str(self._backmap[self._pathway_index]['index'][0]) \
                   +'_'+ str(self._backmap[self._pathway_index]['index'][1])

        # of course the shift of the ODMR peak is not linear for a movement in
        # axis0 and axis1, but we need just an estimate how to set the boundary
        # conditions for the first scan, since the first scan will move to a
        # start position and then it need to know where to search for the ODMR
        # peak(s).

        # calculate the parameters for the odmr scan:
        high_start_freq = self.odmr_2d_high_center_freq - self.odmr_2d_high_range_freq/2
        high_step_freq = self.odmr_2d_high_step_freq
        high_stop_freq = self.odmr_2d_high_center_freq + self.odmr_2d_high_range_freq/2

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
            store_dict['high_freq_'+str(entry)] = param[entry]

        # extract the frequency meausure:
        if param.get('Frequency') is not None:
            odmr_high_freq_meas = param['Frequency']['value']*1e6
        elif param.get('Freq. 1') is not None:
            odmr_high_freq_meas = param['Freq. 1']['value']*1e6
        else:
            # a default value for testing and debugging:
            odmr_high_freq_meas = 2000e6

        # correct the estimated center frequency by the actual measured one.
        self.odmr_2d_high_center_freq = odmr_high_freq_meas

        #FIXME: the normalization is just done for the display to view the
        #       value properly! There is right now a bug in the colorbad
        #       display, which need to be solved.
        diff = (abs(odmr_high_freq_meas - odmr_low_freq_meas)/2)/self.norm

        while self._odmr_logic.getState() != 'idle' and not self._stop_measure:
            time.sleep(0.5)

        return diff, store_dict

    def _perform_nuclear_measure(self):
        """ Make a single shot alignment. """
        pass

    def _do_postmeasurement_proc(self):

        # do a selected post measurement procedure,

        return

    def save_1d_data(self):


        # save also all kinds of data, which are the results during the
        # alignment measurements

        pass


    def save_2d_data(self, tag=None, timestamp=None):
        """ Save the data of the  """

        filepath = self._save_logic.get_path_for_module(module_name='Magnet')

        if timestamp is None:
            timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_magnet_alignment_data'
            filelabel2 = tag + '_magnet_alignment_add_data'
        else:
            filelabel = 'magnet_alignment_data'
            filelabel2 = 'magnet_alignment_add_data'

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
            parameters['index_'+str(index)] = entry

        parameters['Backmap of the magnet alignment'] = 'Index wise display'

        for entry in self._backmap:
            parameters['related_intex_'+str(entry)] = self._backmap[entry]



        self._save_logic.save_data(matrix_data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True)

        self.logMsg('Magnet 2D data saved to:\n{0}'.format(filepath),
                    msgType='status', importance=3)

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



        self._save_logic.save_data(add_data, filepath,
                                   filelabel=filelabel2, timestamp=timestamp,
                                   as_text=True)
        # save also all kinds of data, which are the results during the
        # alignment measurements


    def _move_to_index(self, pathway_index, pathway):

        # make here the move and set also for the move the velocity, if
        # specified!

        move_commmands = pathway[pathway_index]

        move_dict_abs = dict()
        move_dict_rel = dict()
        move_dict_vel = dict()

        for axis_name in move_commmands:

            if move_commmands[axis_name].get('vel') is not None:
                    move_dict_vel[axis_name] = move_commmands[axis_name]['vel']

            if move_commmands[axis_name].get('move_abs') is not None:
                move_dict_abs[axis_name] = move_commmands[axis_name]['move_abs']
            elif move_commmands[axis_name].get('move_rel') is not None:
                move_dict_rel[axis_name] = move_commmands[axis_name]['move_rel']

        return move_dict_vel, move_dict_abs, move_dict_rel

    def set_pos_checktime(self, checktime):
        if not np.isclose(0, checktime) and checktime>0:
            self._checktime = checktime
        else:
            self.logMsg('Could not set a new value for checktime, since the '
                        'passed value "{0}" is either zero or negative!\n'
                        'Choose a proper checktime value in seconds, the old '
                        'value will be kept!', msgType='warning')


    def get_2d_data_matrix(self):
        return self._2D_data_matrix

    def get_2d_axis_arrays(self):
        return self._2D_axis0_data, self._2D_axis1_data

    def set_optimize_pos(self, state=True):
        """ Activate the optimize position option. """
        self._optimize_pos = state

    def get_optimize_pos(self):
        """ Retrieve whether the optimize position is set.

        @return bool: whether the optimize_pos is set or not.
        """
        return self._optimize_pos
