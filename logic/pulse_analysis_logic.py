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

    analysis_settings = StatusVar('analysis_settings', default={'signal_start_s': 0.0,
                                                                'signal_end_s': 200.0e-9,
                                                                'norm_start_s': 500.0e-9,
                                                                'norm_end_s': 700.0e-9,
                                                                'current_method': 'mean_norm'})

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

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
                    if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(PulseAnalysisLogic, method, getattr(mod, method))
                        # Add method to dictionary if it is a generator method
                        if method.startswith('analyse_'):
                            self.analysis_methods[method[8:]] = eval('self.' + method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'PulseAnalysisLogic.'.format(method, filename))
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    def analyze_data(self, laser_data):
        """ Analysis the laser pulses and computes the measuring error given by photon shot noise

        @param numpy.ndarray (int) laser_data: 2D array containing the extracted laser countdata

        @return: float array signal_data: Array with the computed signal
        @return: float array measuring_error: Array with the computed signal error
        """
#
        # convert time to bin
        self.signal_start_bin = round(self.analysis_settings['signal_start_s'] / self.fast_counter_binwidth)
        self.signal_end_bin = round(self.analysis_settings['signal_end_s'] / self.fast_counter_binwidth)
        self.norm_start_bin = round(self.analysis_settings['norm_start_s'] / self.fast_counter_binwidth)
        self.norm_end_bin = round(self.analysis_settings['norm_end_s'] / self.fast_counter_binwidth)

        signal_data, measuring_error = self.analysis_methods[self.analysis_settings['current_method']](laser_data)
        return signal_data, measuring_error
