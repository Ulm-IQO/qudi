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
#               bare stretched exponential decay                           #
#                                                                          #
############################################################################

def make_barestretchedexponentialdecay_model(self, prefix=None):
    """ Create a general bare exponential decay model.

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
    def barestretchedexponentialdecay_function(x, beta, lifetime):
        """ Function of a bare exponential decay.

        @param array x: variable variable - e.g. time
        @param float lifetime: lifetime

        @return: bare exponential decay function: in order to use it as a model
        """
        return np.exp(-np.power(x/lifetime, beta))

    model = Model(barestretchedexponentialdecay_function, independent_vars='x',
                  prefix=prefix)
    params = model.make_params()

    return model, params
