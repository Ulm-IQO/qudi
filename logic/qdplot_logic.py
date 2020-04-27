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
from core.configoption import ConfigOption
from core.util.mutex import RecursiveMutex
from logic.generic_logic import GenericLogic
from core.util import units


class QDPlotLogic(GenericLogic):
    """ This logic module helps display user data in plots, and makes it easy to save.
    
    There are phythonic setters and getters for each of the parameter and data. 
    They can be called by "plot_<plot_number>_parameter". plot_number ranges from 1 to 3.
    Parameters are: x_limits, y_limits, x_label, y_label, x_unit, y_unit, x_data, y_data, clear_old_data
    
    All parameters and data can also be interacted with by calling get_ and set_ functions.

    Example config for copy-paste:

    qdplotlogic:
        module.Class: 'qdplot_logic.QDPlotLogic'
        connect:
            save_logic: 'savelogic'
            fit_logic: 'fitlogic'
        default_plot_number: 3
    """
    sigPlotDataUpdated = QtCore.Signal(int, list, list, bool)
    sigPlotParamsUpdated = QtCore.Signal(int, dict)
    sigPlotNumberChanged = QtCore.Signal(int)
    sigFitUpdated = QtCore.Signal(int, np.ndarray, str, str)

    # declare connectors
    save_logic = Connector(interface='SaveLogic')
    fit_logic = Connector(interface='FitLogic')

    _default_plot_number = ConfigOption(name='default_plot_number', default=3)

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
        self.threadlock = RecursiveMutex()

        self._clear_old = list()
        self._x_limits = list()
        self._y_limits = list()
        self._x_label = list()
        self._y_label = list()
        self._x_unit = list()
        self._y_unit = list()
        self._x_data = list()
        self._y_data = list()
        self._fit_data = list()
        self._fit_results = list()
        self._fit_method = list()

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # Sanity-check ConfigOptions
        if not isinstance(self._default_plot_number, int) or self._default_plot_number < 1:
            self.log.warning('Invalid number of plots encountered in config. Falling back to 1.')
            self._default_plot_number = 1

        self._save_logic = self.save_logic()
        self._fit_logic = self.fit_logic()

        self._clear_old = list()
        self._x_limits = list()
        self._y_limits = list()
        self._x_label = list()
        self._y_label = list()
        self._x_unit = list()
        self._y_unit = list()
        self._x_data = list()
        self._y_data = list()
        self._fit_data = list()
        self._fit_results = list()
        self._fit_method = list()

        self.set_number_of_plots(self._default_plot_number)

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        for i in reversed(range(self.number_of_plots)):
            self.remove_plot(i)
        self._save_logic = None
        self._fit_logic = None

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

    @property
    def number_of_plots(self):
        with self.threadlock:
            return len(self._clear_old)

    @QtCore.Slot()
    def add_plot(self):
        with self.threadlock:
            self._clear_old.append(True)
            self._x_limits.append([-0.5, 0.5])
            self._y_limits.append([-0.5, 0.5])
            self._x_label.append('X')
            self._y_label.append('Y')
            self._x_unit.append('a.u.')
            self._y_unit.append('a.u.')
            self._x_data.append([np.zeros(1)])
            self._y_data.append([np.zeros(1)])
            self._fit_data.append(None)
            self._fit_results.append(None)
            self._fit_method.append('No Fit')
            plot_index = self.number_of_plots - 1

            self.sigPlotNumberChanged.emit(self.number_of_plots)
            self.sigPlotDataUpdated.emit(plot_index,
                                         self._x_data[plot_index],
                                         self._y_data[plot_index],
                                         self._clear_old[plot_index])
            if self._fit_method[plot_index] != 'No Fit':
                self.sigFitUpdated.emit(plot_index,
                                        self._fit_data[plot_index],
                                        self._fit_results[plot_index],
                                        self._fit_method[plot_index])
            params = {'x_label' : self._x_label[plot_index],
                      'y_label' : self._y_label[plot_index],
                      'x_unit'  : self._x_unit[plot_index],
                      'y_unit'  : self._y_unit[plot_index],
                      'x_limits': self._x_limits[plot_index],
                      'y_limits': self._y_limits[plot_index]}
            self.sigPlotParamsUpdated.emit(plot_index, params)

    @QtCore.Slot()
    @QtCore.Slot(int)
    def remove_plot(self, plot_index=None):
        with self.threadlock:
            if plot_index is None or plot_index == -1:
                plot_index = -1
            elif not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))

            del self._clear_old[plot_index]
            del self._x_limits[plot_index]
            del self._y_limits[plot_index]
            del self._x_label[plot_index]
            del self._y_label[plot_index]
            del self._x_unit[plot_index]
            del self._y_unit[plot_index]
            del self._x_data[plot_index]
            del self._y_data[plot_index]
            del self._fit_data[plot_index]
            del self._fit_results[plot_index]
            del self._fit_method[plot_index]
            self.sigPlotNumberChanged.emit(self.number_of_plots)

            update_range = (-1,) if plot_index == -1 else range(plot_index, self.number_of_plots)
            for i in update_range:
                self.sigPlotDataUpdated.emit(i, self._x_data[i], self._y_data[i], self._clear_old[i])
                self.sigFitUpdated.emit(i, self._fit_data[i], self._fit_results[i], self._fit_method[i])
                params = {'x_label': self._x_label[i],
                          'y_label': self._y_label[i],
                          'x_unit': self._x_unit[i],
                          'y_unit': self._y_unit[i],
                          'x_limits': self._x_limits[i],
                          'y_limits': self._y_limits[i]}
                self.sigPlotParamsUpdated.emit(i, params)

    @QtCore.Slot(int)
    def set_number_of_plots(self, plt_count):
        with self.threadlock:
            if not isinstance(plt_count, int):
                raise TypeError
            if plt_count < 1:
                self.log.error('number of plots must be integer >= 1.')
                return
            while self.number_of_plots < plt_count:
                self.add_plot()
            while self.number_of_plots > plt_count:
                self.remove_plot()
    
    def get_x_data(self, plot_index=0):
        """ Get the data of the x-axis being plotted.
        
        @param int plot_index: index of the plot in the range from 0 to number_of_plots-1
        @return np.ndarray or list of np.ndarrays x: data of the x-axis
        """
        with self.threadlock:
            if 0 <= plot_index < self.number_of_plots:
                return self._x_data[plot_index]
            self.log.error('Error while retrieving plot x_data. Plot index {0:d} out of bounds.'
                           ''.format(plot_index))
            return [np.zeros(0)]
    
    def get_y_data(self, plot_index=0):
        """ Get the data of the y-axis being plotted.
        
        @param int plot_index: index of the plot in the range from 0 to number_of_plots-1
        @return np.ndarray or list of np.ndarrays y: data of the y-axis
        """
        with self.threadlock:
            if 0 <= plot_index < self.number_of_plots:
                return self._y_data[plot_index]
            self.log.error('Error while retrieving plot y_data. Plot index {0:d} out of bounds.'
                           ''.format(plot_index))
            return [np.zeros(0)]

    def set_data(self, x=None, y=None, clear_old=True, plot_index=0, adjust_scale=True):
        """ Set the data to plot

        @param np.ndarray or list of np.ndarrays x: data of independents variable(s)
        @param np.ndarray or list of np.ndarrays y: data of dependent variable(s)
        @param bool clear_old: clear old plots in GUI if True
        @param int plot_index: index of the plot in the range from 0 to 2
        @param bool adjust_scale: Whether auto-scale should be performed after adding data or not.
        """
        with self.threadlock:
            if x is None:
                self.log.error('No x-values provided. Cannot set plot data.')
                return -1
            if y is None:
                self.log.error('No y-values provided. Cannot set plot data.')
                return -1
            if not (0 <= plot_index < self.number_of_plots):
                self.log.error(
                    'Plot index {0:d} out of bounds. To add a new plot, call set_number_of_plots(int) '
                    'or add_plot() first.'.format(plot_index))
                return -1

            self._clear_old[plot_index] = clear_old
            # check if input is only an array (single plot) or a list of arrays (one or several plots)
            if isinstance(x[0], np.ndarray):  # if x is an array, type(x[0]) is a np.float
                self._x_data[plot_index] = list(x)
                self._y_data[plot_index] = list(y)
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

            self.sigPlotDataUpdated.emit(plot_index,
                                         self._x_data[plot_index],
                                         self._y_data[plot_index],
                                         clear_old)
            self.sigPlotParamsUpdated.emit(plot_index,
                                           {'x_limits': self._x_limits[plot_index],
                                            'y_limits': self._y_limits[plot_index]})
            if adjust_scale:
                self.update_auto_range(plot_index, True, True)
            return 0

    @QtCore.Slot(str, int)
    def do_fit(self, fit_method, plot_index=0):
        """ Get the data of the x-axis being plotted.
        
        @param str fit_method: name of the fit_method, this needs to match the methods in
                               fit_container.
        @param int plot_index: index of the plot in the range from 0 to 2
        @return int plot_index, 3D np.ndarray fit_data, str result, str fit_method: result of fit
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError(
                    'Plot index {0:d} out of bounds. Unable to perform data fit.'.format(plot_index))
            # check that the fit_method is correct
            if fit_method is None or isinstance(fit_method, str):
                if fit_method not in self.fit_container.fit_list:
                    if fit_method is not None and fit_method != 'No Fit':
                        self.log.warning('Fit function "{0}" not available in fit container. Configure '
                                         'available fits first.'.format(fit_method))
                    fit_method = 'No Fit'
            else:
                raise TypeError('Parameter fit_method must be str or None type.')

            result = ''
            fit_data = list()

            # do one fit for each data set in the plot
            for data_set in range(len(self._x_data[plot_index])):
                x_data = self._x_data[plot_index][data_set]
                y_data = self._y_data[plot_index][data_set]

                self.fit_container.set_current_fit(fit_method)

                # only fit if the is enough data to actually do the fit
                if len(x_data) < 2 or len(y_data) < 2 or min(x_data) == max(x_data):
                    self.log.warning(
                        'The data you are trying to fit does not contain enough points for a fit.')
                    return (plot_index,
                            np.zeros(shape=(len(self._x_data[plot_index]), 2, 10)),
                            'results',
                            self.fit_container.current_fit)

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

    def get_fit_data(self, plot_index):
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return (self._fit_data[plot_index],
                    self._fit_results[plot_index],
                    self._fit_method[plot_index])

    def save_data(self, postfix='', plot_index=0):
        """ Save the data to a file.

        @param str postfix: an additional tag, which will be added to the filename upon save
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError(
                    'Plot index {0:d} out of bounds. Unable to save data.'.format(plot_index))

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
                ax1.plot(self._x_data[plot_index][data_set],
                         self._y_data[plot_index][data_set],
                         linestyle=':',
                         linewidth=1)

                if self._fit_data[plot_index] is not None:
                    ax1.plot(self._fit_data[plot_index][data_set][0],
                             self._fit_data[plot_index][data_set][1],
                             color='r',
                             marker='None',
                             linewidth=1.5,
                             label='fit')

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
                chunks = [entry_list[x:x + entries_per_col] for x in
                          range(0, len(entry_list), entries_per_col)]

                is_first_column = True  # first entry should contain header or \n

                for column in chunks:
                    max_length = max(column, key=len)  # get the longest entry
                    column_text = ''

                    for entry in column:
                        column_text += entry.rstrip() + '\n'

                    column_text = column_text[:-1]  # remove the last new line

                    heading = 'Fit results for method: {}'.format(
                        self._fit_method[plot_index]) if is_first_column else ''
                    column_text = heading + '\n' + column_text

                    ax1.text(1.00 + rel_offset,
                             0.99,
                             column_text,
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

    def get_limits(self, plot_index=0):
        with self.threadlock:
            return self.get_x_limits(plot_index), self.get_y_limits(plot_index)

    def set_limits(self, limits=None, plot_index=0):
        with self.threadlock:
            if limits is None:
                limits = (None, None)
            self.set_x_limits(limits[0], plot_index)
            self.set_y_limits(limits[1], plot_index)

    def get_x_limits(self, plot_index=0):
        """ Get the limits of the x-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return 2-element list: limits of the x-axis e.g. as [0, 1]
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._x_limits[plot_index]

    def set_x_limits(self, limits=None, plot_index=0):
        """Set the x_limits, to match the data (default) or to a specified new range

        @param float limits: 2-element list containing min and max x-values
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            if limits is not None:
                if isinstance(limits, (list, tuple, np.ndarray)) and len(limits) > 1:
                    self._x_limits[plot_index] = limits
                else:
                    self.log.error('limits need to be a list of at least 2 elements but is {}.'
                                   ''.format(limits))
                    return
            else:
                range_min = np.min([np.min(values) for values in self._x_data[plot_index]])
                range_max = np.max([np.max(values) for values in self._x_data[plot_index]])
                range_range = range_max - range_min
                self._x_limits[plot_index] = [range_min - 0.02 * range_range,
                                              range_max + 0.02 * range_range]
            self.sigPlotParamsUpdated.emit(plot_index, {'x_limits': self._x_limits[plot_index]})

    def get_y_limits(self, plot_index):
        """ Get the limits of the y-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return 2-element list: limits of the y-axis e.g. as [0, 1]
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._y_limits[plot_index]

    def set_y_limits(self, limits=None, plot_index=0):
        """Set the y_limits, to match the data (default) or to a specified new range

        @param float limits: 2-element list containing min and max y-values
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            if limits is not None:
                if isinstance(limits, (list, tuple, np.ndarray)) and len(limits) > 1:
                    self._y_limits[plot_index] = limits
                else:
                    self.log.error('limits need to be a list of at least 2 elements but is {}.'
                                   ''.format(limits))
            else:
                range_min = np.min([np.min(values) for values in self._y_data[plot_index]])
                range_max = np.max([np.max(values) for values in self._y_data[plot_index]])
                range_range = range_max - range_min
                self._y_limits[plot_index] = [range_min - 0.02 * range_range,
                                              range_max + 0.02 * range_range]
            self.sigPlotParamsUpdated.emit(plot_index, {'y_limits': self._y_limits[plot_index]})

    def get_labels(self, plot_index=0):
        with self.threadlock:
            return self.get_x_label(plot_index), self.get_y_label(plot_index)

    def set_labels(self, labels, plot_index=0):
        with self.threadlock:
            self.set_x_label(labels[0], plot_index)
            self.set_y_label(labels[1], plot_index)

    def get_x_label(self, plot_index=0):
        """ Get the label of the x-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current label of the x-axis
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._x_label[plot_index]
    
    def set_x_label(self, value, plot_index=0):
        """ Set the label of the x-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            self._x_label[plot_index] = str(value)
            self.sigPlotParamsUpdated.emit(plot_index, {'x_label': self._x_label[plot_index]})

    def get_y_label(self, plot_index=0):
        """ Get the label of the y-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current label of the y-axis
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._y_label[plot_index]
    
    def set_y_label(self, value, plot_index=0):
        """ Set the label of the y-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            self._y_label[plot_index] = str(value)
            self.sigPlotParamsUpdated.emit(plot_index, {'y_label': self._y_label[plot_index]})

    def get_units(self, plot_index=0):
        with self.threadlock:
            return self.get_x_unit(plot_index), self.get_y_unit(plot_index)

    def set_units(self, units, plot_index=0):
        with self.threadlock:
            self.set_x_unit(units[0], plot_index)
            self.set_y_unit(units[1], plot_index)

    def get_x_unit(self, plot_index=0):
        """ Get the unit of the x-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current unit of the x-axis
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._x_unit[plot_index]
    
    def set_x_unit(self, value, plot_index=0):
        """ Set the unit of the x-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            self._x_unit[plot_index] = str(value)
            self.sigPlotParamsUpdated.emit(plot_index, {'x_unit': self._x_unit[plot_index]})

    def get_y_unit(self, plot_index=0):
        """ Get the unit of the y-axis being plotted.

        @param int plot_index: index of the plot in the range from 0 to 2
        @return str: current unit of the y-axis
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._y_unit[plot_index]
    
    def set_y_unit(self, value, plot_index=0):
        """ Set the unit of the y-axis being plotted.

        @param str value: label to be set
        @param int plot_index: index of the plot in the range for 0 to 2
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            self._y_unit[plot_index] = str(value)
            self.sigPlotParamsUpdated.emit(plot_index, {'y_unit': self._y_unit[plot_index]})

    def clear_old_data(self, plot_index=0):
        """ Get the information, if the previous plots in the windows are kept or not

        @param int plot_index: index of the plot in the range from 0 to 2
        @return bool: are the plots currently in the GUI kept or not
        """
        with self.threadlock:
            if not (0 <= plot_index < self.number_of_plots):
                raise IndexError('Plot index {0:d} out of bounds.'.format(plot_index))
            return self._clear_old[plot_index]

    @QtCore.Slot(int, dict)
    def update_plot_parameters(self, plot_index, params):
        with self.threadlock:
            if 0 <= plot_index < len(self._x_data):
                if 'x_label' in params:
                    self.set_x_label(params['x_label'], plot_index)
                if 'x_unit' in params:
                    self.set_x_unit(params['x_unit'], plot_index)
                if 'y_label' in params:
                    self.set_y_label(params['y_label'], plot_index)
                if 'y_unit' in params:
                    self.set_y_unit(params['y_unit'], plot_index)
                if 'x_limits' in params:
                    self.set_x_limits(params['x_limits'], plot_index)
                if 'y_limits' in params:
                    self.set_y_limits(params['y_limits'], plot_index)

    @QtCore.Slot(int, bool, bool)
    def update_auto_range(self, plot_index, auto_x, auto_y):
        with self.threadlock:
            if 0 <= plot_index < len(self._x_data):
                if auto_x:
                    self.set_x_limits(plot_index=plot_index)
                if auto_y:
                    self.set_y_limits(plot_index=plot_index)
