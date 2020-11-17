# -*- coding: utf-8 -*-
"""
This file contains methods for decay-like fitting, these methods
are imported by class FitLogic.

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

import numpy as np
from lmfit.models import Model
from scipy.ndimage import filters


############################################################################
#                                                                          #
#               Defining Exponential Models                                #
#                                                                          #
############################################################################

####################################################
#  General case: bare stretched exponential decay  #
####################################################

def make_barestretchedexponentialdecay_model(self, prefix=None):
    """ Create a general bare exponential decay model.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params)

    Explanation of the objects:
        object lmfit.model.CompositeModel model:
            A model the lmfit module will use for that fit. Here a
            gaussian model. Returns an object of the class
            lmfit.model.CompositeModel.

        object lmfit.parameter.Parameters params:
            It is basically a dictionary, with keys
            denoting the parameters as string names and values which are
            lmfit.parameter.Parameter (without s) objects, keeping the
            information about the current value.

    """

    def barestretchedexponentialdecay_function(x, beta, lifetime):
        """ Function of a bare exponential decay.

        @param numpy.array x: 1D array as the independent variable - e.g. time
        @param float lifetime: constant lifetime

        @return: bare exponential decay function: in order to use it as a model
        """
        return np.exp(-np.power(x / lifetime, beta))

    if not isinstance(prefix, str) and prefix is not None:

        self.log.error('The passed prefix <{0}> of type {1} is not a string and'
                       'cannot be used as a prefix and will be ignored for now.'
                       'Correct that!'.format(prefix, type(prefix)))
        model = Model(barestretchedexponentialdecay_function,
                      independent_vars='x')
    else:
        model = Model(barestretchedexponentialdecay_function,
                      independent_vars='x', prefix=prefix)

    params = model.make_params()

    return model, params


##############################
#  Single exponential decay  #
##############################

def make_bareexponentialdecay_model(self, prefix=None):
    """ Create a bare single exponential decay model.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_barestretchedexponentialdecay_model.
    """

    bare_exp_decay, params = self.make_barestretchedexponentialdecay_model(prefix=prefix)

    bare_exp_decay.set_param_hint(name='beta', value=1, vary=False)
    params = bare_exp_decay.make_params()

    return bare_exp_decay, params


def make_decayexponential_model(self, prefix=None):
    """ Create a exponential decay model with an amplitude and offset.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_barestretchedexponentialdecay_model.
    """

    bare_exp_model, params = self.make_bareexponentialdecay_model(prefix=prefix)

    amplitude_model, params = self.make_amplitude_model(prefix=prefix)

    constant_model, params = self.make_constant_model(prefix=prefix)

    exponentialdecay_model = amplitude_model * bare_exp_model + constant_model
    params = exponentialdecay_model.make_params()

    return exponentialdecay_model, params


#################################
#  Stretched exponential decay  #
#################################

def make_decayexponentialstretched_model(self, prefix=None):
    """ Create a stretched exponential decay model with offset.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_barestretchedexponentialdecay_model.
    """

    bare_stre_exp_decay, params = self.make_barestretchedexponentialdecay_model(prefix=prefix)
    amplitude_model, params = self.make_amplitude_model()
    constant_model, params = self.make_constant_model(prefix=prefix)

    stre_exp_decay_offset = amplitude_model * bare_stre_exp_decay + constant_model
    params = stre_exp_decay_offset.make_params()

    return stre_exp_decay_offset, params


#################################
#      Biexponential decay      #
#################################

def make_biexponential_model(self, prefix=None):
    """ Create a exponential model with an amplitude and offset.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_barestretchedexponential_model.
    """

    exp0_model, params = self.make_bareexponentialdecay_model(prefix='e0_')
    amp0_model, params = self.make_amplitude_model(prefix='e0_')

    exp1_model, params = self.make_bareexponentialdecay_model(prefix='e1_')
    amp1_model, params = self.make_amplitude_model(prefix='e1_')

    constant_model, params = self.make_constant_model(prefix=prefix)

    exponential_model = amp0_model * exp0_model + amp1_model * exp1_model + constant_model
    params = exponential_model.make_params()

    return exponential_model, params


############################################################################
#                                                                          #
#                Fit methods and their estimators                          #
#                                                                          #
############################################################################

##########################################
#  single exponential decay with offset  #
##########################################

def make_decayexponential_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Performes a exponential decay with offset fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    exponentialdecay, params = self.make_decayexponential_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = exponentialdecay.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = exponentialdecay.fit(data, x=x_axis, params=params, **kwargs)
        self.log.warning('The exponentialdecay with offset fit did not work. '
                         'Message: {}'.format(str(result.message)))

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui

    result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                    'error': result.params['amplitude'].stderr,
                                    'unit': units[1]}  # amplitude

    result_str_dict['Lifetime'] = {'value': result.params['lifetime'].value,
                                   'error': result.params['lifetime'].stderr,
                                   'unit': units[0]}  # lifetime

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}  # offset

    result.result_str_dict = result_str_dict

    return result


def estimate_decayexponential(self, x_axis, data, params):
    """ Estimation of the initial values for an exponential decay function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # calculation of offset, take the last 10% from the end of the data
    # and perform the mean from those.
    offset = data[-max(1, int(len(x_axis) / 10)):].mean()

    # substraction of offset, check whether
    if data[0] < data[-1]:
        data_level = offset - data
    else:
        data_level = data - offset

    # check if the data level contain still negative values and correct
    # the data level therefore. Otherwise problems in the logarithm appear.
    if data_level.min() <= 0:
        data_level = data_level - data_level.min()

    # remove all the data that can be smaller than or equals to std.
    # when the data is smaller than std, it is beyond resolution
    # which is not helpful to our fitting.
    for i in range(0, len(x_axis)):
        if data_level[i] <= data_level.std():
            break

    # values and bound of parameter.
    ampl = data[-max(1, int(len(x_axis) / 10)):].std()
    min_lifetime = 2 * (x_axis[1] - x_axis[0])

    try:
        data_level_log = np.log(data_level[0:i])

        # linear fit, see linearmethods.py
        linear_result = self.make_linear_fit(x_axis=x_axis[0:i], data=data_level_log, estimator=self.estimate_linear)
        params['lifetime'].set(value=-1 / linear_result.params['slope'].value, min=min_lifetime)

        # amplitude can be positive of negative
        if data[0] < data[-1]:
            params['amplitude'].set(value=-np.exp(linear_result.params['offset'].value), max=-ampl)
        else:
            params['amplitude'].set(value=np.exp(linear_result.params['offset'].value), min=ampl)
    except:
        self.log.warning('Lifetime too small in estimate_exponentialdecay, beyond resolution!')

        params['lifetime'].set(value=x_axis[i] - x_axis[0], min=min_lifetime)
        params['amplitude'].set(value=data_level[0])

    params['offset'].set(value=offset)

    return error, params


#############################################
#  stretched exponential decay with offset  #
#############################################

def make_decayexponentialstretched_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Performes a stretched exponential decay with offset fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param object estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    stret_exp_decay_offset, params = self.make_decayexponentialstretched_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = stret_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = stret_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
        self.log.warning('The double exponentialdecay with offset fit did not work. '
                         'Message: {}'.format(str(result.message)))

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui

    result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                    'error': result.params['amplitude'].stderr,
                                    'unit': units[1]}  # amplitude

    result_str_dict['Lifetime'] = {'value': result.params['lifetime'].value,
                                   'error': result.params['lifetime'].stderr,
                                   'unit': units[0]}  # lifetime

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}  # offset

    result_str_dict['Beta'] = {'value': result.params['beta'].value,
                               'error': result.params['beta'].stderr,
                               'unit': ''}  # Beta (exponent of exponential exponent)

    result.result_str_dict = result_str_dict

    return result


def estimate_decayexponentialstretched(self, x_axis, data, params):
    """ Provide an estimation for initial values for a stretched exponential decay with offset.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # Smooth very radically the provided data, so that noise fluctuations will
    # not disturb the parameter estimation.
    std_dev = 10
    data_smoothed = filters.gaussian_filter1d(data, std_dev)

    # calculation of offset, take the last 10% from the end of the data
    # and perform the mean from those.
    offset = data_smoothed[-max(1, int(len(x_axis) / 10)):].mean()

    # substraction of the offset and correction of the decay behaviour
    # (decay to a bigger value or decay to a smaller value)
    if data_smoothed[0] < data_smoothed[-1]:
        data_smoothed = offset - data_smoothed
        ampl_sign = -1
    else:
        data_smoothed = data_smoothed - offset
        ampl_sign = 1

    if data_smoothed.min() <= 0:
        data_smoothed = data_smoothed - data_smoothed.min()

    # Take all values up to the standard deviation, the remaining values are
    # more disturbing the estimation then helping:
    for stop_index in range(0, len(x_axis)):
        if data_smoothed[stop_index] <= data_smoothed.std():
            break

    data_level_log = np.log(data_smoothed[0:stop_index])

    # make a polynomial fit with a second order polynom on the remaining data:
    poly_coef = np.polyfit(x_axis[0:stop_index], data_level_log, deg=2)

    # obtain the values from the polynomical fit
    lifetime = 1 / np.sqrt(abs(poly_coef[0]))
    amplitude = np.exp(poly_coef[2])

    # Include all the estimated fit parameter:
    params['amplitude'].set(value=amplitude * ampl_sign)
    params['offset'].set(value=offset)

    min_lifetime = 2 * (x_axis[1] - x_axis[0])
    params['lifetime'].set(value=lifetime, min=min_lifetime)

    # as an arbitrary starting point:
    params['beta'].set(value=2, min=0)

    return error, params


#############################################
#  biexponential function with offset       #
#############################################


def make_biexponential_fit(self, x_axis, data, estimator,
                           units=None,
                           add_params=None, **kwargs):
    """ Perform a biexponential fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, dict for the fit
                which will be used instead of the values from the estimator.

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...
    """
    if units is None:
        units = ['arb. unit', 'arb. unit']

    model, params = self.make_biexponential_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
        self.log.warning('The double gaussian dip fit did not work: {0}'.format(
            result.message))

    # Write the parameters to allow human-readable output to be generated
    result_str_dict = dict()

    result_str_dict['1st amplitude'] = {'value': result.params['e0_amplitude'].value,
                                        'error': result.params['e0_amplitude'].stderr,
                                        'unit': units[1]}  # amplitude

    result_str_dict['1st lifetime'] = {'value': result.params['e0_lifetime'].value,
                                       'error': result.params['e0_lifetime'].stderr,
                                       'unit': units[0]}  # lifetime

    result_str_dict['1st beta'] = {'value': result.params['e0_beta'].value,
                                   'error': result.params['e0_beta'].stderr,
                                   'unit': ''}  # Beta (exponent of exponential exponent)

    result_str_dict['2nd amplitude'] = {'value': result.params['e1_amplitude'].value,
                                        'error': result.params['e1_amplitude'].stderr,
                                        'unit': units[1]}  # amplitude

    result_str_dict['2nd lifetime'] = {'value': result.params['e1_lifetime'].value,
                                       'error': result.params['e1_lifetime'].stderr,
                                       'unit': units[0]}  # lifetime

    result_str_dict['2nd beta'] = {'value': result.params['e1_beta'].value,
                                   'error': result.params['e1_beta'].stderr,
                                   'unit': ''}  # Beta (exponent of exponential exponent)

    result_str_dict['offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}  # offset

    result.result_str_dict = result_str_dict
    return result


def estimate_biexponential(self, x_axis, data, params):
    """ Estimation of the initial values for an biexponential function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # calculation of offset, take the last 10% from the end of the data
    # and perform the mean from those.
    offset = data[-max(1, int(len(x_axis) / 10)):].mean()

    # substraction of offset, check whether
    if data[0] < data[-1]:
        data_level = offset - data
    else:
        data_level = data - offset

    # check if the data level contain still negative values and correct
    # the data level therefore. Otherwise problems in the logarithm appear.
    if data_level.min() <= 0:
        data_level = data_level - data_level.min()

    # remove all the data that can be smaller than or equals to std.
    # when the data is smaller than std, it is beyond resolution
    # which is not helpful to our fitting.
    for i in range(0, len(x_axis)):
        if data_level[i] <= data_level.std():
            break

    # values and bound of parameter.
    ampl = data[-max(1, int(len(x_axis) / 10)):].std()
    min_lifetime = 1e-16

    try:
        data_level_log = np.log(data_level[0:i])

        # linear fit, see linearmethods.py
        linear_result = self.make_linear_fit(x_axis=x_axis[0:i], data=data_level_log, estimator=self.estimate_linear)
        params['e0_lifetime'].set(value=-1 / linear_result.params['slope'].value, min=min_lifetime)
        params['e1_lifetime'].set(value=-1 / linear_result.params['slope'].value, min=min_lifetime)

        # amplitude can be positive of negative
        if data[0] < data[-1]:
            params['e0_amplitude'].set(value=-np.exp(linear_result.params['offset'].value), max=-ampl)
            params['e1_amplitude'].set(value=-np.exp(linear_result.params['offset'].value), max=-ampl)
        else:
            params['e0_amplitude'].set(value=np.exp(linear_result.params['offset'].value), min=ampl)
            params['e1_amplitude'].set(value=np.exp(linear_result.params['offset'].value), min=ampl)
    except:
        self.log.warning('Lifetime too small in estimate_exponential, beyond resolution!')

        params['e0_lifetime'].set(value=x_axis[i] - x_axis[0], min=min_lifetime)
        params['e1_lifetime'].set(value=x_axis[i] - x_axis[0], min=min_lifetime)
        params['e0_amplitude'].set(value=data_level[0])
        params['e1_amplitude'].set(value=data_level[0])

    params['offset'].set(value=offset)

    return error, params
