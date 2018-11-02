# -*- coding: utf-8 -*-
"""
This file contains the Qudi powermeter logic class.

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

from core.util.mutex import Mutex


class PowermeterLogic(GenericLogic):
    """ This logic module gathers data from a hardware measuring device.

    @signal sigPowermeterUpdate: there is new measuring data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???

    @return error: 0 is OK, -1 is error
    """
    sigPowermeterUpdated = QtCore.Signal()

    sigCountDataNext = QtCore.Signal()

    sigGatedPowermeterFinished = QtCore.Signal()
    sigGatedPowermeterContinue = QtCore.Signal(bool)
    sigMeasuringSamplesChanged = QtCore.Signal(int)
    sigCountLengthChanged = QtCore.Signal(int)
    sigSavingStatusChanged = QtCore.Signal(bool)
    sigCountStatusChanged = QtCore.Signal(bool)


    _modclass = 'PowermeterLogic'
    _modtype = 'logic'

    ## declare connectors
    powermeter1 = Connector(interface='PowermeterInterface')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _count_length = StatusVar('count_length', 300)
    #_measuring_samples = StatusVar('measuring_samples', 1)
    _count_frequency = StatusVar('count_frequency', 4)
    _saving = StatusVar('saving', False)


    def __init__(self, config, **kwargs):
        """ Create PowermeterLogic object with connectors.

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
        #self._measuring_samples = 1      # oversampling
        # in hertz
        self._count_frequency = 4

        # self._binned_measuring = True  # UNUSED?
        #self._measuring_mode = MeasuringMode['CONTINUOUS']

        self._saving = False
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Connect to hardware and save logic
        self._measuring_device = self.powermeter1()
        self._save_logic = self.savelogic()

        # Recall saved app-parameters
        #if 'measuring_mode' in self._statusVariables:
        #    self._measuring_mode = MeasuringMode[self._statusVariables['measuring_mode']]

        # initialize data arrays
        self.powerdata = np.zeros(self._count_length)
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

        # Stop measurement
        if self.module_state() == 'locked':
            self._stopCount_wait()

        self.sigCountDataNext.disconnect()
        return


    def set_count_length(self, length=300):
        """ Sets the time trace in units of bins.

        @param int length: time trace in units of bins (positive int).

        @return int: length of time trace in units of bins

        This makes sure, the powermeter is stopped first and restarted afterwards.
        """
        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if length > 0:
            self._stopCount_wait()
            self._count_length = int(length)
            # if the powermeter was running, restart it
            if restart:
                self.startCount()
        else:
            self.log.warning('count_length has to be larger than 0! Command ignored!')
        self.sigCountLengthChanged.emit(self._count_length)
        return self._count_length

    def get_count_length(self):
        """ Returns the currently set length of the measuring array.

        @return int: count_length
        """
        return self._count_length

    def get_saving_state(self):
        """ Returns if the data is saved in the moment.

        @return bool: saving state
        """
        return self._saving

    def start_saving(self, resume=False):
        """
        Sets up start-time and initializes data array, if not resuming, and changes saving state.
        If the powermeter is not running it will be started in order to have data to save.

        @return bool: saving state
        """
        if not resume:
            self._data_to_save = []
            self._saving_start_time = time.time()

        self._saving = True

        # If the powermeter is not running, then it should start running so there is data to save
        if self.module_state() != 'locked':
            self.startCount()

        self.sigSavingStatusChanged.emit(self._saving)
        return self._saving

    def save_data(self, to_file=True, postfix=''):
        """ Save the powermeter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save

        @return dict parameters: Dictionary which contains the saving parameters
        """
        # stop saving thus saving state has to be set to False
        self._saving = False
        self._saving_stop_time = time.time()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start measuring time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop measuring time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
        parameters['Count frequency (Hz)'] = self._count_frequency


        if to_file:
            # If there is a postfix then add separating underscore
            if postfix == '':
                filelabel = 'count_trace'
            else:
                filelabel = 'count_trace_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            header = 'Time (s)  Power(W)'

            data = {header: self._data_to_save}
            filepath = self._save_logic.get_path_for_module(module_name='Powermeter')

            fig = self.draw_figure(data=np.array(self._data_to_save))
            self._save_logic.save_data(data, filepath=filepath, parameters=parameters,
                                       filelabel=filelabel, plotfig=fig, delimiter='\t')
            self.log.info('Powermeter Data saved to:\n{0}'.format(filepath))

        self.sigSavingStatusChanged.emit(self._saving)
        return self._data_to_save, parameters

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        power_data = data[:, 1]
        time_data = data[:, 0]

        # Scale count values using SI prefix

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots()
        ax.plot(time_data, power_data, linestyle=':', linewidth=0.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Power (W)')
        return fig


    # FIXME: Not implemented for self._measuring_mode == 'gated'

    def startCount(self):
      
        # Sanity checks


        with self.threadlock:
            # Lock module
            if self.module_state() != 'locked':
                self.module_state.lock()
            else:
                self.log.warning('Powermeter already running. Method call ignored.')
                return 0

            # # Set up clock
            # clock_status = self._measuring_device.set_up_clock(clock_frequency=self._count_frequency)
            # if clock_status < 0:
            #     self.module_state.unlock()
            #     self.sigCountStatusChanged.emit(False)
            #     return -1

            # # Set up powermeter
            # if self._measuring_mode == MeasuringMode['FINITE_GATED']:
            #     powermeter_status = self._measuring_device.set_up_powermeter(powermeter_buffer=self._count_length)
            # # elif self._measuring_mode == MeasuringMode['GATED']:
            # #
            # else:
            #     powermeter_status = self._measuring_device.set_up_powermeter()
            # if powermeter_status < 0:
            #     self._measuring_device.close_clock()
            #     self.module_state.unlock()
            #     self.sigCountStatusChanged.emit(False)
            #     return -1

            # # initialising the data arrays
            # self.rawdata = np.zeros([len(self.get_channels()), self._measuring_samples])
            # self.countdata = np.zeros([len(self.get_channels()), self._count_length])
            # self.countdata_smoothed = np.zeros([len(self.get_channels()), self._count_length])
            # self._sampling_data = np.empty([len(self.get_channels()), self._measuring_samples])
            #
            # # the sample index for gated measuring
            # self._already_counted_samples = 0

            # Start data reader loop
            self.sigCountStatusChanged.emit(True)
            self.sigCountDataNext.emit()
            return

    def stopCount(self):
        """ Set a flag to request stopping measuring.
        """
        if self.module_state() == 'locked':
            with self.threadlock:
                self.stopRequested = True
        return

    def count_loop_body(self):
        """ This method gets the count data from the hardware for the continuous measuring mode (default).

        It runs repeatedly in the logic module event loop by being connected
        to sigCountContinuousNext and emitting sigCountContinuousNext through a queued connection.
        """
        if self.module_state() == 'locked':
            with self.threadlock:
                # check for aborts of the thread in break if necessary
                if self.stopRequested:
                    # close off the actual powermeter
                    self._measuring_device.disconnect()
                    # switch the state variable off again
                    self.stopRequested = False
                    self.module_state.unlock()
                    self.sigPowermeterUpdated.emit()
                    return

                # read the current powermeter value
                self.powerdata.append(self._measuring_device.get_power())

            # call this again from event loop
            self.sigPowermeterUpdated.emit()
            self.sigCountDataNext.emit()
        return


    def _stopCount_wait(self, timeout=5.0):
        """
        Stops the powermeter and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        self.stopCount()
        start_time = time.time()
        while self.module_state() == 'locked':
            time.sleep(0.1)
            if time.time() - start_time >= timeout:
                self.log.error('Stopping the powermeter timed out after {0}s'.format(timeout))
                return -1
        return 0
