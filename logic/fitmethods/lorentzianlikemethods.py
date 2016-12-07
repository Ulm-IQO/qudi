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


import logging
logger = logging.getLogger(__name__)
import numpy as np
from lmfit.models import ConstantModel, LorentzianModel, VoigtModel, PseudoVoigtModel
from lmfit import Parameters

from scipy.ndimage import filters
from scipy.interpolate import InterpolatedUnivariateSpline


################################################################################
#                                                                              #
#                               Lorentzian Model                               #
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

This notation we will call as the physical definition of the Lorentzian, with
I as the height of the Lorentzian, x_0 is its location and sigma as the half
width at half maximum.

Note that the fitting algorithm is using now the equation L(x; I, x_0, sigma)
and not f(x; A, x_0, sigma), therefore all the parameters are defined according
to L(x; I, x_0, sigma). The full width at half maximum is therefore 2*sigma.

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


def make_lorentzian_model(self):
    """ This method creates a model of lorentzian with an offset. The
    parameters are: 'amplitude', 'center', 'sigma, 'fwhm' and offset
    'c'. For function see:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel

    @return lmfit.model.CompositeModel model: Returns an object of the
                                              class CompositeModel
    @return object params: lmfit.parameter.Parameters object, returns an
                           object of the class Parameters with all
                           parameters for the lorentzian model.
    """

    model = LorentzianModel()+ConstantModel()
    params = model.make_params()

    return model, params

def estimate_lorentz(self, x_axis=None,data=None):
    """ This method provides a lorentzian function.

    @param numpy.array x_axis: x values
    @param numpy.array data: value of each data point corresponding to
                        x values

    @return int error: error code (0:OK, -1:error)
    @return float amplitude: estimated amplitude
    @return float x_zero: estimated x value of maximum
    @return float sigma_x: estimated standard deviation in x direction
    @return float offset: estimated offset
    """
#           TODO: make sigma and amplitude good, this is only a dirty fast solution
    error = 0
    # check if parameters make sense
    parameters=[x_axis,data]
    for var in parameters:
        if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
            logger.error('Given parameter is no array.')
            error=-1
        elif len(np.shape(var))!=1:
            logger.error('Given parameter is no one dimensional array.')
    #set parameters

    data_smooth, offset = self.find_offset_parameter(x_axis, data)

    # data_level = data-offset
    data_level = data - data_smooth.mean()
    data_min = data_level.min()
    data_max = data_level.max()

    # estimate sigma
    # numerical_integral = (np.sum(data_level) *
    #                       (abs(x_axis[-1] - x_axis[0])) / len(x_axis))


    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    function = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
    numerical_integral = function.integral(x_axis[0], x_axis[-1])

    if data_max > abs(data_min):
        logger.warning('The lorentzian estimator set the peak to the '
                'minimal value, if you want to fit a peak instead '
                'of a dip rewrite the estimator.')

    amplitude_median = data_min
    x_zero = x_axis[np.argmin(data_smooth)]

    # For the fitting procedure it is much better to start with a larger sigma
    # then with a smaller one. A small sigma is prone to larger instabilities
    # in the fit.
    oversize_sigma = 8

    sigma = numerical_integral*oversize_sigma / (np.pi * amplitude_median)
    amplitude = amplitude_median * np.pi * sigma

    amplitude = -1 *abs(amplitude_median * np.pi * sigma)

    return error, amplitude, x_zero, sigma, offset

def make_lorentzian_fit(self, x_axis, data, add_params=None):
    """ This method performes a 1D lorentzian fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...
    """

    error, amplitude, x_zero, sigma, offset = self.estimate_lorentz(x_axis, data)

    model, params = self.make_lorentzian_model()

    # auxiliary variables
    stepsize = x_axis[1]-x_axis[0]
    n_steps = len(x_axis)

    # TODO: Make sigma amplitude and x_zero better
    # Defining standard parameters

    if x_axis[1]-x_axis[0]>0:
        #                (Name,       Value,    Vary,  Min,                        Max,                         Expr)
        params.add_many(('amplitude', amplitude, True, None,                       -1e-12,                      None),
                        ('sigma',     sigma,     True, (x_axis[1]-x_axis[0])/2 ,       (x_axis[-1]-x_axis[0])*10,       None),
                        ('center',    x_zero,    True, (x_axis[0])-n_steps*stepsize, (x_axis[-1])+n_steps*stepsize, None),
                        ('c',         offset,    True, None,                       None,                        None))


    if x_axis[0]-x_axis[1]>0:

    #                   (Name,        Value,  Vary,    Min,                 Max,                  Expr)
        params.add_many(('amplitude', amplitude, True, None,                -1e-12,               None),
                        ('sigma',     sigma,     True, (x_axis[0]-x_axis[1])/2, (x_axis[0]-x_axis[1])*10, None),
                        ('center',    x_zero,    True, (x_axis[-1]),          (x_axis[0]),            None),
                        ('c',         offset,    True, None,                None,                 None))


    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = model.fit(data, x=x_axis, params=params)
    except:
        result = model.fit(data, x=x_axis, params=params)
        logger.warning('The 1D lorentzian fit did not work. Error '
                'message: {0}\n'.format(result.message))
    return result

################################################################################
#                                                                              #
#                        Lorentzian Model with offset                          #
#                                                                              #
################################################################################



################################################################################
#                                                                              #
#                   Multiple Lorentzian Model with offset                      #
#                                                                              #
################################################################################




############################################################################
#                                                                          #
#                   Lorentz fit for peak instead of dip                    #
#                                                                          #
############################################################################


def estimate_lorentzpeak (self, x_axis=None, data=None):
    """ This method provides a lorentzian function to fit a peak.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values


    @return int error: error code (0:OK, -1:error)
    @return float amplitude: estimated amplitude
    @return float x_zero: estimated x value of maximum
    @return float sigma_x: estimated standard deviation in x direction
    @return float offset: estimated offset
    """

    #TODO: make sigma and amplitude good, this is only a dirty fast solution
    error = 0
    # check if parameters make sense

    parameters = [x_axis, data]
    for var in parameters:
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            logger.error('Given parameter is no array.')
            error = -1
        elif len(np.shape(var)) != 1:
            logger.error('Given parameter is no one dimensional array.')
    #set paraameters

    data_smooth, offset = self.find_offset_parameter(x_axis, data)
    data_level = data-offset
    data_min = data_level.min()
    data_max = data_level.max()


    numerical_integral = np.sum(data_level) * \
                        (np.abs(x_axis[0] - x_axis[-1])) / len(x_axis)



    if data_max<abs(data_min):
        logger.warning('This lorentzian estimator set the peak to the '
                'maximum value, if you want to fit a dip '
                'instead of a peak use estimate_lorentz.')

    amplitude_median = data_max
    x_zero = x_axis[np.argmax(data)]
    sigma = np.abs(numerical_integral / (np.pi * amplitude_median))
    amplitude = amplitude_median * np.pi * sigma


    return error, amplitude, x_zero, sigma, offset

def make_lorentzianpeak_fit(self, x_axis, data, add_params=None):
    """ Perform a 1D Lorentzian peak fit on the provided data.

    @param array [] axis: axis values
    @param array[]  x_data: data
    @param dictionary add_parameters: Additional parameters

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...
    """

    error,      \
    amplitude,  \
    x_zero,     \
    sigma,      \
    offset      = self.estimate_lorentzpeak(x_axis, data)


    model, params = self.make_lorentzian_model()

    # auxiliary variables:
    stepsize=np.abs(x_axis[1]-x_axis[0])
    n_steps=len(x_axis)

#            TODO: Make sigma amplitude and x_zero better

    #Defining standard parameters

    if x_axis[1]-x_axis[0]>0:

    #                   (Name,        Value,     Vary, Min,                        Max,                         Expr)
        params.add_many(('amplitude', amplitude, True, 2e-12,                      None,                        None),
                        ('sigma',     sigma,     True, (x_axis[1]-x_axis[0])/2,        (x_axis[-1]-x_axis[0])*10,       None),
                        ('center',    x_zero,    True, (x_axis[0])-n_steps*stepsize, (x_axis[-1])+n_steps*stepsize, None),
                        ('c',         offset,    True, None,                       None,                        None))
    if x_axis[0]-x_axis[1]>0:

    #                   (Name,        Value,     Vary, Min,                  Max,                  Expr)
        params.add_many(('amplitude', amplitude, True, 2e-12,                None,                 None),
                        ('sigma',     sigma,     True, (x_axis[0]-x_axis[1])/2 , (x_axis[0]-x_axis[1])*10, None),
                        ('center',    x_zero,    True, (x_axis[-1]),           (x_axis[0]),            None),
                        ('c',         offset,    True, None,                 None,                 None))

    #redefine values of additional parameters

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result=model.fit(data, x=x_axis, params=params)
    except:
        result=model.fit(data, x=x_axis, params=params)
        logger.warning('The 1D gaussian fit did not work. Error '
                'message:' + result.message)

    return result


############################################################################
#                                                                          #
#                          Double Lorentzian Model                         #
#                                                                          #
############################################################################

def make_multiplelorentzian_model(self, no_of_lor=None):
    """ This method creates a model of lorentzian with an offset. The
    parameters are: 'amplitude', 'center', 'sigm, 'fwhm' and offset
    'c'. For function see:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel

    @return lmfit.model.CompositeModel model: Returns an object of the
                                              class CompositeModel
    @return lmfit.parameter.Parameters params: Returns an object of the
                                               class Parameters with all
                                               parameters for the
                                               lorentzian model.
    """

    model=ConstantModel()
    for ii in range(no_of_lor):
        model += LorentzianModel(prefix='lorentz{0}_'.format(ii))

    params = model.make_params()

    return model, params




def estimate_doublelorentz(self, x_axis=None, data=None,
                            threshold_fraction=0.3,
                            minimal_threshold=0.01,
                            sigma_threshold_fraction=0.3):
    """ This method provides a lorentzian function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values

    @return int error: error code (0:OK, -1:error)
    @return float lorentz0_amplitude: estimated amplitude of 1st peak
    @return float lorentz1_amplitude: estimated amplitude of 2nd peak
    @return float lorentz0_center: estimated x value of 1st maximum
    @return float lorentz1_center: estimated x value of 2nd maximum
    @return float lorentz0_sigma: estimated sigma of 1st peak
    @return float lorentz1_sigma: estimated sigma of 2nd peak
    @return float offset: estimated offset
    """
    error = 0
    # check if parameters make sense
    parameters = [x_axis,data]
    for var in parameters:
        if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
            logger.error('Given parameter is no array.')
            error=-1
        elif len(np.shape(var)) != 1:
            logger.error('Given parameter is no one dimensional array.')


    #set paraameters
    data_smooth,offset=self.find_offset_parameter(x_axis,data)

    data_level=data_smooth-offset

    #search for double lorentzian

    error, \
    sigma0_argleft, dip0_arg, sigma0_argright, \
    sigma1_argleft, dip1_arg , sigma1_argright = \
    self._search_double_dip(x_axis, data_level, threshold_fraction,
                           minimal_threshold, sigma_threshold_fraction)



    if dip0_arg == dip1_arg:
        lorentz0_amplitude = data_level[dip0_arg]/2.
        lorentz1_amplitude = lorentz0_amplitude
    else:
        lorentz0_amplitude=data_level[dip0_arg]
        lorentz1_amplitude=data_level[dip1_arg]

    lorentz0_center = x_axis[dip0_arg]
    lorentz1_center = x_axis[dip1_arg]

    #Both sigmas are set to the same value
    numerical_integral_0=(np.sum(data_level[sigma0_argleft:sigma0_argright]) *
                       (x_axis[sigma0_argright] - x_axis[sigma0_argleft]) /
                        len(data_level[sigma0_argleft:sigma0_argright]))

    lorentz0_sigma = abs(numerical_integral_0 /
                         (np.pi * lorentz0_amplitude) )

    numerical_integral_1=numerical_integral_0

    lorentz1_sigma = abs( numerical_integral_1
                          / (np.pi * lorentz1_amplitude)  )

    #esstimate amplitude
    lorentz0_amplitude = -1*abs(lorentz0_amplitude*np.pi*lorentz0_sigma)
    lorentz1_amplitude = -1*abs(lorentz1_amplitude*np.pi*lorentz1_sigma)


    if lorentz1_center < lorentz0_center :
        lorentz0_amplitude_temp = lorentz0_amplitude
        lorentz0_amplitude = lorentz1_amplitude
        lorentz1_amplitude = lorentz0_amplitude_temp
        lorentz0_center_temp    = lorentz0_center
        lorentz0_center    = lorentz1_center
        lorentz1_center    = lorentz0_center_temp
        lorentz0_sigma_temp= lorentz0_sigma
        lorentz0_sigma     = lorentz1_sigma
        lorentz1_sigma     = lorentz0_sigma_temp


    return error, lorentz0_amplitude,lorentz1_amplitude, \
           lorentz0_center,lorentz1_center, lorentz0_sigma, \
           lorentz1_sigma, offset

def make_doublelorentzian_fit(self, x_axis, data, add_params=None):
    """ This method performes a 1D lorentzian fit on the provided data.

    @param array [] axis: axis values
    @param array[]  x_data: data
    @param dictionary add_parameters: Additional parameters

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...

    """

    error,              \
    lorentz0_amplitude, \
    lorentz1_amplitude, \
    lorentz0_center,    \
    lorentz1_center,    \
    lorentz0_sigma,     \
    lorentz1_sigma,     \
    offset              = self.estimate_doublelorentz(x_axis, data)

    model, params = self.make_multiplelorentzian_model(no_of_lor=2)

    # Auxiliary variables:
    stepsize=x_axis[1]-x_axis[0]
    n_steps=len(x_axis)

    #Defining standard parameters
    #            (Name,                  Value,          Vary, Min,                        Max,                         Expr)
    params.add('lorentz0_amplitude', lorentz0_amplitude, True, None,                       -0.01,                       None)
    params.add('lorentz0_sigma',     lorentz0_sigma,     True, (x_axis[1]-x_axis[0])/2 ,       (x_axis[-1]-x_axis[0])*4,        None)
    params.add('lorentz0_center',    lorentz0_center,    True, (x_axis[0])-n_steps*stepsize, (x_axis[-1])+n_steps*stepsize, None)
    params.add('lorentz1_amplitude', lorentz1_amplitude, True, None,                       -0.01,                       None)
    params.add('lorentz1_sigma',     lorentz1_sigma,     True, (x_axis[1]-x_axis[0])/2 ,       (x_axis[-1]-x_axis[0])*4,        None)
    params.add('lorentz1_center',    lorentz1_center,    True, (x_axis[0])-n_steps*stepsize, (x_axis[-1])+n_steps*stepsize, None)
    params.add('c',                  offset,             True, None,                       None,                        None)

    #redefine values of additional parameters
    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result=model.fit(data, x=x_axis, params=params)
    except:
        result=model.fit(data, x=x_axis, params=params)
        logger.warning('The double lorentzian fit did not '
                'work: {0}'.format(result.message))

    return result

############################################################################
#                                                                          #
#                                N14 fitting                               #
#                                                                          #
############################################################################

def estimate_N14(self, x_axis=None, data=None):
    """ Provide an estimation of all fitting parameters for fitting the
    three equdistant lorentzian dips of the hyperfine interaction
    of a N14 nuclear spin. Here the splitting is set as an expression,
    if the splitting is not exactly 2.15MHz the fit will not work.

    @param array x_axis: x values in Hz
    @param array data: value of each data point corresponding to
                        x values

    @return lmfit.parameter.Parameters parameters: New object corresponding
                                                   parameters like offset,
                                                   the three sigma's, the
                                                   three amplitudes and centers

    """

    # find the offset parameter, which should be in the fit the zero level:
    data_smooth_lorentz, offset = self.find_offset_parameter(x_axis, data)

    # Create now a filter of length 5MHz, then create a step-wise function with
    # three dips. This step-wise function will be convolved with the smoothed
    # data, where the maximal contribution will be if the peaks are within the
    # filter. Take that to obtain from that the accurate peak position:

    #filter of one dip should always have a length of approx linewidth 1MHz
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
        data_convolved = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(), mode='constant', cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()]-2.15*1e6
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]-2.15*1e6

    # Create the parameter container, with the estimated values, which should be
    # passed to the fit algorithm:
    parameters = Parameters()

    # level of the data, that means the offset is subtracted and the real data
    # are present
    data_level = data_smooth_lorentz - data_smooth_lorentz.mean()
    minimum_level = data_level.min()

    # In order to perform a smooth integral to obtain the area under the curve
    # make an interpolation of the passed data, in case they are very sparse.
    # That increases the accuracy of the calculated Integral.
    # integral of data corresponds to sqrt(2) * Amplitude * Sigma

    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    function = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
    integrated_area = function.integral(x_axis[0], x_axis[-1])

    sigma = abs(integrated_area / (minimum_level/np.pi))
    # That is wrong, so commenting out:
    # sigma = abs(integrated_area /(np.pi * minimum_level) )

    amplitude = -1*abs(minimum_level*np.pi*sigma)

    # Since the total amplitude of the lorentzian is depending on sigma it makes
    # sense to vary sigma within an interval, which is smaller than the minimal
    # distance between two points. Then the fit algorithm will have a larger
    # range to determine the amplitude properly. That is the main issue with the
    # fit!
    linewidth = sigma
    minimal_linewidth = (x_axis[1]-x_axis[0])/4
    maximal_linewidth = x_axis[-1]-x_axis[0]

    # The linewidth of all the lorentzians are set to be the same! that is a
    # physical constraint for the N14 fitting.

    #            (Name,                  Value,          Vary, Min,             Max,           Expr)
    parameters.add('lorentz0_amplitude', value=amplitude,                                                  max=-1e-6)
    parameters.add('lorentz0_center',    value=x_axis_min)
    parameters.add('lorentz0_sigma',     value=linewidth,                           min=minimal_linewidth, max=maximal_linewidth)
    parameters.add('lorentz1_amplitude', value=parameters['lorentz0_amplitude'].value,                     max=-1e-6)
    parameters.add('lorentz1_center',    value=parameters['lorentz0_center'].value+2.15*1e6,                                      expr='lorentz0_center+2.15*1e6')
    parameters.add('lorentz1_sigma',     value=parameters['lorentz0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
    parameters.add('lorentz2_amplitude', value=parameters['lorentz0_amplitude'].value,                     max=-1e-6)
    parameters.add('lorentz2_center',    value=parameters['lorentz1_center'].value+2.15*1e6,                                      expr='lorentz0_center+4.3*1e6')
    parameters.add('lorentz2_sigma',     value=parameters['lorentz0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
    parameters.add('c',                  value=data_smooth_lorentz.max())

    return parameters


def make_N14_fit(self, x_axis, data, add_params=None):
    """ This method performs a fit on the provided data where a N14
    hyperfine interaction of 2.15 MHz is taken into account.

    @param array [] axis: axis values
    @param array[]  data: data
    @param dictionary add_parameters: Additional parameters

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...

    """

    parameters = self.estimate_N14(x_axis, data)

    parameters = self._substitute_params(initial_params=parameters,
                                        update_params=add_params)

    mod, params = self.make_multiplelorentzian_model(no_of_lor=3)

    result = mod.fit(data=data, x=x_axis, params=parameters)

    return result

############################################################################
#                                                                          #
#                               N15 fitting                                #
#                                                                          #
############################################################################

def estimate_N15(self, x_axis=None, data=None):
    """ This method provides an estimation of all fitting parameters for
    fitting the three equdistant lorentzian dips of the hyperfine interaction
    of a N15 nuclear spin. Here the splitting is set as an expression, if the
    splitting is not exactly 3.03MHz the fit will not work.

    @param array x_axis: x values in Hz
    @param array data: value of each data point corresponding to
                        x values

    @return lmfit.parameter.Parameters parameters: New object corresponding
                                                   parameters like offset,
                                                   the three sigma's, the
                                                   three amplitudes and centers

    """

    data_smooth_lorentz, offset = self.find_offset_parameter(x_axis, data)

    hf_splitting = 3.03 * 1e6 # Hz
    #filter should always have a length of approx linewidth 1MHz
    points_within_1MHz = len(x_axis)/(x_axis.max()-x_axis.min()) * 1e6
    # filter should have a width of 4 MHz
    x_filter = np.linspace(0,4*points_within_1MHz,4*points_within_1MHz)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/4),
                                    (x_filter >= len(x_filter)/4)*(x_filter<len(x_filter)*3/4),
                                    (x_filter >= len(x_filter)*3/4)], [1, 0,1])

    # if the filter is smaller than 5 points a convolution does not make sense
    if len(lorentz) >= 3:
        data_convolved = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(),
                                     mode='constant', cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()]-hf_splitting/2.
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]

    data_level = data_smooth_lorentz - data_smooth_lorentz.max()
    minimum_level = data_level.min()
    # integral of data:
    function = InterpolatedUnivariateSpline(x_axis, data_level, k=1)
    Integral = function.integral(x_axis[0], x_axis[-1])

    sigma = abs(Integral /(np.pi * minimum_level) )

    amplitude = -1*abs(minimum_level*np.pi*sigma)

    minimal_sigma = x_axis[1]-x_axis[0]
    maximal_sigma = x_axis[-1]-x_axis[0]


    parameters = Parameters()

    parameters.add('lorentz0_amplitude', value=amplitude/2.,                                             max=-1e-6)
    parameters.add('lorentz0_center',    value=x_axis_min)
    parameters.add('lorentz0_sigma',     value=sigma/2.,                              min=minimal_sigma, max=maximal_sigma)
    parameters.add('lorentz1_amplitude', value=parameters['lorentz0_amplitude'].value,                   max=-1e-6)
    parameters.add('lorentz1_center',    value=parameters['lorentz0_center'].value+hf_splitting,                             expr='lorentz0_center+3.03*1e6')
    parameters.add('lorentz1_sigma',     value=parameters['lorentz0_sigma'].value,    min=minimal_sigma, max=maximal_sigma,  expr='lorentz0_sigma')
    parameters.add('c',                  value=data_smooth_lorentz.max())

    return parameters


def make_N15_fit(self, x_axis, data, add_params=None):
    """ This method performes a fit on the provided data where a N14
    hyperfine interaction of 3.03 MHz is taken into accound.

    @param array [] axis: axis values in Hz
    @param array[]  data: data
    @param dictionary add_parameters: Additional parameters

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...

    """

    parameters = self.estimate_N15(x_axis, data)

    # redefine values of additional parameters
    parameters = self._substitute_params(initial_params=parameters,
                                         update_params=add_params)

    mod, params = self.make_multiplelorentzian_model(no_of_lor=2)

    result = mod.fit(data=data, x=x_axis, params=parameters)

    return result
