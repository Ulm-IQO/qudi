# -*- coding: utf-8 -*-
"""
This file contains the QuDi counter logic class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import matplotlib.pyplot as plt

class CounterLogic(GenericLogic):
    """ This logic module gathers data from a hardware counting device.

    @signal sigCounterUpdate: there is new counting data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???
    """
    sigCounterUpdated = QtCore.Signal()
    sigCountContinuousNext = QtCore.Signal()
    sigCountGatedNext = QtCore.Signal()

    sigCountFiniteGatedNext = QtCore.Signal()
    sigGatedCounterFinished = QtCore.Signal()
    sigGatedCounterContinue = QtCore.Signal(bool)

    _modclass = 'CounterLogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'counter1': 'SlowCounterInterface',
            'savelogic': 'SaveLogic'
            }
    _out = {'counterlogic': 'CounterLogic'}

    def __init__(self, config, **kwargs):
        """ Create CounterLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

        self._count_length = 300
        self._count_frequency = 50
        self._counting_samples = 1
        self._smooth_window_length = 10
        self._binned_counting = True

        self._counting_mode = 'continuous'


    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """
        self.countdata = np.zeros((self._count_length,))
        self.countdata_smoothed = np.zeros((self._count_length,))
        self.countdata2 = np.zeros((self._count_length,))
        self.countdata_smoothed2 = np.zeros((self._count_length,))
        self.rawdata = np.zeros([2, self._counting_samples])

        self.running = False
        self.stopRequested = False
        self._saving = False
        self._data_to_save=[]
        self._saving_start_time=time.time()

        self._counting_device = self.connector['in']['counter1']['object']
#        print("Counting device is", self._counting_device)

        self._save_logic = self.connector['in']['savelogic']['object']

        #QSignals
        self.sigCountContinuousNext.connect(self.countLoopBody_continuous, QtCore.Qt.QueuedConnection)
        self.sigCountGatedNext.connect(self.countLoopBody_gated, QtCore.Qt.QueuedConnection)

        # for finite gated counting:
        self.sigCountFiniteGatedNext.connect(self.countLoopBody_finite_gated,
                                             QtCore.Qt.QueuedConnection)

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.stopCount()
        return

    def set_counting_samples(self, samples = 1):
        """ Sets the length of the counted bins.

        @param int length: the length of the array to be set.

        @return int: error code (0:OK, -1:error)

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        # do I need to restart the counter?
        restart = False

        # if the counter is running, stop it
        if self.getState() == 'locked':
            restart = True
            self.stopCount()
            while self.getState() == 'locked':
                time.sleep(0.01)

        self._counting_samples = int(samples)

        # if the counter was running, restart it
        if restart:
            self.startCount()

        return 0

    def set_count_length(self, length = 300):
        """ Sets the length of the counted bins.

        @param int length: the length of the array to be set.

        @return int: error code (0:OK, -1:error)

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        # do I need to restart the counter?
        restart = False

        # if the counter is running, stop it
        if self.getState() == 'locked':
            restart = True
            self.stopCount()
            while self.getState() == 'locked':
                time.sleep(0.01)

        self._count_length = int(length)

        # if the counter was running, restart it
        if restart:
            self.startCount()

        return 0

    def set_count_frequency(self, frequency = 50):
        """ Sets the frequency with which the data is acquired.

        @param int frequency: the frequency of counting in Hz.

        @return int: error code (0:OK, -1:error)

        This makes sure, the counter is stopped first and restarted afterwards.
        """

        # do I need to restart the counter?
        restart = False

        # if the counter is running, stop it
        if self.getState() == 'locked':
            restart = True
            self.stopCount()
            while self.getState() == 'locked':
                time.sleep(0.01)

        self._count_frequency = int(frequency)

        # if the counter was running, restart it
        if restart:
            self.startCount()

        return 0

    def get_count_length(self):
        """ Returns the currently set length of the counting array.

        @return int: count_length
        """
        return self._count_length

    def get_count_frequency(self):
        """ Returns the currently set frequency of counting (resolution).

        @return int: count_frequency
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
        """ Starts saving the data in a list.

        @return int: error code (0:OK, -1:error)
        """

        if not resume:
            self._data_to_save = []
            self._saving_start_time = time.time()
        self._saving = True

        # If the counter is not running, then it should start running so there is data to save
        if self.isstate('idle'):
            self.startCount()

        return 0

    def save_data(self, to_file=True, postfix=''):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save

        @return np.array([2 or 3][X]), OrderedDict: array with the
        """
        self._saving = False
        self._saving_stop_time = time.time()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        if to_file:
            # If there is a postfix then add separating underscore
            if postfix == '':
                filelabel = 'count_trace'
            else:
                filelabel = 'count_trace_'+postfix

            # prepare the data in a dict or in an OrderedDict:
            data = OrderedDict()
            data = {'Time (s),Signal (counts/s)': self._data_to_save}
            if self._counting_device._photon_source2 is not None:
                data = {'Time (s),Signal 1 (counts/s),Signal 2 (counts/s)': self._data_to_save}

            filepath = self._save_logic.get_path_for_module(module_name='Counter')

            fig = self.draw_figure(data=np.array(self._data_to_save))

            self._save_logic.save_data(data,
                                       filepath,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       as_text=True,
                                       plotfig = fig
                                       )
            #, as_xml=False, precision=None, delimiter=None)
            self.log.debug('Counter Trace saved to:\n{0}'.format(filepath))

        return self._data_to_save, parameters

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        # TODO: Draw plot for second APD if it is connected

        count_data = data[:,1]
        time_data = data[:,0]

        # Scale count values using SI prefix
        prefix = ['', 'k', 'M', 'G']
        prefix_index = 0

        while np.max(count_data) > 1000:
            count_data = count_data/1000
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

    def set_counting_mode(self, mode='continuous'):
        """Set the counting mode, to change between continuous and gated counting.
        Possible options are:
            'continuous'    = counts continuously
            'gated'         = bins the counts according to a gate signal
            'finite-gated'  = finite measurement with predefined number of samples
        """
        self._counting_mode = mode

    def startCount(self):
        """ This is called externally, and is basically a wrapper that
            redirects to the chosen counting mode start function.
        """

        if self._counting_mode == 'continuous':
            self._startCount_continuous()
        elif self._counting_mode == 'gated':
            self._startCount_gated()
        elif self._counting_mode == 'finite-gated':
            self._startCount_finite_gated()
        else:
            self.log.error('Unknown counting mode, cannot start the counter.')

    def _startCount_continuous(self):
        """Prepare to start counting change state and start counting 'loop'."""
        # setting up the counter
        # set a lock, to signify the measurment is running
        self.lock()

        returnvalue = self._counting_device.set_up_clock(clock_frequency = self._count_frequency)
        if returnvalue < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return

        returnvalue = self._counting_device.set_up_counter()
        if returnvalue < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return

        # initialising the data arrays
        self.rawdata = np.zeros([2, self._counting_samples])
        self.countdata = np.zeros((self._count_length,))
        self.countdata_smoothed = np.zeros((self._count_length,))
        self._sampling_data = np.empty((self._counting_samples, 2))

        # It is robust to check whether the photon_source2 even exists first.
        if hasattr(self._counting_device, '_photon_source2'):
            if self._counting_device._photon_source2 is not None:
                self.countdata2 = np.zeros((self._count_length,))
                self.countdata_smoothed2 = np.zeros((self._count_length,))
                self._sampling_data2 = np.empty((self._counting_samples, 2))

        self.sigCountContinuousNext.emit()

    def _startCount_gated(self):
        """Prepare to start gated counting, and start the loop.
        """
        #eventually:
        #self.sigCountGatedNext.emit()
        pass

    def stopCount(self):
        """ Set a flag to request stopping counting.
        """
        with self.threadlock:
            self.stopRequested = True

    def _startCount_finite_gated(self):
        """Prepare to start finite gated counting.

        Change state and start counting 'loop'."""

        # setting up the counter
        # set a lock, to signify the measurment is running
        self.lock()

        returnvalue = self._counting_device.set_up_clock(clock_frequency = self._count_frequency)
        if returnvalue < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return

        returnvalue = self._counting_device.set_up_counter(counter_buffer=self._count_length)
        if returnvalue < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return

        # initialising the data arrays

        # in rawdata the 'fresh counts' are read in
        self.rawdata = np.zeros([2, self._counting_samples])
        # countdata contains the appended data, that is the total displayed counttrace
        self.countdata = np.zeros((self._count_length,))
        # do not use a smoothed count trace
        # self.countdata_smoothed = np.zeros((self._count_length,)) # contains the smoothed data
        # for now, there will be no oversampling mode.
        # self._sampling_data = np.empty((self._counting_samples, 2))

        # the index
        self._already_counted_samples = 0

        self.sigCountFiniteGatedNext.emit()



    def countLoopBody_continuous(self):
        """ This method gets the count data from the hardware for the continuous counting mode (default).

        It runs repeatedly in the logic module event loop by being connected
        to sigCountContinuousNext and emitting sigCountContinuousNext through a queued connection.
        """

        # check for aborts of the thread in break if necessary
        if self.stopRequested:
            with self.threadlock:
                try:
                    # close off the actual counter
                    self._counting_device.close_counter()
                    self._counting_device.close_clock()
                except Exception as e:
                    self.log.exception('Could not even close the hardware,'
                            ' giving up.')
                    raise e
                finally:
                    # switch the state variable off again
                    self.unlock()
                    self.stopRequested = False
                    self.sigCounterUpdated.emit()
                    return

        try:
            # read the current counter value
            self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)

        except Exception as e:
            self.log.error('The counting went wrong, killing the counter.')
            self.stopCount()
            self.sigCountContinuousNext.emit()
            raise e

        # remember the new count data in circular array
        self.countdata[0] = np.average(self.rawdata[0])
        # move the array to the left to make space for the new data
        self.countdata = np.roll(self.countdata, -1)
        # also move the smoothing array
        self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
        # calculate the median and save it
        self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])

        # It is robust to check whether the photon_source2 even exists first.
        if hasattr(self._counting_device, '_photon_source2'):
            if self._counting_device._photon_source2 is not None:
                self.countdata2[0] = np.average(self.rawdata[1])
                # move the array to the left to make space for the new data
                self.countdata2 = np.roll(self.countdata2, -1)
                # also move the smoothing array
                self.countdata_smoothed2 = np.roll(self.countdata_smoothed2, -1)
                # calculate the median and save it
                self.countdata_smoothed2[-int(self._smooth_window_length/2)-1:] = np.median(self.countdata2[-self._smooth_window_length:])

        # save the data if necessary
        if self._saving:
             # if oversampling is necessary
            if self._counting_samples > 1:
                if self._counting_device._photon_source2 is not None:
                    self._sampling_data = np.empty([self._counting_samples, 3])
                    self._sampling_data[:, 0] = time.time() - self._saving_start_time
                    self._sampling_data[:, 1] = self.rawdata[0]
                    self._sampling_data[:, 2] = self.rawdata[1]
                else:
                    self._sampling_data = np.empty([self._counting_samples, 2])
                    self._sampling_data[:, 0] = time.time() - self._saving_start_time
                    self._sampling_data[:, 1] = self.rawdata[0]

                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                if self._counting_device._photon_source2 is not None:
                    self._data_to_save.append(np.array(
                                                       (time.time() - self._saving_start_time,
                                                        self.countdata[-1],
                                                        self.countdata2[-1])
                                                        ))
                else:
                    self._data_to_save.append(
                        np.array(
                            (time.time() - self._saving_start_time,
                             self.countdata[-1]
                             )))
        # call this again from event loop
        self.sigCounterUpdated.emit()
        self.sigCountContinuousNext.emit()


    def countLoopBody_gated(self):
        """ This method gets the count data from the hardware for the gated
        counting mode.

        It runs repeatedly in the logic module event loop by being connected
        to sigCountGatedNext and emitting sigCountGatedNext through a queued
        connection.
        """

        # check for aborts of the thread in break if necessary
        if self.stopRequested:
            with self.threadlock:
                try:
                    # close off the actual counter
                    self._counting_device.close_counter()#gated
                    self._counting_device.close_clock()#gated
                except Exception as e:
                    self.log.error('Could not even close the hardware, '
                            'giving up.')
                    raise e
                finally:
                    # switch the state variable off again
                    self.unlock()
                    self.stopRequested = False
                    self.sigCounterUpdated.emit()
                    return

        try:
            # read the current counter value
            self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)#gated

        except Exception as e:
            self.log.error('The counting went wrong, killing the counter.')
            self.stopCount()
            self.sigCountContinuousNext.emit()
            raise e

        # remember the new count data in circular array
        self.countdata[0] = np.average(self.rawdata[0])
        # move the array to the left to make space for the new data
        self.countdata=np.roll(self.countdata, -1)
        # also move the smoothing array
        self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
        # calculate the median and save it
        self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])

        # save the data if necessary
        if self._saving:
             # if oversampling is necessary
            if self._counting_samples > 1:
                self._sampling_data=np.empty((self._counting_samples,2))
                self._sampling_data[:, 0] = time.time()-self._saving_start_time
                self._sampling_data[:, 1] = self.rawdata[0]
                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                self._data_to_save.append(np.array((time.time()-self._saving_start_time, self.countdata[-1])))
        # call this again from event loop
        self.sigCounterUpdated.emit()
        self.sigCountGatedNext.emit()



    def countLoopBody_finite_gated(self):
        """ This method gets the count data from the hardware for the finite
        gated counting mode.

        It runs repeatedly in the logic module event loop by being connected
        to sigCountFiniteGatedNext and emitting sigCountFiniteGatedNext through
        a queued connection.
        """

        # check for aborts of the thread in break if necessary
        if self.stopRequested:
            with self.threadlock:
                try:
                    # close off the actual counter
                    self._counting_device.close_counter()
                    self._counting_device.close_clock()
                except Exception as e:
                    self.log.exception('Could not even close the '
                            'hardware, giving up.')
                    raise e
                finally:
                    # switch the state variable off again
                    self.unlock()
                    self.stopRequested = False
                    self.sigCounterUpdated.emit()
                    self.sigGatedCounterFinished.emit()
                    return
        try:
            # read the current counter value

            self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)

        except Exception as e:
            self.log.error('The counting went wrong, killing the counter.')
            self.stopCount()
            self.sigCountFiniteGatedNext.emit()
            raise e


        if self._already_counted_samples+len(self.rawdata[0]) >= len(self.countdata):

            needed_counts = len(self.countdata) - self._already_counted_samples
            self.countdata[0:needed_counts] = self.rawdata[0][0:needed_counts]
            self.countdata=np.roll(self.countdata, -needed_counts)

            self._already_counted_samples = 0
            self.stopRequested = True

        else:
            #self.log.debug(('len(self.rawdata[0]):', len(self.rawdata[0])))
            #self.log.debug(('self._already_counted_samples', self._already_counted_samples))

            # replace the first part of the array with the new data:
            self.countdata[0:len(self.rawdata[0])] = self.rawdata[0]
            # roll the array by the amount of data it had been inserted:
            self.countdata=np.roll(self.countdata, -len(self.rawdata[0]))
            # increment the index counter:
            self._already_counted_samples += len(self.rawdata[0])
            # self.log.debug(('already_counted_samples:',self._already_counted_samples))

        # remember the new count data in circular array
        # self.countdata[0:len(self.rawdata)] = np.average(self.rawdata[0])
        # move the array to the left to make space for the new data
        # self.countdata=np.roll(self.countdata, -1)
        # also move the smoothing array
        # self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
        # calculate the median and save it
        # self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])

        # in this case, saving should happen afterwards, therefore comment out:
        # # save the data if necessary
        # if self._saving:
        #      # if oversampling is necessary
        #     if self._counting_samples > 1:
        #         self._sampling_data=np.empty((self._counting_samples,2))
        #         self._sampling_data[:, 0] = time.time()-self._saving_start_time
        #         self._sampling_data[:, 1] = self.rawdata[0]
        #         self._data_to_save.extend(list(self._sampling_data))
        #     # if we don't want to use oversampling
        #     else:
        #         # append tuple to data stream (timestamp, average counts)
        #         self._data_to_save.append(np.array((time.time()-self._saving_start_time, self.countdata[-1])))
        # # call this again from event loop

        self.sigCounterUpdated.emit()
        self.sigCountFiniteGatedNext.emit()

    def save_current_count_trace(self, name_tag=''):
        """ The current displayed counttrace will be saved.

        @param str name_tag: optional, personal description that will be
                             appended to the file name

        This method saves the already displayed counts to file and does not
        accumulate them. The counttrace variable will be saved to file with the
        provided name!
        """

        # If there is a postfix then add separating underscore
        if name_tag == '':
            filelabel = 'snapshot_count_trace'
        else:
            filelabel = 'snapshot_count_trace_'+name_tag

        stop_time = self._count_length/self._count_frequency
        time_step_size = stop_time/len(self.countdata)
        x_axis = np.arange(0, stop_time, time_step_size)

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        if hasattr(self._counting_device, '_photon_source2'):
            # if self._counting_device._photon_source2 is None:
            data['Time (s),Signal 1 (counts/s),Signal 2 (counts/s)'] = np.array((x_axis, self.countdata, self.countdata2)).transpose()
        else:
            data['Time (s),Signal (counts/s)'] = np.array((x_axis, self.countdata)).transpose()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Saved at time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
                                                        time.localtime(time.time()))

        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        filepath = self._save_logic.get_path_for_module(module_name='Counter')
        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, as_text=True)

        #, as_xml=False, precision=None, delimiter=None)
        self.log.debug('Current Counter Trace saved to:\n'
                    '{0}'.format(filepath))




