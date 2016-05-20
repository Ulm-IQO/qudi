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

Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

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

    if prefix is not None:
        model = Model(constant_function, prefix=prefix)
    else:
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
    #constant_x, constant_x_param = self.make_constant_model(prefix='x_')
    constant, constant_param = self.make_constant_model()

    model = slope * Model(linear_function) + constant
    params = model.make_params()

    return model, params

def estimate_linear(self, x_axis=None, data=None, params=None):
    """

    @param self:
    @param x_axis: x
    @param data: y
    @param params:
    @return:
    """
    error = 0
    # check if parameters make sense
    parameters = [x_axis, data]
    for var in parameters:
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.',
                        msgType='error')
            error = -1
        elif len(np.shape(var)) != 1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')
            error = -1
    if not isinstance(params, Parameters):
        self.logMsg('Parameters object is not valid in estimate_gaussian.',
                    msgType='error')
        error = -1
    # slope
    s = (sum(data[int(len(x_axis)/2):])-sum(data[:int(len(x_axis)/2)]))/int(len(x_axis)/2)*(x_axis[int(len(x_axis)/2)]
                                                                                            -x_axis[0])
    params['slope'].value = s
    # offset (y when x = 0 )
    y_c=s*(0.75*(x_axis[int(len(x_axis)/2)]-x_axis[0])+x_axis[0])/(sum(data[int(len(x_axis)/2):])/int(len(x_axis)/2))

    params['offset'].value = y_c

    return error, params

def make_linear_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a linear fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
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
        self.logMsg('The linear fit did not work.',
                    msgType='warning')
        result = linear.fit(data, x=axis, params=params)
        print(result.message)

    return result
############################################################################
#                                                                          #
#                     fixed_slope linear fitting                           #
#                                                                          #
############################################################################


def make_fixedslopelinear_model(self):
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
    def fixedslopelinearfunction(x):
        return 2.0*x

    constant_model, params = self.make_constant_model()

    model = Model(fixedslopelinearfunction) + constant_model
    params = model.make_params()

    return model, params

def estimate_fixedslopelinear(self, x_axis=None, data=None, params=None):
    """

    @param self:
    @param x_axis: x
    @param data: y
    @param params:
    @return:
    """
    error = 0
    # check if parameters make sense
    parameters = [x_axis, data]
    for var in parameters:
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.',
                        msgType='error')
            error = -1
        elif len(np.shape(var)) != 1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')
            error = -1
    if not isinstance(params, Parameters):
        self.logMsg('Parameters object is not valid in estimate_gaussian.',
                    msgType='error')
        error = -1

    # offset (y when x = 0 )
    y_c = sum(data)/len(x_axis)-2*sum(x_axis)/len(x_axis)

    params['offset'].value = y_c

    return error, params

def make_fixedslopelinear_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a linear fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    fixedslopelinear, params = self.make_fixedslopelinear_model()

    error, params = self.estimate_fixedslopelinear(axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = fixedslopelinear.fit(data, x=axis, params=params)
    except:
        self.logMsg('The linear fit did not work.',
                    msgType='warning')
        result = fixedslopelinear.fit(data, x=axis, params=params)
        print(result.message)

    return result

