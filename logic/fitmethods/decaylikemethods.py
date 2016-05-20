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
#                              decay fitting                               #
#                                                                          #
############################################################################

def make_exponentialdecay_model(self): # pure exponential decay
    """

    @param self:
    @return:
    """
    def exponentialdecay_function(x,lifetime,amplitude,offset):
        """

        @param x:
        @param lifetime:
        @param amplitude:
        @param offset:
        @return:
        """
        return amplitude*np.exp(-x/lifetime)+offset
    model = Model(exponentialdecay_function)
    params = model.make_params()

    return model, params

def estimate_exponentialdecay(self,x_axis=None, data=None, params=None):
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

    offset = data.min()

    data_sub = data - offset
    for i in range(0, len(data_sub)):
        if data_sub[i] == 0:
            data_sub[i] = np.std(data_sub) / len(data_sub)
    data_level = data_sub
    i=0
    while i in range(0, len(x_axis) + 1):
        i += 1
        if data_level[i - 1] <= data_level.max() / (2 * len(data_level)) or data_level[i - 1] < data_level.std():
            break
    data_level_log = np.log(data_level[3:i-2])

    linear_result = self.make_linear_fit(axis=x_axis[3:i-2],data= data_level_log,add_parameters=None)
    params['lifetime'].value = -1/(linear_result.params['slope'].value)
    params['amplitude'].value = np.exp(linear_result.params['offset'].value)

    params['offset'].value = offset

    params['lifetime'].min = 0
    params['amplitude'].min = 0

    return error, params

def make_exponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """

    @param self:
    @param axis:
    @param data:
    @param add_parameters:
    @return:
    """
    exponentialdecay, params = self.make_exponentialdecay_model()

    error, params = self.estimate_exponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = exponentialdecay.fit(data, x=axis, params=params)
    except:
        self.logMsg('The exponentialdecay fit did not work.',
                    msgType='warning')
        result = exponentialdecay.fit(data, x=axis, params=params)
        print(result.message)

    return result

############################################################################
#                                                                          #
#                      stretched decay fitting                             #
#                                                                          #
############################################################################
# This is an general fitting for stretched/compress fitting, with no amplitude and offset
def make_stretchedexponentialdecay_model(self):
    """

    @param self:
    @return:
    """
    def stretched_exponentialdecay_function(x,lifetime,beta ):
        """
        #Todo: write docstring

        @param x:x
        @param lifetime: lifetime
        @param beta: stretch exponent
        @return:
        """
        return np.exp(-np.power(x,beta)/lifetime)
    model = Model(stretched_exponentialdecay_function)
    params = model.make_params()
    return model, params

def estimate_stretchedexponentialdecay(self,x_axis=None, data=None, params=None):
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

    #offset = np.min(data)

    #data_level = data - offset

    data_level = abs(data)
    #plt.plot(x_axis,np.log(-np.log(data_level)))
    
    #warnings.simplefilter('ignore', np.RankWarning)
    
    #Fixme: Check for sensible values and overwirte + logmassage 
    
    try:
        i = 0    
        # cut off values that are too small to be resolved
        while i in range(0,len(x_axis)+1):
            i+=1
            #flip down the noise
            if data_level[i-1] >=1:
                data_level[i-1]=1-(data_level[i-1]-1)
            if data_level[i-1] <= data_level.max()/(2*len(data_level)) or data_level[i-1]<data_level.std():
                break
        # double logarithmus of data, should be linear to the loagarithmus of x_axis
        double_lg_data = np.log(-np.log(data_level[0:i-1]))

        #linear fit, see linearmethods.py
        X=np.log(x_axis[0:i-1])

        linear_result = self.make_linear_fit(axis=X, data=double_lg_data, add_parameters=None)

        print(linear_result.params)
        params['beta'].value = linear_result.params['slope'].value
        params['lifetime'].value = np.exp(-linear_result.params['offset'].value/linear_result.params['slope'].value)
    except:
        print("linear fit failed")
        for i, data in enumerate(data_level):
            if abs(data * np.e - 1) < 0.05:
                print(i)
                index = i
        params['lifetime'].value = x_axis[index] - x_axis[0]
        params['beta'].value = 2
    
    params['beta'].min = 0
    params['lifetime'].min = 0
    params['beta'].max = 3
    params['lifetime'].max = 10 * (x_axis[-1]-x_axis[0])
    print('\n','lifetime.min: ',params['lifetime'].min,'\n',
          'lifetime.max: ',params['lifetime'].max,'\n','beta.min: ',
          params['beta'].min,'\n','beta.max: ',params['beta'].max)
    #params['offset'].value = offset

    return error, params


def make_stretchedexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    """

    @param self:
    @param axis:
    @param data:
    @param add_parameters:
    @return:
    """
    stretchedexponentialdecay, params = self.make_stretchedexponentialdecay_model()

    error, params = self.estimate_stretchedexponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = stretchedexponentialdecay.fit(data, x=axis, params=params)
    except:
        self.logMsg('The stretchedexponentialdecay fit did not work.',
                    msgType='warning')
        result = stretchedexponentialdecay.fit(data, x=axis, params=params)
        print(result.message)

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

    try:
        i = 0
        # cut off values that are too small to be resolved
        while i in range(0, len(x_axis) + 1):
            i += 1
             #flip down the noise that are larger than 1.
            if data_level[i - 1] >= 1:
                data_level[i - 1] = 1 - (data_level[i - 1] - 1)
            if data_level[i - 1] <= data_level.max() / (2 * len(data_level)) or data_level[i - 1] < data_level.std():
                break
        # double logarithmus of data, should be linear to the loagarithmus of x_axis
        double_lg_data = np.log(-np.log(data_level[5:i-2]))

        # linear fit, see linearmethods.py
        X = np.log(x_axis[5:i-2])

        linear_result = self.make_fixedslopelinear_fit(axis=X, data=double_lg_data, add_parameters=None)
        params['lifetime'].value = np.exp(-linear_result.params['offset'].value/2)
     # if linear fit failed
        if np.isnan(linear_result.params['offset'].value):
               for i, data in enumerate(data_level):
                      if abs(data * np.e - 1) < 0.05:
                          print(i)
                          index = i
                          break
               params['lifetime'].value = x_axis[index] - x_axis[0]
    except:
        print( "linear fit failed")
        s#elf.logMsg('The linear fit did not work.',
                    #msgType='warning')
        for i, data in enumerate(data_level):
            if abs(data*np.e-1)<0.05:
                print(i)
                index = i
        params['lifetime'].value = x_axis[index]-x_axis[0]

    params['amplitude'].min = 0
    params['lifetime'].min = 0
    params['lifetime'].max = (x_axis[-1]-x_axis[0])*(1-1/np.e)

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
