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

import numpy as np
import os
import importlib
import inspect
from logic.generic_logic import GenericLogic
from collections import OrderedDict
from qtpy import QtCore


class PulseAnalysisLogic(GenericLogic):
    """unstable: Nikolas Tomek  """

    _modclass = 'PulseAnalysisLogic'
    _modtype = 'logic'

    # declare connectors
    _out = {'pulseanalysislogic': 'PulseAnalysisLogic'}

    sigAnalysisMethodsUpdated = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self.analysis_methods = OrderedDict()
        filename_list = []
        # The assumption is that in the directory pulsed_analysis_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(self.get_main_dir(), 'logic', 'pulsed_analysis_methods')
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
        self.sigAnalysisMethodsUpdated.emit(self.analysis_methods)
        return

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def analyze_data(self, laser_data, norm_start_bin, norm_end_bin, signal_start_bin,
                     signal_end_bin, method):
        """ Analysis the laser pulses and computes the measuring error given by photon shot noise

        @param numpy.ndarray (int) laser_data: 2D array containing the extracted laser countdata
        @param int norm_start_bin: Bin where the data for reference starts
        @param int norm_end_bin: Bin where the data for reference ends
        @param int signal_start_bin: Bin where the signal starts
        @param int signal_end_bin: Bin where the signal stops
        @param str method: The desired analysis method name

        @return: float array signal_data: Array with the computed signal
        @return: float array laser_data: Array with the laser data
        @return: float array raw_data: Array with the raw data
        """
        signal_data, measuring_error = self.analysis_methods[method](laser_data, norm_start_bin,
                                                                     norm_end_bin, signal_start_bin,
                                                                     signal_end_bin)
        return signal_data, measuring_error
