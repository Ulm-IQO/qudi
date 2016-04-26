# -*- coding: utf-8 -*-
"""
This file contains methods for decay-like fitting, these methods
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

Copyright (C) 2016 Ou Wang ou.wang@uni-ulm.de
"""

import numpy as np
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel,LinearModel
from lmfit import Parameters
from lmfit import minimize
from scipy.interpolate import splrep, sproot, splev
############################################################################
#                                                                          #
#                              decay fitting                              #
#                                                                          #
############################################################################

def make_exponentialdecay_model(self): # pure exponential decay

    #def bareexponentaildecay_function(x,lifetime):
        #return np.exp(x/lifetime)
    #def exponentialdecay_function(x,lifetime,amplitude,x_offset,y_offset):
        #return amplitude*np.exp((x+x_offset)/lifetime) + y_offset
    def exponentialdecay_function(x,lifetime):
        return np.exp(-x/lifetime)
    #amplitude_model, params = self.make_amplitude_model()
    #constant_model, params = self.make_constant_model()
    #model = amplitude_model * Model(exponentialdecay_function) + constant_model
    model = Model(exponentialdecay_function)
    params = model.make_params()

    return model, params

def estimate_exponentialdecay(self,x_axis=None, data=None, params=None):
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

    #offset = np.min(data)

    #data_level = data - offset

    data_level_log = np.log(abs(data))

    params['lifetime'].value = -1/(np.polyfit(x_axis,data_level_log,1)[0])

    #params['amplitude'].value = np.exp(data_level+x_axis/params['lifetime'].value)

    #params['offset'].value = offset

    return error, params

def make_exponential_fit(self, axis=None, data=None, add_parameters=None):
    exponentialdecay, params = self.make_exponentialdecay_model()

    error, params = self.estimate_exponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = exponentialdecay.fit(data, x=axis, params=params)
    except:
        self.logMsg('The exponentialdecay fit did not work.',
                    msgType='warning')
        result = exponentialdecay.fit(data, x=axis, params=params)
        print(result.message)

    return result

################################################################################################################
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
    fourier_real = fourier.real

    def fwhm(x, y, k=10):
        """
        Determine full-with-half-maximum of a peaked set of points, x and y.

        Assumes that there is only one peak present in the datasset.  The function
        uses a spline interpolation of order k.
        """

        class MultiplePeaks(Exception):
            pass

        class NoPeaksFound(Exception):
            pass

        half_max = max(y) / 2.0
        s = splrep(x, y - half_max)
        roots = sproot(s)
        if len(roots) < 2:
            raise NoPeaksFound("No proper peaks were found in the data set; likely "
                               "the dataset is flat (e.g. all zeros).")
        else:
            print(len(roots))
            return abs(roots[1] - roots[0])

        # print(freq)
        # print(len(fourier_real))
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
    print(len(np.array(freq_plus)), np.array(freq_plus))
    fwhm_plus = fwhm(np.array(freq_plus), np.array(fourier_real_plus), k=10)
    params['lifetime'].value = 1 / (fwhm_plus * np.pi)
    print("FWHM", fwhm_plus)

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

    params['frequency'].value = frequency_max
    params['phase'].value = phase
    params['offset'].value = offset
    params['lifetime'].value = 1/(fwhm_plus*np.pi)
    return error, params

def make_sineexponentialdecay_fit(self, axis=None, data=None, add_parameters=None):
    sineexponentialdecay, params = self.make_sineexponentialdecay_model()

    error, params = self.estimate_sineexponentialdecay(axis, data, params)

    if add_parameters is not None:
        params = self._substitute_parameter(parameters=params,
                                            update_dict=add_parameters)
    try:
        result = sineexponentialdecay.fit(data, x=axis, params=params)
    except:
        self.logMsg('The sineexponentialdecay fit did not work.',
                    msgType='warning')
        result = sineexponentialdecay.fit(data, x=axis, params=params)
        print(result.message)

    return result