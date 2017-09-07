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


class GatedCounterLogic(GenericLogic):
    """
    This logic module gathers from a gated hardware counting device.
    """
    sigCountDataUpdated = QtCore.Signal(np.ndarray, list, list, int)
    sigCountSettingsChanged = QtCore.Signal(dict)
    sigCountStatusChanged = QtCore.Signal(bool, bool)

    sigCountDataNext = QtCore.Signal()

    _modclass = 'GatedCounterLogic'
    _modtype = 'logic'

    ## declare connectors
    counter1 = Connector(interface='SlowCounterInterface')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _number_of_gates = StatusVar('number_of_gates', 100)
    _samples_per_read = StatusVar('samples_per_read', 5)

    def __init__(self, config, **kwargs):
        """ Create CounterLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)
        #locking for thread safety
        self.threadlock = Mutex()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Connect to hardware and save logic
        self._counting_device = self.get_connector('counter1')
        self._save_logic = self.get_connector('savelogic')

        # initialize data arrays
        self.countdata = np.zeros([len(self._counting_device.get_counter_channels()),
                                   self._number_of_gates], dtype=int)
        self.histogram = [np.zeros(self._number_of_gates, dtype=int) for i, ch in
                          enumerate(self._counting_device.get_counter_channels())]
        self.histogram_bin_array = [np.zeros(self._number_of_gates, dtype=int) for i, ch in
                                    enumerate(self._counting_device.get_counter_channels())]
        self._databuffer = np.zeros([len(self._counting_device.get_counter_channels()),
                                     self._samples_per_read])
        self.already_counted_samples = 0

        # Flag to stop the loop
        self.stopRequested = False

        # connect signals
        self.sigCountDataNext.connect(self.count_loop_body, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Stop measurement
        if self.getState() != 'idle':
            self._stop_count_wait()

        self.sigCountDataNext.disconnect()
        return

    def set_counter_settings(self, settings=None):
        """
        Sets various settings for gated counting.
        Restarts the counting if it is already running.

        @param dict settings: A dictionary containing the settings name and value to set.

        @return dict: dictionary containing the actually set settings
        """
        if settings is None or not isinstance(settings, dict):
            settings = dict()

        return_dict = dict()

        # if nothing has been passed or dict is empty, return empty dict.
        if len(settings) < 1:
            return return_dict

        # Determine if the counter has to be restarted after setting the parameter
        if self.getState() == 'locked':
            restart = True
            self._stop_count_wait()
        else:
            restart = False

        if 'number_of_gates' in settings:
            self._number_of_gates = settings['number_of_gates']
            return_dict['number_of_gates'] = self._number_of_gates
        if 'samples_per_read' in settings:
            self._samples_per_read = settings['samples_per_read']
            return_dict['samples_per_read'] = self._samples_per_read

        # if the counter was running, restart it
        if restart:
            self.start_count()

        self.sigCountSettingsChanged.emit(return_dict)
        return return_dict

    def start_count(self):
        """
        This is called externally and starts the counting loop.

        @return error: 0 is OK, -1 is error
        """
        # Sanity checks
        constraints = self._counting_device.get_constraints()

        with self.threadlock:
            # Perform sanity checks on settings before starting
            if self._samples_per_read > self._number_of_gates:
                self.log.warning('Number of samples per read larger than number of gates. ({0:d} > '
                                 '{1:d}).\nSetting "samples_per_read" to "number_of_gates".'
                                 ''.format(self._samples_per_read, self._number_of_gates))
                self.set_counter_settings(settings={'samples_per_read': self._number_of_gates})

            # Lock module
            if self.getState() != 'locked':
                self.lock()
            else:
                self.log.warning('Counter already running. Method call ignored.')
                return 0

            # Set up counter in hardware
            counter_status = self._counting_device.set_up_gated_counter(buffer_length=self._number_of_gates)
            if counter_status < 0:
                self.unlock()
                self.sigCountStatusChanged.emit(False, False)
                return -1

            # initialising the data arrays
            self.countdata = np.zeros([len(self._counting_device.get_counter_channels()),
                                       self._number_of_gates], dtype=int)
            self.histogram = [np.zeros(self._number_of_gates, dtype=int) for i, ch in
                              enumerate(self._counting_device.get_counter_channels())]
            self.histogram_bin_array = [np.zeros(self._number_of_gates, dtype=int) for i, ch in
                                        enumerate(self._counting_device.get_counter_channels())]
            self._databuffer = np.zeros([len(self._counting_device.get_counter_channels()),
                                         self._samples_per_read])
            # initialize the sample index for gated counting
            self.already_counted_samples = 0

            # Start data reader loop
            self.sigCountStatusChanged.emit(True, False)
            self.sigCountDataNext.emit()
        return

    def stop_count(self):
        """ Set a flag to request stopping counting.
        """
        if self.getState() == 'locked':
            with self.threadlock:
                self.stopRequested = True
        return

    def count_loop_body(self):
        """
        This method gets the count data from the hardware.

        It runs repeatedly in the logic module event loop by being connected to sigCountDataNext
        and emitting sigCountDataNext through a queued connection.
        """
        if self.getState() == 'locked':
            with self.threadlock:
                # check for aborts of the thread in break if necessary
                if self.stopRequested or (self.already_counted_samples >= self._number_of_gates):
                    # stop and close the actual counter
                    cnt_err = self._counting_device.close_gated_counter()
                    if cnt_err < 0:
                        self.log.error('Could not stop the gated counting hardware! giving up...')
                    # switch the state variable off again
                    self.stopRequested = False
                    self.unlock()
                    self.sigCountStatusChanged.emit(False, False)
                    return

                # read the current counter value
                self._databuffer = self._counting_device.get_gated_counts(samples=self._samples_per_read)
                if self._databuffer[0, 0] < 0:
                    self.log.error('The counting went wrong, killing the counter.')
                    self.stopRequested = True
                else:
                    self._process_data_finite_gated()
                    self.sigCountDataUpdated.emit(self.countdata, self.histogram,
                                                  self.histogram_bin_array,
                                                  self.already_counted_samples)

                # call this again from event loop
                self.sigCountDataNext.emit()
        return

    def _process_data_finite_gated(self):
        """
        Processes the raw data from the gated counting device.
        """
        # Get count trace
        if (self.already_counted_samples + self._databuffer[0].size) > self._number_of_gates:
            needed_counts = self._number_of_gates - self.already_counted_samples
            for i in range(self.countdata.shape[0]):
                self.countdata[i][0:needed_counts] = self._databuffer[i][0:needed_counts]
                self.countdata[i] = np.roll(self.countdata[i], -needed_counts)
            self.already_counted_samples += needed_counts
            self.stopRequested = True
        else:
            for i in range(self.countdata.shape[0]):
                # replace the first part of the array with the new data:
                self.countdata[i][0:self._databuffer[i].size] = self._databuffer[i]
                # roll the array by the amount of data it had been inserted:
                self.countdata[i] = np.roll(self.countdata[i], -self._databuffer[i].size)
                # increment the index counter:
            self.already_counted_samples += self._databuffer[0].size

        # Create histogram
        for i in range(self.countdata.shape[0]):
            self.histogram[i], self.histogram_bin_array[i] = np.histogram(self.countdata[i][-self.already_counted_samples:], bins=np.arange(np.max(self.countdata[i])+1))
        return

    def save_data(self, tag=''):
        """ Save the counter trace data and writes it to a file.

        @param str tag: user-definable tag which will be added to the filename upon save
        """
        # write the parameters:
        parameters = OrderedDict()
        parameters['Number of gates/samples (#)'] = self._number_of_gates
        parameters['Number of samples per read command (#)'] = self._samples_per_read

        if tag == '':
            filelabel = 'gated_counter_trace'
        else:
            filelabel = 'gated_counter_trace_' + tag

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['gate index'] = np.arange(self.countdata.shape[1])
        if self.countdata.shape[0] == 1:
            data['signal (#counts)'] = self.countdata[0]
        else:
            for i in range(1, self.countdata.shape[0] + 1):
                data['signal{0:d} (#counts)'.format(i)] = self.countdata[i-1]

        fig = self.draw_figure()
        self._save_logic.save_data(data, fmt='%d', parameters=parameters,  filelabel=filelabel, plotfig=fig)


        if tag == '':
            filelabel = 'gated_counter_histogram'
        else:
            filelabel = 'gated_counter_histogram_' + tag
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        if len(self.histogram) == 1:
            data['counts'] = self.histogram_bin_array[0][:-1]
            data['occurences'] = self.histogram[0]
        else:
            for i, histo in enumerate(self.histogram):
                data['counts{0:d}'.format(i+1)] = self.histogram_bin_array[i][:-1]
                data['occurences{0:d}'.format(i+1)] = histo

        self._save_logic.save_data(data, fmt='%d', filelabel=filelabel)

        self.log.info('Gated counter data saved.')
        return

    def draw_figure(self):
        """ Draw figure to save with data file.

        @return: fig: a matplotlib figure object to be saved to file.
        """
        y_data = self.countdata[0]
        x_data = np.arange(self.countdata[0].size, dtype=int)

        # Scale count values using SI prefix
        prefix = ['', 'k', 'M', 'G']
        prefix_index = 0
        while np.max(y_data) > 1000:
            y_data = y_data / 1000
            prefix_index += 1

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots()
        ax.plot(x_data, y_data, linestyle='-', linewidth=0.5)
        ax.set_xlabel('Gate index (#)')
        ax.set_ylabel('Fluorescence (' + prefix[prefix_index] + 'counts)')
        return fig

    def _stop_count_wait(self, timeout=5.0):
        """
        Stops the counter and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        self.stop_count()
        start_time = time.time()
        while self.getState() == 'locked':
            time.sleep(0.1)
            if (time.time() - start_time) >= timeout:
                self.log.error('Stopping the counter timed out after {0}s'.format(timeout))
                return -1
        return 0
