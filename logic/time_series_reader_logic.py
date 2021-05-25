# -*- coding: utf-8 -*-
"""
This file contains the qudi logic to continuously read data from a streaming device as time series.

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
import numpy as np
import datetime as dt
import time
import matplotlib.pyplot as plt

from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.util.units import ScaledFloat
from interface.data_instream_interface import StreamChannelType, StreamingMode


class TimeSeriesReaderLogic(GenericLogic):
    """
    This logic module gathers data from a hardware streaming device.

    Example config for copy-paste:

    time_series_reader_logic:
        module.Class: 'time_series_reader_logic.TimeSeriesReaderLogic'
        max_frame_rate: 10  # optional (10Hz by default)
        calc_digital_freq: True  # optional (True by default)
        connect:
            _streamer_con: <streamer_name>
            _savelogic_con: <save_logic_name>
    """
    # declare signals
    sigDataChanged = QtCore.Signal(object, object, object, object)
    sigStatusChanged = QtCore.Signal(bool, bool)
    sigSettingsChanged = QtCore.Signal(dict)
    _sigNextDataFrame = QtCore.Signal()  # internal signal

    # declare connectors
    _streamer_con = Connector(interface='DataInStreamInterface')
    _savelogic_con = Connector(interface='SaveLogic')

    # config options
    _max_frame_rate = ConfigOption('max_frame_rate', default=10, missing='warn')
    _calc_digital_freq = ConfigOption('calc_digital_freq', default=True, missing='warn')

    # status vars
    _trace_window_size = StatusVar('trace_window_size', default=6)
    _moving_average_width = StatusVar('moving_average_width', default=9)
    _oversampling_factor = StatusVar('oversampling_factor', default=1)
    _data_rate = StatusVar('data_rate', default=50)
    _active_channels = StatusVar('active_channels', default=None)
    _averaged_channels = StatusVar('averaged_channels', default=None)

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)

        self._streamer = None
        self._savelogic = None

        # locking for thread safety
        self.threadlock = Mutex()
        self._samples_per_frame = None
        self._stop_requested = True

        # Data arrays
        self._trace_data = None
        self._trace_times = None
        self._trace_data_averaged = None
        self.__moving_filter = None

        # for data recording
        self._recorded_data = None
        self._data_recording_active = False
        self._record_start_time = None
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Store references to connected modules
        self._streamer = self._streamer_con()
        self._savelogic = self._savelogic_con()

        # Flag to stop the loop and process variables
        self._stop_requested = True
        self._data_recording_active = False
        self._record_start_time = None

        # Check valid StatusVar
        # active channels
        avail_channels = tuple(ch.name for ch in self._streamer.available_channels)
        if self._active_channels is None:
            if self._streamer.active_channels:
                self._active_channels = tuple(ch.name for ch in self._streamer.active_channels)
            else:
                self._active_channels = avail_channels
        elif any(ch not in avail_channels for ch in self._active_channels):
            self.log.warning('Invalid active channels found in StatusVar. StatusVar ignored.')
            if self._streamer.active_channels:
                self._active_channels = tuple(ch.name for ch in self._streamer.active_channels)
            else:
                self._active_channels = avail_channels

        # averaged channels
        if self._averaged_channels is None:
            self._averaged_channels = self._active_channels
        else:
            self._averaged_channels = tuple(
                ch for ch in self._averaged_channels if ch in self._active_channels)

        # Check for odd moving averaging window
        if self._moving_average_width % 2 == 0:
            self.log.warning('Moving average width ConfigOption must be odd integer number. '
                             'Changing value from {0:d} to {1:d}.'
                             ''.format(self._moving_average_width, self._moving_average_width + 1))
            self._moving_average_width += 1

        # set settings in streamer hardware
        settings = self.all_settings
        settings['active_channels'] = self._active_channels
        settings['data_rate'] = self._data_rate
        self.configure_settings(**settings)

        # set up internal frame loop connection
        self._sigNextDataFrame.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
        """
        # Stop measurement
        if self.module_state() == 'locked':
            self._stop_reader_wait()

        self._sigNextDataFrame.disconnect()

        # Save status vars
        self._active_channels = self.active_channel_names
        self._data_rate = self.data_rate
        return

    def _init_data_arrays(self):
        window_size = self.trace_window_size_samples
        self._trace_data = np.zeros(
            [self.number_of_active_channels, window_size + self._moving_average_width // 2])
        self._trace_data_averaged = np.zeros(
            [len(self._averaged_channels), window_size - self._moving_average_width // 2])
        self._trace_times = np.arange(window_size) / self.data_rate
        self._recorded_data = list()
        return

    @property
    def trace_window_size_samples(self):
        return int(round(self._trace_window_size * self.data_rate))

    @property
    def streamer_constraints(self):
        """
        Retrieve the hardware constrains from the counter device.

        @return SlowCounterConstraints: object with constraints for the counter
        """
        return self._streamer.get_constraints()

    @property
    def data_rate(self):
        return self.sampling_rate / self.oversampling_factor

    @data_rate.setter
    def data_rate(self, val):
        self.configure_settings(data_rate=val)
        return

    @property
    def trace_window_size(self):
        return self._trace_window_size

    @trace_window_size.setter
    def trace_window_size(self, val):
        self.configure_settings(trace_window_size=val)
        return

    @property
    def moving_average_width(self):
        return self._moving_average_width

    @moving_average_width.setter
    def moving_average_width(self, val):
        self.configure_settings(moving_average_width=val)
        return

    @property
    def data_recording_active(self):
        return self._data_recording_active

    @property
    def oversampling_factor(self):
        """

        @return int: Oversampling factor (always >= 1). Value of 1 means no oversampling.
        """
        return self._oversampling_factor

    @oversampling_factor.setter
    def oversampling_factor(self, val):
        """

        @param int val: The oversampling factor to set. Must be >= 1.
        """
        self.configure_settings(oversampling_factor=val)
        return

    @property
    def sampling_rate(self):
        return self._streamer.sample_rate

    @property
    def available_channels(self):
        return self._streamer.available_channels

    @property
    def active_channels(self):
        return self._streamer.active_channels

    @property
    def active_channel_names(self):
        return tuple(ch.name for ch in self._streamer.active_channels)

    @property
    def active_channel_units(self):
        unit_dict = dict()
        for ch in self._streamer.active_channels:
            if self._calc_digital_freq and ch.type == StreamChannelType.DIGITAL:
                unit_dict[ch.name] = 'Hz'
            else:
                unit_dict[ch.name] = ch.unit
        return unit_dict

    @property
    def active_channel_types(self):
        return {ch.name: ch.type for ch in self._streamer.active_channels}

    @property
    def has_active_analog_channels(self):
        return any(ch.type == StreamChannelType.ANALOG for ch in self._streamer.active_channels)

    @property
    def has_active_digital_channels(self):
        return any(ch.type == StreamChannelType.DIGITAL for ch in self._streamer.active_channels)

    @property
    def averaged_channel_names(self):
        return self._averaged_channels

    @property
    def number_of_active_channels(self):
        return self._streamer.number_of_channels

    @property
    def trace_data(self):
        data_offset = self._trace_data.shape[1] - self._moving_average_width // 2
        data = {ch: self._trace_data[i, :data_offset] for i, ch in
                enumerate(self.active_channel_names)}
        return self._trace_times, data

    @property
    def averaged_trace_data(self):
        if not self.averaged_channel_names or self.moving_average_width <= 1:
            return None, None
        data = {ch: self._trace_data_averaged[i] for i, ch in
                enumerate(self.averaged_channel_names)}
        return self._trace_times[-self._trace_data_averaged.shape[1]:], data

    @property
    def all_settings(self):
        return {'oversampling_factor': self.oversampling_factor,
                'active_channels': self.active_channels,
                'averaged_channels': self.averaged_channel_names,
                'moving_average_width': self.moving_average_width,
                'trace_window_size': self.trace_window_size,
                'data_rate': self.data_rate}

    @QtCore.Slot(dict)
    def configure_settings(self, settings_dict=None, **kwargs):
        """
        Sets the number of samples to average per data point, i.e. the oversampling factor.
        The counter is stopped first and restarted afterwards.

        @param dict settings_dict: optional, dict containing all parameters to set. Entries will
                                   be overwritten by conflicting kwargs.

        @return dict: The currently configured settings
        """
        if self.data_recording_active:
            self.log.warning('Unable to configure settings while data is being recorded.')
            return self.all_settings

        if settings_dict is None:
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)

        if not settings_dict:
            return self.all_settings

        # Flag indicating if the stream should be restarted
        restart = self.module_state() == 'locked'
        if restart:
            self._stop_reader_wait()

        with self.threadlock:
            constraints = self.streamer_constraints
            all_ch = tuple(ch.name for ch in self._streamer.available_channels)
            data_rate = self.data_rate
            active_ch = self.active_channel_names

            if 'oversampling_factor' in settings_dict:
                new_val = int(settings_dict['oversampling_factor'])
                if new_val < 1:
                    self.log.error('Oversampling factor must be integer value >= 1 '
                                   '(received: {0:d}).'.format(new_val))
                else:
                    if self.has_active_analog_channels and self.has_active_digital_channels:
                        min_val = constraints.combined_sample_rate.min
                        max_val = constraints.combined_sample_rate.max
                    elif self.has_active_analog_channels:
                        min_val = constraints.analog_sample_rate.min
                        max_val = constraints.analog_sample_rate.max
                    else:
                        min_val = constraints.digital_sample_rate.min
                        max_val = constraints.digital_sample_rate.max
                    if not (min_val <= (new_val * data_rate) <= max_val):
                        if 'data_rate' in settings_dict:
                            self._oversampling_factor = new_val
                        else:
                            self.log.error('Oversampling factor to set ({0:d}) would cause '
                                           'sampling rate outside allowed value range. '
                                           'Setting not changed.'.format(new_val))
                    else:
                        self._oversampling_factor = new_val

            if 'moving_average_width' in settings_dict:
                new_val = int(settings_dict['moving_average_width'])
                if new_val < 1:
                    self.log.error('Moving average width must be integer value >= 1 '
                                   '(received: {0:d}).'.format(new_val))
                elif new_val % 2 == 0:
                    new_val += 1
                    self.log.warning('Moving average window must be odd integer number in order to '
                                     'ensure perfect data alignment. Will increase value to {0:d}.'
                                     ''.format(new_val))
                if new_val / data_rate > self.trace_window_size:
                    if 'data_rate' in settings_dict or 'trace_window_size' in settings_dict:
                        self._moving_average_width = new_val
                        self.__moving_filter = np.full(shape=self.moving_average_width,
                                                       fill_value=1.0 / self.moving_average_width)
                    else:
                        self.log.warning('Moving average width to set ({0:d}) is smaller than the '
                                         'trace window size. Will adjust trace window size to '
                                         'match.'.format(new_val))
                        self._trace_window_size = float(new_val / data_rate)
                else:
                    self._moving_average_width = new_val
                    self.__moving_filter = np.full(shape=self.moving_average_width,
                                                   fill_value=1.0 / self.moving_average_width)

            if 'data_rate' in settings_dict:
                new_val = float(settings_dict['data_rate'])
                if new_val < 0:
                    self.log.error('Data rate must be float value > 0.')
                else:
                    if self.has_active_analog_channels and self.has_active_digital_channels:
                        min_val = constraints.combined_sample_rate.min
                        max_val = constraints.combined_sample_rate.max
                    elif self.has_active_analog_channels:
                        min_val = constraints.analog_sample_rate.min
                        max_val = constraints.analog_sample_rate.max
                    else:
                        min_val = constraints.digital_sample_rate.min
                        max_val = constraints.digital_sample_rate.max
                    sample_rate = new_val * self.oversampling_factor
                    if not (min_val <= sample_rate <= max_val):
                        self.log.warning('Data rate to set ({0:.3e}Hz) would cause sampling rate '
                                         'outside allowed value range. Will clip data rate to '
                                         'boundaries.'.format(new_val))
                        if sample_rate > max_val:
                            new_val = max_val / self.oversampling_factor
                        elif sample_rate < min_val:
                            new_val = min_val / self.oversampling_factor

                    data_rate = new_val
                    if self.moving_average_width / data_rate > self.trace_window_size:
                        if 'trace_window_size' not in settings_dict:
                            self.log.warning('Data rate to set ({0:.3e}Hz) would cause too few '
                                             'data points within the trace window. Adjusting window'
                                             ' size.'.format(new_val))
                            self._trace_window_size = self.moving_average_width / data_rate

            if 'trace_window_size' in settings_dict:
                new_val = float(settings_dict['trace_window_size'])
                if new_val < 0:
                    self.log.error('Trace window size must be float value > 0.')
                else:
                    # Round window to match data rate
                    data_points = int(round(new_val * data_rate))
                    new_val = data_points / data_rate
                    # Check if enough points are present
                    if data_points < self.moving_average_width:
                        self.log.warning('Requested trace_window_size ({0:.3e}s) would have too '
                                         'few points for moving average. Adjusting window size.'
                                         ''.format(new_val))
                        new_val = self.moving_average_width / data_rate
                    self._trace_window_size = new_val

            if 'active_channels' in settings_dict:
                new_val = tuple(settings_dict['active_channels'])
                if any(ch not in all_ch for ch in new_val):
                    self.log.error('Invalid channel found to set active.')
                else:
                    active_ch = new_val

            if 'averaged_channels' in settings_dict:
                new_val = tuple(ch for ch in settings_dict['averaged_channels'] if ch in active_ch)
                if any(ch not in all_ch for ch in new_val):
                    self.log.error('Invalid channel found to set activate moving average for.')
                else:
                    self._averaged_channels = new_val

            # Apply settings to hardware if needed
            self._streamer.configure(sample_rate=data_rate * self.oversampling_factor,
                                     streaming_mode=StreamingMode.CONTINUOUS,
                                     active_channels=active_ch,
                                     buffer_size=10000000,
                                     use_circular_buffer=True)

            # update actually set values
            self._averaged_channels = tuple(
                ch for ch in self._averaged_channels if ch in self.active_channel_names)

            self._samples_per_frame = int(round(self.data_rate / self._max_frame_rate))
            self._init_data_arrays()
            settings = self.all_settings
            self.sigSettingsChanged.emit(settings)
            if not restart:
                self.sigDataChanged.emit(*self.trace_data, *self.averaged_trace_data)
        if restart:
            self.start_reading()
        return settings

    @QtCore.Slot()
    def start_reading(self):
        """
        Start data acquisition loop.

        @return error: 0 is OK, -1 is error
        """
        with self.threadlock:
            # Lock module
            if self.module_state() == 'locked':
                self.log.warning('Data acquisition already running. "start_reading" call ignored.')
                self.sigStatusChanged.emit(True, self._data_recording_active)
                return 0

            self.module_state.lock()
            self._stop_requested = False

            self.sigStatusChanged.emit(True, self._data_recording_active)

            # # Configure streaming device
            # curr_settings = self._streamer.configure(sample_rate=self.sampling_rate,
            #                                          streaming_mode=StreamingMode.CONTINUOUS,
            #                                          active_channels=self._active_channels,
            #                                          buffer_size=10000000,
            #                                          use_circular_buffer=True)
            # # update actually set values
            # self._active_channels = tuple(ch.name for ch in curr_settings['active_channels'])
            # self._averaged_channels = tuple(
            #     ch for ch in self._averaged_channels if ch in self._active_channels)
            # self._data_rate = curr_settings['sample_rate'] / self._oversampling_factor
            #
            # self._samples_per_frame = int(round(self._data_rate / self._max_frame_rate))
            # self._init_data_arrays()
            # settings = self.all_settings
            # self.sigSettingsChanged.emit(settings)

            if self._data_recording_active:
                self._record_start_time = dt.datetime.now()
                self._recorded_data = list()

            if self._streamer.start_stream() < 0:
                self.log.error('Error while starting streaming device data acquisition.')
                self._stop_requested = True
                self._sigNextDataFrame.emit()
                return -1

            self._sigNextDataFrame.emit()
        return 0

    @QtCore.Slot()
    def stop_reading(self):
        """
        Send a request to stop counting.

        @return int: error code (0: OK, -1: error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self._stop_requested = True
        return 0

    @QtCore.Slot()
    def acquire_data_block(self):
        """
        This method gets the available data from the hardware.

        It runs repeatedly by being connected to a QTimer timeout signal.
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                # check for break condition
                if self._stop_requested:
                    # terminate the hardware streaming
                    if self._streamer.stop_stream() < 0:
                        self.log.error(
                            'Error while trying to stop streaming device data acquisition.')
                    if self._data_recording_active:
                        self._save_recorded_data(to_file=True, save_figure=True)
                        self._recorded_data = list()
                    self._data_recording_active = False
                    self.module_state.unlock()
                    self.sigStatusChanged.emit(False, False)
                    return

                samples_to_read = max(
                    (self._streamer.available_samples // self._oversampling_factor) * self._oversampling_factor,
                    self._samples_per_frame * self._oversampling_factor)
                if samples_to_read < 1:
                    self._sigNextDataFrame.emit()
                    return

                # read the current counter values
                data = self._streamer.read_data(number_of_samples=samples_to_read)
                if data.shape[1] != samples_to_read:
                    self.log.error('Reading data from streamer went wrong; '
                                   'killing the stream with next data frame.')
                    self._stop_requested = True
                    self._sigNextDataFrame.emit()
                    return

                # Process data
                self._process_trace_data(data)

                # Emit update signal
                self.sigDataChanged.emit(*self.trace_data, *self.averaged_trace_data)
                self._sigNextDataFrame.emit()
        return

    def _process_trace_data(self, data):
        """
        Processes raw data from the streaming device
        """
        # Down-sample and average according to oversampling factor
        if self.oversampling_factor > 1:
            if data.shape[1] % self.oversampling_factor != 0:
                self.log.error('Number of samples per channel not an integer multiple of the '
                               'oversampling factor.')
                return -1
            tmp = data.reshape((data.shape[0],
                                data.shape[1] // self.oversampling_factor,
                                self.oversampling_factor))
            data = np.mean(tmp, axis=2)

        digital_channels = [c for c, typ in self.active_channel_types.items() if
                            typ == StreamChannelType.DIGITAL]
        # Convert digital event count numbers into frequencies according to ConfigOption
        if self._calc_digital_freq and digital_channels:
            data[:len(digital_channels)] *= self.sampling_rate

        # Append data to save if necessary
        if self._data_recording_active:
            self._recorded_data.append(data.copy())

        data = data[:, -self._trace_data.shape[1]:]
        new_samples = data.shape[1]

        # Roll data array to have a continuously running time trace
        self._trace_data = np.roll(self._trace_data, -new_samples, axis=1)
        # Insert new data
        self._trace_data[:, -new_samples:] = data

        # Calculate moving average by using numpy.convolve with a normalized uniform filter
        if self.moving_average_width > 1 and self.averaged_channel_names:
            # Only convolve the new data and roll the previously calculated moving average
            self._trace_data_averaged = np.roll(self._trace_data_averaged, -new_samples, axis=1)
            offset = new_samples + len(self.__moving_filter) - 1
            for i, ch in enumerate(self.averaged_channel_names):
                data_index = self.active_channel_names.index(ch)
                self._trace_data_averaged[i, -new_samples:] = np.convolve(
                    self._trace_data[data_index, -offset:], self.__moving_filter, mode='valid')
        return

    @QtCore.Slot()
    def start_recording(self):
        """
        Sets up start-time and initializes data array, if not resuming, and changes saving state.
        If the counter is not running it will be started in order to have data to save.

        @return int: Error code (0: OK, -1: Error)
        """
        with self.threadlock:
            if self._data_recording_active:
                self.sigStatusChanged.emit(self.module_state() == 'locked', True)
                return -1

            self._data_recording_active = True
            if self.module_state() == 'locked':
                self._recorded_data = list()
                self._record_start_time = dt.datetime.now()
                self.sigStatusChanged.emit(True, True)
            else:
                self.start_reading()
        return 0

    @QtCore.Slot()
    def stop_recording(self):
        """
        Stop the accumulative data recording and save data to file. Will not stop the data stream.
        Ignored if stream reading is inactive (module is in idle state).

        @return int: Error code (0: OK, -1: Error)
        """
        with self.threadlock:
            if not self._data_recording_active:
                self.sigStatusChanged.emit(self.module_state() == 'locked', False)
                return 0

            self._data_recording_active = False
            if self.module_state() == 'locked':
                self._save_recorded_data(to_file=True, save_figure=True)
                self._recorded_data = list()
                self.sigStatusChanged.emit(True, False)
        return 0

    def _save_recorded_data(self, to_file=True, name_tag='', save_figure=True):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str name_tag: an additional tag, which will be added to the filename upon save
        @param bool save_figure: select whether png and pdf should be saved

        @return dict parameters: Dictionary which contains the saving parameters
        """
        if not self._recorded_data:
            self.log.error('No data has been recorded. Save to file failed.')
            return np.empty(0), dict()

        data_arr = np.concatenate(self._recorded_data, axis=1)
        if data_arr.size == 0:
            self.log.error('No data has been recorded. Save to file failed.')
            return np.empty(0), dict()

        saving_stop_time = self._record_start_time + dt.timedelta(
            seconds=data_arr.shape[1] / self.data_rate)

        # write the parameters:
        parameters = dict()
        parameters['Start recoding time'] = self._record_start_time.strftime(
            '%d.%m.%Y, %H:%M:%S.%f')
        parameters['Stop recoding time'] = saving_stop_time.strftime('%d.%m.%Y, %H:%M:%S.%f')
        parameters['Data rate (Hz)'] = self.data_rate
        parameters['Oversampling factor (samples)'] = self.oversampling_factor
        parameters['Sampling rate (Hz)'] = self.sampling_rate

        if to_file:
            # If there is a postfix then add separating underscore
            filelabel = 'data_trace_{0}'.format(name_tag) if name_tag else 'data_trace'

            # prepare the data in a dict:
            header = ', '.join(
                '{0} ({1})'.format(ch, unit) for ch, unit in self.active_channel_units.items())

            data = {header: data_arr.transpose()}
            filepath = self._savelogic.get_path_for_module(module_name='TimeSeriesReader')
            set_of_units = set(self.active_channel_units.values())
            unit_list = tuple(self.active_channel_units)
            y_unit = 'arb.u.'
            occurrences = 0
            for unit in set_of_units:
                count = unit_list.count(unit)
                if count > occurrences:
                    occurrences = count
                    y_unit = unit

            fig = self._draw_figure(data_arr, self.data_rate, y_unit) if save_figure else None

            self._savelogic.save_data(data=data,
                                      filepath=filepath,
                                      parameters=parameters,
                                      filelabel=filelabel,
                                      plotfig=fig,
                                      delimiter='\t',
                                      timestamp=saving_stop_time)
            self.log.info('Time series saved to: {0}'.format(filepath))
        return data_arr, parameters

    def _draw_figure(self, data, timebase, y_unit):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        # Use qudi style
        plt.style.use(self._savelogic.mpl_qd_style)

        # Create figure and scale data
        max_abs_value = ScaledFloat(max(data.max(), np.abs(data.min())))
        time_data = np.arange(data.shape[1]) / timebase
        fig, ax = plt.subplots()
        if max_abs_value.scale:
            ax.plot(time_data,
                    data.transpose() / max_abs_value.scale_val,
                    linestyle=':',
                    linewidth=0.5)
        else:
            ax.plot(time_data, data.transpose(), linestyle=':', linewidth=0.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Signal ({0}{1})'.format(max_abs_value.scale, y_unit))
        return fig

    @QtCore.Slot()
    def save_trace_snapshot(self, to_file=True, name_tag='', save_figure=True):
        """
        The currently displayed data trace will be saved.

        @param bool to_file: optional, whether data should be saved to a text file
        @param str name_tag: optional, additional description that will be appended to the file name
        @param bool save_figure: optional, whether a data thumbnail figure should be saved

        @return dict, dict: Data which was saved, Experiment parameters

        This method saves the already displayed counts to file and does not accumulate them.
        """
        with self.threadlock:
            timestamp = dt.datetime.now()

            # write the parameters:
            parameters = dict()
            parameters['Time stamp'] = timestamp.strftime('%d.%m.%Y, %H:%M:%S.%f')
            parameters['Data rate (Hz)'] = self.data_rate
            parameters['Oversampling factor (samples)'] = self.oversampling_factor
            parameters['Sampling rate (Hz)'] = self.sampling_rate

            header = ', '.join(
                '{0} ({1})'.format(ch, unit) for ch, unit in self.active_channel_units.items())
            data_offset = self._trace_data.shape[1] - self.moving_average_width // 2
            data = {header: self._trace_data[:, :data_offset].transpose()}

            if to_file:
                filepath = self._savelogic.get_path_for_module(module_name='TimeSeriesReader')
                filelabel = 'data_trace_snapshot_{0}'.format(
                    name_tag) if name_tag else 'data_trace_snapshot'
                self._savelogic.save_data(data=data,
                                          filepath=filepath,
                                          parameters=parameters,
                                          filelabel=filelabel,
                                          timestamp=timestamp,
                                          delimiter='\t')
                self.log.info('Time series snapshot saved to: {0}'.format(filepath))
        return data, parameters

    def _stop_reader_wait(self):
        """
        Stops the counter and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        with self.threadlock:
            self._stop_requested = True
            # terminate the hardware streaming
            if self._streamer.stop_stream() < 0:
                self.log.error(
                    'Error while trying to stop streaming device data acquisition.')
            if self._data_recording_active:
                self._save_recorded_data(to_file=True, save_figure=True)
                self._recorded_data = list()
            self._data_recording_active = False
            self.module_state.unlock()
            self.sigStatusChanged.emit(False, False)
        return 0
