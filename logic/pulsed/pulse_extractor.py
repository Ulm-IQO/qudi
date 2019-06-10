# -*- coding: utf-8 -*-
"""
This file contains the Qudi helper classes for the extraction of laser pulses.

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
import sys
import inspect
import importlib

from core.util.modules import get_main_dir
from core.util.helpers import natural_sort


class PulseExtractorBase:
    """
    All extractor classes to import from must inherit exclusively from this base class.
    This base class enables extractor classes masked read-only access to settings from
    PulsedMeasurementLogic.

    See BasicPulseExtractor class for an example usage.
    """
    def __init__(self, pulsedmeasurementlogic):
        self.__pulsedmeasurementlogic = pulsedmeasurementlogic

    @property
    def is_gated(self):
        return self.__pulsedmeasurementlogic.fast_counter_settings.get('is_gated')

    @property
    def measurement_settings(self):
        return self.__pulsedmeasurementlogic.measurement_settings

    @property
    def sampling_information(self):
        return self.__pulsedmeasurementlogic.sampling_information

    @property
    def fast_counter_settings(self):
        return self.__pulsedmeasurementlogic.fast_counter_settings

    @property
    def log(self):
        return self.__pulsedmeasurementlogic.log


class PulseExtractor(PulseExtractorBase):
    """
    Management class to automatically combine and interface extraction methods and associated
    parameters from extractor classes defined in several modules.

    Extractor class to import from must comply to the following rules:
    1) Exclusive inheritance from PulseExtractorBase class
    2) No direct access to PulsedMeasurementLogic instance except through properties defined in
       base class (read-only access)
    3) Extraction methods must be bound instance methods
    4) Extraction methods must be named starting with "ungated_" or "gated_" accordingly
    5) Extraction methods must have as first argument "count_data"
    6) Apart from "count_data" extraction methods must have exclusively keyword arguments with
       default values of the right data type. (e.g. differentiate between 42 (int) and 42.0 (float))
    7) Make sure that no two extraction methods in any module share a keyword argument of different
       default data type.
    8) The keyword "method" must not be used in the extraction method parameters

    See BasicPulseExtractor class for an example usage.
    """

    def __init__(self, pulsedmeasurementlogic):
        # Init base class
        super().__init__(pulsedmeasurementlogic)

        # Dictionaries holding references to the extraction methods
        self._gated_extraction_methods = dict()
        self._ungated_extraction_methods = dict()
        # dictionary containing all possible parameters that can be used by the extraction methods
        self._parameters = dict()
        # Currently selected extraction method
        self._current_extraction_method = None

        # import path for extraction modules from default directory (logic.pulse_extraction_methods)
        path_list = [os.path.join(get_main_dir(), 'logic', 'pulsed', 'pulse_extraction_methods')]
        # import path for extraction modules from non-default directory if a path has been given
        if isinstance(pulsedmeasurementlogic.extraction_import_path, str):
            path_list.append(pulsedmeasurementlogic.extraction_import_path)

        # Import extraction modules and get a list of extractor classes
        extractor_classes = self.__import_external_extractors(paths=path_list)

        # create an instance of each class and put them in a temporary list
        extractor_instances = [cls(pulsedmeasurementlogic) for cls in extractor_classes]

        # add references to all extraction methods in each instance to a dict
        self.__populate_method_dicts(instance_list=extractor_instances)

        # populate "_parameters" dictionary from extraction method signatures
        self.__populate_parameter_dict()

        # Set default extraction method
        if self.is_gated:
            self._current_extraction_method = natural_sort(self._gated_extraction_methods)[0]
        else:
            self._current_extraction_method = natural_sort(self._ungated_extraction_methods)[0]

        # Update from parameter_dict if handed over
        if isinstance(pulsedmeasurementlogic.extraction_parameters, dict):
            # Delete unused parameters
            params = [p for p in pulsedmeasurementlogic.extraction_parameters if
                      p not in self._parameters and p != 'method']
            for param in params:
                del pulsedmeasurementlogic.extraction_parameters[param]
            # Update parameter dict and current method
            self.extraction_settings = pulsedmeasurementlogic.extraction_parameters
        return

    @property
    def extraction_settings(self):
        """
        This property holds all parameters needed for the currently selected extraction_method as
        well as the currently selected method name.

        @return dict: dictionary with keys being the parameter name and values being the parameter
        """
        # Get reference to the extraction method
        if self.is_gated:
            method = self._gated_extraction_methods.get(self._current_extraction_method)
        else:
            method = self._ungated_extraction_methods.get(self._current_extraction_method)

        # Get keyword arguments for the currently selected method
        settings_dict = self._get_extraction_method_kwargs(method)

        # Attach current extraction method name
        settings_dict['method'] = self._current_extraction_method
        return settings_dict

    @extraction_settings.setter
    def extraction_settings(self, settings_dict):
        """
        Update parameters contained in self._parameters by values in settings_dict.
        Also sets the current extraction method by passing its name using key "method".
        Parameters not included in self._parameters (except "method") will be ignored.

        @param dict settings_dict: dictionary containing the parameters to set (name, value)
        """
        if not isinstance(settings_dict, dict):
            return

        # go through all key-value pairs in settings_dict and update self._parameters and
        # self._current_extraction_method accordingly. Ignore unknown parameters.
        for parameter, value in settings_dict.items():
            if parameter == 'method':
                if (value in self._gated_extraction_methods and self.is_gated) or (
                        value in self._ungated_extraction_methods and not self.is_gated):
                    self._current_extraction_method = value
                else:
                    self.log.error('Extraction method "{0}" could not be found in PulseExtractor.'
                                   ''.format(value))
            elif parameter in self._parameters:
                self._parameters[parameter] = value
            else:
                self.log.warning('No extraction parameter "{0}" found in PulseExtractor.\n'
                                 'Parameter will be ignored.'.format(parameter))
        return

    @property
    def extraction_methods(self):
        """
        Return available extraction methods depending on if the fast counter is gated or not.

        @return dict: Dictionary with keys being the method names and values being the methods.
        """
        if self.is_gated:
            return self._gated_extraction_methods
        else:
            return self._ungated_extraction_methods

    @property
    def full_settings_dict(self):
        """
        Returns the full set of parameters for all methods as well as the currently selected method
        in order to store them in a StatusVar in PulsedMeasurementLogic.

        @return dict: full set of parameters and currently selected extraction method.
        """
        settings_dict = self._parameters.copy()
        settings_dict['method'] = self._current_extraction_method
        return settings_dict

    def extract_laser_pulses(self, count_data):
        """
        Wrapper method to call the currently selected extraction method with count_data and the
        appropriate keyword arguments.

        @param numpy.ndarray count_data: 1D (ungated) or 2D (gated) numpy array (dtype='int64')
                                         containing the timetrace to extract laser pulses from.
        @return dict: result dictionary of the extraction method
        """
        if count_data.ndim > 1 and not self.is_gated:
            self.log.error('"is_gated" flag is set to False but the count data to extract laser '
                           'pulses from is in the format of a gated timetrace (2D numpy array).')
        elif count_data.ndim == 1 and self.is_gated:
            self.log.error('"is_gated" flag is set to True but the count data to extract laser '
                           'pulses from is in the format of an ungated timetrace (1D numpy array).')

        if self.is_gated:
            extraction_method = self._gated_extraction_methods[self._current_extraction_method]
        else:
            extraction_method = self._ungated_extraction_methods[self._current_extraction_method]
        kwargs = self._get_extraction_method_kwargs(extraction_method)
        return extraction_method(count_data=count_data, **kwargs)

    def _get_extraction_method_kwargs(self, method):
        """
        Get the proper values for keyword arguments other than "count_data" for <method>.
        Try to take the values from self._parameters. If the keyword is missing in the dictionary,
        take the default values from the method signature.

        @param method: reference to a callable extraction method
        @return dict: A dictionary containing the argument keywords for <method> and corresponding
                      values from self._parameters.
        """
        kwargs_dict = dict()
        method_signature = inspect.signature(method)
        for name in method_signature.parameters.keys():
            if name == 'count_data':
                continue

            default = method_signature.parameters[name].default
            recalled = self._parameters.get(name)

            if recalled is not None and type(recalled) == type(default):
                kwargs_dict[name] = recalled
            else:
                kwargs_dict[name] = default
        return kwargs_dict

    def __import_external_extractors(self, paths):
        """
        Helper method to import all modules from directories contained in paths.
        Find all classes in those modules that inherit exclusively from PulseExtractorBase class
        and return a list of them.

        @param iterable paths: iterable containing paths to import modules from
        @return list: A list of imported valid extractor classes
        """
        class_list = list()
        for path in paths:
            if not os.path.exists(path):
                self.log.error('Unable to import extraction methods from "{0}".\n'
                               'Path does not exist.'.format(path))
                continue
            # Get all python modules to import from.
            # The assumption is that in the directory pulse_extraction_methods, there are
            # *.py files, which contain only extractor classes!
            module_list = [name[:-3] for name in os.listdir(path) if
                           os.path.isfile(os.path.join(path, name)) and name.endswith('.py')]

            # append import path to sys.path
            if path not in sys.path:
                sys.path.append(path)

            # Go through all modules and create instances of each class found.
            for module_name in module_list:
                # import module
                mod = importlib.import_module('{0}'.format(module_name))
                importlib.reload(mod)
                # get all extractor class references defined in the module
                tmp_list = [m[1] for m in inspect.getmembers(mod, self.is_extractor_class)]
                # append to class_list
                class_list.extend(tmp_list)
        return class_list

    def __populate_method_dicts(self, instance_list):
        """
        Helper method to populate the dictionaries containing all references to callable extraction
        methods contained in extractor instances passed to this method.

        @param list instance_list: List containing instances of extractor classes
        """
        self._ungated_extraction_methods = dict()
        self._gated_extraction_methods = dict()
        for instance in instance_list:
            for method_name, method_ref in inspect.getmembers(instance, inspect.ismethod):
                if method_name.startswith('gated_'):
                    self._gated_extraction_methods[method_name[6:]] = method_ref
                elif method_name.startswith('ungated_'):
                    self._ungated_extraction_methods[method_name[8:]] = method_ref
        return

    def __populate_parameter_dict(self):
        """
        Helper method to populate the dictionary containing all possible keyword arguments from all
        extraction methods.
        """
        self._parameters = dict()
        for method in self._ungated_extraction_methods.values():
            self._parameters.update(self._get_extraction_method_kwargs(method=method))
        for method in self._gated_extraction_methods.values():
            self._parameters.update(self._get_extraction_method_kwargs(method=method))
        return

    @staticmethod
    def is_extractor_class(obj):
        """
        Helper method to check if an object is a valid extractor class.

        @param object obj: object to check
        @return bool: True if obj is a valid extractor class, False otherwise
        """
        if inspect.isclass(obj):
            return PulseExtractorBase in obj.__bases__ and len(obj.__bases__) == 1
        return False
