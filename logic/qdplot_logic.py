# -*- coding: utf-8 -*-
"""
This file contains the QuDi counter logic class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Lachlan J. Rogers <lachlan.j.rogers@quantum.diamonds>
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np


class QdplotLogic(GenericLogic):

    """ This logic module helps display user data in plots, and makes it easy to save.

    @signal sigCounterUpdate: there is new counting data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???
    """
    sigPlotDataUpdated = QtCore.Signal()
    sigPlotParamsUpdated = QtCore.Signal()

    _modclass = 'QdplotLogic'
    _modtype = 'logic'

    # declare connectors
    _in = {'savelogic': 'SaveLogic'
           }
    _out = {'qdplotlogic': 'QdplotLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create QdplotLogic object with connectors.

        @param object manager: Manager object thath loaded this module
        @param str name: unique module name
        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """
        self.indep_vals = np.zeros((10,))
        self.depen_vals = np.zeros((10,))

        self.plot_domain = [0, 1]
        self.plot_range = [0, 1]

        self.set_hlabel()
        self.set_vlabel()

        self._save_logic = self.connector['in']['savelogic']['object']

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        return

    def set_data(self, x=None, y=None):
        """Set the data to plot
        """
        if x is None:
            self.logMsg('No x-values provided, cannot set plot data.', 
                        msgType='error', 
                        importance=3
                        )
            return -1

        if y is None:
            self.logMsg('No y-values provided, cannot set plot data.', 
                        msgType='error', 
                        importance=3
                        )
            return -1

        self.indep_vals = x
        self.depen_vals = y

        self.sigPlotDataUpdated.emit()
        self.sigPlotParamsUpdated.emit()
        return

    def set_domain(self, newdomain=None):
        """Set the plot domain

        @param float newdomain: 2-element list containing min and max x-values
        """
        # TODO: This needs to check that newdomain is a 2-element list with numerical values.
        if newdomain is not None:
            self.plot_domain = newdomain
        else:
            return -1

        self.sigPlotParamsUpdated.emit()
        return 0

    def set_range(self, newrange=None):
        """Set the plot range

        @param float newrange: 2-element list containing min and max y-values
        """
        # TODO: This needs to check that newdomain is a 2-element list with numerical values.
        if newrange is not None:
            self.plot_range = newrange
        else:
            return -1

        self.sigPlotParamsUpdated.emit()
        return 0

    def set_hlabel(self, label='Independent variable', units='arb. units'):
        """Set the horizontal axis label and specify units.

        @param string label: name of axis

        @param string units: symbol for units
        """
        self.h_label = label
        self.h_units = units

        self.sigPlotParamsUpdated.emit()
        return 0

    def set_vlabel(self, label='Dependent variable', units='arb. units'):
        """Set the vertical axis label and specify units.

        @param string label: name of axis

        @param string units: symbol for units
        """
        self.v_label = label
        self.v_units = units

        self.sigPlotParamsUpdated.emit()
        return 0

    def get_domain(self):
        return self.plot_domain

    def get_range(self):
        return self.plot_range


    def start_saving(self, resume=False):
        """ Starts saving the data in a list.

        @return int: error code (0:OK, -1:error)
        """

        if not resume:
            self._data_to_save = []
            self._saving_start_time = time.time()
        self._saving = True

        # If the counter is not running, then it should start running so there is data to save
        if self.isstate('idle'):
            self.startCount()

        return 0

    def save_data(self, to_file=True, postfix=''):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save

        @return np.array([2 or 3][X]), OrderedDict: array with the
        """
        self._saving = False
        self._saving_stop_time = time.time()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        if to_file:
            # If there is a postfix then add separating underscore
            if postfix == '':
                filelabel = 'count_trace'
            else:
                filelabel = 'count_trace_'+postfix

            # prepare the data in a dict or in an OrderedDict:
            data = OrderedDict()
            data = {'Time (s),Signal (counts/s)': self._data_to_save}
            if self._counting_device._photon_source2 is not None:
                data = {'Time (s),Signal 1 (counts/s),Signal 2 (counts/s)': self._data_to_save}

            filepath = self._save_logic.get_path_for_module(module_name='Counter')
            self._save_logic.save_data(data, filepath, parameters=parameters, filelabel=filelabel, as_text=True)
            #, as_xml=False, precision=None, delimiter=None)
            self.logMsg('Counter Trace saved to:\n{0}'.format(filepath), msgType='status', importance=3)

        return self._data_to_save, parameters


    def save_current_count_trace(self, name_tag=''):
        """ The current displayed counttrace will be saved.

        @param str name_tag: optional, personal description that will be
                             appended to the file name

        This method saves the already displayed counts to file and does not
        accumulate them. The counttrace variable will be saved to file with the
        provided name!
        """

        # If there is a postfix then add separating underscore
        if name_tag == '':
            filelabel = 'snapshot_count_trace'
        else:
            filelabel = 'snapshot_count_trace_'+name_tag

        stop_time = self._count_length/self._count_frequency
        time_step_size = stop_time/len(self.countdata)
        x_axis = np.arange(0, stop_time, time_step_size)

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        if hasattr(self._counting_device, '_photon_source2'):
            # if self._counting_device._photon_source2 is None:
            data['Time (s),Signal 1 (counts/s),Signal 2 (counts/s)'] = np.array((x_axis, self.countdata, self.countdata2)).transpose()
        else:
            data['Time (s),Signal (counts/s)'] = np.array((x_axis, self.countdata)).transpose()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Saved at time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
                                                        time.localtime(time.time()))

        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        filepath = self._save_logic.get_path_for_module(module_name='Counter')
        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, as_text=True)

        #, as_xml=False, precision=None, delimiter=None)
        self.logMsg('Current Counter Trace saved to:\n'
                    '{0}'.format(filepath), msgType='status', importance=3)




