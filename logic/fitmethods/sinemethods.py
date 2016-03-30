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
from lmfit import Parameters
import scipy

############################################################################
#                                                                          #
#                               Sinus fitting                              #
#                                                                          #
############################################################################

def estimate_sine(self, x_axis=None, data=None):
    """ This method provides a sine function.

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values

    @return int error: error code (0:OK, -1:error)
    @return float amplitude: estimated amplitude
    @return float omega: estimated period of the sine
    @return float shift: estimated phase shift
    @return float decay: estimated decay of the curve
    @return float offset: estimated offset
    """

    error = 0

    # check if parameters make sense

    parameters=[x_axis,data]
    for var in parameters:
        if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
            self.logMsg('Given parameter is no array.', msgType='error')
            error=-1
        elif len(np.shape(var))!=1:
            self.logMsg('Given parameter is no one dimensional '
                        'array.', msgType='error')
            error=-1

    # set parameters

    offset = np.average(data)
    data_level = data - offset
    amplitude = max(data_level.max(),np.abs(data_level.min()))
    fourier = np.fft.fft(data_level)
    stepsize = x_axis[1]-x_axis[0]
    freq = np.fft.fftfreq(data_level.size,stepsize)
    tmp = freq,np.log(fourier)
    omega = 1/(np.abs(tmp[0][tmp[1].argmax()]))
    shift_tmp = (offset-data[0])/amplitude
    shift = np.arccos(shift_tmp)

    # TODO: Improve decay estimation
    if len(data) > omega/stepsize * 2.5:
        pos01 = int((1-shift/(np.pi**2)) * omega/(2*stepsize))
        pos02 = pos01 + int(omega/stepsize)
        # print(pos01,pos02,data[pos01],data[pos02])
        decay = np.log(data[pos02]/data[pos01])/omega
        # decay = - np.log(0.2)/x_axis[-1]
    else:
        decay = 0.0

    return amplitude, offset, shift, omega, decay

# define objective function: returns the array to be minimized
def fcn2min(self,params, x, data):
    """ model decaying sine wave, subtract data"""
    v = params.valuesdict()

    model = v['amplitude'] * \
            np.sin(x * 1/v['omega']*np.pi*2 + v['shift']) * \
            np.exp(-x*v['decay']) + v['offset']

    return model - data

def make_sine_fit(self, axis=None, data=None, add_parameters=None):
    """ This method performes a sine fit on the provided data.

    @param array[] axis: axis values
    @param array[]  data: data
    @param dictionary add_parameters: Additional parameters

    @return result: All parameters provided about the fitting, like:
                    success,
                    initial fitting values, best fitting values, data
                    with best fit with given axis,...
    @return float fit_x: x values to plot the fit
    @return float fit_y: y values to plot the fit
    """


    amplitude,  \
    offset,     \
    shift,      \
    omega,      \
    decay       = self.estimate_sine(axis, data)

    params = Parameters()

    #Defining standard parameters
    #               (Name,        Value,     Vary, Min,  Max,  Expr)
    params.add_many(('amplitude', amplitude, True, None, None, None),
                    ('offset',    offset,    True, None, None, None),
                    ('shift',     shift,     True, None, None, None),
                    ('omega',     omega,     True, None, None, None),
                    ('decay',     decay,     True, None, None, None))


    #redefine values of additional parameters
    if add_parameters is not None:
        params=self._substitute_parameter(parameters=params,
                                         update_parameters=add_parameters)
    try:
        result = minimize(self.fcn2min, params, args=(axis, data))
    except:
        result = minimize(self.fcn2min, params, args=(axis, data))
        self.logMsg('The sine fit did not work. Error '
                    'message:'+result.message,
                    msgType='message')

    fit_y = data + result.residual
    fit_x = axis


    return result, fit_x, fit_y

