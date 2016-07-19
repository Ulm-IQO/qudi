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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


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
            self.log.error('No x-values provided, cannot set plot data.')
            return -1

        if y is None:
            self.log.error('No y-values provided, cannot set plot data.')
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
        print('label_in_sethlabel', label)
        self.h_label = label
        self.h_units = units

        self.sigPlotParamsUpdated.emit()
        return 0

    def set_vlabel(self, label='Dependent variable', units='arb. units'):
        """Set the vertical axis label and specify units.

        @param string label: name of axis

        @param string units: symbol for units
        """
        print('label_in_setvlabel', label)
        self.v_label = label
        self.v_units = units

        self.sigPlotParamsUpdated.emit()
        return 0

    def get_domain(self):
        return self.plot_domain

    def get_range(self):
        return self.plot_range

    def save_data(self, postfix=''):
        """ Save the data to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save

        @return np.array([2 or 3][X]), OrderedDict: array with the
        """
        # Set the parameters:
        parameters = OrderedDict()
        parameters['User-selected display domain'] = self.plot_domain
        parameters['User-selected display range'] = self.plot_range

        # If there is a postfix then add separating underscore
        if postfix == '':
            filelabel = 'qdplot'
        else:
            filelabel = postfix

        # Data labels
        indep_label = self.h_label + ' (' + self.h_units + ')'
        depen_label = self.v_label + ' (' + self.v_units + ')'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data[indep_label] = self.indep_vals
        data[depen_label] = self.depen_vals

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)

        fig, ax1 = plt.subplots()

        ax1.plot(self.indep_vals, self.depen_vals)

        ax1.set_xlabel(indep_label)
        ax1.set_ylabel(depen_label)

        ax1.set_xlim(self.plot_domain)
        ax1.set_ylim(self.plot_range)

        fig.tight_layout()

        filepath = self._save_logic.get_path_for_module(module_name='qdplot')

        # Call save logic to write everything to file
        self._save_logic.save_data(data,
                                   filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   as_text=True,
                                   plotfig=fig
                                   )
        self.log.debug('Data saved to:\n{0}'.format(filepath))
