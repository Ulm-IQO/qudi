# -*- coding: utf-8 -*-

"""
This file contains the QuDi fitting logic functions needed for 
poissinian-like-methods.

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

import numpy as np
from lmfit.models import Model
from lmfit import Parameters
from scipy.special  import factorial
from scipy.signal import gaussian
from scipy.ndimage import filters


############################################################################
#                                                                          #
#                          1D poissonian model                             #
#                                                                          #
############################################################################

def make_poissonian_model(self):
    """ This method creates a model of a poissonian with an offset.

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
            The used model has the Parameter with the meaning:
                'mu' : expected value mu

    For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """
    def poisson_function(x, mu):
        """
        Function of a poisson distribution.
        @param x: occurences
        @param mu: expected value

        @return: poisson function: in order to use it as a model
        """
        return (mu**x / factorial(x)  )* np.exp(-mu)
    
    model = Model(poisson_function)
    params = model.make_params()

    return model, params

def make_poissonian_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a 1D gaussian fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    mod_final, params = self.make_poissonian_model()

    error, params = self.estimate_poissonian(axis, data, params)

    if params['mu']>80:
        self.logMsg('The poissonian fit is not written to fit data with higher'
                    ' then 80 counts. Please use a gaussian fit, which is'
                    ' from 10 counts on a valid approximation.',
                    msgType='warning')
    if axis.max()>150:
        self.logMsg('The poissonian fit is not written to fit data with a '
                    'higher counts value of 150. Most probable the fit can'
                    ' not work, because for big numbers standard calculation'
                    ' for the fit is not written appropriately. For poissonian'
                    ' distributions with higher values than 10 a normal '
                    ' distribution is a good approximation.',
                    msgType='warning')
        
    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_parameters=add_parameters)
                                            
    try:
        result = mod_final.fit(data, x=axis, params=params)
    except:
        self.logMsg('The poissonian fit did not work. Check if a poisson '
                    'distribution is needed or a normal approximation can be'
                    'used. For values above 10 a normal/ gaussian distribution'
                    ' is a good approximation.',
                    msgType='warning')
        result = mod_final.fit(data, x=axis, params=params)
        print(result.message)

    return result

def estimate_poissonian(self, x_axis=None, data=None, params=None):
    """ This method provides a one dimensional gaussian function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values
    @param Parameters object params: object includes parameter dictionary which can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
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

    # a gaussian filter is appropriate due to the well approximation of poisson
    # distribution
    gaus=gaussian(10,10)
    data_smooth = filters.convolve1d(data, gaus/gaus.sum(),mode='mirror')

    # set parameters
    params['mu'].value = x_axis[np.argmax(data_smooth)]

    return error, params