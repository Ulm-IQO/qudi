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
from qudi.interface.microwave_interface import MicrowaveMode, TriggerEdge
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt

from qudi.core.module import LogicBase
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar


class OdmrLogic(LogicBase):
    """This is the Logic class for ODMR."""

    # declare connectors
    # odmrcounter = Connector(interface='ODMRCounterInterface')
    # fitlogic = Connector(interface='FitLogic')
    # microwave1 = Connector(interface='MicrowaveInterface')
    # savelogic = Connector(interface='SaveLogic')
    # taskrunner = Connector(interface='TaskRunner')

    # config option
    _mw_scan_mode = ConfigOption('scanmode',
                                 'LIST',
                                 missing='warn',
                                 converter=lambda x: MicrowaveMode[x.upper()])

    _cw_frequency = StatusVar(name='cw_frequency', default=2870e6)
    _cw_power = StatusVar(name='cw_power', default=-30)
    _scan_power = StatusVar(name='scan_power', default=-30)
    _scan_frequency_ranges = StatusVar(name='scan_frequency_ranges',
                                       default=[(2820e6, 2920e6, 101)])
    _run_time = StatusVar(name='run_time', default=60)
    _lines_to_average = StatusVar(name='lines_to_average', default=0)
    _sample_rate = StatusVar(name='sample_rate', default=200)
    _oversampling_factor = StatusVar(name='oversampling_factor', default=1)

    # Internal signals
    _sigNextLine = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigScanParametersUpdated = QtCore.Signal(dict)
    sigElapsedUpdated = QtCore.Signal(float, int)
    sigScanStateUpdated = QtCore.Signal(bool)
    sigCwStateUpdated = QtCore.Signal(bool)
    sigScanDataUpdated = QtCore.Signal(object, object)
    sigFitUpdated = QtCore.Signal(object, object, str, int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._threadlock = RecursiveMutex()

        self._elapsed_time = 0.0
        self._elapsed_sweeps = 0

        self._raw_data = None
        self._signal_data = None
        self._frequency_data = None
        self._fit_data = None

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Set/recall microwave parameters and check against constraints
        # ToDo: check all StatusVars
        # limits = self.get_hw_constraints()
        # self._cw_mw_frequency = limits.frequency_in_range(self.cw_mw_frequency)
        # self._cw_mw_power = limits.power_in_range(self.cw_mw_power)
        # self._scan_mw_power = limits.power_in_range(self.sweep_mw_power)

        # Elapsed measurement time and number of sweeps
        self._elapsed_time = 0.0
        self._elapsed_sweeps = 0

        # Initialize the ODMR data arrays (mean signal and sweep matrix)
        self._initialize_odmr_data()

        # Connect signals
        self._sigNextLine.connect(self._scan_odmr_line, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Stop measurement if it is still running
        self._sigNextLine.disconnect()
        if self.module_state() == 'locked':
            self.stop_odmr_scan()
        # Switch off microwave source for sure (also if CW mode is active or module is still locked)
        # ToDo: Switch off
        # self._mw_device.off()

    # @fc.constructor
    # def sv_set_fits(self, val):
    #     # Setup fit container
    #     fc = self.fitlogic().make_fit_container('ODMR sum', '1d')
    #     fc.set_units(['Hz', 'c/s'])
    #     if isinstance(val, dict) and len(val) > 0:
    #         fc.load_from_dict(val)
    #     else:
    #         d1 = OrderedDict()
    #         d1['Lorentzian dip'] = {
    #             'fit_function': 'lorentzian',
    #             'estimator': 'dip'
    #         }
    #         d1['Two Lorentzian dips'] = {
    #             'fit_function': 'lorentziandouble',
    #             'estimator': 'dip'
    #         }
    #         d1['N14'] = {
    #             'fit_function': 'lorentziantriple',
    #             'estimator': 'N14'
    #         }
    #         d1['N15'] = {
    #             'fit_function': 'lorentziandouble',
    #             'estimator': 'N15'
    #         }
    #         d1['Two Gaussian dips'] = {
    #             'fit_function': 'gaussiandouble',
    #             'estimator': 'dip'
    #         }
    #         default_fits = OrderedDict()
    #         default_fits['1d'] = d1
    #         fc.load_from_dict(default_fits)
    #     return fc
    #
    # @fc.representer
    # def sv_get_fits(self, val):
    #     """ save configured fits """
    #     if len(val.fit_list) > 0:
    #         return val.save_to_dict()
    #     else:
    #         return None

    def _initialize_odmr_data(self):
        """ Initializing the ODMR data arrays (signal and matrix). """
        self._frequency_data = [np.linspace(*r) for r in self._scan_frequency_ranges]

        # ToDo: Get proper channel constraints
        # constraints = self.hardware_constraints
        self._raw_data = dict()
        self._fit_data = dict()
        self._signal_data = dict()
        for channel in ('APD Counter', 'Photodiode'):
            self._raw_data[channel] = [
                np.full((freq_arr.size, 1), np.nan) for freq_arr in self._frequency_data
            ]
            self._signal_data[channel] = [
                np.zeros(freq_arr.size) for freq_arr in self._frequency_data
            ]
            self._fit_data[channel] = [None] * len(self._frequency_data)

    def _calculate_signal_data(self):
        for channel, raw_data_list in self._raw_data.items():
            for range_index, raw_data in enumerate(raw_data_list):
                masked_raw_data = np.ma.masked_invalid(raw_data)
                if masked_raw_data.compressed().size == 0:
                    arr_size = self._frequency_data[range_index].size
                    self._signal_data[channel][range_index] = np.zeros(arr_size)
                elif self._lines_to_average > 0:
                    self._signal_data[channel][range_index] = np.mean(
                        masked_raw_data[:, :self._lines_to_average],
                        axis=1
                    ).compressed()
                    if self._signal_data[channel][range_index].size == 0:
                        arr_size = self._frequency_data[range_index].size
                        self._signal_data[channel][range_index] = np.zeros(arr_size)
                else:
                    self._signal_data[channel][range_index] = np.mean(masked_raw_data,
                                                                      axis=1).compressed()

    def set_average_length(self, lines_to_average):
        """ Sets the number of lines to average for the sum of the data

        @param int lines_to_average: desired number of lines to average (0 means all)
        @return int: actually set lines to average
        """
        with self._threadlock:
            self._lines_to_average = int(lines_to_average)
            self._calculate_signal_data()
            self.sigScanDataUpdated.emit(self._signal_data, None)

    def set_runtime(self, runtime):
        """ Sets the runtime for ODMR measurement

        @param float runtime: desired runtime in seconds
        """
        with self._threadlock:
            try:
                self._run_time = float(runtime)
            except (TypeError, ValueError):
                self.log.exception('set_runtime failed:')
            self.sigScanParametersUpdated.emit({'run_time': self._run_time})

    def set_frequency_range(self, start, stop, points, index):
        with self._threadlock:
            if self.module_state() == 'locked':
                self.log.error('Unable to set frequency range. ODMR scan in progress.')
            else:
                try:
                    self._scan_frequency_ranges[index] = (start, stop, points)
                    self._frequency_data[index] = np.linspace(start, stop, points)
                    for channel, data_list in self._raw_data.items():
                        data_list[index] = np.full((points, 1), np.nan)
                        self._signal_data[channel][index] = np.zeros(points)
                except:
                    self.log.exception('Error while trying to set frequency range:')
            self.sigScanDataUpdated.emit(self._signal_data, self._raw_data)

    def set_clock_frequency(self, clock_frequency):
        """
        Sets the frequency of the counter clock

        @param int clock_frequency: desired frequency of the clock

        @return int: actually set clock frequency
        """
        # checks if scanner is still running
        if self.module_state() != 'locked' and isinstance(clock_frequency, (int, float)):
            self.clock_frequency = int(clock_frequency)
        else:
            self.log.warning('set_clock_frequency failed. Logic is either locked or input value is '
                             'no integer or float.')

        update_dict = {'clock_frequency': self.clock_frequency}
        self.sigParameterUpdated.emit(update_dict)
        return self.clock_frequency

    @property
    def oversampling(self):
        return self._oversampling

    @oversampling.setter
    def oversampling(self, oversampling):
        """
        Sets the frequency of the counter clock

        @param int oversampling: desired oversampling per frequency step
        """
        # checks if scanner is still running
        if self.module_state() != 'locked' and isinstance(oversampling, (int, float)):
            self._oversampling = int(oversampling)
            self._odmr_counter.oversampling = self._oversampling
        else:
            self.log.warning('setter of oversampling failed. Logic is either locked or input value is '
                             'no integer or float.')

        update_dict = {'oversampling': self._oversampling}
        self.sigParameterUpdated.emit(update_dict)

    def set_oversampling(self, oversampling):
        with self._threadlock:
            if self.module_state() == 'locked':
                self.log.error('Unable to set oversampling factor. ODMR scan in progress.')
            else:
                self._oversampling_factor = int(oversampling)
            update_dict = {'oversampling': self._oversampling_factor}
            self.sigParameterUpdated.emit(update_dict)

    def set_cw_parameters(self, frequency, power):
        """ Set the desired new cw mode parameters.

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._threadlock:
            try:
                constraints = self.get_hw_constraints()
                self._cw_frequency = constraints.frequency_in_range(frequency)
                self._cw_power = constraints.power_in_range(power)
                # ToDo: Hardware calls
                # self._mw_device.set_cw(frequency_to_set, power_to_set)
                # self._cw_mw_frequency, self._cw_mw_power = self._mw_device.get_cw()
            except:
                self.log.exception('Error while trying to set CW parameters:')
            param_dict = {'cw_frequency': self._cw_frequency, 'cw_power': self._cw_power}
            self.sigParameterUpdated.emit(param_dict)

    def toggle_cw_output(self, enable):
        # ToDo: implement
        self.sigCwStateUpdated.emit(enable)

    def mw_cw_on(self):
        """
        Switching on the mw source in cw mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        if self.module_state() == 'locked':
            self.log.error('Can not start microwave in CW mode. ODMRLogic is already locked.')
        else:
            self.cw_mw_frequency, \
            self.cw_mw_power, \
            mode = self._mw_device.set_cw(self.cw_mw_frequency, self.cw_mw_power)
            param_dict = {'cw_mw_frequency': self.cw_mw_frequency, 'cw_mw_power': self.cw_mw_power}
            self.sigParameterUpdated.emit(param_dict)
            if mode != 'cw':
                self.log.error('Switching to CW microwave output mode failed.')
            else:
                err_code = self._mw_device.cw_on()
                if err_code < 0:
                    self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def mw_sweep_on(self):
        """
        Switching on the mw source in list/sweep mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """

        limits = self.get_hw_constraints()
        param_dict = {}
        self.final_freq_list = []
        if self.mw_scanmode == MicrowaveMode.LIST:
            final_freq_list = []
            used_starts = []
            used_steps = []
            used_stops = []
            for mw_start, mw_stop, mw_step in zip(self.mw_starts, self.mw_stops, self.mw_steps):
                num_steps = int(np.rint((mw_stop - mw_start) / mw_step))
                end_freq = mw_start + num_steps * mw_step
                freq_list = np.linspace(mw_start, end_freq, num_steps + 1)

                # adjust the end frequency in order to have an integer multiple of step size
                # The master module (i.e. GUI) will be notified about the changed end frequency
                final_freq_list.extend(freq_list)

                used_starts.append(mw_start)
                used_steps.append(mw_step)
                used_stops.append(end_freq)

            final_freq_list = np.array(final_freq_list)
            if len(final_freq_list) >= limits.list_maxentries:
                self.log.error('Number of frequency steps too large for microwave device.')
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                return mode, is_running
            freq_list, self.sweep_mw_power, mode = self._mw_device.set_list(final_freq_list,
                                                                            self.sweep_mw_power)

            self.final_freq_list = np.array(freq_list)
            self.mw_starts = used_starts
            self.mw_stops = used_stops
            self.mw_steps = used_steps
            param_dict = {'mw_starts': used_starts, 'mw_stops': used_stops,
                          'mw_steps': used_steps, 'sweep_mw_power': self.sweep_mw_power}

            self.sigParameterUpdated.emit(param_dict)

        elif self.mw_scanmode == MicrowaveMode.SWEEP:
            if self.ranges == 1:
                mw_stop = self.mw_stops[0]
                mw_step = self.mw_steps[0]
                mw_start = self.mw_starts[0]

                if np.abs(mw_stop - mw_start) / mw_step >= limits.sweep_maxentries:
                    self.log.warning('Number of frequency steps too large for microwave device. '
                                     'Lowering resolution to fit the maximum length.')
                    mw_step = np.abs(mw_stop - mw_start) / (limits.list_maxentries - 1)
                    self.sigParameterUpdated.emit({'mw_steps': [mw_step]})

                sweep_return = self._mw_device.set_sweep(
                    mw_start, mw_stop, mw_step, self.sweep_mw_power)
                mw_start, mw_stop, mw_step, self.sweep_mw_power, mode = sweep_return

                param_dict = {'mw_starts': [mw_start], 'mw_stops': [mw_stop],
                              'mw_steps': [mw_step], 'sweep_mw_power': self.sweep_mw_power}
                self.final_freq_list = np.arange(mw_start, mw_stop + mw_step, mw_step)
            else:
                self.log.error('sweep mode only works for one frequency range.')

        else:
            self.log.error('Scanmode not supported. Please select SWEEP or LIST.')

        self.sigParameterUpdated.emit(param_dict)

        if mode != 'list' and mode != 'sweep':
            self.log.error('Switching to list/sweep microwave output mode failed.')
        elif self.mw_scanmode == MicrowaveMode.SWEEP:
            err_code = self._mw_device.sweep_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')
        else:
            err_code = self._mw_device.list_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def reset_sweep(self):
        """
        Resets the list/sweep mode of the microwave source to the first frequency step.
        """
        if self.mw_scanmode == MicrowaveMode.SWEEP:
            self._mw_device.reset_sweeppos()
        elif self.mw_scanmode == MicrowaveMode.LIST:
            self._mw_device.reset_listpos()
        return

    def mw_off(self):
        """ Switching off the MW source.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        error_code = self._mw_device.off()
        if error_code < 0:
            self.log.error('Switching off microwave source failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def _start_odmr_counter(self):
        """
        Starting the ODMR counter and set up the clock for it.

        @return int: error code (0:OK, -1:error)
        """

        clock_status = self._odmr_counter.set_up_odmr_clock(clock_frequency=self.clock_frequency)
        if clock_status < 0:
            return -1

        counter_status = self._odmr_counter.set_up_odmr()
        if counter_status < 0:
            self._odmr_counter.close_odmr_clock()
            return -1

        return 0

    def _stop_odmr_counter(self):
        """
        Stopping the ODMR counter.

        @return int: error code (0:OK, -1:error)
        """

        ret_val1 = self._odmr_counter.close_odmr()
        if ret_val1 != 0:
            self.log.error('ODMR counter could not be stopped!')
        ret_val2 = self._odmr_counter.close_odmr_clock()
        if ret_val2 != 0:
            self.log.error('ODMR clock could not be stopped!')

        # Check with a bitwise or:
        return ret_val1 | ret_val2

    def toggle_odmr_scan(self, start):
        """
        """
        # if start:
        #     self.start_odmr_scan()
        # else:
        #     self.stop_odmr_scan()
        self.sigScanStateUpdated.emit(start)

    def start_odmr_scan(self):
        """ Starting an ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start ODMR scan. Logic is already locked.')
                return -1

            self.set_trigger(self.mw_trigger_pol, self.clock_frequency)

            self.module_state.lock()
            self._clearOdmrData = False
            self.stopRequested = False
            self.fc.clear_result()

            self.elapsed_sweeps = 0
            self.elapsed_time = 0.0
            self._startTime = time.time()
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)

            odmr_status = self._start_odmr_counter()
            if odmr_status < 0:
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                self.module_state.unlock()
                return -1

            mode, is_running = self.mw_sweep_on()
            if not is_running:
                self._stop_odmr_counter()
                self.module_state.unlock()
                return -1

            self._initialize_odmr_plots()
            # initialize raw_data array
            estimated_number_of_lines = self.run_time * self.clock_frequency / self.odmr_plot_x.size
            estimated_number_of_lines = int(1.5 * estimated_number_of_lines)  # Safety
            if estimated_number_of_lines < self.number_of_lines:
                estimated_number_of_lines = self.number_of_lines
            self.log.debug('Estimated number of raw data lines: {0:d}'
                           ''.format(estimated_number_of_lines))
            self.odmr_raw_data = np.zeros(
                [estimated_number_of_lines,
                 len(self._odmr_counter.get_odmr_channels()),
                 self.odmr_plot_x.size]
            )
            self.sigNextLine.emit()
            return 0

    def continue_odmr_scan(self):
        """ Continue ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start ODMR scan. Logic is already locked.')
                return -1

            self.set_trigger(self.mw_trigger_pol, self.clock_frequency)

            self.module_state.lock()
            self.stopRequested = False
            self.fc.clear_result()

            self._startTime = time.time() - self.elapsed_time
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)

            odmr_status = self._start_odmr_counter()
            if odmr_status < 0:
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                self.module_state.unlock()
                return -1

            mode, is_running = self.mw_sweep_on()
            if not is_running:
                self._stop_odmr_counter()
                self.module_state.unlock()
                return -1

            self.sigNextLine.emit()
            return 0

    def stop_odmr_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        return 0

    def clear_odmr_data(self):
        """¨Set the option to clear the curret ODMR data.

        The clear operation has to be performed within the method
        _scan_odmr_line. This method just sets the flag for that. """
        with self.threadlock:
            if self.module_state() == 'locked':
                self._clearOdmrData = True
        return

    def _scan_odmr_line(self):
        """ Scans one line in ODMR

        (from mw_start to mw_stop in steps of mw_step)
        """
        with self.threadlock:
            # If the odmr measurement is not running do nothing
            if self.module_state() != 'locked':
                return

            # Stop measurement if stop has been requested
            if self.stopRequested:
                self.stopRequested = False
                self.mw_off()
                self._stop_odmr_counter()
                self.module_state.unlock()
                return

            # if during the scan a clearing of the ODMR data is needed:
            if self._clearOdmrData:
                self.elapsed_sweeps = 0
                self._startTime = time.time()

            # reset position so every line starts from the same frequency
            self.reset_sweep()

            # Acquire count data
            error, new_counts = self._odmr_counter.count_odmr(length=self.odmr_plot_x.size)

            if error:
                self.stopRequested = True
                self.sigNextLine.emit()
                return

            # Add new count data to raw_data array and append if array is too small
            if self._clearOdmrData:
                self.odmr_raw_data[:, :, :] = 0
                self._clearOdmrData = False
            if self.elapsed_sweeps == (self.odmr_raw_data.shape[0] - 1):
                expanded_array = np.zeros(self.odmr_raw_data.shape)
                self.odmr_raw_data = np.concatenate((self.odmr_raw_data, expanded_array), axis=0)
                self.log.warning('raw data array in ODMRLogic was not big enough for the entire '
                                 'measurement. Array will be expanded.\nOld array shape was '
                                 '({0:d}, {1:d}), new shape is ({2:d}, {3:d}).'
                                 ''.format(self.odmr_raw_data.shape[0] - self.number_of_lines,
                                           self.odmr_raw_data.shape[1],
                                           self.odmr_raw_data.shape[0],
                                           self.odmr_raw_data.shape[1]))

            # shift data in the array "up" and add new data at the "bottom"
            self.odmr_raw_data = np.roll(self.odmr_raw_data, 1, axis=0)

            self.odmr_raw_data[0] = new_counts

            # Add new count data to mean signal
            if self._clearOdmrData:
                self.odmr_plot_y[:, :] = 0

            if self.lines_to_average <= 0:
                self.odmr_plot_y = np.mean(
                    self.odmr_raw_data[:max(1, self.elapsed_sweeps), :, :],
                    axis=0,
                    dtype=np.float64
                )
            else:
                self.odmr_plot_y = np.mean(
                    self.odmr_raw_data[:max(1, min(self.lines_to_average, self.elapsed_sweeps)), :, :],
                    axis=0,
                    dtype=np.float64
                )

            # Set plot slice of matrix
            self.odmr_plot_xy = self.odmr_raw_data[:self.number_of_lines, :, :]

            # Update elapsed time/sweeps
            self.elapsed_sweeps += 1
            self.elapsed_time = time.time() - self._startTime
            if self.elapsed_time >= self.run_time:
                self.stopRequested = True
            # Fire update signals
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)
            self.sigOdmrPlotsUpdated.emit(self.odmr_plot_x, self.odmr_plot_y, self.odmr_plot_xy)
            self.sigNextLine.emit()
            return

    def get_odmr_channels(self):
        return self._odmr_counter.get_odmr_channels()

    def get_hw_constraints(self):
        """ Return the names of all ocnfigured fit functions.
        @return object: Hardware constraints object
        """
        constraints = self._mw_device.get_limits()
        return constraints

    def get_fit_functions(self):
        """ Return the hardware constraints/limits
        @return list(str): list of fit function names
        """
        return list(self.fc.fit_list)

    def do_fit(self, fit_function=None, x_data=None, y_data=None, channel_index=0, fit_range=0):
        """
        Execute the currently configured fit on the measurement data. Optionally on passed data
        """
        if (x_data is None) or (y_data is None):
            x_data = self.frequency_lists[fit_range]
            x_data_full_length = np.zeros(len(self.final_freq_list))
            # how to insert the data at the right position?
            start_pos = np.where(np.isclose(self.final_freq_list, self.mw_starts[fit_range]))[0][0]
            x_data_full_length[start_pos:(start_pos + len(x_data))] = x_data
            y_args = np.array([ind_list[0] for ind_list in np.argwhere(x_data_full_length)])
            y_data = self.odmr_plot_y[channel_index][y_args]
        if fit_function is not None and isinstance(fit_function, str):
            if fit_function in self.get_fit_functions():
                self.fc.set_current_fit(fit_function)
            else:
                self.fc.set_current_fit('No Fit')
                if fit_function != 'No Fit':
                    self.log.warning('Fit function "{0}" not available in ODMRLogic fit container.'
                                     ''.format(fit_function))

        self.odmr_fit_x, self.odmr_fit_y, result = self.fc.do_fit(x_data, y_data)
        key = 'channel: {0}, range: {1}'.format(channel_index, fit_range)
        if fit_function != 'No Fit':
            self.fits_performed[key] = (self.odmr_fit_x, self.odmr_fit_y, result, self.fc.current_fit)
        else:
            if key in self.fits_performed:
                self.fits_performed.pop(key)

        if result is None:
            result_str_dict = {}
        else:
            result_str_dict = result.result_str_dict
        self.sigOdmrFitUpdated.emit(
            self.odmr_fit_x, self.odmr_fit_y, result_str_dict, self.fc.current_fit)
        return

    def save_odmr_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')

        if tag is None:
            tag = ''

        for nch, channel in enumerate(self.get_odmr_channels()):
            # first save raw data for each channel
            if len(tag) > 0:
                filelabel_raw = '{0}_ODMR_data_ch{1}_raw'.format(tag, nch)
            else:
                filelabel_raw = 'ODMR_data_ch{0}_raw'.format(nch)

            data_raw = OrderedDict()
            data_raw['count data (counts/s)'] = self.odmr_raw_data[:self.elapsed_sweeps, nch, :]
            parameters = OrderedDict()
            parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
            parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
            parameters['Run Time (s)'] = self.run_time
            parameters['Number of frequency sweeps (#)'] = self.elapsed_sweeps
            parameters['Start Frequencies (Hz)'] = self.mw_starts
            parameters['Stop Frequencies (Hz)'] = self.mw_stops
            parameters['Step sizes (Hz)'] = self.mw_steps
            parameters['Clock Frequencies (Hz)'] = self.clock_frequency
            parameters['Channel'] = '{0}: {1}'.format(nch, channel)
            self._save_logic.save_data(data_raw,
                                       filepath=filepath,
                                       parameters=parameters,
                                       filelabel=filelabel_raw,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       timestamp=timestamp)

            # now create a plot for each scan range
            data_start_ind = 0
            for ii, frequency_arr in enumerate(self.frequency_lists):
                if len(tag) > 0:
                    filelabel = '{0}_ODMR_data_ch{1}_range{2}'.format(tag, nch, ii)
                else:
                    filelabel = 'ODMR_data_ch{0}_range{1}'.format(nch, ii)

                # prepare the data in a dict or in an OrderedDict:
                data = OrderedDict()
                data['frequency (Hz)'] = frequency_arr

                num_points = len(frequency_arr)
                data_end_ind = data_start_ind + num_points
                data['count data (counts/s)'] = self.odmr_plot_y[nch][data_start_ind:data_end_ind]
                data_start_ind += num_points

                parameters = OrderedDict()
                parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
                parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
                parameters['Run Time (s)'] = self.run_time
                parameters['Number of frequency sweeps (#)'] = self.elapsed_sweeps
                parameters['Start Frequency (Hz)'] = frequency_arr[0]
                parameters['Stop Frequency (Hz)'] = frequency_arr[-1]
                parameters['Step size (Hz)'] = frequency_arr[1] - frequency_arr[0]
                parameters['Clock Frequencies (Hz)'] = self.clock_frequency
                parameters['Channel'] = '{0}: {1}'.format(nch, channel)
                parameters['frequency range'] = str(ii)

                key = 'channel: {0}, range: {1}'.format(nch, ii)
                if key in self.fits_performed.keys():
                    parameters['Fit function'] = self.fits_performed[key][3]
                    for name, param in self.fits_performed[key][2].params.items():
                        parameters[name] = str(param)
                # add all fit parameter to the saved data:

                fig = self.draw_figure(nch, ii,
                                       cbar_range=colorscale_range,
                                       percentile_range=percentile_range)

                self._save_logic.save_data(data,
                                           filepath=filepath,
                                           parameters=parameters,
                                           filelabel=filelabel,
                                           fmt='%.6e',
                                           delimiter='\t',
                                           timestamp=timestamp,
                                           plotfig=fig)

        self.log.info('ODMR data saved to:\n{0}'.format(filepath))
        return

    def draw_figure(self, channel_number, freq_range, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        key = 'channel: {0}, range: {1}'.format(channel_number, freq_range)
        freq_data = self.frequency_lists[freq_range]
        lengths = [len(freq_range) for freq_range in self.frequency_lists]
        cumulative_sum = list()
        tmp_val = 0
        cumulative_sum.append(tmp_val)
        for length in lengths:
            tmp_val += length
            cumulative_sum.append(tmp_val)

        ind_start = cumulative_sum[freq_range]
        ind_end = cumulative_sum[freq_range + 1]
        count_data = self.odmr_plot_y[channel_number][ind_start:ind_end]
        fit_freq_vals = self.frequency_lists[freq_range]
        if key in self.fits_performed:
            fit_count_vals = self.fits_performed[key][2].eval()
        else:
            fit_count_vals = 0.0
        matrix_data = self.select_odmr_matrix_data(self.odmr_plot_xy, channel_number, freq_range)

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = np.array([np.min(matrix_data), np.max(matrix_data)])
        else:
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
        if hasattr(fit_count_vals, '__len__'):
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(
            matrix_data,
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

    def select_odmr_matrix_data(self, odmr_matrix, nch, freq_range):
        odmr_matrix_dp = odmr_matrix[:, nch]
        x_data = self.frequency_lists[freq_range]
        x_data_full_length = np.zeros(len(self.final_freq_list))
        mw_starts = [freq_arr[0] for freq_arr in self.frequency_lists]
        start_pos = np.where(np.isclose(self.final_freq_list,
                                        mw_starts[freq_range]))[0][0]
        x_data_full_length[start_pos:(start_pos + len(x_data))] = x_data
        y_args = np.array([ind_list[0] for ind_list in np.argwhere(x_data_full_length)])
        odmr_matrix_range = odmr_matrix_dp[:, y_args]
        return odmr_matrix_range

    def perform_odmr_measurement(self, freq_start, freq_step, freq_stop, power, channel, runtime,
                                 fit_function='No Fit', save_after_meas=True, name_tag=''):
        """ An independant method, which can be called by a task with the proper input values
            to perform an odmr measurement.

        @return
        """
        timeout = 30
        start_time = time.time()
        while self.module_state() != 'idle':
            time.sleep(0.5)
            timeout -= (time.time() - start_time)
            if timeout <= 0:
                self.log.error('perform_odmr_measurement failed. Logic module was still locked '
                               'and 30 sec timeout has been reached.')
                return tuple()

        # set all relevant parameter:
        self.set_sweep_parameters(freq_start, freq_stop, freq_step, power)
        self.set_runtime(runtime)

        # start the scan
        self.start_odmr_scan()

        # wait until the scan has started
        while self.module_state() != 'locked':
            time.sleep(1)
        # wait until the scan has finished
        while self.module_state() == 'locked':
            time.sleep(1)

        # Perform fit if requested
        if fit_function != 'No Fit':
            self.do_fit(fit_function, channel_index=channel)
            fit_params = self.fc.current_fit_param
        else:
            fit_params = None

        # Save data if requested
        if save_after_meas:
            self.save_odmr_data(tag=name_tag)

        return self.odmr_plot_x, self.odmr_plot_y, fit_params
