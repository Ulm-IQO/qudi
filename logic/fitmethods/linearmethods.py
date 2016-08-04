# -*- coding: utf-8 -*-
"""
This file contains methods for linear fitting, these methods
are imported by class FitLogic. The functions can be used for amy
types of offsets or slopes in other methods.

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
Copyright (c) 2016 Ou Wang ou.wang@uni-ulm.de
"""


import logging
logger = logging.getLogger(__name__)
from lmfit.models import Model
import numpy as np
from lmfit import Parameters
import math
############################################################################
#                                                                          #
#                              linear fitting                              #
#                                                                          #
############################################################################

def make_constant_model(self, prefix=None):
    """ This method creates a model of a constant model.
    @param string prefix: variable prefix

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
        """
        Function of a constant value.
        @param x: variable variable
        @param offset: independent variable - e.g. offset

        @return: constant function: in order to use it as a model
        """

        return offset + 0.0 * x

    if prefix is None:
        model = Model(constant_function)
    else:
        if not isinstance(prefix,str):
            logger.error('Given prefix in constant model is no string. '
                    'Deleting prefix.')
        try:
            model = Model(constant_function, prefix=prefix)
        except:
            logger.error('Creating the constant model failed. '
                    'The prefix might not be a valid string. '
                    'The prefix was deleted.')
            model = Model(constant_function)

    params = model.make_params()

    return model, params

def make_amplitude_model(self):
    """ This method creates a model of a constant model.

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
    def amplitude_function(x, amplitude):
        """
        Function of a constant value.
        @param x: variable variable
        @param amplitude: independent variable - e.g. amplitude

        @return: constant function: in order to use it as a model
        """

        return amplitude + 0.0 * x

    model = Model(amplitude_function)
    params = model.make_params()

    return model, params

def make_slope_model(self):
    """ This method creates a model of a slope model.

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
    def slope_function(x, slope):
        """
        Function of a constant value.
        @param x: variable variable
        @param slope: independent variable - slope

        @return: slope function: in order to use it as a model
        """

        return slope + 0.0 * x

    model = Model(slope_function)
    params = model.make_params()

    return model, params

def make_linear_model(self):
    """ This method creates a model of a constant model.

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
    def linear_function(x):
        """
        Function of a linear.
        @param x: variable variable

        @return: constant function: in order to use it as a model
        """

        return x

    slope, slope_param = self.make_slope_model()
    constant, constant_param = self.make_constant_model()

    model = slope * Model(linear_function) + constant
    params = model.make_params()

    return model, params

def estimate_linear(self, x_axis=None, data=None, params=None):
    """
    This method provides a estimation of a initial values
     for a linear function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values
    @param Parameters object params: object includes parameter dictionary
            which can be set

    @return: tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = 0
    # check if parameters make sense
    parameters = [x_axis, data]
    for var in parameters:
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            logger.error('Given parameter is no array.')
            error = -1
        elif len(np.shape(var)) != 1:
            logger.error('Given parameter is no one dimensional array.')
            error = -1
    if not isinstance(params, Parameters):
        logger.error('Parameters object is not valid in estimate_gaussian.')
        error = -1
    try:
        """
        #calculate the parameters using Least-squares estimation of linear
        #regression
        """
        a_1 = 0
        a_2 = 0
        x_mean = x_axis.mean()
        data_mean = data.mean()
        for i in range(0,len(x_axis)):
            a_1+=(x_axis[i]-x_mean)*(data[i]-data_mean)
            a_2+=np.power(x_axis[i]-x_mean,2)
        slope = a_1/a_2
        intercept = data_mean - slope*x_mean
        params['offset'].value = intercept
        params['slope'].value = slope
    except:
        logger.warning('The linear fit did not work.')
        params['slope'].value = 0
        params['offset'].value = 0

    return error, params

def make_linear_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a linear fit on the provided data.

    @param array[] axis: axis values
    @param array[] data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    linear, params = self.make_linear_model()

    error, params = self.estimate_linear(axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = linear.fit(data, x=axis, params=params)
    except:
        logger.warning('The linear fit did not work.lmfit result '
                'Message: {}'.format(str(result.message)))
        result = linear.fit(data, x=axis, params=params)

    return result
