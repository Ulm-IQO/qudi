# -*- coding: utf-8 -*-
"""
This file contains the general Qudi trace analysis logic.

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


from qtpy import QtCore
import numpy as np
from scipy.signal import gaussian
from scipy.ndimage import filters
import scipy.integrate as integrate
from scipy.interpolate import InterpolatedUnivariateSpline
from collections import OrderedDict

from core.module import Connector
from logic.generic_logic import GenericLogic


class TraceAnalysisLogic(GenericLogic):
    """ Perform a gated counting measurement with the hardware.  """

    _modclass = 'TraceAnalysisLogic'
    _modtype = 'logic'

    # declare connectors
    counterlogic1 = Connector(interface='CounterLogic')
    savelogic = Connector(interface='SaveLogic')
    fitlogic = Connector(interface='FitLogic')

    sigHistogramUpdated = QtCore.Signal()


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

        self.hist_data = None
        self._hist_num_bins = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._counter_logic = self.get_connector('counterlogic1')
        self._save_logic = self.get_connector('savelogic')
        self._fit_logic = self.get_connector('fitlogic')

        self._counter_logic.sigGatedCounterFinished.connect(self.do_calculate_histogram)


        self.current_fit_function = 'No Fit'

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    def set_num_bins_histogram(self, num_bins, update=True):
        """ Set the number of bins

        @param int num_bins: number of bins for the histogram
        @param bool update: if the change of bins should evoke a recalculation
                            of the histogram.
        """
        self._hist_num_bins = num_bins

        if update:
            self.do_calculate_histogram()

    def do_calculate_histogram(self, mode='normal'):
        """ Passes all the needed parameters to the appropriated methods.

        @return:
        """
        if mode == 'normal':
            self.hist_data = self.calculate_histogram(self._counter_logic.countdata[0],
                                                      self._hist_num_bins)
        if mode == 'fastcomtec':
            self.sigHistogramUpdated.emit()


    def calculate_histogram(self, trace, num_bins=None, custom_bin_arr=None):
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
            hist_y_val, hist_x_val = np.histogram(trace, custom_bin_arr,
                                                  density=False)
        else:

            # analyze the trace, and check whether all values are the same
            difference = trace.max() - trace.min()

            # if all values are the same, run at least the method with an zero
            # array. That will ensure at least an output:
            if np.isclose(0, difference) and num_bins is None:
                # numpy can handle an array of zeros
                num_bins = 50
                hist_y_val, hist_x_val = np.histogram(trace, num_bins)

            # if no number of bins are passed, then take the integer difference
            # between the counts, that will prevent strange histogram artifacts:
            elif not np.isclose(0, difference) and num_bins is None:
                hist_y_val, hist_x_val = np.histogram(trace, int(difference))

            # a histogram with self defined number of bins
            else:
                hist_y_val, hist_x_val = np.histogram(trace, num_bins)

        return hist_x_val, hist_y_val


    def analyze_flip_prob(self, trace, num_bins=None, threshold=None):
        """General method, which analysis how often a value was changed from
           one data point to another in relation to a certain threshold.

        @param np.array trace: 1D trace of data
        @param int num_bins: optional, if a specific size for the histogram is
                             desired, which is used to calculate the threshold.
        @param float threshold: optional, if a specific threshold is going to be
                                used, otherwise the threshold is calculated from
                                the data.

        @return tuple(flip_prop, param):

                      float flip_prop: the actual flip probability
                      int num_of_flips: the total number of flips
                      float fidelity: the fidelity
                      float threshold: the calculated or passed threshold
                      float lifetime_dark: the lifetime in the dark state in s
                      float lifetime_bright: lifetime in the bright state in s
        """

        hist_data = self.calculate_histogram(trace=trace, num_bins=num_bins)
        threshold_fit, fidelity, fit_param = self.calculate_threshold(hist_data)
        bin_trace = self.calculate_binary_trace(trace, threshold_fit)

        # here the index_arr contain all indices where the state is above
        # threshold, indicating the bright state.
        index_arr, filtered_arr = self.extract_filtered_values(trace, threshold_fit, below=False)

        # by shifting the index_arr one value further, one will investigate
        # basically the next state, where a change has happened.
        next_index_arr = index_arr+1

        # Just for safety neglect the last value in the index_arr so that one
        # will not go beyond the array.
        next_filtered_bin_arr = bin_trace[next_index_arr[:-1]]

        # calculate how many darkstates are present in the array, remember
        # filtered_arr contains all the bright states.
        num_dark_state = len(trace) - len(filtered_arr)
        num_bright_state = len(filtered_arr)

        # extract the number of state, which has been flipped to dark state
        # (True) started in the bright state (=False)
        num_flip_to_dark = len(np.where(next_filtered_bin_arr == True)[0])

        # flip probability:
        # In the array filtered_bin_arr all states are in bright state meaning
        # that if you would perform for
        #   filtered_bin_arr = bin_trace[index_arr]
        # the mean value with filtered_bin_arr.mean() then you should get 0.0
        # since every entry in that array is False. By looking at the next index
        # it might be that some entries turn to True, i.e. a flip from bright to
        # dark occurred. Then you get a different mean value, which would
        # indicate how many states are flipped from bright (False) to dark (True).
        # If all the next states would be dark (True), then you would perform a
        # perfect flip into the dark state, meaning a flip probability of 1.
        flip_prob = next_filtered_bin_arr.mean()

        # put all the calculated parameters in a proper dict:
        param = OrderedDict()
        param['num_dark_state'] = num_dark_state # Number of Dark States
        param['num_bright_state'] = num_bright_state # Number of Bright States
        param['num_flip_to_dark'] = num_flip_to_dark # Number of flips from bright to dark
        param['fidelity'] = fidelity # Fidelity of Double Poissonian Fit
        param['threshold'] = threshold_fit # Threshold

        # add the fit parameter to the output parameter:
        param.update(fit_param)

        return flip_prob, param

    def analyze_flip_prob_postselect(self):
        """ Post select the data trace so that the flip probability is only
            calculated from a jump from below a threshold value to an value
            above threshold.

        @return:
        """
        pass



    def get_fit_functions(self):
        """ Return all fit functions, which are currently implemented for that module.

        @return list: with string entries denoting the name of the fit.
        """
        return ['No Fit', 'Gaussian', 'Double Gaussian', 'Poisson',
                'Double Poisson']

    def do_fit(self, fit_function=None):
        """ Makes the a fit of the current fit function.

        @param str fit_function: name of the chosen fit function.

        @return tuple(x_val, y_val, fit_results):
                    x_val: a 1D numpy array containing the x values
                    y_val: a 1D numpy array containing the y values
                    fit_results: a string containing the information of the fit
                                 results.

        You can obtain with get_fit_methods all implemented fit methods.
        """

        if self.hist_data is None:
            hist_fit_x = []
            hist_fit_y = []
            param_dict = OrderedDict()
            fit_result = None
            return hist_fit_x, hist_fit_y, param_dict, fit_result
        else:

            # self.log.debug((self.calculate_threshold(self.hist_data)))

            # shift x axis to middle of bin
            axis = self.hist_data[0][:-1]+(self.hist_data[0][1]-self.hist_data[0][0])/2.
            data = self.hist_data[1]

            if fit_function == 'No Fit':
                hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_no_fit()
                return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
            elif fit_function == 'Gaussian':
                hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_gaussian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
            elif fit_function == 'Double Gaussian':
                hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_doublegaussian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
            elif fit_function == 'Poisson':
                hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_possonian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_param_dict, fit_result
            elif fit_function == 'Double Poisson':
                hist_fit_x, hist_fit_y, fit_param_dict, fit_result = self.do_doublepossonian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_param_dict, fit_result

    def do_no_fit(self):
        """ Perform no fit, basically return an empty array.

        @return tuple(x_val, y_val, fit_results):
                    x_val: a 1D numpy array containing the x values
                    y_val: a 1D numpy array containing the y values
                    fit_results: a string containing the information of the fit
                                 results.
        """
        hist_fit_x = []
        hist_fit_y = []
        param_dict = {}
        fit_result = None
        return hist_fit_x, hist_fit_y, param_dict, fit_result

    def analyze_lifetime(self, trace, dt, method='postselect',
                         distr='gaussian_normalized', state='|-1>', num_bins=50):
        """ Perform an lifetime analysis of a 1D time trace. The analysis is
            based on the method provided ( for now only post select is implemented ).

        @param numpy array trace: 1 D array
        @param string method: The method used for the lifetime analysis
        @param string distr: distribution used for analysis
        @param string state: State that the mw was applied to
        @param int num_bins: number of bins used in the histogram to determine the threshold before digitalisation
                             of data
        @return: dictionary containing the lifetimes of the different states |0>, |1>, |-1> in the case of the HMM method
                 For the postselect method only lifetime for bright and darkstate is returned, keys are 'bright_state' and
                 'dark_state'
        """
        lifetime_dict = {}

        if method == 'postselect':
            if distr == 'gaussian_normalized':
                hist_y_val, hist_x_val = np.histogram(trace, num_bins)
                hist_data = np.array([hist_x_val, hist_y_val])
                threshold_fit, fidelity, param_dict = self.calculate_threshold(hist_data=hist_data,
                                                                               distr='gaussian_normalized')
                threshold = threshold_fit

            # helper functions to get and analyze the timetrace
            def analog_digitial_converter(cut_off, data):
                digital_trace = []
                for data_point in data:
                    if data_point >= cut_off:
                        digital_trace.append(1)
                    else:
                        digital_trace.append(0)
                return digital_trace

            def time_in_high_low(digital_trace, dt):
                """
                What I need this function to do is to get all consecutive {1, ... , n} 1s or 0s and add
                them up and put into a list to later make a histogram from them.
                """
                occurances = []
                index = 0
                index2 = 0

                while (index < len(digital_trace)):
                    occurances.append(0)
                    # start following the consecutive 1s
                    while (digital_trace[index] == 1):
                        occurances[index2] += 1
                        if index == (len(digital_trace) - 1):
                            occurances = np.array(occurances)
                            return occurances * dt
                        else:
                            index += 1
                    if digital_trace[index - 1] == 1:
                        index2 += 1
                        occurances.append(0)
                    # start following the consecutive 0s
                    while (digital_trace[index] == 0):
                        occurances[index2] -= 1
                        if index == (len(digital_trace) - 1):
                            occurances = np.array(occurances)
                            return occurances * dt
                        else:
                            index += 1
                    index2 += 1

            digital_trace = analog_digitial_converter(threshold, trace)
            time_array = time_in_high_low(digital_trace, dt)

            # now we need to make a histogram as well as a fit
            # what would be a good estimate for the number of bins

            # longest = np.max(np.array(occurances))
            # number of steps in between, rather not use that for now
            # est_bins = np.int(longest/dt)

            time_array_high = np.array([ii for ii in filter(lambda x: x > 0, time_array)])
            time_array_low = np.array([ii for ii in filter(lambda x: x < 0, time_array)])


            # get lifetime of bright state
            time_hist_high = np.histogram(time_array_high, bins=num_bins)
            vals = [i for i in filter(lambda x: x[1] > 0, enumerate(time_hist_high[0][0:num_bins]))]

            indices = np.array([val[0] for val in vals])
            indices = np.array([np.int(indice) for indice in indices])
            self.log.debug('threshold {0}'.format(threshold))
            self.log.debug('time_array:{0}'.format(time_array))
            self.log.debug('time_array_high:{0}'.format(time_array_high))
            self.log.debug('time_hist_high:{0}'.format(time_hist_high))
            self.log.debug('indices: {0}'.format(indices))
            self.debug_lifetime_x = time_hist_high[1][indices]
            self.debug_lifetime_y = time_hist_high[0][indices]
            para = dict()
            para['offset'] = {"value": 0.0, "vary": False}
            result = self._fit_logic.make_exponentialdecayoffset_fit(time_hist_high[1][indices],
                                                               time_hist_high[0][indices], add_params=para)
            bright_liftime = result.params['lifetime']
            # for debug purposes give also the results back of the fits for now
            lifetime_dict['result_bright'] = result
            # also give back the data used for the fit
            lifetime_dict['bright_raw'] =  np.array([time_hist_high[1][indices],time_hist_high[0][indices]])

            # get lifetime of dark state
            time_hist_low = np.histogram(time_array_low, bins=num_bins)
            vals = [i for i in filter(lambda x: x[1] > 0, enumerate(time_hist_low[0][0:num_bins]))]
            indices = np.array([val[0] for val in vals])
            indices = np.array([np.int(indice) for indice in indices])
            values = np.array([val[1] for val in vals])
            # positive axis
            mirror_axis = -time_hist_low[1][indices]
            result = self._fit_logic.make_exponentialdecayoffset_fit(mirror_axis,
                                                               values, add_params=para)
            dark_liftime = result.params['lifetime']
            lifetime_dict['result_dark'] = result

            lifetime_dict['bright_state'] = bright_liftime.value
            lifetime_dict['dark_state'] = dark_liftime.value
            # also give back the data used for the fit
            lifetime_dict['dark_raw'] = np.array([mirror_axis, values])



        return lifetime_dict

    def do_gaussian_fit(self, axis, data):
        """ Perform a gaussian fit.

        @param axis:
        @param data:
        @return:
        """

        model, params = self._fit_logic.make_gaussian_model()
        if len(axis) < len(params):
            self.log.warning('Fit could not be performed because number of '
                    'parameters is smaller than data points.')
            return self.do_no_fit()

        else:

            parameters_to_substitute = dict()
            update_dict=dict()

            #TODO: move this to "gated counter" estimator in fitlogic
            #      make the filter an extra function shared and usable for other
            #      functions
            gauss = gaussian(10, 10)
            data_smooth = filters.convolve1d(data, gauss/gauss.sum(), mode='mirror')

            # integral of data corresponds to sqrt(2) * Amplitude * Sigma
            function = InterpolatedUnivariateSpline(axis, data_smooth, k=1)
            Integral = function.integral(axis[0], axis[-1])
            amp = data_smooth.max()
            sigma = Integral / amp / np.sqrt(2 * np.pi)
            amplitude = amp * sigma * np.sqrt(2 * np.pi)

            update_dict['offset']    = {'min': 0,          'max': data.max(), 'value': 0, 'vary': False}
            update_dict['center']    = {'min': axis.min(), 'max': axis.max(), 'value': axis[np.argmax(data)]}
            update_dict['sigma']     = {'min': -np.inf,    'max': np.inf,     'value': sigma}
            update_dict['amplitude'] = {'min': 0,          'max': np.inf,     'value': amplitude}

            result = self._fit_logic.make_gaussian_fit(x_axis=axis,
                                                       data=data,
                                                       estimator=self._fit_logic.estimate_gaussian_peak,
                                                       units=None,  # TODO
                                                       add_params=update_dict)
            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            param_dict = OrderedDict()

            # create the proper param_dict with the values:
            param_dict['sigma_0'] = {'value': result.params['sigma'].value,
                                     'error': result.params['sigma'].stderr,
                                     'unit' : 'Occurrences'}

            param_dict['FWHM'] = {'value': result.params['fwhm'].value,
                                  'error': result.params['fwhm'].stderr,
                                  'unit' : 'Counts/s'}

            param_dict['Center'] = {'value': result.params['center'].value,
                                    'error': result.params['center'].stderr,
                                    'unit' : 'Counts/s'}

            param_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                       'error': result.params['amplitude'].stderr,
                                       'unit' : 'Occurrences'}

            param_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}


            return hist_fit_x, hist_fit_y, param_dict, result

    def do_doublegaussian_fit(self, axis, data):
        model, params = self._fit_logic.make_gaussiandouble_model()

        if len(axis) < len(params):
            self.log.warning('Fit could not be performed because number of '
                    'parameters is smaller than data points')
            return self.do_no_fit()

        else:
            result = self._fit_logic.make_twogausspeakoffset_fit(x_axis=axis,
                                                                 data=data)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # this dict will be passed to the formatting method
            param_dict = OrderedDict()

            # create the proper param_dict with the values:
            param_dict['sigma_0'] = {'value': result.params['g0_sigma'].value,
                                     'error': result.params['g0_sigma'].stderr,
                                     'unit' : 'Counts/s'}

            param_dict['FWHM_0'] = {'value': result.params['g0_fwhm'].value,
                                    'error': result.params['g0_fwhm'].stderr,
                                    'unit' : 'Counts/s'}

            param_dict['Center_0'] = {'value': result.params['g0_center'].value,
                                      'error': result.params['g0_center'].stderr,
                                      'unit' : 'Counts/s'}

            param_dict['Amplitude_0'] = {'value': result.params['g0_amplitude'].value,
                                         'error': result.params['g0_amplitude'].stderr,
                                         'unit' : 'Occurrences'}

            param_dict['sigma_1'] = {'value': result.params['g1_sigma'].value,
                                     'error': result.params['g1_sigma'].stderr,
                                     'unit' : 'Counts/s'}

            param_dict['FWHM_1'] = {'value': result.params['g1_fwhm'].value,
                                    'error': result.params['g1_fwhm'].stderr,
                                    'unit' : 'Counts/s'}

            param_dict['Center_1'] = {'value': result.params['g1_center'].value,
                                      'error': result.params['g1_center'].stderr,
                                      'unit' : 'Counts/s'}

            param_dict['Amplitude_1'] = {'value': result.params['g1_amplitude'].value,
                                         'error': result.params['g1_amplitude'].stderr,
                                         'unit' : 'Occurrences'}

            param_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

            return hist_fit_x, hist_fit_y, param_dict, result

    def do_doublepossonian_fit(self, axis, data):
        model, params = self._fit_logic.make_multiplepoissonian_model(no_of_functions=2)
        if len(axis) < len(params):
            self.log.warning('Fit could not be performed because number of '
                    'parameters is smaller than data points')
            return self.do_no_fit()

        else:
            result = self._fit_logic.make_doublepoissonian_fit(x_axis=axis,
                                                               data=data,
                                                               add_params=None)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # this dict will be passed to the formatting method
            param_dict = OrderedDict()

            # create the proper param_dict with the values:
            param_dict['lambda_0'] = {'value': result.params['p0_mu'].value,
                                     'error': result.params['p0_mu'].stderr,
                                     'unit' : 'Counts/s'}
            param_dict['Amplitude_0'] = {'value': result.params['p0_amplitude'].value,
                                         'error': result.params['p0_amplitude'].stderr,
                                         'unit' : 'Occurrences'}
            param_dict['lambda_1'] = {'value': result.params['p1_mu'].value,
                                     'error': result.params['p1_mu'].stderr,
                                     'unit' : 'Counts/s'}
            param_dict['Amplitude_1'] = {'value': result.params['p1_amplitude'].value,
                                         'error': result.params['p1_amplitude'].stderr,
                                         'unit' : 'Occurrences'}

            param_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}
            # removed last return value <<result>> here, because function calculate_threshold only expected
            # three return values
            return hist_fit_x, hist_fit_y, param_dict

    def do_possonian_fit(self, axis, data):
        model, params = self._fit_logic.make_poissonian_model()
        if len(axis) < len(params):
            self.log.error('Fit could not be performed because number of '
                    'parameters is smaller than data points')
            return self.do_no_fit()
        else:
            result = self._fit_logic.make_poissonian_fit(x_axis=axis,
                                                         data=data,
                                                         add_params=None)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # this dict will be passed to the formatting method
            param_dict = OrderedDict()

            # create the proper param_dict with the values:
            param_dict['lambda'] = {'value': result.params['mu'].value,
                                    'error': result.params['mu'].stderr,
                                    'unit' : 'Counts/s'}

            param_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

            return hist_fit_x, hist_fit_y, param_dict, result

    def get_poissonian(self, x_val, mu, amplitude):
        """ Calculate, bases on the passed values a poisson distribution.

        @param float mu: expected value of poisson distribution
        @param float amplitude: Amplitude to which is multiplied on distribution
        @param int,float or np.array x_val: x values for poisson distribution,
                                            also works for numbers (int or float)
        @return np.array: a 1D array with the calculated poisson distribution,
                          corresponding to given parameters/ x values

        Calculate a Poisson distribution according to:
            P(k) =  mu^k * exp(-mu) / k!
        """

        model, params = self._fit_logic.make_poissonian_model()

        return model.eval(x=np.array(x_val), poissonian_mu=mu, poissonian_amplitude=amplitude)

    def guess_threshold(self, hist_val=None, trace=None, max_ratio_value=0.1):
        """ Assume a distribution between two values and try to guess the threshold.

        @param np.array hist_val: 1D array whitch represent the y values of a
                                    histogram of a trace. Optional, if None
                                    is passed here, the passed trace will be
                                    used for calculations.
        @param np.array trace: optional, 1D array containing the y values of a
                               meausured counter trace. If None is passed to
                               hist_y_val then the threshold will be calculated
                               from the trace.
        @param float max_ration_value: the ratio how strong the lower y values
                                       will be cut off. For max_ratio_value=0.1
                                       all the data which are 10% or less in
                                       amptitude compared to the maximal value
                                       are neglected.

        The guess procedure tries to find all values, which are
        max_ratio_value * maximum value of the histogram of the trace and
        selects those by indices. Then taking the first an the last might and
        assuming that the threshold is in the middle, gives a first estimate
        of the threshold value.

        FIXME: That guessing procedure can be improved!

        @return float: a guessed threshold
        """

        if hist_val is None and trace is not None:
            hist_val = self.calculate_histogram(trace)

        hist_val = np.array(hist_val)   # just to be sure to have a np.array
        indices_arr = np.where(hist_val[1] > hist_val[1].max() * max_ratio_value)[0]
        guessed_threshold = hist_val[0][int((indices_arr[-1] + indices_arr[0])/2)]

        return guessed_threshold

    def calculate_threshold(self, hist_data=None, distr='poissonian'):
        """ Calculate the threshold by minimizing its overlap with the poissonian fits.

        @param np.array hist_data: 2D array whitch represent the x and y values
                                   of a histogram of a trace.
               string distr: tells the function on what distribution it should calculate
                             the threshold ( Added because it might happen that one normalizes data
                             between (-1,1) and then a poissonian distribution won't work anymore.

        @return tuple(float, float):
                    threshold: the calculated threshold between two overlapping
                               poissonian distributed peaks.
                    fidelity: the measure how good the two peaks are resolved
                              according to the calculated threshold

        The calculation of the threshold relies on fitting two poissonian
        distributions to the count histogram and minimize a threshold with
        respect to the overlap area:

        """
        # in any case calculate the hist data
        x_axis = hist_data[0][:-1] + (hist_data[0][1] - hist_data[0][0]) / 2.
        y_data = hist_data[1]
        if distr == 'poissonian':
            # perform the fit

            hist_fit_x, hist_fit_y, param_dict = self.do_doublepossonian_fit(x_axis, y_data)

            if param_dict.get('lambda_0') is None:
                self.log.error('The double poissonian fit does not work! Take at '
                            'least a dummy value, in order not to break the '
                            'routine.')
                amp0 = 1
                amp1 = 1

                param_dict['Amplitude_0'] = {'value': amp0, 'unit': 'occurences'}
                param_dict['Amplitude_1'] = {'value': amp0, 'unit': 'occurences'}

                # make them a bit different so that fit works.
                mu0 = hist_data[0][:].mean()-0.1
                mu1 = hist_data[0][:].mean()+0.1

                param_dict['lambda_0'] = {'value': mu0, 'unit': 'counts'}
                param_dict['lambda_1'] = {'value': mu1, 'unit': 'counts'}

            else:

                mu0 = param_dict['lambda_0']['value']
                mu1 = param_dict['lambda_1']['value']

                amp0 = param_dict['Amplitude_0']['value']
                amp1 = param_dict['Amplitude_1']['value']

            if mu0 < mu1:
                first_dist = self.get_poissonian(x_val=hist_data[0], mu=mu0, amplitude=amp0)
                sec_dist = self.get_poissonian(x_val=hist_data[0], mu=mu1, amplitude=amp1)
            else:
                first_dist = self.get_poissonian(x_val=hist_data[0], mu=mu1, amplitude=amp1)
                sec_dist = self.get_poissonian(x_val=hist_data[0], mu=mu0, amplitude=amp0)

            # create a two poissonian array, where the second poissonian
            # distribution is add as negative values. Now the transition from
            # positive to negative values will get the threshold:
            difference_poissonian = first_dist - sec_dist

            trans_index = 0
            for i in range(len(difference_poissonian)-1):
                # go through the combined histogram array and the point which
                # changes the sign. The transition from positive to negative values
                # will get the threshold:
                if difference_poissonian[i] < 0 and difference_poissonian[i+1] >= 0:
                    trans_index = i
                    break
                elif difference_poissonian[i] > 0 and difference_poissonian[i+1] <= 0:
                    trans_index = i
                    break

            threshold_fit = hist_data[0][trans_index]

            # Calculate also the readout fidelity, i.e. sum the area under the
            # first peak before the threshold of the first and second distribution
            # and take the ratio of that area. Do the same thing after the threshold
            # (of course with a reversed choice of the distribution). If the overlap
            # in both cases is very small, then the fidelity is good, if the overlap
            # is identical, then fidelity indicates a poor separation of the peaks.

            if mu0 < mu1:
                area0_low = self.get_poissonian(hist_data[0][0:trans_index], mu0, 1).sum()
                area0_high = self.get_poissonian(hist_data[0][trans_index:], mu0, 1).sum()
                area1_low = self.get_poissonian(hist_data[0][0:trans_index], mu1, 1).sum()
                area1_high = self.get_poissonian(hist_data[0][trans_index:], mu1, 1).sum()

                area0_low_amp = self.get_poissonian(hist_data[0][0:trans_index], mu0, amp0).sum()
                area0_high_amp = self.get_poissonian(hist_data[0][trans_index:], mu0, amp0).sum()
                area1_low_amp = self.get_poissonian(hist_data[0][0:trans_index], mu1, amp1).sum()
                area1_high_amp = self.get_poissonian(hist_data[0][trans_index:], mu1, amp1).sum()

            else:
                area1_low = self.get_poissonian(hist_data[0][0:trans_index], mu0, 1).sum()
                area1_high = self.get_poissonian(hist_data[0][trans_index:], mu0, 1).sum()
                area0_low = self.get_poissonian(hist_data[0][0:trans_index], mu1, 1).sum()
                area0_high = self.get_poissonian(hist_data[0][trans_index:], mu1, 1).sum()

                area1_low_amp = self.get_poissonian(hist_data[0][0:trans_index], mu0, amp0).sum()
                area1_high_amp = self.get_poissonian(hist_data[0][trans_index:], mu0, amp0).sum()
                area0_low_amp = self.get_poissonian(hist_data[0][0:trans_index], mu1, amp1).sum()
                area0_high_amp = self.get_poissonian(hist_data[0][trans_index:], mu1, amp1).sum()

            # Now calculate how big is the overlap relative to the sum of the other
            # part of the area, that will give the normalized fidelity:
            fidelity = 1 - (area1_low / area0_low + area0_high / area1_high) / 2

            area0 = self.get_poissonian(hist_data[0][:], mu0, amp0).sum()
            area1 = self.get_poissonian(hist_data[0][:], mu1, amp1).sum()

            # try this new measure for the fidelity
            fidelity2 = 1 - ((area1_low_amp/area1) / (area0_low_amp/area0) + (area0_high_amp/area0) / (area1_high_amp/area1) ) / 2

            param_dict['normalized_fidelity'] = fidelity2

            return threshold_fit, fidelity, param_dict

        # this works if your data is normalized to the interval (-1,1)
        if distr == 'gaussian_normalized':
            # first some helper functions
            def two_gaussian_intersect(m1, m2, std1, std2, amp1, amp2):
                """
                function to calculate intersection of two gaussians
                """
                a = 1 / (2 * std1 ** 2) - 1 / (2 * std2 ** 2)
                b = m2 / (std2 ** 2) - m1 / (std1 ** 2)
                c = m1 ** 2 / (2 * std1 ** 2) - m2 ** 2 / (2 * std2 ** 2) - np.log(amp2 / amp1)
                return np.roots([a, b, c])

            def gaussian(counts, amp, stdv, mean):
                return amp * np.exp(-(counts - mean) ** 2 / (2 * stdv ** 2)) / (stdv * np.sqrt(2 * np.pi))

            try:
                result = self._fit_logic.make_twogausspeakoffset_fit(x_axis, y_data)
                # calculating the threshold
                # NOTE the threshold is taken as the intersection of the two gaussians, while this should give
                # a good approximation I doubt it is mathematical exact.

                mu0 = result.params['g0_center'].value
                mu1 = result.params['g1_center'].value
                sigma0 = result.params['g0_sigma'].value
                sigma1 = result.params['g1_sigma'].value
                amp0 = result.params['g0_amplitude'].value / (sigma0 * np.sqrt(2 * np.pi))
                amp1 = result.params['g1_amplitude'].value / (sigma1 * np.sqrt(2 * np.pi))
                candidates = two_gaussian_intersect(mu0, mu1, sigma0, sigma1, amp0, amp1)

                # we want to get the intersection that lies between the two peaks
                if mu0 < mu1:
                    threshold = [i for i in filter(lambda x: (x > mu0) & (x < mu1), candidates)]
                else:
                    threshold = [i for i in filter(lambda x: (x < mu0) & (x > mu1), candidates)]

                threshold = threshold[0]

                # now we want to get the readout fidelity
                # of the bigger peak ( most likely the two states that aren't driven by the mw pi pulse )
                if mu0 < mu1:
                    gc0 = integrate.quad(lambda counts: gaussian(counts, amp1, sigma1, mu1), -1, 1)
                    gp0 = integrate.quad(lambda counts: gaussian(counts, amp1, sigma1, mu1), -1, threshold)
                else:
                    gc0 = integrate.quad(lambda counts: gaussian(counts, amp0, sigma0, mu0), -1, 1)
                    gp0 = integrate.quad(lambda counts: gaussian(counts, amp0, sigma0, mu0), -1, threshold)

                # and then the same for the other peak ]

                if mu0 > mu1:
                    gc1 = integrate.quad(lambda counts: gaussian(counts, amp1, sigma1, mu1), -1, 1)
                    gp1 = integrate.quad(lambda counts: gaussian(counts, amp1, sigma1, mu1), threshold, 1)
                else:
                    gc1 = integrate.quad(lambda counts: gaussian(counts, amp0, sigma0, mu0), -1, 1)
                    gp1 = integrate.quad(lambda counts: gaussian(counts, amp0, sigma0, mu0), threshold, 1)

                param_dict = {}
                fidelity = 1 - (gp0[0] / gc0[0] + gp1[0] / gc1[0])/2
                fidelity1 = 1 - (gp0[0] / gc0[0])
                fidelity2 = 1 - gp1[0] / gc1[0]
                threshold_fit = threshold
                # if the fit worked, add also the result to the param_dict, which might be useful for debugging
                param_dict['result'] = result
            except:
                self.log.error('could not fit the data')
                error= True
                fidelity = 0
                threshold_fit = 0
                param_dict = {}
                new_dict = {}
                new_dict['value'] = np.inf
                param_dict['chi_sqr'] = new_dict

            return threshold_fit, fidelity, param_dict




    def calculate_binary_trace(self, trace, threshold):
        """ Calculate for a given threshold all the trace values und output a
            binary array, where
                True = Below or equal Threshold
                False = Above Threshold.

        @param np.array trace: a 1D array containing the y data, e.g. ccunts
        @param float threshold: value to decide whether a point in the trace
                                is below/equal (True) or above threshold (False).

        @return np.array: 1D trace of the length(trace) but now with boolean
                          entries
        """
        return trace <= threshold

    def extract_filtered_values(self, trace, threshold, below=True):
        """ Extract only those values, which are below or equal a certain Threshold.

        @param np.array trace:
        @param float threshold:

        @return tuple(index_array, filtered_array):
                    np.array index_array: 1D integer array containing the
                                          indices of the passed trace array
                                          which are equal or below the threshold
                    np.array filtered_array: the actual values of the trace,
                                             which are equal or below threshold
        """
        if below:
            index_array = np.where(trace <= threshold)[0]
        else:
            index_array = np.where(trace > threshold)[0]
        filtered_array = trace[index_array]
        return index_array, filtered_array

