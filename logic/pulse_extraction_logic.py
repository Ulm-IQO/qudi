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

from qtpy import QtCore
from collections import OrderedDict
from core.module import StatusVar
from core.util.modules import get_main_dir
from logic.generic_logic import GenericLogic


class PulseExtractionLogic(GenericLogic):
    """

    """
    _modclass = 'PulseExtractionLogic'
    _modtype = 'logic'

    sigExtractionSettingsUpdated = QtCore.Signal(dict)

    # The currently chosen extraction method
    current_extraction_method = StatusVar(default='conv_deriv')

    # Parameters used by all or some extraction methods.
    # The keywords for the function arguments must be the same as these variable names.
    # If you add new parameters, make sure you include them in the extraction_settings property
    # below.
    conv_std_dev = StatusVar(default=20.0)
    count_threshold = StatusVar(default=10)
    min_laser_length = StatusVar(default=200e-9)
    threshold_tolerance = StatusVar(default=20e-9)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # The width of a single time bin in the count data in seconds
        self.counter_bin_width = 1e-9
        # Flag indicating if the count data comes from a gated counter (True) or not (False)
        self.is_gated = False
        # The number of laser pulses to find in the time trace
        self.number_of_lasers = 50
        # Dictionary container holding information about the currently running sequence
        self.sequence_information = None
        # Dictionaries holding references to the extraction methods
        self.gated_extraction_methods = None
        self.ungated_extraction_methods = None
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.gated_extraction_methods = OrderedDict()
        self.ungated_extraction_methods = OrderedDict()

        # Get all python modules to import from.
        # The assumption is that in the directory pulse_extraction_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(get_main_dir(), 'logic', 'pulse_extraction_methods')
        filename_list = [name[:-3] for name in os.listdir(path) if
                         os.path.isfile(os.path.join(path, name)) and name.endswith('.py')]

        for filename in filename_list:
            mod = importlib.import_module('logic.pulse_extraction_methods.{0}'.format(filename))
            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if method.startswith(('gated_', 'ungated_')) and callable(ref) and (
                            inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(PulseExtractionLogic, method, staticmethod(ref))
                        # Add method to appropriate dictionary
                        if method.startswith('gated_'):
                            self.gated_extraction_methods[method[6:]] = getattr(self, method)
                        elif method.startswith('ungated_'):
                            self.ungated_extraction_methods[method[8:]] = getattr(self, method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'PulseExtractionLogic.'.format(method, filename))
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    @property
    def extraction_settings(self):
        """
        This property holds all parameters needed for the currently selected extraction_method.

        @return dict:
        """
        # Get reference to the extraction method
        if self.is_gated:
            method = self.gated_extraction_methods.get(self.current_extraction_method)
        else:
            method = self.ungated_extraction_methods.get(self.current_extraction_method)
        # Get keyword arguments for the currently selected method
        settings_dict = self._get_extraction_method_kwargs(method)
        # Remove arguments that have a corresponding attribute defined in __init__
        for parameter in ('counter_bin_width', 'number_of_lasers', 'sequence_information'):
            if parameter in settings_dict:
                del settings_dict[parameter]
        # Attach current extraction method name
        settings_dict['current_extraction_method'] = self.current_extraction_method
        return settings_dict

    @extraction_settings.setter
    def extraction_settings(self, settings_dict):
        for name, value in settings_dict.items():
            if not hasattr(self, name):
                self.log.warning('No extraction setting "{0}" found in PulseExtractionLogic.\n'
                                 'Creating it now but this can lead to problems.\nThis parameter '
                                 'is probably not part of any extraction method.'.format(name))
            if name != 'count_data':
                setattr(self, name, value)

        # emit signal with all important parameters for the currently selected analysis method
        self.sigExtractionSettingsUpdated.emit(self.extraction_settings)
        return

    def extract_laser_pulses(self, count_data):
        """

        @param count_data:
        @return:
        """
        if len(count_data.shape) > 1 and not self.is_gated:
            self.log.error('"is_gated" flag is set to False but the count data to extract laser '
                           'pulses from is in the format of a gated timetrace (2D numpy array).')
        elif len(count_data.shape) == 1 and self.is_gated:
            self.log.error('"is_gated" flag is set to True but the count data to extract laser '
                           'pulses from is in the format of an ungated timetrace (1D numpy array).')
        if self.is_gated:
            extraction_method = self.gated_extraction_methods[self.current_extraction_method]
        else:
            extraction_method = self.ungated_extraction_methods[self.current_extraction_method]
        kwargs = self._get_extraction_method_kwargs(extraction_method)
        return extraction_method(count_data, **kwargs)

    def _get_extraction_method_kwargs(self, method):
        """
        Get the proper values for keyword arguments other than "count_data" for <method> from this
        classes attributes.

        @param method: reference to a callable extraction method
        @return dict: A dictionary containing the argument keywords for <method> and corresponding
                      values from PulseExtractionLogic attributes.
        """
        # Sanity checking
        if not callable(method) or not (inspect.ismethod(method) or inspect.isfunction(method)):
            self.log.error('Method "_get_extraction_method_kwargs" needs a reference to a callable '
                           'method but instead received "{0}"'.format(type(method)))
            return dict()

        kwargs_dict = dict()
        method_signature = inspect.signature(method)
        for name in method_signature.parameters.keys():
            if name == 'count_data':
                pass
            elif hasattr(self, name):
                kwargs_dict[name] = getattr(self, name)
            else:
                kwargs_dict[name] = method_signature.parameters[name].default
                self.log.warning('Parameter "{0}" for extraction method "{1}" is no attribute of '
                                 'PulseExtractionLogic.\nTaking default value of "{2}" instead.'
                                 ''.format(name, method.__name__, kwargs_dict[name]))
        return kwargs_dict
