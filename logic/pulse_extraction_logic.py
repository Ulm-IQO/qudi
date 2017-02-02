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
from qtpy import QtCore


class PulseExtractionLogic(GenericLogic):
    """

    """
    _modclass = 'PulseExtractionLogic'
    _modtype = 'logic'

    # declare connectors
    _out = {'pulseextractionlogic': 'PulseExtractionLogic'}

    sigExtractionMethodsUpdated = QtCore.Signal(dict, dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        self.conv_std_dev = None
        self.number_of_lasers = None
        self.count_treshold = None
        self.threshold_tolerance_bins = None
        self.min_laser_length = None

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
        self.gated_extraction_methods = OrderedDict()
        self.ungated_extraction_methods = OrderedDict()
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
                        elif method.startswith('ungated_'):
                            self.ungated_extraction_methods[method[8:]] = eval('self.' + method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'PulseExtractionLogic.'.format(method, filename))
        self.sigExtractionMethodsUpdated.emit(self.gated_extraction_methods,
                                              self.ungated_extraction_methods)
        return

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def extract_laser_pulses(self, count_data, method, is_gated=False):
        """

        @param count_data:
        @param method:
        @param is_gated:
        @return:
        """
        if is_gated:
            laser_arr = self.gated_extraction_methods[method](count_data)
        else:
            laser_arr = self.ungated_extraction_methods[method](count_data)
        return laser_arr

    # FIXME: What's that???
    def excise_laser_pulses(self,count_data,num_lasers,laser_length,initial_offset,initial_length,increment):


        laser_x = []
        laser_y = []

        x_data = np.linspace(initial_offset,initial_offset+laser_length,laser_length+1)
        y_data = count_data[initial_offset:initial_offset+laser_length]
        laser_x.append(x_data)
        laser_y.append(y_data)

        time = initial_length + initial_offset

        for laser in range(int(num_lasers)-1):

            x_data = np.linspace(time,time+laser_length,laser_length+1)
            y_data = count_data[time:(time+laser_length)]
            laser_x.append(np.array(x_data))
            laser_y.append(np.array(y_data))


            time = time + initial_length + (laser+1)*increment




        laser_arr=np.asarray(laser_y)

        self.log.debug(laser_y)

        return laser_arr.astype(int)

