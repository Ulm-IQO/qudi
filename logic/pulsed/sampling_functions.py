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

import os
import importlib
import sys
import inspect
import copy
import logging
import numpy as np
from collections import OrderedDict
import enum
from enum import Enum

##############################################################
# Helper class for everything that need dynamical decoupling #
##############################################################

class DDMethodsHelper():
    @staticmethod
    def get_phases(seq):
        if type(seq) == dict:
            _phases = list(seq.values())[0]
        else:
            _phases = seq
        return _phases

    @staticmethod
    def get_ampl_scale(dd_method):
        seq = dd_method.value
        _ampls = np.ones(len(dd_method.phases))
        if type(seq) == dict:
            if 'scale_ampl' in seq.keys():
                _ampls = seq['scale_ampl']
        return _ampls

@enum.unique
class DDMethods(Enum):

    # define a function to nest the phases of sequence 1 into sequence 2
    def nest_phases_function(xseq1, xseq2):
        xseq1 = DDMethodsHelper.get_phases(xseq1)
        xseq2 = DDMethodsHelper.get_phases(xseq2)
        return [((xseq1[j] + xseq2[k]) % 360.) for k in range(len(xseq2)) for j in range(len(xseq1))]


    # define a function to calculate the phases of the UR sequences,
    # reference: DOI:https://doi.org/10.1103/PhysRevLett.118.133202
    def ur_phases_function(xn):

        # define phi_large, depending on the number of pulses in the UR sequence
        if xn % 4 == 0:
            phi_large = 720. / xn
        elif xn % 4 == 2:
            phi_large = 180. * (xn - 2) / xn
        else:
            phi_large = 0.
            print("Error: the UR sequence can only have an even number of pulses")
        # formula for the UR sequences phases, we round the degrees to the 8th digit to avoid some small machine
        # numbers in the phases when calculated from the formula but such rounding is in principle not necessary
        ur_phases_array = [(round(k * ((k - 1) * phi_large / 2 + phi_large) % 360., 8)) for k in range(xn)]
        return ur_phases_array



    # # define a function to compare the phases of sequence 1 and sequence 2, useful for testing after uncommenting
    # def compare_phases_function(xseq1, xseq2):
    #     return [((xseq1[k] - xseq2[k]) % 360.) for k in range(len(xseq2))]


    # define phases of pi decoupling pulses
    # to differentiate same phases for different DD, use dicts with unique keys
    SE = [0., ]
    SE2 = [0., 0.]
    CPMG = [90., 90.]

    XY4 = {0: [0., 90., 0., 90.]}
    XY4_leave_2i = [0., float('nan'), 90., float('nan')]
    XY4_leave_3i = [0., 90 ,  float('nan'), 0]
    XY4_skip_01_04_06 = [0., np.nan, 90., 0., np.nan, 90., np.nan]
    XY8 = [0., 90., 0., 90., 90., 0., 90., 0.]
    XY8_leave_2i = [0., float('nan'), 90., float('nan'), 0., float('nan'), 90., float('nan'),
                    90., float('nan'), 0., float('nan'), 90., float('nan'), 0.]
    XY16 = [0., 90., 0., 90., 90., 0., 90., 0., 180., -90., 180., -90., -90., 180., -90., 180.]
    YY8 = [-90., 90., 90., -90., -90., -90., 90., 90.]
    KDD = [30., 0., 90., 0., 30.]  # composite pulse (CP) for population inversion, U5b shifted by 30 degrees

    KDD2 = nest_phases_function(KDD, SE2)
    KDD4 = nest_phases_function(KDD, XY4)
    KDD8 = nest_phases_function(KDD, XY8)
    KDD16 = nest_phases_function(KDD, XY16)

    PPol_up = {0: [90., 0., 90., 0.]}
    PPol_down = [360., 450., 360., 450.]

    # for Double Quantum transition
    DQT_XY16 = [90, 0, 90, 0, 0, 90, 0, 90, -90, -180, -90, -180, -180, -90, -180, -90]  # Mamin (2014)

    # 2x NV composite pulses
    MW_DD_XY3 = [90, 0, 90]
    MW_DD_SE8 = [0, 0, 0, 0, 0, 0, 0, 0]
    MW_DD_XY4s = {1: [0., 90., 0., 90.]}
    MW_DD_XY4s_2nd = {1: [90., 0., 90., 0.]}
    MW_DD_XY4s_leave_02 = [np.nan, 0, np.nan, np.nan]
    MW_DD_XY4s_leave_02_2nd = [90, 0, 90, np.nan]
    MW_DD_XY4s_scale_02_2x =     {0: [0, 0, 90, np.nan], 'scale_ampl': [1, 2, 1, 1]}
    MW_DD_XY4s_scale_02_2x_2nd = {1: [0, 0, 90, np.nan], 'scale_ampl': [1, 2, 1, 1]}
    MW_DD_XY4s_skip_01_04_06 = {1: [0., np.nan, 90., 0., np.nan, 90., np.nan]}
    MW_DD_XY4s_skip_01_04_06_2nd = {1: [np.nan, 90., np.nan, 0, 90., np.nan, 0]}

    # define the specific UR sequences to use, reference: DOI:https://doi.org/10.1103/PhysRevLett.118.133202
    UR4 = ur_phases_function(4)
    UR6 = ur_phases_function(6)
    UR8 = ur_phases_function(8)
    UR10 = ur_phases_function(10)
    UR12 = ur_phases_function(12)
    UR14 = ur_phases_function(14)

    UR16 = ur_phases_function(16)
    UR18 = ur_phases_function(18)
    UR20 = ur_phases_function(20)
    UR40 = ur_phases_function(40)
    UR80 = ur_phases_function(80)
    UR100 = ur_phases_function(100)

    def __init__(self, phases):
        self._phases = DDMethodsHelper.get_phases(phases)

    @property
    def suborder(self):
        return len(self._phases)

    @property
    def phases(self):
        return np.array(self._phases)

    @property
    def scale_ampl(self):
        return DDMethodsHelper.get_ampl_scale(self)

    @property
    def dd_after_mwx(self):
        """
        For use in arbitrary (x) gates embedded in dd_x_dd decoupling.
        Allows to set another DD in 2nd half of composite pulse.
        """
        after_x = {DDMethods.MW_DD_XY4s: DDMethods.MW_DD_XY4s_2nd,
                   DDMethods.MW_DD_XY4s_leave_02: DDMethods.MW_DD_XY4s_leave_02_2nd,
                   DDMethods.MW_DD_XY4s_scale_02_2x: DDMethods.MW_DD_XY4s_scale_02_2x_2nd,
                   DDMethods.MW_DD_XY4s_skip_01_04_06: DDMethods.MW_DD_XY4s_skip_01_04_06_2nd}

        if self in after_x.keys():
            return after_x[self]
        else:
            return self

class SamplingBase:
    """
    Base class for all sampling functions
    """
    params = OrderedDict()
    log = logging.getLogger(__name__)

    def __repr__(self):
        kwargs = []
        for param, def_dict in self.params.items():
            if def_dict['type'] is str:
                kwargs.append('{0}=\'{1}\''.format(param, getattr(self, param)))
            else:
                kwargs.append('{0}={1}'.format(param, getattr(self, param)))
        return '{0}({1})'.format(type(self).__name__, ', '.join(kwargs))

    def __str__(self):
        kwargs = ('='.join((param, str(getattr(self, param)))) for param in self.params)
        return_str = 'Sampling Function: "{0}"\nParameters:'.format(type(self).__name__)
        if len(self.params) < 1:
            return_str += ' None'
        else:
            return_str += '\n\t' + '\n\t'.join(kwargs)
        return return_str

    def __eq__(self, other):
        if not isinstance(other, SamplingBase):
            return False
        hash_list = [type(self).__name__]
        for param in self.params:
            hash_list.append(getattr(self, param))
        hash_self = hash(tuple(hash_list))
        hash_list = [type(other).__name__]
        for param in other.params:
            hash_list.append(getattr(other, param))
        hash_other = hash(tuple(hash_list))
        return hash_self == hash_other

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['name'] = type(self).__name__
        dict_repr['params'] = dict()
        for param in self.params:
            dict_repr['params'][param] = getattr(self, param)
        return dict_repr

class SamplingFunctions:
    """

    """
    parameters = dict()

    @classmethod
    def import_sampling_functions(cls, path_list):
        param_dict = dict()
        for path in path_list:
            if not os.path.exists(path):
                continue
            # Get all python modules to import from.
            module_list = [name[:-3] for name in os.listdir(path) if
                           os.path.isfile(os.path.join(path, name)) and name.endswith('.py')]

            # append import path to sys.path
            if path not in sys.path:
                sys.path.append(path)

            # Go through all modules and get all sampling function classes.
            for module_name in module_list:
                # import module
                mod = importlib.import_module('{0}'.format(module_name))
                # Delete all remaining references to sampling functions.
                # This is neccessary if you have removed a sampling function class.
                for attr in cls.parameters:
                    if hasattr(mod, attr):
                        delattr(mod, attr)
                importlib.reload(mod)
                # get all sampling function class references defined in the module
                for name, ref in inspect.getmembers(mod, cls.is_sampling_function_class):
                    setattr(cls, name, cls.__get_sf_method(ref))
                    param_dict[name] = copy.deepcopy(ref.params)

        # Remove old sampling functions
        for func in cls.parameters:
            if func not in param_dict:
                delattr(cls, func)

        cls.parameters = param_dict
        return

    @staticmethod
    def __get_sf_method(sf_ref):
        return lambda *args, **kwargs: sf_ref(*args, **kwargs)

    @staticmethod
    def is_sampling_function_class(obj):
        """
        Helper method to check if an object is a valid sampling function class.

        @param object obj: object to check
        @return bool: True if obj is a valid sampling function class, False otherwise
        """
        if inspect.isclass(obj):
            return SamplingBase in inspect.getmro(obj) and object not in obj.__bases__
        return False
