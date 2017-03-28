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
from logic.generic_logic import GenericLogic


class PulseExtractionLogic(GenericLogic):
    """

    """
    _modclass = 'PulseExtractionLogic'
    _modtype = 'logic'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        self.conv_std_dev = 10.0
        self.number_of_lasers = 50
        self.count_treshold = 10
        self.threshold_tolerance_bins = 20
        self.min_laser_length = 200
        self.current_method = 'conv_deriv'

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
        # recall saved variables from file
        if 'conv_std_dev' in self._statusVariables:
            self.conv_std_dev = self._statusVariables['conv_std_dev']
        if 'count_treshold' in self._statusVariables:
            self.count_treshold = self._statusVariables['count_treshold']
        if 'threshold_tolerance_bins' in self._statusVariables:
            self.threshold_tolerance_bins = self._statusVariables['threshold_tolerance_bins']
        if 'min_laser_length' in self._statusVariables:
            self.min_laser_length = self._statusVariables['min_laser_length']
        #if 'number_of_lasers' in self._statusVariables:
        #    self.number_of_lasers = self._statusVariables['number_of_lasers']
        if 'current_method' in self._statusVariables:
            self.current_method = self._statusVariables['current_method']

        self.gated_extraction_methods = OrderedDict()
        self.ungated_extraction_methods = OrderedDict()
        self.extraction_methods = OrderedDict()
        filename_list = []
        # The assumption is that in the directory pulse_extraction_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(self.get_main_dir(), 'logic', 'pulse_extraction_methods')
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

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        # Save variables to file
        self._statusVariables['conv_std_dev'] = self.conv_std_dev
        self._statusVariables['count_treshold'] = self.count_treshold
        self._statusVariables['threshold_tolerance_bins'] = self.threshold_tolerance_bins
        self._statusVariables['min_laser_length'] = self.min_laser_length
        #self._statusVariables['number_of_lasers'] = self.number_of_lasers
        self._statusVariables['current_method'] = self.current_method
        return

    def extract_laser_pulses(self, count_data, is_gated=False):
        """

        @param count_data:
        @param is_gated:
        @return:
        """
        if is_gated:
            return_dict = self.gated_extraction_methods[self.current_method](count_data)
        else:
            return_dict = self.ungated_extraction_methods[self.current_method](count_data)
        return return_dict

    # FIXME: What's that???
    # def excise_laser_pulses(self,count_data,num_lasers,laser_length,initial_offset,initial_length,increment):
    #
    #     return_dict = {}
    #     laser_x = []
    #     laser_y = []
    #
    #     x_data = np.linspace(initial_offset,initial_offset+laser_length,laser_length+1)
    #     y_data = count_data[initial_offset:initial_offset+laser_length]
    #     laser_x.append(x_data)
    #     laser_y.append(y_data)
    #
    #     time = initial_length + initial_offset
    #
    #     for laser in range(int(num_lasers)-1):
    #
    #         x_data = np.linspace(time,time+laser_length,laser_length+1)
    #         y_data = count_data[time:(time+laser_length)]
    #         laser_x.append(np.array(x_data))
    #         laser_y.append(np.array(y_data))
    #
    #
    #         time = time + initial_length + (laser+1)*increment
    #
    #
    #
    #
    #     laser_y = np.asarray(laser_y)
    #     laser_x = np.asarray(laser_x)
    #
    #     self.log.debug(laser_y)
    #
    #     rising_ind = np.array([i[0] for i in laser_x])
    #     falling_ind = np.array([i[-1] for i in laser_y])
    #
    #     return_dict['laser_rising'] = rising_ind
    #     return_dict['laser_falling'] = falling_ind
    #     return_dict['laser_arr_y'] = laser_y.astype(int)
    #
    #     return return_dict

