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

from PySide2 import QtCore
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt

from qudi.core import qudi_slot
from qudi.core.module import LogicBase
from qudi.core.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar


class OdmrLogic(LogicBase):
    """ This is the Logic class for CW ODMR measurements """

    # declare connectors
    _cw_microwave_source = Connector(name='cw_microwave_source',
                                     interface='MicrowaveInterface',
                                     optional=True)
    _odmr_scanner = Connector(name='odmr_scanner',
                              interface='OdmrNicardScannerInterfuse')

    _cw_frequency = StatusVar(name='cw_frequency', default=2870e6)
    _cw_power = StatusVar(name='cw_power', default=-30)
    _scan_power = StatusVar(name='scan_power', default=-30)
    _scan_frequency_ranges = StatusVar(name='scan_frequency_ranges',
                                       default=[(2820e6, 2920e6, 101)])
    _run_time = StatusVar(name='run_time', default=60)
    _lines_to_average = StatusVar(name='lines_to_average', default=0)
    _data_rate = StatusVar(name='data_rate', default=200)
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
        self.__estimated_lines = 0
        self.__start_time = 0.0

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
        # limits = self.microwave_constraints
        # self._cw_mw_frequency = limits.frequency_in_range(self.cw_mw_frequency)
        # self._cw_mw_power = limits.power_in_range(self.cw_mw_power)
        # self._scan_mw_power = limits.power_in_range(self.sweep_mw_power)

        # Elapsed measurement time and number of sweeps
        self._elapsed_time = 0.0
        self._elapsed_sweeps = 0
        self.__estimated_lines = 0
        self.__start_time = 0.0

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
        self._odmr_scanner().off()

    # @fc.constructor
    # def sv_set_fits(self, val):
    #     # Setup fit container
    #     fc = self.fitlogic().make_fit_container('ODMR sum', '1d')
    #     fc.set_units(['Hz', 'c/s'])
    #     if isinstance(val, dict) and len(val) > 0:
    #         fc.load_from_dict(val)
    #     else:
    #         d1 = dict()
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
    #         default_fits = dict()
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
        """ Initializing the ODMR data arrays (signal and raw data matrix). """
        self._frequency_data = [np.linspace(*r) for r in self._scan_frequency_ranges]

        # ToDo: Get proper channel constraints
        # constraints = self.microwave_constraints
        self._raw_data = dict()
        self._fit_data = dict()
        self._signal_data = dict()
        estimated_samples = self._run_time * self._data_rate / self._oversampling_factor
        samples_per_line = sum(freq_range[-1] for freq_range in self._scan_frequency_ranges)
        # Add 5% Safety; Minimum of 1 line
        self.__estimated_lines = max(1, int(1.05 * estimated_samples / samples_per_line))
        for channel in self.channels:
            self._raw_data[channel] = [
                np.full((freq_arr.size, self.__estimated_lines), np.nan) for freq_arr in
                self._frequency_data
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

    @property
    def scanner_constraints(self):
        return self._odmr_scanner().constraints

    @property
    def microwave_constraints(self):
        return self._cw_microwave_source().constraints

    @property
    def active_channels(self):
        return self._odmr_scanner().active_channels

    @property
    def active_channel_units(self):
        scanner = self._odmr_scanner()
        return {ch: u for ch, u in scanner.channel_units.items() if ch in scanner.active_channels}

    @property
    def signal_data(self):
        return self._signal_data.copy()

    @property
    def raw_data(self):
        return self._raw_data.copy()

    @property
    def frequency_data(self):
        return self._frequency_data.copy()

    @property
    def average_length(self):
        return self._lines_to_average

    @average_length.setter
    def average_length(self, lines_to_average):
        self.set_average_length(lines_to_average)

    def set_average_length(self, lines_to_average):
        """ Sets the number of lines to average for the sum of the data

        @param int lines_to_average: desired number of lines to average (0 means all)
        """
        with self._threadlock:
            self._lines_to_average = int(lines_to_average)
            self._calculate_signal_data()
            self.sigScanDataUpdated.emit(self._signal_data, None)

    @property
    def runtime(self):
        return self._run_time

    @runtime.setter
    def runtime(self, new_runtime):
        self.set_runtime(new_runtime)

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

    @property
    def frequency_ranges(self):
        return self._scan_frequency_ranges.copy()

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
                except IndexError:
                    self.log.exception('Frequency range index is out of range.')
                except:
                    self.log.exception('Error while trying to set frequency range:')
            self.sigScanDataUpdated.emit(self._signal_data, self._raw_data)

    @property
    def data_rate(self):
        return self._data_rate

    @data_rate.setter
    def data_rate(self, rate):
        self.set_data_rate(rate)

    def set_data_rate(self, rate):
        """ Sets the frequency or rate of the sample acquisition.
        This is the physical sampling rate of the hardware, so the actually displayed data rate is
        this sampling rate divided by the oversampling factor.

        @param float rate: desired sample rate in Hz
        """
        with self._threadlock:
            # checks if scanner is still running
            if self.module_state() == 'locked':
                self.log.error('Unable to set data rate. ODMR measurement in progress.')
            else:
                rate = float(rate)
                if self.scanner_constraints.sample_rate_in_range(rate * self._oversampling_factor):
                    self._data_rate = rate
                else:
                    self.log.error('Unable to set data rate. Resulting sample rate out of bounds '
                                   'for ODMR scanner constraints.')
            self.sigScanParametersUpdated.emit({'sample_rate': self._data_rate})

    @property
    def oversampling(self):
        return self._oversampling_factor

    @oversampling.setter
    def oversampling(self, factor):
        self.set_oversampling(factor)

    def set_oversampling(self, factor):
        with self._threadlock:
            # checks if scanner is still running
            if self.module_state() == 'locked':
                self.log.error('Unable to set oversampling factor. ODMR scan in progress.')
            else:
                factor = max(1, int(factor))
                if self.scanner_constraints.sample_rate_in_range(self._data_rate * factor):
                    self._oversampling_factor = factor
                else:
                    self.log.error('Unable to set oversampling factor. Resulting sample rate out '
                                   'of bounds for ODMR scanner constraints.')
            self.sigScanParametersUpdated.emit({'oversampling': self._oversampling_factor})

    @property
    def cw_parameters(self):
        return self._cw_frequency, self._cw_power

    def set_cw_parameters(self, frequency, power):
        """ Set the desired new cw mode parameters.

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._threadlock:
            try:
                constraints = self.microwave_constraints
                self._cw_frequency = constraints.frequency_in_range(frequency)
                self._cw_power = constraints.power_in_range(power)
                # ToDo: Hardware calls
                # self._mw_device.set_cw(frequency_to_set, power_to_set)
                # self._cw_mw_frequency, self._cw_mw_power = self._mw_device.get_cw()
            except:
                self.log.exception('Error while trying to set CW parameters:')
            param_dict = {'cw_frequency': self._cw_frequency, 'cw_power': self._cw_power}
            self.sigScanParametersUpdated.emit(param_dict)

    def toggle_cw_output(self, enable):
        # ToDo: implement
        self.sigCwStateUpdated.emit(enable)

    def toggle_odmr_scan(self, start):
        """
        """
        if start:
            self.start_odmr_scan()
        else:
            self.stop_odmr_scan()

    def start_odmr_scan(self):
        """ Starting an ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start ODMR scan. Measurement is already running.')
                self.sigScanStateUpdated.emit(True)
                return -1

            self.module_state.lock()

            # Set up scanner hardware
            scanner = self._odmr_scanner()
            try:
                scanner.sample_rate = self._oversampling_factor * self._data_rate
                self._data_rate = scanner.sample_rate / self._oversampling_factor
                scanner.set_frequency_samples(self._frequency_data)
            except:
                self.log.exception(
                    'Unable to start ODMR scan. Error while setting up scanner hardware.'
                )
                self.module_state.unlock()
                self.sigScanStateUpdated.emit(False)
                return -1
            finally:
                # ToDo: Emit new parameters
                pass

            # ToDo: Clear old fit

            self._elapsed_sweeps = 0
            self._elapsed_time = 0.0
            self.sigElapsedUpdated.emit(self._elapsed_time, self._elapsed_sweeps)
            self._initialize_odmr_data()
            self.sigScanDataUpdated.emit(self._signal_data, self._raw_data)
            self.sigScanStateUpdated.emit(True)
            self.__start_time = time.time()
            self._sigNextLine.emit()
            return 0

    def continue_odmr_scan(self):
        """ Continue ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not continue ODMR scan. Measurement is already running.')
                self.sigScanStateUpdated.emit(True)
                return -1

            self.module_state.lock()

            # ToDo: see start_odmr_scan

            self.sigScanStateUpdated.emit(True)
            self.__start_time = time.time() - self._elapsed_time
            self._sigNextLine.emit()
            return 0

    def stop_odmr_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                self._odmr_scanner().stop_scan()
                self.module_state.unlock()
            self.sigScanStateUpdated.emit(False)
            return 0

    def clear_odmr_data(self):
        """ Clear the current ODMR data and reset elapsed time/sweeps """
        with self._threadlock:
            if self.module_state() == 'locked':
                self._elapsed_time = 0.0
                self._elapsed_sweeps = 0
                self._initialize_odmr_data()
                self.sigElapsedUpdated.emit(self._elapsed_time, self._elapsed_sweeps)
                self.sigScanDataUpdated.emit(self._signal_data, self._raw_data)
                self.__start_time = time.time()

    def _scan_odmr_line(self):
        """ Scans one line in ODMR

        (from mw_start to mw_stop in steps of mw_step)
        """
        with self._threadlock:
            # If the odmr measurement is not running do nothing
            if self.module_state() != 'locked':
                return

            try:
                new_counts = self._odmr_scanner().get_single_scan_data()
            except:
                self.log.exception('Error while trying to read ODMR scan data from hardware:')
                self.stop_odmr_scan()
                return

            # Add new count data to raw_data array and append if array is too small
            current_line_buffer_size = next(iter(self._raw_data.values()))[0].shape[1]
            if self._elapsed_sweeps == current_line_buffer_size:
                expand_arrays = tuple(np.full((r[-1], self.__estimated_lines), np.nan) for r in
                                      self._scan_frequency_ranges)
                self._raw_data = {
                    ch: [np.concatenate((r, expand_arrays[ii]), axis=0) for ii, r in
                         enumerate(range_list)] for ch, range_list in self._raw_data.items()
                }
                self.log.warning(
                    'raw data scan line buffer was not big enough for the entire measurement. '
                    'Buffer will be expanded.\nOld line buffer size was {0:d}, new line buffer '
                    'size is {1:d}.'.format(current_line_buffer_size,
                                            current_line_buffer_size + self.__estimated_lines)
                )

            # shift data in the array "up" and add new data at the "bottom"
            for ch, range_list in self._raw_data.items():
                start = 0
                for range_index, range_params in enumerate(self._scan_frequency_ranges):
                    range_list[range_index][:, 0] = new_counts[ch][start:start + range_params[-1]]
                    start += range_params[-1]

            # Calculate averaged signal
            self._calculate_signal_data()

            # Update elapsed time/sweeps
            self._elapsed_sweeps += 1
            self._elapsed_time = time.time() - self.__start_time

            # Fire update signals
            self.sigElapsedUpdated.emit(self._elapsed_time, self._elapsed_sweeps)
            self.sigScanDataUpdated.emit(self._signal_data, self._raw_data)
            if self._elapsed_time >= self._run_time:
                self.stop_odmr_scan()
            else:
                self._sigNextLine.emit()
            return

    @qudi_slot(str, str, int)
    def do_fit(self, fit_config, channel='', fit_range=-1, x_data=None, y_data=None):
        """
        Execute the currently configured fit on the measurement data. Optionally on passed data
        """
        if not fit_config:
            self.log.error(f'Unable to perform fit. Invalid fit_config encountered: "{fit_config}"')
            return
        if (x_data is None) or (y_data is None):
            if fit_range < 0 or not channel:
                self.log.error(f'Unable to perform fit. You must either provide x_data AND y_data '
                               f'or you must provide the data channel AND range index to fit.')
                return
            x_data = self._frequency_data[fit_range]
            y_data = self._signal_data[channel][fit_range]

        # ToDo: Perform fit

        # self.sigOdmrFitUpdated.emit(
        #     self.odmr_fit_x, self.odmr_fit_y, result_str_dict, self.fc.current_fit)

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

            data_raw = dict()
            data_raw['count data (counts/s)'] = self.odmr_raw_data[:self._elapsed_sweeps, nch, :]
            parameters = dict()
            parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
            parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
            parameters['Run Time (s)'] = self.run_time
            parameters['Number of frequency sweeps (#)'] = self._elapsed_sweeps
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

                # prepare the data in a dict:
                data = dict()
                data['frequency (Hz)'] = frequency_arr

                num_points = len(frequency_arr)
                data_end_ind = data_start_ind + num_points
                data['count data (counts/s)'] = self.odmr_plot_y[nch][data_start_ind:data_end_ind]
                data_start_ind += num_points

                parameters = dict()
                parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
                parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
                parameters['Run Time (s)'] = self.run_time
                parameters['Number of frequency sweeps (#)'] = self._elapsed_sweeps
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
