# -*- coding: utf-8 -*-

"""
This file contains the Qudi fitting logic functions needed for
poissinian-like-methods.

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

import numpy as np
from lmfit.models import Model
from lmfit import Parameters
from scipy.signal import gaussian
from scipy.ndimage import filters
from scipy.interpolate import InterpolatedUnivariateSpline
from collections import OrderedDict


from scipy.special import gammaln, xlogy

################################################################################
#                                                                              #
#                      Defining Poissonian models                              #
#                                                                              #
################################################################################


def poisson(self, x, mu):
    """
    Poisson function taken from:
    https://github.com/scipy/scipy/blob/master/scipy/stats/_discrete_distns.py

    For license see documentation/BSDLicense_scipy.md

    Author:  Travis Oliphant  2002-2011 with contributions from
             SciPy Developers 2004-2011
    """
    if len(np.atleast_1d(x)) == 1:
        check_val = x
    else:
        check_val = x[0]

    if check_val > 1e18:
        self.log.warning('The current value in the poissonian distribution '
                         'exceeds 1e18! Due to numerical imprecision a valid '
                         'functional output cannot be guaranteed any more!')

    # According to the central limit theorem, a poissonian distribution becomes
    # a gaussian distribution for large enough x. Since the numerical precision
    # is limited to calculate the logarithmized poissonian and obtain from that
    # the exponential value, a self defined cutoff is introduced and set to
    # 1e12. Beyond that number a gaussian distribution is assumed, which is a
    # completely valid assumption.

    if check_val < 1e12:
        return np.exp(xlogy(x, mu) - gammaln(x + 1) - mu)
    else:
        return np.exp(-((x - mu) ** 2) / (2 * mu)) / (np.sqrt(2 * np.pi * mu))


def make_poissonian_model(self, prefix=None):
    """ Create a model of a single poissonian with an offset.

    param str prefix: optional string, which serves as a prefix for all
                       parameters used in this model. That will prevent
                       name collisions if this model is used in a composite
                       way.

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
    def poisson_function(x, mu):
        """ Function of a poisson distribution.

        @param numpy.array x: 1D array as the independent variable - e.g. occurences
        @param float mu: expectation value

        @return: poisson function: in order to use it as a model
        """
        return self.poisson(x, mu)

    amplitude_model, params = self.make_amplitude_model(prefix=prefix)

    if not isinstance(prefix, str) and prefix is not None:

        self.log.error('The passed prefix <{0}> of type {1} is not a string and'
                       'cannot be used as a prefix and will be ignored for now.'
                       'Correct that!'.format(prefix, type(prefix)))

        poissonian_model = Model(poisson_function, independent_vars='x')

    else:

        poissonian_model = Model(poisson_function, independent_vars='x',
                                 prefix=prefix)

    poissonian_ampl_model = amplitude_model * poissonian_model
    params = poissonian_ampl_model.make_params()

    return poissonian_ampl_model, params


def make_poissonianmultiple_model(self, no_of_functions=1):
    """ Create a model with multiple poissonians with amplitude.

    @param no_of_functions: for default=1 there is one poissonian, else
                            more functions are added

    @return tuple: (object model, object params), for more description see in
                   the method make_poissonian_model.
    """

    if no_of_functions == 1:
        multi_poisson_model, params = self.make_poissonian_model()
    else:
        multi_poisson_model, params = self.make_poissonian_model(prefix='p0_')

        for ii in range(1, no_of_functions):
            multi_poisson_model += self.make_poissonian_model(prefix='p{0:d}_'.format(ii))[0]
    params = multi_poisson_model.make_params()

    return multi_poisson_model, params

def make_poissoniandouble_model(self):
    return self.make_poissonianmultiple_model(2)

################################################################################
#                                                                              #
#                    Poissonian fits and their estimators                      #
#                                                                              #
################################################################################


def make_poissonian_fit(self, x_axis, data, estimator, units=None, add_params=None):
    """ Performe a poissonian fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    poissonian_model, params = self.make_poissonian_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)

    try:
        result = poissonian_model.fit(data, x=x_axis, params=params)
    except:
        self.log.warning('The poissonian fit did not work. Check if a poisson '
                         'distribution is needed or a normal approximation can be'
                         'used. For values above 10 a normal/ gaussian distribution '
                         'is a good approximation.')
        result = poissonian_model.fit(data, x=x_axis, params=params)
        print(result.message)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui   oder OrderedDict()

    result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                    'error': result.params['amplitude'].stderr,
                                    'unit': units[1]}     # Amplitude

    result_str_dict['Event rate'] = {'value': result.params['mu'].value,
                                    'error': result.params['mu'].stderr,
                                    'unit': units[0]}      # event rate

    result.result_str_dict = result_str_dict

    return result


def estimate_poissonian(self, x_axis, data, params):
    """ Provide an estimator for initial values of a poissonian function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # a gaussian filter is appropriate due to the well approximation of poisson
    # distribution
    # gaus = gaussian(10,10)
    # data_smooth = filters.convolve1d(data, gaus/gaus.sum(), mode='mirror')
    data_smooth = self.gaussian_smoothing(data=data, filter_len=10,
                                          filter_sigma=10)

    # set parameters
    mu = x_axis[np.argmax(data_smooth)]
    params['mu'].value = mu
    params['amplitude'].value = data_smooth.max() / self.poisson(mu, mu)

    return error, params


def make_poissoniandouble_fit(self, x_axis, data, estimator, units=None, add_params=None):
    """ Perform a double poissonian fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    double_poissonian_model, params = self.make_poissoniandouble_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)

    try:
        result = double_poissonian_model.fit(data, x=x_axis, params=params)
    except:
        self.log.warning('The double poissonian fit did not work. Check if a '
                         'poisson distribution is needed or a normal '
                         'approximation can be used. For values above 10 a '
                         'normal/ gaussian distribution is a good '
                         'approximation.')
        result = double_poissonian_model.fit(data, x=x_axis, params=params)

    # Write the parameters to allow human-readable output to be generated
    result_str_dict = OrderedDict()
    if units is None:
        units = ["arb. units", 'arb. unit']

    result_str_dict['Amplitude 1'] = {'value': result.params['p0_amplitude'].value,
                                      'error': result.params['p0_amplitude'].stderr,
                                      'unit': units[0]}

    result_str_dict['Event rate 1'] = {'value': result.params['p0_mu'].value,
                                       'error': result.params['p0_mu'].stderr,
                                       'unit':  units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['p1_amplitude'].value,
                                      'error': result.params['p1_amplitude'].stderr,
                                      'unit': units[0]}

    result_str_dict['Event rate 2'] = {'value': result.params['p1_mu'].value,
                                       'error': result.params['p1_mu'].stderr,
                                       'unit':  units[1]}

    result.result_str_dict = result_str_dict

    return result


def estimate_poissoniandouble(self, x_axis, data, params, threshold_fraction=0.4,
                              minimal_threshold=0.1, sigma_threshold_fraction=0.2):
    """ Provide initial values for a double poissonian fit.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set
    @param float threshold_fraction : Threshold to find second poissonian
    @param float minimal_threshold: Threshold is lowered to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values

    The parameters coming from the physical properties of an experiment
    done in gated counter:
                    - positive peak
                    - no values below 0
                    - rather broad overlapping functions
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # TODO: make the filter an extra function shared and usable for other functions.
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
    x_axis_interpol = np.linspace(x_axis[0], x_axis[-1], len(x_axis) * interpol_factor)
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
    params['p0_mu'].set(value=x_axis_interpol[dip0_arg])
    amplitude0 = (data_smooth[dip0_arg] / self.poisson(x_axis_interpol[dip0_arg], x_axis_interpol[dip0_arg]))
    params['p0_amplitude'].set(value=amplitude0, min=1e-15)

    params['p1_mu'].set(value=x_axis_interpol[dip1_arg])
    amplitude1 = (data_smooth[dip1_arg] / self.poisson(x_axis_interpol[dip1_arg], x_axis_interpol[dip1_arg]))
    params['p1_amplitude'].set(value=amplitude1, min=1e-15)

    return error, params
