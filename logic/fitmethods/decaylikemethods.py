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

#  Todo: Find another way to do this instead of sm or it has to be included into the package list
# import statsmodels.api as sm

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
    #Todo: write docstring
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

    data_level = abs(data)
    #plt.plot(x_axis,np.log(-np.log(data_level)))
    
    #warnings.simplefilter('ignore', np.RankWarning)
    
    #Fixme: use our own fitting with constraints for estimation
    
    #Fixme: implement proper error handling
    
    #Fixme: Check for sensible values and overwirte + logmassage 
    
    try:
        i = 0    
        while i in range(0,len(x_axis)+1):
            i+=1
            if data_level[i-1] >=1:
                data_level[i-1]=1-(data_level[i-1]-1)
            if data_level[i-1] <= data_level.max()/(2*len(data_level)):
                break
        double_lg_data = np.log(-np.log(data_level[0:i-1]))
        #linear regression
        X=np.log(x_axis[0:i-1])


        # Todo: Find another way to do this instead of sm or it has to be included into the package list
        X = sm.add_constant(X)
        linear_model = sm.OLS(double_lg_data,X)        
        linear_results = linear_model.fit()
        print(linear_results.params)
        params['beta'].value = linear_results.params[1]
        params['lifetime'].value = np.exp(-linear_results.params[0])
        
        #print(slope, intercept, r_value, p_value, std_err)
        #if math.isnan(params['beta'].value):
            #print("Set to two, was None")
            #params['beta'].value = float(2)  
        #if math.isnan(params['lifetime'].value):
            #print("Set to 100, was None")
           # params['lifetime'].value = float(100)
    except:
        print("Set to 2 and 100, polyfit failed")
        params['beta'].value = 2
        params['lifetime'].value = 4*(x_axis[-1]-x_axis[0])
    
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
