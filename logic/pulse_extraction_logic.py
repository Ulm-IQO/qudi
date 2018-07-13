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
import numpy as np

from collections import OrderedDict
from core.module import StatusVar
from core.util.modules import get_main_dir
from logic.generic_logic import GenericLogic


class PulseExtractionLogic(GenericLogic):
    """

    """
    _modclass = 'PulseExtractionLogic'
    _modtype = 'logic'

    extraction_settings = StatusVar('extraction_settings', default={'conv_std_dev': 10.0,
                                                                    'count_threshold': 10,
                                                                    'threshold_tolerance': 20e-9,
                                                                    'min_laser_length': 200e-9,
                                                                    'current_method': 'conv_deriv'})

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        self.number_of_lasers = 50

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.gated_extraction_methods = OrderedDict()
        self.ungated_extraction_methods = OrderedDict()
        self.extraction_methods = OrderedDict()
        filename_list = []
        # The assumption is that in the directory pulse_extraction_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(get_main_dir(), 'logic', 'pulse_extraction_methods')
        for entry in os.listdir(path):
            if os.path.isfile(os.path.join(path, entry)) and entry.endswith('.py'):
                filename_list.append(entry[:-3])

        for filename in filename_list:
            mod = importlib.import_module('logic.pulse_extraction_methods.{0}'.format(filename))
            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(PulseExtractionLogic, method, getattr(mod, method))
                        # Add method to dictionary if it is an extraction method
                        if method.startswith('gated_'):
                            self.gated_extraction_methods[method[6:]] = eval('self.' + method)
                            self.extraction_methods[method[6:]] = eval('self.' + method)
                        elif method.startswith('ungated_'):
                            self.ungated_extraction_methods[method[8:]] = eval('self.' + method)
                            self.extraction_methods[method[8:]] = eval('self.' + method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'PulseExtractionLogic.'.format(method, filename))
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    def extract_laser_pulses(self, count_data, is_gated=False):
        """

        @param count_data:
        @param is_gated:
        @return:
        """

        # convert time to bin
        self.threshold_tolerance_bin = int(self.extraction_settings['threshold_tolerance']/self.fast_counter_binwidth+1)
        self.min_laser_length_bin = int(self.extraction_settings['min_laser_length'] / self.fast_counter_binwidth + 1)

        self.log.debug('Minimum laser length in bins: {0}'.format(self.min_laser_length_bin))
        self.log.debug('Threshold tolerance in bins: {0}'.format(self.threshold_tolerance_bin))

        if is_gated:
            return_dict = self.gated_extraction_methods[self.extraction_settings['current_method']](count_data)
        else:
            return_dict = self.ungated_extraction_methods[self.extraction_settings['current_method']](count_data)
        return return_dict

