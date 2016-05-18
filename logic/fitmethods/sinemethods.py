# -*- coding: utf-8 -*-
"""
This file contains methods for sine fitting, these methods
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

Copyright (C) 2015 Florian Frank florian.frank@uni-ulm.de
Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import numpy as np
from lmfit.models import Model
from lmfit import Parameters
from scipy.interpolate import splrep, sproot, splev
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import matplotlib.pylab as plt

############################################################################
#                                                                          #
#                               Sinus fitting                              #
#                                                                          #
############################################################################

def make_sine_model(self):
    """ This method creates a model of sine.

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
    def sine_function(x, amplitude, frequency, phase):
        """
        Function of a sine.
        @param x: variable variable - e.g. time
        @param amplitude: amplitude
        @param frequency: frequency
        @param phase: phase

        @return: sine function: in order to use it as a model
        """

        return amplitude*np.sin(2*np.pi*frequency*x+phase)

    constant_model, params = self.make_constant_model()
    model = Model(sine_function) + constant_model

    params = model.make_params()

    return model, params


def make_sine_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a sine fit on the provided data.

    @param array[] axis: axis values
    @param array[]  x_data: data
    @param dict add_parameters: Additional parameters

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    sine, params = self.make_sine_model()

    error, params = self.estimate_sine(axis, data, params)

    # overwrite values of additional parameters
    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sine.fit(data, x=axis, params=params)
    except:
        self.logMsg('The sine fit did not work.',
                    msgType='warning')
        result = sine.fit(data, x=axis, params=params)
        print(result.message)

    return result


def estimate_sine(self, x_axis=None, data=None, params=None):
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
            self.logMsg('Given parameter is no array.',
                        msgType='error')
            error = -1
        elif len(np.shape(var)) != 1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')
            error = -1
    if not isinstance(params, Parameters):
        self.logMsg('Parameters object is not valid in estimate_gaussian.',
                    msgType='error')
        error = -1

    # set parameters

    # set the offset as the average of the data
    offset = np.average(data)

    # level data
    data_level = data - offset

    # estimate amplitude
    params['amplitude'].value = max(np.abs(data_level.min()), np.abs(data_level.max()))

    # perform fourier transform with zeropadding to get higher resolution
    data_level_zeropaded = np.zeros(int(len(data_level)*2))
    data_level_zeropaded[:len(data_level)] = data_level
    fourier = np.fft.fft(data_level_zeropaded)
    stepsize = x_axis[1]-x_axis[0]  # for frequency axis
    freq = np.fft.fftfreq(data_level_zeropaded.size, stepsize)
    frequency_max = np.abs(freq[np.log(fourier).argmax()])

    # estimating the phase from the first point
    # TODO: This only works when data starts at 0
    phase_tmp = (data_level[0])/params['amplitude'].value
    phase = abs(np.arcsin(phase_tmp))


    if np.gradient(data)[0] < 0 and data_level[0] > 0:
        phase = np.pi - phase
    elif np.gradient(data)[0] < 0 and data_level[0] < 0:
        phase += np.pi
    elif np.gradient(data)[0] > 0 and data_level[0] < 0:
        phase = 2.*np.pi - phase
    
    params['frequency'].value = frequency_max
    params['phase'].value = phase
    params['offset'].value = offset

    #Adding constraints
    params['frequency'].min = 0.0
    params['frequency'].max = 1/(stepsize) * 3


    return error, params

############################################################################
#                                                                          #
#                Sinus with exponential decay fitting                      #
#                                                                          #
############################################################################

def make_sineexponentialdecay_model(self):

    def sine_function(x, amplitude, frequency, phase):
        """
        Function of a sine.
        @param x: variable variable - e.g. time
        @param amplitude: amplitude
        @param frequency: frequency
        @param phase: phase

        @return: sine function: in order to use it as a model
        """

        return amplitude * np.sin(2 * np.pi * frequency * x + phase)

    exponentialdecay_model, params = self.make_exponentialdecay_model()
    constant_model, params = self.make_constant_model()
    model = Model(sine_function)*exponentialdecay_model + constant_model
    params = model.make_params()

    return model, params

def estimate_sineexponentialdecay(self,x_axis=None, data=None, params=None):
    error = 0
    parameters = [x_axis, data]
    for var in parameters:
        if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.',
                        msgType='error')
            error = -1
        elif len(np.shape(var)) != 1:
            self.logMsg('Given parameter is no one dimensional array.',
                        msgType='error')
            error = -1
    if not isinstance(params, Parameters):
        self.logMsg('Parameters object is not valid in estimate_gaussian.',
                    msgType='error')
        error = -1
        
    # set the offset as the average of the data
    offset = np.average(data)

    # level data
    data_level = data - offset

    # estimate amplitude
    params['amplitude'].value = max(np.abs(data_level.min()), np.abs(data_level.max()))

    # perform fourier transform with zeropadding to get higher resolution
    data_level_zeropaded = np.zeros(int(len(data_level) * 2))
    data_level_zeropaded[:len(data_level)] = data_level
    fourier = np.fft.fft(data_level_zeropaded)
    stepsize = x_axis[1] - x_axis[0]  # for frequency axis
    freq = np.fft.fftfreq(data_level_zeropaded.size, stepsize)
    frequency_max = np.abs(freq[np.log(fourier).argmax()])
    fourier_real = abs(fourier.real)
    params['frequency'].value = frequency_max
    def fwhm(x, y, k=3):
        """
        Determine full-with-half-maximum of a peaked set of points, x and y.

        Assumes that there is only one peak present in the datasset.  The function
        uses a spline interpolation of order k.

        Function taken from:
        http://stackoverflow.com/questions/10582795/finding-the-full-width-half-maximum-of-a-peak/14327755#14327755

        Question from: http://stackoverflow.com/users/490332/harpal
        Answer: http://stackoverflow.com/users/1146963/jdg
        """


        half_max = max(y) / 2.0
        s = splrep(x, y- half_max)
        roots = sproot(s)
        if len(roots) < 2:
            # self.logMsg('No peak was found.',
            #             msgType='error')
            print("No peaks")
            return [0.0010001]         #pass
        elif len(roots) > 2:
            # self.logMsg('Multiple peaks was found.',
            #             msgType='error')
            print("Multiple paires of roots.")
            return [abs(roots[1] - roots[0])*2]
            #pass
        else:
            return [abs(roots[1] - roots[0])]

        # print(freq)
        # print(len(fourier_real))
    #adjustion the order for freq and fourier, this is not necessity, but it need to be awared that the order of
    #frequency is not from minus inf to plus inf.
    freq_plus = [0] * len(freq)
    for i in range(0, int(len(freq) / 2)):
        freq_plus[i + int(len(freq) / 2)] = freq[i]
    for i in range(int(len(freq) * 0.5), len(freq)):
        freq_plus[i - int(len(freq) / 2)] = freq[i]
    fourier_real_plus = [0] * len(fourier_real)
    for i in range(0, int(len(fourier_real) / 2)):
        fourier_real_plus[i + int(len(fourier_real) / 2)] = fourier_real[i]
    for i in range(int(len(fourier_real) * 0.5), len(fourier_real)):
        fourier_real_plus[i - int(len(fourier_real) / 2)] = fourier_real[i]
    #print(len(np.array(freq_plus)), np.array(freq_plus))


    gaus = gaussian(2,2)
    smooth_data = filters.convolve1d(fourier_real_plus[int(len(freq) / 2):] - max(fourier_real_plus) / 2,
                                     gaus / gaus.sum(), mode='mirror')
    plt.plot(freq_plus[int(len(freq) / 2):], smooth_data, '-g')
    plt.plot(freq_plus[int(len(freq) / 2):],
             fourier_real_plus[int(len(freq) / 2):] - max(fourier_real_plus) / 2, '-or')
    plt.plot(freq_plus[int(len(freq) / 2):], splev(freq[:int(len(freq) / 2)],
                                                   splrep(np.array(freq_plus[int(len(freq_plus) / 2):]),
                                                          np.array(
                                                              fourier_real_plus[int(len(freq_plus) / 2):] - max(
                                                                  fourier_real_plus) / 2))))
    #plt.xlim(0, 0.1)
    plt.show()
    
    # estimate life time from peak width
    fwhm_plus = fwhm(np.array(freq_plus[int(len(freq_plus)/2):]),np.array(smooth_data),k=3)

    params['lifetime'].value = 1 / (fwhm_plus[0]*1.5)
    print("FWHM", fwhm_plus[0])

    # estimating the phase from the first point
    # TODO: This only works when data starts at 0
    phase_tmp = (data_level[0]) / params['amplitude'].value
    phase = abs(np.arcsin(phase_tmp))

    if np.gradient(data)[0] < 0 and data_level[0] > 0:
        phase = np.pi - phase
    elif np.gradient(data)[0] < 0 and data_level[0] < 0:
        phase += np.pi
    elif np.gradient(data)[0] > 0 and data_level[0] < 0:
        phase = 2. * np.pi - phase


    params['phase'].value = phase
    params['offset'].value = offset
    #params['lifetime'].value = 1/(fwhm_plus*2.8)
    
    #bounds of initial parameters
    params['lifetime'].min = 0
    params['lifetime'].max = 1/(abs(freq[1]-freq[0])*1.5)   
    params['frequency'].min = 0.1 / (x_axis[-1]-x_axis[0])
    params['frequency'].max = min(0.5 / stepsize, freq.max()-abs(freq[1]-freq[0]))
    
    print('\n','lifetime.min: ',params['lifetime'].min,'\n',
          'lifetime.max: ',params['lifetime'].max,'\n','frequency.min: ',
          params['frequency'].min,'\n','frequency.max: ',params['frequency'].max)
    
    
    
    return error, params

# Basically the same as sine fitting.
def make_sineexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    #Todo: docstring
    sineexponentialdecay, params = self.make_sineexponentialdecay_model()

    error, params = self.estimate_sineexponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sineexponentialdecay.fit(data, x=axis, params=params)
    except:
        # self.logMsg('The sineexponentialdecay fit did not work.',
        #             msgType='warning')
        result = sineexponentialdecay.fit(data, x=axis, params=params)
        print("Error in sinexp fit:",result.message)

    return result
