# -*- coding: utf-8 -*-

"""
This file contains the QuDi Logic to control Nuclear Operations.

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

import numpy as np
from PyQt4 import QtCore
import time
from collections import OrderedDict

from logic.generic_logic import GenericLogic


class NuclearOperationsLogic(GenericLogic):
    """ A higher order logic, which combines several lower class logic modules
        in order to perform measurements and manipulations of nuclear spins.

    DISCLAIMER:
    ===========

    This module has two major issues:
        - a lack of proper documentation of all the methods
        - usage of tasks is not implemented and therefore direct connection to
          all the modules is used (I tried to compress as good as possible all
          the part, where access to other modules occurs so that a later
          replacement would be easier and one does not have to search throughout
          the whole file.)

    The state of this module is considered to be UNSTABLE.

    I am currently working on that and will from time to time improve the status
    of this module. So if you want to use it, be aware that there might appear
    drastic changes.
    ---
    Alexander Stark

    """

    _modclass = 'NuclearOperationsLogic'
    _modtype = 'logic'

        ## declare connectors
    _in = {'sequencegenerationlogic': 'SequenceGenerationLogic',
           'traceanalysislogic': 'TraceAnalysisLogic',
           'odmrlogic': 'ODMRLogic',
           'optimizerlogic': 'OptimizerLogic',
           'scannerlogic':'ScannerLogic',
           'savelogic': 'SaveLogic'}

    _out = {'nuclearoperationlogic': 'NuclearOperationsLogic'}

    sigNextMeasPoint = QtCore.Signal()
    sigCurrMeasPointUpdated = QtCore.Signal()
    sigMeasValueUpdated = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')



    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """


        # choose some default values:
        self.x_axis_start = 1e-3
        self.x_axis_step = 10e3
        self.x_axis_num_points = 50

        self._stop_requested = False

        self.initialize_x_axis()
        self.initialize_y_axis()
        self.initialize_meas_param()

        # establish the access to all connectors:
        self._save_logic = self.connector['in']['savelogic']['object']

        #FIXME: THAT IS JUST A TEMPORARY SOLUTION! Implement the access on the
        #       needed methods via the TaskRunner!
        self._seq_gen_logic = self.connector['in']['sequencegenerationlogic']['object']
        self._trace_logic = self.connector['in']['traceanalysislogic']['object']
        self._odmr_logic = self.connector['in']['odmrlogic']['object']
        self._optimizer_logic = self.connector['in']['optimizerlogic']['object']
        self._confocal_logic = self.connector['in']['scannerlogic']['object']


        # connect signals:
        self.sigNextMeasPoint.connect(self._meas_point_loop, QtCore.Qt.QueuedConnection)

    def deactivation(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """
        pass


    def initialize_x_axis(self):
        """ Initialize the x axis. """

        stop = self.x_axis_start + self.x_axis_step*self.x_axis_num_points
        self.x_axis_list = np.arange(self.x_axis_start, stop+(self.x_axis_step/2), self.x_axis_step)
        self.current_meas_point = self.x_axis_start
        self.sigCurrMeasPointUpdated.emit()

    def initialize_y_axis(self):
        """ Initialize the y axis. """
        self.y_axis_list = np.zeros(self.x_axis_list.shape)
        self.y_axis_fit_list = np.zeros(self.x_axis_list.shape)

    def initialize_meas_param(self):
        """ Initialize the measurement param containter. """
        # here all measurement parameters will be included for any kind of
        # nuclear measurement.
        self._meas_param = OrderedDict()


    def start_nuclear_meas(self):
        """ Start the nuclear operation measurement. """
        self.sigNextMeasPoint.emit()
        pass



    def _meas_point_loop(self):
        """ Run this loop continuously until the an abort criterium is reached. """
        if self._stop_requested:
            with self.threadlock:
                # end measurement and switch all devices off
                self.stopRequested = False
                self.unlock()
                # emit all needed signals for the update:
                self.sigMeasValueUpdated.emit()
                return




        self.sigNextMeasPoint.emit()


    def stop_nuclear_meas(self):
        """ Stop the Nuclear Operation Measurement.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self._stop_requested = True
        return 0



    def get_fit_functions(self):
        """ Returns all fit methods, which are currently implemented for that module.

        @return list: with string entries denoting the names of the fit.
        """
        return ['No Fit', 'pos. Lorentzian', 'neg. Lorentzian', 'pos. Gaussian']


    def do_fit(self, fit_function=None):
        """ Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function

        @return dict: a dictionary with the relevant fit parameters, i.e. the
                      result of the fit
        """
        #TODO: implement the fit.
        pass


    def get_meas_type_list(self):
        return ['Nuclear Rabi', 'Nuclear Frequency Scan',
                'QSD - Artificial Drive', 'QSD - SWAP FID',
                'QSD - Entanglement FID']


    def prepare_measurement(self, meas_type):
        """ Prepare and create all measurement sequences for the specified
            measurement type

        @param str meas_type: a measurement type from the list get_meas_type_list
        """

        if meas_type == 'Nuclear Rabi':
            pass

        elif meas_type == 'Nuclear Frequency Scan':
            pass

        elif meas_type == 'QSD - Artificial Drive':
            pass

        elif meas_type == 'QSD - SWAP FID':
            pass

        elif meas_type == 'QSD - Entanglement FID':
            pass


    def do_optimize_pos(self):
        """ Perform an optimize position. """

        #FIXME: Move this optimization routine to the tasks!

        curr_pos = self._confocal_logic.get_position()

        self._optimizer_logic.start_refocus(curr_pos, caller_tag='nuclear_operations_logic')

        # check just the state of the optimizer
        while self._optimizer_logic.getState() != 'idle' and not self._stop_requested:
            time.sleep(0.5)

        # use the position to move the scanner
        self._confocal_logic.set_position('nuclear_operations_logic',
                                          self._optimizer_logic.optim_pos_x,
                                          self._optimizer_logic.optim_pos_y,
                                          self._optimizer_logic.optim_pos_z)


    def do_optimize_odmr_pos(self):
        pass


    def set_odmr_freq(self, freq1, freq2=None, freq3=None, power=-30, low=True):
        """ Set the parameters for the ODMR measurement/optimization.

        @param float freq1: frequency in Hz
        @param float freq2: frequency in Hz
        @param float freq3: frequency in Hz
        @param float power: power in dBm
        @param bool low: if True frequencies are for lower electron spin
                         transition, else for higher electron spin transition.

        """


        if low:
            text = 'low'
        else:
            text = 'high'

        self._meas_param['odmr_'+text+'_power'] = power
        self._meas_param['odmr_'+text+'_freq1'] = freq1

        if freq2 is not None:
            self._meas_param['odmr_'+text+'_freq2'] = freq2
        if freq3 is not None:
            self._meas_param['odmr_'+text+'_freq3'] = freq3
