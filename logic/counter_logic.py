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

from logic.generic_logic import GenericLogic
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
            self.log.info('{0}: {1}'.format(key,config[key]))

        # in bins
        self._count_length = 300
        # in hertz
        self._count_frequency = 50
        # oversampling in bins
        self._counting_samples = 1
        # in bins
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
        # Connect to hardware and save logic
        self._counting_device = self.get_in_connector('counter1')
        self._save_logic = self.get_in_connector('savelogic')

        constraints = self.get_hardware_constraints()
        number_of_detectors = constraints['#detectors']

        self.countdata = np.zeros(
            (len(self.get_channels()), self._count_length))
        self.countdata_smoothed = np.zeros(
            (len(self.get_channels()), self._count_length))
        self.rawdata = np.zeros(
            (len(self.get_channels()), self._counting_samples))

        self.running = False
        self.stopRequested = False
        self._saving = False
        self._data_to_save=[]
        self._saving_start_time = time.time()

        # connect signals
        # FIXME: Is it really necessary to have three different Signals? They are doing almost the same
        # for continuous counting:
        self.sigCountContinuousNext.connect(
            self.countLoopBody_continuous,
            QtCore.Qt.QueuedConnection)
        # for gated counting:
        self.sigCountGatedNext.connect(
            self.countLoopBody_gated,
            QtCore.Qt.QueuedConnection)
        # for finite gated counting:
        self.sigCountFiniteGatedNext.connect(
            self.countLoopBody_finite_gated,
            QtCore.Qt.QueuedConnection)

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.stopCount()
        for attempt in range(20):
            if self.getState() == 'idle':
                break
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.1)
        else:
            self.log.error('Stopped deactivate counter after trying for 2 seconds!')

    def get_hardware_constraints(self):
        """ Retrieve the hardware constrains from the counter device.

        @return dict: dict with constraints for the counter
        """
        return self._counting_device.get_constraints()

    def set_counting_samples(self, samples=1):
        """ Sets the oversampling in units of bins.

        @param int samples: oversampling in units of bins (positive int ).

        @return int: oversampling in units of bins.

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        if samples > 0:
            restart = self.stop_counter()
            self._counting_samples = int(samples)
            # if the counter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('counting_samples has to be larger than 0! Command ignored!')
        return self._counting_samples

    def set_count_length(self, length=300):
        """ Sets the time trace in units of bins.

        @param int length: time trace in units of bins (positive int).

        @return int: length of time trace in units of bins

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        if length > 0:
            restart = self.stop_counter()
            self._count_length = int(length)
            # if the counter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('count_length has to be larger than 0! Command ignored!')
        return self._count_length

    def set_count_frequency(self, frequency=50.0):
        """ Sets the frequency with which the data is acquired.

        @param float frequency: the desired frequency of counting in Hz

        @return float: the actual frequency of counting in Hz

        This makes sure, the counter is stopped first and restarted afterwards.
        """
        constraints = self.get_hardware_constraints()
        if constraints['min_count_frequency'] <= frequency <= constraints['max_count_frequency']:
            restart = self.stop_counter()
            self._count_frequency = frequency
            # if the counter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('count_frequency not in range! Command ignored!')
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
        """ Sets up start-time and initializes data array, if not resuming, and changes saving state
        If the counter is not running it will be started in order to have data to save

        @return bool: saving state
        """
        if not resume:
            self._data_to_save = []
            self._saving_start_time = time.time()
        self._saving = True

        # If the counter is not running, then it should start running so there is data to save
        if self.isstate('idle'):
            self.startCount()
        return self._saving

    def save_data(self, to_file=True, postfix=''):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save

        @return dict parameters: Dictionary which contains the saving parameters
        """
        # stop saving thus saving state has to be set to False
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
                filelabel = 'count_trace_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            data = OrderedDict()
            header = 'Time (s)'
            for i, detector in enumerate(self.get_channels()):
                header = header + ',Signal{0} (counts/s)'.format(i)

            data = {header: self._data_to_save}
            filepath = self._save_logic.get_path_for_module(module_name='Counter')
            fig = self.draw_figure(data=np.array(self._data_to_save))
            self._save_logic.save_data(
                data,
                filepath,
                parameters=parameters,
                filelabel=filelabel,
                as_text=True,
                plotfig=fig
                )

            plt.close(fig)
            self.log.info('Counter Trace saved to:\n{0}'.format(filepath))

        return self._data_to_save, parameters

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        # TODO: Draw plot for second APD if it is connected
        # TODO: One plot for all apds or for every APD one plot?

        count_data = data[:, 1]
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

    def set_counting_mode(self, mode='continuous'):
        """Set the counting mode, to change between continuous and gated counting.
        Possible options are:
            'continuous'    = counts continuously
            'gated'         = bins the counts according to a gate signal
            'finite-gated'  = finite measurement with predefined number of samples

        @return str: counting mode
        """
        constraints = self.get_hardware_constraints()

        if mode in constraints['counting_mode']:
            self._counting_mode = mode
            self.log.debug(self._counting_mode)
        else:
            self.log.warning('Counting mode not supported from hardware. Command ignored!')
        return self._counting_mode

    def get_counting_mode(self):
        """ Retrieve the current counting mode.

        @return str: one of the possible counting options:
                'continuous'    = counts continuously
                'gated'         = bins the counts according to a gate signal
                'finite-gated'  = finite measurement with predefined number of samples
        """
        return self._counting_mode

    # FIXME: Is it really necessary to have 3 different methods here?
    def startCount(self):
        """ This is called externally, and is basically a wrapper that
            redirects to the chosen counting mode start function.

            @return error: 0 is OK, -1 is error
        """

        if self._counting_mode == 'continuous':
            return self._startCount_continuous()
        elif self._counting_mode == 'gated':
            return self._startCount_gated()
        elif self._counting_mode == 'finite-gated':
            return self._startCount_finite_gated()
        else:
            self.log.error('Unknown counting mode, cannot start the counter.')
            return -1

    def _startCount_continuous(self):
        """Prepare to start counting change state and start counting 'loop'.

        @return error: 0 is OK, -1 is error
        """
        # setting up the counter
        # set a lock, to signify the measurment is running
        self.lock()

        clock_status = self._counting_device.set_up_clock(clock_frequency = self._count_frequency)
        if clock_status < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return -1

        counter_status = self._counting_device.set_up_counter()
        if counter_status < 0:
            self._counting_device.close_clock()
            self.unlock()
            self.sigCounterUpdated.emit()
            return -1

        # initialising the data arrays
        self.rawdata = np.zeros(
            (len(self.get_channels()), self._counting_samples))
        self.countdata = np.zeros(
            (len(self.get_channels()), self._count_length))
        self.countdata_smoothed = np.zeros(
            (len(self.get_channels()), self._count_length))
        self._sampling_data = np.empty(
            (len(self.get_channels()), self._counting_samples))

        self.sigCountContinuousNext.emit()

    #FIXME: To Do!
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

        @return error: 0 is OK, -1 is error

        Change state and start counting 'loop'.
        """

        # setting up the counter
        # set a lock, to signify the measurment is running
        self.lock()

        returnvalue = self._counting_device.set_up_clock(clock_frequency = self._count_frequency)
        if returnvalue < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return -1

        returnvalue = self._counting_device.set_up_counter(counter_buffer=self._count_length)
        if returnvalue < 0:
            self.unlock()
            self.sigCounterUpdated.emit()
            return -1

        # initialising the data arrays

        # in rawdata the 'fresh counts' are read in
        self.rawdata = np.zeros(
            (len(self.get_channels()), self._counting_samples))
        # countdata contains the appended data, that is the total displayed counttrace
        self.countdata = np.zeros(
            (len(self.get_channels()), self._count_length))

        # the index
        self._already_counted_samples = 0
        self.sigCountFiniteGatedNext.emit()
        return 0

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
                    self.log.exception('Could not even close the hardware, giving up.')
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
            self.countdata_smoothed[i, window:] = np.median(self.countdata[i, -self._smooth_window_length:])

        # save the data if necessary
        if self._saving:
             # if oversampling is necessary
            if self._counting_samples > 1:
                chans = self.get_channels()
                self._sampling_data = np.empty((len(chans) + 1, self._counting_samples))
                self._sampling_data[0, :] = time.time() - self._saving_start_time
                for i, ch in enumerate(chans):
                    self._sampling_data[i+1, 0] = self.rawdata[i]

                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                chans = self._counting_device.get_counter_channels()
                newdata =  np.empty((len(chans) + 1, ))
                newdata[0] = time.time() - self._saving_start_time
                for i, ch in enumerate(chans):
                    newdata[i+1] = self.countdata[-1]

                self._data_to_save.append(newdata)

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
                    self._counting_device.close_counter()  # gated
                    self._counting_device.close_clock()  # gated
                except Exception as e:
                    self.log.error('Could not even close the hardware, giving up.')
                    raise e
                finally:
                    # switch the state variable off again
                    self.unlock()
                    self.stopRequested = False
                    self.sigCounterUpdated.emit()
                    return

        try:
            # read the current counter value
            self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)  # gated

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
        self.countdata_smoothed[-int(self._smooth_window_length/2)-1:] = np.median(self.countdata[-self._smooth_window_length:])

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

        except:
            self.log.error('The counting went wrong, killing the counter.')
            self.stopCount()
            self.sigCountFiniteGatedNext.emit()

        if self._already_counted_samples+len(self.rawdata[0]) >= len(self.countdata):

            needed_counts = len(self.countdata) - self._already_counted_samples
            self.countdata[0:needed_counts] = self.rawdata[0][0:needed_counts]
            self.countdata=np.roll(self.countdata, -needed_counts)

            self._already_counted_samples = 0
            self.stopRequested = True

        else:
            # replace the first part of the array with the new data:
            self.countdata[0:len(self.rawdata[0])] = self.rawdata[0]
            # roll the array by the amount of data it had been inserted:
            self.countdata=np.roll(self.countdata, -len(self.rawdata[0]))
            # increment the index counter:
            self._already_counted_samples += len(self.rawdata[0])
            # self.log.debug(('already_counted_samples:',self._already_counted_samples))

        self.sigCounterUpdated.emit()
        self.sigCountFiniteGatedNext.emit()

    def save_current_count_trace(self, name_tag=''):
        """ The currently displayed count trace will be saved.

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
        parameters['Saved at time (s)'] = timestr

        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

        filepath = self._save_logic.get_path_for_module(module_name='Counter')
        self._save_logic.save_data(
            data,
            filepath,
            parameters=parameters,
            filelabel=filelabel,
            as_text=True)

        self.log.debug('Current Counter Trace saved to: {0}'.format(filepath))
        return data, filepath, parameters, filelabel

    def get_channels(self):
        """ Shortcut for hardware get_counter_channels.

            @return list(str): return list of active counter channel names
        """
        return self._counting_device.get_counter_channels()

