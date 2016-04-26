# -*- coding: utf-8 -*-
"""
This file contains methods for a power vs. fluorescence fitting, these methods
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

Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import numpy as np
from lmfit.models import Model, LinearModel
from lmfit import Parameters


############################################################################
#                                                                          #
#           Excitation power - fluorescence dependency                     #
#                                                                          #
############################################################################

#Todo: Rename to real function name
def make_powerfluorescence_model(self):
    """ This method creates a model of the fluorescence depending on excitation power with an linear offset.

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

    For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """
    def powerfluorescence_function(x, I_saturation, P_saturation):
        """
        Function to describe the fluorescence depending on excitation power
        @param x: variable variable - Excitation pwer
        @param I_saturation: Saturation Intensity
        @param P_saturation: Saturation power
    
        @return: powerfluorescence function: for using it as a model
        """
    
        return I_saturation * (x / (x + P_saturation))
        
    mod_sat = Model(powerfluorescence_function)

    model = mod_sat + LinearModel()

    params = model.make_params()

    return model, params

def make_powerfluorescence_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a fit of the fluorescence depending on power
        on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    mod_final, params = self.make_powerfluorescence_model()

    error, params = self.estimate_powerfluorescence(axis, data, params)


    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = mod_final.fit(data, x=axis, params=params)
    except:
        self.logMsg('The 1D gaussian fit did not work.',
                    msgType='warning')
        result = mod_final.fit(data, x=axis, params=params)
        print(result.message)

    return result

def estimate_powerfluorescence(self, x_axis=None, data=None, params=None):
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

    #TODO: some estimated values should be input here

    return error, params
