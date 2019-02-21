# -*- coding: utf-8 -*-
"""
This file contains methods for lorentzian-like fitting, these methods
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

Developed from PI3diamond code Copyright (C) 2009 Helmut Rathgen <helmut.rathgen@gmail.com>

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


import numpy as np
from lmfit import Parameters
from lmfit.models import Model
from collections import OrderedDict

from scipy.ndimage import filters
from scipy.interpolate import InterpolatedUnivariateSpline


################################################################################
#                                                                              #
#                       Defining Lorentzian Models                             #
#                                                                              #
################################################################################


"""
Information about the general Lorentzian Model
==============================================

The lorentzian has the following general form:

                                 _                       _
                            A   |           sigma         |
    f(x; A, x_0, sigma) = ----- |  ---------------------- |
                            pi  |_ (x_0 - x)^2 + sigma^2 _|

That is the appearance if the lorentzian is considered as a probability
distribution. Then it is also called a Cauchy distribution. For physical
applications it is sensible to redefine the Lorentzian like that:

                 !      A
    f(x=x_0) = I = -----------
                    pi * sigma


                                 _                            _
                                |         (sigma)^2          |
    L(x; I, x_0, sigma) =   I * |  --------------------------  |
                                |_ (x_0 - x)^2 + (sigma)^2  _|

We will call this notation the physical definition of the Lorentzian, with I as
the height of the Lorentzian, x_0 is its location and sigma as the half
width at half maximum (HWHM).

Note that the fitting algorithm is using now the equation L(x; I, x_0, sigma)
and not f(x; A, x_0, sigma), therefore all the parameters are defined according
to L(x; I, x_0, sigma). The full width at half maximum (FWHM) is therefore
2*sigma.

The indefinite Integral of the Lorentzian is

    integral(f(x),x) = A/pi *Arctan( (x-x0)/sigma)

Plugging in the limits [0 to inf] we get:

    integral(f(x), {x,0,inf}) = (A * sigma/pi) *(  pi/(2*sigma) + Arctan(x_0/sigma)/sigma) ) = F

(You can confirm that with Mathematica.) For the assumption that

    x_0 >> sigma

we can take the limit of Arctan to which it converges: pi/2

That simplifies the formula further to

F = (A * sigma/pi) * (  pi/(2*sigma) + pi/(2*sigma) ) = A

Using the formula for I (above) we can solve the equation for sigma:

sigma = A / (pi* I) = F /(pi * I)

The parameter I can be really easy determined, since it will be just the
maximal/minimal value of the Lorentzian. If the area F is calculated
numerically, then the parameter sigma can be estimated.

"""

####################################
# Lorentzian model                 #
####################################

def make_lorentzianwithoutoffset_model(self, prefix=None):
    """ Create a model of a bare physical Lorentzian with an amplitude.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

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
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel
    """

    def physical_lorentzian(x, center, sigma):
        """ Function of a Lorentzian with unit height at center.

        @param numpy.array x: independent variable - e.g. frequency
        @param float center: center around which the distributions will be
        @param float sigma: half length at half maximum

        @return: numpy.array with length equals to input x and with the values
                 of a lorentzian.
        """
        return np.power(sigma, 2) / (np.power((center - x), 2) + np.power(sigma, 2))

    amplitude_model, params = self.make_amplitude_model(prefix=prefix)

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error(
            'The passed prefix <{0}> of type {1} is not a string and'
            'cannot be used as a prefix and will be ignored for now.'
            'Correct that!'.format(prefix, type(prefix)))
        lorentz_model = Model(physical_lorentzian, independent_vars='x')
    else:
        lorentz_model = Model(
            physical_lorentzian,
            independent_vars='x',
            prefix=prefix)

    full_lorentz_model = amplitude_model * lorentz_model
    params = full_lorentz_model.make_params()

    # introduces a new parameter, which is solely depending on others and which
    # will be not optimized:
    if prefix is None:
        prefix = ''
    full_lorentz_model.set_param_hint(
        '{0!s}fwhm'.format(prefix),
        expr="2*{0!s}sigma".format(prefix))
    # full_lorentz_model.set_param_hint('{0}contrast'.format(prefix),
    #                                   expr='(-100.0)')
                                      # expr='({0!s}amplitude/offset)*100'.format(prefix))
    # params.add('{0}contrast'.format(prefix), expr='({0!s}amplitude/offset)*100'.format(prefix))

    return full_lorentz_model, params


####################################
# Lorentzian model with offset     #
####################################


def make_lorentzian_model(self, prefix=None):
    """ Create a Lorentz model with amplitude and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_lorentzian_model.
    """

    lorentz_model, params = self.make_lorentzianwithoutoffset_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    lorentz_offset_model = lorentz_model + constant_model

    if prefix is None:
        prefix = ''

    lorentz_offset_model.set_param_hint('{0}contrast'.format(prefix),
                                        expr='({0}amplitude/offset)*100'.format(prefix))

    params = lorentz_offset_model.make_params()

    return lorentz_offset_model, params


#################################################
#    Mulitiple Lorentzian model with offset     #
#################################################

def make_multiplelorentzian_model(self, no_of_functions=1):
    """ Create a model with multiple lorentzians with offset.

    @param no_of_functions: for default=1 there is one lorentzian, else
                            more functions are added

    @return tuple: (object model, object params), for more description see in
                   the method make_lorentzian_model.
    """

    if no_of_functions == 1:
        multi_lorentz_model, params = self.make_lorentzian_model()
    else:
        prefix = 'l0_'
        multi_lorentz_model, params = self.make_lorentzianwithoutoffset_model(prefix=prefix)

        constant_model, params = self.make_constant_model()
        multi_lorentz_model = multi_lorentz_model + constant_model

        multi_lorentz_model.set_param_hint(
            '{0}contrast'.format(prefix),
            expr='({0}amplitude/offset)*100'.format(prefix))


        for ii in range(1, no_of_functions):
            prefix = 'l{0:d}_'.format(ii)
            multi_lorentz_model += self.make_lorentzianwithoutoffset_model(prefix=prefix)[0]
            multi_lorentz_model.set_param_hint(
                '{0}contrast'.format(prefix),
                expr='({0}amplitude/offset)*100'.format(prefix))

    params = multi_lorentz_model.make_params()

    return multi_lorentz_model, params

#################################################
#    Double Lorentzian model with offset        #
#################################################

def make_lorentziandouble_model(self):
    """ Create a model with double lorentzian with offset.

    @return tuple: (object model, object params), for more description see in
                   the method make_lorentzian_model.
    """

    return self.make_multiplelorentzian_model(no_of_functions=2)

#################################################
#       Triple Lorentzian model with offset     #
#################################################

def make_lorentziantriple_model(self):
    """ Create a model with triple lorentzian with offset.

    @return tuple: (object model, object params), for more description see in
                   the method make_lorentzian_model.
    """

    return self.make_multiplelorentzian_model(no_of_functions=3)

################################################################################
#                                                                              #
#                    Fit functions and their estimators                        #
#                                                                              #
################################################################################

################################################################################
#                 Single Lorentzian with offset fitting                        #
################################################################################

def make_lorentzian_fit(self, x_axis, data, estimator, units=None,
                        add_params=None, **kwargs):
    """ Perform a 1D lorentzian fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...
    """

    model, params = self.make_lorentzian_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
        self.log.warning('The 1D lorentzian fit did not work. Error '
                         'message: {0}\n'.format(result.message))

    # Write the parameters to allow human-readable output to be generated
    result_str_dict = OrderedDict()

    if units is None:
        units = ["arb. units"]

    result_str_dict['Position'] = {'value': result.params['center'].value,
                                   'error': result.params['center'].stderr,
                                   'unit': units[0]}

    result_str_dict['Contrast'] = {'value': abs(result.params['contrast'].value),
                                   'error': result.params['contrast'].stderr,
                                   'unit': '%'}

    result_str_dict['FWHM'] = {'value': result.params['fwhm'].value,
                               'error': result.params['fwhm'].stderr,
                               'unit': units[0]}

    result_str_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

    result.result_str_dict = result_str_dict
    return result

def estimate_lorentzian_dip(self, x_axis, data, params):
    """ Provides an estimator to obtain initial values for lorentzian function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """
    # check if parameters make sense
    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # check if input x-axis is ordered and increasing
    sorted_indices = np.argsort(x_axis)
    if not np.all(sorted_indices == np.arange(len(x_axis))):
        x_axis = x_axis[sorted_indices]
        data = data[sorted_indices]

    data_smooth, offset = self.find_offset_parameter(x_axis, data)

    # data_level = data-offset
    data_level = data_smooth - offset

    # calculate from the leveled data the amplitude:
    amplitude = data_level.min()

    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    fit_function = InterpolatedUnivariateSpline(x_axis, data_level,
                                            k=smoothing_spline)
    numerical_integral = fit_function.integral(x_axis[0], x_axis[-1])

    x_zero = x_axis[np.argmin(data_smooth)]

    # according to the derived formula, calculate sigma. The crucial part is
    # here that the offset was estimated correctly, then the area under the
    # curve is calculated correctly:
    sigma = np.abs(numerical_integral / (np.pi * amplitude))

    # auxiliary variables
    stepsize = x_axis[1] - x_axis[0]
    n_steps = len(x_axis)

    params['amplitude'].set(value=amplitude, max=-1e-12)
    params['sigma'].set(value=sigma, min=stepsize / 2,
                        max=(x_axis[-1] - x_axis[0]) * 10)
    params['center'].set(value=x_zero, min=(x_axis[0]) - n_steps * stepsize,
                         max=(x_axis[-1]) + n_steps * stepsize)
    params['offset'].set(value=offset)

    return error, params

def estimate_lorentzian_peak (self, x_axis, data, params):
    """ Provides a lorentzian offset peak estimator.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    # check if parameters make sense
    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # the peak and dip lorentzians have the same parameters:
    params_dip = params
    data_negative = data * (-1)

    error, params_ret = self.estimate_lorentzian_dip(
        x_axis,
        data_negative,
        params_dip)

    params['sigma'] = params_ret['sigma']
    params['offset'].set(value=-params_ret['offset'])
    # set the maximum to infinity, since that is the default value.
    params['amplitude'].set(
        value=-params_ret['amplitude'].value,
        min=-1e-12,
        max=np.inf)
    params['center'] = params_ret['center']

    return error, params


################################################################################
#                   Double Lorentzian with offset fitting                      #
################################################################################

def make_lorentziandouble_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a 1D double lorentzian dip fit with offset on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...

    """

    model, params = self.make_lorentziandouble_model()

    error, params = estimator(x_axis, data, params)

    # redefine values of additional parameters
    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
        self.log.error('The double lorentzian fit did not '
                     'work: {0}'.format(result.message))

    # Write the parameters to allow human-readable output to be generated
    result_str_dict = OrderedDict()

    if units is None:
        units = ["arb. u."]

    result_str_dict['Position 0'] = {'value': result.params['l0_center'].value,
                                     'error': result.params['l0_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Position 1'] = {'value': result.params['l1_center'].value,
                                     'error': result.params['l1_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Splitting'] = {'value': (result.params['l1_center'].value -
                                              result.params['l0_center'].value),
                                    'error': (result.params['l0_center'].stderr +
                                              result.params['l1_center'].stderr),
                                    'unit': units[0]}

    result_str_dict['Contrast 0'] = {'value': abs(result.params['l0_contrast'].value),
                                     'error': result.params['l0_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['Contrast 1'] = {'value': abs(result.params['l1_contrast'].value),
                                     'error': result.params['l1_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['FWHM 0'] = {'value': result.params['l0_fwhm'].value,
                                 'error': result.params['l0_fwhm'].stderr,
                                 'unit': units[0]}

    result_str_dict['FWHM 1'] = {'value': result.params['l1_fwhm'].value,
                                 'error': result.params['l1_fwhm'].stderr,
                                 'unit': units[0]}

    result_str_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

    result.result_str_dict = result_str_dict
    return result

def estimate_lorentziandouble_dip(self, x_axis, data, params,
                                  threshold_fraction=0.3,
                                  minimal_threshold=0.01,
                                  sigma_threshold_fraction=0.3):
    """ Provide an estimator for double lorentzian dip with offset.

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

    # smooth with gaussian filter and find offset:
    data_smooth, offset = self.find_offset_parameter(x_axis, data)

    # level data:
    data_level = data_smooth - offset

    # search for double lorentzian dip:
    ret_val = self._search_double_dip(x_axis, data_level, threshold_fraction,
                                      minimal_threshold,
                                      sigma_threshold_fraction)

    error = ret_val[0]
    sigma0_argleft, dip0_arg, sigma0_argright = ret_val[1:4]
    sigma1_argleft, dip1_arg, sigma1_argright = ret_val[4:7]

    if dip0_arg == dip1_arg:
        lorentz0_amplitude = data_level[dip0_arg] / 2.
        lorentz1_amplitude = lorentz0_amplitude
    else:
        lorentz0_amplitude = data_level[dip0_arg]
        lorentz1_amplitude = data_level[dip1_arg]

    lorentz0_center = x_axis[dip0_arg]
    lorentz1_center = x_axis[dip1_arg]

    # Both sigmas are set to the same value
    # numerical_integral_0 = (np.sum(data_level[sigma0_argleft:sigma0_argright]) *
    #                    (x_axis[sigma0_argright] - x_axis[sigma0_argleft]) /
    #                     len(data_level[sigma0_argleft:sigma0_argright]))

    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    fit_function = InterpolatedUnivariateSpline(x_axis, data_level,
                                            k=smoothing_spline)
    numerical_integral_0 = fit_function.integral(x_axis[sigma0_argleft],
                                             x_axis[sigma0_argright])

    lorentz0_sigma = abs(numerical_integral_0 / (np.pi * lorentz0_amplitude))

    numerical_integral_1 = numerical_integral_0

    lorentz1_sigma = abs(numerical_integral_1 / (np.pi * lorentz1_amplitude))

    # esstimate amplitude
    # lorentz0_amplitude = -1*abs(lorentz0_amplitude*np.pi*lorentz0_sigma)
    # lorentz1_amplitude = -1*abs(lorentz1_amplitude*np.pi*lorentz1_sigma)

    stepsize = x_axis[1] - x_axis[0]
    full_width = x_axis[-1] - x_axis[0]
    n_steps = len(x_axis)

    if lorentz0_center < lorentz1_center:
        params['l0_amplitude'].set(value=lorentz0_amplitude, max=-0.01)
        params['l0_sigma'].set(value=lorentz0_sigma, min=stepsize / 2,
                               max=full_width * 4)
        params['l0_center'].set(value=lorentz0_center,
                                min=(x_axis[0]) - n_steps * stepsize,
                                max=(x_axis[-1]) + n_steps * stepsize)
        params['l1_amplitude'].set(value=lorentz1_amplitude, max=-0.01)
        params['l1_sigma'].set(value=lorentz1_sigma, min=stepsize / 2,
                               max=full_width * 4)
        params['l1_center'].set(value=lorentz1_center,
                                min=(x_axis[0]) - n_steps * stepsize,
                                max=(x_axis[-1]) + n_steps * stepsize)
    else:
        params['l0_amplitude'].set(value=lorentz1_amplitude, max=-0.01)
        params['l0_sigma'].set(value=lorentz1_sigma, min=stepsize / 2,
                               max=full_width * 4)
        params['l0_center'].set(value=lorentz1_center,
                                min=(x_axis[0]) - n_steps * stepsize,
                                max=(x_axis[-1]) + n_steps * stepsize)
        params['l1_amplitude'].set(value=lorentz0_amplitude, max=-0.01)
        params['l1_sigma'].set(value=lorentz0_sigma, min=stepsize / 2,
                               max=full_width * 4)
        params['l1_center'].set(value=lorentz0_center,
                                min=(x_axis[0]) - n_steps * stepsize,
                                max=(x_axis[-1]) + n_steps * stepsize)

    params['offset'].set(value=offset)

    return error, params

def estimate_lorentziandouble_peak(self, x_axis, data, params,
                                   threshold_fraction=0.3,
                                   minimal_threshold=0.01,
                                   sigma_threshold_fraction=0.3):
    """ Provide an estimator for double lorentzian peak with offset.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    # check if parameters make sense
    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # the peak and dip lorentzians have the same parameters:
    params_dip = params
    data_negative = data * (-1)

    error, params_ret = self.estimate_lorentziandouble_dip(x_axis,
                                                           data_negative,
                                                           params_dip)

    params['l0_sigma'] = params_ret['l0_sigma']
    # set the maximum to infinity, since that is the default value.
    params['l0_amplitude'].set(value=-params_ret['l0_amplitude'].value, min=-1e-12,
                               max=np.inf)
    params['l0_center'] = params_ret['l0_center']
    params['l1_amplitude'].set(value=-params_ret['l1_amplitude'].value, min=-1e-12,
                               max=np.inf)
    params['l1_sigma'] = params_ret['l1_sigma']
    params['l1_center'] = params_ret['l1_center']

    params['offset'].set(value=-params_ret['offset'])

    return error, params


############################################################################
#                               N15 fitting                                #
############################################################################

def estimate_lorentziandouble_N15(self, x_axis, data, params):
    """ Estimation of a the hyperfine interaction of a N15 nuclear spin.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values

    Provide an estimation of all fitting parameters for fitting the
    two equidistant lorentzian dips of the hyperfine interaction
    of a N15 nuclear spin. Here the splitting is set as an expression,
    if the splitting is not exactly 3.03MHz the fit will not work.
    """

    # check if parameters make sense
    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    hf_splitting = 3.03 * 1e6 # Hz

    # this is an estimator, for a physical application, therefore the x_axis
    # should fulfill certain constraints:
    length_x_scan = x_axis[-1] - x_axis[0]

    if length_x_scan < hf_splitting/2 or hf_splitting > 1e9:
        self.log.error('The N15 estimator expects an x_axis with a length in the '
                       'range [{0},{1}]Hz, but the passed x_axis has a length of '
                       '{2}, which is not sensible for the N15 estimator. Correct '
                       'that!'.format(hf_splitting / 2, 1e9, length_x_scan))
        return -1, params

    data_smooth_lorentz, offset = self.find_offset_parameter(x_axis, data)

    # filter should always have a length of approx linewidth 1MHz
    points_within_1MHz = len(x_axis) / (x_axis.max() - x_axis.min()) * 1e6

    # filter should have a width of 4 MHz
    x_filter = np.linspace(0, 4 * points_within_1MHz, 4 * points_within_1MHz)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0) * (x_filter < len(x_filter) / 4),
                                      (x_filter >= len(x_filter) / 4) * (x_filter < len(x_filter) * 3 / 4),
                                      (x_filter >= len(x_filter) * 3 / 4)],
                           [1, 0, 1])

    # if the filter is smaller than 3 points a convolution does not make sense
    if len(lorentz) >= 3:
        data_convolved = filters.convolve1d(data_smooth_lorentz,
                                            lorentz / lorentz.sum(),
                                            mode='constant',
                                            cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()] - hf_splitting / 2.
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]

    # data_level = data_smooth_lorentz - data_smooth_lorentz.max()
    data_level = data_smooth_lorentz - offset

    minimum_level = data_level.min()
    # integral of data:
    fit_function = InterpolatedUnivariateSpline(x_axis, data_level, k=1)
    Integral = fit_function.integral(x_axis[0], x_axis[-1])

    # assume both peaks contribute to the linewidth, so devive by 2, that makes
    # the peaks narrower
    sigma = abs(Integral / (np.pi * minimum_level))

    amplitude = -abs(minimum_level)

    minimal_sigma = x_axis[1] - x_axis[0]
    maximal_sigma = x_axis[-1] - x_axis[0]

    params['l0_amplitude'].set(value=amplitude, max=-1e-6)
    params['l0_center'].set(value=x_axis_min)
    params['l0_sigma'].set(value=sigma, min=minimal_sigma,
                           max=maximal_sigma)
    params['l1_amplitude'].set(value=params['l0_amplitude'].value,
                               max=-1e-6)
    params['l1_center'].set(value=params['l0_center'].value + hf_splitting,
                            expr='l0_center+{0}'.format(hf_splitting))
    params['l1_sigma'].set(value=params['l0_sigma'].value,
                           min=minimal_sigma, max=maximal_sigma,
                           expr='l0_sigma')
    params['offset'].set(value=offset)

    return error, params


############################################################################
#                                                                          #
#                      Triple Lorentzian fitting                           #
#                                                                          #
############################################################################
#Todo: check where code breaks
# Old Method Names:
# make_N14_fit

def make_lorentziantriple_fit(self, x_axis, data, estimator, units=None,
                            add_params=None, **kwargs):
    """ Perform a triple lorentzian fit

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...
    """

    model, params = self.make_lorentziantriple_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = model.fit(data, x=x_axis, params=params, **kwargs)
        self.log.error('The triple lorentzian fit did not '
                       'work: {0}'.format(result.message))

    # Write the parameters to allow human-readable output to be generated
    result_str_dict = OrderedDict()

    if units is None:
        units = ["arb. units"]

    result_str_dict['Position 0'] = {'value': result.params['l0_center'].value,
                                     'error': result.params['l0_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Position 1'] = {'value': result.params['l1_center'].value,
                                     'error': result.params['l1_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Position 2'] = {'value': result.params['l2_center'].value,
                                     'error': result.params['l2_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Contrast 0'] = {'value': abs(result.params['l0_contrast'].value),
                                     'error': result.params['l0_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['Contrast 1'] = {'value': abs(result.params['l1_contrast'].value),
                                     'error': result.params['l1_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['Contrast 2'] = {'value': abs(result.params['l2_contrast'].value),
                                     'error': result.params['l2_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['FWHM 0'] = {'value': result.params['l0_sigma'].value,
                                 'error': result.params['l0_sigma'].stderr,
                                 'unit': units[0]}

    result_str_dict['FWHM 1'] = {'value': result.params['l1_sigma'].value,
                                 'error': result.params['l1_sigma'].stderr,
                                 'unit': units[0]}

    result_str_dict['FWHM 2'] = {'value': result.params['l2_sigma'].value,
                                 'error': result.params['l2_sigma'].stderr,
                                 'unit': units[0]}

    result_str_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

    result.result_str_dict = result_str_dict
    return result

def estimate_lorentziantriple_N14(self, x_axis, data, params):
    """ Estimation of a the hyperfine interaction of a N14 nuclear spin.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values

    Provide an estimation of all fitting parameters for fitting the
    three equidistant lorentzian dips of the hyperfine interaction
    of a N14 nuclear spin. Here the splitting is set as an expression,
    if the splitting is not exactly 2.15MHz the fit will not work.

    Note that this estimator is really specific to a physical scenario.
    Therefore the x_axis is expected to be in SI units Hz, and the x_axis should
    be at least half of the hyperfine interaction long (2.15MHz) but also be
    less then 1 GHz. Otherwise the underlying estimation algorithm will not
    work.
    """

    # check if parameters make sense
    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    hf_splitting = 2.15e6 # hyperfine splitting for a N14 spin

    # this is an estimator, for a physical application, therefore the x_axis
    # should fulfill certain constraints:
    length_x_scan = x_axis[-1] - x_axis[0]

    if length_x_scan < hf_splitting/2 or hf_splitting > 1e9:
        self.log.error('The N14 estimator expects an x_axis with a length in the '
                     'range [{0},{1}]Hz, but the passed x_axis has a length of '
                     '{2}, which is not sensible for the N14 estimator. Correct '
                     'that!'.format(hf_splitting/2, 1e9, length_x_scan))
        return -1, params

    # find the offset parameter, which should be in the fit the zero level:
    data_smooth_lorentz, offset = self.find_offset_parameter(x_axis, data)

    # Create now a filter of length 5MHz, then create a step-wise function with
    # three dips. This step-wise function will be convolved with the smoothed
    # data, where the maximal contribution will be if the peaks are within the
    # filter. Take that to obtain from that the accurate peak position:

    # filter of one dip should always have a length of approx linewidth 1MHz
    points_within_1MHz = len(x_axis)/(x_axis.max()-x_axis.min()) * 1e6

    # filter should have a width of 5MHz
    x_filter = np.linspace(0, 5*points_within_1MHz, 5*points_within_1MHz)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0)                   * (x_filter < len(x_filter)*1/5),
                                      (x_filter >= len(x_filter)*1/5)   * (x_filter < len(x_filter)*2/5),
                                      (x_filter >= len(x_filter)*2/5)   * (x_filter < len(x_filter)*3/5),
                                      (x_filter >= len(x_filter)*3/5)   * (x_filter < len(x_filter)*4/5),
                                      (x_filter >= len(x_filter)*4/5)],
                           [1, 0, 1, 0, 1])

    # if the filter is smaller than 5 points a convolution does not make sense
    if len(lorentz) >= 5:
        data_convolved = filters.convolve1d(data_smooth_lorentz,
                                            lorentz/lorentz.sum(),
                                            mode='constant',
                                            cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()]-2.15*1e6
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]-2.15*1e6

    # level of the data, that means the offset is subtracted and the real data
    # are present
    data_level = data_smooth_lorentz - offset
    minimum_level = data_level.min()

    # In order to perform a smooth integral to obtain the area under the curve
    # make an interpolation of the passed data, in case they are very sparse.
    # That increases the accuracy of the calculated Integral.
    # integral of data corresponds to sqrt(2) * Amplitude * Sigma

    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    fit_function = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
    integrated_area = fit_function.integral(x_axis[0], x_axis[-1])

    # sigma = abs(integrated_area / (minimum_level/np.pi))
    # That is wrong, so commenting out:
    sigma = abs(integrated_area /(np.pi * minimum_level))/3

    amplitude = -1*abs(minimum_level)

    # Since the total amplitude of the lorentzian is depending on sigma it makes
    # sense to vary sigma within an interval, which is smaller than the minimal
    # distance between two points. Then the fit algorithm will have a larger
    # range to determine the amplitude properly. That is the main issue with the
    # fit!
    minimal_linewidth = (x_axis[1]-x_axis[0])/4
    maximal_linewidth = x_axis[-1]-x_axis[0]

    # The linewidth of all the lorentzians are set to be the same! that is a
    # physical constraint for the N14 fitting.

    # Fill the parameter container, with the estimated values, which should be
    # passed to the fit algorithm:
    params['l0_amplitude'].set(value=amplitude, max=-1e-6)
    params['l0_center'].set(value=x_axis_min)
    params['l0_sigma'].set(value=sigma, min=minimal_linewidth,
                           max=maximal_linewidth)
    params['l1_amplitude'].set(value=amplitude, max=-1e-6)
    params['l1_center'].set(value=x_axis_min+hf_splitting,
                            expr='l0_center+{0}'.format(hf_splitting))
    params['l1_sigma'].set(value=sigma, min=minimal_linewidth,
                           max=maximal_linewidth, expr='l0_sigma')
    params['l2_amplitude'].set(value=amplitude, max=-1e-6)
    params['l2_center'].set(value=x_axis_min+hf_splitting*2,
                            expr='l0_center+{0}'.format(hf_splitting*2))
    params['l2_sigma'].set(value=sigma, min=minimal_linewidth,
                           max=maximal_linewidth, expr='l0_sigma')
    params['offset'].set(value=offset)

    return error, params
