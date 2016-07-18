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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


import core.logger as logger
import numpy as np
from lmfit.models import Model
from lmfit import Parameters
from scipy.signal import gaussian
from scipy.ndimage import filters
from scipy.interpolate import InterpolatedUnivariateSpline
#from scipy.stats import poisson

from scipy import special
from scipy.special import gammaln as gamln

############################################################################
#                                                                          #
#                           poissonian model                               #
#                                                                          #
############################################################################

def poisson(self,x,mu):
    """
    Poisson function taken from:
    https://github.com/scipy/scipy/blob/master/scipy/stats/_discrete_distns.py

    For license see documentation/BSDLicense_scipy.md

    Author:  Travis Oliphant  2002-2011 with contributions from
             SciPy Developers 2004-2011
    """
    return np.exp(special.xlogy(x, mu) - gamln(x + 1) - mu)

def make_poissonian_model(self, no_of_functions=None):
    """ This method creates a model of a poissonian with an offset.
    @param no_of_functions: if None or 1 there is one poissonian, else
                            more functions are added
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
    """
    def poisson_function(x, mu):
        """
        Function of a poisson distribution.
        @param x: occurences
        @param mu: expected value

        @return: poisson function: in order to use it as a model
        """
        return self.poisson(x, mu)

    def amplitude_function(x, amplitude):
        """
        Function of a amplitude value.
        @param x: variable variable
        @param offset: independent variable - amplitude

        @return: amplitude function: in order to use it as a model
        """

        return amplitude + 0.0 * x

    if no_of_functions is None or no_of_functions == 1:
        model = ( Model(poisson_function, prefix='poissonian_') *
                  Model(amplitude_function, prefix='poissonian_') )
    else:
        model = (Model(poisson_function, prefix='poissonian{}_'.format('0')) *
                 Model(amplitude_function, prefix='poissonian{}_'.format('0')))
        for ii in range(no_of_functions-1):
            model += (Model(poisson_function, prefix='poissonian{}_'.format(ii+1)) *
                      Model(amplitude_function, prefix='poissonian{}_'.format(ii+1)))
    params = model.make_params()

    return model, params


def make_poissonian_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a poissonian fit on the provided data.

    @param array[] axis: axis values
    @param array[]  data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    parameters = [axis, data]
    for var in parameters:
        if len(np.shape(var)) != 1:
                logger.error('Given parameter is no one dimensional array.')

    mod_final, params = self.make_poissonian_model()

    error, params = self.estimate_poissonian(axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)

    try:
        result = mod_final.fit(data, x=axis, params=params)
    except:
        logger.warning('The poissonian fit did not work. Check if a poisson '
                'distribution is needed or a normal approximation can be'
                'used. For values above 10 a normal/ gaussian distribution'
                ' is a good approximation.')
        result = mod_final.fit(data, x=axis, params=params)
        print(result.message)

    return result

def estimate_poissonian(self, x_axis=None, data=None, params=None):
    """ This method provides a poissonian function.

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
        if len(np.shape(var)) != 1:
            logger.error('Given parameter is no one dimensional array.')
            error = -1
    if not isinstance(params, Parameters):
        logger.error('Parameters object is not valid in estimate_gaussian.')
        error = -1

    # a gaussian filter is appropriate due to the well approximation of poisson
    # distribution
    # gaus = gaussian(10,10)
    # data_smooth = filters.convolve1d(data, gaus/gaus.sum(), mode='mirror')
    data_smooth = self.gaussian_smoothing(data=data, filter_len=10, filter_sigma=10)

    # set parameters
    mu = x_axis[np.argmax(data_smooth)]
    params['poissonian_mu'].value = mu
    params['poissonian_amplitude'].value = data_smooth.max()/self.poisson(mu,mu)

    return error, params


def make_doublepoissonian_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a double poissonian fit on the provided data.

    @param array[] axis: axis values
    @param array[]  data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    parameters = [axis, data]
    for var in parameters:
        if len(np.shape(var)) != 1:
                logger.error('Given parameter is no one dimensional array.')

    mod_final, params = self.make_poissonian_model(no_of_functions=2)

    error, params = self.estimate_doublepoissonian(axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)

    try:
        result = mod_final.fit(data, x=axis, params=params)
    except:
        logger.warning('The double poissonian fit did not work. Check if a '
                'poisson distribution is needed or a normal approximation '
                'can be used. For values above 10 a normal/ gaussian '
                'distribution is a good approximation.')
        result = mod_final.fit(data, x=axis, params=params)
        print(result.message)

    return result

############################################################################
#                                                                          #
#                     double poissonian model                              #
#                                                                          #
############################################################################

def estimate_doublepoissonian(self, x_axis=None, data=None, params=None,
                              threshold_fraction=0.4, minimal_threshold=0.1,
                              sigma_threshold_fraction=0.2):
    """ This method provides a an estimator for a double poissonian fit
    with the parameters coming from the physical properties of an experiment
    done in gated counter:
                    - positive peak
                    - no values below 0
                    - rather broad overlapping funcitons

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values
    @param Parameters object params: Needed parameters
    @param float threshold_fraction : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowered to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return int error: error code (0:OK, -1:error)
    @return Parameters object params: estimated values
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

    #TODO: make the filter an extra function shared and usable for other functions.
    # Calculate here also an interpolation factor, which will be based on the
    # given data set. If the convolution later on has more points, then the fit
    # has a higher chance to be successful. The interpol_factor multiplies the
    # number of points.
    # Set the interpolation factor according to the amount of data. Too much
    # interpolation is not good for the peak estimation, also too less in not
    # good.

    if len(x_axis) < 20.:
        len_x = 5
        interpol_factor = 8
    elif len(x_axis) >= 100.:
        len_x = 10
        interpol_factor = 1
    else:
        if len(x_axis) < 60:
            interpol_factor = 4
        else:
            interpol_factor = 2
        len_x = int(len(x_axis) / 10.) + 1

    # Create the interpolation function, based on the data:
    interpol_function = InterpolatedUnivariateSpline(x_axis, data, k=1)
    # adjust the x_axis to that:
    x_axis_interpol = np.linspace(x_axis[0], x_axis[-1], len(x_axis)*interpol_factor)
    # create actually the interpolated data:
    interpol_data = interpol_function(x_axis_interpol)

    # Use a gaussian function to convolve with the data, to smooth the datatrace.
    # Then the peak search algorithm performs much better.
    gaus = gaussian(len_x, len_x)
    data_smooth = filters.convolve1d(interpol_data, gaus / gaus.sum(), mode='mirror')

    # search for double gaussian
    search_results = self._search_double_dip(x_axis_interpol,
                                             data_smooth * (-1),
                                             threshold_fraction,
                                             minimal_threshold,
                                             sigma_threshold_fraction,
                                             make_prints=False)
    error = search_results[0]
    sigma0_argleft, dip0_arg, sigma0_argright = search_results[1:4]
    sigma1_argleft, dip1_arg, sigma1_argright = search_results[4:7]

    # set the initial values for the fit:
    params['poissonian0_mu'].value = x_axis_interpol[dip0_arg]
    params['poissonian0_amplitude'].value = (data_smooth[dip0_arg] / self.poisson(x_axis_interpol[dip0_arg], x_axis_interpol[dip0_arg]))
    params['poissonian0_amplitude'].min = 1e-15

    params['poissonian1_mu'].value = x_axis_interpol[dip1_arg]
    params['poissonian1_amplitude'].value = (data_smooth[dip1_arg] / self.poisson(x_axis_interpol[dip1_arg], x_axis_interpol[dip1_arg]))
    params['poissonian1_amplitude'].min = 1e-15

    return error, params
