# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic for analysis of laser pulses.

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


class PulseAnalyzerBase:
    """
    All analyzer classes to import from must inherit exclusively from this base class.
    This base class enables analyzer classes masked read-only access to settings from
    PulsedMeasurementLogic.

    See BasicPulseAnalyzer class for an example usage.
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


class PulseAnalyzer(PulseAnalyzerBase):
    """
    Management class to automatically combine and interface analysis methods and associated
    parameters from analyzer classes defined in several modules.

    Analyzer class to import from must comply to the following rules:
    1) Exclusive inheritance from PulseAnalyzerBase class
    2) No direct access to PulsedMeasurementLogic instance except through properties defined in
       base class (read-only access)
    3) Analysis methods must be bound instance methods
    4) Analysis methods must be named starting with "analyse_"
    5) Analysis methods must have as first argument "laser_data"
    6) Apart from "laser_data" analysis methods must have exclusively keyword arguments with
       default values of the right data type. (e.g. differentiate between 42 (int) and 42.0 (float))
    7) Make sure that no two analysis methods in any module share a keyword argument of different
       default data type.
    8) The keyword "method" must not be used in the analysis method parameters

    See BasicPulseAnalyzer class for an example usage.
    """

    def __init__(self, pulsedmeasurementlogic):
        # Init base class
        super().__init__(pulsedmeasurementlogic)

        # Dictionary holding references to all analysis methods
        self._analysis_methods = dict()
        # dictionary containing all possible parameters that can be used by the analysis methods
        self._parameters = dict()
        # Currently selected analysis method
        self._current_analysis_method = None

        # import path for analysis modules from default directory (logic.pulse_analysis_methods)
        path_list = [os.path.join(get_main_dir(), 'logic', 'pulsed', 'pulsed_analysis_methods')]
        # import path for analysis modules from non-default directory if a path has been given
        if isinstance(pulsedmeasurementlogic.analysis_import_path, str):
            path_list.append(pulsedmeasurementlogic.analysis_import_path)

        # Import analysis modules and get a list of analyzer classes
        analyzer_classes = self.__import_external_analyzers(paths=path_list)

        # create an instance of each class and put them in a temporary list
        analyzer_instances = [cls(pulsedmeasurementlogic) for cls in analyzer_classes]

        # add references to all analysis methods in each instance to a dict
        self.__populate_method_dict(instance_list=analyzer_instances)

        # populate "_parameters" dictionary from analysis method signatures
        self.__populate_parameter_dict()

        # Set default analysis method
        self._current_analysis_method = natural_sort(self._analysis_methods)[0]

        # Update from parameter_dict if handed over
        if isinstance(pulsedmeasurementlogic.analysis_parameters, dict):
            # Delete unused parameters
            params = [p for p in pulsedmeasurementlogic.analysis_parameters if
                      p not in self._parameters and p != 'method']
            for param in params:
                del pulsedmeasurementlogic.analysis_parameters[param]
            # Update parameter dict and current method
            self.analysis_settings = pulsedmeasurementlogic.analysis_parameters
        return

    @property
    def analysis_settings(self):
        """
        This property holds all parameters needed for the currently selected analysis_method as
        well as the currently selected method name.

        @return dict: dictionary with keys being the parameter name and values being the parameter
        """
        # Get reference to the extraction method
        method = self._analysis_methods.get(self._current_analysis_method)

        # Get keyword arguments for the currently selected method
        settings_dict = self._get_analysis_method_kwargs(method)

        # Attach current analysis method name
        settings_dict['method'] = self._current_analysis_method
        return settings_dict

    @analysis_settings.setter
    def analysis_settings(self, settings_dict):
        """
        Update parameters contained in self._parameters by values in settings_dict.
        Also sets the current analysis method by passing its name using key "method".
        Parameters not included in self._parameters (except "method") will be ignored.

        @param dict settings_dict: dictionary containing the parameters to set (name, value)
        """
        if not isinstance(settings_dict, dict):
            return

        # go through all key-value pairs in settings_dict and update self._parameters and
        # self._current_analysis_method accordingly. Ignore unknown parameters.
        for parameter, value in settings_dict.items():
            if parameter == 'method':
                if value in self._analysis_methods:
                    self._current_analysis_method = value
                else:
                    self.log.error('Analysis method "{0}" could not be found in PulseAnalyzer.'
                                   ''.format(value))
            elif parameter in self._parameters:
                self._parameters[parameter] = value
            else:
                self.log.warning('No analysis parameter "{0}" found in PulseAnalyzer.\n'
                                 'Parameter will be ignored.'.format(parameter))
        return

    @property
    def analysis_methods(self):
        """
        Return available analysis methods.

        @return dict: Dictionary with keys being the method names and values being the methods.
        """
        return self._analysis_methods

    @property
    def full_settings_dict(self):
        """
        Returns the full set of parameters for all methods as well as the currently selected method
        in order to store them in a StatusVar in PulsedMeasurementLogic.

        @return dict: full set of parameters and currently selected analysis method.
        """
        settings_dict = self._parameters.copy()
        settings_dict['method'] = self._current_analysis_method
        return settings_dict

    def analyse_laser_pulses(self, laser_data):
        """
        Wrapper method to call the currently selected analysis method with laser_data and the
        appropriate keyword arguments.

        @param numpy.ndarray laser_data: 2D numpy array (dtype='int64') containing the timetraces
                                         for all extracted laser pulses.
        @return (numpy.ndarray, numpy.ndarray): tuple of two numpy arrays containing the evaluated
                                                signal data (one data point for each laser pulse)
                                                and the measurement error corresponding to each
                                                data point.
        """
        analysis_method = self._analysis_methods[self._current_analysis_method]

        kwargs = self._get_analysis_method_kwargs(analysis_method)
        return analysis_method(laser_data=laser_data, **kwargs)

    def _get_analysis_method_kwargs(self, method):
        """
        Get the proper values for keyword arguments other than "laser_data" for <method>.
        Try to take the values from self._parameters. If the keyword is missing in the dictionary,
        take the default values from the method signature.

        @param method: reference to a callable analysis method
        @return dict: A dictionary containing the argument keywords for <method> and corresponding
                      values from self._parameters.
        """
        kwargs_dict = dict()
        method_signature = inspect.signature(method)
        for name in method_signature.parameters.keys():
            if name == 'laser_data':
                continue

            default = method_signature.parameters[name].default
            recalled = self._parameters.get(name)

            if recalled is not None and type(recalled) == type(default):
                kwargs_dict[name] = recalled
            else:
                kwargs_dict[name] = default
        return kwargs_dict

    def __import_external_analyzers(self, paths):
        """
        Helper method to import all modules from directories contained in paths.
        Find all classes in those modules that inherit exclusively from PulseAnalyzerBase class
        and return a list of them.

        @param iterable paths: iterable containing paths to import modules from
        @return list: A list of imported valid analyzer classes
        """
        class_list = list()
        for path in paths:
            if not os.path.exists(path):
                self.log.error('Unable to import analysis methods from "{0}".\n'
                               'Path does not exist.'.format(path))
                continue
            # Get all python modules to import from.
            # The assumption is that in the directory pulse_analysis_methods, there are
            # *.py files, which contain only analyzer classes!
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
                # get all analyzer class references defined in the module
                tmp_list = [m[1] for m in inspect.getmembers(mod, self.__is_analyzer_class)]
                # append to class_list
                class_list.extend(tmp_list)
        return class_list

    def __populate_method_dict(self, instance_list):
        """
        Helper method to populate the dictionaries containing all references to callable analysis
        methods contained in analyzer instances passed to this method.

        @param list instance_list: List containing instances of analyzer classes
        """
        self._analysis_methods = dict()
        for instance in instance_list:
            for method_name, method_ref in inspect.getmembers(instance, inspect.ismethod):
                if method_name.startswith('analyse_'):
                    self._analysis_methods[method_name[8:]] = method_ref
        return

    def __populate_parameter_dict(self):
        """
        Helper method to populate the dictionary containing all possible keyword arguments from all
        analysis methods.
        """
        self._parameters = dict()
        for method in self._analysis_methods.values():
            self._parameters.update(self._get_analysis_method_kwargs(method=method))
        return

    @staticmethod
    def __is_analyzer_class(obj):
        """
        Helper method to check if an object is a valid analyzer class.

        @param object obj: object to check
        @return bool: True if obj is a valid analyzer class, False otherwise
        """
        if inspect.isclass(obj):
            return PulseAnalyzerBase in obj.__bases__ and len(obj.__bases__) == 1
        return False
