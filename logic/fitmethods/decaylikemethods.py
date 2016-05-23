# -*- coding: utf-8 -*-
"""
This file contains methods for decay-like fitting, these methods
are imported by class FitLogic.

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

Copyright (c) 2016 Ou Wang ou.wang@uni-ulm.de
"""

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
    def bareexponentialdecay_function(x,lifetime):
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

    #remove all the data that can be smaller than or equals to 0.
    data = abs(data)
    for i in range(0, len(data)):
        if data[i] == 0:
            data[i] = np.std(data) / len(data)
    i=0
    #when the data is smaller than std of the data, it is beyond the resolution
    #which is not helpful to our fitting.
    while i in range(0, len(x_axis) + 1):
        i += 1
        if data[i - 1] < data_sub[-max(1,int(len(x_axis)/10)):].std():
            break
        
    #take the logarithom of data, calculate the life time with linear fit.
    data_log = np.log(data)

    linear_result = self.make_linear_fit(axis=x_axis[0:i-2], 
                                         data= data_log[0:i-2], 
                                             add_parameters=None)

    params['lifetime'].value = -1/linear_result.params['slope'].value
    #bound of parameters    
    params['lifetime'].min = 2 * (x_axis[1]-x_axis[0])

    return error, params

def make_bareexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """ 
    This method performes a sine fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
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
        self.logMsg('The bare exponential decay fit did not work. lmfit result'
                    'message: {}'.format(str(result.message)),
                    msgType='warning')
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
   

   def exponentialdecay_function(x,lifetime,amplitude,offset):
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

    #check if amplitude is positive or negative
    if data[0]<data[-1]:
        params['amplitude'].max = 0-data[-max(1,int(len(x_axis)/10)):].std()
    else:
        params['amplitude'].min = data[-max(1,int(len(x_axis)/10)):].std()
    #calculation of offset
    offset = data[-max(1,int(len(x_axis)/10)):].mean()
    #substraction of offset
    data_sub = abs(data - offset)
    #remove all the data that can be smaller than or equals to 0.
    for i in range(0, len(data_sub)):
        if data_sub[i] == 0:
            data_sub[i] = np.std(data_sub) / len(data_sub)
    data_level = data_sub
    i=0
    #when the data is smaller than std of the data, it is beyond the resolution
    #which is not helpful to our fitting.    
    while i in range(0, len(x_axis) + 1):
        i += 1
        if data_level[i - 1] < data_sub[-max(1,int(len(x_axis)/10)):].std():
            break
    
    try:
        data_level_log = np.log(data_level[0:i-2])
        linear_result = self.make_linear_fit(axis=x_axis[0:i-2], 
                                             data=data_level_log, 
                                             add_parameters=None)
        params['lifetime'].value = -1/linear_result.params['slope'].value
        if data[0]<data[-1]:
            params['amplitude'].value = -np.exp(linear_result.params['offset'].value)
        else:
            params['amplitude'].value = np.exp(linear_result.params['offset'].value)
    except:
        print("lifetime too small, beyond resolution")
        params['lifetime'].value = x_axis[i]-x_axis[0]
    
    params['offset'].value = offset
    #bound of parameter.
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
        #Todo: change print to inside logsmsg see above
        self.logMsg('The exponentialdecay fit did not work.'
                    'message: {}'.format(str(result.message)),
                    msgType='warning')
        result = exponentialdecay.fit(data, x=axis, params=params)

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
        #Todo: make docstring
        """
        Function of a stretched exponential decay.
        @param x: variable variable - e.g. time
        @param amplitude: amplitude
        @param beta: stretch exponent
        @param offset: offset

        @return: streched exponential decay function: 
        in order to use it as a model
        """
        return np.exp(-np.power(x, beta)/lifetime)
    constant_model, params = self.make_constant_model()
    amplitude_model, params = self.make_amplitude_model()
    model = amplitude_model*Model(stretched_exponentialdecay_function) + constant_model
    params = model.make_params()
    return model, params

def estimate_stretchedexponentialdecay(self,x_axis=None, data=None, params=None):
    #Todo: make docstring
    """

    @param self:
    @param x_axis:
    @param data:
    @param params:
    @return:
    """
    error = 0
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
    #check if amplitude is positive or negative
    if data[0]<data[-1]:
        params['amplitude'].max = 0-data.std()
    else:
        params['amplitude'].min = data.std()
        
    #calculation of offset
    offset = data[-max(1,int(len(x_axis)/10)):].mean()
    #substraction of offset
    data_sub = abs(data - offset)
    #remove all the 0 in data_sub    
    for i in range(0,len(data_sub)):
        if data_sub[i] == 0:
            data_sub[i] = np.std(data_sub)/len(data_sub)

    amplitude = data_sub.max()-data_sub[-max(1,int(len(x_axis)/10)):].std()

    data_level = data_sub/amplitude

    params['offset'].value = offset
    if data[0]<data[-1]:
        params['amplitude'].max = 0-amplitude
    else:
        params['amplitude'].min = amplitude

    i = 0
    # cut off values that are too small to be resolved
    while i in range(0, len(x_axis)):
        i += 1
         #flip down the noise that are larger than 1.
        if data_level[i - 1] >= 1:
            data_level[i - 1] = 1 - (data_level[i - 1] - 1)
        if data_level[i - 1] < data_sub[-max(1,int(len(x_axis)/10)):].std():
            break    
    try:        
        double_lg_data = np.log(-np.log(data_level[max(1,int(len(x_axis)/25)):i-2]))

        #linear fit, see linearmethods.py
        X=np.log(x_axis[max(1,int(len(x_axis)/25)):i-2])

        linear_result = self.make_linear_fit(axis=X, data=double_lg_data, 
                                             add_parameters=None)

        params['beta'].value = linear_result.params['slope'].value
        params['lifetime'].value = np.exp(-linear_result.params['offset'].value/linear_result.params['slope'].value)
    except:
        print("linear fit failed")
        #self.logMsg('The linear fit did not work.',
                    #msgType='warning')
        params['lifetime'].value = x_axis[i] - x_axis[0]
        params['beta'].value = 2
    
    params['beta'].min = 0
    params['lifetime'].min = 2 * (x_axis[1]-x_axis[0])

    return error, params


def make_stretchedexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
   """ 
   This method performes a sine fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

   stretchedexponentialdecay, params = self.make_stretchedexponentialdecay_model()

   error, params = self.estimate_stretchedexponentialdecay(axis, data, params)
   
   params['beta'].value = 2.
   params['beta'].vary = False

   if add_parameters is not None:
       params = self._substitute_parameter(parameters=params,
                                           update_dict=add_parameters)
   try:
       result = stretchedexponentialdecay.fit(data, x=axis, params=params)
   except:
       self.logMsg('The stretchedexponentialdecay fit did not work.'
                   'message: {}'.format(str(result.message)),
                   msgType='warning')
       result = stretchedexponentialdecay.fit(data, x=axis, params=params)
   return result

############################################################################
#                                                                          #
#            double compressed exponential decay fitting                   #
#                                                                          #
############################################################################
def make_doublecompressedexponentialdecay_model(self):
    def doublecompressed_exponentialdecay_function(x,lifetime,amplitude,offset ):
        """

        @param x:
        @param lifetime:
        @param amplitude:
        @param offset:
        @return:
        """
        return amplitude*np.exp(-np.power((x/lifetime),2))+ offset
    model = Model(doublecompressed_exponentialdecay_function)
    params = model.make_params()
    return model, params

def estimate_doublecompressedexponentialdecay(self,x_axis=None, data=None, params=None):
    """

    @param self:
    @param x_axis:
    @param data:
    @param params:
    @return:
    """
    error = 0
    parameters = [x_axis, data]
    #test if the input make sense
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

    offset = sum(data[-5:])/5

    data_level = abs(data - offset)
#prevent the existence of 0
    for i in range(0,len(data_level)):
        if data_level[i] == 0:
            data_level[i] = np.std(data_level)/len(data_level)

    amplitude = data_level.max()-data_level[-5:].std()

    data_level = data_level/amplitude

    params['offset'].value = offset
    params['amplitude'].value=amplitude

    i = 0
    # cut off values that are too small to be resolved
    while i in range(0, len(x_axis) + 1):
        i += 1
         #flip down the noise that are larger than 1.
        if data_level[i - 1] >= 1:
            data_level[i - 1] = 1 - (data_level[i - 1] - 1)
        if data_level[i - 1] <= data_level.max() / (2 * len(data_level)) or data_level[i - 1] < data_level.std():
            break    
    try:
       
        # double logarithmus of data, should be linear to the loagarithmus of x_axis
        double_lg_data = np.log(-np.log(data_level[0:i-2]))

        # linear fit, see linearmethods.py
        X = np.log(x_axis[0:i-2])

        linear_result = self.make_fixedslopelinear_fit(axis=X, data=double_lg_data, add_parameters=None)
        params['lifetime'].value = np.exp(-linear_result.params['offset'].value/2)
     # if linear fit failed
    except:
        print( "linear fit failed")
        #self.logMsg('The linear fit did not work.',
                    #msgType='warning')
        params['lifetime'].value = x_axis[i]-x_axis[0]

    params['amplitude'].min = 0
    params['lifetime'].min = x_axis[1]-x_axis[0]
    params['lifetime'].max = (x_axis[-1]-x_axis[0])*3

    return error, params


def make_doublecompressedexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """

    @param self:
    @param axis:
    @param data:
    @param add_parameters:
    @return:
    """
    doublecompressedexponentialdecay, params = self.make_doublecompressedexponentialdecay_model()

    # Todo: Use general stretched exponential decay and restrict here
    # params['beta'].value = 2.
    # params['beta'].vary = False

    error, params = self.estimate_doublecompressedexponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = doublecompressedexponentialdecay.fit(data, x=axis, params=params)
    except:
        self.logMsg('The doublecompressedexponentialdecay fit did not work.',
                    msgType='warning')
        result = doublecompressedexponentialdecay.fit(data, x=axis, params=params)
        print(result.message)

    return result
