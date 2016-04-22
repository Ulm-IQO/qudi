# -*- coding: utf-8 -*-
"""
This file contains the QuDi task runner module.

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

Copyright (C) 2015 Florian Frank florian.frank@uni-ulm.de
Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import numpy as np
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel,LinearModel
from lmfit import Parameters
from lmfit import minimize

############################################################################
#                                                                          #
#                              linear fitting                              #
#                                                                          #
############################################################################

def make_constant_model(self, prefix=None):
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
    def constant_function(x, offset):
        """
        Function of a constant value.
        @param x: variable variable
        @param offset: independent variable - e.g. offset

        @return: constant function: in order to use it as a model
        """

        return offset + 0.0 * x

    #Todo: Check if prefix is string
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
        @param amplitude: independent variable - e.g. amplitude

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
    constant_x, constant_x_param = self.make_constant_model(prefix='x_')
    constant_y, constant_y_param = self.make_constant_model(prefix='y_')
    
    
    model = slope * (Model(linear_function)+ constant_x) +constant_y
#    model = slope * (Model(linear_function))
    
    params = model.make_params()

    return model, params