# -*- coding: utf-8 -*-
"""
This file contains the Qudi counter logic class.

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


from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt

from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic


class PulsedExtractionExternalLogic(GenericLogic):

    """ This logic module helps display user data in plots, and makes it easy to save.

    @signal sigCounterUpdate: there is new counting data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???
    """

    _modclass = 'PulsedExtractionExternalLogic'
    _modtype = 'logic'

    # declare connectors
    _in = {'savelogic': 'SaveLogic',
           'pulseextractionlogic': 'PulseExtractionLogic',
           'pulseanalysislogic': 'PulseAnalysisLogic'}
    _out = {'pulsedextractionexternallogic': 'PulsedExtractionExternalLogic'}

    def __init__(self, **kwargs):
        """ Create QdplotLogic object with connectors.

        @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """


        self._save_logic = self.get_in_connector('savelogic')
        self._pe_logic = self.get_in_connector('pulseextractionlogic')
        self._pa_logic = self.get_in_connector('pulseanalysislogic')

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        return

    def load_data(self,len_header,column,filename):
        self.data = np.genfromtxt(filename,skip_header=len_header,usecols=column)
        return self.data

    def extract_laser_pulses(self,count_treshold,min_len_laser,exception,ignore_first):
        laser_x,laser_y = self._pe_logic.extract_laser_pulses(self.data,count_treshold,
                                                              min_len_laser,exception,ignore_first)
        return laser_x,laser_y

    def find_longest_laser_pulse(self,laser):
        length=np.zeros(len(laser))
        for jj in range(len(laser)):
            length[jj]=len(laser[jj])
        return np.max(length)

    def sum_pulses(self,laser_1,laser_2):
        longest=self.find_longest_laser_pulse(laser_2)
        for jj in range(len(laser_2)):
            while len(laser_2[jj])<longest:
                laser_1[jj]=np.append(laser_1[jj],laser_1[jj][-1]+1)
                laser_2[jj]=np.append(laser_2[jj],laser_2[jj][-1])
        return np.sum(laser_2,axis=0)


    def analyze_data(self, laser_data, norm_start_bin, norm_end_bin, signal_start_bin,
                     signal_end_bin):

        signal_data,measuring_error=self._pa_logic.analyze_data(laser_data,norm_start_bin,norm_end_bin,
                                                   signal_start_bin,signal_end_bin)
        return signal_data,measuring_error



