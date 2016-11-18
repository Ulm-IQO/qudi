# -*- coding: utf-8 -*-
"""
This file contains methods for sine fitting, these methods
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
from core.util.units import compute_dft


################################################################################
#                                                                              #
#                               Bare Sinus fitting                             #
#                                                                              #
################################################################################

def make_baresine_model(self, prefix=None):
    """ Create a bare sine model without amplitude and offset.

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
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """

    def bare_sine_function(x, frequency, phase):
        """ Function of a bare sine.

        @param numpy.array x: independant variable - e.g. time
        @param float frequency: frequency
        @param float phase: phase

        @return: reference to method of a sine function in order to use it as a
                 model
        """

        return np.sin(2*np.pi*frequency*x+phase)

    model = Model(bare_sine_function, independent_vars='x', prefix=prefix)
    params = model.make_params()

    return model, params

def estimate_baresine(self, x_axis, data, params):
    """ Bare sine estimator with a frequency and phase.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        lmfit.Parameters params: derived OrderedDict object contains the initial
                                 values for the fit.
    """

    # Convert for safety:
    x_axis = np.array(x_axis)
    data = np.array(data)

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # calculate dft with zeropadding to obtain nicer interpolation between the
    # appearing peaks.
    dft_x, dft_y = compute_dft(x_axis, data, zeropad_num=1)

    stepsize = x_axis[1]-x_axis[0]  # for frequency axis
    frequency_max = np.abs(dft_x[np.log(dft_y).argmax()])

    # find minimal distance to the next meas point in the corresponding time value>
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data - func_val).sum()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = sum_res.argmax()/iter_steps *2*np.pi - np.pi

    params['frequency'].set(value=frequency_max, min=0.0, max=1/(stepsize)*3)
    params['phase'].set(value=phase, min=-np.pi, max=np.pi)

    return error, params


def make_baresine_fit(self, x_axis, data, add_parameters=None):
    """ Perform a bare sine fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param dict add_parameters: optional, additional parameters for the fit,
                                which will be used instead of the values from
                                the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    baresine, params = self.make_sine_model()
    error, params = self.estimate_baresine(x_axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = baresine.fit(data, x=x_axis, params=params)
    except:
        logger.warning('The sine fit did not work.')
        result = baresine.fit(data, x=x_axis, params=params)
        print(result.message)

    return result


################################################################################
#                                                                              #
#                                Sinus fitting                                 #
#                                                                              #
################################################################################


def make_sine_model(self, prefix=None):
    """ Create a model of sine with an amplitude.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """
    baresine_model, params = self.make_baresine_model(prefix=prefix)
    amplitude_model, params = self.make_amplitude_model(prefix=prefix)

    sine_model = amplitude_model*baresine_model
    params = sine_model.make_params()

    return sine_model, params

def estimate_sine(self, x_axis, data, params):
    """ Sine estimator, with an amplitude, frequency and phase.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        lmfit.Parameters params: derived OrderedDict object contains the initial
                                 values for the fit.
    """

    # Convert for safety:
    x_axis = np.array(x_axis)
    data = np.array(data)

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # estimate amplitude
    ampl_val = max(np.abs(data.min()), np.abs(data.max()))

    # calculate dft with zeropadding to obtain nicer interpolation between the
    # appearing peaks.
    dft_x, dft_y = compute_dft(x_axis, data, zeropad_num=1)

    stepsize = x_axis[1]-x_axis[0]  # for frequency axis
    frequency_max = np.abs(dft_x[np.log(dft_y).argmax()])

    # find minimal distance to the next meas point in the corresponding time value>
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data - func_val).sum()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = sum_res.argmax()/iter_steps *2*np.pi - np.pi

    # values and bounds of initial parameters
    params['amplitude'].set(value=ampl_val)
    params['frequency'].set(value=frequency_max, min=0.0, max=1/(stepsize)*3)
    params['phase'].set(value=phase, min=-np.pi, max=np.pi)

    return error, params


def make_sine_fit(self, x_axis, data, add_parameters=None):
    """ Perform a simple sine fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param dict add_parameters: optional, additional parameters for the fit,
                                which will be used instead of the values from
                                the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    sine, params = self.make_sine_model()
    error, params = self.estimate_sine(x_axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sine.fit(data, x=x_axis, params=params)
    except:
        logger.warning('The sine fit did not work.')
        result = sine.fit(data, x=x_axis, params=params)
        print(result.message)

    return result

################################################################################
#                                                                              #
#                         Sinus with offset fitting                            #
#                                                                              #
################################################################################

def make_sineoffset_model(self, prefix=None):
    """ Create a sine model with amplitude and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    sine_model, params = self.make_sine_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    sine_offset_model = sine_model + constant_model
    params = sine_offset_model.make_params()

    return sine_offset_model, params

def estimate_sineoffset(self, x_axis, data, params):
    """ Provides an estimator to obtain initial values for sine fitting.

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

    # set the offset as the average of the data
    offset = np.average(data)

    # level data
    data_level = data - offset

    error, params = self.estimate_sine(x_axis=x_axis, data=data_level, params=params)

    params['offset'].set(value=offset)

    return error, params

def make_sineoffset_fit(self, x_axis, data, add_parameters=None):
    """ Perform a sine fit with a constant offset on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param dict add_parameters: optional, additional parameters for the fit,
                                which will be used instead of the values from
                                the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    sine, params = self.make_sineoffset_model()

    error, params = self.estimate_sineoffset(x_axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sine.fit(data, x=x_axis, params=params)
    except:
        logger.warning('The sine fit did not work.')
        result = sine.fit(data, x=x_axis, params=params)
        print(result.message)

    return result

############################################################################
#                                                                          #
#                Sinus with exponential decay fitting                      #
#                                                                          #
############################################################################

def make_sineexponentialdecay_model(self, prefix=None):
    """ Create a model of sine with exponential decay.

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

    sine_model, params = self.make_sine_model(prefix=prefix)
    bareexponentialdecay_model, params = self.make_bareexponentialdecay_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    model = sine_model*bareexponentialdecay_model + constant_model
    params = model.make_params()

    return model, params

def estimate_sineexponentialdecay(self, x_axis, data, params=None):
    """ Provide a estimation of a initial values for a sine exponential decay function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    # Convert for safety:
    x_axis = np.array(x_axis)
    data = np.array(data)

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # set the offset as the median of the data
    offset = np.mean(data)

    # level data
    data_level = data - offset

    # estimate amplitude
    ampl_val = max(np.abs(data_level.min()), np.abs(data_level.max()))

    dft_x, dft_y = compute_dft(x_axis, data_level, zeropad_num=1)

    stepsize = x_axis[1] - x_axis[0]  # for frequency axis

    frequency_max = np.abs(dft_x[dft_y.argmax()])

    params['frequency'].set(value=frequency_max,
                            min=min(0.1 / (x_axis[-1]-x_axis[0]),dft_x[3]),
                            max=min(0.5 / stepsize, dft_x.max()-abs(dft_x[2]-dft_x[0])))

    # # perform fourier transform with zeropadding to get higher resolution
    # data_level_zeropaded = np.zeros(int(len(data_level) * 2))
    # data_level_zeropaded[:len(data_level)] = data_level
    # fourier = np.fft.fft(data_level_zeropaded)
    # stepsize = x_axis[1] - x_axis[0]  # for frequency axis
    # freq = np.fft.fftfreq(data_level_zeropaded.size, stepsize)
    # fourier_power = abs(fourier)
    # frequency_max = np.abs(freq[np.log(fourier).argmax()])

    # remove noise
    # a = np.std(fourier_power[:int(len(freq)/2)])
    # for i in range(0,int(len(fourier)/2)):
    #     if fourier_power[i] <= a:
    #         fourier_power[i] = 0
    #
    # calculating the width of the FT peak for the estimation of lifetime
    # peak_width = 0
    # for i in range(0, int(len(freq) / 2)):
    #     peak_width += fourier_power[i]*abs(freq[1]-freq[0])/max(fourier_power[:int(len(freq) / 2)])
    #
    # lifetime = 0.5 / peak_width

    #remove noise
    a = np.std(dft_y)
    for i in range(0, len(dft_x)):
        if dft_y[i]<=a:
            dft_y[i] = 0

    #calculating the width of the FT peak for the estimation of lifetime
    s = 0
    for i in range(0, len(dft_x)):
        s+= dft_y[i]*abs(dft_x[1]-dft_x[0])/max(dft_y)
    lifetime_val = 0.5/s

    # find minimal distance to the next meas point in the corresponding time value>
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data_level - func_val).sum()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = (sum_res.argmax()/iter_steps *2*np.pi - np.pi)%(2*np.pi)

    # values and bounds of initial parameters
    params['phase'].set(value=phase, min=-2*np.pi, max=2*np.pi)
    params['amplitude'].set(value=ampl_val, min=0)
    params['offset'].set(value=offset)

    params['lifetime'].set(value=lifetime_val,
                           min=2*(x_axis[1]-x_axis[0]),
                           max=1/(abs(dft_x[1]-dft_x[0])*0.5))

    # params['frequency'].set(value=frequency_max,
    #                         min=min(0.1 / (x_axis[-1]-x_axis[0]),freq[3]),
    #                         max=min(0.5 / stepsize, freq.max()-abs(freq[2]-freq[0])))

    return error, params

def make_sineexponentialdecay_fit(self, x_axis=None, data=None, add_parameters=None):
    """ Perform a sine exponential decay fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    sineexponentialdecay, params = self.make_sineexponentialdecay_model()

    error, params = self.estimate_sineexponentialdecay(x_axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sineexponentialdecay.fit(data, x=x_axis, params=params)
    except:
        logger.warning('The sineexponentialdecay fit did not work. '
                'Error message: {}'.format(str(result.message)))
        result = sineexponentialdecay.fit(data, x=x_axis, params=params)

    return result


############################################################################
#                                                                          #
#             Sinus with double exponential decay fitting                  #
#                                                                          #
############################################################################

def make_sinedoubleexponentialdecay_model(self, prefix=None):
    """ Create a model of sine with double exponential decay.

    @param str prefix: optional string, which serves as a prefix for all
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

    For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """

    sine_model, params = self.make_sine_model(prefix=prefix)
    baredoubleexponentialdecay_model, params = self.make_baredoubleexponentialdecay_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    model = sine_model * baredoubleexponentialdecay_model + constant_model
    params = model.make_params()

    return model, params


def make_sinedoubleexponentialdecay_fit(self, x_axis, data, add_parameters=None):
    """ Perform a sine double exponential decay fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    sine_double_exp_decay, params = self.make_sinedoubleexponentialdecay_model()

    error, params = self.estimate_sineexponentialdecay(x_axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sine_double_exp_decay.fit(data, x=x_axis, params=params)
    except:
        logger.warning('The sineexponentialdecay fit did not work. '
                'Error message: {}'.format(str(result.message)))
        result = sine_double_exp_decay.fit(data, x=x_axis, params=params)

    return result



############################################################################
#                                                                          #
#          Sinus with arbitrary exponential decay fitting                  #
#                                                                          #
############################################################################

def make_sinestretchedexponentialdecay_model(self, prefix=None):
    """ Create a model of a sine with stretched exponential decay.

    @param str prefix: optional string, which serves as a prefix for all
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

    For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """

    sine_model, params = self.make_sine_model(prefix=prefix)
    bare_stretched_exp_decay_model, params = self.make_barestretchedexponentialdecay_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    model = sine_model * bare_stretched_exp_decay_model + constant_model
    params = model.make_params()

    return model, params


def estimate_sinestretchedexponentialdecay(self, x_axis, data, params):
    """ Provide a estimation of a initial values for a sine stretched exponential decay function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param Parameters object params: object includes parameter dictionary which can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error, params = self.estimate_sineexponentialdecay(x_axis, data, params)
    #TODO: estimate the exponent cleaverly! For now, set the value to 2 since
    #      the usual values for our cases are between 1 and 3.
    params['beta'].set(value=2, min=0.0, max=10)

    return error, params

def make_sinestretchedexponentialdecay_fit(self, x_axis, data, add_parameters=None):
    """ Perform a sine stretched exponential decay fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    sine_stretched_exp_decay, params = self.make_sinestretchedexponentialdecay_model()

    error, params = self.estimate_sinestretchedexponentialdecay(x_axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sine_stretched_exp_decay.fit(data, x=x_axis, params=params)
    except:
        logger.warning('The sineexponentialdecay fit did not work. '
                'Error message: {}'.format(str(result.message)))
        result = sine_stretched_exp_decay.fit(data, x=x_axis, params=params)

    return result