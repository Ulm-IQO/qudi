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
    """
    # declare signals
    sigDataChanged = QtCore.Signal(np.ndarray, np.ndarray, object, object)
    sigStatusChanged = QtCore.Signal(bool, bool)
    sigSettingsChanged = QtCore.Signal(dict)
    _sigNextDataFrame = QtCore.Signal()  # internal signal

    # declare connectors
    _streamer_con = Connector(interface='DataInStreamInterface')
    _savelogic_con = Connector(interface='SaveLogic')

    # config options
    _max_frame_rate = ConfigOption('max_frame_rate', default=10, missing='warn')

    # status vars
    _trace_window_size = StatusVar('trace_window_size', default=6)
    _moving_average_width = StatusVar('moving_average_width', default=9)
    _oversampling_factor = StatusVar('oversampling_factor', default=1)
    _data_rate = StatusVar('data_rate', default=50)

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
        self.trace_time_axis = None
        self.trace_data_averaged = None

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

        # initialize data arrays
        self._init_data_arrays()

        # Flag to stop the loop and process variables
        self._stop_requested = True
        self._data_recording_active = False
        self._record_start_time = None
        self._samples_per_frame = int(round(self._data_rate / self._max_frame_rate))

        # Check for odd moving averaging window
        if self._moving_average_width % 2 == 0:
            self.log.warning('Moving average width ConfigOption must be odd integer number. '
                             'Changing value from {0:d} to {1:d}.'
                             ''.format(self._moving_average_width, self._moving_average_width + 1))
            self._moving_average_width += 1

        # set up timer
        self._sigNextDataFrame.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
        """
        # Stop measurement
        if self.module_state() == 'locked':
            self._stop_reader_wait()

        self._sigNextDataFrame.disconnect()
        return

    def _init_data_arrays(self):
        channel_number = self._streamer.number_of_channels
        window_size = self.trace_window_size_samples
        self._trace_data = np.zeros(
            [channel_number, window_size + self._moving_average_width // 2])
        self.trace_data_averaged = np.zeros(
            [channel_number, window_size - self._moving_average_width // 2])
        self.trace_time_axis = np.arange(self.trace_data.shape[1]) / self._data_rate
        self._recorded_data = list()
        return

    @property
    def trace_window_size_samples(self):
        return int(round(self._trace_window_size * self._data_rate))

    @property
    def streamer_constraints(self):
        """
        Retrieve the hardware constrains from the counter device.

        @return SlowCounterConstraints: object with constraints for the counter
        """
        return self._streamer.get_constraints()

    @property
    def data_rate(self):
        return self._data_rate

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
        return self._oversampling_factor * self._data_rate

    @property
    def channel_names(self):
        return self._streamer.channel_names

    @property
    def number_of_channels(self):
        return self._streamer.number_of_channels

    @property
    def channel_units(self):
        return {ch: prop['unit'] for ch, prop in self._streamer.channel_properties.items()}

    @property
    def channel_types(self):
        return {ch: prop['type'] for ch, prop in self._streamer.channel_properties.items()}

    @property
    def has_analog_channels(self):
        return any(StreamChannelType.ANALOG == ch_type for ch_type in self.channel_types.values())

    @property
    def has_digital_channels(self):
        return any(StreamChannelType.DIGITAL == ch_type for ch_type in self.channel_types.values())

    @property
    def trace_data(self):
        if self._moving_average_width == 1:
            return self._trace_data
        return self._trace_data[:, :-(self._moving_average_width // 2)]

    @property
    def averaged_trace_time_axis(self):
        return self.trace_time_axis[-self.trace_data_averaged.shape[1]:]

    @property
    def all_settings(self):
        return {'oversampling_factor': self._oversampling_factor,
                'moving_average_width': self._moving_average_width,
                'trace_window_size': self._trace_window_size,
                'data_rate': self._data_rate}

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

        # Return early if no values are about to change
        if all(val == getattr(self, key, None) for key, val in settings_dict.items()):
            return

        restart = self.module_state() == 'locked'
        if restart:
            self._stop_reader_wait()
        # Flag indicating if the stream should be restarted
        with self.threadlock:
            if 'oversampling_factor' in settings_dict:
                new_val = int(settings_dict['oversampling_factor'])
                if new_val < 1:
                    self.log.error('Oversampling factor must be integer value >= 1 '
                                   '(received: {0:d}).'.format(new_val))
                else:
                    if self.has_analog_channels and self.has_digital_channels:
                        min_val = self.streamer_constraints.combined_sample_rate.min
                        max_val = self.streamer_constraints.combined_sample_rate.max
                    elif self.has_analog_channels:
                        min_val = self.streamer_constraints.analog_sample_rate.min
                        max_val = self.streamer_constraints.analog_sample_rate.max
                    else:
                        min_val = self.streamer_constraints.digital_sample_rate.min
                        max_val = self.streamer_constraints.digital_sample_rate.max
                    if not (min_val <= (new_val * self._data_rate) <= max_val):
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
                elif new_val / self._data_rate > self._trace_window_size:
                    if 'data_rate' in settings_dict or 'trace_window_size' in settings_dict:
                        self._moving_average_width = new_val
                    else:
                        self.log.warning('Moving average width to set ({0:d}) is smaller than the '
                                         'trace window size. Will adjust trace window size to '
                                         'match.'.format(new_val))
                        self._trace_window_size = float(new_val / self._data_rate)
                else:
                    self._moving_average_width = new_val

            if 'data_rate' in settings_dict:
                new_val = float(settings_dict['data_rate'])
                if new_val < 0:
                    self.log.error('Data rate must be float value > 0.')
                else:
                    if self.has_analog_channels and self.has_digital_channels:
                        min_val = self.streamer_constraints.combined_sample_rate.min
                        max_val = self.streamer_constraints.combined_sample_rate.max
                    elif self.has_analog_channels:
                        min_val = self.streamer_constraints.analog_sample_rate.min
                        max_val = self.streamer_constraints.analog_sample_rate.max
                    else:
                        min_val = self.streamer_constraints.digital_sample_rate.min
                        max_val = self.streamer_constraints.digital_sample_rate.max
                    sample_rate = new_val * self._oversampling_factor
                    if not (min_val <= sample_rate <= max_val):
                        self.log.warning('Data rate to set ({0:.3e}Hz) would cause sampling rate '
                                         'outside allowed value range. Will clip data rate to '
                                         'boundaries.'.format(new_val))
                        if sample_rate > max_val:
                            new_val = max_val / self._oversampling_factor
                        elif sample_rate < min_val:
                            new_val = min_val / self._oversampling_factor

                    data_period = 1 / new_val
                    self._data_rate = new_val
                    if data_period * self._moving_average_width > self._trace_window_size:
                        if 'trace_window_size' not in settings_dict:
                            self.log.warning('Data rate to set ({0:.3e}Hz) would cause too few '
                                             'data points within the trace window. Adjusting window'
                                             ' size.'.format(new_val))
                            self._trace_window_size = data_period * self._moving_average_width

            if 'trace_window_size' in settings_dict:
                new_val = float(settings_dict['trace_window_size'])
                if new_val < 0:
                    self.log.error('Trace window size must be float value > 0.')
                else:
                    # Round window to match data rate
                    data_points = int(round(new_val * self._data_rate))
                    new_val = data_points / self._data_rate
                    # Check if enough points are present
                    if data_points < self._moving_average_width:
                        self.log.warning('Requested trace_window_size ({0:.3e}s) would have too '
                                         'few points for moving average. Adjusting window size.'
                                         ''.format(new_val))
                        new_val = self._moving_average_width / self._data_rate
                        data_points = self._moving_average_width
                    self._trace_window_size = new_val

            self._samples_per_frame = int(round(self._data_rate / self._max_frame_rate))
            self._init_data_arrays()
            settings = self.all_settings
            self.sigSettingsChanged.emit(settings)
            if not restart:
                if self._moving_average_width > 1:
                    self.sigDataChanged.emit(self.trace_time_axis,
                                             self.trace_data,
                                             self.averaged_trace_time_axis,
                                             self.trace_data_averaged)
                else:
                    self.sigDataChanged.emit(self.trace_time_axis,
                                             self.trace_data,
                                             None,
                                             None)
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
            self._init_data_arrays()
            self._stop_requested = False

            self.sigStatusChanged.emit(True, self._data_recording_active)

            # Configure streaming device
            dtype = self.streamer_constraints.data_types[0]
            curr_settings = self._streamer.configure(sample_rate=self.sampling_rate,
                                                     data_type=dtype,
                                                     streaming_mode=StreamingMode.CONTINUOUS,
                                                     buffer_size=10000000,
                                                     use_circular_buffer=True)
            if self._data_recording_active:
                self._record_start_time = dt.datetime.now()
                self._recorded_data = list()

            if self._streamer.start_stream() < 0:
                self.log.error('Error while starting streaming device data acquisition.')
                self._stop_requested = True
                self.sigStatusChanged.emit(False, False)
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

                samples_to_read = max(self._streamer.available_samples, self._samples_per_frame)
                samples_to_read -= samples_to_read % self._oversampling_factor
                if samples_to_read < 1:
                    self._sigNextDataFrame.emit()
                    return

                # read the current counter values
                data = self._streamer.read_data(number_of_samples=samples_to_read)
                if data.shape[1] != samples_to_read:
                    self.log.error('Reading data from streamer went wrong; '
                                   'killing the stream with next data frame.')
                    self._stop_requested = True
                    return

                # Process data
                self._process_trace_data(data)

                # Emit update signal
                if self._moving_average_width > 1:
                    self.sigDataChanged.emit(self.trace_time_axis,
                                             self.trace_data,
                                             self.averaged_trace_time_axis,
                                             self.trace_data_averaged)
                else:
                    self.sigDataChanged.emit(self.trace_time_axis,
                                             self.trace_data,
                                             None,
                                             None)
                self._sigNextDataFrame.emit()
        return

    def _process_trace_data(self, data):
        """
        Processes raw data from the streaming device
        """
        # Down-sample and average according to oversampling factor
        if self._oversampling_factor > 1:
            if data.shape[1] % self._oversampling_factor != 0:
                self.log.error('Number of samples per channel not an integer multiple of the '
                               'oversampling factor.')
                return -1
            tmp = data.reshape((data.shape[0],
                                data.shape[1] // self._oversampling_factor,
                                self._oversampling_factor))
            data = np.mean(tmp, axis=2)

        digital_channels = [c for c, p in self._streamer.channel_properties.items() if
                            p['type'] == StreamChannelType.DIGITAL]
        if digital_channels:
            data[:len(digital_channels)] *= self.sampling_rate

        # save the data if necessary
        if self._data_recording_active:
            self._recorded_data.append(data)

        data = data[:, -self._trace_data.shape[1]:]
        new_samples = data.shape[1]

        # Roll data array to have a continuously running time trace
        self._trace_data = np.roll(self._trace_data, -new_samples, axis=1)
        # Insert new data
        self._trace_data[:, -new_samples:] = data

        # Calculate moving average
        if self._moving_average_width > 1:
            cumsum = np.cumsum(self._trace_data, axis=1)
            n = self._moving_average_width
            self.trace_data_averaged = (cumsum[:, n:] - cumsum[:, :-n]) / n
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
            seconds=data_arr.shape[1] * self._data_rate)

        # write the parameters:
        parameters = dict()
        parameters['Start recoding time'] = self._record_start_time.strftime(
            '%d.%m.%Y, %H:%M:%S.%f')
        parameters['Stop recoding time'] = saving_stop_time.strftime('%d.%m.%Y, %H:%M:%S.%f')
        parameters['Data rate (Hz)'] = self._data_rate
        parameters['Oversampling factor (samples)'] = self._oversampling_factor
        parameters['Sampling rate (Hz)'] = self.sampling_rate

        if to_file:
            # If there is a postfix then add separating underscore
            filelabel = 'data_trace_{0}'.format(name_tag) if name_tag else 'data_trace'

            # prepare the data in a dict:
            header = ', '.join('{0} ({1})'.format(ch, prop['unit']) for ch, prop in
                               self._streamer.channel_properties.items())

            data = {header: data_arr}
            filepath = self._savelogic.get_path_for_module(module_name='TimeSeriesReader')

            fig = self.draw_figure(data_arr, self._data_rate) if save_figure else None

            self._savelogic.save_data(data=data,
                                      filepath=filepath,
                                      parameters=parameters,
                                      filelabel=filelabel,
                                      plotfig=fig,
                                      delimiter='\t',
                                      timestamp=saving_stop_time)
            self.log.info('Time series saved to: {0}'.format(filepath))
        return data_arr, parameters

    def _draw_figure(self, data, timebase):
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
        ax.set_ylabel('Signal ({0}arb.u.)'.format(max_abs_value.scale))
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
            parameters['Data rate (Hz)'] = self._data_rate
            parameters['Oversampling factor (samples)'] = self._oversampling_factor
            parameters['Sampling rate (Hz)'] = self.sampling_rate

            header = ', '.join('{0} ({1})'.format(ch, prop['unit']) for ch, prop in
                               self._streamer.channel_properties.items())
            data = {header: self.trace_data}

            if to_file:
                # time_arr = np.arange(self._trace_window_size) / self._data_rate
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
