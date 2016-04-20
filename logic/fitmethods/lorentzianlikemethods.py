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

Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import numpy as np
from lmfit.models import ConstantModel, LorentzianModel
from lmfit import Parameters

from scipy.ndimage import filters

############################################################################
#                                                                          #
#                             Lorentzian Model                             #
#                                                                          #
############################################################################


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

    model=LorentzianModel()+ConstantModel()
    params=model.make_params()

    return model,params

def estimate_lorentz(self,x_axis=None,data=None):
    """ This method provides a lorentzian function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values

    @return int error: error code (0:OK, -1:error)
    @return float amplitude: estimated amplitude
    @return float x_zero: estimated x value of maximum
    @return float sigma_x: estimated standard deviation in x direction
    @return float offset: estimated offset
    """
#           TODO: make sigma and amplitude good, this is only a dirty fast solution
    error=0
    # check if parameters make sense
    parameters=[x_axis,data]
    for var in parameters:
        if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.', msgType='error')
            error=-1
        elif len(np.shape(var))!=1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')
    #set paraameters

    data_smooth,offset=self.find_offset_parameter(x_axis,data)

    data_level=data-offset
    data_min=data_level.min()
    data_max=data_level.max()

    #estimate sigma
    numerical_integral=np.sum(data_level) * \
                       (abs(x_axis[-1] - x_axis[0])) / len(x_axis)

    if data_max>abs(data_min):
        try:
            self.logMsg('The lorentzian estimator set the peak to the '
                        'minimal value, if you want to fit a peak instead '
                        'of a dip rewrite the estimator.',
                        msgType='warning')
        except:
            self.logMsg('The lorentzian estimator set the peak to the '
                        'minimal value, if you want to fit a peak instead '
                        'of a dip rewrite the estimator.',
                        msgType='warning')

    amplitude_median=data_min
    x_zero=x_axis[np.argmin(data_smooth)]

    sigma = numerical_integral / (np.pi * amplitude_median)
    amplitude=amplitude_median * np.pi * sigma

    return error, amplitude, x_zero, sigma, offset

def make_lorentzian_fit(self, axis=None, data=None,
                        add_parameters=None):
    """ This method performes a 1D lorentzian fit on the provided data.

    @param array [] axis: axis values
    @param array[]  x_data: data
    @param dictionary add_parameters: Additional parameters

    @return object model: lmfit.model.ModelFit object, all parameters
                          provided about the fitting, like: success,
                          initial fitting values, best fitting values, data
                          with best fit with given axis,...
    """

    error,amplitude, x_zero, sigma, offset = self.estimate_lorentz(
                                                            axis,data)

    model,params = self.make_lorentzian_model()

    #auxiliary variables
    stepsize=axis[1]-axis[0]
    n_steps=len(axis)

    # TODO: Make sigma amplitude and x_zero better
    # Defining standard parameters

    if axis[1]-axis[0]>0:
        #                (Name,       Value,    Vary,  Min,                        Max,                         Expr)
        params.add_many(('amplitude', amplitude, True, None,                       -1e-12,                      None),
                        ('sigma',     sigma,     True, (axis[1]-axis[0])/2 ,       (axis[-1]-axis[0])*10,       None),
                        ('center',    x_zero,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None),
                        ('c',         offset,    True, None,                       None,                        None))


    if axis[0]-axis[1]>0:

    #                   (Name,        Value,  Vary,    Min,                 Max,                  Expr)
        params.add_many(('amplitude', amplitude, True, None,                -1e-12,               None),
                        ('sigma',     sigma,     True, (axis[0]-axis[1])/2, (axis[0]-axis[1])*10, None),
                        ('center',    x_zero,    True, (axis[-1]),          (axis[0]),            None),
                        ('c',         offset,    True, None,                None,                 None))

#TODO: Add logmessage when value is changed
    #redefine values of additional parameters
    if add_parameters is not None :
        params=self._substitute_parameter(parameters=params,
                                         update_dict=add_parameters)
    try:
        result=model.fit(data, x=axis,params=params)
    except:
        result=model.fit(data, x=axis,params=params)
        self.logMsg('The 1D lorentzian fit did not work. Error '
                    'message:'+result.message,
                    msgType='warning')
    return result

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

#           TODO: make sigma and amplitude good, this is only a dirty fast solution
    error=0
    # check if parameters make sense

    parameters=[x_axis,data]
    for var in parameters:
        if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.',
                        msgType='error')
            error=-1
        elif len(np.shape(var))!=1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')
    #set paraameters
    #print('data',data)
    data_smooth,offset=self.find_offset_parameter(x_axis,data)
    #print('offset',offset)
    data_level=data-offset
    data_min=data_level.min()
    data_max=data_level.max()
    #print('data_min',data_min)
    #print('data_max',data_max)
    #estimate sigma

    numerical_integral=np.sum(data_level) * \
                       (np.abs(x_axis[0] - x_axis[-1])) / len(x_axis)



    if data_max<abs(data_min):
        try:
            self.logMsg('This lorentzian estimator set the peak to the '
                        'maximum value, if you want to fit a dip '
                        'instead of a peak use estimate_lorentz.',
                        msgType='warning')
        except:
            print('This lorentzian estimator set the peak to the '
                  'maximum value, if you want to fit a dip instead of '
                  'a peak use estimate_lorentz.')

    amplitude_median=data_max
    #x_zero=x_axis[np.argmax(data_smooth)]
    x_zero=x_axis[np.argmax(data)]
    sigma = np.abs(numerical_integral / (np.pi * amplitude_median))
    amplitude=amplitude_median * np.pi * sigma

    #print('amplitude',amplitude)
    #print('x_zero',x_zero)
    #print('offset',offset)

    return error, amplitude, x_zero, sigma, offset

def make_lorentzianpeak_fit(self, axis=None, data=None,
                             add_parameters=None):
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
    offset      = self.estimate_lorentzpeak(axis, data)


    model, params = self.make_lorentzian_model()

    # auxiliary variables:
    stepsize=np.abs(axis[1]-axis[0])
    n_steps=len(axis)

#            TODO: Make sigma amplitude and x_zero better

    #Defining standard parameters

    if axis[1]-axis[0]>0:

    #                   (Name,        Value,     Vary, Min,                        Max,                         Expr)
        params.add_many(('amplitude', amplitude, True, 2e-12,                      None,                        None),
                        ('sigma',     sigma,     True, (axis[1]-axis[0])/2,        (axis[-1]-axis[0])*10,       None),
                        ('center',    x_zero,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None),
                        ('c',         offset,    True, None,                       None,                        None))
    if axis[0]-axis[1]>0:

    #                   (Name,        Value,     Vary, Min,                  Max,                  Expr)
        params.add_many(('amplitude', amplitude, True, 2e-12,                None,                 None),
                        ('sigma',     sigma,     True, (axis[0]-axis[1])/2 , (axis[0]-axis[1])*10, None),
                        ('center',    x_zero,    True, (axis[-1]),           (axis[0]),            None),
                        ('c',         offset,    True, None,                 None,                 None))

    #TODO: Add logmessage when value is changed
    #redefine values of additional parameters

    if add_parameters is not None :
        params=self._substitute_parameter(parameters=params,
                                         update_dict=add_parameters)
    try:
        result=model.fit(data, x=axis,params=params)
    except:
        result=model.fit(data, x=axis,params=params)
        self.logMsg('The 1D gaussian fit did not work. Error '
                    'message:' + result.message,
                    msgType='warning')

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
        model+=LorentzianModel(prefix='lorentz{}_'.format(ii))

    params=model.make_params()

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
    error=0
    # check if parameters make sense
    parameters=[x_axis,data]
    for var in parameters:
        if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.', \
                        msgType='error')
            error=-1
        elif len(np.shape(var))!=1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')


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

def make_doublelorentzian_fit(self, axis=None, data=None,
                               add_parameters=None):
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
    offset              = self.estimate_doublelorentz(axis, data)

    model, params = self.make_multiplelorentzian_model(no_of_lor=2)

    # Auxiliary variables:
    stepsize=axis[1]-axis[0]
    n_steps=len(axis)

    #Defining standard parameters
    #            (Name,                  Value,          Vary, Min,                        Max,                         Expr)
    params.add('lorentz0_amplitude', lorentz0_amplitude, True, None,                       -0.01,                       None)
    params.add('lorentz0_sigma',     lorentz0_sigma,     True, (axis[1]-axis[0])/2 ,       (axis[-1]-axis[0])*4,        None)
    params.add('lorentz0_center',    lorentz0_center,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None)
    params.add('lorentz1_amplitude', lorentz1_amplitude, True, None,                       -0.01,                       None)
    params.add('lorentz1_sigma',     lorentz1_sigma,     True, (axis[1]-axis[0])/2 ,       (axis[-1]-axis[0])*4,        None)
    params.add('lorentz1_center',    lorentz1_center,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None)
    params.add('c',                  offset,             True, None,                       None,                        None)

    #redefine values of additional parameters
    if add_parameters is not None:
        params=self._substitute_parameter(parameters=params,
                                         update_dict=add_parameters)
    try:
        result=model.fit(data, x=axis,params=params)
    except:
        result=model.fit(data, x=axis,params=params)
        self.logMsg('The double lorentzian fit did not '
                    'work:'+result.message,
                    msgType='warning')

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

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values

    @return lmfit.parameter.Parameters parameters: New object corresponding
                                                   parameters like offset,
                                                   the three sigma's, the
                                                   three amplitudes and centers

    """

    data_smooth_lorentz,offset=self.find_offset_parameter(x_axis,data)

    #filter should always have a length of approx linewidth 1MHz
    stepsize_in_x=1/((x_axis.max()-x_axis.min())/len(x_axis))
    lorentz=np.ones(int(stepsize_in_x)+1)
    x_filter=np.linspace(0,5*stepsize_in_x,5*stepsize_in_x)
    lorentz=np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/5),
                                    (x_filter >= len(x_filter)/5)*(x_filter<len(x_filter)*2/5),
                                    (x_filter >= len(x_filter)*2/5)*(x_filter<len(x_filter)*3/5),
                                    (x_filter >= len(x_filter)*3/5)*(x_filter<len(x_filter)*4/5),
                                    (x_filter >= len(x_filter)*4/5)], [1, 0,1,0,1])
    data_smooth = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(),mode='constant',cval=data_smooth_lorentz.max())

    parameters=Parameters()

    #            (Name,                  Value,          Vary, Min,                        Max,                         Expr)
    parameters.add('lorentz0_amplitude', value=data_smooth_lorentz.min()-offset,         max=-1e-6)
    parameters.add('lorentz0_center',    value=x_axis[data_smooth.argmin()]-2.15)
    parameters.add('lorentz0_sigma',     value=0.5,                                      min=0.01,    max=4.)
    parameters.add('lorentz1_amplitude', value=parameters['lorentz0_amplitude'].value,   max=-1e-6)
    parameters.add('lorentz1_center',    value=parameters['lorentz0_center'].value+2.15, expr='lorentz0_center+2.15')
    parameters.add('lorentz1_sigma',     value=parameters['lorentz0_sigma'].value,       min=0.01,  max=4.,expr='lorentz0_sigma')
    parameters.add('lorentz2_amplitude', value=parameters['lorentz0_amplitude'].value,   max=-1e-6)
    parameters.add('lorentz2_center',    value=parameters['lorentz1_center'].value+2.15, expr='lorentz0_center+4.3')
    parameters.add('lorentz2_sigma',     value=parameters['lorentz0_sigma'].value,       min=0.01,  max=4.,expr='lorentz0_sigma')
    parameters.add('c',                  value=offset)

    return parameters


def make_N14_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a fit on the provided data where a N14
    hyperfine interaction of 2.15 MHz is taken into accound.

    @param array [] axis: axis values
    @param array[]  x_data: data
    @param dictionary add_parameters: Additional parameters

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...

    """

    parameters=self.estimate_N14(axis, data)

    # redefine values of additional parameters
    if add_parameters is not None:
        parameters=self._substitute_parameter(parameters=parameters,
                                              update_dict=add_parameters)

    mod,params = self.make_multiplelorentzian_model(no_of_lor=3)

    result=mod.fit(data=data, x=axis, params=parameters)


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

    @param array x_axis: x values
    @param array data: value of each data point corresponding to
                        x values

    @return lmfit.parameter.Parameters parameters: New object corresponding
                                                   parameters like offset,
                                                   the three sigma's, the
                                                   three amplitudes and centers

    """

    data_smooth_lorentz, offset = self.find_offset_parameter(x_axis, data)

    hf_splitting=3.03
    #filter should always have a length of approx linewidth 1MHz
    stepsize_in_x=1/((x_axis.max()-x_axis.min())/len(x_axis))
    lorentz=np.zeros(int(stepsize_in_x)+1)
    x_filter = np.linspace(0,4*stepsize_in_x,4*stepsize_in_x)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/4),
                                    (x_filter >= len(x_filter)/4)*(x_filter<len(x_filter)*3/4),
                                    (x_filter >= len(x_filter)*3/4)], [1, 0,1])
    data_smooth = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(),
                                     mode='constant', cval=data_smooth_lorentz.max())

    parameters = Parameters()

    parameters.add('lorentz0_amplitude', value=data_smooth.min()-offset,max=-1e-6)
    parameters.add('lorentz0_center', value=x_axis[data_smooth.argmin()]-hf_splitting/2.)
    parameters.add('lorentz0_sigma', value=0.5, min=0.01, max=4.)
    parameters.add('lorentz1_amplitude', value=parameters['lorentz0_amplitude'].value,max=-1e-6)
    parameters.add('lorentz1_center', value=parameters['lorentz0_center'].value+hf_splitting, expr='lorentz0_center+3.03')
    parameters.add('lorentz1_sigma', value=parameters['lorentz0_sigma'].value,min=0.01,max=4., expr='lorentz0_sigma')
    parameters.add('c', value=offset)

    return parameters


def make_N15_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a fit on the provided data where a N14
    hyperfine interaction of 3.03 MHz is taken into accound.

    @param array [] axis: axis values
    @param array[]  data: data
    @param dictionary add_parameters: Additional parameters

    @return lmfit.model.ModelFit result: All parameters provided about
                                         the fitting, like: success,
                                         initial fitting values, best
                                         fitting values, data with best
                                         fit with given axis,...

    """

    parameters = self.estimate_N15(axis, data)

    # redefine values of additional parameters
    if add_parameters is not None:
        parameters = self._substitute_parameter(parameters=parameters,
                                                update_dict=add_parameters)

    mod, params = self.make_multiplelorentzian_model(no_of_lor=2)

    result = mod.fit(data=data, x=axis, params=parameters)

    return result
