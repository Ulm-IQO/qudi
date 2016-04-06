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

    sigMeasurementStart = QtCore.Signal(dict)
    sigMeasurementStop = QtCore.Signal(dict)

    # Alignment Signals:
    sigAlingmentNextPoint = QtCore.Signal()

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

        self._magnet_device.move_rel(param_dict)

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
        self._magnet_device.move_abs(param_dict)

    def stop_movement(self):
        """ Stops movement of the stage. """
        self._magnet_device.abort()


    def _create_1d_pathway(self, axis_name, axis_start, axis_step, axis_stop):
        """  Create a path along with the magnet should move with one axis

        @param str axis_name:
        @param axis_start:
        @param axis_step:
        @param axis_stop:

        @return:

        Here you can also create fancy 1D pathways, not only linear but also
        in any kind on nonlinear fashion.
        """


    def _create_2d_pathway(self, axis0_name, axis0_start, axis0_step, axis0_stop,
                              axis1_name, axis1_start, axis1_step, axis1_stop):
        """ Create a path along with the magnet should move.

        @param str x_axis:
        @param x_start:
        @param x_step:
        @param x_stop:
        @param str y_axis:
        @param y_start:
        @param y_step:
        @param y_stop:

        @return array: 1D np.array, which has dictionary as entries. In this
                       dictionary, it will be specified, how the magnet is going
                       from the present point to the next.
        """
        pass



    def _move_loop_body(self):
        """ Go one by one through the created path

        @return:

        The loop body goes through the 1D array
        """
        pass