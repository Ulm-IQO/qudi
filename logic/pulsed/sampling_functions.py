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
from collections import OrderedDict


class SamplingBase:
    """
    Base class for all sampling functions
    """
    params = OrderedDict()

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['name'] = self.__class__.__name__
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
            return SamplingBase in obj.__bases__ and len(obj.__bases__) == 1
        return False
