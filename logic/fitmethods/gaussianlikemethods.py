# -*- coding: utf-8 -*-

"""
This file contains methods for gaussian-like fitting, these methods
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


import numpy as np
from lmfit.models import Model, GaussianModel, ConstantModel
from lmfit import Parameters
from collections import OrderedDict

from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.ndimage import filters

############################################################################
#                                                                          #
#                          Defining models                                 #
#                                                                          #
############################################################################

####################################
# Gaussian model                   #
####################################


def make_gaussianwithoutoffset_model(self, prefix=None):
    """ Create a model of a gaussian with specified amplitude.

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
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html
    """

    def physical_gauss(x, center, sigma):
        """ Function of a bare Gaussian with unit height at center.

        @param numpy.array x: independent variable - e.g. frequency
        @param float center: center around which the distributions (expectation
                             value).
        @param float sigma: standard deviation of the gaussian

        @return: numpy.array with length equals to input x and with the values
                 of a bare Gaussian.
        """
        return np.exp(- np.power((center - x), 2) / (2 * np.power(sigma, 2)))

    amplitude_model, params = self.make_amplitude_model(prefix=prefix)

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and'
                       'cannot be used as a prefix and will be ignored for now.'
                       'Correct that!'.format(prefix, type(prefix)))
        gaussian_model = Model(physical_gauss, independent_vars='x')
    else:
        gaussian_model = Model(physical_gauss, independent_vars='x',
                               prefix=prefix)

    full_gaussian_model = amplitude_model * gaussian_model

    if prefix is None:
        prefix = ''
    full_gaussian_model.set_param_hint('{0!s}fwhm'.format(prefix),
                                       expr="2.3548200450309493*{0}sigma".format(prefix))

    params = full_gaussian_model.make_params()

    return full_gaussian_model, params

####################################
# 1D Gaussian model with offset    #
####################################

def make_gaussian_model(self, prefix=None):
    """ Create a gauss model with amplitude and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_gaussianwithoutoffset_model.
    """

    gaussian_model, params = self.make_gaussianwithoutoffset_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    gaussian_offset_model = gaussian_model + constant_model

    if prefix is None:
        prefix = ''

    gaussian_offset_model.set_param_hint('{0}contrast'.format(prefix),
                                         expr='({0}amplitude/offset)*100'.format(prefix))

    params = gaussian_offset_model.make_params()

    return gaussian_offset_model, params

######################################################
# 1D Gaussian model with linear (inclined) offset    #
######################################################

def make_gaussianlinearoffset_model(self, prefix=None):
    """ Create a gauss with a linear offset (i.e. a slope).

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_gaussianwithoutoffset_model.
    """

    # Note that the offset parameter comes here from the gauss model and not
    # from the slope model.
    slope_model, params = self.make_slope_model(prefix)
    gaussian_model, params = self.make_gaussian_model(prefix)

    gaussian_linear_offset = gaussian_model + slope_model
    params = gaussian_linear_offset.make_params()

    return gaussian_linear_offset, params

##########################################
# 1D Multiple Gaussian Model with offset #
##########################################


def make_multiplegaussianoffset_model(self, no_of_functions=1):
    """ Create a model with multiple gaussian with offset.

    @param no_of_functions: for default=1 there is one gaussian, else
                            more functions are added

    @return tuple: (object model, object params), for more description see in
                   the method make_gaussianwithoutoffset_model.
    """

    if no_of_functions == 1:
        multi_gaussian_model, params = self.make_gaussian_model()
    else:

        prefix = 'g0_'
        multi_gaussian_model, params = self.make_gaussianwithoutoffset_model(prefix=prefix)

        constant_model, params = self.make_constant_model()
        multi_gaussian_model = multi_gaussian_model + constant_model

        multi_gaussian_model.set_param_hint('{0}contrast'.format(prefix),
                                            expr='({0}amplitude/offset)*100'.format(prefix))

        for ii in range(1, no_of_functions):

            prefix = 'g{0:d}_'.format(ii)
            multi_gaussian_model += self.make_gaussianwithoutoffset_model(prefix=prefix)[0]
            multi_gaussian_model.set_param_hint('{0}contrast'.format(prefix),
                                                expr='({0}amplitude/offset)*100'.format(prefix))

    params = multi_gaussian_model.make_params()

    return multi_gaussian_model, params

##########################################
#   1D Double Gaussian Model with offset #
##########################################


def make_gaussiandouble_model(self):
    """ Create a model with double gaussian with offset.

    @return tuple: (object model, object params), for more description see in
                   the method make_gaussianwithoutoffset_model.
    """

    return self.make_multiplegaussianoffset_model(no_of_functions=2)

##########################################
#   1D Triple Gaussian Model with offset #
##########################################


def make_gaussiantriple_model(self):
    """ Create a model with double gaussian with offset.

    @return tuple: (object model, object params), for more description see in
                   the method make_gaussianwithoutoffset_model.
    """

    return self.make_multiplegaussianoffset_model(no_of_functions=3)

#####################
# 2D gaussian model #
#####################

def make_twoDgaussian_model(self, prefix=None):
    """ Creates a model of the 2D gaussian function.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_gaussianwithoutoffset_model.

    """

    def twoDgaussian_function(x, amplitude, center_x, center_y, sigma_x, sigma_y,
                              theta, offset):
        """ Provide a two dimensional gaussian function.

        @param float amplitude: Amplitude of gaussian
        @param float center_x: x value of maximum
        @param float center_y: y value of maximum
        @param float sigma_x: standard deviation in x direction
        @param float sigma_y: standard deviation in y direction
        @param float theta: angle for eliptical gaussians
        @param float offset: offset

        @return callable function: returns the reference to the function

        Function taken from:
        http://stackoverflow.com/questions/21566379/fitting-a-2d-gaussian-function-using-scipy-optimize-curve-fit-valueerror-and-m/21566831

        Question from: http://stackoverflow.com/users/2097737/bland
                       http://stackoverflow.com/users/3273102/kokomoking
                       http://stackoverflow.com/users/2767207/jojodmo
        Answer: http://stackoverflow.com/users/1461210/ali-m
                http://stackoverflow.com/users/5234/mrjrdnthms
        """

        # FIXME: x_data_tuple: dimension of arrays
        # @param np.arra[k][M] x_data_tuple: array which is (k,M)-shaped,
        #                                   x and y values

        (u, v) = x
        center_x = float(center_x)
        center_y = float(center_y)

        a = (np.cos(theta) ** 2) / (2 * sigma_x ** 2) \
            + (np.sin(theta) ** 2) / (2 * sigma_y ** 2)
        b = -(np.sin(2 * theta)) / (4 * sigma_x ** 2) \
            + (np.sin(2 * theta)) / (4 * sigma_y ** 2)
        c = (np.sin(theta) ** 2) / (2 * sigma_x ** 2) \
            + (np.cos(theta) ** 2) / (2 * sigma_y ** 2)
        g = offset + amplitude * np.exp(- (a * ((u - center_x) ** 2)
                                           + 2 * b * (u - center_x) * (v - center_y)
                                           + c * ((v - center_y) ** 2)))
        return g.ravel()

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and'
                     'cannot be used as a prefix and will be ignored for now.'
                     'Correct that!'.format(prefix, type(prefix)))
        gaussian_2d_model = Model(twoDgaussian_function, independent_vars='x')
    else:
        gaussian_2d_model = Model(twoDgaussian_function, independent_vars='x',
                               prefix=prefix)

    params = gaussian_2d_model.make_params()

    return gaussian_2d_model, params

################################################################################
#                                                                              #
#                    Fit functions and their estimators                        #
#                                                                              #
################################################################################

###################################
# 1D Gaussian with flat offset    #
###################################

def make_gaussian_fit(self, x_axis, data, estimator, units=None, add_params=None):
    """ Perform a 1D gaussian peak fit on the provided data.

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

    mod_final, params = self.make_gaussian_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = mod_final.fit(data, x=x_axis, params=params)
    except:
        self.log.warning('The 1D gaussian peak fit did not work. Error '
                       'message: {0}\n'.format(result.message))

    if units is None:
            units = ['arb. unit', 'arb. unit']

    result_str_dict = OrderedDict()  # create result string for gui

    #result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
    #                                    'error': result.params['amplitude'].stderr,
    #                                    'unit': units[1]}                               #amplitude

    result_str_dict['Position'] = {'value': result.params['center'].value,
                                        'error': result.params['center'].stderr,
                                        'unit': units[0]}                               #position

    #result_str_dict['Standard deviation'] = {'value': result.params['sigma'].value,
    #                                'error': result.params['sigma'].stderr,
    #                                'unit': units[0]}                               #standart deviation

    result_str_dict['Linewidth'] = {'value': result.params['fwhm'].value,
                                        'error': result.params['fwhm'].stderr,
                                        'unit': units[0]}                               #FWHM

    result_str_dict['Contrast'] = {'value': result.params['contrast'].value,
                                        'error': result.params['contrast'].stderr,
                                        'unit': '%'}                                    #Contrast
    result.result_str_dict = result_str_dict

    return result



def estimate_gaussian_peak(self, x_axis, data, params):
    """ Provides a gaussian offset peak estimator.

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

    # If the estimator is not good enough one can start improvement with
    # a convolution

    # auxiliary variables
    stepsize = abs(x_axis[1] - x_axis[0])
    n_steps = len(x_axis)

    # Smooth the provided data, so that noise fluctuations will not disturb the
    # parameter estimation. This value performs the best in many scenarios:
    std_dev = 2
    data_smoothed = filters.gaussian_filter1d(data, std_dev)

    # Define constraints:
    # maximal and minimal the length of the given array to the right and to the
    # left:
    center_min = (x_axis[0]) - n_steps * stepsize
    center_max = (x_axis[-1]) + n_steps * stepsize
    ampl_min = 0
    sigma_min = stepsize
    sigma_max = 3 * (x_axis[-1] - x_axis[0])

    # set parameters:
    offset = data_smoothed.min()
    params['offset'].set(value=offset)

    # it is more reliable to select the maximal value rather then
    # calculating the first moment of the gaussian distribution (which is the
    # mean value), since it is unreliable if the distribution begins or ends at
    # the edges of the data (but it helps a lot for standard deviation):
    mean_val_calc = np.sum(x_axis*data_smoothed) / np.sum(data_smoothed)
    params['center'].set(value=x_axis[np.argmax(data_smoothed)],
                         min=center_min, max=center_max)

    # calculate the second moment of the gaussian distribution:
    #   int (x^2 * f(x) dx) :
    mom2 = np.sum((x_axis)**2 * data_smoothed) / np.sum(data_smoothed)

    # and use the standard formula to obtain the standard deviation:
    #   sigma^2 = int( (x - mean)^2 f(x) dx ) = int (x^2 * f(x) dx) - mean^2

    # If the mean is situated at the edges of the distribution then this
    # procedure performs better then setting the initial value for sigma to
    # 1/3 of the length of the distribution since the calculated value for the
    # mean is then higher, which will decrease eventually the initial value for
    # sigma. But if the peak values is within the distribution the standard
    # deviation formula performs even better:
    params['sigma'].set(value=np.sqrt(abs(mom2 - mean_val_calc**2)),
                        min=sigma_min, max=sigma_max)
    # params['sigma'].set(value=(x_axis.max() - x_axis.min()) / 3.)

    # Do not set the maximal amplitude value based on the distribution, since
    # the fit will fail if the peak is at the edges or beyond the range of the
    # x values.
    params['amplitude'].set(value=data_smoothed.max()-data_smoothed.min(),
                            min=ampl_min)

    return error, params

def estimate_gaussian_dip(self, x_axis, data, params):
    """ Provides a gaussian offset dip estimator.

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

    # the peak and dip gaussian have the same parameters:
    params_peak = params
    data_negative = data * (-1)

    error, params_ret = self.estimate_gaussian_peak(x_axis,
                                                          data_negative,
                                                          params_peak
                                                          )

    params['sigma'] = params_ret['sigma']
    params['offset'].set(value=-params_ret['offset'])
    # set the maximum to infinity, since that is the default value.
    params['amplitude'].set(value=-params_ret['amplitude'].value, min=-np.inf,
                            max=1e-12)
    params['center'] = params_ret['center']

    return error, params

##############################################
# 1D Gaussian with linear inclined offset    #
##############################################

def make_gaussianlinearoffset_fit(self, x_axis, data, estimator, units=None, add_params=None):
    """ Perform a 1D gaussian peak fit with linear offset on the provided data.
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

    mod_final, params = self.make_gaussianlinearoffset_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = mod_final.fit(data, x=x_axis, params=params)
    except:
        self.log.warning('The 1D gaussian peak fit did not work. Error '
                       'message: {0}\n'.format(result.message))
    if units is None:
            units = ['arb. unit', 'arb. unit']

    result_str_dict = OrderedDict()  # create result string for gui

    #result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
    #                                    'error': result.params['amplitude'].stderr,
    #                                    'unit': units[1]}                               #amplitude

    result_str_dict['Position'] = {'value': result.params['center'].value,
                                        'error': result.params['center'].stderr,
                                        'unit': units[0]}                               #position

    #result_str_dict['Standard deviation'] = {'value': result.params['sigma'].value,
    #                                'error': result.params['sigma'].stderr,
    #                                'unit': units[0]}                               #standart deviation

    result_str_dict['Linewidth'] = {'value': result.params['fwhm'].value,
                                        'error': result.params['fwhm'].stderr,
                                        'unit': units[0]}                               #FWHM

    result_str_dict['Contrast'] = {'value': result.params['contrast'].value,
                                        'error': result.params['contrast'].stderr,
                                        'unit': '%'}                                    #Contrast

    #result_str_dict['Slope'] = {'value': result.params['slope'].value,
    #                                    'error': result.params['slope'].stderr,
    #                                    'unit': ''}                                    #Slope

    result.result_str_dict = result_str_dict

    return result

def estimate_gaussianlinearoffset_peak(self, x_axis, data, params):
    """ Provides a gauss peak estimator with a linear changing offset.

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

    # try at first a fit with the ordinary gauss function
    res_ordinary_gauss = self.make_gaussian_fit(
        x_axis=x_axis,
        data=data,
        units=None,
        estimator=self.estimate_gaussian_peak
    )

    # subtract the result and perform again a linear fit:
    data_subtracted = data - res_ordinary_gauss.best_fit

    res_linear = self.make_linear_fit(
        x_axis=x_axis,
        data=data_subtracted,
        estimator=self.estimate_linear
    )

    # this way works much better than performing at first a linear fit,
    # subtracting the fit and make an ordinary gaussian fit. Especially for a
    # peak at the borders, this method is much more beneficial.

    # assign the obtained values for the initial fit:
    params['offset'] = res_ordinary_gauss.params['offset']
    params['center'] = res_ordinary_gauss.params['center']
    params['amplitude'] = res_ordinary_gauss.params['amplitude']
    params['sigma'] = res_ordinary_gauss.params['sigma']
    params['slope'] = res_linear.params['slope']

    return error, params

#################################
# Two Gaussian with flat offset #
#################################

def make_gaussiandouble_fit(self, x_axis, data, estimator,
                            units=None,
                            add_params=None,
                            threshold_fraction=0.4,
                            minimal_threshold=0.2,
                            sigma_threshold_fraction=0.3):
    """ Perform a 1D two gaussian dip fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.
    @param float threshold_fraction : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowerd to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...
    """
    if units is None:
        units = ['arb. unit', 'arb. unit']

    model, params = self.make_multiplegaussianoffset_model(no_of_functions=2)

    error, params = estimator(x_axis, data, params,
                              threshold_fraction,
                              minimal_threshold,
                              sigma_threshold_fraction
                              )

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = model.fit(data, x=x_axis, params=params)
    except:
        result = model.fit(data, x=x_axis, params=params)
        self.log.warning('The double gaussian dip fit did not work: {0}'.format(
            result.message))

    # Write the parameters to allow human-readable output to be generated
    result_str_dict = OrderedDict()

    result_str_dict['Position 0'] = {'value': result.params['g0_center'].value,
                                     'error': result.params['g0_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Position 1'] = {'value': result.params['g1_center'].value,
                                     'error': result.params['g1_center'].stderr,
                                     'unit': units[0]}

    result_str_dict['Contrast 0'] = {'value': abs(result.params['g0_contrast'].value),
                                     'error': result.params['g0_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['Contrast 1'] = {'value': abs(result.params['g1_contrast'].value),
                                     'error': result.params['g1_contrast'].stderr,
                                     'unit': '%'}

    result_str_dict['Linewidth 0'] = {'value': result.params['g0_sigma'].value,
                                      'error': result.params['g0_sigma'].stderr,
                                      'unit': units[0]}

    result_str_dict['Linewidth 1'] = {'value': result.params['g1_sigma'].value,
                                      'error': result.params['g1_sigma'].stderr,
                                      'unit': units[0]}

    result_str_dict['chi_sqr'] = {'value': result.chisqr, 'unit': ''}

    result.result_str_dict = result_str_dict
    return result

def estimate_gaussiandouble_peak(self, x_axis, data, params,
                                threshold_fraction=0.4, minimal_threshold=0.1,
                                sigma_threshold_fraction=0.2):
    """ Provide an estimator for a double gaussian peak fit with the parameters
    coming from the physical properties of an experiment done in gated counter:
                    - positive peak
                    - no values below 0
                    - rather broad overlapping functions

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set
    @param float threshold_fraction : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowerd to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return int error: error code (0:OK, -1:error)
    @return Parameters object params: estimated values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)


    mod_lor, params_lor = self.make_multiplelorentzian_model(no_of_functions=2)

    error, params_lor = self.estimate_lorentziandouble_dip(x_axis=x_axis,
                                                     data=-data,
                                                     params=params_lor,
                                                     threshold_fraction=threshold_fraction,
                                                     minimal_threshold=minimal_threshold,
                                                     sigma_threshold_fraction=sigma_threshold_fraction)

    params['g0_amplitude'].value = -params_lor['l0_amplitude'].value
    params['g0_center'].value = params_lor['l0_center'].value
    params['g0_sigma'].value = params_lor['l0_sigma'].value/(np.sqrt(2*np.log(2)))
    params['g1_amplitude'].value = -params_lor['l1_amplitude'].value
    params['g1_center'].value = params_lor['l1_center'].value
    params['g1_sigma'].value = params_lor['l1_sigma'].value/(np.sqrt(2*np.log(2)))
    params['offset'].value = -params_lor['offset'].value

    return error, params

def estimate_gaussiandouble_dip(self, x_axis, data, params,
                               threshold_fraction=0.4, minimal_threshold=0.1,
                               sigma_threshold_fraction=0.2):
    """ Provide an estimator for a double gaussian dip fit with the parameters
    coming from the physical properties of an experiment done in gated counter:
                    - positive peak
                    - no values below 0
                    - rather broad overlapping functions

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set
    @param float threshold_fraction : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowerd to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return int error: error code (0:OK, -1:error)
    @return Parameters object params: estimated values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    mod_lor, params_lor = self.make_multiplelorentzian_model(no_of_functions=2)

    error, params_lor = self.estimate_lorentziandouble_dip(x_axis=x_axis,
                                                     data=data,
                                                     params=params_lor,
                                                     threshold_fraction=threshold_fraction,
                                                     minimal_threshold=minimal_threshold,
                                                     sigma_threshold_fraction=sigma_threshold_fraction)

    params['g0_amplitude'].value = params_lor['l0_amplitude'].value
    params['g0_center'].value = params_lor['l0_center'].value
    params['g0_sigma'].value = params_lor['l0_sigma'].value/(np.sqrt(2*np.log(2)))
    params['g1_amplitude'].value = params_lor['l1_amplitude'].value
    params['g1_center'].value = params_lor['l1_center'].value
    params['g1_sigma'].value = params_lor['l1_sigma'].value/(np.sqrt(2*np.log(2)))
    params['offset'].value = params_lor['offset'].value

    return error, params

###################################
# 2D Gaussian with flat offset    #
###################################

# TODO: I think this has an offset, and it should be named so to be consistent with
#       the 1D functions.

def make_twoDgaussian_fit(self, xy_axes, data, estimator, units=None, add_params=None):
    """ This method performes a 2D gaussian fit on the provided data.

    @param numpy.array xy_axes: 2D axes values. xy_axes[0] contains x_axis and
                                xy_axes[1] contains y_axis
    @param numpy.array data: 2D matrix data, should have the dimension as
                             len(xy_axes[0]) x len(xy_axes[1]).
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

    x_axis, y_axis = xy_axes

    gaussian_2d_model, params = self.make_twoDgaussian_model()

    error, params = estimator(x_axis=x_axis, y_axis=y_axis,
                              data=data, params=params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = gaussian_2d_model.fit(data, x=xy_axes, params=params)
    except:
        result = gaussian_2d_model.fit(data, x=xy_axes, params=params)
        self.log.warning('The 2D gaussian fit did not work: {0}'.format(
                       result.message))

    return result

def estimate_twoDgaussian(self, x_axis, y_axis, data, params):
    """ Provide a simple two dimensional gaussian function.

    @param numpy.array x_axis: 1D x axis values
    @param numpy.array y_axis: 1D y axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

        Explanation of the return parameter:
            int error: error code (0:OK, -1:error)
            Parameters object params: set parameters of initial values
    """

    # TODO:Make clever estimator
    # FIXME: 1D array x_axis, y_axis, 2D data???

    #            #needed me 1 hour to think about, but not needed in the end...maybe needed at a later point
    #            len_x=np.where(x_axis[0]==x_axis)[0][1]
    #            len_y=len(data)/len_x

    amplitude = float(data.max() - data.min())

    center_x = x_axis[data.argmax()]
    center_y = y_axis[data.argmax()]

    sigma_x = (x_axis.max() - x_axis.min()) / 3.
    sigma_y = (y_axis.max() - y_axis.min()) / 3.
    theta = 0.0
    offset = float(data.min())

    # check for sensible values
    parameters = [x_axis, y_axis, data]

    error = 0
    for var in parameters:
        # FIXME: Why don't you check earlier?
        # FIXME: Check for 1D array, 2D
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            self.log.error('Given parameter is not an array.')
            amplitude = 0.
            center_x = 0.
            center_y = 0.
            sigma_x = 0.
            sigma_y = 0.
            theta = 0.0
            offset = 0.
            error = -1

    # auxiliary variables:
    stepsize_x = x_axis[1]-x_axis[0]
    stepsize_y = y_axis[1]-y_axis[0]
    n_steps_x = len(x_axis)
    n_steps_y = len(y_axis)

    # populate the parameter container:
    params['amplitude'].set(value=amplitude, min=100, max=1e7)
    params['sigma_x'].set(value=sigma_x, min=1*stepsize_x,
                          max=3*(x_axis[-1]-x_axis[0]))
    params['sigma_y'].set(value=sigma_y, min=1*stepsize_y,
                          max=3*(y_axis[-1]-y_axis[0]))
    params['center_x'].set(value=center_x, min=(x_axis[0])-n_steps_x*stepsize_x,
                           max=x_axis[-1]+n_steps_x*stepsize_x)
    params['center_y'].set(value=center_y, min=(y_axis[0])-n_steps_y*stepsize_y,
                           max=y_axis[-1]+n_steps_y*stepsize_y)
    params['theta'].set(value=theta, min=0, max=np.pi)
    params['offset'].set(value=offset, min=0, max=1e7)

    return error, params

def estimate_twoDgaussian_MLE(self, x_axis, y_axis, data, params):
    """ Provide an estimator for 2D gaussian based on maximum likelihood estimation.

    @param numpy.array x_axis: 1D x axis values
    @param numpy.array y_axis: 1D y axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

        Explanation of the return parameter:
            int error: error code (0:OK, -1:error)
            Parameters object params: set parameters of initial values

    For the parameters characterizing of the two dimensional gaussian a maximum
    likelihood estimation is used (at the moment only for the center_x and
    center_y values).
    """

    # TODO: Make good estimates for sigma_x, sigma_y and theta

    amplitude = float(data.max() - data.min())

    # By calculating the log likelihood of the 2D gaussian pdf, one obtain for
    # the minimization of the center_x or center_y values the following formula
    # (which are in fact just the expectation/mean value formula):
    center_x = np.sum(x_axis * data) / np.sum(data)
    center_y = np.sum(y_axis * data) / np.sum(data)

    sigma_x = (x_axis.max() - x_axis.min()) / 3.
    sigma_y = (y_axis.max() - y_axis.min()) / 3.
    theta = 0.0
    offset = float(data.min())
    error = 0
    # check for sensible values
    parameters = [x_axis, y_axis, data]
    for var in parameters:
        # FIXME: Why don't you check earlier?
        # FIXME: Check for 1D array, 2D
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            self.log.error('Given parameter is not an array.')
            amplitude = 0.
            center_x = 0.
            center_y = 0.
            sigma_x = 0.
            sigma_y = 0.
            theta = 0.0
            offset = 0.
            error = -1

    # auxiliary variables:
    stepsize_x = x_axis[1]-x_axis[0]
    stepsize_y = y_axis[1]-y_axis[0]
    n_steps_x = len(x_axis)
    n_steps_y = len(y_axis)

    # populate the parameter container:
    params['amplitude'].set(value=amplitude, min=100, max=1e7)
    params['sigma_x'].set(value=sigma_x, min=1*stepsize_x,
                          max=3*(x_axis[-1]-x_axis[0]))
    params['sigma_y'].set(value=sigma_y, min=1*stepsize_y,
                          max=3*(y_axis[-1]-y_axis[0]))
    params['center_x'].set(value=center_x, min=(x_axis[0])-n_steps_x*stepsize_x,
                           max=x_axis[-1]+n_steps_x*stepsize_x)
    params['center_y'].set(value=center_y, min=(y_axis[0])-n_steps_y*stepsize_y,
                           max=y_axis[-1]+n_steps_y*stepsize_y)
    params['theta'].set(value=theta, min=0, max=np.pi)
    params['offset'].set(value=offset, min=0, max=1e7)

    return error, params
