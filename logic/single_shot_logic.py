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

import datetime
import numpy as np
from core.util.mutex import Mutex
import time

from core.module import Connector, ConfigOption, StatusVar
from collections import OrderedDict
from core.module import Connector
from core.util import units
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import scipy.integrate as integrate
import matplotlib.pyplot as plt



class SingleShotLogic(GenericLogic):
    """ This class brings raw data coming from ssrcounter measurements (gated or ungated)
        into trace form processable by the trace_analysis_logic.
    """

    _modclass = 'SingleShotLogic'
    _modtype = 'logic'

    # declare connectors
    savelogic = Connector(interface='SaveLogic')
    fitlogic = Connector(interface='FitLogic')
    singleshotreadoutcounter = Connector(interface='SingleShotInterface')
    pulsedmeasurementlogic = Connector(interface='PulsedMeasurementLogic')

    # ssr counter settings
    countlength = StatusVar(default=100)
    counts_per_readout = StatusVar(default=150)
    num_bins  = StatusVar(default=20)
    init_threshold0 = StatusVar(default=0)
    init_threshold1 = StatusVar(default=0)
    ana_threshold0 = StatusVar(default=0)
    ana_threshold1 = StatusVar(default=0)
    analyze_mode = StatusVar(default='full')
    sequence_length = StatusVar(default=1)
    analysis_period = StatusVar(default=5)
    normalized = StatusVar(default=False)

    # measurement timer settings
    timer_interval = StatusVar(default=5)


    # ssr measurement settings
    _number_of_ssr_readouts = StatusVar(default=1000)
    _normalized = StatusVar(default=False)

    # Container to store measurement information about the currently loaded sequence
    _ssr_measurement_information = StatusVar(default=dict())

    # notification signals for master module (i.e. GUI)
    sigTimerUpdated = QtCore.Signal(float, int, float)
    sigStatusSSRUpdated = QtCore.Signal(bool)
    sigSSRCounterSettingsUpdated = QtCore.Signal(dict)
    sigNumBinsUpdated = QtCore.Signal(int)
    sigSequenceLengthUpdated = QtCore.Signal(float)
    sigAnalysisPeriodUpdated = QtCore.Signal(float)
    sigNormalizedUpdated = QtCore.Signal(bool)
    sigAnalyzeModeUpdated = QtCore.Signal(str)
    sigThresholdUpdated = QtCore.Signal(dict)
    sigTraceUpdated = QtCore.Signal(np.ndarray, np.ndarray, float, float, int)
    sigHistogramUpdated = QtCore.Signal(np.ndarray)
    sigFitUpdated = QtCore.Signal(dict)



    # Internal signals
    sigStartTimer = QtCore.Signal()
    sigStopTimer = QtCore.Signal()



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        # timer for measurement
        self.__analysis_timer = None
        self.__start_time = 0
        self.__elapsed_time = 0
        self.__elapsed_sweeps = 0 # not used yet, could be used for length of timetrace

        # threading
        self._threadlock = Mutex()

        # measurement data
        self.time_axis = np.zeros(25)
        self.trace = np.zeros(25)
        self.hist_data = list([np.linspace(1,25,25),np.ones(24)])
        self.laser_data = np.zeros((10, 20), dtype='int64')
        self.raw_data = np.zeros((10, 20), dtype='int64')
        self.spin_flip_prob = 0
        self.error_flip_prob = 0
        self.lost_events = 0



        self._saved_raw_data = OrderedDict()  # temporary saved raw data
        self._recalled_raw_data_tag = None  # the currently recalled raw data dict key

        # Paused measurement flag, FIXME: not implemented yet
        self.__is_paused = False


        # for fit:
        self.fc = None  # Fit container
        self.signal_fit_data = np.empty((2, 0), dtype=float)  # The x,y data of the fit result

        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """


        # QTimer must be created here instead of __init__ because otherwise the timer will not run
        # in this logic's thread but in the manager instead.
        self.__analysis_timer = QtCore.QTimer()
        self.__analysis_timer.setSingleShot(False)
        self.__analysis_timer.setInterval(round(1000. * self.timer_interval))
        self.__analysis_timer.timeout.connect(self._ssr_analysis_loop,
                                              QtCore.Qt.QueuedConnection)

        # Fitting
        self.fc = self.fitlogic().make_fit_container('pulsed', '1d')
        self.fc.set_units(['s', 'arb.u.'])

        self.timer_pulsed_old = self.pulsedmeasurementlogic().timer_interval

        # Recall saved status variables
        if 'fits' in self._statusVariables and isinstance(self._statusVariables.get('fits'), dict):
            self.fc.load_from_dict(self._statusVariables['fits'])

        # Turn off pulse generator
        self.pulsedmeasurementlogic().pulse_generator_off()


        # update gui
        # For as long as there are no status variables define here:
        self.set_number_of_histogram_bins(self.num_bins)
        self.set_threshold({'init_threshold0': self.init_threshold0,
                            'init_threshold1': self.init_threshold1,
                            'ana_threshold0': self.ana_threshold0,
                            'ana_threshold1': self.ana_threshold1})
        self.set_ssr_counter_settings({'counts_per_readout': self.counts_per_readout,
                                       'countlength': self.countlength})

        # recalled saved raw data dict key
        self._recalled_raw_data_tag = None

        # Connect internal signals
        self.sigStartTimer.connect(self.__analysis_timer.start, QtCore.Qt.QueuedConnection)
        self.sigStopTimer.connect(self.__analysis_timer.stop, QtCore.Qt.QueuedConnection)
        return


    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        if self.module_state() == 'locked':
            self.stop_ssr_measurement()

        if len(self.fc.fit_list) > 0:
            self._statusVariables['fits'] = self.fc.save_to_dict()


        self.__analysis_timer.timeout.disconnect()
        self.sigStartTimer.disconnect()
        self.sigStopTimer.disconnect()
        return

        ############################################################################
        # ssr counter control methods and properties
        ############################################################################
    @property
    def ssr_counter_constraints(self):
        """Get SSR counter constraints

        @return dict: SSR counter constraints as a dict
        """
        return self.singleshotreadoutcounter().get_constraints()


    def ssr_counter_on(self):
        """Switching on the ssr counter

        @return int: error code (0:OK, -1:error)
        """
        return self.singleshotreadoutcounter().start_measure()

    def ssr_counter_off(self):
        """Switching off the ssr counter

        @return int: error code (0:OK, -1:error)
        """
        return self.singleshotreadoutcounter().stop_measure()

    @QtCore.Slot(bool)
    def toggle_ssr_counter(self, switch_on):
        """
        Convenience method to start/stop ssr counter

        @param bool start: Start the ssr counter (True) or stop the ssr counter (False)
        """
        if not isinstance(switch_on, bool):
            return -1

        if switch_on:
            err = self.ssr_counter_on()
        else:
            err = self.ssr_counter_off()
        return err





    ############################################################################
    # Measurement control methods and properties
    ############################################################################


    def toggle_ssr_measurement(self, start, stash_raw_data_tag=''):
        """
        Convenience method to start/stop measurement

        @param bool start: Start the measurement (True) or stop the measurement (False)
        """
        if start:
            self.start_ssr_measurement(stash_raw_data_tag)
        else:
            self.stop_ssr_measurement(stash_raw_data_tag)
        return


    def start_ssr_measurement(self, stashed_raw_data_tag=''):
        """Start the ssr measurement."""

        #turn off the analysis timer for pulsedmeasurment by setting it to zero
        self.timer_pulsed_old = self.pulsedmeasurementlogic().timer_interval
        self.pulsedmeasurementlogic().set_timer_interval(0)

        with self._threadlock:
            if self.module_state() == 'idle':
                # Lock module state
                self.module_state.lock()

                self.pulsedmeasurementlogic().start_pulsed_measurement(stashed_raw_data_tag)
                # initialize analysis_timer
                self.__elapsed_time = 0.0
                self.sigTimerUpdated.emit(self.__elapsed_time,
                                          self.__elapsed_sweeps,
                                          self.timer_interval)

                # Set starting time and start timer
                self.__start_time = time.time()
                self.sigStartTimer.emit()
                self.sigStatusSSRUpdated.emit(True)
        return


    def stop_ssr_measurement(self, stash_raw_data_tag=''):
        """
        Stop the measurement
        """
        try:
            # do one last analysis
            self._ssr_analysis_loop()
        except:
            pass
        with self._threadlock:
            if self.module_state() == 'locked':
                self.pulsedmeasurementlogic().stop_pulsed_measurement(stash_raw_data_tag)
                self.sigStopTimer.emit()
                self.module_state.unlock()
                # update status
                self.sigStatusSSRUpdated.emit(False)

        # set pulsedmeasurement timer again
        self.pulsedmeasurementlogic().set_timer_interval(self.timer_pulsed_old)
        return


    ############################### set & get ########################

    def set_parameters(self, settings_dict):
        # Set parameters if present
        if self.module_state() == 'idle':
            if 'analyze_mode' in settings_dict:
                self.set_analyze_mode(settings_dict['analyze_mode'])
            if 'num_bins' in settings_dict:
                self.set_number_of_histogram_bins(settings_dict['num_bins'])
            if 'sequence_length' in settings_dict:
                self.set_sequence_length(settings_dict['sequence_length'])
            if 'analysis_period' in settings_dict:
                self.set_analysis_period(settings_dict['analysis_period'])
            if 'ssr_normalise' in settings_dict:
                self.set_normalized(bool(settings_dict['ssr_normalise']))
            if 'threshold_dict' in settings_dict:
                self.set_threshold(settings_dict['threshold_dict'])
        else:
            self.log.warning('SSR measurement is running. CAnnot change parameters')
        return



    def set_ssr_counter_settings(self, settings_dict=None, **kwargs):
        """
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        # Check if ssr counter is running and do nothing if that is the case
        counter_status = self.singleshotreadoutcounter().get_status()
        if not counter_status >= 2 and not counter_status < 0:
            # Determine complete settings dictionary
            if not isinstance(settings_dict, dict):
                settings_dict = kwargs
            else:
                settings_dict.update(kwargs)

            # Set parameters if present
            if 'countlength' in settings_dict:
                self.countlength= int(settings_dict['countlength'])
            if 'counts_per_readout' in settings_dict:
                self.counts_per_readout = int(settings_dict['counts_per_readout'])


            # Apply the settings to hardware
            self.singleshotreadoutcounter().configure_ssr_counter(countlength=self.countlength,
                                                                  counts_per_readout=self.counts_per_readout)
        else:
            self.log.warning('Gated counter is not idle (status: {0}).\n'
                             'Unable to apply new settings.'.format(counter_status))

        # emit update signal for master (GUI or other logic module)
        self.sigSSRCounterSettingsUpdated.emit({'countlength': self.countlength,
                                                'counts_per_readout': self.counts_per_readout})
        return self.countlength, self.counts_per_readout


    def get_ssr_counter_settings(self):
        counter_dict=dict()
        counter_dict['countlength'] = self.countlength
        counter_dict['counts_per_readout'] = self.counts_per_readout
        return counter_dict

    def set_analyze_mode(self, mode):
        self.analyze_mode = mode
        self.sigAnalyzeModeUpdated.emit(mode)
        return


    def set_number_of_histogram_bins(self, num_bins):
        self.num_bins = num_bins
        self.sigNumBinsUpdated.emit(num_bins)
        return self.num_bins

    def get_number_of_bins(self):
        return self.num_bins

    def set_sequence_length(self, sequence_length):
        self.sequence_length = sequence_length
        self.sigSequenceLengthUpdated.emit(sequence_length)
        return self.sequence_length

    def get_sequence_length(self):
        return self.sequence_length

    def set_analysis_period(self, analysis_period):
        with self._threadlock:
            self.timer_interval = analysis_period
            if self.timer_interval > 0:
                self.__analysis_timer.setInterval(int(1000. * self.timer_interval))
                if self.module_state() == 'locked':
                    self.sigStartTimer.emit()
            else:
                self.sigStopTimer.emit()

            self.sigTimerUpdated.emit(self.__elapsed_time, self.__elapsed_sweeps,
                                      self.timer_interval)

        self.timer_interval = analysis_period
        self.__analysis_timer.setInterval(round(1000. * self.timer_interval))
        self.sigAnalysisPeriodUpdated.emit(analysis_period)
        return self.timer_interval

    def get_analysis_period(self):
        return self.timer_interval


    def set_normalized(self, norm):
        # normalized mode is only working with a fast counter
        self.normalized = norm
        self.sigNormalizedUpdated.emit(norm)
        return

    def get_normalized(self):
        return self.normalized


    def set_threshold(self, threshold_dict):
        if 'init_threshold0' in threshold_dict:
            self.init_threshold0=threshold_dict['init_threshold0']
        if 'init_threshold1' in threshold_dict:
            self.init_threshold1 = threshold_dict['init_threshold1']
        if 'ana_threshold0' in threshold_dict:
            self.ana_threshold0 = threshold_dict['ana_threshold0']
        if 'ana_threshold1' in threshold_dict:
            self.ana_threshold1 = threshold_dict['ana_threshold1']
        self.sigThresholdUpdated.emit(threshold_dict)
        #self._ssr_analysis_loop()
        return

    def get_threshold(self):
        threshold_dict = dict()
        threshold_dict['init_threshold'] = list()
        threshold_dict['ana_threshold'] = list()
        threshold_dict['init_threshold0'] = self.init_threshold0
        threshold_dict['init_threshold1'] = self.init_threshold1
        threshold_dict['ana_threshold0'] = self.ana_threshold0
        threshold_dict['ana_threshold1'] = self.ana_threshold1
        return threshold_dict

#################################################### Analysis ##################################################

    def manually_pull_data(self):
        """ Analyse and display the data
        """
        self._ssr_analysis_loop()
        return

    def _ssr_analysis_loop(self):
        """ Acquires laser pulses from ssr counter,
            calculates fluorescence signal and creates plots.
        """
        with self._threadlock:
            # Update elapsed time
            self.__elapsed_time = time.time() - self.__start_time

            # Get counter raw data (including recalled raw data from previous measurement)
            self.trace = self._get_raw_data()

            self.time_axis = np.arange(1, len(self.trace) + 1) * self.sequence_length

            # compute spin flip probabilities
            try:
                self.spin_flip_prob, self.error_flip_prob, self.lost_events = self.analyze_flip_probability()
            except:
                #self.log.warning('Computation of spin flip rate failed')
                self.spin_flip_prob, self.error_flip_prob, self.lost_events = 0, 0, 0

            # update the trace in GUI
            self.sigTraceUpdated.emit(self.time_axis, self.trace, self.spin_flip_prob, self.error_flip_prob, self.lost_events)


            # compute and fit histogram
            self.calculate_histogram()
            self.double_gaussian_fit_histogram()
        return


    def _get_raw_data(self):
        """
        Get the raw count data from the ssr counting hardware and perform sanity checks.
        Also add recalled raw data to the newly received data.
        :return numpy.ndarray: The count data (1D for ungated, 2D for gated counter)
        """
        # get raw data from ssr counter
        ssr_data = netobtain(self.singleshotreadoutcounter().get_data_trace())

        # add old raw data from previous measurements if necessary
        if self._saved_raw_data.get(self._recalled_raw_data_tag) is not None:
            if not ssr_data.any():
                ssr_data = self._saved_raw_data[self._recalled_raw_data_tag]
            elif self._saved_raw_data[self._recalled_raw_data_tag].shape == ssr_data.shape:
                ssr_data = self._saved_raw_data[self._recalled_raw_data_tag] + ssr_data

            else:
                pass
                #self.log.warning('Recalled raw data has not the same shape as current data.'
                 #                '\nDid NOT add recalled raw data to current time trace.')
        elif not ssr_data.any():
            #self.log.warning('Only zeros received from ssr counter!')
            ssr_data = np.zeros(ssr_data.shape, dtype='int64')

        return ssr_data



    def analyze_flip_probability(self):
        """
        Method which calculates the histogram, the fidelity and the flip probability of a time trace.
        :return:
        """

        # calculate the flip probability
        no_flip = 0.0
        flip = 0.0
        # find all indices in the trace-array, where the value is above init_threshold[1]
        init_high = np.where(self.trace[:-1] >= self.init_threshold1)[0]
        # find all indices in the trace-array, where the value is below init_threshold[0]
        init_low = np.where(self.trace[:-1] < self.init_threshold0)[0]
        # find all indices in the trace-array, where the value is above ana_threshold[1]
        ana_high = np.where(self.trace >= self.ana_threshold1)[0]
        # find all indices in the trace-array, where the value is below ana_threshold[0]
        ana_low = np.where(self.trace < self.ana_threshold0)[0]

        if self.analyze_mode == 'bright' or self.analyze_mode == 'full':
            # analyze the trace where the data were the nuclear was initalized into one direction
            for index in init_high:
                # check if the following data point is in the analysis array
                if index + 1 in ana_high:
                    no_flip = no_flip + 1
                elif index + 1 in ana_low:
                    flip = flip + 1
        if self.analyze_mode == 'dark' or self.analyze_mode == 'full':
            # repeat the same if the nucleus was initalized into the other array
            for index in init_low:
                # check if the following data point is in the analysis array
                if index + 1 in ana_high:
                    flip = flip + 1
                elif index + 1 in ana_low:
                    no_flip = no_flip + 1

        # the flip probability is given by the number of flips divided by the total number of analyzed data points
        if (flip + no_flip) == 0:
            #self.log.warning('There is not enough data to anaylsis SSR!')
            self.spin_flip_prob = 0
            self.spin_flip_error = 0
        else:
            self.spin_flip_prob = flip / (flip + no_flip)
            self.spin_flip_error = np.sqrt((flip*(1-self.spin_flip_prob)**2+no_flip*self.spin_flip_prob**2)\
                                   /(flip + no_flip-1)/(flip + no_flip))
        # the number of lost events is given by the length of the time_trace minus the number of analyzed data points
        self.lost_events = len(self.trace) - 1 - (flip + no_flip)

        return self.spin_flip_prob, self.spin_flip_error, self.lost_events





    def calculate_histogram(self, custom_bin_arr=None):
        """ Calculate the histogram of a given trace.
        @param np.array trace: a 1D trace
        @param int num_bins: number of bins between the minimal and maximal
                             value of the trace. That must be an integer greater
                             than or equal to 1.
        @param np.array custom_bin_arr: optional, 1D array. If a specific,
                                        non-uniform binning array is desired
                                        then it can be passed to the numpy
                                        routine. Then the parameter num_bins is
                                        ignored. Otherwise a uniform binning is
                                        applied by default.
        @return: np.array: a 2D array, where first entry are the x_values and
                           second entry are the count values. The length of the
                           array is normally determined by the num_bins
                           parameter.
        Usually the bins for the histogram are taken to be equally spaced,
        ranging from the minimal to the maximal value of the input trace array.
        """

        if custom_bin_arr is not None:
            hist_y_val, hist_x_val = np.histogram(self.trace, custom_bin_arr,
                                                  density=False)
        else:

            # analyze the trace, and check whether all values are the same
            difference = self.trace.max() - self.trace.min()

            # if all values are the same, run at least the method with an zero
            # array. That will ensure at least an output:
            if np.isclose(0, difference) and self.num_bins is None:
                # numpy can handle an array of zeros
                num_bins = 50
                hist_y_val, hist_x_val = np.histogram(self.trace, self.num_bins)

            # if no number of bins are passed, then take the integer difference
            # between the counts, that will prevent strange histogram artifacts:
            elif not np.isclose(0, difference) and self.num_bins is None:
                hist_y_val, hist_x_val = np.histogram(self.trace, int(difference))

            # a histogram with self defined number of bins
            else:
                hist_y_val, hist_x_val = np.histogram(self.trace, self.num_bins)

        self.hist_data = np.array([hist_x_val, hist_y_val])
        # update the histogram in GUI
        self.sigHistogramUpdated.emit(self.hist_data)
        return self.hist_data


    def double_gaussian_fit_histogram(self):
        # fit histogram with a double Gaussian
        axis = self.hist_data[0][:-1] + (self.hist_data[0][1] - self.hist_data[0][0]) / 2.
        data = self.hist_data[1]

        add_params = dict()
        add_params['offset'] = {'min': 0, 'max': data.max(), 'value': 1e-15, 'vary': False}
        if not axis.min() >= self.init_threshold0:
            add_params['g0_center'] = {'min': axis.min(), 'max': self.init_threshold0,
                                       'value': self.init_threshold0 - (self.init_threshold0 - axis.min()) / 10}
        else:
            add_params['g0_center'] = {'min': axis.min()-1, 'max': self.init_threshold0,
                                       'value': self.init_threshold0 - (self.init_threshold0 - axis.min()) / 10}
        if not axis.max() <= self.init_threshold1:
            add_params['g1_center'] = {'min': self.init_threshold1, 'max': axis.max(),
                                       'value': self.init_threshold1 + (axis.max() - self.init_threshold1) / 10}
        else:
            add_params['g1_center'] = {'min': self.init_threshold1, 'max': axis.max()+1,
                                       'value': self.init_threshold1 + (axis.max() - self.init_threshold1) / 10}
        add_params['g0_amplitude'] = {'min': data.max() / 4, 'max': 1.3 * data.max(), 'value': data.max()}
        add_params['g1_amplitude'] = {'min': data.max() / 4, 'max': 1.3 * data.max(), 'value': data.max()}
        add_params['g0_sigma'] = {'min': (self.init_threshold0 - axis.min()) / 10,
                                  'max': (axis.max() - axis.min()) / 2,
                                  'value': (axis.max() - axis.min()) / 5}
        add_params['g1_sigma'] = {'min': (axis.max() - self.init_threshold1) / 10,
                                  'max': (axis.max() - axis.min()) / 2,
                                  'value': (axis.max() - axis.min()) / 7}

        try:
            hist_fit_x, hist_fit_y, param_dict, fit_result = self.do_doublegaussian_fit(axis, data,
                                                                                        add_params=add_params)
            fit_params = fit_result.best_values

            # calculate the fidelity for the left and right part from the threshold
            center1 = fit_params['g0_center']
            center2 = fit_params['g1_center']
            std1 = fit_params['g0_sigma']
            std2 = fit_params['g1_sigma']
            gaussian1 = lambda x: fit_params['g0_amplitude'] * np.exp(-(x - center1) ** 2 / (2 * std1 ** 2))
            gaussian2 = lambda x: fit_params['g1_amplitude'] * np.exp(-(x - center2) ** 2 / (2 * std2 ** 2))
            if center1 > center2:
                gaussian = gaussian1
                gaussian1 = gaussian2
                gaussian2 = gaussian
            area_left1 = integrate.quad(gaussian1, -np.inf, self.init_threshold0)
            area_left2 = integrate.quad(gaussian2, -np.inf, self.init_threshold0)
            area_right1 = integrate.quad(gaussian1, self.init_threshold1, np.inf)
            area_right2 = integrate.quad(gaussian2, self.init_threshold1, np.inf)
            self.fidelity_left = area_left1[0] / (area_left1[0] + area_left2[0])
            self.fidelity_right = area_right2[0] / (area_right1[0] + area_right2[0])
            self.fidelity_total = (area_left1[0] + area_right2[0]) / (
                area_left1[0] + area_left2[0] + area_right1[0] + area_right2[0])

            fit_dict = dict()
            fit_dict['fit_result'] = fit_result
            fit_dict['fit_x'] = hist_fit_x
            fit_dict['fit_y'] = hist_fit_y
            fit_dict['fidelity_left'] = self.fidelity_left
            fit_dict['fidelity_right'] = self.fidelity_right
            fit_dict['fidelity_total'] = self.fidelity_total

        except:
            fit_dict = dict()
            fit_dict['fit_result'] = None
            fit_dict['fit_x'] = axis
            fit_dict['fit_y'] = data
            fit_dict['fidelity_left'] = 0
            fit_dict['fidelity_right'] = 0
            fit_dict['fidelity_total'] = 0

        self.sigFitUpdated.emit(fit_dict)
        self.fit_dict = fit_dict
        return fit_dict

    def do_doublegaussian_fit(self, axis, data, add_params=None):
        model, params = self.fitlogic().make_gaussiandouble_model()

        if len(axis) < len(params):
            #self.log.warning('Fit could not be performed because number of '
             #                'parameters is larger than data points')
            return self.do_no_fit()

        else:
            result = self.fitlogic().make_gaussiandouble_fit(axis, data, self.fitlogic().estimate_gaussiandouble_peak,
                                                             add_params=add_params)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # this dict will be passed to the formatting method
            param_dict = OrderedDict()

            # create the proper param_dict with the values:
            param_dict['sigma_0'] = {'value': result.params['g0_sigma'].value,
                                     'error': result.params['g0_sigma'].stderr,
                                     'unit': 'Counts/s'}

            param_dict['FWHM_0'] = {'value': result.params['g0_fwhm'].value,
                                    'error': result.params['g0_fwhm'].stderr,
                                    'unit': 'Counts/s'}

            param_dict['Center_0'] = {'value': result.params['g0_center'].value,
                                      'error': result.params['g0_center'].stderr,
                                      'unit': 'Counts/s'}

            param_dict['Amplitude_0'] = {'value': result.params['g0_amplitude'].value,
                                         'error': result.params['g0_amplitude'].stderr,
                                         'unit': 'Occurrences'}

            param_dict['sigma_1'] = {'value': result.params['g1_sigma'].value,
                                     'error': result.params['g1_sigma'].stderr,
                                     'unit': 'Counts/s'}

            param_dict['FWHM_1'] = {'value': result.params['g1_fwhm'].value,
                                    'error': result.params['g1_fwhm'].stderr,
                                    'unit': 'Counts/s'}

            param_dict['Center_1'] = {'value': result.params['g1_center'].value,
                                      'error': result.params['g1_center'].stderr,
                                      'unit': 'Counts/s'}

            param_dict['Amplitude_1'] = {'value': result.params['g1_amplitude'].value,
                                         'error': result.params['g1_amplitude'].stderr,
                                         'unit': 'Occurrences'}

            param_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

            return hist_fit_x, hist_fit_y, param_dict, result



#FIXME: Manual fitting is not working yet
    def do_fit(self, fit_function):
        return
    #     """ Makes the a fit of the current fit function.
    #     @param str fit_function: name of the chosen fit function.
    #     @return tuple(x_val, y_val, fit_results):
    #                 x_val: a 1D numpy array containing the x values
    #                 y_val: a 1D numpy array containing the y values
    #                 fit_results: a string containing the information of the fit
    #                              results.
    #     You can obtain with get_fit_methods all implemented fit methods.
    #     """
    #
    #     if self.hist_data is None:
    #         hist_fit_x = []
    #         hist_fit_y = []
    #         param_dict = OrderedDict()
    #         fit_result = None
    #         return hist_fit_x, hist_fit_y, param_dict, fit_result
    #     else:
    #
    #         # self.log.debug((self.calculate_threshold(self.hist_data)))
    #
    #         # shift x axis to middle of bin
    #         axis = self.hist_data[0][:-1] + (self.hist_data[0][1] - self.hist_data[0][0]) / 2.
    #         data = self.hist_data[1]
    #
    #         if fit_function == 'No Fit':
    #             hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_no_fit()
    #             return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
    #         elif fit_function == 'Gaussian':
    #             hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_gaussian_fit(axis, data)
    #             return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
    #         elif fit_function == 'Double Gaussian':
    #             hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_doublegaussian_fit(axis, data)
    #             return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
    #         elif fit_function == 'Poisson':
    #             hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_possonian_fit(axis, data)
    #             return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
    #         elif fit_function == 'Double Poisson':
    #             hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_doublepossonian_fit(axis, data)
    #             return hist_fit_x, hist_fit_y, fit_param_dict, fit_result



    ############################################################################
    def save_measurement(self, save_tag):

        filepath = self.savelogic().get_path_for_module('SSR')
        timestamp = datetime.datetime.now()

        data = OrderedDict()
        data['time'] = np.array(self.time_axis)
        data['Norm. Counts'] = np.array(self.trace)

        # write the parameters:
        parameters = OrderedDict()
        parameters['number bins'] = self.num_bins
        parameters['init_threshold0'] = self.init_threshold0
        parameters['init_threshold1'] = self.init_threshold1
        parameters['ana_threshold0'] = self.ana_threshold0
        parameters['ana_threshold1'] = self.ana_threshold1
        parameters['counts_per_readout'] = self.counts_per_readout
        parameters['countlength'] = self.countlength

        plt.style.use(self.savelogic().mpl_qd_style)
        fig, (ax1, ax2) = plt.subplots(2, 1)
        ax1.plot(self.time_axis, self.trace, '-o', color='blue',
                 linestyle=':', linewidth=0.5, label='count trace')
        # add the spin flip probability to first plot
        # The position of the text annotation is controlled with the
        # relative offset in x direction
        rel_offset = 0.02
        ax1.text(1.00 + rel_offset, 0.99, 'spin flip prob.: ' + str(round(self.spin_flip_prob * 100, 2)),
                 verticalalignment='top', horizontalalignment='left', transform=ax1.transAxes, fontsize=12)
        ax1.set_xlabel('time [s]')
        ax1.set_ylabel('norm. intensity')
        try:
            ax2.hist(self.trace, self.num_bins)

            # include fit curve and fit parameters.
            fit_result = self.fit_dict['fit_result']
            hist_fit_x = self.fit_dict['fit_x']
            hist_fit_y = self.fit_dict['fit_y']
            ax2.plot(hist_fit_x, hist_fit_y,
                     marker='None', linewidth=1.5,  # color='o',
                     label='fit: double Gaussian')

            # add then the fit result to the second plot:
            # Parameters for the text plot:
            # create the formatted fit text:
            if hasattr(fit_result, 'result_str_dict'):
                fit_res = units.create_formatted_output(fit_result.result_str_dict)
            else:
                self.savelogic().log.warning('The fit container does not contain any data '
                                      'from the fit! Apply the fit once again.')
                fit_res = ''
            # do reverse processing to get each entry in a list
            entry_list = fit_res.split('\n')
            entry_text = 'Fit results: \n'
            for entry in entry_list:
                entry_text += entry + '\n'
            entry_text += 'fidelity left: ' + str(round(self.fidelity_left * 100, 2)) + '\n'
            entry_text += 'fidelity right: ' + str(round(self.fidelity_right * 100, 2)) + '\n'
            entry_text += 'fidelity total: ' + str(round(self.fidelity_total * 100, 2))

            ax2.text(1.00 + rel_offset, 0.99, entry_text,
                     verticalalignment='top', horizontalalignment='left', transform=ax2.transAxes, fontsize=12)

            ax2.set_xlabel('norm. intensity')
            ax2.set_ylabel('occurence')

            fig.tight_layout()

            self.savelogic().save_data(data, timestamp=timestamp,
                                parameters=parameters, fmt='%.15e',
                                filepath=self.savelogic().get_path_for_module('SSR'),
                                filelabel=save_tag,
                                delimiter='\t', plotfig=fig)
        except:
            pass

        np.savez(self.savelogic().get_path_for_module('SSR') + '\\' + timestamp.strftime(
            '%Y%m%d-%H%M-%S') + '_' + save_tag + '_fastcounter', self.raw_data)
        # np.savez(save_directory + save_tag + '_summed_rows', tmp_signal)
        plt.close()
        return



