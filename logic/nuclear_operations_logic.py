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
from pyqtgraph.Qt import QtCore
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
           'gatedcounterlogic': 'CounterLogic',
           'odmrlogic': 'ODMRLogic',
           'optimizerlogic': 'OptimizerLogic',
           'scannerlogic':'ScannerLogic',
           'savelogic': 'SaveLogic'}

    _out = {'nuclearoperationlogic': 'NuclearOperationsLogic'}

    sigNextMeasPoint = QtCore.Signal()
    sigCurrMeasPointUpdated = QtCore.Signal()
    sigMeasValueUpdated = QtCore.Signal()

    sigMeasStarted = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))



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


        # choose default values:
        self.x_axis_start = 1e-3                    # in s
        self.x_axis_step = 10e-3                     # in s
        self.x_axis_num_points = 50



        self.current_meas_point = self.x_axis_start
        self.current_meas_index = 0
        self.num_of_current_meas_runs = 0
        self.num_of_meas_runs   = 1 # How often the measurement should be repeated.
        self.elapsed_time = 0
        self.start_time = 0
        self.optimize_period = 200
        self.next_optimize_time = self.start_time


        self._stop_requested = False

        self.mw_cw_freq = 10e9                      # in Hz
        self.mw_power = -30                         # in dBm

        # parameters for pulsed ODMR:
        self.odmr_meas_freq0 = 10000e6              # in Hz
        self.odmr_meas_freq1 = 10002.1e6            # in Hz
        self.odmr_meas_freq2 = 10004.2e6            # in Hz
        self.odmr_meas_runtime = 30             # in s
        self.odmr_meas_freq_range = 30e6            # in Hz
        self.odmr_meas_step = 0.15e6                # in Hz
        self.odmr_meas_power = -30                  # in dBm
        self.odmr_time_for_next_optimize = 300      # in s

        self.electron_rabi_periode = 1800e-9        # in s



        # store here all the measured odmr peaks
        self.measured_odmr_list = []

        # on which odmr peak the manipulation is going to be applied:
        self.mw_on_odmr_peak = 1

        # laser options:
        self.pulser_laser_ch = 1
        self.pulser_laser_amp = 1       # in V
        self.pulser_laser_length = 3e-6 # in s
        self.pulser_mw_ch = -1
        self.pulser_mw_freq = 200e6     # in Hz
        self.pulser_mw_amp = 2.25          # in V
        self.pulser_idle_time = 1.5e-6  # in s
        self.pulser_rf_ch = -2
        self.pulser_rf_amp = 0.1

        self.pulser_detect_ch = 1

        self.nuclear_rabi_period = 30e-6
        self.pulser_rf_freq0 = 6.32e6   # in Hz

        self.num_singleshot_readout = 3000

        self.gc_number_of_samples = 3000    # in counts
        self.gc_samples_per_readout = 50    # in counts

        # self.rf_length_measure_point = 10e-6
        # self.rf_freq_measure_point =

        self._optimize_now = False

        self.initialize_x_axis()
        self.initialize_y_axis()
        self.initialize_meas_param()

        self.current_meas_asset_name = ''

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

        # here all consequutive measurements are saved, where the
        # self.num_of_meas_runs determines the measurement index for the row.
        self.y_axis_matrix = np.zeros(1, len(self.x_axis_list))

        # here all the measurement parameters per measurement point are stored:
        self.parameter_matrix = np.zeros(1, len(self.x_axis_list), dtype=object)

    def initialize_meas_param(self):
        """ Initialize the measurement param containter. """
        # here all measurement parameters will be included for any kind of
        # nuclear measurement.
        self._meas_param = OrderedDict()


    def start_nuclear_meas(self, continue_meas=False):
        """ Start the nuclear operation measurement. """

        if not continue_meas:
            # prepare here everything for a measurement and go to the measurement
            # loop.
            self.prepare_measurement_protocols()

            self.initialize_x_axis()
            self.initialize_y_axis()

        # load the measurement sequence:
        self._load_measurement_seq(self.current_meas_asset_name)
        self._pulser_on()
        self.set_mw_on_odmr_freq(self.mw_cw_freq, self.mw_power)
        self.mw_on()

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
                self.sigMeasValueUpdated.emit()
                return

        if self._optimize_now:
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

            if self.mw_on_odmr_peak == 0:
                self.mw_cw_freq = self.odmr_meas_freq0
            elif self.mw_on_odmr_peak == 1:
                self.mw_cw_freq = self.odmr_meas_freq1
            elif self.mw_on_odmr_peak == 2:
                self.mw_cw_freq = self.odmr_meas_freq2
            else:
                self.log.error('The maximum number of odmr can only be 3, '
                        'therfore only the peaks with number 0, 1 or 2 can '
                        'be selected but an number of "{0}" was set. '
                        'Measurement stopped!'.format(self.mw_on_odmr_peak))
                self.stop_nuclear_meas()
                self.sigNextMeasPoint.emit()
                return

            self.set_mw_on_odmr_freq(self.mw_cw_freq, self.mw_power)
            # establish the previous measurement conditions
            self.mw_on()
            self._load_measurement_seq(current_meas_asset)
            self._pulser_on()

        # if stop request was done already here, do not perform the current
        # measurement but jump to the switch off procedure at the top of this
        # method.
        if self._stop_requested:
            self.sigNextMeasPoint.emit()
            return

        # this routine will return a desired measurement value and the
        # measurement parameters, which belong to it.
        curr_meas_points, meas_param = self._get_meas_point()

        # this routine will handle the saving and storing of the measurement
        # results:
        self._set_meas_point(self.current_meas_index, self.num_of_current_meas_runs, curr_meas_points, meas_param)

        # increment the measurement index or set it back to zero if it exceed
        # the maximal number of x axis measurement points. The measurement index
        # will be used for the next measurement
        if self.current_meas_index + 1 > self.x_axis_num_points:
            self.current_meas_index = 0

            # If the next measurement run begins, add a new matrix line to the
            # self.y_axis_matrix
            self.num_of_current_meas_runs += 1

            new_row = np.zeros(self.x_axis_num_points)

            # that vertical stack command behaves similar to the append method
            # in python lists, where the new_row will be appended to the matrix:
            self.y_axis_matrix = np.vstack((self.y_axis_matrix, new_row))
            self.parameter_matrix = np.vstack((self.parameter_matrix, new_row))

        else:
            self.current_meas_index += 1

        if self.num_of_current_meas_runs < self.num_of_meas_runs:

            # take the next measurement index from the x axis as the current
            # measurement point:
            self.current_meas_point = self.x_axis_list[self.current_meas_index]

            # adjust the measurement protocol with the new current_meas_point
            self.adjust_measurement(self.current_meas_asset_name)
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

        self._gc_logic.set_counting_mode(mode='gated')
        self._gc_logic.set_count_length()
        self._gc_logic.set_counting_samples(self.gc_number_of_samples)
        self._gc_logic.startCount()

        # wait until the gated counter is done or available to start:
        while self._counter_logic.getState() == 'locked' or not self._stop_requested:
            time.sleep(1)

        name_tag = '{0}_{1}'.format(self.current_meas_asset_name, self.current_meas_point)
        self._gc_logic.save_current_count_trace(name_tag=name_tag)

        if meas_type in ['Nuclear_Rabi', 'Nuclear_Frequency_Scan']:
            flip_prop, param = self._trace_ana_logic.analyze_flip_prob(self._gc_logic.countdata)
            # flip_prop = [flip_prop]
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
                                                          rf_freq_MHz=self.pulser_rf_freq0,
                                                          rf_amp_V=self.pulser_rf_amp,
                                                          rf_channel=self.pulser_rf_ch,
                                                          mw_freq_MHz=self.pulser_mw_freq,
                                                          mw_amp_V=self.pulser_mw_amp,
                                                          mw_rabi_period_ns=self.electron_rabi_periode*1e9,
                                                          mw_channel=self.pulser_mw_ch,
                                                          laser_time_ns=self.pulser_laser_length*1e9,
                                                          laser_channel=self.pulser_laser_ch,
                                                          laser_amp_V=self.pulser_laser_amp,
                                                          detect_channel=self.pulser_detect_ch,
                                                          wait_time_ns=self.pulser_idle_time,
                                                          num_singleshot_readout=self.num_singleshot_readout)
            # sample:
            self._seq_gen_logic.sample_pulse_sequence(ensemble_name=meas_type,
                                                      write_to_file=True,
                                                      chunkwise=False)
            # upload:
            self._seq_gen_logic.upload_asset(asset_name=meas_type)

        elif meas_type == 'Nuclear_Frequency_Scan':
            # generate:
            self._seq_gen_logic.generate_nuclear_meas_seq(name=meas_type,
                                                          rf_length_ns=(self.nuclear_rabi_period*1e9)/2,
                                                          rf_freq_MHz=self.current_meas_point*1e-6,
                                                          rf_amp_V=self.pulser_rf_amp,
                                                          rf_channel=self.pulser_rf_ch,
                                                          mw_freq_MHz=self.pulser_mw_freq,
                                                          mw_amp_V=self.pulser_mw_amp,
                                                          mw_rabi_period_ns=self.electron_rabi_periode*1e9,
                                                          mw_channel=self.pulser_mw_ch,
                                                          laser_time_ns=self.pulser_laser_length*1e9,
                                                          laser_channel=self.pulser_laser_ch,
                                                          laser_amp_V=self.pulser_laser_amp,
                                                          detect_channel=self.pulser_detect_ch,
                                                          wait_time_ns=self.pulser_idle_time,
                                                          num_singleshot_readout=self.num_singleshot_readout)
            # sample:
            self._seq_gen_logic.sample_pulse_sequence(ensemble_name=meas_type,
                                                      write_to_file=True,
                                                      chunkwise=False)
            # upload:
            self._seq_gen_logic.upload_asset(asset_name=meas_type)

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

        if meas_type == 'Nuclear_Rabi':
            # only the rf asset has to be regenerated since that is the only
            # thing what has changed.
            # You just have to ensure that the RF pulse in the sequence
            # Nuclear_Rabi is called exactly like this RF pulse:

            # generate the new pulse (which will overwrite the Ensemble)
            self._seq_gen_logic.generate_rf_pulse_ens(name='RF_pulse',
                                                      rf_length_ns=(self.current_meas_point*1e9)/2,
                                                      rf_freq_MHz=self.pulser_rf_freq0*1e6,
                                                      rf_amp_V=self.pulser_rf_amp,
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
                                                      rf_length_ns=(self.nuclear_rabi_period*1e9)/2,
                                                      rf_freq_MHz=self.current_meas_point*1e6,
                                                      rf_amp_V=self.pulser_rf_amp,
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
        """ switch on the pulsing device.

        @return:
        """
        #FIXME: Move this creation routine to the tasks!

        config_name = self._seq_gen_logic.get_activation_config()
        config = self._seq_gen_logic.get_hardware_constraints()['activation_config'][config_name]

        active_ch = {}
        for entry in config:
            active_ch[entry] = True
        self._seq_gen_logic.set_active_channels(active_ch)
        self._seq_gen_logic.pulser_on()

    def _pulser_off(self):
        """ switch off the pulsing device.

        @return:
        """
        #FIXME: Move this creation routine to the tasks!

        self._seq_gen_logic.pulser_off()

        config_name = self._seq_gen_logic.get_activation_config()
        config = self._seq_gen_logic.get_hardware_constraints()['activation_config'][config_name]

        active_ch = {}
        for entry in config:
            active_ch[entry] = False
        self._seq_gen_logic.set_active_channels(active_ch)


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
                                                mw_freq_MHz=self.pulser_mw_freq*1e-6,
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

        self.measured_odmr_list.append([self.odmr_meas_freq0,
                                        self.odmr_meas_freq1,
                                        self.odmr_meas_freq2])


    def mw_on(self):
        """ Start the microwave device. """
        self._odmr_logic.MW_on()

    def mw_off(self):
        """ Stop the microwave device. """
        self.MW_off()

    def set_mw_on_odmr_freq(self, freq, power):
        """ Set the microwave on a the specified freq with the specified power. """

        self.set_frequency(freq)
        self.set_power(power)

