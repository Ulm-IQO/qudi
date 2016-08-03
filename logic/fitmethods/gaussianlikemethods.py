# -*- coding: utf-8 -*-

"""
This file contains methods for gaussian-like fitting, these methods
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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


import logging
logger = logging.getLogger(__name__)
import numpy as np
from lmfit.models import Model, GaussianModel, ConstantModel
from lmfit import Parameters

from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.signal import gaussian
from scipy.ndimage import filters

############################################################################
#                                                                          #
#                          1D gaussian model                               #
#                                                                          #
############################################################################

def make_gaussian_model(self):
    """ This method creates a model of a gaussian with an offset.

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
                'amplitude' : amplitude
                'center'    : center
                'sigm'      : sigma
                'fwhm'      : full width half maximum
                'c'         : offset

    For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """

    model = GaussianModel() + ConstantModel()
    params = model.make_params()

    return model, params

def make_gaussian_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a 1D gaussian fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters which will substitute the
                                estimated parameters/bounds

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    mod_final, params = self.make_gaussian_model()

    error, params = self.estimate_gaussian(axis, data, params)

    # auxiliary variables
    stepsize = abs(axis[1] - axis[0])
    n_steps = len(axis)

    # Define constraints
    params['center'].min = (axis[0]) - n_steps * stepsize
    params['center'].max = (axis[-1]) + n_steps * stepsize
    params['amplitude'].min = 100  # that is already noise from APD
    params['amplitude'].max = data.max() * params['sigma'].value * np.sqrt(2 * np.pi)
    params['sigma'].min = stepsize
    params['sigma'].max = 3 * (axis[-1] - axis[0])
    params['c'].min = 100  # that is already noise from APD
    params['c'].max = data.max() * params['sigma'].value * np.sqrt(2 * np.pi)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = mod_final.fit(data, x=axis, params=params)
    except:
        logger.warning('The 1D gaussian fit did not work.')
        result = mod_final.fit(data, x=axis, params=params)
        print(result.message)

    return result

def estimate_gaussian(self, x_axis=None, data=None, params=None):
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
            logger.error('Given parameter is no array.')
            error = -1
        elif len(np.shape(var)) != 1:
            logger.error('Given parameter is no one dimensional array.')
            error = -1
    if not isinstance(params, Parameters):
        logger.error('Parameters object is not valid in estimate_gaussian.')
        error = -1

    # If the estimator is not good enough one can start improvement with
    # a convolution

    # set parameters
    params['center'].value = x_axis[np.argmax(data)]
    params['sigma'].value = (x_axis.max() - x_axis.min()) / 3.
    params['amplitude'].value = (data.max() - data.min()) * (params['sigma'].value * np.sqrt(2 * np.pi))
    params['c'].value = data.min()

    return error, params

############################################################################
#                                                                          #
#                            2D gaussian model                             #
#                                                                          #
############################################################################
1

def make_twoDgaussian_fit(self, axis=None, data=None,
                           add_parameters=None):
    """ This method performes a 2D gaussian fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    x_axis, y_axis = axis

    error,      \
    amplitude,  \
    x_zero,     \
    y_zero,     \
    sigma_x,    \
    sigma_y,    \
    theta,      \
    offset = self.estimate_twoDgaussian(x_axis=x_axis,
                                          y_axis=y_axis, data=data)
    mod, params = self.make_twoDgaussian_model()

    #auxiliary variables
    stepsize_x=x_axis[1]-x_axis[0]
    stepsize_y=y_axis[1]-y_axis[0]
    n_steps_x=len(x_axis)
    n_steps_y=len(y_axis)

    #When I was sitting in the train coding and my girlfiend was sitting next to me she said: "Look it looks like an animal!" - is it a fox or a rabbit???

    #Defining standard parameters
    #                  (Name,       Value,      Vary,           Min,                             Max,                       Expr)
    params.add_many(('amplitude',   amplitude,  True,        100,                               1e7,                           None),
                   (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(x_axis[-1]-x_axis[0]),          None),
                   (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(y_axis[-1]-y_axis[0]) ,   None),
                   (  'x_zero',    x_zero,      True,     (x_axis[0])-n_steps_x*stepsize_x ,         x_axis[-1]+n_steps_x*stepsize_x,               None),
                   (  'y_zero',     y_zero,     True,    (y_axis[0])-n_steps_y*stepsize_y ,         (y_axis[-1])+n_steps_y*stepsize_y,         None),
                   (  'theta',       0.,        True,           0. ,                             np.pi,               None),
                   (  'offset',      offset,    True,           0,                              1e7,                       None))


#           redefine values of additional parameters
    if add_parameters is not None:
        params=self._substitute_parameter(parameters=params,
                                         update_dict=add_parameters)

    try:
        result=mod.fit(data, x=axis,params=params)
    except:
        result=mod.fit(data, x=axis,params=params)
        logger.warning('The 2D gaussian fit did not work: {0}'.format(
            result.message))

    return result


def make_twoDgaussian_model(self):
    """ This method creates a model of the 2D gaussian function.

    The parameters are: 'amplitude', 'center', 'sigm, 'fwhm' and offset
    'c'. For function see:

    @return lmfit.model.CompositeModel model: Returns an object of the
                                              class CompositeModel
    @return lmfit.parameter.Parameters params: Returns an object of the
                                               class Parameters with all
                                               parameters for the
                                               gaussian model.

    """

    def twoDgaussian_function(x, amplitude, x_zero, y_zero, sigma_x, sigma_y,
                              theta, offset):
        # FIXME: x_data_tuple: dimension of arrays

        """ This method provides a two dimensional gaussian function.

        Function taken from:
        http://stackoverflow.com/questions/21566379/fitting-a-2d-gaussian-function-using-scipy-optimize-curve-fit-valueerror-and-m/21566831

        Question from: http://stackoverflow.com/users/2097737/bland & http://stackoverflow.com/users/3273102/kokomoking
                       & http://stackoverflow.com/users/2767207/jojodmo
        Answer: http://stackoverflow.com/users/1461210/ali-m & http://stackoverflow.com/users/5234/mrjrdnthms

        @param array[k][M] x_data_tuple: array which is (k,M)-shaped, x and y
                                         values
        @param float or int amplitude: Amplitude of gaussian
        @param float or int x_zero: x value of maximum
        @param float or int y_zero: y value of maximum
        @param float or int sigma_x: standard deviation in x direction
        @param float or int sigma_y: standard deviation in y direction
        @param float or int theta: angle for eliptical gaussians
        @param float or int offset: offset

        @return callable function: returns the function
        """

        (u, v) = x
        x_zero = float(x_zero)
        y_zero = float(y_zero)

        a = (np.cos(theta) ** 2) / (2 * sigma_x ** 2) \
            + (np.sin(theta) ** 2) / (2 * sigma_y ** 2)
        b = -(np.sin(2 * theta)) / (4 * sigma_x ** 2) \
            + (np.sin(2 * theta)) / (4 * sigma_y ** 2)
        c = (np.sin(theta) ** 2) / (2 * sigma_x ** 2) \
            + (np.cos(theta) ** 2) / (2 * sigma_y ** 2)
        g = offset + amplitude * np.exp(- (a * ((u - x_zero) ** 2) \
                                           + 2 * b * (u - x_zero) * (v - y_zero) \
                                           + c * ((v - y_zero) ** 2)))
        return g.ravel()

    model = Model(twoDgaussian_function)
    params = model.make_params()

    return model, params


def estimate_twoDgaussian(self, x_axis=None, y_axis=None, data=None):
    # TODO:Make clever estimator
    # FIXME: 1D array x_axis, y_axis, 2D data???
    """ This method provides a two dimensional gaussian function.

    @param array x_axis: x values
    @param array y_axis: y values
    @param array data: value of each data point corresponding to
                        x and y values

    @return float amplitude: estimated amplitude
    @return float x_zero: estimated x value of maximum
    @return float y_zero: estimated y value of maximum
    @return float sigma_x: estimated standard deviation in x direction
    @return float sigma_y: estimated  standard deviation in y direction
    @return float theta: estimated angle for eliptical gaussians
    @return float offset: estimated offset
    @return int error: error code (0:OK, -1:error)
    """

    #            #needed me 1 hour to think about, but not needed in the end...maybe needed at a later point
    #            len_x=np.where(x_axis[0]==x_axis)[0][1]
    #            len_y=len(data)/len_x


    amplitude = float(data.max() - data.min())

    x_zero = x_axis[data.argmax()]
    y_zero = y_axis[data.argmax()]

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
            logger.error('Given parameter is not an array.')
            amplitude = 0.
            x_zero = 0.
            y_zero = 0.
            sigma_x = 0.
            sigma_y = 0.
            theta = 0.0
            offset = 0.
            error = -1

    return error, amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset


############################################################################
#                                                                          #
#                          Double Gaussian Model                           #
#                                                                          #
############################################################################

def make_multiplegaussian_model(self, no_of_gauss=None):
    """ This method creates a model of multiple gaussians with an offset. The
    parameters are: 'amplitude', 'center', 'sigma', 'fwhm' and offset
    'c'. For function see:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel

    @return lmfit.model.CompositeModel model: Returns an object of the
                                              class CompositeModel
    @return lmfit.parameter.Parameters params: Returns an object of the
                                               class Parameters with all
                                               parameters for the
                                               lorentzian model.
    """

    model = ConstantModel()
    for ii in range(no_of_gauss):
        model += GaussianModel(prefix='gaussian{}_'.format(ii))

    params = model.make_params()

    return model, params


def estimate_doublegaussian_gatedcounter(self, x_axis=None, data=None, params=None,
                                         threshold_fraction=0.4,
                                         minimal_threshold=0.1,
                                         sigma_threshold_fraction=0.2):
    """ This method provides a an estimator for a double gaussian fit with the parameters
    coming from the physical properties of an experiment done in gated counter:
                    - positive peak
                    - no values below 0
                    - rather broad overlapping funcitons

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values
    @param Parameters object params: Needed parameters
    @param float threshold : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowerd to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return int error: error code (0:OK, -1:error)
    @return Parameters object params: estimated values
    """

    error = 0

    data_smooth = self.gaussian_smoothing(data=data)

    # search for double gaussian

    error, \
    sigma0_argleft, dip0_arg, sigma0_argright, \
    sigma1_argleft, dip1_arg, sigma1_argright = \
        self._search_double_dip(x_axis,
                                data_smooth * (-1),
                                threshold_fraction,
                                minimal_threshold,
                                sigma_threshold_fraction,
                                make_prints=False
                                )

    # set offset to zero
    params['c'].value = 0.0

    params['gaussian0_center'].value = x_axis[dip0_arg]

    # integral of data corresponds to sqrt(2) * Amplitude * Sigma
    function = InterpolatedUnivariateSpline(x_axis, data_smooth, k=1)
    Integral = function.integral(x_axis[0], x_axis[-1])

    amp_0 = data_smooth[dip0_arg] - params['c'].value
    amp_1 = data_smooth[dip1_arg] - params['c'].value

    params['gaussian0_sigma'].value = Integral / (amp_0 + amp_1) / np.sqrt(2 * np.pi)
    params['gaussian0_amplitude'].value = amp_0 * params['gaussian0_sigma'].value * np.sqrt(2 * np.pi)

    params['gaussian1_center'].value = x_axis[dip1_arg]
    params['gaussian1_sigma'].value = Integral / (amp_0 + amp_1) / np.sqrt(2 * np.pi)
    params['gaussian1_amplitude'].value = amp_1 * params['gaussian1_sigma'].value * np.sqrt(2 * np.pi)

    return error, params


def estimate_doublegaussian_odmr(self, x_axis=None, data=None, params=None,
                                 threshold_fraction=0.4,
                                 minimal_threshold=0.1,
                                 sigma_threshold_fraction=0.2):
    """ This method provides a an estimator for a double gaussian fit with the parameters
    coming from the physical properties of an experiment done in gated counter:
                    - positive peak
                    - no values below 0
                    - rather broad overlapping funcitons

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values
    @param Parameters object params: Needed parameters
    @param float threshold : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowerd to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return int error: error code (0:OK, -1:error)
    @return Parameters object params: estimated values
    """

    error, \
    params['gaussian0_amplitude'].value, \
    params['gaussian1_amplitude'].value, \
    params['gaussian0_center'].value, \
    params['gaussian1_center'].value, \
    params['gaussian0_sigma'].value, \
    params['gaussian1_sigma'].value, \
    params['c'].value = self.estimate_doublelorentz(x_axis, data)

    return error, params


def make_doublegaussian_fit(self, axis=None, data=None,
                            add_parameters=None,
                            estimator='gated_counter',
                            threshold_fraction=0.4,
                            minimal_threshold=0.2,
                            sigma_threshold_fraction=0.3):
    """ This method performes a 1D double gaussian fit on the provided data.

    @param array [] axis: axis values
    @param array[]  data: data
    @param dictionary add_parameters: Additional parameters
    @param float threshold_fraction : Threshold to find second gaussian
    @param float minimal_threshold: Threshold is lowerd to minimal this
                                    value as a fraction
    @param float sigma_threshold_fraction: Threshold for detecting
                                           the end of the peak

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...

    """

    model, params = self.make_multiplegaussian_model(no_of_gauss=2)

    if estimator == 'gated_counter':
        error, params = self.estimate_doublegaussian_gatedcounter(axis, data, params,
                                                                  threshold_fraction,
                                                                  minimal_threshold,
                                                                  sigma_threshold_fraction)
        # Defining constraints
        params['c'].min = 0.0

        params['gaussian0_amplitude'].min = 0.0
        params['gaussian1_amplitude'].min = 0.0

    elif estimator == 'odmr_dip':
        error, params = self.estimate_doublegaussian_odmr(axis, data, params,
                                                          threshold_fraction,
                                                          minimal_threshold,
                                                          sigma_threshold_fraction)

    # redefine values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = model.fit(data, x=axis, params=params)
    except:
        result = model.fit(data, x=axis, params=params)
        logger.warning('The double gaussian fit did not work: {0}'.format(
            result.message))

    return result
