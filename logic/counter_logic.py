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
import time
import matplotlib.pyplot as plt

from core.module import Connector, StatusVar, ConfigOption
from logic.generic_logic import GenericLogic
from interface.slow_counter_interface import CountingMode
from core.util.mutex import Mutex


class CounterLogic(GenericLogic):
    """ This logic module gathers data from a hardware counting device.

    @signal sigCounterUpdate: there is new counting data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???

    @return error: 0 is OK, -1 is error
    """
    sigCountDataChanged = QtCore.Signal()

    sigCountDataNext = QtCore.Signal()

    sigGatedCounterFinished = QtCore.Signal()
    sigGatedCounterContinue = QtCore.Signal(bool)
    sigCounterSettingsChanged = QtCore.Signal(dict)
    sigSavingStatusChanged = QtCore.Signal(bool)
    sigCounterStatusChanged = QtCore.Signal(bool)
    sigCountingModeChanged = QtCore.Signal(CountingMode)

    # declare connectors
    counter = Connector(interface='SlowCounterInterface')
    savelogic = Connector(interface='SaveLogic')

    # config options
    _data_update_rate = ConfigOption('data_update_rate', default=0.1, missing='warn')

    # status vars
    _count_length = StatusVar('count_length', default=300)
    _smooth_window_length = StatusVar('smooth_window_length', default=9)
    _oversampling = StatusVar('oversampling', default=1)
    _count_frequency = StatusVar('count_frequency', default=50)
    _cumulative_acquisition = StatusVar('cumulative_acquisition', False)

    def __init__(self, *args, **kwargs):
        """ Create CounterLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(*args, **kwargs)

        self._counter = None
        self._save_logic = None

        # locking for thread safety
        self.threadlock = Mutex()

        self._counting_mode = CountingMode.CONTINUOUS

        # Data arrays
        self._count_data = None
        self.count_data_smoothed = None
        self._data_to_save = None
        self._saving_start_time = None

        self.stop_requested = True
        self.__last_data_update = None
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Connect to hardware and save logic
        self._counter = self.counter()
        self._save_logic = self.savelogic()

        # Recall saved app-parameters
        if 'counting_mode' in self._statusVariables:
            self._counting_mode = CountingMode(self._statusVariables['counting_mode'])

        # initialize data arrays
        self._count_data = np.zeros(
            [self.counter_channel_number, self._count_length + self._smooth_window_length // 2])
        self.count_data_smoothed = np.zeros(
            [self.counter_channel_number, self._count_length - self._smooth_window_length // 2])
        self._data_to_save = list()

        # Flag to stop the loop
        self.stop_requested = True
        self.__last_data_update = None

        self._saving_start_time = None

        # Check for odd smoothing window
        if self._smooth_window_length % 2 == 0:
            self.log.warning('Smoothing window ConfigOption must be odd integer number. CHanging '
                             'value from {0:d} to {1:d}.'.format(self._smooth_window_length,
                                                                 self._smooth_window_length + 1))
            self._smooth_window_length += 1

        # connect signals
        self.sigCountDataNext.connect(self.count_loop_body, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
        """
        # Save parameters to disk
        self._statusVariables['counting_mode'] = self._counting_mode.value

        # Stop measurement
        if self.module_state() == 'locked':
            self._stop_counting_wait()

        self.sigCountDataNext.disconnect()
        return

    def get_hardware_constraints(self):
        """
        Retrieve the hardware constrains from the counter device.

        @return SlowCounterConstraints: object with constraints for the counter
        """
        return self._counter.get_constraints()

    def set_oversampling(self, oversampling):
        """
        Sets the number of samples to average per data point, i.e. the oversampling factor.
        The counter is stopped first and restarted afterwards.

        @param int oversampling: oversampling in units of bins (positive int).

        @return int: oversampling in units of bins.
        """
        oversampling = int(oversampling)
        if oversampling < 1:
            self.log.warning('Oversampling factor has to be larger than 0! '
                             '"set_oversampling" call ignored!')

        self._oversampling = oversampling
        self.set_count_frequency(self._count_frequency)
        self.sigCounterSettingsChanged.emit({'oversampling': self._oversampling})
        return self._oversampling

    def set_count_length(self, length):
        """ Sets the time trace in units of bins.

        @param int length: time trace in units of bins (positive int).

        @return int: length of time trace in units of bins

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        length = int(length)
        if length < 1:
            self.log.warning('Count length has to be larger than 0! "set_count_length" call '
                             'ignored!')
        restart = self.module_state() == 'locked'

        self._stop_counting_wait()
        self._count_length = length
        # if the counter was running, restart it
        if restart:
            self.start_counting()

        self.sigCounterSettingsChanged.emit({'count_length': self._count_length})
        return self._count_length

    def set_count_frequency(self, frequency):
        """ Sets the frequency with which the data is acquired.

        @param float frequency: the desired frequency of counting in Hz

        @return float: the actual frequency of counting in Hz

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        constraints = self.get_hardware_constraints()

        restart = self.module_state() == 'locked'

        if constraints.min_count_frequency <= frequency * self._oversampling <= constraints.max_count_frequency:
            self._stop_counting_wait()
            self._count_frequency = frequency
            # if the counter was running, restart it
            if restart:
                self.start_counting()
        else:
            self.log.warning('Counter sampling frequency (count_frequency * oversampling) not in '
                             'range! "set_count_frequency" call ignored!')
        self.sigCounterSettingsChanged.emit({'count_frequency': self._count_frequency})
        return self._count_frequency

    @property
    def count_length(self):
        return self._count_length

    @property
    def count_frequency(self):
        return self._count_frequency

    @property
    def oversampling(self):
        return self._oversampling

    @property
    def sample_rate(self):
        return self._oversampling * self._count_frequency

    @property
    def is_recording(self):
        return self._cumulative_acquisition

    @property
    def counting_mode(self):
        return self._counting_mode

    @property
    def counter_channels(self):
        return self._counter.get_counter_channels()

    @property
    def counter_channel_number(self):
        return len(self._counter.get_counter_channels())

    @property
    def count_data(self):
        return self._count_data[:, :-(self._smooth_window_length // 2)]

    def start_recording(self, resume=False):
        """
        Sets up start-time and initializes data array, if not resuming, and changes saving state.
        If the counter is not running it will be started in order to have data to save.

        @return bool: saving state
        """
        if not resume:
            self._data_to_save = list()
            self._saving_start_time = time.time()

        self._cumulative_acquisition = True

        # If the counter is not running, then it should start running so there is data to save
        if self.module_state() != 'locked':
            self.startCount()

        self.sigSavingStatusChanged.emit(self._cumulative_acquisition)
        return self._cumulative_acquisition

    def save_data(self, to_file=True, postfix='', save_figure=True):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save
        @param bool save_figure: select whether png and pdf should be saved

        @return dict parameters: Dictionary which contains the saving parameters
        """
        # stop saving thus saving state has to be set to False
        self._cumulative_acquisition = False
        saving_stop_time = time.time()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(saving_stop_time))
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._oversampling
        parameters['Smooth Window Length (Samples)'] = self._smooth_window_length

        if to_file:
            # If there is a postfix then add separating underscore
            if not postfix:
                filelabel = 'count_trace'
            else:
                filelabel = 'count_trace_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            header = 'Time (s)'
            for i, detector in enumerate(self.counter_channels):
                header = header + ',Signal{0} (counts/s)'.format(i)

            self._data_to_save = np.concatenate(self._data_to_save, axis=1)
            data = {header: self._data_to_save}
            filepath = self._save_logic.get_path_for_module(module_name='Counter')

            if save_figure:
                fig = self.draw_figure(data=self._data_to_save)
            else:
                fig = None
            self._save_logic.save_data(data, filepath=filepath, parameters=parameters,
                                       filelabel=filelabel, plotfig=fig, delimiter='\t')
            self.log.info('Counter Trace saved to:\n{0}'.format(filepath))

        self.sigSavingStatusChanged.emit(self._cumulative_acquisition)
        return self._data_to_save, parameters

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        count_data = data[:, 1:self.counter_channel_number+1]
        time_data = data[:, 0]

        # Scale count values using SI prefix
        prefix = ['', 'k', 'M', 'G']
        prefix_index = 0
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            prefix_index = prefix_index + 1
        counts_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots()
        ax.plot(time_data, count_data, linestyle=':', linewidth=0.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        return fig

    def set_counting_mode(self, mode):
        """
        Set the counting mode, to change between continuous and gated counting.
        Possible options are:
            CountingMode.CONTINUOUS (0)   = counts continuously
            CountingMode.GATED (1)        = bins the counts according to a gate signal
            CountingMode.FINITE_GATED (2) = finite measurement with predefined number of samples

        @param CountingMode|int mode: The counting mode to set. (CountingMode enum or int)

        @return CountingMode: counting mode set
        """
        if not isinstance(mode, (CountingMode, int)):
            self.log.error('Counting mode to set must be CountingMode enum or int type.')
            return self._counting_mode
        if self.module_state() == 'locked':
            self.log.error('Cannot change counting mode while counter is still running.')
            return self._counting_mode

        constraints = self.get_hardware_constraints()
        mode = CountingMode(mode)

        if mode in constraints.counting_mode:
            self._counting_mode = mode
            self.sigCountingModeChanged.emit(self._counting_mode)
        else:
            self.log.error('Counting mode not supported by slow counter hardware. '
                           '"set_counting_mode" call ignored!')
        return self._counting_mode

    # FIXME: Not implemented for self._counting_mode == 'gated'
    def start_counting(self):
        """
        Start data acquisition loop.

        @return error: 0 is OK, -1 is error
        """
        print('start called')
        with self.threadlock:
            print('start in lock')
            # Lock module
            if self.module_state() == 'locked':
                self.log.warning('Counter already running. "start_counting" call ignored.')
                self.sigCounterStatusChanged.emit(True)
                return 0

            self.module_state.lock()
            self.stop_requested = False
            print('start module locked')

            # initialising the data arrays
            self._count_data = np.zeros((self.counter_channel_number,
                                         self._count_length + self._smooth_window_length // 2))
            self.count_data_smoothed = np.zeros(
                (self.counter_channel_number,
                 self._count_length - self._smooth_window_length // 2 - 1))
            self._data_to_save = list()

            # Set up clock
            clock_status = self._counter.set_up_clock(clock_frequency=self.sample_rate)
            if clock_status < 0:
                print('clock nope')
                self.module_state.unlock()
                self.sigCounterStatusChanged.emit(False)
                return -1

            # Set up counter
            # FIXME: Set up gated counting in hardware
            counter_status = self._counter.set_up_counter()
            if counter_status < 0:
                print('counter nope')
                self._counter.close_clock()
                self.module_state.unlock()
                self.sigCounterStatusChanged.emit(False)
                return -1

            self.__last_data_update = time.time()

            # Start data reader loop
            self.sigCounterStatusChanged.emit(True)
            self.sigCountDataNext.emit()
        return 0

    def stop_counting(self):
        """
        Send a request to stop counting.

        @return int: error code (0: OK, -1: error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stop_requested = True
        return 0

    def count_loop_body(self):
        """ This method gets the count data from the hardware for the continuous counting mode (default).

        It runs repeatedly in the logic module event loop by being connected
        to sigCountContinuousNext and emitting sigCountContinuousNext through a queued connection.
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                # check for break condition
                if self.stop_requested:
                    # terminate the hardware counting
                    cnt_err = self._counter.close_counter()
                    clk_err = self._counter.close_clock()
                    if cnt_err < 0 or clk_err < 0:
                        self.log.error('Could not even close the hardware, giving up.')

                    self.module_state.unlock()
                    self.sigCountDataChanged.emit()
                    self.sigCounterStatusChanged.emit(False)
                    return

                # Estimate read length from elapsed time.
                curr_time = time.time()
                samples_to_read = int(max(#(curr_time - self.__last_data_update) * self.sample_rate,
                                          self._data_update_rate * self.sample_rate,
                                          1))
                print(samples_to_read)
                if self._oversampling > 1:
                    samples_to_read += self._oversampling - samples_to_read % self._oversampling
                self.__last_data_update = curr_time

                # read the current counter values
                data = self._counter.get_counter(samples=samples_to_read)
                if data.shape[1] != samples_to_read or data[0, 0] < 0:
                    self.log.error('The counting went wrong, killing the counter.')
                    self.stop_requested = True
                else:
                    if self._counting_mode == CountingMode.CONTINUOUS:
                        self._process_data_continuous(data)
                    elif self._counting_mode == CountingMode.GATED:
                        self._process_data_gated(data)
                    elif self._counting_mode == CountingMode.FINITE_GATED:
                        self._process_data_finite_gated(data)
                    else:
                        self.log.error('No valid counting mode set! Can not process counter data.')

            # call this again from event loop
            self.sigCountDataChanged.emit()
            self.sigCountDataNext.emit()
        return

    def save_current_count_trace(self, name_tag=''):
        """ The currently displayed counttrace will be saved.

        @param str name_tag: optional, personal description that will be
                             appended to the file name

        @return: dict data: Data which was saved
                 str filepath: Filepath
                 dict parameters: Experiment parameters
                 str filelabel: Filelabel

        This method saves the already displayed counts to file and does not
        accumulate them. The counttrace variable will be saved to file with the
        provided name!
        """

        # If there is a postfix then add separating underscore
        if name_tag == '':
            filelabel = 'snapshot_count_trace'
        else:
            filelabel = 'snapshot_count_trace_' + name_tag

        stop_time = self._count_length / self._count_frequency
        time_step_size = stop_time / len(self.countdata)
        x_axis = np.arange(0, stop_time, time_step_size)

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        chans = self.get_channels()
        savearr = np.empty((len(chans) + 1, len(x_axis)))
        savearr[0] = x_axis
        datastr = 'Time (s)'

        for i, ch in enumerate(chans):
            savearr[i+1] = self.countdata[i]
            datastr += ',Signal {0} (counts/s)'.format(i)

        data[datastr] = savearr.transpose()

        # write the parameters:
        parameters = OrderedDict()
        timestr = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(time.time()))
        parameters['Saved at time'] = timestr
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        filepath = self._save_logic.get_path_for_module(module_name='Counter')
        self._save_logic.save_data(data, filepath=filepath, parameters=parameters,
                                   filelabel=filelabel, delimiter='\t')

        self.log.debug('Current Counter Trace saved to: {0}'.format(filepath))
        return data, filepath, parameters, filelabel

    def _process_data_continuous(self, data):
        """
        Processes the raw data from the counting device
        """
        # Down-sample and average according to oversampling factor
        if self._oversampling > 1:
            if data.shape[1] % self._oversampling != 0:
                self.log.error('Number of samples per counter channel not an integer multiple of '
                               'the oversampling factor.')
                return -1
            print('oversampling:', np.mean(data[0]), max(data[0]), len(data[0]))
            tmp = data.reshape(
                (data.shape[0], data.shape[1] // self._oversampling, self._oversampling))
            data = np.mean(tmp, axis=2)
            print('oversampling:', np.mean(data[0]), max(data[0]), len(data[0]))

        # FIXME: Currently all digital count data is converted into a frequency.
        #  This needs to be more generally handled (maybe selectable?)
        digital_channels = [chnl for chnl in self.counter_channels if 'ai' not in chnl.lower()]
        if digital_channels:
            data[:len(digital_channels)] *= self.count_frequency * self.oversampling

        # save the data if necessary
        if self._cumulative_acquisition:
            self._data_to_save.append(data)

        data = data[:, -self._count_data.shape[1]:]
        new_samples = data.shape[1]

        # Roll data array to have a continuously running time trace
        self._count_data = np.roll(self._count_data, -new_samples, axis=1)
        # Insert new data
        self._count_data[:, -new_samples:] = data

        # Calculate moving average
        cumsum = np.cumsum(self._count_data, axis=1)
        n = self._smooth_window_length
        self.count_data_smoothed = (cumsum[:, n:] - cumsum[:, :-n]) / n
        return

    def _process_data_gated(self, data):
        """
        Processes the raw data from the counting device
        @return:
        """
        self.log.warning('Counting mode GATED not implemented, yet.')
        # # remember the new count data in circular array
        # self.countdata[0] = np.average(self.rawdata[0])
        # # move the array to the left to make space for the new data
        # self.countdata = np.roll(self.countdata, -1)
        # # also move the smoothing array
        # self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
        # # calculate the median and save it
        # self.countdata_smoothed[-int(self._smooth_window_length / 2) - 1:] = np.median(
        #     self.countdata[-self._smooth_window_length:])
        #
        # # save the data if necessary
        # if self._saving:
        #     # if oversampling is necessary
        #     if self._counting_samples > 1:
        #         self._sampling_data = np.empty((self._counting_samples, 2))
        #         self._sampling_data[:, 0] = time.time() - self._saving_start_time
        #         self._sampling_data[:, 1] = self.rawdata[0]
        #         self._data_to_save.extend(list(self._sampling_data))
        #     # if we don't want to use oversampling
        #     else:
        #         # append tuple to data stream (timestamp, average counts)
        #         self._data_to_save.append(np.array((time.time() - self._saving_start_time,
        #                                             self.countdata[-1])))
        # return
        pass

    def _process_data_finite_gated(self, data):
        """
        Processes the raw data from the counting device
        @return:
        """
        self.log.warning('Counting mode FINITE_GATED not implemented, yet.')
        # if self._already_counted_samples+len(self.rawdata[0]) >= len(self.countdata):
        #     needed_counts = len(self.countdata) - self._already_counted_samples
        #     self.countdata[0:needed_counts] = self.rawdata[0][0:needed_counts]
        #     self.countdata = np.roll(self.countdata, -needed_counts)
        #     self._already_counted_samples = 0
        #     self.stopRequested = True
        # else:
        #     # replace the first part of the array with the new data:
        #     self.countdata[0:len(self.rawdata[0])] = self.rawdata[0]
        #     # roll the array by the amount of data it had been inserted:
        #     self.countdata = np.roll(self.countdata, -len(self.rawdata[0]))
        #     # increment the index counter:
        #     self._already_counted_samples += len(self.rawdata[0])
        # return
        return

    def _stop_counting_wait(self, timeout=5.0):
        """
        Stops the counter and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        self.stop_counting()
        start_time = time.time()
        while self.module_state() == 'locked':
            time.sleep(0.1)
            if time.time() - start_time >= timeout:
                self.log.error('Stopping the counter timed out after {0}s'.format(timeout))
                return -1
        return 0
