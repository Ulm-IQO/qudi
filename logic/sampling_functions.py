# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware interface for pulsing devices.

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

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
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
        self._math_func['Idle']         = self._idle
        self._math_func['DC']           = self._dc
        self._math_func['Sin']          = self._sin
        self._math_func['Cos']          = self._cos
        self._math_func['DoubleSin']    = self._doublesin
        self._math_func['TripleSin']    = self._triplesin


        # Use ONLY THESE allowed set of parameters for the functions. You can
        # use an arbitrary amount of these parameters in the mathematical
        # functions. If you need a parameter for your mathematical function
        # which cannot be represented by one of the given parameters, ONLY THEN
        # you can extend the list (e.g. a variance parameter for a gaussian
        # function).
        # DO NOT INVENT NEW NAMES FOR ALREADY EXISTING PARAMETERS!
        # (e.g. do not include 'ampl', since 'amplitude' already exists)
        self._allowed_param = ['amplitude', 'frequency', 'phase']

        # Configure also the parameter for the defined functions so that it is
        # know which input parameters the function desires:

        self.func_config = OrderedDict()
        self.func_config['Idle'] = []
        self.func_config['DC'] = {'amplitude': 1}
        self.func_config['Sin'] = {'frequency':1, 'amplitude':1, 'phase':1}
        self.func_config['Cos'] = {'frequency':1, 'amplitude':1, 'phase':1}
        self.func_config['DoubleSin'] = {'frequency'    : 2,
                                         'amplitude'    : 2,
                                         'phase'        : 2}
        self.func_config['TripleSin'] = {'frequency'    : 3,
                                         'amplitude'    : 3,
                                         'phase'        : 3}

        # self.func_config['DoubleSin'] = ['frequency1', 'frequency2',
        #                                  'amplitude1', 'amplitude2',
        #                                  'phase1', 'phase2']
        # self.func_config['TripleSin'] = ['frequency1', 'frequency2',
        #                                  'frequency3', 'amplitude1',
        #                                  'amplitude2', 'amplitude3',
        #                                  'phase1', 'phase2', 'phase3']

        self._validate()


    def _validate(self):
        """ Check whether the function configuration has valid parameters.
        """
        for func in self.func_config:
            for param in self.func_config[func]:
                if param not in self._allowed_param:
                    raise ValueError('Sample Function: Invalid or not known '
                                     'parameter "{0}" for the '
                                     'function "{1}"!'.format(param, func))


    def _idle(self, time_arr, parameters={}):
        result_arr = np.zeros(len(time_arr))
        return result_arr

    def _dc(self, time_arr, parameters):
        amp = parameters['amplitude']
        result_arr = np.full(len(time_arr), amp)
        return result_arr

    def _sin(self, time_arr, parameters):
        amp = parameters['amplitude']
        freq = parameters['frequency']
        phase = 180*np.pi * parameters['phase']
        result_arr = amp * np.sin(2*np.pi * freq * time_arr + phase)
        return result_arr

    def _cos(self, time_arr, parameters):
        amp = parameters['amplitude']
        freq = parameters['frequency']
        phase = 180*np.pi * parameters['phase']
        result_arr = amp * np.cos(2*np.pi * freq * time_arr + phase)
        return result_arr

    def _doublesin(self, time_arr, parameters):
        amp1 = parameters['amplitude1']
        amp2 = parameters['amplitude2']
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        phase1 = 180*np.pi * parameters['phase1']
        phase2 = 180*np.pi * parameters['phase2']
        result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1)
        result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
        return result_arr

    def _triplesin(self, time_arr, parameters):
        amp1 = parameters['amplitude1']
        amp2 = parameters['amplitude2']
        amp3 = parameters['amplitude3']
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        freq3 = parameters['frequency3']
        phase1 = 180*np.pi * parameters['phase1']
        phase2 = 180*np.pi * parameters['phase2']
        phase3 = 180*np.pi * parameters['phase3']
        result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1)
        result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
        result_arr += amp3 * np.sin(2*np.pi * freq3 * time_arr + phase3)
        return result_arr




