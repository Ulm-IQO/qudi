# -*- coding: utf-8 -*-

"""
This file contains the Qudi file with all available sampling functions.

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
from collections import OrderedDict


class SamplingFunctions():
    """ Collection of mathematical functions used for sampling of the pulse
        sequences.
    """
    def __init__(self):
        # If you want to define a new function, make a new method and add the
        # reference to this function to the _math_func dictionary:
        self._math_func = OrderedDict()
        self._math_func['Idle']             = self._idle
        self._math_func['DC']               = self._dc
        self._math_func['Sin']              = self._sin
        self._math_func['Cos']              = self._cos
        self._math_func['DoubleSin']        = self._doublesin
        self._math_func['TripleSin']        = self._triplesin

        self._math_func['SinGauss']         = self._singauss
        self._math_func['CosGauss']         = self._cosgauss
        self._math_func['DoubleSinGauss']   = self._doublesingauss
        self._math_func['TripleSinGauss']   = self._triplesingauss

        # Definition of constraints for the parameters
        # --------------------------------------------
        # Mathematical parameters may be subjected to certain constraints
        # (e.g. a range within the function is defined). These contraints can
        # be set here individually for each parameter. There exist some
        # predefined lists of constraints for the common parameters like
        # frequency, amplitude, phase. If your functions do not desire special
        # limitations, then use these.
        # Moreover, the display Widget in the GUI will depend on the
        # contraints you are setting here.
        # FIXME: This GUI dependancy has to move to other places

        # predefine a general range for the frequency, amplitude and phase
        # <general_parameter> = {}
        freq_def = {'unit': 'Hz', 'init_val': 0.0, 'min': 0.0, 'max': np.inf,
                    'view_stepsize': 1.0, 'dec': 15, 'type': float}
        ampl_def = {'unit': 'V', 'init_val': 0.0, 'min': 0.0, 'max': 1.0,
                    'view_stepsize': 0.01, 'dec': 15, 'type': float}
        phase_def = {'unit': '°', 'init_val': 0.0, 'min': -360, 'max': 360,
                     'view_stepsize': 0.1, 'dec': 15, 'type': float}

        # the following keywords are known to the GUI elements, and you should
        # use only those to define you own limitation. Here is an explanation
        # for the used keywords:

        # 'unit' : string for the SI unit.
        # 'init_val' : initial value the parameter should have
        # 'min' : minimal value of the parameter
        # 'max' : maximal value of the parameter
        # 'view_stepsize' : optional, the corresponding ViewWidget will have
        #                   buttons to increment and decrement the current
        #                   value.
        # 'hard_stepsize' : optional, the accepted value will be a multiple of
        #                   this. Normally, this will be dictate by hardware.
        # 'type' : the type of the parameter, either int, float, bool


        # Configure also the parameter for the defined functions so that it is
        # know which input parameters the function desires:

        self.func_config = OrderedDict()
        self.func_config['Idle'] = OrderedDict()
        self.func_config['DC'] = OrderedDict()
        self.func_config['DC']['amplitude1'] = ampl_def

        self.func_config['Sin'] = OrderedDict()
        self.func_config['Sin']['frequency1'] = freq_def
        self.func_config['Sin']['amplitude1'] = ampl_def
        self.func_config['Sin']['phase1'] = phase_def

        self.func_config['Cos'] = OrderedDict()
        self.func_config['Cos']['frequency1'] = freq_def
        self.func_config['Cos']['amplitude1'] = ampl_def
        self.func_config['Cos']['phase1'] = phase_def

        self.func_config['DoubleSin'] = OrderedDict()
        self.func_config['DoubleSin']['frequency1'] = freq_def
        self.func_config['DoubleSin']['frequency2'] = freq_def
        self.func_config['DoubleSin']['amplitude1'] = ampl_def
        self.func_config['DoubleSin']['amplitude2'] = ampl_def
        self.func_config['DoubleSin']['phase1']     = phase_def
        self.func_config['DoubleSin']['phase2']     = phase_def

        self.func_config['TripleSin'] = OrderedDict()
        self.func_config['TripleSin']['frequency1'] = freq_def
        self.func_config['TripleSin']['frequency2'] = freq_def
        self.func_config['TripleSin']['frequency3'] = freq_def
        self.func_config['TripleSin']['amplitude1'] = ampl_def
        self.func_config['TripleSin']['amplitude2'] = ampl_def
        self.func_config['TripleSin']['amplitude3'] = ampl_def
        self.func_config['TripleSin']['phase1']     = phase_def
        self.func_config['TripleSin']['phase2']     = phase_def
        self.func_config['TripleSin']['phase3']     = phase_def


    def _idle(self, time_arr, parameters=None):
        result_arr = np.zeros(len(time_arr))
        return result_arr

    def _dc(self, time_arr, parameters):
        amp = parameters['amplitude1']
        result_arr = np.full(len(time_arr), amp, dtype='float64')
        return result_arr

    def _sin(self, time_arr, parameters):
        amp = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        freq = parameters['frequency1']
        phase = np.pi * parameters['phase1'] / 180
        result_arr = amp * np.sin(2*np.pi * freq * time_arr + phase)
        return result_arr

    def _cos(self, time_arr, parameters):
        amp = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        freq = parameters['frequency1']
        phase = np.pi * parameters['phase1'] / 180
        result_arr = amp * np.cos(2*np.pi * freq * time_arr + phase)
        return result_arr

    def _doublesin(self, time_arr, parameters):
        amp1 = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        amp2 = 2*parameters['amplitude2'] #conversion so that the AWG actually outputs the specified voltage
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        phase1 = np.pi * parameters['phase1'] / 180
        phase2 = np.pi * parameters['phase2'] / 180
        result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1)
        result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
        return result_arr

    def _triplesin(self, time_arr, parameters):
        amp1 = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        amp2 = 2*parameters['amplitude2'] #conversion so that the AWG actually outputs the specified voltage
        amp3 = 2*parameters['amplitude3'] #conversion so that the AWG actually outputs the specified voltage
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        freq3 = parameters['frequency3']
        phase1 = np.pi * parameters['phase1'] / 180
        phase2 = np.pi * parameters['phase2'] / 180
        phase3 = np.pi * parameters['phase3'] / 180
        result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1)
        result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
        result_arr += amp3 * np.sin(2*np.pi * freq3 * time_arr + phase3)
        return result_arr

    def _singauss(self, time_arr, parameters):
        amp = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        freq = parameters['frequency1']
        phase = np.pi * parameters['phase1'] / 180
        length_s = time_arr[-1]-time_arr[0]
        sigma = length_s / 6
        mu = time_arr[time_arr.size//2]
        result_arr = amp * np.sin(2*np.pi * freq * time_arr + phase) * np.exp(-(((time_arr-mu)/sigma)**2)/2)
        return result_arr

    def _cosgauss(self, time_arr, parameters):
        amp = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        freq = parameters['frequency1']
        phase = np.pi * parameters['phase1'] / 180
        length_s = time_arr[-1]-time_arr[0]
        sigma = length_s / 6
        mu = time_arr[time_arr.size//2]
        result_arr = amp * np.cos(2*np.pi * freq * time_arr + phase) * np.exp(-(((time_arr-mu)/sigma)**2)/2)
        return result_arr

    def _doublesingauss(self, time_arr, parameters):
        amp1 = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        amp2 = 2*parameters['amplitude2'] #conversion so that the AWG actually outputs the specified voltage
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        phase1 = np.pi * parameters['phase1'] / 180
        phase2 = np.pi * parameters['phase2'] / 180
        length_s = time_arr[-1]-time_arr[0]
        sigma = length_s / 6
        mu = time_arr[time_arr.size//2]
        result_arr = (amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1) + amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)) * np.exp(-(((time_arr-mu)/sigma)**2)/2)
        return result_arr

    def _triplesingauss(self, time_arr, parameters):
        amp1 = 2*parameters['amplitude1'] #conversion so that the AWG actually outputs the specified voltage
        amp2 = 2*parameters['amplitude2'] #conversion so that the AWG actually outputs the specified voltage
        amp3 = 2*parameters['amplitude3'] #conversion so that the AWG actually outputs the specified voltage
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        freq3 = parameters['frequency3']
        phase1 = np.pi * parameters['phase1'] / 180
        phase2 = np.pi * parameters['phase2'] / 180
        phase3 = np.pi * parameters['phase3'] / 180
        length_s = time_arr[-1]-time_arr[0]
        sigma = length_s / 6
        mu = time_arr[time_arr.size//2]
        result_arr = (amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1) + amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2) + amp3 * np.sin(2*np.pi * freq3 * time_arr + phase3)) * np.exp(-(((time_arr-mu)/sigma)**2)/2)
        return result_arr




