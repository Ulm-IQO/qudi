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

from core.module import Connector, StatusVar
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
    sigCounterUpdated = QtCore.Signal()

    sigCountDataNext = QtCore.Signal()

    sigGatedCounterFinished = QtCore.Signal()
    sigGatedCounterContinue = QtCore.Signal(bool)
    sigCountingSamplesChanged = QtCore.Signal(int)
    sigCountLengthChanged = QtCore.Signal(int)
    sigCountFrequencyChanged = QtCore.Signal(float)
    sigSavingStatusChanged = QtCore.Signal(bool)
    sigCountStatusChanged = QtCore.Signal(bool)
    sigCountingModeChanged = QtCore.Signal(CountingMode)


    _modclass = 'CounterLogic'
    _modtype = 'logic'

    ## declare connectors
    counter1 = Connector(interface='SlowCounterInterface')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _count_length = StatusVar('count_length', 300)
    _smooth_window_length = StatusVar('smooth_window_length', 10)
    _counting_samples = StatusVar('counting_samples', 1)
    _count_frequency = StatusVar('count_frequency', 50)
    _saving = StatusVar('saving', False)


    def __init__(self, config, **kwargs):
        """ Create CounterLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        # in bins
        self._count_length = 300
        self._smooth_window_length = 10
        self._counting_samples = 1      # oversampling
        # in hertz
        self._count_frequency = 50

        # self._binned_counting = True  # UNUSED?
        self._counting_mode = CountingMode['CONTINUOUS']

        self._saving = False
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Connect to hardware and save logic
        self._counting_device = self.counter1()
        self._save_logic = self.savelogic()

        # Recall saved app-parameters
        if 'counting_mode' in self._statusVariables:
            self._counting_mode = CountingMode[self._statusVariables['counting_mode']]

        constraints = self.get_hardware_constraints()
        number_of_detectors = constraints.max_detectors

        # initialize data arrays
        self.countdata = np.zeros([len(self.get_channels()), self._count_length])
        self.countdata_smoothed = np.zeros([len(self.get_channels()), self._count_length])
        self.rawdata = np.zeros([len(self.get_channels()), self._counting_samples])
        self._already_counted_samples = 0  # For gated counting
        self._data_to_save = []

        # Flag to stop the loop
        self.stopRequested = False

        self._saving_start_time = time.time()

        # connect signals
        self.sigCountDataNext.connect(self.count_loop_body, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Save parameters to disk
        self._statusVariables['counting_mode'] = self._counting_mode.name

        # Stop measurement
        if self.module_state() == 'locked':
            self._stopCount_wait()

        self.sigCountDataNext.disconnect()
        return

    def get_hardware_constraints(self):
        """
        Retrieve the hardware constrains from the counter device.

        @return SlowCounterConstraints: object with constraints for the counter
        """
        return self._counting_device.get_constraints()

    def set_counting_samples(self, samples=1):
        """
        Sets the length of the counted bins.
        The counter is stopped first and restarted afterwards.

        @param int samples: oversampling in units of bins (positive int ).

        @return int: oversampling in units of bins.
        """
        # Determine if the counter has to be restarted after setting the parameter
        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if samples > 0:
            self._stopCount_wait()
            self._counting_samples = int(samples)
            # if the counter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('counting_samples has to be larger than 0! Command ignored!')
        self.sigCountingSamplesChanged.emit(self._counting_samples)
        return self._counting_samples

    def set_count_length(self, length=300):
        """ Sets the time trace in units of bins.

        @param int length: time trace in units of bins (positive int).

        @return int: length of time trace in units of bins

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if length > 0:
            self._stopCount_wait()
            self._count_length = int(length)
            # if the counter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('count_length has to be larger than 0! Command ignored!')
        self.sigCountLengthChanged.emit(self._count_length)
        return self._count_length

    def set_count_frequency(self, frequency=50):
        """ Sets the frequency with which the data is acquired.

        @param float frequency: the desired frequency of counting in Hz

        @return float: the actual frequency of counting in Hz

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        constraints = self.get_hardware_constraints()

        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if constraints.min_count_frequency <= frequency <= constraints.max_count_frequency:
            self._stopCount_wait()
            self._count_frequency = frequency
            # if the counter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('count_frequency not in range! Command ignored!')
        self.sigCountFrequencyChanged.emit(self._count_frequency)
        return self._count_frequency

    def get_count_length(self):
        """ Returns the currently set length of the counting array.

        @return int: count_length
        """
        return self._count_length

    #FIXME: get from hardware
    def get_count_frequency(self):
        """ Returns the currently set frequency of counting (resolution).

        @return float: count_frequency
        """
        return self._count_frequency

    def get_counting_samples(self):
        """ Returns the currently set number of samples counted per readout.

        @return int: counting_samples
        """
        return self._counting_samples

    def get_saving_state(self):
        """ Returns if the data is saved in the moment.

        @return bool: saving state
        """
        return self._saving

    def start_saving(self, resume=False):
        """
        Sets up start-time and initializes data array, if not resuming, and changes saving state.
        If the counter is not running it will be started in order to have data to save.

        @return bool: saving state
        """
        if not resume:
            self._data_to_save = []
            self._saving_start_time = time.time()

        self._saving = True

        # If the counter is not running, then it should start running so there is data to save
        if self.module_state() != 'locked':
            self.startCount()

        self.sigSavingStatusChanged.emit(self._saving)
        return self._saving

    def save_data(self, to_file=True, postfix='', save_figure=True):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save
        @param bool save_figure: select whether png and pdf should be saved

        @return dict parameters: Dictionary which contains the saving parameters
        """
        # stop saving thus saving state has to be set to False
        self._saving = False
        self._saving_stop_time = time.time()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        if to_file:
            # If there is a postfix then add separating underscore
            if postfix == '':
                filelabel = 'count_trace'
            else:
                filelabel = 'count_trace_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            header = 'Time (s)'
            for i, detector in enumerate(self.get_channels()):
                header = header + ',Signal{0} (counts/s)'.format(i)

            data = {header: self._data_to_save}
            filepath = self._save_logic.get_path_for_module(module_name='Counter')

            if save_figure:
                fig = self.draw_figure(data=np.array(self._data_to_save))
            else:
                fig = None
            self._save_logic.save_data(data, filepath=filepath, parameters=parameters,
                                       filelabel=filelabel, plotfig=fig, delimiter='\t')
            self.log.info('Counter Trace saved to:\n{0}'.format(filepath))

        self.sigSavingStatusChanged.emit(self._saving)
        return self._data_to_save, parameters

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        count_data = data[:, 1:len(self.get_channels())+1]
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

    def set_counting_mode(self, mode='CONTINUOUS'):
        """Set the counting mode, to change between continuous and gated counting.
        Possible options are:
            'CONTINUOUS'    = counts continuously
            'GATED'         = bins the counts according to a gate signal
            'FINITE_GATED'  = finite measurement with predefined number of samples

        @return str: counting mode
        """
        constraints = self.get_hardware_constraints()
        if self.module_state() != 'locked':
            if CountingMode[mode] in constraints.counting_mode:
                self._counting_mode = CountingMode[mode]
                self.log.debug('New counting mode: {}'.format(self._counting_mode))
            else:
                self.log.warning('Counting mode not supported from hardware. Command ignored!')
            self.sigCountingModeChanged.emit(self._counting_mode)
        else:
            self.log.error('Cannot change counting mode while counter is still running.')
        return self._counting_mode

    def get_counting_mode(self):
        """ Retrieve the current counting mode.

        @return str: one of the possible counting options:
                'CONTINUOUS'    = counts continuously
                'GATED'         = bins the counts according to a gate signal
                'FINITE_GATED'  = finite measurement with predefined number of samples
        """
        return self._counting_mode

    # FIXME: Not implemented for self._counting_mode == 'gated'
    def startCount(self):
        """ This is called externally, and is basically a wrapper that
            redirects to the chosen counting mode start function.

            @return error: 0 is OK, -1 is error
        """
        # Sanity checks
        constraints = self.get_hardware_constraints()
        if self._counting_mode not in constraints.counting_mode:
            self.log.error('Unknown counting mode "{0}". Cannot start the counter.'
                           ''.format(self._counting_mode))
            self.sigCountStatusChanged.emit(False)
            return -1

        with self.threadlock:
            # Lock module
            if self.module_state() != 'locked':
                self.module_state.lock()
            else:
                self.log.warning('Counter already running. Method call ignored.')
                return 0

            # Set up clock
            clock_status = self._counting_device.set_up_clock(clock_frequency=self._count_frequency)
            if clock_status < 0:
                self.module_state.unlock()
                self.sigCountStatusChanged.emit(False)
                return -1

            # Set up counter
            if self._counting_mode == CountingMode['FINITE_GATED']:
                counter_status = self._counting_device.set_up_counter(counter_buffer=self._count_length)
            # elif self._counting_mode == CountingMode['GATED']:
            #
            else:
                counter_status = self._counting_device.set_up_counter()
            if counter_status < 0:
                self._counting_device.close_clock()
                self.module_state.unlock()
                self.sigCountStatusChanged.emit(False)
                return -1

            # initialising the data arrays
            self.rawdata = np.zeros([len(self.get_channels()), self._counting_samples])
            self.countdata = np.zeros([len(self.get_channels()), self._count_length])
            self.countdata_smoothed = np.zeros([len(self.get_channels()), self._count_length])
            self._sampling_data = np.empty([len(self.get_channels()), self._counting_samples])

            # the sample index for gated counting
            self._already_counted_samples = 0

            # Start data reader loop
            self.sigCountStatusChanged.emit(True)
            self.sigCountDataNext.emit()
            return

    def stopCount(self):
        """ Set a flag to request stopping counting.
        """
        if self.module_state() == 'locked':
            with self.threadlock:
                self.stopRequested = True
        return

    def count_loop_body(self):
        """ This method gets the count data from the hardware for the continuous counting mode (default).

        It runs repeatedly in the logic module event loop by being connected
        to sigCountContinuousNext and emitting sigCountContinuousNext through a queued connection.
        """
        if self.module_state() == 'locked':
            with self.threadlock:
                # check for aborts of the thread in break if necessary
                if self.stopRequested:
                    # close off the actual counter
                    cnt_err = self._counting_device.close_counter()
                    clk_err = self._counting_device.close_clock()
                    if cnt_err < 0 or clk_err < 0:
                        self.log.error('Could not even close the hardware, giving up.')
                    # switch the state variable off again
                    self.stopRequested = False
                    self.module_state.unlock()
                    self.sigCounterUpdated.emit()
                    return

                # read the current counter value
                self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)
                if self.rawdata[0, 0] < 0:
                    self.log.error('The counting went wrong, killing the counter.')
                    self.stopRequested = True
                else:
                    if self._counting_mode == CountingMode['CONTINUOUS']:
                        self._process_data_continous()
                    elif self._counting_mode == CountingMode['GATED']:
                        self._process_data_gated()
                    elif self._counting_mode == CountingMode['FINITE_GATED']:
                        self._process_data_finite_gated()
                    else:
                        self.log.error('No valid counting mode set! Can not process counter data.')

            # call this again from event loop
            self.sigCounterUpdated.emit()
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

    def get_channels(self):
        """ Shortcut for hardware get_counter_channels.

            @return list(str): return list of active counter channel names
        """
        return self._counting_device.get_counter_channels()

    def _process_data_continous(self):
        """
        Processes the raw data from the counting device
        @return:
        """
        for i, ch in enumerate(self.get_channels()):
            # remember the new count data in circular array
            self.countdata[i, 0] = np.average(self.rawdata[i])
        # move the array to the left to make space for the new data
        self.countdata = np.roll(self.countdata, -1, axis=1)
        # also move the smoothing array
        self.countdata_smoothed = np.roll(self.countdata_smoothed, -1, axis=1)
        # calculate the median and save it
        window = -int(self._smooth_window_length / 2) - 1
        for i, ch in enumerate(self.get_channels()):
            self.countdata_smoothed[i, window:] = np.median(self.countdata[i,
                                                            -self._smooth_window_length:])

        # save the data if necessary
        if self._saving:
             # if oversampling is necessary
            if self._counting_samples > 1:
                chans = self.get_channels()
                self._sampling_data = np.empty([len(chans) + 1, self._counting_samples])
                self._sampling_data[0, :] = time.time() - self._saving_start_time
                for i, ch in enumerate(chans):
                    self._sampling_data[i+1, 0] = self.rawdata[i]

                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                chans = self.get_channels()
                newdata = np.empty((len(chans) + 1, ))
                newdata[0] = time.time() - self._saving_start_time
                for i, ch in enumerate(chans):
                    newdata[i+1] = self.countdata[i, -1]
                self._data_to_save.append(newdata)
        return

    def _process_data_gated(self):
        """
        Processes the raw data from the counting device
        @return:
        """
        # remember the new count data in circular array
        self.countdata[0] = np.average(self.rawdata[0])
        # move the array to the left to make space for the new data
        self.countdata = np.roll(self.countdata, -1)
        # also move the smoothing array
        self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
        # calculate the median and save it
        self.countdata_smoothed[-int(self._smooth_window_length / 2) - 1:] = np.median(
            self.countdata[-self._smooth_window_length:])

        # save the data if necessary
        if self._saving:
            # if oversampling is necessary
            if self._counting_samples > 1:
                self._sampling_data = np.empty((self._counting_samples, 2))
                self._sampling_data[:, 0] = time.time() - self._saving_start_time
                self._sampling_data[:, 1] = self.rawdata[0]
                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                self._data_to_save.append(np.array((time.time() - self._saving_start_time,
                                                    self.countdata[-1])))
        return

    def _process_data_finite_gated(self):
        """
        Processes the raw data from the counting device
        @return:
        """
        if self._already_counted_samples+len(self.rawdata[0]) >= len(self.countdata):
            needed_counts = len(self.countdata) - self._already_counted_samples
            self.countdata[0:needed_counts] = self.rawdata[0][0:needed_counts]
            self.countdata = np.roll(self.countdata, -needed_counts)
            self._already_counted_samples = 0
            self.stopRequested = True
        else:
            # replace the first part of the array with the new data:
            self.countdata[0:len(self.rawdata[0])] = self.rawdata[0]
            # roll the array by the amount of data it had been inserted:
            self.countdata = np.roll(self.countdata, -len(self.rawdata[0]))
            # increment the index counter:
            self._already_counted_samples += len(self.rawdata[0])
        return

    def _stopCount_wait(self, timeout=5.0):
        """
        Stops the counter and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        self.stopCount()
        start_time = time.time()
        while self.module_state() == 'locked':
            time.sleep(0.1)
            if time.time() - start_time >= timeout:
                self.log.error('Stopping the counter timed out after {0}s'.format(timeout))
                return -1
        return 0
