# -*- coding: utf-8 -*-
"""
This file contains methods for linear fitting, these methods
are imported by class FitLogic. The functions can be used for amy
types of offsets or slopes in other methods.

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

from lmfit.models import Model
import numpy as np

############################################################################
#                                                                          #
#                              linear fitting                              #
#                                                                          #
############################################################################

def make_constant_model(self, prefix=None):
    """ Create constant model.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params)

    Explanation of the objects:
        object lmfit.model.CompositeModel model:
            A model the lmfit module will use for that fit. Returns an object of the class
            lmfit.model.CompositeModel.

        object lmfit.parameter.Parameters params:
            It is basically an OrderedDict, so a dictionary, with keys
            denoting the parameters as string names and values which are
            lmfit.parameter.Parameter (without s) objects, keeping the
            information about the current value.

    For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """
    def constant_function(x, offset):
        """ Function of a constant value.

        @param numpy.array x: 1D array as the independent variable - e.g. time
        @param float offset: constant offset

        @return: constant function, in order to use it as a model
        """

        return offset

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and cannot be used as '
                       'a prefix and will be ignored for now. Correct that!'.format(prefix,
                                                                                    type(prefix)))
        model = Model(constant_function, independent_vars='x')
    else:
        model = Model(constant_function, independent_vars='x', prefix=prefix)

    params = model.make_params()

    return model, params


def make_amplitude_model(self, prefix=None):
    """ Create a constant model.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_constant_model.
    """

    def amplitude_function(x, amplitude):
        """ Function of a constant value.

        @param numpy.array x: 1D array as the independent variable - e.g. time
        @param float amplitude: constant offset

        @return: constant function, in order to use it as a model
        """

        return amplitude

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and cannot be used as '
                       'a prefix and will be ignored for now. Correct that!'.format(prefix,
                                                                                    type(prefix)))
        model = Model(amplitude_function, independent_vars='x')
    else:
        model = Model(amplitude_function, independent_vars='x', prefix=prefix)

    params = model.make_params()

    return model, params


def make_slope_model(self, prefix=None):
    """ Create a slope model.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_constant_model.
    """

    def slope_function(x, slope):
        """ Function of a constant value.

        @param numpy.array x: 1D array as the independent variable - e.g. time
        @param float slope: constant slope

        @return: slope function, in order to use it as a model
        """

        return slope

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and cannot be used as '
                       'a prefix and will be ignored for now. Correct that!'.format(prefix,
                                                                                    type(prefix)))
        model = Model(slope_function, independent_vars='x')
    else:
        model = Model(slope_function, independent_vars='x', prefix=prefix)

    params = model.make_params()

    return model, params


def make_linear_model(self, prefix=None):
    """ Create linear model.

    @param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

    @return tuple: (object model, object params), for more description see in
                   the method make_constant_model.
    """

    def linear_function(x):
        """ Function of a linear model.

        @param numpy.array x: 1D array as the independent variable - e.g. time

        @return: linear function, in order to use it as a model
        """

        return x

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and cannot be used as '
                       'a prefix and will be ignored for now. Correct that!'.format(prefix,
                                                                                    type(prefix)))
        linear_mod = Model(linear_function, independent_vars='x')
    else:
        linear_mod = Model(linear_function, independent_vars='x', prefix=prefix)

    slope, slope_param = self.make_slope_model(prefix=prefix)
    constant, constant_param = self.make_constant_model(prefix=prefix)

    model = slope * linear_mod + constant
    params = model.make_params()

    return model, params


def make_linear_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Performe a linear fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    # Make mathematical fit model
    linear, params = self.make_linear_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params, update_params=add_params)

    result = linear.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()

    result_str_dict['Slope'] = {'value': result.params['slope'].value,
                                'error': result.params['slope'].stderr,
                                'unit': '{0}/{1}'.format(units[1], units[0])}
    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result.result_str_dict = result_str_dict
    return result


def estimate_linear(self, x_axis, data, params):
    """ Provide an estimation for the initial values of a linear function.

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

    try:
        # calculate the parameters using Least-squares estimation of linear
        # regression
        a_1 = 0
        a_2 = 0
        x_mean = x_axis.mean()
        data_mean = data.mean()

        for i in range(0, len(x_axis)):
            a_1 += (x_axis[i]-x_mean)*(data[i]-data_mean)
            a_2 += np.power(x_axis[i]-x_mean, 2)
        slope = a_1/a_2
        intercept = data_mean - slope * x_mean
        params['offset'].value = intercept
        params['slope'].value = slope
    except:
        self.log.warning('The estimation for linear fit did not work.')
        params['slope'].value = 0
        params['offset'].value = 0

    return error, params

