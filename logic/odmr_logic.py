# -*- coding: utf-8 -*-

"""
This file contains the Qudi Logic module base class.

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
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt
import lmfit

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex

class ODMRLogic(GenericLogic):

    """This is the Logic class for ODMR."""
    _modclass = 'odmrlogic'
    _modtype = 'logic'
    # declare connectors
    _connectors = {
        'odmrcounter': 'ODMRCounterInterface',
        'fitlogic': 'FitLogic',
        'microwave1': 'mwsourceinterface',
        'savelogic': 'SaveLogic',
        'taskrunner': 'TaskRunner'
    }

    sigNextLine = QtCore.Signal()
    sigOdmrStarted = QtCore.Signal()
    sigOdmrStopped = QtCore.Signal()
    sigOdmrPlotUpdated = QtCore.Signal()
    # an arbitrary object will be emitted
    sigOdmrFitUpdated = QtCore.Signal()
    sigOdmrMatrixUpdated = QtCore.Signal()
    sigOdmrFinished = QtCore.Signal()
    sigOdmrElapsedTimeChanged = QtCore.Signal()
    sigODMRMatrixAxesChanged = QtCore.Signal()
    sigMicrowaveCWModeChanged = QtCore.Signal(bool)
    sigMicrowaveListModeChanged = QtCore.Signal(bool)
    # Here all parameter changes will be emitted. Look in the code for an example.
    sigParameterChanged = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        # number of lines in the matrix plot
        self.number_of_lines = 50
        self.threadlock = Mutex()
        self.stopRequested = False
        self._clear_odmr_plots = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._mw_device = self.get_connector('microwave1')
        self._fit_logic = self.get_connector('fitlogic')
        self._odmr_counter = self.get_connector('odmrcounter')
        self._save_logic = self.get_connector('savelogic')
        self._taskrunner = self.get_connector('taskrunner')

        config = self.getConfiguration()
        self.limits = self._mw_device.get_limits()
        if 'scanmode' in config and ('sweep' in config['scanmode'] or 'SWEEP' in config['scanmode']):
            self.scanmode = MicrowaveMode.SWEEP
        elif 'scanmode' in config and ('list' in config['scanmode'] or 'LIST' in config['scanmode']):
            self.scanmode = MicrowaveMode.LIST
        else:
            self.scanmode = MicrowaveMode.LIST
            self.log.warning('No scanmode defined in config for odmr_logic module.\n'
                             'Falling back to list mode.')

        self.fc = self._fit_logic.make_fit_container('ODMR sum', '1d')
        self.fc.set_units(['Hz', 'c/s'])

        # theoretically this can be changed, but the current counting scheme willnot support that
        self.MW_trigger_pol = TriggerEdge.RISING

        self._odmrscan_counter = 0
        self._clock_frequency = 200     # in Hz

        self.mw_frequency = self.limits.frequency_in_range(2870e6)

        self.mw_power = self.limits.power_in_range(-30)
        self.mw_start = self.limits.frequency_in_range(2800e6)
        self.mw_stop = self.limits.frequency_in_range(2950e6)
        self.mw_step = self.limits.list_step_in_range(2e6)
        self.run_time = 10          # in s
        self.elapsed_time = 0       # in s

        self.saveRawData = False  # flag for saving raw data

        # load parameters stored in app state store
        if 'clock_frequency' in self._statusVariables:
            self._clock_frequency = self._statusVariables['clock_frequency']

        if 'mw_frequency' in self._statusVariables:
            self.mw_frequency = self.limits.frequency_in_range(
                self._statusVariables['mw_frequency'])

        if 'mw_power' in self._statusVariables:
            self.mw_power = self.limits.power_in_range(self._statusVariables['mw_power'])

        if 'mw_start' in self._statusVariables:
            self.mw_start = self.limits.frequency_in_range(self._statusVariables['mw_start'])

        if 'mw_stop' in self._statusVariables:
            self.mw_stop = self.limits.frequency_in_range(self._statusVariables['mw_stop'])

        if 'mw_step' in self._statusVariables:
            self.mw_step = self.limits.list_step_in_range(self._statusVariables['mw_step'])

        if 'run_time' in self._statusVariables:
            self.run_time = self._statusVariables['run_time']

        if 'saveRawData' in self._statusVariables:
            self.saveRawData = self._statusVariables['saveRawData']

        if 'number_of_lines' in self._statusVariables:
            self.number_of_lines = self._statusVariables['number_of_lines']

        if 'fits' in self._statusVariables and isinstance(self._statusVariables['fits'], dict):
            self.fc.load_from_dict(self._statusVariables['fits'])
        else:
            d1 = OrderedDict()
            d1['Lorentzian dip'] = {
                'fit_function': 'lorentzian',
                'estimator': 'dip'
                }
            d1['Two Lorentzian dips'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'dip'
                }
            d1['N14'] = {
                'fit_function': 'lorentziantriple',
                'estimator': 'N14'
                }
            d1['N15'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'N15'
                }
            d1['Two Gaussian dips'] = {
                'fit_function': 'gaussiandouble',
                'estimator': 'dip'
                }
            default_fits = OrderedDict()
            default_fits['1d'] = d1
            self.fc.load_from_dict(default_fits)

        self.sigNextLine.connect(self._scan_ODMR_line, QtCore.Qt.QueuedConnection)

        # Initalize the ODMR plot and matrix image
        self._mw_frequency_list = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.ODMR_fit_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step / 10.)
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()

        # setting to low power and turning off the input during activation
        self.set_frequency(frequency=self.mw_frequency)
        self.set_power(power=self.mw_power)
        self.MW_off()
        self._mw_device.set_ext_trigger(self.MW_trigger_pol)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # save parameters stored in app state store
        self._statusVariables['clock_frequency'] = self._clock_frequency
        self._statusVariables['mw_frequency'] = self.mw_frequency
        self._statusVariables['mw_power'] = self.mw_power
        self._statusVariables['mw_start'] = self.mw_start
        self._statusVariables['mw_stop'] = self.mw_stop
        self._statusVariables['mw_step'] = self.mw_step
        self._statusVariables['run_time'] = self.run_time
        self._statusVariables['saveRawData'] = self.saveRawData
        self._statusVariables['number_of_lines'] = self.number_of_lines
        if len(self.fc.fit_list) > 0:
            self._statusVariables['fits'] = self.fc.save_to_dict()

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """

        self._clock_frequency = int(clock_frequency)

        # checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            dict_param = {'clock_frequency': self._clock_frequency}
            self.sigParameterChanged.emit(dict_param)
            return 0

    def _start_odmr_counter(self):
        """ Starting the ODMR counter and set up the clock for it.

        @return int: error code (0:OK, -1:error)
        """

        self.lock()
        clock_status = self._odmr_counter.set_up_odmr_clock(clock_frequency=self._clock_frequency)
        if clock_status < 0:
            self.unlock()
            return -1

        counter_status = self._odmr_counter.set_up_odmr()
        if counter_status < 0:
            self._odmr_counter.close_odmr_clock()
            self.unlock()
            return -1

        self.sigMicrowaveCWModeChanged.emit(False)
        self.sigMicrowaveListModeChanged.emit(True)
        return 0

    def _stop_odmr_counter(self):
        """ Stopping the ODMR counter. """

        ret_val1 = self._odmr_counter.close_odmr()
        if ret_val1 != 0:
            self.log.error('ODMR counter could not be stopped!')
        ret_val2 = self._odmr_counter.close_odmr_clock()
        if ret_val1 != 0:
            self.log.error('ODMR clock could not be stopped!')

        # Check with a bitwise or:
        return ret_val1 | ret_val2

    def start_odmr_scan(self):
        """ Starting an ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        self._clear_odmr_plots = False
        self._odmrscan_counter = 0
        self._startTime = time.time()
        self.elapsed_time = 0
        self.sigOdmrElapsedTimeChanged.emit()
        self.mw_start = self.limits.frequency_in_range(self.mw_start)
        self.mw_stop = self.limits.frequency_in_range(self.mw_stop)

        if self.scanmode == MicrowaveMode.SWEEP:
            self.mw_step = self.limits.sweep_step_in_range(self.mw_step)
        elif self.scanmode == MicrowaveMode.LIST:
            self.mw_step = self.limits.list_step_in_range(self.mw_step)

        param_dict = {'mw_start': self.mw_start, 'mw_step':self.mw_step,
                      'mw_stop': self.mw_stop}
        self.sigParameterChanged.emit(param_dict)

        self._mw_frequency_list = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)

        self.ODMR_fit_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step / 10.)
        self.fc.clear_result()

        if self.saveRawData:
            # All that is necesarry fo saving of raw data:
            # length of req list
            self._mw_frequency_list_length = int(self._mw_frequency_list.shape[0])
            # time for one line
            self._ODMR_line_time = self._mw_frequency_list_length / self._clock_frequency
            # amout of lines done during run_time
            self._ODMR_line_count = self.run_time / self._ODMR_line_time
            # list used to store the raw data, is saved in seperate file for post prossesing initiallized with -1
            self.ODMR_raw_data = np.full((self._mw_frequency_list_length, self._ODMR_line_count), -1)
            self.log.info('Raw data saving...')
        else:
            self.log.info('Raw data NOT saved.')

        odmr_status = self._start_odmr_counter()
        if odmr_status < 0:
            self.sigMicrowaveCWModeChanged.emit(False)
            self.sigMicrowaveListModeChanged.emit(False)
            self.sigOdmrStopped.emit()
            return -1

        if self.scanmode == MicrowaveMode.SWEEP:
            if len(self._mw_frequency_list) >= self.limits.sweep_maxentries:
                self.stopRequested = True
                self.sigNextLine.emit()
                return -1
            n = self._mw_device.set_sweep(self.mw_start, self.mw_stop, self.mw_step, self.mw_power)
            return_val = n - len(self._mw_frequency_list)

        elif self.scanmode == MicrowaveMode.LIST:
            if len(self._mw_frequency_list) >= self.limits.list_maxentries:
                self.stopRequested = True
                self.sigNextLine.emit()
                return -1
            return_val = self._mw_device.set_list(self._mw_frequency_list, self.mw_power)

        if return_val != 0:
            self.stopRequested = True
        else:
            param_dict = {'mw_power': self.mw_power,
                          '_mw_frequency_list': self._mw_frequency_list}
            self.sigParameterChanged.emit(param_dict)

            if self.scanmode == MicrowaveMode.SWEEP:
                self._mw_device.sweep_on()
            elif self.scanmode == MicrowaveMode.LIST:
                self._mw_device.list_on()

        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()
        self.sigOdmrStarted.emit()
        self.sigNextLine.emit()
        return return_val

    def continue_odmr_scan(self):
        """ Continue ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        self._startTime = time.time() - self.elapsed_time

        odmr_status = self._start_odmr_counter()
        if odmr_status < 0:
            self.sigMicrowaveCWModeChanged.emit(False)
            self.sigMicrowaveListModeChanged.emit(False)
            self.sigOdmrStopped.emit()
            return -1

        if self.scanmode == MicrowaveMode.SWEEP:
            n = self._mw_device.set_sweep(self.mw_start, self.mw_stop, self.mw_step, self.mw_power)
            return_val = n - len(self._mw_frequency_list)
        elif self.scanmode == MicrowaveMode.LIST:
            return_val = self._mw_device.set_list(self._mw_frequency_list, self.mw_power)

        if return_val != 0:
            self.stopRequested = True
        else:
            if self.scanmode == MicrowaveMode.SWEEP:
                self._mw_device.sweep_on()
            elif self.scanmode == MicrowaveMode.LIST:
                self._mw_device.list_on()
        self.sigOdmrStarted.emit()
        self.sigNextLine.emit()
        return return_val

    def stop_odmr_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        return 0

    def _initialize_ODMR_plot(self):
        """ Initializing the ODMR line plot. """
        self.ODMR_plot_x = self._mw_frequency_list
        self.ODMR_plot_y = np.zeros(self._mw_frequency_list.shape)
        self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)
        self.sigOdmrPlotUpdated.emit()

    def _initialize_ODMR_matrix(self):
        """ Initializing the ODMR matrix plot. """
        self.ODMR_plot_xy = np.zeros((self.number_of_lines, len(self._mw_frequency_list)))
        self.sigODMRMatrixAxesChanged.emit()

    def clear_odmr_plots(self):
        """¨Set the option to clear the curret ODMR plot.

        The clear operation has to be performed within the method
        _scan_ODMR_line. This method just sets the flag for that. """
        self._clear_odmr_plots = True

    def _scan_ODMR_line(self):
        """ Scans one line in ODMR

        (from mw_start to mw_stop in steps of mw_step)
        """
        if self.stopRequested:
            with self.threadlock:
                self.MW_off()
                # no need to check the return value, since the logic will be
                # anyway released after the this.
                self._stop_odmr_counter()
                self.stopRequested = False
                self.unlock()
                self.sigOdmrPlotUpdated.emit()
                self.sigOdmrMatrixUpdated.emit()

                self.sigMicrowaveCWModeChanged.emit(False)
                self.sigMicrowaveListModeChanged.emit(False)
                self.sigOdmrStopped.emit()
                return

        # reset position so every line starts from the same frequency
        if self.scanmode == MicrowaveMode.SWEEP:
            self._mw_device.reset_sweep()
        elif self.scanmode == MicrowaveMode.LIST:
            self._mw_device.reset_listpos()
        new_counts = self._odmr_counter.count_odmr(length=len(self._mw_frequency_list))
        if new_counts[0] == -1:
            self.stopRequested = True
            self.sigNextLine.emit()
            return

        # if during the scan a clearing of the ODMR plots is needed:
        if self._clear_odmr_plots:
            self._odmrscan_counter = 0
            self._initialize_ODMR_plot()
            self._initialize_ODMR_matrix()
            self._clear_odmr_plots = False

        self.ODMR_plot_y = (self._odmrscan_counter * self.ODMR_plot_y + new_counts) / (self._odmrscan_counter + 1)

        # React on the case, when the number of matrix lines have changed during
        # the scan. Essentially, there are three cases which can happen:
        curr_num_lines = np.shape(self.ODMR_plot_xy)[0]
        if curr_num_lines > self.number_of_lines:

            self.ODMR_plot_xy = np.vstack((new_counts, self.ODMR_plot_xy[:self.number_of_lines - 1, :]))

            # It is very necessary that the matrix will be updated BEFORE the
            # axes are adjusted, otherwise, there the display will not fit with
            # the data!
            self.sigOdmrMatrixUpdated.emit()
            self.sigODMRMatrixAxesChanged.emit()

        elif np.shape(self.ODMR_plot_xy)[0] < self.number_of_lines:
            new_matrix = np.zeros((self.number_of_lines, len(self._mw_frequency_list)))
            new_matrix[1:curr_num_lines + 1, :] = self.ODMR_plot_xy
            new_matrix[0, :] = new_counts
            self.ODMR_plot_xy = new_matrix

            # It is very necessary that the matrix will be updated BEFORE the
            # axes are adjusted, otherwise, there the display will not fit with
            # the data!
            self.sigOdmrMatrixUpdated.emit()
            self.sigODMRMatrixAxesChanged.emit()

        else:
            self.ODMR_plot_xy = np.vstack((new_counts, self.ODMR_plot_xy[:-1, :]))
            self.sigOdmrMatrixUpdated.emit()

        if self.saveRawData:
            self.ODMR_raw_data[:, self._odmrscan_counter] = new_counts  # adds the ne odmr line to the overall np.array

        self._odmrscan_counter += 1
        self.elapsed_time = time.time() - self._startTime
        self.sigOdmrElapsedTimeChanged.emit()
        if self.elapsed_time >= self.run_time:
            self.stopRequested = True
            self.sigOdmrFinished.emit()

        self.sigOdmrPlotUpdated.emit()
        self.sigNextLine.emit()

    def set_power(self, power=None):
        """ Forwarding the desired new power from the GUI to the MW source.

        @param float power: power set at the GUI

        @return int: error code (0:OK, -1:error)
        """
        if isinstance(power, (int, float)):
            self.mw_power = self.limits.power_in_range(power)
        else:
            return -1

        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._mw_device.set_power(
                self.limits.power_in_range(power))
            if error_code == 0:
                param_dict = {'mw_power': self.mw_power}
                self.sigParameterChanged.emit(param_dict)
            return error_code

    def get_power(self):
        """ Getting the current power from the MW source.

        @return float: current power of the MW source
        """
        power = self._mw_device.get_power()
        return power

    def set_frequency(self, frequency=None):
        """ Forwarding the desired new frequency from the GUI to the MW source.

        @param float frequency: frequency set at the GUI

        @return int: error code (0:OK, -1:error)
        """
        if isinstance(frequency, (int, float)):
            self.mw_frequency = self.limits.frequency_in_range(frequency)
        else:
            return -1
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._mw_device.set_frequency(
                self.limits.frequency_in_range(frequency))
            if error_code == 0:
                param_dict = {'mw_frequency': self.mw_frequency}
                self.sigParameterChanged.emit(param_dict)
            return error_code

    def get_frequency(self):
        """ Getting the current frequency from the MW source.

        @return float: current frequency of the MW source
        """
        frequency = self._mw_device.get_frequency()  # divided by 1e6 is now done in gui!!
        return frequency

    def MW_on(self):
        """ Switching on the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._mw_device.on()

        self.sigMicrowaveCWModeChanged.emit(True)
        self.sigMicrowaveListModeChanged.emit(False)

        return error_code

    def MW_off(self):
        """ Switching off the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._mw_device.off()

        self.sigMicrowaveCWModeChanged.emit(False)
        self.sigMicrowaveListModeChanged.emit(False)

        return error_code

    def get_fit_functions(self):
        """ Return the names of all ocnfigured fit functions.
        @return list(str): list of fit function names
        """
        return self.fc.fit_list.keys()

    def do_fit(self):
        """ Execute the currently configured fit
        """
        x_data = self._mw_frequency_list
        y_data = self.ODMR_plot_y

        self.ODMR_fit_x, self.ODMR_fit_y, result = self.fc.do_fit(x_data, y_data)

        self.sigOdmrFitUpdated.emit()
        self.sigOdmrPlotUpdated.emit()

    def save_ODMR_Data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""

        # three paths to save the raw data (if desired), the odmr scan data and
        # the matrix data.
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath2 = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath3 = self._save_logic.get_path_for_module(module_name='ODMR')

        timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_ODMR_data'
            filelabel2 = tag + '_ODMR_data_matrix'
            filelabel3 = tag + '_ODMR_data_raw'
        else:
            filelabel = 'ODMR_data'
            filelabel2 = 'ODMR_data_matrix'
            filelabel3 = 'ODMR_data_raw'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data2 = OrderedDict()
        data3 = OrderedDict()
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        matrix_data = self.ODMR_plot_xy  # the data in the matrix plot
        data['frequency values (Hz)'] = np.array(freq_data)
        data['count data (counts/s)'] = np.array(count_data)
        data2['count data (counts/s)'] = np.array(matrix_data)  # saves the raw data used in the matrix NOT all only the size of the matrix

        parameters = OrderedDict()
        parameters['Microwave Power (dBm)'] = self.mw_power
        parameters['Run Time (s)'] = self.run_time
        parameters['Start Frequency (Hz)'] = self.mw_start
        parameters['Stop Frequency (Hz)'] = self.mw_stop
        parameters['Step size (Hz)'] = self.mw_step
        parameters['Clock Frequency (Hz)'] = self._clock_frequency
        parameters['Number of matrix lines (#)'] = self.number_of_lines
        if self.fc.current_fit != 'No Fit':
            parameters['Fit function'] = self.fc.fit_list[self.fc.current_fit]['fit_name']

        # add all fit parameter to the saved data:
        for name, param in self.fc.current_fit_param.items():
            parameters[name] = str(param)

        fig = self.draw_figure(cbar_range=colorscale_range,
                               percentile_range=percentile_range
                               )

        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   timestamp=timestamp,
                                   plotfig=fig)

        self._save_logic.save_data(data2,
                                   filepath=filepath2,
                                   parameters=parameters,
                                   filelabel=filelabel2,
                                   timestamp=timestamp)

        self.log.info('ODMR data saved to:\n{0}'.format(filepath))

        if self.saveRawData:
            raw_data = self.ODMR_raw_data  # array cotaining ALL messured data
            data3['count data'] = np.array(raw_data)  # saves the raw data, ALL of it so keep an eye on performance
            self._save_logic.save_data(data3,
                                       filepath=filepath3,
                                       parameters=parameters,
                                       filelabel=filelabel3,
                                       timestamp=timestamp)

            self.log.info('Raw data succesfully saved.')
        else:
            self.log.info('Raw data is NOT saved')

    def draw_figure(self, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        fit_freq_vals = self.ODMR_fit_x
        fit_count_vals = self.ODMR_fit_y
        matrix_data = self.ODMR_plot_xy

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = [np.min(matrix_data), np.max(matrix_data)]

        # Convert cbar_range to numpy array for division in the SI prefix calculation
        cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(matrix_data,
                                      cmap=plt.get_cmap('inferno'),  # reference the right place in qd
                                      origin='lower',
                                      vmin=cbar_range[0],
                                      vmax=cbar_range[1],
                                      extent=[np.min(freq_data),
                                              np.max(freq_data),
                                              0,
                                              self.number_of_lines
                                              ],
                                      aspect='auto',
                                      interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig

    def perform_odmr_measurement(self, freq_start, freq_step, freq_stop, power,
                                 runtime, fit_function='No Fit',
                                 save_after_meas=True, name_tag=''):
        """ An independant method, which can be called by a task with the proper input values
            to perform an odmr measurement.

        @return dict: a parameter container, containing all measurement results
                      of the ODMR measurement.
        """

        while self.getState() != 'idle':
            time.sleep(1)
            print('wait until ready')

        # set all relevant parameter:
        self.mw_start = freq_start
        self.mw_step = freq_step
        self.mw_stop = freq_stop
        self.mw_power = power
        self.run_time = runtime

        # start the scan
        self.start_odmr_scan()

        # check just the state of the optimizer
        while self.getState() != 'idle' and not self.stopRequested:
            time.sleep(1)

        old_fit = self.fc.current_fit
        self.fc.set_current_fit(fit_function)
        self.do_fit()
        meas_param['ODMR frequency start (Hz)'] = self.mw_start
        meas_param['ODMR frequency step (Hz)'] = self.mw_step
        meas_param['ODMR frequency stop (Hz)'] = self.mw_stop
        meas_param['ODMR power (dBm)'] = self.mw_power
        meas_param['ODMR run time (s)'] = self.run_time
        meas_param['ODMR measurement saved separetely'] = save_after_meas

        if save_after_meas:
            timestamp = datetime.datetime.now()
            self.save_ODMR_Data(tag=name_tag)
            meas_param['ODMR measurement saved at time'] = timestamp

        self.fc.set_current_fit(old_fit)
        return meas_param
