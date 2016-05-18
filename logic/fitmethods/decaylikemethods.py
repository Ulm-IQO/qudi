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
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel,LinearModel
from lmfit import Parameters
import warnings

############################################################################
#                                                                          #
#                              decay fitting                               #
#                                                                          #
############################################################################

def make_exponentialdecay_model(self): # pure exponential decay
    # Todo: docstring
    #def bareexponentaildecay_function(x,lifetime):
        #return np.exp(x/lifetime)
    #def exponentialdecay_function(x,lifetime,amplitude,x_offset,y_offset):
        #return amplitude*np.exp((x+x_offset)/lifetime) + y_offset
    def exponentialdecay_function(x,lifetime):
        return np.exp(-x/lifetime)
    #amplitude_model, params = self.make_amplitude_model()
    #constant_model, params = self.make_constant_model()
    #model = amplitude_model * Model(exponentialdecay_function) + constant_model
    model = Model(exponentialdecay_function)
    params = model.make_params()

    return model, params

def estimate_exponentialdecay(self,x_axis=None, data=None, params=None):
    # Todo: docstring
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

    data_level_log = np.log(abs(data))

    params['lifetime'].value = -1/(np.polyfit(x_axis,data_level_log,1)[0])

    #params['amplitude'].value = np.exp(data_level+x_axis/params['lifetime'].value)

    #params['offset'].value = offset

    return error, params

def make_exponential_fit(self, axis=None, data=None, add_parameters=None):
    # Todo: docstring
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
def make_stretchedexponentialdecay_model(self):
    def stretched_exponentialdecay_function(x,lifetime,beta ):
        """

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

    # Todo: docstring
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

    data_level = data
    #plt.plot(x_axis,np.log(-np.log(data_level)))
    double_lg_data = np.log(-np.log(data_level))
    warnings.simplefilter('ignore', np.RankWarning)
    params['beta'].value = np.polyfit(np.log(x_axis),double_lg_data,1)[0]
    params['lifetime'].value = np.exp( -np.polyfit(np.log(x_axis),double_lg_data,1)[1])
    fit_result = params['beta'].value*np.log(x_axis) + np.polyfit(np.log(x_axis),double_lg_data,1)[1]
    print(params['beta'].value,params['lifetime'].value)
    #lt.plot(np.log(x_axis),double_lg_data,'or')
    #plt.plot(np.log(x_axis),fit_result, '-g')
    #plt.show()


    #params['offset'].value = offset

    return error, params


def make_stretchedexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    # Todo: docstring
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
