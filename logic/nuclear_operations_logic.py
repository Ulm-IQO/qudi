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

    # declare connectors
    #TODO: Use rather the task runner instead directly the module!

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
        self.x_axis_start = 1e-3                    # in s
        self.x_axis_step = 10e-3                     # in s
        self.x_axis_num_points = 50
        self.current_meas_point = self.x_axis_start
        self.current_meas_index = 0

        self._stop_requested = False

        self.mw_cw_freq = 10e9                      # in Hz
        self.mw_power = -30                         # in dBm

        self.odmr_meas_freq0 = 10000e6              # in Hz
        self.odmr_meas_freq1 = 10002.1e6            # in Hz
        self.odmr_meas_freq2 = 10004.2e6            # in Hz
        self.odmr_optimize_runtime = 30             # in s
        self.odmr_time_for_next_optimize = 300      # in s

        # store here all the measured odmr peaks
        self.measured_odmr_list = []

        # on which odmr peak the manipulation is going to be applied:
        self.mw_on_odmr_peak = 1

        self._optimize_now = False

        self.initialize_x_axis()
        self.initialize_y_axis()
        self.initialize_meas_param()

        self.current_meas_seq_name = ''

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
        self.current_meas_index = 0
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

        # prepare here everything for a measurement and go to the measurement
        # loop.
        self.prepare_measurement()

        self.sigNextMeasPoint.emit()
        pass



    def _meas_point_loop(self):
        """ Run this loop continuously until the an abort criterium is reached. """
        if self._stop_requested:
            with self.threadlock:
                # end measurement and switch all devices off
                self.stopRequested = False
                self.unlock()

                self.mw_off()
                self._pulser_off()
                # emit all needed signals for the update:
                self.sigMeasValueUpdated.emit()
                return

        if self._optimize_now:
            current_meas_seq = self.current_meas_seq_name
            self.mw_off()
            self._load_laser_on()
            self._pulser_on()
            self.do_optimize_pos()
            self._load_pulsed_odmr()
            self._pulser_on()
            self.do_optimize_odmr_freq()
            self.mw_on()
            self._load_measurement_seq(current_meas_seq)

        if self._stop_requested:
            self.sigNextMeasPoint.emit()
            return

        curr_meas_points, meas_param = self._get_meas_point()

        self._set_meas_point(self.current_meas_index, curr_meas_points, meas_param)


        # increment the measurement index or set it back to zero if it exceed
        # the maximal number of x axis measurement points:
        if self.current_meas_index + 1 > self.x_axis_num_points:
            self.current_meas_index = 0
        else:
            self.current_meas_index += 1

        self.sigNextMeasPoint.emit()

    def _set_meas_point(self, meas_index, meas_points, meas_param):
        """ Handle the proper setting of the current meas_point and store all
            the additional measurement parameter.

        @param meas_index:
        @param meas_points:
        @param meas_param:
        @return:
        """
        pass

    def _get_meas_point(self):
        """ Start the actual measurement (most probably with the gated counter)

        And perform the measurement with that routine.
        @return list, dict:
        """

        # save also the count trace of the gated counter after the measurement.
        # here the actual measurement is going to be started and stoped and
        # then analyzed and outputted in a proper format.

        return [0], {}


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

    def get_available_odmr_peaks(self):
        """ Retrieve the information on which odmr peak the microwave can be
            applied.

        @return list: with string entries denoting the peak number
        """
        return [1, 2, 3]


    def prepare_measurement(self, meas_type):
        """ Prepare and create all measurement sequences for the specified
            measurement type

        @param str meas_type: a measurement type from the list get_meas_type_list
        """
        self._create_laser_on()
        self._create_pulsed_odmr()

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

    def adjust_measurement(self, meas_type):
        """ Adjust the measurement sequence for the next measurement point.

        @param meas_type:
        @return:
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

    def _load_measurement_seq(self):
        """ Load the current measurement sequence in the pulser

        @return:
        """
        pass

    def _create_laser_on(self):
        """ Create the laser asset.

        @return:
        """
        pass

    def _load_laser_on(self):
        """ Load the laser on asset into the pulser.

        @return:
        """
        pass

    def _pulser_on(self):
        """ switch on the pulsing device.

        @return:
        """
        pass

    def _pulser_off(self):
        """ switch off the pulsing device.

        @return:
        """
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


    def _create_pulsed_odmr(self):
        #FIXME: Move this creation routine to the tasks!

        pass

    def _load_pulsed_odmr(self):
        #FIXME: Move this creation routine to the tasks!

        pass

    def do_optimize_odmr_freq(self):
        pass

    def mw_on(self):
        pass

    def mw_off(self):
        pass

    def set_mw_on_odmr_freq(self, freq, power):
        """ Set the microwave on a the specified freq with the specified power.

        """
        pass

