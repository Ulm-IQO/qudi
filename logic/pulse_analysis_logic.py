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

import importlib
import inspect
import numpy as np
import os

from collections import OrderedDict
from core.module import StatusVar
from core.util.modules import get_main_dir
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class PulseAnalysisLogic(GenericLogic):
    """unstable: Nikolas Tomek  """

    _modclass = 'PulseAnalysisLogic'
    _modtype = 'logic'

    sigAnalysisSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisMethodsUpdated = QtCore.Signal(dict)

    # The currently chosen analysis method
    current_analysis_method = StatusVar(default='mean_norm')

    # Parameters used by all or some analysis methods.
    # The keywords for the function arguments must be the same as these variable names.
    # If you add new parameters, make sure you include them in the analysis_settings property below.
    signal_start = StatusVar(default=0.0)
    signal_end = StatusVar(default=200.0e-9)
    norm_start = StatusVar(default=300.0e-9)
    norm_end = StatusVar(default=500.0e-9)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Dictionary container holding information about the currently running sequence
        self.sequence_information = None
        # The width of a single time bin in the count data in seconds
        self.counter_bin_width = 1e-9
        # Dictionary holding references to the analysis methods
        self.analysis_methods = None
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.analysis_methods = OrderedDict()
        filename_list = []
        # The assumption is that in the directory pulsed_analysis_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(get_main_dir(), 'logic', 'pulsed_analysis_methods')
        for entry in os.listdir(path):
            if os.path.isfile(os.path.join(path, entry)) and entry.endswith('.py'):
                filename_list.append(entry[:-3])

        for filename in filename_list:
            mod = importlib.import_module('logic.pulsed_analysis_methods.{0}'.format(filename))
            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if method.startswith('analyse_') and callable(ref) and (
                            inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(PulseAnalysisLogic, method, staticmethod(ref))
                        # Add method to dictionary if it is a generator method
                        self.analysis_methods[method[8:]] = getattr(self, method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'PulseAnalysisLogic.'.format(method, filename))
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    @property
    def analysis_settings(self):
        """
        This property holds all parameters needed for the currently selected analysis_method.

        @return dict:
        """
        # Get reference to the analysis method
        method = self.analysis_methods.get(self.current_analysis_method)
        # Get keyword arguments for the analysis method
        settings_dict = self._get_analysis_method_kwargs(method)
        # Remove arguments that have a corresponding attribute defined in __init__
        for parameter in ('counter_bin_width', 'sequence_information'):
            if parameter in settings_dict:
                del settings_dict[parameter]
        # Attach current analysis method name
        settings_dict['current_analysis_method'] = self.current_analysis_method
        return settings_dict

    @analysis_settings.setter
    def analysis_settings(self, settings_dict):
        for name, value in settings_dict.items():
            if not hasattr(self, name):
                self.log.warning('No analysis setting "{0}" found in PulseAnalysisLogic.\n'
                                 'Creating it now but this can lead to problems.\nThis parameter '
                                 'is probably not part of any analysis method.'.format(name))

            if name == 'laser_data':
                pass
            else:
                setattr(self, name, value)

        # emit signal with all important parameters for the currently selected analysis method
        self.sigAnalysisSettingsUpdated.emit(self.analysis_settings)
        return

    def analyze_data(self, laser_data):
        """ Analysis the laser pulses and computes the measuring error given by photon shot noise

        @param numpy.ndarray (int) laser_data: 2D array containing the extracted laser countdata

        @return: float array signal_data: Array with the computed signal
        @return: float array measuring_error: Array with the computed signal error
        """
        # convert time to bin
        # self.signal_start_bin = round(self.analysis_settings['signal_start_s'] / self.fast_counter_binwidth)
        # self.signal_end_bin = round(self.analysis_settings['signal_end_s'] / self.fast_counter_binwidth)
        # self.norm_start_bin = round(self.analysis_settings['norm_start_s'] / self.fast_counter_binwidth)
        # self.norm_end_bin = round(self.analysis_settings['norm_end_s'] / self.fast_counter_binwidth)
        analysis_method = self.analysis_methods[self.current_analysis_method]
        kwargs = self._get_analysis_method_kwargs(analysis_method)
        return analysis_method(laser_data, **kwargs)

    def _get_analysis_method_kwargs(self, method):
        """
        Get the proper values for keyword arguments other than "count_data" for <method> from this
        classes attributes.

        @param method: reference to a callable analysis method
        @return dict: A dictionary containing the argument keywords for <method> and corresponding
                      values from PulseAnalysisLogic attributes.
        """
        # Sanity checking
        if not callable(method) or not (inspect.ismethod(method) or inspect.isfunction(method)):
            self.log.error('Method "_get_analysis_method_kwargs" needs a reference to a callable '
                           'method but instead received "{0}"'.format(type(method)))
            return dict()

        kwargs_dict = dict()
        method_signature = inspect.signature(method)
        for name in method_signature.parameters.keys():
            if name == 'laser_data':
                pass
            elif hasattr(self, name):
                kwargs_dict[name] = getattr(self, name)
            else:
                kwargs_dict[name] = method_signature.parameters[name].default
                self.log.warning('Parameter "{0}" for analysis method "{1}" is no attribute of '
                                 'PulseAnalysisLogic.\nTaking default value of "{2}" instead.'
                                 ''.format(name, method.__name__, kwargs_dict[name]))
        return kwargs_dict
