# -*- coding: utf-8 -*-
"""
This file contains the QuDi gated counter logic class.

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

from logic.generic_logic import GenericLogic
from PyQt4 import QtCore
import numpy as np
import time
import scipy.misc
from scipy.stats import poisson
from scipy.signal import  gaussian
from scipy.ndimage import filters
from scipy.interpolate import InterpolatedUnivariateSpline

class TraceAnalysisLogic(GenericLogic):
    """ Perform a gated counting measurement with the hardware.  """

    _modclass = 'TraceAnalysisLogic'
    _modtype = 'logic'

    ## declare connectors
    _in = {'counterlogic1': 'CounterLogic',
           'savelogic': 'SaveLogic',
           'fitlogic': 'FitLogic',
            }

    _out = {'traceanalysislogic1': 'TraceAnalysisLogic'}

    sigHistogramUpdated = QtCore.Signal()


    def __init__(self, manager, name, config, **kwargs):
        """ Create CounterLogic object with connectors.

        @param object manager: Manager object thath loaded this module
        @param str name: unique module name
        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        self.hist_data = None
        self._hist_num_bins = None

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

        self._counter_logic = self.connector['in']['counterlogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']

        self._counter_logic.sigGatedCounterFinished.connect(self.do_calculate_histogram)

        self.current_fit_function = 'No Fit'

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
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

    def do_calculate_histogram(self):
        """ Passes all the needed parameters to the appropriated methods.

        @return:
        """

        self.hist_data = self.calculate_histogram(self._counter_logic.countdata,
                                                  self._hist_num_bins)
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
            if np.isclose(0, difference) or num_bins is None:
                # numpy can handle an array of zeros
                hist_y_val, hist_x_val = np.histogram(trace)
            else:
                # a histogram with self defined number of bins
                hist_y_val, hist_x_val = np.histogram(trace, num_bins)

        return hist_x_val, hist_y_val


    def analyze_flip_prob(self, trace, ):
        """ General method, which analysis how often a value was changed from
            one data point to another in relation to a certain threshold.

        @return:
        """
        # # check whether the passed trace is a numpy array:
        # if not type(trace).__module__ == np.__name__:
        #     trace = np.array(trace)
        pass


    def analyze_flip_prob_postselect(self):
        """ Post select the data trace so that the flip probability is only
            calculated from a jump from below a threshold value to an value
            above threshold.

        @return:
        """
        pass

    def get_fit_methods(self):
        """ Return all fit methods, which are currently implemented for that module.

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
            fit_result = 'No data to fit in histogram.'
            return hist_fit_x, hist_fit_y, fit_result
        else:
            # shift x axis to middle of bin
            axis = self.hist_data[0][:-1]+(self.hist_data[0][1]-self.hist_data[0][0])/2.
            data = self.hist_data[1]
            if fit_function == 'No Fit':
                hist_fit_x, hist_fit_y, fit_result = self.do_no_fit()
                return hist_fit_x, hist_fit_y, fit_result
            elif fit_function == 'Gaussian':
                hist_fit_x, hist_fit_y, fit_result = self.do_gaussian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_result
            elif fit_function == 'Double Gaussian':
                hist_fit_x, hist_fit_y, fit_result = self.do_doublegaussian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_result
            elif fit_function == 'Poisson':
                hist_fit_x, hist_fit_y, fit_result = self.do_possonian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_result
            elif fit_function == 'Double Poisson':
                hist_fit_x, hist_fit_y, fit_result = self.do_doublepossonian_fit(axis, data)
                return hist_fit_x, hist_fit_y, fit_result

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
        fit_result = 'No Fit'
        return hist_fit_x, hist_fit_y, fit_result

    def do_gaussian_fit(self, axis, data):
        """ Perform a gaussian fit.

        @param axis:
        @param data:
        @return:
        """

        model, params = self._fit_logic.make_gaussian_model()
        if len(axis) < len(params):
            self.logMsg('Fit could not be performed because number of '
                        'parameters is smaller than data points.',
                        msgType='warning')
            return self.do_no_fit()

        else:

            parameters_to_substitute = dict()
            update_dict=dict()

            #Todo: move this to "gated counter" estimator in fitlogic
            #make the filter an extra function shared and usable for other functions
            gaus = gaussian(10, 10)
            data_smooth = filters.convolve1d(data, gaus/gaus.sum(),mode='mirror')

            # integral of data corresponds to sqrt(2) * Amplitude * Sigma
            function = InterpolatedUnivariateSpline(axis, data_smooth, k=1)
            Integral = function.integral(axis[0], axis[-1])
            amp = data_smooth.max()
            sigma = Integral / (amp) / np.sqrt(2 * np.pi)
            amplitude = amp * sigma * np.sqrt(2 * np.pi)

            update_dict['c'] = {'min': 0, 'max': data.max(), 'value': 0, 'vary': False}
            update_dict['center'] = {'min': axis.min(), 'max': axis.max(), 'value': axis[np.argmax(data)]}
            update_dict['sigma'] = {'min': -np.inf, 'max': np.inf, 'value': sigma}
            update_dict['amplitude'] = {'min': 0, 'max': np.inf, 'value': amplitude}

            result = self._fit_logic.make_gaussian_fit(axis=axis,
                                                       data=data,
                                                       add_parameters=update_dict)
            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # units = {'center': 'cts/s',
            #          'c': '#',
            #          'amplitude': '#',
            #          'sigma': 'cts/s'}
            # fit_result = self._fit_logic.create_fit_string(result, model, units=units)
            fit_result = str("Center (Counts/s): {:.1f} \n".format(result.best_values['center']))
            return hist_fit_x, hist_fit_y, fit_result

    def do_doublegaussian_fit(self, axis, data):
        model, params = self._fit_logic.make_multiplegaussian_model(no_of_gauss=2)
        if len(axis) < len(params):
            self.logMsg('Fit could not be performed because number of '
                        'parameters is smaller than data points',
                        msgType='warning')
            return self.do_no_fit()

        else:
            result = self._fit_logic.make_doublegaussian_fit(axis=axis,
                                                             data=data,
                                                             add_parameters=None)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # units = {'gaussian0_center': 'cts/s',
            #          'gaussian1_center': 'cts/s',
            #          'gaussian0_sigma': 'cts/s',
            #          'gaussian1_sigma': 'cts/s',
            #          'gaussian0_amplitude': '#',
            #          'gaussian1_amplitude': '#',
            #          'c': '#'}
            # fit_result = self._fit_logic.create_fit_string(result, model, units=units)
            fit_result = str("Center 1 (kCounts/s): {:.1f} \nCenter 2 (kCounts/s): {:.1f}".format(
                result.best_values['gaussian0_center']/1e3, result.best_values['gaussian1_center']/1e3))
            return hist_fit_x, hist_fit_y, fit_result

    def do_doublepossonian_fit(self, axis, data):
        model, params = self._fit_logic.make_poissonian_model(no_of_functions=2)
        if len(axis) < len(params):
            return self.do_no_fit()
            self.logMsg('Fit could not be performed because number of parameters is smaller than data points',
                        msgType='warning')
        else:
            result = self._fit_logic.make_doublepoissonian_fit(axis=axis,
                                                               data=data,
                                                               add_parameters=None)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # units = {'poissonian0_mu', 'Counts/s',
            #          'poissonian1_mu', 'kCounts/s'}
            # fit_result = self._fit_logic.create_fit_string(result, doublepoissonian, units=units)
            fit_result = str("poissonian0_mu (kCounts/s): {:.1f} \npoissonian1_mu (kCounts/s): {:.1f}".format(
                result.best_values['poissonian0_mu']/1e3, result.best_values['poissonian1_mu']/1e3))
            return hist_fit_x, hist_fit_y, fit_result

    def do_possonian_fit(self, axis, data):
        model, params = self._fit_logic.make_poissonian_model()
        if len(axis) < len(params):
            self.logMsg('Fit could not be performed because number of parameters is smaller than data points',
                        msgType='error')
            return self.do_no_fit()
        else:
            result = self._fit_logic.make_poissonian_fit(axis=axis,
                                                               data=data,
                                                               add_parameters=None)

            # 1000 points in x axis for smooth fit data
            hist_fit_x = np.linspace(axis[0], axis[-1], 1000)
            hist_fit_y = model.eval(x=hist_fit_x, params=result.params)

            # units = {'poissonian0_mu', 'Counts/s',
            #          'poissonian1_mu', 'kCounts/s'}
            # fit_result = self._fit_logic.create_fit_string(result, doublepoissonian, units=units)
            fit_result = str("poissonian_mu (Counts/s): {:.1f}".format(result.best_values['poissonian_mu']))
            return hist_fit_x, hist_fit_y, fit_result

    def get_poissonian(self, x_val, mu):
        """ Calculate, bases on the passed values a poissonian distribution.

        @param float mu:
        @param x_val:
        @return np.array: a 2D array with the given x axis and the calculated
                          values for the y axis.

        Calculate a Poissonian Distribution according to:
            P(k) =  mu^k * exp(-mu) / k!
        """

        return self._fit_logic.poisson(x_val, mu)

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


    def calculate_threshold(self, hist_val=None, trace=None, threshold=None):
        """ Calculate the threshold by minimizing its overlap with the poissonian fits.

        @param np.array hist_val: 1D array whitch represent the y values of a
                                    histogram of a trace. Optional, if None
                                    is passed here, the passed trace will be
                                    used for calculations.
        @param np.array trace: optional, 1D array containing the y values of a
                               meausured counter trace. If None is passed to
                               hist_y_val then the threshold will be calculated
                               from the trace.
        @param float threshold: optional, pass an estimated threshold, otherwise
                                it will be calculated.
        @return tuple(float, float):
                    threshold: the calculated threshold between two overlapping
                               poissonian distributed peaks.
                    fidelity: the measure how good the two peaks are resolved
                              according to the calculated threshold

        The calculation of the threshold relies on fitting two poissonian
        distributions to the count histogram and minimize a threshold with
        respect to the overlap area:

        """

        if threshold is None:
            threshold = self.guess_threshold(hist_val=hist_val, trace=trace)

        # perform the fit, maybe more fitting parameter will come
        #Fixme: This won't work, defitinion of fit and get_poissonian is not appropriate
        mu1, mu2 = self.do_double_possonian_fit(hist_val, threshold)

        first_dist = self.get_poissonian(x_val=hist_val, mu=mu1)
        sec_dist = self.get_poissonian(x_val=hist_val, mu=mu1)

        # create a two poissonian array, where the second poissonian
        # distribution is add as negative values. Now the transition from
        # positive to negative values will get the threshold:
        difference_poissonian = first_dist[1] - sec_dist[1]

        trans_index = 0
        for i in range(len(difference_poissonian)-1):
            # go through the combined histogram array and the point which
            # changes the sign. The transition from positive to negative values
            # will get the threshold:
            if difference_poissonian[i] < 0 and difference_poissonian[i+1] >= 0:
                trans_index = i+1
                break
            elif difference_poissonian[i] > 0 and difference_poissonian[i+1] <= 0:
                trans_index = i+1
                break

        threshold_fit = hist_val[trans_index]

        # Calculate also the readout fidelity, i.e. sum the area under the
        # first peak before the threshold and after it and sum also the area
        # under the second peak before the threshold and after it:
        area1_low = self.get_poissonian(hist_val[0:trans_index], mu1).sum()
        area1_high = self.get_poissonian(hist_val[trans_index:], mu1).sum()
        area2_low = self.get_poissonian(hist_val[0:trans_index], mu2).sum()
        area2_high = self.get_poissonian(hist_val[trans_index:], mu2).sum()

        # Now calculate how big is the overlap relative to the sum of the other
        # part of the area, that will give the normalized fidelity:
        fidelity = 1 - (area2_low / area1_low + area1_high / area2_high) / 2

        return threshold, fidelity



    def calculate_binary_trace(self, trace, threshold):
        """ Calculate for a given threshold all the trace values und output a
            binary array, where
                True = Below or equal Threshold
                False = Above Threshold.

        @param trace:
        @param threshold:
        @return:
        """
        pass


    def extract_filtered_values(self, trace, threshold, as_binary=False):
        """ Extract only those values, which are below a certain Threshold.

        @param trace:
        @param threshold:
        @return:
        """
        pass
