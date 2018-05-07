# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic for the extraction of laser pulses.

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
import inspect
import sys

from core.util.modules import get_main_dir


class PulseExtractorBase:
    """

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

    """
    # Parameters used by all or some extraction methods.
    # The keywords for the function arguments must be the same as these variable names.
    # If you define a new extraction method you can use two different kinds of parameters:
    # 1) The parameters defined in the __init__ of this module.
    #    These must be non-optional arguments.
    # 2) The StatusVars of this module. These parameters are optional arguments in your method
    #    definition with default values. If you need to define a new parameter, you must add it to
    #    these modules' StatusVars (with the same name as the argument keyword)
    # Make sure that you define static methods, i.e. do not make use of something like "self.<name>"
    # If you have properly defined your extraction method and added all parameters to this module
    # the PulsedMainGui should automatically generate the appropriate elements.

    def __init__(self, pulsedmeasurementlogic, parameter_dict=None, import_path=None):
        # Init base class
        super().__init__(pulsedmeasurementlogic)

        # import path for extraction modules from default directory (logic.pulse_extraction_methods)
        path_list = [os.path.join(get_main_dir(), 'logic', 'pulse_extraction_methods')]
        # import path for extraction modules from non-default directory if a path has been given
        if isinstance(import_path, str):
            path_list.append(import_path)

        # Dictionaries holding references to the extraction methods
        self._gated_extraction_methods = dict()
        self._ungated_extraction_methods = dict()
        # Import extraction modules, create instances of these classes and add method references of
        # extraction methods to dictionaries defined above
        self.__import_external_extractors(paths=path_list,
                                          pulsedmeasurementlogic=pulsedmeasurementlogic)

        # dictionary containing all possible parameters that can be used by the extraction methods
        self._parameters = dict()
        # populate "_parameters" dictionary from extraction method signatures
        self._populate_parameter_dict()

        # Currently selected extraction method
        if self.is_gated:
            self._current_extraction_method = sorted(self._gated_extraction_methods)[0]
        else:
            self._current_extraction_method = sorted(self._ungated_extraction_methods)[0]

        # Update from parameter_dict if handed over
        if isinstance(parameter_dict, dict):
            # Delete unused parameters
            invalid = [p for p in parameter_dict if p not in self._parameters and p != 'method']
            for param in invalid:
                del parameter_dict[param]
            # Update parameter dict and current method
            self.extraction_settings = parameter_dict
        return

    @property
    def extraction_settings(self):
        """
        This property holds all parameters needed for the currently selected extraction_method.

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
        if not isinstance(settings_dict, dict):
            return

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
        if self.is_gated:
            return self._gated_extraction_methods
        else:
            return self._ungated_extraction_methods

    @property
    def full_settings_dict(self):
        settings_dict = self._parameters.copy()
        settings_dict['method'] = self._current_extraction_method
        return settings_dict

    def extract_laser_pulses(self, count_data):
        """

        @param count_data:
        @return:
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

    def _populate_parameter_dict(self):
        """

        @return:
        """
        self._parameters = dict()
        for method in self._ungated_extraction_methods.values():
            self._parameters.update(self._get_extraction_method_kwargs(method=method))
        return

    def _get_extraction_method_kwargs(self, method):
        """
        Get the proper values for keyword arguments other than "count_data" for <method>.
        Try to take the values from self._parameters dictionary. If the keyword is missing in the
        dictionary, take the default values from the method signature.

        @param method: reference to a callable extraction method
        @return dict: A dictionary containing the argument keywords for <method> and corresponding
                      values from PulseExtractionLogic attributes.
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

    def __import_external_extractors(self, paths, pulsedmeasurementlogic):
        """
        """
        if not isinstance(paths, (list, tuple, set)):
            return

        extractor_instances = list()
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
            sys.path.append(path)

            # Go through all modules and create instances of each class found.
            for module_name in module_list:
                # import module
                module = importlib.import_module('{0}'.format(module_name))
                importlib.reload(module)
                # get all class names defined in the module
                class_list = [m[0] for m in inspect.getmembers(module, inspect.isclass) if
                              m[1].__module__ == module_name]
                for class_name in class_list:
                    class_ref = getattr(module, class_name)
                    class_inst = class_ref(pulsedmeasurementlogic)
                    extractor_instances.append(class_inst)

        # add references to all extraction methods in the class to a dict
        self.__get_extraction_methods(instance_list=extractor_instances)
        return

    def __get_extraction_methods(self, instance_list):
        """

        @return:
        """
        for instance in instance_list:
            for method_name, method_ref in inspect.getmembers(instance, predicate=inspect.ismethod):
                if method_name.startswith('gated_'):
                    self._gated_extraction_methods[method_name[6:]] = method_ref
                elif method_name.startswith('ungated_'):
                    self._ungated_extraction_methods[method_name[8:]] = method_ref
        return
