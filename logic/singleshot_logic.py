# -*- coding: utf-8 -*-
"""
This file contains the Qudi counter logic class.

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

import copy
import datetime
import numpy as np
import os
import pylab as pb
import time

from collections import OrderedDict
from core.module import Connector
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class SingleShotLogic(GenericLogic):
    """ This class brings raw data coming from fastcounter measurements (gated or ungated)
        into trace form processable by the trace_analysis_logic.
    """

    _modclass = 'SingleShotLogic'
    _modtype = 'logic'

    # declare connectors
    savelogic = Connector(interface='SaveLogic')
    fitlogic = Connector(interface='FitLogic')
    fastcounter = Connector(interface='FastCounterInterface')
    pulseextractionlogic = Connector(interface='PulseExtractionLogic')
    pulsedmeasurementlogic = Connector(interface='PulsedMeasurementLogic')
    traceanalysislogic1 = Connector(interface='TraceAnalysisLogic')
    pulsegenerator = Connector(interface='PulserInterface')
    scannerlogic = Connector(interface='ScannerLogic')
    optimizerlogic = Connector(interface='OptimizerLogic')
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')
    odmrlogic = Connector(interface='ODMRLogic')

    # add possible signals here
    sigHistogramUpdated = QtCore.Signal()
    sigMeasurementFinished = QtCore.Signal()
    sigTraceUpdated = QtCore.Signal()

    def __init__(self, config, **kwargs):
        """ Create CounterLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        # initalize internal variables here
        self.hist_data = None
        self._hist_num_bins = None

        self.data_dict = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._fast_counter_device = self.get_connector('fastcounter')
        self._pulse_generator_device = self.get_connector('pulsegenerator')
        self._save_logic = self.get_connector('savelogic')
        self._fit_logic = self.get_connector('fitlogic')
        self._traceanalysis_logic = self.get_connector('traceanalysislogic1')
        self._pe_logic = self.get_connector('pulseextractionlogic')
        self._pm_logic = self.get_connector('pulsedmeasurementlogic')
        self._odmr_logic = self.get_connector('odmrlogic')
        self._pulsed_master_logic = self.get_connector('pulsedmasterlogic')
        self._confocal_logic = self.get_connector('scannerlogic')
        self._optimizer_logic = self.get_connector('optimizerlogic')

        self.hist_data = None
        self.trace = None
        self.sigMeasurementFinished.connect(self.ssr_measurement_analysis)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        return

    # =========================================================================
    #                           Raw Data Analysis
    # =========================================================================

    def get_data(self, fastcounter='fastcomtec'):
        """
        get the singleshot data from the fastcounter along with its shape
        @param: optional string fastcounter: Determines how the data is extracted from the fastcounter
        @return: dictionary containing shape of the data as well as the raw data coming from fastcounter and
                 possible additional data to calculate dt ( the time between two singleshot measurements ) later.
        """
        return_dict = OrderedDict()

        if not self._fast_counter_device.is_gated():
            if fastcounter == 'fastcomtec':
                settings = self._fast_counter_device.get_settings()
                # check if settings object is coming from a remote connection
                settings = netobtain(settings)
                n_rows = settings.cycles
                # looks like this is in ns, but I'm not completely sure
                n_columns = settings.range
                reps_per_row = settings.swpreset
                raw_data = netobtain(self._fast_counter_device.get_data_trace(sweep_reset=True))


                return_dict['n_rows'] = n_rows
                return_dict['n_columns'] = n_columns
                return_dict['reps_per_row'] = reps_per_row
                return_dict['raw_data'] = raw_data
                # needed to internally calculate the measurement time, unless the columns are
                # always in ns ?
                return_dict['bin_width'] = self._fast_counter_device.get_binwidth()
            else:
                self.log.warning('other ungated counters are not implemented at the moment')
        else:
            self.log.warning('using gated counter not implemented yet')

        self.data_dict = return_dict

        return 0

    def find_laser(self, smoothing=10.0, n_laserpulses=2):
        """
        returns the start and stop indices of laserpulses
        @param smoothing: smoothing data to improve flank detection
        @param n_laserpulses: the number of laserpulses expected in the data
        @return: list containing tupels of start and stop values of individual laser pulses
        """

        data = self.data_dict['raw_data']
        n_rows = self.data_dict['n_rows']

        # we want to add up the pulses along the cycles axis
        shape = data.shape
        if shape[0] == n_rows:
            axis = 0
        elif shape[1] == n_rows:
            axis = 1
        else:
            self.log.debug('something went wrong in identifying the correct axis of data in find_laser '
                           'of singleshot_logic')

        summed_pulses = np.sum(data, axis)

        # TODO make the type of pulsed extraction adjustable
        self._pe_logic.number_of_lasers = n_laserpulses
        self._pe_logic.extraction_settings['conv_std_dev'] = smoothing
        return_dict = self._pe_logic.ungated_extraction_methods['conv_deriv'](summed_pulses)
        rising_ind = return_dict['laser_indices_rising']
        falling_ind = return_dict['laser_indices_falling']

        start_stop_tupel_list = []
        for jj, rising in enumerate(rising_ind):
            start_stop_tupel_list.append((rising, falling_ind[jj]))

        return start_stop_tupel_list

    def sum_laserpulse(self, smoothing=10.0, n_laserpulses=2):
        """
        First find the laserpulses, then go on to add up the individual laserpulses.
        After that the data depending on the sequence may need normalization and higher
        binwidths may be calculated ( add to gather 2 up to floor( n_rows // 2) values ).

        @param float smoothing: If pulse detection doesn't work, change this value
        @return numpy array: dimensionality is n_rows x n_laserpulses
        """
        sum_single_pulses = []
        start_stop_tupel_list = self.find_laser(smoothing=smoothing, n_laserpulses=n_laserpulses)
        if self.data_dict:
            data = self.data_dict['raw_data']
            for row in data:
                laser_pulses = [np.sum(row[jj[0]:jj[1]]) for jj in start_stop_tupel_list]
                sum_single_pulses.append(laser_pulses)
        else:
            self.log.error('Pull data from fastcounting device using get_data function before trying to sum_laserpulse.')

        return np.array(sum_single_pulses)


    def get_normalized_signal(self, smoothing=10.0):
        """
        given the raw data this function will calculate
        the normalized signal. It assumes that the pulse sequence used has
        2 laserpulses ( for normalization purposes )

        @param float smoothing: If pulse detection doesn't work, change this value
        @return numpy array: 1D array containing the normalized signal
        """

        sum_single_pulses = self.sum_laserpulse()
        if sum_single_pulses.shape[1] == 2:
            normalized_signal = np.array([(ii[0] - ii[1])/(ii[0] + ii[1]) for ii in sum_single_pulses])
        else:
            self.log.warning('could not perform normalisation. Wrong number of laserpulses.')

        return normalized_signal

    def calc_all_binnings(self, num_bins=100):
        """
        calculate reasonable binnings of the signal
        @param int num_bins: minimal number the binnings can have
        @return list bin_list: Contains the arrays with the binned data.
                               Data is structured as follows: bin_list[0] is the
                               initial binning given by the measurement and then going up.
        """

        if self.data_dict:
            data = self.data_dict
        else:
            self.log.error('Pull data from fastcounting device using get_data function '
                           'before trying to calc_all_binnings.')

        NN = data['n_rows']
        # this is just a guess value, at some point it doesn't make
        # sense anymore to further decrease the number of bins
        max_bin = NN // num_bins
        count_var = 1
        bin_list = []
        temp_list = []
        signal = self.sum_laserpulse()
        while count_var <= max_bin:
            # check if the the first run through loop was done
            if temp_list:
                app_arr = np.array(temp_list)
                bin_list.append(app_arr)
                temp_list = []
            jj = 0
            while jj < NN:
                sum_ind = np.linspace(jj, jj + count_var - 1, count_var, dtype=np.int)
                # make sure we don't try to adress not reserved memory
                jj += count_var
                if sum_ind[-1] < NN:
                    # normalize
                    temp_list.append(np.array([np.sum(signal[sum_ind, 0]), np.sum(signal[sum_ind, 1])]))
                else:
                    jj = NN
            count_var += 1

        return np.array(bin_list)

    def calc_all_binnings_normalized(self, num_bins=100):
        """
        Calculate all normalized binnings from singleshot data
        @param integer num_bins: Tells how many data points should still remain ( in this sense restricts the maximum
                                 number of data points added up together )
        @return list normalized_bin_list: The entries are numpy arrays that represent different binnings
                                          ( 1 to n values)
        """

        bin_list = self.calc_all_binnings(num_bins=num_bins)
        normalized_bin_list = []
        for binning in bin_list:
            normalized_binning = (binning[:, 0] - binning[:, 1])/(binning[:, 0] + binning[:, 1])
            normalized_bin_list.append(normalized_binning)

        return np.array(normalized_bin_list)


    def get_timetrace(self):
        """
        This function will help to find the optimal binning in the fastcomtec data,
        for now under development, as we decided for now to manually pick the right binning.
        Therefore the function visualize_bin_list is there to help with that task. It will make
        a plot of all binnings and show which shows the best features.
        @return:
        """
        # what needs to be done here now is the basic evaluation steps like fit, threshold
        # readout fidelity

        bin_list = self.calc_all_binnings(self, num_bins=100)

        param_dict_list = []
        fidelity_list = []
        for ii in bin_list:
            # what is a good estimate for the number of bins ?
            hist_y_val, hist_x_val = np.histogram(ii, bins=50)
            hist_data = np.array([hist_x_val, hist_y_val])
            threshold_fit, fidelity, \
            param_dict = self._traceanalysis_logic.calculate_threshold(hist_data=hist_data,
                                                                       distr='gaussian_normalized')
            param_dict_list.append(param_dict)
            fidelity_list.append(fidelity)

        # now get the maximum fidelity, not really working up till now. The fidelity alone is not a good indicator
        # because the fit can still be bad. Need somehow a mixed measure of this. Will look for some heuristic.

        ind = np.argmax(np.array(fidelity_list))

        timetrace = bin_list[ind]

        return timetrace
    # =========================================================================
    #                           Single Shot measurements
    # =========================================================================

    # TODO make more general for other devices
    def do_singleshot(self, mw_dict=None, refocus=True, laser_wfm='LaserOn', singleshot_wfm='SSR_normalise_2MW',
                      normalized=True):
        """
        For additional microwave usage this assumes an external signal generator. Could be also done with an
        additional pulser channel though.
        """
        use_mw = False
        if mw_dict:
            use_mw = True
            if mw_dict['freq']:
                mw_freq = mw_dict['freq']
                self._odmr_logic.set_frequency(frequency=mw_freq)
            if mw_dict['power']:
                mw_power = mw_dict['power']
                self._odmr_logic.set_power(mw_power)
        # set mw power
        # self._odmr_logic.set_power(mw_power)

        # turn on laser to refocus
        self._pulse_generator_device.load_asset(laser_wfm)
        self._pulse_generator_device.pulser_on()
        # TODO make this with queue connections
        if refocus:
            self._do_optimize_pos()
        # load sequence for SSR measurement
        self._pulse_generator_device.load_asset(singleshot_wfm)
        self._pulse_generator_device.pulser_on()

        # set mw frequency and turn it on
        if use_mw:
            self._odmr_logic.MW_on()

        self._fast_counter_device.start_measure()
        time.sleep(10)
        # try to do this differently
        tmp_var1 = self._fast_counter_device.get_status()
        while (tmp_var1 - 1):
            time.sleep(5)
            tmp_var1 = self._fast_counter_device.get_status()

        # pull data. This will also update the variable self.data_dict
        self.get_data()

        if normalized:
            bin_list = self.calc_all_binnings()
        else:
            bin_list = self.calc_all_binnings_normalized()

        return bin_list

    # I would very much like to have this function here, both in respect to the magnet logic, which will
    # need such a function for the nuclear alignment as well as for other measurements such as rf odmr and so on
    # therefore I'm going to include it here.
    # TODO include focusing on a single peak here
    # TODO refocus replaced through refocus frequency
    def do_pulsed_odmr(self, measurement_time, controlled_vals_start, controlled_vals_incr, num_of_lasers,
                       sequence_length_s, refocus=True, pulsedODMR_wfm='PulsedODMR', save_tag=''):
        """
        A function to do pulsed odmr. Important as exact transition frequencies are important.
        @param measurement_time:
        @param controlled_vals_start:
        @param controlled_vals_incr:
        @param num_of_lasers:
        @param sequence_length_s:
        @param refocus:
        @param pulsedODMR_wfm:
        @param save_tag:
        @return:
        """
        laser_ignore_list = []
        # TODO maybe this data is also differently available or units can be set within the logic
        alternating = False

        controlled_vals = np.arange(controlled_vals_start,
                                    controlled_vals_start + (controlled_vals_incr * num_of_lasers) - (
                                    controlled_vals_incr / 2),
                                    controlled_vals_incr)

        self._pulsed_master_logic.measurement_sequence_settings_changed(controlled_vals,
                                                                        num_of_lasers,
                                                                        sequence_length_s,
                                                                        laser_ignore_list,
                                                                        alternating)
        self._pm_logic._initialize_plots()

        self._pulse_generator_device.load_asset(pulsedODMR_wfm)
        self._pulsed_master_logic.start_measurement()
        if refocus:
            self._do_optimize_pos()
        time.sleep(measurement_time)
        self._pulsed_master_logic.stop_measurement()

        freqs = self._pm_logic.signal_plot_x
        signal = self._pm_logic.signal_plot_y
        # now everything is saved, lets do the fitting
        results = self._fit_logic.make_N14_fit(freqs, signal)
        freq_peaks = np.array([results.params['l0_center'].value, results.params['l1_center'].value,
                              results.params['l2_center'].value])
        if save_tag:
            controlled_val_unit = 'Hz'
            self._pulsed_master_logic.save_measurement_data(controlled_val_unit, save_tag)

        return freq_peaks


    def save_singleshot(self, tag=None, normalized=True, visualize=True):
        """
        When called this will save the attribute data_dict of class savelogic to file.
        The raw data will be postprocessed to bin lists as well as normalized bin lists
        ( containing all the possible binnings of the data. Additionally the meta_data
        will be saved.
        @return:
        """
        filepath = self._save_logic.get_path_for_module(module_name='SingleShot')
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime('%Y%m%d-%H%M-%S')
        if normalized:
            if tag is not None and len(tag) > 0:
                filelabel2 = tag + '_' + timestamp_str + '_normalized_bin_list'
            else:
                filelabel2 = timestamp_str + '_normalized_bin_list'

            normalized_bin_list = self.calc_all_binnings_normalized()
            save_path2 = os.path.join(filepath, filelabel2)
            np.save(save_path2, normalized_bin_list)
            if visualize:
                visualize_path = os.path.join(filepath, timestamp_str + '_visualize_bins')
                os.mkdir(visualize_path)
                self.visualize_bin_list(normalized_bin_list, visualize_path)

        else:
            if tag is not None and len(tag) > 0:
                filelabel1 = tag + '_' + timestamp_str + '_bin_list'
            else:
                filelabel1 = timestamp_str + '_bin_list'

            bin_list = self.calc_all_binnings()
            save_path1 = os.path.join(filepath, filelabel1)
            np.save(save_path1, bin_list)

        meta_data_dict = copy.deepcopy(self.data_dict)
        meta_data_dict.pop('raw_data')
        meta_path = os.path.join(filepath, timestamp_str + '_meta_data')
        np.save(meta_path,meta_data_dict)
        for key in meta_data_dict:
            meta_data_dict[key] = [meta_data_dict[key]]
        self._save_logic.save_data(meta_data_dict, filepath=filepath, filelabel='meta_data')


        return

    # Helper methods

    def _do_optimize_pos(self):

        curr_pos = self._confocal_logic.get_position()

        self._optimizer_logic.start_refocus(curr_pos, caller_tag='singleshot_logic')

        # check just the state of the optimizer
        while self._optimizer_logic.module_state() != 'idle':
            time.sleep(0.5)

        # use the position to move the scanner
        self._confocal_logic.set_position('magnet_logic',
                                          self._optimizer_logic.optim_pos_x,
                                          self._optimizer_logic.optim_pos_y,
                                          self._optimizer_logic.optim_pos_z)

    def visualize_bin_list(self, bin_list, path):
        """
        Will create a histogram of all bin_list entries and save it to the specified path
        """
        # TODO use savelogic here
        for jj, bin_entry in enumerate(bin_list):
            hist_x, hist_y = self._traceanalysis_logic.calculate_histogram(bin_entry, num_bins=50)
            pb.plot(hist_x[0:len(hist_y)], hist_y)
            fname = 'bin_' + str(jj) + '.png'
            savepath = os.path.join(path, fname)
            pb.savefig(savepath)
            pb.close()

    # =========================================================================
    #                           Connecting to GUI
    # =========================================================================

    # absolutely not working at the moment.

    def ssr_measurement_analysis(self, record_length):
        """
        Gets executed when a single shot measurment has finished. This function will update GUI elements
        @param record_length:
        @return:
        """
        normalized_bin_list = self.calc_all_binnings_normalized(self, num_bins=100)

        # for now take only the initial binning
        data = normalized_bin_list[0]
        measurement = self.data_dict
        # also only the initial binning, needs to be adjusted then
        time_axis = np.linspace(record_length * measurement['reps_per_row'],
                                record_length * (measurement['reps_per_row'] + 1), measurement['n_rows'])
        # update the histogram in the gui
        self.do_calculate_histogram(data)

        # update the trace in the gui
        self._do_calculate_trace(time_axis, data)



    def do_calculate_histogram(self, data):
        """ Passes all the needed parameters to the appropriated methods.

        @return:
        """
        self.hist_data = self._traceanalysis_logic.calculate_histogram(data, self._traceanalysis_logic._hist_num_bins)

        self.sigHistogramUpdated.emit()

    def do_calculate_trace(self, time_axis, data):

        self.trace = np.array([time_axis, data])
        self.sigTraceUpdated.emit()
    # # now make time trace ( usually what you get from the gated counter )
    # # with the addition of the normalisation
    # # the fidelity depends on the binning, so it may be smart to calculate
    # # the best binning here
    # self.genertte timetrace
    #
    # # now do the post processing that we want to do
    # # e.g. T1 time, readout fidelity ...
    # send to geted counter
