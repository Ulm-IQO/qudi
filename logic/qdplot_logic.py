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

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic


class QDPlotLogic(GenericLogic):
    """ This logic module helps display user data in plots, and makes it easy to save.

    @signal sigCounterUpdate: there is new counting data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???
    """
    sigPlotDataUpdated = QtCore.Signal()
    sigPlotParamsUpdated = QtCore.Signal()
    sigFit1Updated = QtCore.Signal(np.ndarray, str, str)

    # declare connectors
    save_logic = Connector(interface='SaveLogic')
    fit_logic = Connector(interface='FitLogic')

    plot_1_fit_container = StatusVar(name='plot_1_fit_container', default=None)

    def __init__(self, *args, **kwargs):
        """ Create QDPlotLogic object with connectors.

        @param dict args: optional parameters
        @param dict kwargs: optional keyword parameters
        """
        super().__init__(*args, **kwargs)
        self._save_logic = None
        self._fit_logic = None

        # locking for thread safety
        self.threadlock = Mutex()

        self._clear_old = True
        self._x_limits = [[0., 1.]] * 3
        self._y_limits = [[0., 1.]] * 3
        self._x_label = ['X'] * 3
        self._y_label = ['Y'] * 3
        self._x_unit = ['a.u.'] * 3
        self._y_unit = ['a.u.'] * 3
        self._x_data = np.zeros(shape=(3, 1, 10))
        self._y_data = np.zeros(shape=(3, 1, 10))

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        self._save_logic = self.save_logic()
        self._fit_logic = self.fit_logic()

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        return 0

    @plot_1_fit_container.constructor
    def sv_set_fit_1(self, val):
        # Setup fit container
        fc = self.fit_logic().make_fit_container('Plot 1 QDPlotterLogic', '1d')
        fc.set_units(['', 'a.u.'])
        if not (isinstance(val, dict) and len(val) > 0):
            val = dict()
        fc.load_from_dict(val)
        return fc

    @plot_1_fit_container.representer
    def sv_get_fit_1(self, val):
        """ save configured fits """
        if len(val.fit_list) > 0:
            return val.save_to_dict()
        else:
            return None
        
    def do_fit_1(self, fit_method):
        result = ''
        fit_data = list()
        for dataset in range(len(self._x_data[0])):
            x_data = self._x_data[0][dataset]
            y_data = self._y_data[0][dataset]

            if fit_method is not None and isinstance(fit_method, str):
                if fit_method in self.plot_1_fit_container.fit_list:
                    self.plot_1_fit_container.set_current_fit(fit_method)
                else:
                    self.plot_1_fit_container.set_current_fit('No Fit')
                    if fit_method != 'No Fit':
                        self.log.warning('Fit function "{0}" not available in plot_1 fit container.'
                                         ''.format(fit_method))

            if len(x_data) < 2 or len(y_data) < 2 or min(x_data) == max(x_data):
                self.log.warning('The data you are trying to fit does not contain enough data for a fit.')
                return np.zeros(shape=(len(self._x_data[0]), 2, 10)), 'results', self.plot_1_fit_container.current_fit

            fit_x, fit_y, result_set = self.plot_1_fit_container.do_fit(np.array(x_data), np.array(y_data))
            fit_data_set = np.array([fit_x, fit_y])
            fit_data.append(fit_data_set)
            result += 'Dataset {0}:\n{1}'.format(dataset, result_set)

        fit_data = np.array(fit_data)
        self.sigFit1Updated.emit(fit_data, result, self.plot_1_fit_container.current_fit)
        return fit_data, result, self.plot_1_fit_container.current_fit
    
    @property
    def plot_1_x_data(self):
        return self._x_data[0]
    
    @property
    def plot_1_y_data(self):
        return self._y_data[0]

    def plot_1_set_data(self, x=None, y=None, clear_old=True):
        """Set the data to plot

        @param np.ndarray or list of np.ndarrays x: data of independents variable(s)
        @param np.ndarray or list of np.ndarrays y: data of dependent variable(s)
        @param bool clear_old: clear old plots in GUI if True
        """

        if x is None:
            self.log.error('No x-values provided, cannot set plot data.')
            return -1

        if y is None:
            self.log.error('No y-values provided, cannot set plot data.')
            return -1

        self._clear_old = clear_old
        # check if input is only an array (single plot) or a list of arrays (one or several plots)
        if type(x[0]) is np.ndarray:  # if x is an array, type(x[0]) is a np.float
            self._y_data[0] = x
            self._x_data[0] = y
        else:
            self._y_data[0] = [x]
            self._x_data[0] = [y]

        self.plot_1_y_limits = None
        self.plot_1_x_limits = None

        self.sigPlotDataUpdated.emit()
        self.sigPlotParamsUpdated.emit()

        return 0

    @property
    def plot_1_x_limits(self):
        return self._x_limits[0]

    @plot_1_x_limits.setter
    def plot_1_x_limits(self, limits=None):
        """Set the plot_1_x_limits, to match the data (default) or to a specified new range

        @param float limits: 2-element list containing min and max y-values
        """
        if limits is not None:
            if isinstance(limits, (list, tuple, np.ndarray)) and len(limits) > 1:
                self._x_limits[0] = limits
            else:
                self.log('plot_1_x_limits need to be a list of at least 2 elements but are {}.'.format(limits))
        else:
            range_min = np.min([np.min(values) for values in self.depen_vals])
            range_max = np.max([np.max(values) for values in self.depen_vals])
            range_range = range_max - range_min
            self._x_limits[0] = [range_min - 0.02 * range_range, range_max + 0.02 * range_range]

        self.sigPlotParamsUpdated.emit()

    @property
    def plot_1_y_limits(self):
        return self._y_limits[0]

    @plot_1_y_limits.setter
    def plot_1_y_limits(self, limits=None):
        """Set the plot_1_y_limits, to match the data (default) or to a specified new range

        @param float limits: 2-element list containing min and max y-values
        """
        if limits is not None:
            if isinstance(limits, (list, tuple, np.ndarray)) and len(limits) > 1:
                self._y_limits[0] = limits
            else:
                self.log('plot_1_y_limits need to be a list of at least 2 elements but are {}.'.format(limits))
        else:
            range_min = np.min([np.min(values) for values in self.indep_vals])
            range_max = np.max([np.max(values) for values in self.indep_vals])
            range_range = range_max - range_min
            self._y_limits[0] = [range_min - 0.02 * range_range, range_max + 0.02 * range_range]

        self.sigPlotParamsUpdated.emit()

    @property
    def plot_1_x_label(self):
        return self._x_label[0]

    @plot_1_x_label.setter
    def plot_1_x_label(self, value):
        self._x_label[0] = str(value)

    @property
    def plot_1_y_label(self):
        return self._y_label[0]

    @plot_1_y_label.setter
    def plot_1_y_label(self, value):
        self._y_label[0] = str(value)

    @property
    def plot_1_x_unit(self):
        return self._x_unit[0]

    @plot_1_x_unit.setter
    def plot_1_x_unit(self, value):
        self._x_unit[0] = str(value)

    @property
    def plot_1_y_unit(self):
        return self._y_unit[0]

    @plot_1_y_unit.setter
    def plot_1_y_unit(self, value):
        self._y_unit[0] = str(value)

    @property
    def plot_2_x_label(self):
        return self._x_label[1]

    @plot_2_x_label.setter
    def plot_2_x_label(self, value):
        self._x_label[1] = str(value)

    @property
    def plot_2_y_label(self):
        return self._y_label[1]

    @plot_2_y_label.setter
    def plot_2_y_label(self, value):
        self._y_label[1] = str(value)

    @property
    def plot_2_x_unit(self):
        return self._x_unit[1]

    @plot_2_x_unit.setter
    def plot_2_x_unit(self, value):
        self._x_unit[1] = str(value)

    @property
    def plot_2_y_unit(self):
        return self._y_unit[1]

    @plot_2_y_unit.setter
    def plot_2_y_unit(self, value):
        self._y_unit[1] = str(value)

    @property
    def plot_3_x_label(self):
        return self._x_label[2]

    @plot_3_x_label.setter
    def plot_3_x_label(self, value):
        self._x_label[2] = str(value)

    @property
    def plot_3_y_label(self):
        return self._y_label[2]

    @plot_3_y_label.setter
    def plot_3_y_label(self, value):
        self._y_label[2] = str(value)

    @property
    def plot_3_x_unit(self):
        return self._x_unit[2]

    @plot_3_x_unit.setter
    def plot_3_x_unit(self, value):
        self._x_unit[2] = str(value)

    @property
    def plot_3_y_unit(self):
        return self._y_unit[2]

    @plot_3_y_unit.setter
    def plot_3_y_unit(self, value):
        self._y_unit[2] = str(value)

    @property
    def clear_old_data(self):
        return self._clear_old

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
        for ii in range(len(self.indep_vals)):
            data['indep_label' + str(ii + 1)] = self.indep_vals[ii]
            data['depen_label' + str(ii + 1)] = self.depen_vals[ii]

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)

        fig, ax1 = plt.subplots()

        for ii in range(len(self.indep_vals)):
            ax1.plot(self.indep_vals[ii], self.depen_vals[ii], linestyle=':', linewidth=1)

        ax1.set_xlabel(indep_label)
        ax1.set_ylabel(depen_label)

        ax1.set_xlim(self.plot_domain)
        ax1.set_ylim(self.plot_range)

        fig.tight_layout()

        filepath = self._save_logic.get_path_for_module(module_name='qdplot')

        # Call save logic to write everything to file
        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   plotfig=fig,
                                   delimiter='\t')
        plt.close(fig)
        self.log.debug('Data saved to:\n{0}'.format(filepath))
