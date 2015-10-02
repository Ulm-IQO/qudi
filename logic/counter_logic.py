# -*- coding: utf-8 -*-
"""
This file contains the QuDi couner logic class.

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

Copyright (C) 2015 Kay D. Jahnke
Copyright (C) 2015 Alexander Stark
Copyright (C) 2015 Jan M. Binder
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime

class CounterLogic(GenericLogic):
    """This logic module gathers data from a hardware counting device.
      @signal sigCounterUpdate: there is new counting data available
      @signal sigCountContinuousNext: used to simulate a loop in which the data acquisition runs.
    """
    sigCounterUpdated = QtCore.Signal()
    sigCountContinuousNext = QtCore.Signal()
    sigCountGatedNext = QtCore.Signal()

    _modclass = 'counterlogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'counter1': 'SlowCounterInterface',
            'savelogic': 'SaveLogic'
            }
    _out = {'counterlogic': 'CounterLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create CounterLogic object with connectors.

          @param object manager: Manager object thath loaded this module
          @param str name: unique module name
          @param dict config: module configuration
          @param dict kwargs: optional parameters
        """
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        self._count_length = 300
        self._count_frequency = 50
        self._counting_samples = 1
        self._smooth_window_length = 10
        self._binned_counting = True

        self._counting_mode = 'continuous'


    def activation(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """
        self.countdata = np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        self.rawdata=np.zeros((self._counting_samples,))

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

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
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
            self._data_to_save=[]
            self._saving_start_time=time.time()
        self._saving=True

        # If the counter is not running, then it should start running so there is data to save
        if self.isstate('idle'):
            self.startCount()

        return 0

    def save_data(self, save=True, postfix=''):
        """ Save the counter trace data and writes it to a file.

        @return int: error code (0:OK, -1:error)
        """
        self._saving=False
        self._saving_stop_time=time.time()

        if save:
            filepath = self._save_logic.get_path_for_module(module_name='Counter')
            datetime
            filelabel = 'count_trace'+postfix

            # prepare the data in a dict or in an OrderedDict:
            data = OrderedDict()
            data = {'Time (s),Signal (counts/s)':self._data_to_save}

            # write the parameters:
            parameters = OrderedDict()
            parameters['Start counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
            parameters['Stop counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
            parameters['Count frequency (Hz)'] = self._count_frequency
            parameters['Oversampling (Samples)'] = self._counting_samples
            parameters['Smooth Window Length (# of events)'] = self._smooth_window_length

            self._save_logic.save_data(data, filepath, parameters=parameters,
                                       filelabel=filelabel, as_text=True)#, as_xml=False, precision=None, delimiter=None)

            self.logMsg('Counter Trace saved to:\n{0}'.format(filepath),
                        msgType='status', importance=3)

        return 0

    def set_counting_mode(self, mode='continuous'):
        """Set the counting mode, to change between continuous and gated counting.
        Possible options are:
        'continuous'
        'gated'
        """

        self._counting_mode = mode

    def startCount(self):
        """This is called externally, and is basically a wrapper that redirects to the chosen counting mode start function.
        """
        if self._counting_mode == 'continuous':
            self._startCount_continuous()
        elif self._counting_mode == 'gated':
            self._startCount_gated()
        else:
            self.logMsg('Unknown counting mode, can not start the counter.', msgType='error')

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
        self.countdata=np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        self.rawdata=np.zeros((self._counting_samples,))
        self._sampling_data=np.empty((self._counting_samples,2))

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
                    self.logMsg('Could not even close the hardware, giving up.', msgType='error')
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
            self.logMsg('The counting went wrong, killing the counter.', msgType='error')
            self.stopCount()
            self.sigCountContinuousNext.emit()
            raise e

        # remember the new count data in circular array
        self.countdata[0] = np.average(self.rawdata)
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
                self._sampling_data[:,0]=time.time()-self._saving_start_time
                self._sampling_data[:,1]=self.rawdata
                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                self._data_to_save.append(np.array((time.time()-self._saving_start_time, self.countdata[-1])))
        # call this again from event loop
        self.sigCounterUpdated.emit()
        self.sigCountContinuousNext.emit()


    def countLoopBody_gated(self):
        """ This method gets the count data from the hardware for the gated counting mode.

        It runs repeatedly in the logic module event loop by being connected
        to sigCountGatedNext and emitting sigCountGatedNext through a queued connection.
        """

        # check for aborts of the thread in break if necessary
        if self.stopRequested:
            with self.threadlock:
                try:
                    # close off the actual counter
                    self._counting_device.close_counter()#gated
                    self._counting_device.close_clock()#gated
                except Exception as e:
                    self.logMsg('Could not even close the hardware, giving up.', msgType='error')
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
            self.logMsg('The counting went wrong, killing the counter.', msgType='error')
            self.stopCount()
            self.sigCountContinuousNext.emit()
            raise e

        # remember the new count data in circular array
        self.countdata[0] = np.average(self.rawdata)
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
                self._sampling_data[:,0]=time.time()-self._saving_start_time
                self._sampling_data[:,1]=self.rawdata
                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                self._data_to_save.append(np.array((time.time()-self._saving_start_time, self.countdata[-1])))
        # call this again from event loop
        self.sigCounterUpdated.emit()
        self.sigCountGatedNext.emit()
