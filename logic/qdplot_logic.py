# -*- coding: utf-8 -*-
"""
This file contains the Qudi QDPlotter logic class.

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

Completely reworked by Kay Jahnke, May 2020
"""

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from core.util import units


class QDPlotLogic(GenericLogic):
    """ This logic module helps display user data in plots, and makes it easy to save.
    
    There are phythonic setters and getters for each of the parameter and data. 
    They can be called by "plot_<plot_number>_parameter". plot_number ranges from 1 to 3.
    Parameters are: x_limits, y_limits, x_label, y_label, x_unit, y_unit, x_data, y_data, clear_old_data
    
    All parameters and data can also be interacted with by calling get_ and set_ functions.

    @signal sigPlotDataUpdated: empty signal that is fired whenever the plot data has been updated
    @signal sigPlotParamsUpdated: empty signal that is fired whenever any of the parameters or data have been updated.                
    @signal sigFitUpdated: 
    """
    sigPlotDataUpdated = QtCore.Signal()
    sigPlotParamsUpdated = QtCore.Signal()
    sigFitUpdated = QtCore.Signal(int, np.ndarray, str, str)

    # declare connectors
    save_logic = Connector(interface='SaveLogic')
    fit_logic = Connector(interface='FitLogic')

    fit_container = StatusVar(name='fit_container', default=None)

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

        self._number_of_plots = 3

        self._clear_old = [True] * self._number_of_plots
        self._x_limits = [[0., 1.]] * self._number_of_plots
        self._y_limits = [[0., 1.]] * self._number_of_plots
        self._x_label = ['X'] * self._number_of_plots
        self._y_label = ['Y'] * self._number_of_plots
        self._x_unit = ['a.u.'] * self._number_of_plots
        self._y_unit = ['a.u.'] * self._number_of_plots
        self._x_data = [np.zeros(shape=(1, 10))] * self._number_of_plots
        self._y_data = [np.zeros(shape=(1, 10))] * self._number_of_plots
        self._fit_data = [None] * self._number_of_plots
        self._fit_results = [None] * self._number_of_plots
        self._fit_method = [None] * self._number_of_plots

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        self._save_logic = self.save_logic()
        self._fit_logic = self.fit_logic()

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        return 0

    @fit_container.constructor
    def sv_set_fit(self, val):
        """ Set up fit container """
        fc = self.fit_logic().make_fit_container('Plot QDPlotterLogic', '1d')
        fc.set_units(['', 'a.u.'])
        if not (isinstance(val, dict) and len(val) > 0):
            val = dict()
        fc.load_from_dict(val)
        return fc

    @fit_container.representer
    def sv_get_fit(self, val):
        """ Save configured fits """
        if len(val.fit_list) > 0:
            return val.save_to_dict()
        else:
            return None
    
    def get_x_data(self, plot_index=0):
        """ Get the data of the x-axis being plotted.
        
        @param int plot_index: index of the plot in the range from 0 to 2
        @return np.ndarray or list of np.ndarrays x: data of the x-axis
        """
        return self._x_data[plot_index]
    
    def get_y_data(self, plot_index=0):
        """ Get the data of the y-axis being plotted.
        
        @param int plot_index: index of the plot in the range from 0 to 2
        @return np.ndarray or list of np.ndarrays y: data of the y-axis
        """
        return self._y_data[plot_index]

    def set_data(self, x=None, y=None, clear_old=True, plot_index=0):
        """ Set the data to plot

        @param np.ndarray or list of np.ndarrays x: data of independents variable(s)
        @param np.ndarray or list of np.ndarrays y: data of dependent variable(s)
        @param bool clear_old: clear old plots in GUI if True
        @param int plot_index: index of the plot in the range from 0 to 2
        """

        if x is None:
            self.log.error('No x-values provided, cannot set plot data.')
            return -1

        if y is None:
            self.log.error('No y-values provided, cannot set plot data.')
            return -1

        self._clear_old[plot_index] = clear_old
        # check if input is only an array (single plot) or a list of arrays (one or several plots)
        if type(x[0]) is np.ndarray:  # if x is an array, type(x[0]) is a np.float
            self._x_data[plot_index] = x
            self._y_data[plot_index] = y
        else:
            self._x_data[plot_index] = [x]
            self._y_data[plot_index] = [y]

        # reset fit for this plot
        self._fit_data[plot_index] = None
        self._fit_results[plot_index] = None
        self._fit_method[plot_index] = None

        # automatically set the correct range
        self.set_x_limits(plot_index=plot_index)
        self.set_y_limits(plot_index=plot_index)

        self.sigPlotDataUpdated.emit()

        return 0
        
    def do_fit(self, fit_method, plot_index=0):
        """ Get the data of the x-axis being plotted.
        
        @param str fit_method: name of the fit_method, this needs to match the methods in the fit container
        @param int plot_index: index of the plot in the range from 0 to 2
        @return int plot_index, 3-dimensional np.ndarray fit_data, str result, str fit_method: result of the fit
        """
        result = ''
        fit_data = list()
        
        # do one fit for each data set in the plot
        for data_set in range(len(self._x_data[plot_index])):
            x_data = self._x_data[plot_index][data_set]
            y_data = self._y_data[plot_index][data_set]

            # check that the fit_method is correct
            if fit_method is not None and isinstance(fit_method, str):
                if fit_method in self.fit_container.fit_list:
                    self.fit_container.set_current_fit(fit_method)
                else:
                    self.fit_container.set_current_fit('No Fit')
                    if fit_method != 'No Fit':
                        self.log.warning('Fit function "{0}" not available in plot_1 fit container.'
                                         ''.format(fit_method))

            # only fit if the is enough data to actually do the fit
            if len(x_data) < 2 or len(y_data) < 2 or min(x_data) == max(x_data):
                self.log.warning('The data you are trying to fit does not contain enough data for a fit.')
                return plot_index, np.zeros(shape=(len(self._x_data[plot_index]), 2, 10)), 'results', self.fit_container.current_fit

            # actually do the fit
            fit_x, fit_y, result_set = self.fit_container.do_fit(np.array(x_data), np.array(y_data))
            fit_data_set = np.array([fit_x, fit_y])
            fit_data.append(fit_data_set)

            # Get formatted result string and concatenate the results of the data sets
            if fit_method == 'No Fit':
                formatted_fitresult = 'No Fit'
            else:
                try:
                    formatted_fitresult = units.create_formatted_output(result_set.result_str_dict)
                except:
                    formatted_fitresult = 'This fit does not return formatted results'
            tabbed_result = '\n  '.join(formatted_fitresult.split('\n')[:-1])
            result += 'data_set {0}:\n  {1}\n'.format(data_set, tabbed_result)
            
        # convert list to np.ndarray to make handling it much more efficient
        fit_data = np.array(fit_data)

        # save the fit results internally
        self._fit_data[plot_index] = fit_data
        self._fit_results[plot_index] = result
        self._fit_method[plot_index] = fit_method

        self.sigFitUpdated.emit(plot_index, fit_data, result, self.fit_container.current_fit)
        return plot_index, fit_data, result, self.fit_container.current_fit

    def save_data(self, postfix='', plot_index=0):
        """ Save the data to a file.

        @param str postfix: an additional tag, which will be added to the filename upon save
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        # Set the parameters:
        parameters = OrderedDict()
        parameters['user-selected x-limits'] = self._x_limits[plot_index]
        parameters['user-selected y-limits'] = self._y_limits[plot_index]
        parameters['user-selected x-label'] = self._x_label[plot_index]
        parameters['user-selected y-label'] = self._y_label[plot_index]
        parameters['user-selected x-unit'] = self._x_unit[plot_index]
        parameters['user-selected y-unit'] = self._y_unit[plot_index]

        # If there is a postfix then add separating underscore
        if postfix == '':
            file_label = 'qdplot'
        else:
            file_label = postfix
            
        file_label += '_plot_{0:d}'.format(int(plot_index) + 1)

        # Data labels
        x_label = self._x_label[plot_index] + ' (' + self._x_unit[plot_index] + ')'
        y_label = self._y_label[plot_index] + ' (' + self._y_unit[plot_index] + ')'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        for data_set in range(len(self._x_data[plot_index])):
            data['{0} set {1:d}'.format(x_label, data_set + 1)] = self._x_data[plot_index][data_set]
            data['{0} set {1:d}'.format(y_label, data_set + 1)] = self._y_data[plot_index][data_set]

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)

        fig, ax1 = plt.subplots()

        for data_set in range(len(self._x_data[plot_index])):
            ax1.plot(self._x_data[plot_index][data_set], self._y_data[plot_index][data_set], linestyle=':', linewidth=1)

            if self._fit_data[plot_index] is not None:
                ax1.plot(self._fit_data[plot_index][data_set][0], self._fit_data[plot_index][data_set][1],
                         color='r', marker='None', linewidth=1.5, label='fit')

        # Do not include fit parameter if there is no fit calculated.
        if self._fit_data[plot_index] is not None:
            # Parameters for the text plot:
            # The position of the text annotation is controlled with the
            # relative offset in x direction and the relative length factor
            # rel_len_fac of the longest entry in one column
            rel_offset = 0.02
            rel_len_fac = 0.011
            entries_per_col = 24

            # do reverse processing to get each entry in a list
            entry_list = self._fit_results[plot_index].split('\n')
            # slice the entry_list in entries_per_col
            chunks = [entry_list[x:x + entries_per_col] for x in range(0, len(entry_list), entries_per_col)]

            is_first_column = True  # first entry should contain header or \n

            for column in chunks:
                max_length = max(column, key=len)  # get the longest entry
                column_text = ''

                for entry in column:
                    column_text += entry.rstrip() + '\n'

                column_text = column_text[:-1]  # remove the last new line

                heading = 'Fit results for method: {}'.format(self._fit_method[plot_index]) if is_first_column else ''
                column_text = heading + '\n' + column_text

                ax1.text(1.00 + rel_offset, 0.99, column_text,
                         verticalalignment='top',
                         horizontalalignment='left',
                         transform=ax1.transAxes,
                         fontsize=12)

                # the rel_offset in position of the text is a linear function
                # which depends on the longest entry in the column
                rel_offset += rel_len_fac * len(max_length)

                is_first_column = False

        # set labels, units and limits
        ax1.set_xlabel(x_label)
        ax1.set_ylabel(y_label)

        ax1.set_xlim(self._x_limits[plot_index])
        ax1.set_ylim(self._y_limits[plot_index])

        fig.tight_layout()

        # Call save logic to write everything to file
        file_path = self._save_logic.get_path_for_module(module_name='qdplot')
        self._save_logic.save_data(data,
                                   filepath=file_path,
                                   parameters=parameters,
                                   filelabel=file_label,
                                   plotfig=fig,
                                   delimiter='\t')
        plt.close(fig)
        self.log.debug('Data saved to:\n{0}'.format(file_path))

    def get_x_limits(self, plot_index=0):
        """ Get the limits of the x-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return 2-element list: limits of the x-axis e.g. as [0, 1]
        """
        return self._x_limits[plot_index]

    def set_x_limits(self, limits=None, plot_index=0):
        """Set the x_limits, to match the data (default) or to a specified new range

        @param float limits: 2-element list containing min and max x-values
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        if limits is not None:
            if isinstance(limits, (list, tuple, np.ndarray)) and len(limits) > 1:
                self._x_limits[plot_index] = limits
            else:
                self.log('plot_1_x_limits need to be a list of at least 2 elements but are {}.'.format(limits))
        else:
            range_min = np.min([np.min(values) for values in self._x_data[plot_index]])
            range_max = np.max([np.max(values) for values in self._x_data[plot_index]])
            range_range = range_max - range_min
            self._x_limits[plot_index] = [range_min - 0.02 * range_range, range_max + 0.02 * range_range]

        self.sigPlotParamsUpdated.emit()

    def get_y_limits(self, plot_index):
        """ Get the limits of the y-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return 2-element list: limits of the y-axis e.g. as [0, 1]
        """
        return self._y_limits[plot_index]

    def set_y_limits(self, limits=None, plot_index=0):
        """Set the y_limits, to match the data (default) or to a specified new range

        @param float limits: 2-element list containing min and max y-values
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        if limits is not None:
            if isinstance(limits, (list, tuple, np.ndarray)) and len(limits) > 1:
                self._y_limits[plot_index] = limits
            else:
                self.log('plot_1_y_limits need to be a list of at least 2 elements but are {}.'.format(limits))
        else:
            range_min = np.min([np.min(values) for values in self._y_data[plot_index]])
            range_max = np.max([np.max(values) for values in self._y_data[plot_index]])
            range_range = range_max - range_min
            self._y_limits[plot_index] = [range_min - 0.02 * range_range, range_max + 0.02 * range_range]

        self.sigPlotParamsUpdated.emit()
        
    def get_x_label(self, plot_index=0):
        """ Get the label of the x-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current label of the x-axis
        """
        return self._x_label[plot_index]
    
    def set_x_label(self, value, plot_index=0):
        """ Set the label of the x-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        self._x_label[plot_index] = str(value)
        self.sigPlotParamsUpdated.emit()

    def get_y_label(self, plot_index=0):
        """ Get the label of the y-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current label of the y-axis
        """
        return self._y_label[plot_index]
    
    def set_y_label(self, value, plot_index=0):
        """ Set the label of the y-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        self._y_label[plot_index] = str(value)
        self.sigPlotParamsUpdated.emit()
        
    def get_x_unit(self, plot_index=0):
        """ Get the unit of the x-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current unit of the x-axis
        """
        return self._x_unit[plot_index]
    
    def set_x_unit(self, value, plot_index=0):
        """ Set the unit of the x-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        self._x_unit[plot_index] = str(value)
        self.sigPlotParamsUpdated.emit()

    def get_y_unit(self, plot_index=0):
        """ Get the unit of the y-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current unit of the y-axis
        """
        return self._y_unit[plot_index]
    
    def set_y_unit(self, value, plot_index=0):
        """ Set the unit of the y-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        self._y_unit[plot_index] = str(value)
        self.sigPlotParamsUpdated.emit()

    def clear_old_data(self, plot_index=0):
        """ Get the information, if the previous plots in the windows are kept or not

        @param int plot_index: index of the plot in the range from 0 to 2
        @return bool: are the plots currently in the GUI kept or not
        """
        return self._clear_old[plot_index]

###############################################################################################
#   individual getters and setters
###############################################################################################

    @property
    def plot_1_x_data(self):
        return self.get_x_data(plot_index=0)

    @property
    def plot_1_y_data(self):
        return self.get_y_data(plot_index=0)

    @property
    def plot_2_x_data(self):
        return self.get_x_data(plot_index=1)

    @property
    def plot_2_y_data(self):
        return self.get_y_data(plot_index=1)

    @property
    def plot_3_x_data(self):
        return self.get_x_data(plot_index=2)

    @property
    def plot_3_y_data(self):
        return self.get_y_data(plot_index=2)

    @property
    def plot_1_x_label(self):
        return self._x_label[0]

    @plot_1_x_label.setter
    def plot_1_x_label(self, value):
        self.set_x_label(plot_index=0, value=value)

    @property
    def plot_1_y_label(self):
        return self._y_label[0]

    @plot_1_y_label.setter
    def plot_1_y_label(self, value):
        self.set_y_label(plot_index=0, value=value)

    @property
    def plot_1_x_unit(self):
        return self._x_unit[0]

    @plot_1_x_unit.setter
    def plot_1_x_unit(self, value):
        self.set_x_unit(plot_index=0, value=value)

    @property
    def plot_1_y_unit(self):
        return self._y_unit[0]

    @plot_1_y_unit.setter
    def plot_1_y_unit(self, value):
        self.set_y_unit(plot_index=0, value=value)

    @property
    def plot_2_x_label(self):
        return self._x_label[1]

    @plot_2_x_label.setter
    def plot_2_x_label(self, value):
        self.set_x_label(plot_index=1, value=value)

    @property
    def plot_2_y_label(self):
        return self._y_label[1]

    @plot_2_y_label.setter
    def plot_2_y_label(self, value):
        self.set_y_label(plot_index=1, value=value)

    @property
    def plot_2_x_unit(self):
        return self._x_unit[1]

    @plot_2_x_unit.setter
    def plot_2_x_unit(self, value):
        self.set_x_unit(plot_index=1, value=value)

    @property
    def plot_2_y_unit(self):
        return self._y_unit[1]

    @plot_2_y_unit.setter
    def plot_2_y_unit(self, value):
        self.set_y_unit(plot_index=1, value=value)

    @property
    def plot_3_x_label(self):
        return self._x_label[2]

    @plot_3_x_label.setter
    def plot_3_x_label(self, value):
        self.set_x_label(plot_index=2, value=value)

    @property
    def plot_3_y_label(self):
        return self._y_label[2]

    @plot_3_y_label.setter
    def plot_3_y_label(self, value):
        self.set_y_label(plot_index=2, value=value)

    @property
    def plot_3_x_unit(self):
        return self._x_unit[2]

    @plot_3_x_unit.setter
    def plot_3_x_unit(self, value):
        self.set_x_unit(plot_index=2, value=value)

    @property
    def plot_3_y_unit(self):
        return self._y_unit[2]

    @plot_3_y_unit.setter
    def plot_3_y_unit(self, value):
        self.set_y_unit(plot_index=2, value=value)

    @property
    def plot_1_x_limits(self):
        return self._x_limits[0]

    @plot_1_x_limits.setter
    def plot_1_x_limits(self, limits=None):
        self.set_x_limits(plot_index=0, limits=limits)

    @property
    def plot_2_x_limits(self):
        return self._x_limits[1]

    @plot_2_x_limits.setter
    def plot_2_x_limits(self, limits=None):
        self.set_x_limits(plot_index=1, limits=limits)

    @property
    def plot_3_x_limits(self):
        return self._x_limits[2]

    @plot_3_x_limits.setter
    def plot_3_x_limits(self, limits=None):
        self.set_x_limits(plot_index=2, limits=limits)

    @property
    def plot_1_y_limits(self):
        return self._y_limits[0]

    @plot_1_y_limits.setter
    def plot_1_y_limits(self, limits=None):
        self.set_y_limits(plot_index=0, limits=limits)

    @property
    def plot_2_y_limits(self):
        return self._y_limits[1]

    @plot_2_y_limits.setter
    def plot_2_y_limits(self, limits=None):
        self.set_y_limits(plot_index=1, limits=limits)

    @property
    def plot_3_y_limits(self):
        return self._y_limits[2]

    @plot_3_y_limits.setter
    def plot_3_y_limits(self, limits=None):
        self.set_y_limits(plot_index=2, limits=limits)

    @property
    def plot_1_clear_old_data(self):
        return self.clear_old_data(plot_index=0)

    @property
    def plot_2_clear_old_data(self):
        return self.clear_old_data(plot_index=1)

    @property
    def plot_3_clear_old_data(self):
        return self.clear_old_data(plot_index=2)

    def plot_1_set_data(self, x=None, y=None, clear_old=True):
        self.set_data(x=x, y=y, clear_old=clear_old, plot_index=0)

    def plot_2_set_data(self, x=None, y=None, clear_old=True):
        self.set_data(x=x, y=y, clear_old=clear_old, plot_index=1)

    def plot_3_set_data(self, x=None, y=None, clear_old=True):
        self.set_data(x=x, y=y, clear_old=clear_old, plot_index=2)
    
    def plot_1_do_fit(self, fit_method):
        return self.do_fit(fit_method=fit_method, plot_index=0)
    
    def plot_2_do_fit(self, fit_method):
        return self.do_fit(fit_method=fit_method, plot_index=1)
    
    def plot_3_do_fit(self, fit_method):
        return self.do_fit(fit_method=fit_method, plot_index=2)
    
    def plot_1_save_data(self, postfix=''):
        return self.save_data(postfix=postfix, plot_index=0)
    
    def plot_2_save_data(self, postfix=''):
        return self.save_data(postfix=postfix, plot_index=1)
    
    def plot_3_save_data(self, postfix=''):
        return self.save_data(postfix=postfix, plot_index=2)
