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


import logging
logger = logging.getLogger(__name__)
import numpy as np
from lmfit.models import Model
from lmfit import Parameters

############################################################################
#                                                                          #
#               bare exponential decay fitting                             #
#                                                                          #
############################################################################

def make_bareexponentialdecay_model(self):
    """
    This method creates a model of bare exponential decay.

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
    def bareexponentialdecay_function(x, lifetime):
        """
        Function of a bare exponential decay.
        @param x: variable variable - e.g. time
        @param lifetime: lifetime
        @return: bare exponential decay function: in order to use it as a model
        """
        return np.exp(-x/lifetime)
    model = Model(bareexponentialdecay_function)
    params = model.make_params()

    return model, params

def estimate_bareexponentialdecay(self,x_axis=None, data=None, params=None):
    """
    This method provides a estimation of a initial values for a bare
    exponential decay function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values
    @param Parameters object params: object includes parameter dictionary which
    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = 0
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

    #remove all the data that can be smaller than or equals to data.std()
    #when the data is smaller than std of the data, it is beyond the resolution
    #which is not helpful to our fitting.
    for i in range(0, len(x_axis)):
        if data[i] <= data.std():
            break

    #take the logarithom of data, calculate the life time with linear fit.
    #Todo: Check if values are apropriate for log conversion, see stretched exp
    data_log = np.log(data)
    try:
        linear_result = self.make_linear_fit(axis=x_axis[0:i],
                                             data=data_log[0:i],
                                             add_parameters=None)

        params['lifetime'].value = -1/linear_result.params['slope'].value
        #bound of parameters
    except:
        params['lifetime'].value = x_axis[i]-x_axis[0]
        #bound of parameters
#        logger.error('Linear fit did not work in bare exponential estimator.')

    params['lifetime'].min = 2 * (x_axis[1]-x_axis[0])

    return error, params

def make_bareexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """
    This method performes a bare exponential fit on the provided data.

    @param array[] axis: axis values
    @param array[] data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    bareexponentialdecay, params = self.make_bareexponentialdecay_model()

    error, params = self.estimate_bareexponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = bareexponentialdecay.fit(data, x=axis, params=params)
    except:
        result = bareexponentialdecay.fit(data, x=axis, params=params)
        logger.warning('The bare exponential decay fit did not work. lmfit '
                'result message: {}'.format(str(result.message)))
    return result


############################################################################
#                                                                          #
#                    exponential decay fitting                             #
#                                                                          #
############################################################################

def make_exponentialdecay_model(self): # exponential decay
    """
    This method creates a model of exponential decay.

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

    def exponentialdecay_function(x, lifetime, amplitude, offset):
        """
        Function of a exponential decay.
        @param x: variable variable - e.g. time
        @param amplitude: amplitude
        @param offset: offset
        @param lifetime: lifetime

        @return: sine function: in order to use it as a model
        """
        return amplitude*np.exp(-x/lifetime)+offset
    model = Model(exponentialdecay_function)
    params = model.make_params()

    return model, params

def estimate_exponentialdecay(self,x_axis=None, data=None, params=None):
    """
    This method provides a estimation of a initial values for a exponential
    decay function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values
    @param Parameters object params: object includes parameter dictionary which can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """
    error = 0
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

    #check if amplitude is positive or negative

    #calculation of offset
    offset = data[-max(1,int(len(x_axis)/10)):].mean()
    #substraction of offset
    if data[0]<data[-1]:
        data_level = offset - data
    else:
        data_level = data - offset
    #remove all the data that can be smaller than or equals to std.
    #when the data is smaller than std, it is beyond resolution
    #which is not helpful to our fitting.
    for i in range(0, len(x_axis)):
        if data_level[i] <=data_level.std():
            break

    try:
        data_level_log = np.log(data_level[0:i])
        #linear fit, see linearmethods.py
        linear_result = self.make_linear_fit(axis=x_axis[0:i],
                                             data=data_level_log,
                                             add_parameters=None)
        params['lifetime'].value = -1/linear_result.params['slope'].value
        #amplitude can be positive of negative
        if data[0]<data[-1]:
            params['amplitude'].value = -np.exp(linear_result.params['offset'].value)
        else:
            params['amplitude'].value = np.exp(linear_result.params['offset'].value)
    except:
        print("lifetime too small, beyond resolution")
        #Fixme: make logmessage
        params['lifetime'].value = x_axis[i]-x_axis[0]
        params['amplitude'].value = data_level[0]

    # values and bound of parameter.
    if data[0] < data[-1]:
        params['amplitude'].max = 0 - data[-max(1, int(len(x_axis) / 10)):].std()
    else:
        params['amplitude'].min = data[-max(1, int(len(x_axis) / 10)):].std()
    params['offset'].value = offset
    params['lifetime'].min = 2 * (x_axis[1]-x_axis[0])

    return error, params

def make_exponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """
    This method performes a exponential decay fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    exponentialdecay, params = self.make_exponentialdecay_model()

    error, params = self.estimate_exponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = exponentialdecay.fit(data, x=axis, params=params)
    except:
        result = exponentialdecay.fit(data, x=axis, params=params)
        logger.warning('The exponentialdecay fit did not work. '
                'Message: {}'.format(str(result.message)))
    return result

############################################################################
#                                                                          #
#                      stretched decay fitting                             #
#                                                                          #
############################################################################
def make_stretchedexponentialdecay_model(self):
    """
    This method creates a model of stretched exponential decay.

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
    def stretched_exponentialdecay_function(x, lifetime, beta):
        """
        Function of a stretched exponential decay.
        @param x: variable variable - e.g. time
        @param amplitude: amplitude
        @param beta: stretch exponent
        @param offset: offset

        @return: streched exponential decay function:
        in order to use it as a model
        """
        return np.exp(-np.power(x/lifetime,beta))
    constant_model, params = self.make_constant_model()
    amplitude_model, params = self.make_amplitude_model()
    model = amplitude_model*Model(stretched_exponentialdecay_function) + constant_model
    params = model.make_params()
    return model, params

def estimate_stretchedexponentialdecay(self,x_axis=None, data=None, params=None):
    """
    This method provides a estimation of a initial values for a streched
    exponential decay function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values
    @param Parameters object params: object includes parameter dictionary which can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """
    error = 0
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
    #check if amplitude is positive or negative, get data without offset,set
    #bound for smplitude
    offset = data[-max(1,int(len(x_axis)/10)):].mean()
    if data[0]<data[-1]:
        data_sub = offset - data
    else:
        data_sub = data - offset
    #calculate the absolute value of amplitude
    amplitude = data_sub.max()-data_sub[-max(1,int(len(x_axis)/10)):].mean()-\
                data_sub[-max(1,int(len(x_axis)/10)):].std()
    #normalization of data
    data_norm = data_sub/amplitude
    #remove data that can't under go double log calculation

# Todo: The estimation of stretched exponantial fit is not very stable and
    # needs improvement. But as a first version it works
    #Todo: Add this search to all estimators
    i = 0
    b = len(data)
    c = 0
    a = 0
    for i in range(0,len(data_norm)):
        if data_norm[i] >= 1:
            a = i+1
        if x_axis[i] < 1e-10:
            c = i
        if data_norm[i] <= data_norm.std():
            b = i
            break
    a = max(a, c)
    try:
        # double log of data is linear to log of x_axis, beta is the slope and
        # life time should equals exp(-intercept/slope)
        double_lg_data = np.log(-np.log(data_norm[a:b]))

        #linear fit, see linearmethods.py
        X=np.log(x_axis[a:b])

        linear_result = self.make_linear_fit(axis=X, data=double_lg_data,
                                             add_parameters=None)

        params['beta'].value = linear_result.params['slope'].value
        params['lifetime'].value = np.exp(-linear_result.params['offset'].value/linear_result.params['slope'].value)
    except:
        print("linear fit failed")
#        logger.warning('The linear fit did not work in estimator of stretched '+
#                    'exponential decay.')
        params['lifetime'].value = x_axis[b] - x_axis[0]
        params['beta'].value = 2


    #value and bounds of params
    params['offset'].value = offset
    #put sign infront of amplitude
    if data[0]<data[-1]:
        params['amplitude'].max = 0-data.std()
        params['amplitude'].value = 0-amplitude
    else:
        params['amplitude'].min = data.std()
        params['amplitude'].value = amplitude
    params['beta'].min = 0
    params['lifetime'].min = 2 * (x_axis[1]-x_axis[0])

    return error, params


def make_stretchedexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """
    This method performes a sine fit on the provided data.

    @param array[] axis: axis values
    @param array[]  data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    stretchedexponentialdecay, params = self.make_stretchedexponentialdecay_model()

    error, params = self.estimate_stretchedexponentialdecay(axis, data, params)

    if add_parameters is not None:
       params = self._substitute_parameter(parameters=params,
                                           update_dict=add_parameters)
    try:
       result = stretchedexponentialdecay.fit(data, x=axis, params=params)
    except:
       result = stretchedexponentialdecay.fit(data, x=axis, params=params)
       logger.warning('The stretchedexponentialdecay fit did not work. '
               'Message: {}'.format(str(result.message)))
    return result
