# -*- coding: utf-8 -*-

"""
This file contains the dummy for a motorized stage interface.

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from PyQt4 import QtCore
import numpy as np
import time

from logic.generic_logic import GenericLogic


class MagnetLogic(GenericLogic):
    """This is the Interface class to define the controls for the simple
    magnet hardware.
    """

    _modclass = 'MagnetLogic'
    _modtype = 'logic'

    ## declare connectors
    _in = {'magnetstage': 'MagnetInterface'}
    _out = {'magnetlogic': 'MagnetLogic'}

    # General Signals, used everywhere:
    sigIdleStateChanged = QtCore.Signal(bool)
    sigPosChanged = QtCore.Signal(dict)
    sigVelChanged = QtCore.Signal(dict)

    sigMeasurementStarted = QtCore.Signal()
    sigMeasurementContinued = QtCore.Signal()
    sigMeasurementStopped = QtCore.Signal()
    sigMeasurementFinished = QtCore.Signal()

    sigMoveAbs = QtCore.Signal(dict)
    sigMoveRel = QtCore.Signal(dict)

    sigAbort = QtCore.Signal()

    # Alignment Signals, remember do not touch or connect from outer logic or
    # GUI to the leading underscore signals!
    _sigStepwiseAlignmentNext = QtCore.Signal()
    _sigContinuousAlignmentNext = QtCore.Signal()
    _sigInitializeMeasPos = QtCore.Signal(bool) # signal to go to the initial measurement position
    sigPosReached = QtCore.Signal()

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

        # EXPERIMENTAL:
        # connect now directly signals to the interface methods, so that
        # the logic object will be not blocks and can react on changes or abort
        self.sigMoveAbs.connect(self._magnet_device.move_abs)
        self.sigMoveRel.connect(self._magnet_device.move_rel)
        self.sigAbort.connect(self._magnet_device.abort)


        # signal connect for alignment:

        self._sigInitializeMeasPos.connect(self._move_to_curr_pathway_index)


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
        self.sigMoveRel.emit(param_dict)
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

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        # self._magnet_device.move_abs(param_dict)
        self.sigMoveAbs.emit(param_dict)
        self.sigPosChanged.emit(param_dict)

    def stop_movement(self):
        """ Stops movement of the stage. """
        self._stop_measure = True
        self.sigAbort.emit()
        # self._magnet_device.abort()





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

    def _create_2d_pathway(self, axis0_name, axis0_range, axis0_step, axis0_vel,
                                 axis1_name, axis1_range, axis1_step, axis1_vel):
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
        axis0_num_of_steps = axis0_range//axis0_step
        axis1_num_of_steps = axis1_range//axis1_step

        # make an array of movement steps
        axis0_steparray = [axis0_step] * (axis0_num_of_steps)
        axis1_steparray = [axis1_step] * (axis1_num_of_steps)

        pathway = []

        #FIXME: create these path modes:
        if self.curr_2d_pathway_mode == 'spiral-in':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.curr_2d_pathway_mode),
                        msgType='error')
            return []

        elif self.curr_2d_pathway_mode == 'spiral-out':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.curr_2d_pathway_mode),
                        msgType='error')
            return []

        elif self.curr_2d_pathway_mode == 'diagonal-snake-wise':
            self.logMsg('The pathway creation method "{0}" through the matrix '
                        'is not implemented yet!\nReturn an empty '
                        'patharray.'.format(self.current_2d_pathway_mode),
                        msgType='error')
            return []
        # choose the snake-wise as default for now.
        #FIXME: make a handle of the situation if no method matches!
        else:

            # create a snake-wise stepping procedure through the matrix:
            go_pos_dir = True
            for step_in_axis1 in axis1_steparray:

                if go_pos_dir:
                    go_pos_dir = False
                    direction = +1
                else:
                    go_pos_dir = True
                    direction = -1

                for step_in_axis0 in axis0_steparray:
                    # make move along axis0:
                    step_config = dict()
                    step_config[axis0_name] = {'move_rel': direction*step_in_axis0}
                    pathway.append(step_config)

                # make a move along axis1:
                step_config = dict()
                step_config[axis1_name] = {'move_rel' : step_in_axis1}
                pathway.append(step_config)

        return pathway

    def _create_2d_cont_pathway(self, pathway):

        # go through the passed 1D path and reduce the whole movement just to
        # corner points

        pathway_cont =  dict()

        return pathway_cont

    def _prepare_2d_graph(self, axis0_range, axis0_step,
                                axis1_range, axis1_step):

        # set up a matrix where measurement points are save to

        return

    def _prepare_1d_graph(self, axis_range, axis_step):
        pass





    def start_1d_alignment(self, axis_name, axis_range, axis_step, axis_vel,
                                 stepwise_meas=True, continue_meas=False):


        # actual measurement routine, which is called to start the measurement


        if not continue_meas:

            # to perform the '_do_measure_after_stop' routine from the beginning
            # (which means e.g. an optimize pos)

            self._first_meas_point = True
            self._prepare_1d_graph()

            self._pathway = self._create_1d_pathway()

            if stepwise_meas:
                # just make it to an empty dict
                self._pathway_cont = dict()

            else:
                # create from the path_points the continoues points
                self._pathway_cont = self._create_1d_cont_pathway(self._pathway)




        # start the proper loop for that:

        if stepwise_meas:
            # start the Stepwise alignment loop body:
            self._sigStepwiseAlignmentNext.emit()
        else:
            # start the Stepwise alignment loop body:
            self._sigContinuousAlignmentNext.emit()



    def start_2d_alignment(self, axis0_name, axis0_range, axis0_step,
                                 axis1_name, axis1_range, axis1_step,
                                 axis0_vel=None, axis1_vel=None,
                                 stepwise_meas=True, continue_meas=False, ):

        # before starting the measurement you should convience yourself that the
        # passed traveling range is possible. Otherwise the measurement will be
        # aborted and an error is raised.
        # actual measurement routine, which is called to start the measurement



        self._stop_measure = False

        # save only the position of the axis, which are going to be moved
        # during alignment, the return will be a dict!
        self._saved_pos_before_align = self.get_pos([axis0_name, axis1_name])


        if not continue_meas:

            self.sigMeasurementStarted.emit()

            # to perform the '_do_measure_after_stop' routine from the beginning
            # (which means e.g. an optimize pos)
            self._first_meas_point = True

            # the index, which run through the _pathway list and selects the
            # current measurement point
            self._pathway_index = 0

            self._prepare_2d_graph(axis0_range, axis0_step, axis1_range, axis1_step)

            self._pathway = self._create_2d_pathway(axis0_name, axis0_range,
                                                    axis0_step, axis0_vel,
                                                    axis1_name, axis1_range,
                                                    axis1_step, axis1_vel)

            if stepwise_meas:
                # just make it to an empty dict
                self._pathway_cont = dict()

            else:
                # create from the path_points the continuous points
                self._pathway_cont = self._create_2d_cont_pathway(self._pathway)

        else:
            # tell all the connected instances that measurement is continuing:
            self.sigMeasurementContinued.emit()


        # run at first the _move_to_curr_pathway_index method to go to the
        # index position:
        self._sigInitializeMeasPos.emit(stepwise_meas)





    def _move_to_curr_pathway_index(self, stepwise_meas):

        # move to the passed pathway index in the list _pathway and start the
        # proper loop for that:

        # this function will return to this function if position is reached:
        self._check_position_reached_loop()

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


        if self._first_meas_point:

            self._do_postmeasurement_proc()
            self._first_meas_point = False


        # perform here one of the chosen alignment measurements
        meas_val, add_meas_val = self._do_alignment_measurement()

        # set the measurement point to the proper array and the proper position:
        # save also all additional measurement information, which have been
        # done during the measurement in add_meas_val.
        self._set_meas_point(meas_val, add_meas_val, self._pathway_index, self._pathway)

        # increase the index
        self._pathway_index += 1


        if (self._pathway_index-1) < len(self._pathway):

            self._do_postmeasurement_proc()

            self._move_abs_to_index(self._pathway_index, self._pathway)

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



    def stop_2d_measurement(self):
        """ Stops the 2d measurement by setting the measurement flag.

        That method should be called, if measurement has to be stopped.
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

        self.move_abs(self._saved_pos_before_align)

        self._check_position_reached_loop()

        self.sigMeasurementFinished.emit()

        self._pathway_index = 0
        self._first_meas_point = True

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

        # emit signal which is catched by _move_loop_body
        time.sleep(self.checktime)

        # calc pos:

        #return either pos reached signal of check position


    def _set_meas_point(self, meas_val, pathway_index, pathway):

        # is it point for 1d meas or 2d meas?

        # map the point back to the position in the measurement array
        pass

    def _do_postmeasurement_proc(self):

        # do a selected post measurement procedure, like e.g. optimize position.

        return

    def _do_alignment_measurement(self):

        # perform here one of the selected alignment measurements and return to
        # the loop body the measured values.

        return


    def save_1d_data(self):


        # save also all kinds of data, which are the results during the
        # alignment measurements

        pass


    def save_2d_data(self):


        # save also all kinds of data, which are the results during the
        # alignment measurements

        pass


    def _move_abs_to_index(self, pathway_index, pathway):

        # make here the move and set also for the move the velocity, if
        # specified!


        self._check_position_reached_loop()

        pass

    def set_pos_checktime(self, checktime):
        if not np.isclose(0, checktime) and checktime>0:
            self._checktime = checktime
        else:
            self.logMsg('Could not set a new value for checktime, since the '
                        'passed value "{0}" is either zero or negative!\n'
                        'Choose a proper checktime value in seconds, the old '
                        'value will be kept!', msgType='warning')