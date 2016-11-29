# -*- coding: utf-8 -*-
"""
This file contains methods for a power vs. fluorescence fitting, these methods
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


import logging
logger = logging.getLogger(__name__)
from lmfit.models import Model


################################################################################
#                                                                              #
#                Excitation power - fluorescence dependency                    #
#                                                                              #
################################################################################

#Todo: Rename to real function name
def make_powerfluorescence_model(self, prefix=None):
    """ Create a model of the fluorescence depending on excitation power with
        linear offset.

    @return tuple: (object model, object params)

    Explanation of the objects:
        object lmfit.model.CompositeModel model:
            A model the lmfit module will use for that fit. Here a
            gaussian model. Returns an object of the class
            lmfit.model.CompositeModel.

        object lmfit.parameter.Parameters params:
            It is basically an OrderedDict, so a dictionary, with keys
            denoting the parameters as string names and values which are
            lmfit.parameter.Parameter (without s) objects, keeping the
            information about the current value.
    """

    def powerfluorescence_function(x, I_sat, P_sat):
        """ Fluorescence depending excitation power function

        @param numpy.array x: 1D array as the independent variable e.g. power
        @param float I_sat: Saturation Intensity
        @param float P_sat: Saturation power

        @return: powerfluorescence function: for using it as a model
        """

        return I_sat * (x / (x + P_sat))


    if not isinstance(prefix, str) and prefix is not None:
        logger.error('The passed prefix <{0}> of type {1} is not a string and'
                     'cannot be used as a prefix and will be ignored for now.'
                     'Correct that!'.format(prefix, type(prefix)))

        mod_sat = Model(powerfluorescence_function, independent_vars='x')
    else:
        mod_sat = Model(powerfluorescence_function, independent_vars='x',
                        prefix=prefix)

    linear_model, params = self.make_linear_model(prefix=prefix)
    complete_model = mod_sat + linear_model

    params = complete_model.make_params()

    return complete_model, params


def estimate_powerfluorescence(self, x_axis, data, params):
    """ Provides an estimation for a saturation like function.

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

    #TODO: some estimated values should be input here

    return error, params


def make_powerfluorescence_fit(self, x_axis, data, add_params=None):
    """ Perform a fit on the provided data with a fluorescence depending function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    mod_final, params = self.make_powerfluorescence_model()

    error, params = self.estimate_powerfluorescence(x_axis, data, params)

    # overwrite values of additional parameters
    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = mod_final.fit(data, x=x_axis, params=params)
    except:
        logger.error('The Powerfluorescence fit did not work. Here the fit '
                     'result message:\n'
                     '{0}'.format(result.message))
        result = mod_final.fit(data, x=x_axis, params=params)

    return result

