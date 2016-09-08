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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import time
from collections import OrderedDict
from qtpy import QtCore
import datetime

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


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
           'gatedcounterlogic': 'CounterLogic',
           'odmrlogic': 'ODMRLogic',
           'optimizerlogic': 'OptimizerLogic',
           'scannerlogic':'ScannerLogic',
           'savelogic': 'SaveLogic'}

    _out = {'nuclearoperationlogic': 'NuclearOperationsLogic'}

    sigNextMeasPoint = QtCore.Signal()
    sigCurrMeasPointUpdated = QtCore.Signal()
    sigMeasurementStopped = QtCore.Signal()

    sigMeasStarted = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

        self.threadlock = Mutex()

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        # Retrieve the status variables or use default values:
        # ==========================

        # pulser parameters:
        # ==================

        if 'electron_rabi_periode' in self._statusVariables:
            self.electron_rabi_periode = self._statusVariables['electron_rabi_periode']
        else:
            self.electron_rabi_periode = 1800e-9        # in s

        # pulser microwave:

        if 'pulser_mw_freq' in self._statusVariables:
            self.pulser_mw_freq = self._statusVariables['pulser_mw_freq']
        else:
            self.pulser_mw_freq = 200e6     # in Hz

        if 'pulser_mw_amp' in self._statusVariables:
            self.pulser_mw_amp = self._statusVariables['pulser_mw_amp']
        else:
            self.pulser_mw_amp = 2.25          # in V

        if 'pulser_mw_ch' in self._statusVariables:
            self.pulser_mw_ch = self._statusVariables['pulser_mw_ch']
        else:
            self.pulser_mw_ch = -1

        # pulser rf:
        if 'nuclear_rabi_period0' in self._statusVariables:
            self.nuclear_rabi_period0 = self._statusVariables['nuclear_rabi_period0']
        else:
            self.nuclear_rabi_period0 = 30e-6   # in s

        if 'pulser_rf_freq0' in self._statusVariables:
            self.pulser_rf_freq0 = self._statusVariables['pulser_rf_freq0']
        else:
            self.pulser_rf_freq0 = 6.32e6   # in Hz

        if 'pulser_rf_amp0' in self._statusVariables:
            self.pulser_rf_amp0 = self._statusVariables['pulser_rf_amp0']
        else:
            self.pulser_rf_amp0 = 0.1

        if 'nuclear_rabi_period1' in self._statusVariables:
            self.nuclear_rabi_period1 = self._statusVariables['nuclear_rabi_period1']
        else:
            self.nuclear_rabi_period1 = 30e-6   # in s

        if 'pulser_rf_freq1' in self._statusVariables:
            self.pulser_rf_freq1 = self._statusVariables['pulser_rf_freq1']
        else:
            self.pulser_rf_freq1 = 3.24e6   # in Hz

        if 'pulser_rf_amp1' in self._statusVariables:
            self.pulser_rf_amp1 = self._statusVariables['pulser_rf_amp1']
        else:
            self.pulser_rf_amp1 = 0.1

        if 'pulser_rf_ch' in self._statusVariables:
            self.pulser_rf_ch = self._statusVariables['pulser_rf_ch']
        else:
            self.pulser_rf_ch = -2

        # laser options:
        if 'pulser_laser_length' in self._statusVariables:
            self.pulser_laser_length = self._statusVariables['pulser_laser_length']
        else:
            self.pulser_laser_length = 3e-6 # in s
        if 'pulser_laser_amp' in self._statusVariables:
            self.pulser_laser_amp = self._statusVariables['pulser_laser_amp']
        else:
            self.pulser_laser_amp = 1       # in V
        if 'pulser_laser_ch' in self._statusVariables:
            self.pulser_laser_ch = self._statusVariables['pulser_laser_ch']
        else:
            self.pulser_laser_ch = 1

        if 'num_singleshot_readout' in self._statusVariables:
            self.num_singleshot_readout = self._statusVariables['num_singleshot_readout']
        else:
            self.num_singleshot_readout = 3000

        if 'pulser_idle_time' in self._statusVariables:
            self.pulser_idle_time = self._statusVariables['pulser_idle_time']
        else:
            self.pulser_idle_time = 1.5e-6  # in s
        # detection gated counter:
        if 'pulser_detect_ch' in self._statusVariables:
            self.pulser_detect_ch = self._statusVariables['pulser_detect_ch']
        else:
            self.pulser_detect_ch = 1

        # measurement parameters:
        if 'current_meas_asset_name' in self._statusVariables:
            self.current_meas_asset_name = self._statusVariables['current_meas_asset_name']
        else:
            self.current_meas_asset_name = ''
        if 'x_axis_start' in self._statusVariables:
            self.x_axis_start = self._statusVariables['x_axis_start']
        else:
            self.x_axis_start = 1e-3                    # in s
        if 'x_axis_step' in self._statusVariables:
            self.x_axis_step = self._statusVariables['x_axis_step']
        else:
            self.x_axis_step = 10e-3                     # in s
        if 'x_axis_num_points' in self._statusVariables:
            self.x_axis_num_points = self._statusVariables['x_axis_num_points']
        else:
            self.x_axis_num_points = 50
        if 'num_of_meas_runs' in self._statusVariables:
            self.num_of_meas_runs = self._statusVariables['num_of_meas_runs']
        else:
            self.num_of_meas_runs   = 1 # How often the measurement should be repeated.

        # current measurement information:
        self.current_meas_point = self.x_axis_start
        self.current_meas_index = 0
        self.num_of_current_meas_runs = 0
        self.elapsed_time = 0
        self.start_time = datetime.datetime.now()
        self.next_optimize_time = self.start_time

        # parameters for confocal and odmr optimization:
        if 'optimize_period_odmr' in self._statusVariables:
            self.optimize_period_odmr = self._statusVariables['optimize_period_odmr']
        else:
            self.optimize_period_odmr = 200
        if 'optimize_period_confocal' in self._statusVariables:
            self.optimize_period_confocal = self._statusVariables['optimize_period_confocal']
        else:
            self.optimize_period_confocal = 300      # in s
        if 'odmr_meas_freq0' in self._statusVariables:
            self.odmr_meas_freq0 = self._statusVariables['odmr_meas_freq0']
        else:
            self.odmr_meas_freq0 = 10000e6              # in Hz
        if 'odmr_meas_freq1' in self._statusVariables:
            self.odmr_meas_freq1 = self._statusVariables['odmr_meas_freq1']
        else:
            self.odmr_meas_freq1 = 10002.1e6            # in Hz
        if 'odmr_meas_freq2' in self._statusVariables:
            self.odmr_meas_freq2 = self._statusVariables['odmr_meas_freq2']
        else:
            self.odmr_meas_freq2 = 10004.2e6            # in Hz
        if 'odmr_meas_runtime' in self._statusVariables:
            self.odmr_meas_runtime = self._statusVariables['odmr_meas_runtime']
        else:
            self.odmr_meas_runtime = 30             # in s
        if 'odmr_meas_freq_range' in self._statusVariables:
            self.odmr_meas_freq_range = self._statusVariables['odmr_meas_freq_range']
        else:
            self.odmr_meas_freq_range = 30e6            # in Hz
        if 'odmr_meas_step' in self._statusVariables:
            self.odmr_meas_step = self._statusVariables['odmr_meas_step']
        else:
            self.odmr_meas_step = 0.15e6                # in Hz
        if 'odmr_meas_power' in self._statusVariables:
            self.odmr_meas_power = self._statusVariables['odmr_meas_power']
        else:
            self.odmr_meas_power = -30                  # in dBm

        # Microwave measurment parameters:
        if 'mw_cw_freq' in self._statusVariables:
            self.mw_cw_freq = self._statusVariables['mw_cw_freq']
        else:
            self.mw_cw_freq = 10e9                      # in Hz
        if 'mw_cw_power' in self._statusVariables:
            self.mw_cw_power = self._statusVariables['mw_cw_power']
        else:
            self.mw_cw_power = -30                         # in dBm


        # store here all the measured odmr peaks
        self.measured_odmr_list = []

        # on which odmr peak the manipulation is going to be applied:
        if 'mw_on_odmr_peak' in self._statusVariables:
            self.mw_on_odmr_peak = self._statusVariables['mw_on_odmr_peak']
        else:
            self.mw_on_odmr_peak = 1

        # Gated counter:
        if 'gc_number_of_samples' in self._statusVariables:
            self.gc_number_of_samples = self._statusVariables['gc_number_of_samples']
        else:
            self.gc_number_of_samples = 3000    # in counts

        if 'gc_samples_per_readout' in self._statusVariables:
            self.gc_samples_per_readout = self._statusVariables['gc_samples_per_readout']
        else:
            self.gc_samples_per_readout = 10    # in counts




        self._optimize_now = False
        self._stop_requested = False

        # store here all the measured odmr peaks
        self.measured_odmr_list = []

        # Perform initialization routines:
        self.initialize_x_axis()
        self.initialize_y_axis()
        self.initialize_meas_param()

        # establish the access to all connectors:
        self._save_logic = self.connector['in']['savelogic']['object']

        #FIXME: THAT IS JUST A TEMPORARY SOLUTION! Implement the access on the
        #       needed methods via the TaskRunner!
        self._seq_gen_logic = self.connector['in']['sequencegenerationlogic']['object']
        self._trace_ana_logic = self.connector['in']['traceanalysislogic']['object']
        self._gc_logic = self.connector['in']['gatedcounterlogic']['object']
        self._odmr_logic = self.connector['in']['odmrlogic']['object']
        self._optimizer_logic = self.connector['in']['optimizerlogic']['object']
        self._confocal_logic = self.connector['in']['scannerlogic']['object']


        # connect signals:
        self.sigNextMeasPoint.connect(self._meas_point_loop, QtCore.Qt.QueuedConnection)

    def on_deactivate(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """


        # Save the status variables:
        # ==========================

        # Pulser parameter:
        # electron Rabi:
        self._statusVariables['electron_rabi_periode'] = self.electron_rabi_periode

        # pulser microwave:
        self._statusVariables['pulser_mw_freq'] = self.pulser_mw_freq
        self._statusVariables['pulser_mw_amp'] = self.pulser_mw_amp
        self._statusVariables['pulser_mw_ch'] = self.pulser_mw_ch

        # pulser radiofrequency:
        self._statusVariables['nuclear_rabi_period0'] = self.nuclear_rabi_period0
        self._statusVariables['pulser_rf_freq0'] = self.pulser_rf_freq0
        self._statusVariables['pulser_rf_amp0'] = self.pulser_rf_amp0
        self._statusVariables['nuclear_rabi_period1'] = self.nuclear_rabi_period1
        self._statusVariables['pulser_rf_freq1'] = self.pulser_rf_freq1
        self._statusVariables['pulser_rf_amp1'] = self.pulser_rf_amp1
        self._statusVariables['pulser_rf_ch'] = self.pulser_rf_ch

        # pulser laser parameters:
        self._statusVariables['pulser_laser_length'] = self.pulser_laser_length
        self._statusVariables['pulser_laser_amp'] = self.pulser_laser_amp
        self._statusVariables['pulser_laser_ch'] = self.pulser_laser_ch
        self._statusVariables['num_singleshot_readout'] = self.num_singleshot_readout

        # pulser idle status:
        self._statusVariables['pulser_idle_time'] = self.pulser_idle_time
        # detect channel:
        self._statusVariables['pulser_detect_ch'] = self.pulser_detect_ch


        # Measurement parameter:
        self._statusVariables['current_meas_asset_name'] = self.current_meas_asset_name

        # x-axis value:
        self._statusVariables['x_axis_start'] = self.x_axis_start
        self._statusVariables['x_axis_step'] = self.x_axis_step
        self._statusVariables['x_axis_num_points'] = self.x_axis_num_points
        self._statusVariables['num_of_meas_runs'] = self.num_of_meas_runs


        # Optimization parameter
        self._statusVariables['optimize_period_odmr'] = self.optimize_period_odmr
        self._statusVariables['optimize_period_confocal'] = self.optimize_period_confocal
        # parameters for pulsed ODMR:
        self._statusVariables['odmr_meas_freq0'] = self.odmr_meas_freq0
        self._statusVariables['odmr_meas_freq1'] = self.odmr_meas_freq1
        self._statusVariables['odmr_meas_freq2'] = self.odmr_meas_freq2
        self._statusVariables['odmr_meas_runtime'] = self.odmr_meas_runtime
        self._statusVariables['odmr_meas_freq_range'] = self.odmr_meas_freq_range
        self._statusVariables['odmr_meas_step'] = self.odmr_meas_step
        self._statusVariables['odmr_meas_power'] = self.odmr_meas_power


        # Microwave measurment parameters:
        self._statusVariables['mw_cw_freq'] = self.mw_cw_freq
        self._statusVariables['mw_cw_power'] = self.mw_cw_power
        self._statusVariables['mw_on_odmr_peak'] = self.mw_on_odmr_peak

        # Gated counter parameter
        self._statusVariables['gc_number_of_samples'] = self.gc_number_of_samples
        self._statusVariables['gc_samples_per_readout'] = self.gc_samples_per_readout


    def initialize_x_axis(self):
        """ Initialize the x axis. """

        stop = self.x_axis_start + self.x_axis_step*self.x_axis_num_points
        self.x_axis_list = np.arange(self.x_axis_start, stop+(self.x_axis_step/2), self.x_axis_step)
        self.current_meas_point = self.x_axis_start

    def initialize_y_axis(self):
        """ Initialize the y axis. """

        self.y_axis_list = np.zeros(self.x_axis_list.shape)     # y axis where current data are stored
        self.y_axis_fit_list = np.zeros(self.x_axis_list.shape) # y axis where fit is stored.

        # here all consequutive measurements are saved, where the
        # self.num_of_meas_runs determines the measurement index for the row.
        self.y_axis_matrix = np.zeros((1, len(self.x_axis_list)))

        # here all the measurement parameters per measurement point are stored:
        self.parameter_matrix = np.zeros((1, len(self.x_axis_list)), dtype=object)

    def initialize_meas_param(self):
        """ Initialize the measurement param containter. """
        # here all measurement parameters will be included for any kind of
        # nuclear measurement.
        self._meas_param = OrderedDict()

    def start_nuclear_meas(self, continue_meas=False):
        """ Start the nuclear operation measurement. """

        self._stop_requested = False

        if not continue_meas:
            # prepare here everything for a measurement and go to the measurement
            # loop.
            self.prepare_measurement_protocols(self.current_meas_asset_name)

            self.initialize_x_axis()
            self.initialize_y_axis()

            self.current_meas_index = 0
            self.sigCurrMeasPointUpdated.emit()
            self.num_of_current_meas_runs = 0

            self.measured_odmr_list = []

            self.elapsed_time = 0
            self.start_time = datetime.datetime.now()
            self.next_optimize_time = 0

        # load the measurement sequence:
        self._load_measurement_seq(self.current_meas_asset_name)
        self._pulser_on()
        self.set_mw_on_odmr_freq(self.mw_cw_freq, self.mw_cw_power)
        self.mw_on()

        self.lock()

        self.sigMeasStarted.emit()
        self.sigNextMeasPoint.emit()

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
                self.sigCurrMeasPointUpdated.emit()
                self.sigMeasurementStopped.emit()
                return

        # if self._optimize_now:

        self.elapsed_time = (datetime.datetime.now() - self.start_time).total_seconds()

        if self.next_optimize_time < self.elapsed_time:
            current_meas_asset = self.current_meas_asset_name
            self.mw_off()

            # perform  optimize position:
            self._load_laser_on()
            self._pulser_on()
            self.do_optimize_pos()

            # perform odmr measurement:
            self._load_pulsed_odmr()
            self._pulser_on()
            self.do_optimize_odmr_freq()

            # use the new measured frequencies for the microwave:

            if self.mw_on_odmr_peak == 1:
                self.mw_cw_freq = self.odmr_meas_freq0
            elif self.mw_on_odmr_peak == 2:
                self.mw_cw_freq = self.odmr_meas_freq1
            elif self.mw_on_odmr_peak == 3:
                self.mw_cw_freq = self.odmr_meas_freq2
            else:
                self.log.error('The maximum number of odmr can only be 3, '
                            'therfore only the peaks with number 0, 1 or 2 can '
                            'be selected but an number of "{0}" was set. '
                            'Measurement stopped!'.format(self.mw_on_odmr_peak))
                self.stop_nuclear_meas()
                self.sigNextMeasPoint.emit()
                return

            self.set_mw_on_odmr_freq(self.mw_cw_freq, self.mw_cw_power)
            # establish the previous measurement conditions
            self.mw_on()
            self._load_measurement_seq(current_meas_asset)
            self._pulser_on()

            self.elapsed_time = (datetime.datetime.now() - self.start_time).total_seconds()
            self.next_optimize_time = self.elapsed_time + self.optimize_period_odmr

        # if stop request was done already here, do not perform the current
        # measurement but jump to the switch off procedure at the top of this
        # method.
        if self._stop_requested:
            self.sigNextMeasPoint.emit()
            return

        # this routine will return a desired measurement value and the
        # measurement parameters, which belong to it.
        curr_meas_points, meas_param = self._get_meas_point(self.current_meas_asset_name)

        # this routine will handle the saving and storing of the measurement
        # results:
        self._set_meas_point(num_of_meas_runs=self.num_of_current_meas_runs,
                             meas_index=self.current_meas_index,
                             meas_points=curr_meas_points,
                             meas_param=meas_param)


        if self._stop_requested:
            self.sigNextMeasPoint.emit()
            return

        # increment the measurement index or set it back to zero if it exceed
        # the maximal number of x axis measurement points. The measurement index
        # will be used for the next measurement
        if self.current_meas_index + 1 >= len(self.x_axis_list):
            self.current_meas_index = 0

            # If the next measurement run begins, add a new matrix line to the
            # self.y_axis_matrix
            self.num_of_current_meas_runs += 1

            new_row = np.zeros(len(self.x_axis_list))

            # that vertical stack command behaves similar to the append method
            # in python lists, where the new_row will be appended to the matrix:
            self.y_axis_matrix = np.vstack((self.y_axis_matrix, new_row))
            self.parameter_matrix = np.vstack((self.parameter_matrix, new_row))

        else:
            self.current_meas_index += 1



        # check if measurement is at the end, and if not, adjust the measurement
        # sequence to the next measurement point.
        if self.num_of_current_meas_runs < self.num_of_meas_runs:

            # take the next measurement index from the x axis as the current
            # measurement point:
            self.current_meas_point = self.x_axis_list[self.current_meas_index]

            # adjust the measurement protocol with the new current_meas_point
            self.adjust_measurement(self.current_meas_asset_name)
            self._load_measurement_seq(self.current_meas_asset_name)
        else:
            self.stop_nuclear_meas()

        self.sigNextMeasPoint.emit()

    def _set_meas_point(self, num_of_meas_runs, meas_index,  meas_points, meas_param):
        """ Handle the proper setting of the current meas_point and store all
            the additional measurement parameter.

        @param int meas_index:
        @param int num_of_meas_runs
        @param float meas_points:
        @param meas_param:
        @return:
        """

        # one matrix contains all the measured values, the other one contains
        # all the parameters for the specified measurement point:
        self.y_axis_matrix[num_of_meas_runs, meas_index] = meas_points
        self.parameter_matrix[num_of_meas_runs, meas_index] = meas_param

        # the y_axis_list contains the summed and averaged values for each
        # measurement index:
        self.y_axis_list[meas_index] = self.y_axis_matrix[:, meas_index].mean()

        self.sigCurrMeasPointUpdated.emit()

    def _get_meas_point(self, meas_type):
        """ Start the actual measurement (most probably with the gated counter)

        And perform the measurement with that routine.
        @return tuple (float, dict):
        """

        # save also the count trace of the gated counter after the measurement.
        # here the actual measurement is going to be started and stoped and
        # then analyzed and outputted in a proper format.

        # Check whether proper mode is active and if not activated that:
        if self._gc_logic.get_counting_mode() != 'finite-gated':
            self._gc_logic.set_counting_mode(mode='finite-gated')

        self._gc_logic.set_count_length(self.gc_number_of_samples)
        self._gc_logic.set_counting_samples(self.gc_samples_per_readout)
        self._gc_logic.startCount()
        time.sleep(2)

        # wait until the gated counter is done or available to start:
        while self._gc_logic.getState() != 'idle' and not self._stop_requested:
            # print('in SSR measure')
            time.sleep(1)

        # for safety reasons, stop also the counter if it is still running:
        # self._gc_logic.stopCount()

        name_tag = '{0}_{1}'.format(self.current_meas_asset_name, self.current_meas_point)
        self._gc_logic.save_current_count_trace(name_tag=name_tag)

        if meas_type in ['Nuclear_Rabi', 'Nuclear_Frequency_Scan']:


            entry_indices = np.where(self._gc_logic.countdata>50)
            trunc_countdata = self._gc_logic.countdata[entry_indices]

            flip_prop, param = self._trace_ana_logic.analyze_flip_prob(trunc_countdata)

        elif meas_type in ['QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID',
                           'QSD_-_Entanglement_FID']:
            # do something measurement specific
            pass

        return flip_prop, param


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
        return ['Nuclear_Rabi', 'Nuclear_Frequency_Scan',
                'QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID',
                'QSD_-_Entanglement_FID']

    def get_available_odmr_peaks(self):
        """ Retrieve the information on which odmr peak the microwave can be
            applied.

        @return list: with string entries denoting the peak number
        """
        return [1, 2, 3]

    def prepare_measurement_protocols(self, meas_type):
        """ Prepare and create all measurement protocols for the specified
            measurement type

        @param str meas_type: a measurement type from the list get_meas_type_list
        """

        self._create_laser_on()
        self._create_pulsed_odmr()

        #FIXME: Move this creation routine to the tasks!

        if meas_type == 'Nuclear_Rabi':

            # generate:
            self._seq_gen_logic.generate_nuclear_meas_seq(name=meas_type,
                                                          rf_length_ns=self.current_meas_point*1e9,
                                                          rf_freq_MHz=self.pulser_rf_freq0/1e6,
                                                          rf_amp_V=self.pulser_rf_amp0,
                                                          rf_channel=self.pulser_rf_ch,
                                                          mw_freq_MHz=self.pulser_mw_freq/1e6,
                                                          mw_amp_V=self.pulser_mw_amp,
                                                          mw_rabi_period_ns=self.electron_rabi_periode*1e9,
                                                          mw_channel=self.pulser_mw_ch,
                                                          laser_time_ns=self.pulser_laser_length*1e9,
                                                          laser_channel=self.pulser_laser_ch,
                                                          laser_amp_V=self.pulser_laser_amp,
                                                          detect_channel=self.pulser_detect_ch,
                                                          wait_time_ns=self.pulser_idle_time*1e9,
                                                          num_singleshot_readout=self.num_singleshot_readout)
            # sample:
            self._seq_gen_logic.sample_pulse_sequence(sequence_name=meas_type,
                                                      write_to_file=True,
                                                      chunkwise=False)
            # upload:
            self._seq_gen_logic.upload_sequence(seq_name=meas_type)

        elif meas_type == 'Nuclear_Frequency_Scan':
            # generate:
            self._seq_gen_logic.generate_nuclear_meas_seq(name=meas_type,
                                                          rf_length_ns=(self.nuclear_rabi_period0*1e9)/2,
                                                          rf_freq_MHz=self.current_meas_point/1e6,
                                                          rf_amp_V=self.pulser_rf_amp0,
                                                          rf_channel=self.pulser_rf_ch,
                                                          mw_freq_MHz=self.pulser_mw_freq/1e6,
                                                          mw_amp_V=self.pulser_mw_amp,
                                                          mw_rabi_period_ns=self.electron_rabi_periode*1e9,
                                                          mw_channel=self.pulser_mw_ch,
                                                          laser_time_ns=self.pulser_laser_length*1e9,
                                                          laser_channel=self.pulser_laser_ch,
                                                          laser_amp_V=self.pulser_laser_amp,
                                                          detect_channel=self.pulser_detect_ch,
                                                          wait_time_ns=self.pulser_idle_time*1e9,
                                                          num_singleshot_readout=self.num_singleshot_readout)
            # sample:
            self._seq_gen_logic.sample_pulse_sequence(sequence_name=meas_type,
                                                      write_to_file=True,
                                                      chunkwise=False)
            # upload:
            self._seq_gen_logic.upload_sequence(seq_name=meas_type)

        elif meas_type == 'QSD_-_Artificial_Drive':
            pass

        elif meas_type == 'QSD_-_SWAP_FID':
            pass

        elif meas_type == 'QSD_-_Entanglement_FID':
            pass

    def adjust_measurement(self, meas_type):
        """ Adjust the measurement sequence for the next measurement point.

        @param meas_type:
        @return:
        """

        if meas_type == 'Nuclear_Rabi':
            # only the rf asset has to be regenerated since that is the only
            # thing what has changed.
            # You just have to ensure that the RF pulse in the sequence
            # Nuclear_Rabi is called exactly like this RF pulse:

            # generate the new pulse (which will overwrite the Ensemble)
            self._seq_gen_logic.generate_rf_pulse_ens(name='RF_pulse',
                                                      rf_length_ns=(self.current_meas_point*1e9)/2,
                                                      rf_freq_MHz=self.pulser_rf_freq0/1e6,
                                                      rf_amp_V=self.pulser_rf_amp0,
                                                      rf_channel=self.pulser_rf_ch)

            # sample the ensemble (and maybe save it to file, which will
            # overwrite the old one):
            self._seq_gen_logic.sample_pulse_block_ensemble(ensemble_name='RF_pulse',
                                                            write_to_file=True,
                                                            chunkwise=False)

            # upload the new sampled file to the device:
            self._seq_gen_logic.upload_asset(asset_name='RF_pulse')

        elif meas_type == 'Nuclear_Frequency_Scan':

            # generate the new pulse (which will overwrite the Ensemble)
            self._seq_gen_logic.generate_rf_pulse_ens(name='RF_pulse',
                                                      rf_length_ns=(self.nuclear_rabi_period0*1e9)/2,
                                                      rf_freq_MHz=self.current_meas_point/1e6,
                                                      rf_amp_V=self.pulser_rf_amp0,
                                                      rf_channel=self.pulser_rf_ch)

            # sample the ensemble (and maybe save it to file, which will
            # overwrite the old one):
            self._seq_gen_logic.sample_pulse_block_ensemble(ensemble_name='RF_pulse',
                                                            write_to_file=True,
                                                            chunkwise=False)

            # upload the new sampled file to the device:
            self._seq_gen_logic.upload_asset(asset_name='RF_pulse')

        elif meas_type == 'QSD_-_Artificial Drive':
            pass

        elif meas_type == 'QSD_-_SWAP_FID':
            pass

        elif meas_type == 'QSD_-_Entanglement_FID':
            pass

    def _load_measurement_seq(self, meas_seq):
        """ Load the current measurement sequence in the pulser

        @param str meas_seq: the measurement sequence which should be loaded
                             into the device.

        @return:
        """
        # now load the measurement sequence again on the device, which will
        # load the uploaded pulse instead of the old one:
        self._seq_gen_logic.load_asset(asset_name=meas_seq)

    def _create_laser_on(self):
        """ Create the laser asset.

        @return:
        """
        #FIXME: Move this creation routine to the tasks!
        # generate:
        self._seq_gen_logic.generate_laser_on(name='Laser_On',
                                              laser_time_bins=3000,
                                              laser_channel=self.pulser_laser_ch)

        # sample:
        self._seq_gen_logic.sample_pulse_block_ensemble(ensemble_name='Laser_On',
                                                        write_to_file=True,
                                                        chunkwise=False)

        # upload:
        self._seq_gen_logic.upload_asset(asset_name='Laser_On')

    def _load_laser_on(self):
        """ Load the laser on asset into the pulser.

        @return:
        """
        #FIXME: Move this creation routine to the tasks!

        self._seq_gen_logic.load_asset(asset_name='Laser_On')

    def _pulser_on(self):
        """ Switch on the pulser output. """

        self._set_channel_activation(active=True, apply_to_device=True)
        self._seq_gen_logic.pulser_on()

    def _pulser_off(self):
        """ Switch off the pulser output. """

        self._set_channel_activation(active=False, apply_to_device=False)
        self._seq_gen_logic.pulser_off()

    def _set_channel_activation(self, active=True, apply_to_device=False):
        """ Set the channels according to the current activation config to be either active or not.

        @param bool active: the activation according to the current activation
                            config will be checked and if channel
                            is not active and active=True, then channel will be
                            activated. Otherwise if channel is active and
                            active=False channel will be deactivated.
                            All other channels, which are not in activation
                            config will be deactivated if they are not already
                            deactivated.
        @param bool apply_to_device: Apply the activation or deactivation of the
                                     current activation_config either to the
                                     device and the viewboxes, or just to the
                                     viewboxes.
        """

        pulser_const = self._seq_gen_logic.get_hardware_constraints()

        curr_config_name = self._seq_gen_logic.current_activation_config_name
        activation_config = pulser_const['activation_config'][curr_config_name]

        # here is the current activation pattern of the pulse device:
        active_ch = self._seq_gen_logic.get_active_channels()

        ch_to_change = {} # create something like  a_ch = {1:True, 2:True} to switch

        # check whether the correct channels are already active, and if not
        # correct for that and activate and deactivate the appropriate ones:
        available_ch = self._get_available_ch()
        for ch_name in available_ch:

            # if the channel is in the activation, check whether it is active:
            if ch_name in activation_config:

                if apply_to_device:
                    # if channel is not active but activation is needed (active=True),
                    # then add that to ch_to_change to change the state of the channels:
                    if not active_ch[ch_name] and active:
                        ch_to_change[ch_name] = active

                    # if channel is active but deactivation is needed (active=False),
                    # then add that to ch_to_change to change the state of the channels:
                    if active_ch[ch_name] and not active:
                        ch_to_change[ch_name] = active


            else:
                # all other channel which are active should be deactivated:
                if active_ch[ch_name]:
                    ch_to_change[ch_name] = False

        self._seq_gen_logic.set_active_channels(ch_to_change)

    def _get_available_ch(self):
        """ Helper method to get a list of all available channels.

        @return list: entries are the generic string names of the channels.
        """
        config = self._seq_gen_logic.get_hardware_constraints()['activation_config']

        available_ch = []
        all_a_ch = []
        all_d_ch = []
        for conf in config:

            # extract all analog channels from the config
            curr_a_ch = [entry for entry in config[conf] if 'a_ch' in entry]
            curr_d_ch = [entry for entry in config[conf] if 'd_ch' in entry]

            # append all new analog channels to a temporary array
            for a_ch in curr_a_ch:
                if a_ch not in all_a_ch:
                    all_a_ch.append(a_ch)

            # append all new digital channels to a temporary array
            for d_ch in curr_d_ch:
                if d_ch not in all_d_ch:
                    all_d_ch.append(d_ch)

        all_a_ch.sort()
        all_d_ch.sort()
        available_ch.extend(all_a_ch)
        available_ch.extend(all_d_ch)

        return available_ch

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
        """ Create the pulsed ODMR asset. """
        #FIXME: Move this creation routine to the tasks!
        # generate:
        self._seq_gen_logic.generate_pulsedodmr(name='PulsedODMR',
                                                mw_time_ns=(self.electron_rabi_periode*1e9)/2,
                                                mw_freq_MHz=self.pulser_mw_freq/1e6,
                                                mw_amp_V=self.pulser_mw_amp,
                                                mw_channel=self.pulser_mw_ch,
                                                laser_time_ns=self.pulser_laser_length*1e9,
                                                laser_channel=self.pulser_laser_ch,
                                                laser_amp_V=self.pulser_laser_amp,
                                                wait_time_ns=self.pulser_idle_time*1e9)

        # sample:
        self._seq_gen_logic.sample_pulse_block_ensemble(ensemble_name='PulsedODMR',
                                                        write_to_file=True,
                                                        chunkwise=False)

        # upload:
        self._seq_gen_logic.upload_asset(asset_name='PulsedODMR')

    def _load_pulsed_odmr(self):
        """ Load a pulsed ODMR asset. """
        #FIXME: Move this creation routine to the tasks!

        self._seq_gen_logic.load_asset(asset_name='PulsedODMR')

    def do_optimize_odmr_freq(self):
        """ Perform an ODMR measurement. """
        #FIXME: Move this creation routine to the tasks!

        # make the odmr around the peak which is used for the mw drive:

        if self.mw_on_odmr_peak == 0:
            center_freq = self.odmr_meas_freq0
        if self.mw_on_odmr_peak == 1:
            center_freq = self.odmr_meas_freq1
        if self.mw_on_odmr_peak == 2:
            center_freq = self.odmr_meas_freq2

        start_freq = center_freq - self.odmr_meas_freq_range/2
        stop_freq = center_freq + self.odmr_meas_freq_range/2

        name_tag = 'odmr_meas_for_nuclear_ops'

        param = self._odmr_logic.perform_odmr_measurement(freq_start=start_freq,
                                                          freq_step=self.odmr_meas_step,
                                                          freq_stop=stop_freq,
                                                          power=self.odmr_meas_power,
                                                          runtime=self.odmr_meas_runtime,
                                                          fit_function='N14',
                                                          save_after_meas=True,
                                                          name_tag=name_tag)

        self.odmr_meas_freq0 = param['Freq. 0']['value']
        self.odmr_meas_freq1 = param['Freq. 1']['value']
        self.odmr_meas_freq2 = param['Freq. 2']['value']

        curr_time = (datetime.datetime.now() - self.start_time).total_seconds()

        self.measured_odmr_list.append([curr_time,
                                        self.odmr_meas_freq0,
                                        self.odmr_meas_freq1,
                                        self.odmr_meas_freq2])

        while self._odmr_logic.getState() != 'idle' and not self._stop_requested:
            time.sleep(0.5)

    def mw_on(self):
        """ Start the microwave device. """
        self._odmr_logic.MW_on()

    def mw_off(self):
        """ Stop the microwave device. """
        self._odmr_logic.MW_off()

    def set_mw_on_odmr_freq(self, freq, power):
        """ Set the microwave on a the specified freq with the specified power. """

        self._odmr_logic.set_frequency(freq)
        self._odmr_logic.set_power(power)

    def save_nuclear_operation_measurement(self, name_tag=None, timestamp=None):
        """ Save the nuclear operation data.

        @param str name_tag:
        @param object timestamp: datetime.datetime object, from which everything
                                 can be created.
        """

        filepath = self._save_logic.get_path_for_module(module_name='NuclearOperations')

        if timestamp is None:
            timestamp = datetime.datetime.now()

        if name_tag is not None and len(name_tag) > 0:
            filelabel1 = name_tag + '_nuclear_ops_xy_data'
            filelabel2 = name_tag + '_nuclear_ops_data_y_matrix'
            filelabel3 = name_tag + '_nuclear_ops_add_data_matrix'
            filelabel4 = name_tag + '_nuclear_ops_odmr_data'
        else:
            filelabel1 = '_nuclear_ops_data'
            filelabel2 = '_nuclear_ops_data_matrix'
            filelabel3 = '_nuclear_ops_add_data_matrix'
            filelabel4 = '_nuclear_ops_odmr_data'

        param = OrderedDict()
        param['Electron Rabi Period (ns)'] = self.electron_rabi_periode*1e9
        param['Pulser Microwave Frequency (MHz)'] = self.pulser_mw_freq/1e6
        param['Pulser MW amp (V)'] = self.pulser_mw_amp
        param['Pulser MW channel'] = self.pulser_mw_ch
        param['Nuclear Rabi period Trans 0 (micro-s)'] = self.nuclear_rabi_period0*1e6
        param['Nuclear Trans freq 0 (MHz)'] = self.pulser_rf_freq0/1e6
        param['Pulser RF amp 0 (V)'] = self.pulser_rf_amp0
        param['Nuclear Rabi period Trans 1 (micro-s)'] = self.nuclear_rabi_period1*1e6
        param['Nuclear Trans freq 1 (MHz)'] = self.pulser_rf_freq1/1e6
        param['Pulser RF amp 1 (V)'] = self.pulser_rf_amp1
        param['Pulser Rf channel'] = self.pulser_rf_ch
        param['Pulser Laser length (ns)'] = self.pulser_laser_length*1e9
        param['Pulser Laser amp (V)'] = self.pulser_laser_amp
        param['Pulser Laser channel'] = self.pulser_laser_ch
        param['Number of single shot readouts per pulse'] = self.num_singleshot_readout
        param['Pulser idle Time (ns)'] = self.pulser_idle_time*1e9
        param['Pulser Detect channel'] = self.pulser_detect_ch

        data1 = OrderedDict()
        data2 = OrderedDict()
        data3 = OrderedDict()
        data4 = OrderedDict()

        # Measurement Parameter:
        param[''] = self.current_meas_asset_name
        if self.current_meas_asset_name in ['Nuclear_Frequency_Scan']:
            param['x axis start (MHz)'] = self.x_axis_start/1e6
            param['x axis step (MHz)'] = self.x_axis_step/1e6
            param['Current '] = self.current_meas_point/1e6

            data1['RF pulse frequency (MHz)'] = self.x_axis_list
            data1['Flip Probability'] = self.y_axis_list

            data2['RF pulse frequency matrix (MHz)'] = self.y_axis_matrix

        elif self.current_meas_asset_name in ['Nuclear_Rabi','QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID','QSD_-_Entanglement_FID']:
            param['x axis start (micro-s)'] = self.x_axis_start*1e6
            param['x axis step (micro-s)'] = self.x_axis_step*1e6
            param['Current '] = self.current_meas_point*1e6

            data1['RF pulse length (micro-s)'] = self.x_axis_list
            data1['Flip Probability'] = self.y_axis_list

            data2['RF pulse length matrix (micro-s)'] = self.y_axis_matrix

        else:
            param['x axis start'] = self.x_axis_start
            param['x axis step'] = self.x_axis_step
            param['Current '] = self.current_meas_point

            data1['x axis'] = self.x_axis_list
            data1['y axis'] = self.y_axis_list

            data2['y axis matrix)'] = self.y_axis_matrix

        data3['Additional Data Matrix'] = self.parameter_matrix
        data4['Measured ODMR Data Matrix'] = np.array(self.measured_odmr_list)

        param['Number of expected measurement points per run'] = self.x_axis_num_points
        param['Number of expected measurement runs'] = self.num_of_meas_runs
        param['Number of current measurement runs'] = self.num_of_current_meas_runs

        param['Current measurement index'] = self.current_meas_index
        param['Optimize Period ODMR (s)'] = self.optimize_period_odmr
        param['Optimize Period Confocal (s)'] = self.optimize_period_confocal

        param['current ODMR trans freq0 (MHz)'] = self.odmr_meas_freq0/1e6
        param['current ODMR trans freq1 (MHz)'] = self.odmr_meas_freq1/1e6
        param['current ODMR trans freq2 (MHz)'] = self.odmr_meas_freq2/1e6
        param['Runtime of ODMR optimization (s)'] = self.odmr_meas_runtime
        param['Frequency Range ODMR optimization (MHz)'] = self.odmr_meas_freq_range/1e6
        param['Frequency Step ODMR optimization (MHz)'] = self.odmr_meas_step/1e6
        param['Power of ODMR optimization (dBm)'] = self.odmr_meas_power

        param['Selected ODMR trans freq (MHz)'] = self.mw_cw_freq/1e6
        param['Selected ODMR trans power (dBm)'] = self.mw_cw_power
        param['Selected ODMR trans Peak'] = self.mw_on_odmr_peak

        param['Number of samples in the gated counter'] = self.gc_number_of_samples
        param['Number of samples per readout'] = self.gc_samples_per_readout

        param['Elapsed Time (s)'] = self.elapsed_time
        param['Start of measurement'] = self.start_time.strftime('%Y-%m-%d %H:%M:%S')

        self._save_logic.save_data(data1,
                                   filepath,
                                   parameters=param,
                                   filelabel=filelabel1,
                                   timestamp=timestamp,
                                   as_text=True)

        self._save_logic.save_data(data2,
                                   filepath,
                                   filelabel=filelabel2,
                                   timestamp=timestamp,
                                   as_text=True)

        self._save_logic.save_data(data4,
                                   filepath,
                                   filelabel=filelabel4,
                                   timestamp=timestamp,
                                   as_text=True)

        # self._save_logic.save_data(data3,
        #                            filepath,
        #                            filelabel=filelabel3,
        #                            timestamp=timestamp,
        #                            as_text=True)

        self.log.info('Nuclear Operation data saved to:\n{0}'.format(filepath))

