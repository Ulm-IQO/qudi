# -*- coding: utf-8 -*-

"""
This file contains the logic responsible for coordinating laser scanning.

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
Copyright (C) 2015 Lachlan J. Rogers lachlan.rogers@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime

class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    def __init__(self, parentclass):
        super().__init__()

        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass


    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start the timer.

        @param bool state: (True) starts timer, (False) stops it.
        """

        if state_change:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self._update_data)
            self.timer.start(self._parentclass._logic_acquisition_timing)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _update_data(self):
        """ This method gets the count data from the hardware.
            It runs repeatedly in the logic module event loop by being connected
            to sigCountNext and emitting sigCountNext through a queued connection.
        """

        self._parentclass.current_wavelength = 1.0*self._parentclass._wavemeter_device.get_current_wavelength()
        time_stamp = time.time()-self._parentclass._acqusition_start_time

        # only wavelength >200 nm make sense, ignore the rest
        if self._parentclass.current_wavelength>200:
            self._parentclass._wavelength_data.append(np.array([time_stamp,self._parentclass.current_wavelength]))

        # check if we have a new min or max and save it if so
        if self._parentclass.current_wavelength > self._parentclass.intern_xmax:
            self._parentclass.intern_xmax=self._parentclass.current_wavelength
        if self._parentclass.current_wavelength < self._parentclass.intern_xmin:
            self._parentclass.intern_xmin=self._parentclass.current_wavelength

        if ( not self._parentclass._counter_logic.get_saving_state() ) or self._parentclass._counter_logic.getState() == 'idle':
            self._parentclass.stop_scanning()

class LaserScanningLogic(GenericLogic):
    """This logic module gathers data from wavemeter and the counter logic.
    """

    sig_data_updated = QtCore.Signal()
    sig_update_histogram_next = QtCore.Signal(bool)
    sig_handle_timer = QtCore.Signal(bool)
    sig_new_data_point = QtCore.Signal(list)

    _modclass = 'laserscanninglogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'wavemeter1': 'WavemeterInterface',
            'savelogic': 'SaveLogic',
            'counterlogic': 'CounterLogic'
            }
    _out = {'laserscanninglogic': 'LaserScanningLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create LaserScanningLogic object with connectors.

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

        if 'logic_acquisition_timing' in config.keys():
            self._logic_acquisition_timing = config['logic_acquisition_timing']
        else:
            self._logic_acquisition_timing = 20.
            self.logMsg('No logic_acquisition_timing configured, '
                        'using {} instead.'.format(self._logic_acquisition_timing),
                        msgType='warning')

        if 'logic_update_timing' in config.keys():
            self._logic_update_timing = config['logic_update_timing']
        else:
            self._logic_update_timing = 100.
            self.logMsg('No logic_update_timing configured, '
                        'using {} instead.'.format(self._logic_update_timing),
                        msgType='warning')

        self._acqusition_start_time = 0
        self._bins = 200
        self._data_index = 0
        self._xmin = 650
        self._xmax = 750
        # internal min and max wavelength determined by the measured wavelength
        self.intern_xmax = -1.0
        self.intern_xmin = 1.0e10
        self.current_wavelength = 0


    def activation(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """
        self._wavelength_data = []

        self.stopRequested = False

        self._wavemeter_device = self.connector['in']['wavemeter1']['object']
#        print("Counting device is", self._counting_device)

        self._save_logic = self.connector['in']['savelogic']['object']
        self._counter_logic = self.connector['in']['counterlogic']['object']

        # create a new x axis from xmin to xmax with bins points
        self.histogram_axis=np.arange(self._xmin, self._xmax, (self._xmax-self._xmin)/self._bins)
        self.histogram = np.zeros(self.histogram_axis.shape)
        self.envelope_histogram = np.zeros(self.histogram_axis.shape)

        self.sig_update_histogram_next.connect(self._update_histogram, QtCore.Qt.QueuedConnection)

        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)

        # start the event loop for the hardware
        self.hardware_thread.start()
        self.last_point_time = time.time()

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
        if self.getState() != 'idle' and self.getState() != 'deactivated':
            self.stop_scanning()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()


    def get_max_wavelength(self):
        return self._xmax

    def get_min_wavelength(self):
        return self._xmin

    def get_bins(self):
        return self._bins

    def recalculate_histogram(self, bins=None, xmin=None, xmax=None):
        if not bins is None:
            self._bins=bins
        if not xmin is None:
            self._xmin=xmin
        if not xmax is None:
            self._xmax=xmax

#        print('New histogram', self._bins,self._xmin,self._xmax)
        # create a new x axis from xmin to xmax with bins points
        self.rawhisto = np.zeros(self._bins)
        self.envelope_histogram = np.zeros(self._bins)
        self.sumhisto = np.ones(self._bins)*1.0e-10
        self.histogram_axis = np.linspace(self._xmin, self._xmax, self._bins)
        self.sig_update_histogram_next.emit(True)


    def start_scanning(self, resume=False):
        """ Prepare to start counting:
            zero variables, change state and start counting "loop"
        """

        self.run()

        if self._counter_logic.getState() == 'idle':
            self._counter_logic.startCount()

        if self._counter_logic.get_saving_state():
            self._counter_logic.save_data()

        self._wavemeter_device.start_acqusition()

        self._counter_logic.start_saving(resume=resume)

        if not resume:
            self._acqusition_start_time = self._counter_logic._saving_start_time
            self._wavelength_data = []


            self.data_index = 0
            self.rawhisto=np.zeros(self._bins)
            self.sumhisto=np.ones(self._bins)*1.0e-10
            self.intern_xmax = -1.0
            self.intern_xmin = 1.0e10
            self.recent_avg = [0, 0, 0]
            self.recent_count = 0

        # start the measuring thread
        self.sig_handle_timer.emit(True)
        self._complete_histogram = True
        self.sig_update_histogram_next.emit(False)

        return 0

    def stop_scanning(self):
        """ Set a flag to request stopping counting.
        """

        if not self.getState() == 'idle':
            #self._wavemeter_device.stop_acqusition()
            # stop the measurement thread
            self.sig_handle_timer.emit(False)
            # set status to idle again
            self.stop()

        if self._counter_logic.get_saving_state():
            self._counter_logic.save_data(to_file=False)


        return 0

    def _update_histogram(self, complete_histogram):
        if complete_histogram:
            count_window = len(self._counter_logic._data_to_save)
            self._data_index = 0
            self.logMsg(('Recalcutating Laser Scanning Histogram for: '
                         '{0:d} counts and {1:d} wavelength.').format(
                            count_window,
                            len(self._wavelength_data)
                            ),
                        msgType='status'
                        )
        else:
            count_window = min(100, len(self._counter_logic._data_to_save))

        if  count_window < 2:
            time.sleep(self._logic_update_timing*1e-3)
            self.sig_update_histogram_next.emit(False)
            return

        temp = np.array(self._counter_logic._data_to_save[-count_window:])

        # only do something, if there is data to work with
        if len(self._wavelength_data)>0:

            for i in self._wavelength_data[self._data_index:]:
                self._data_index += 1

                if  i[1] < self._xmin or i[1] > self._xmax:
                    continue

                # calculate the bin the new wavelength needs to go in
                newbin=np.digitize([i[1]],self.histogram_axis)[0]
                # if the bin make no sense, start from the beginning
                if  newbin > len(self.rawhisto)-1:
                    continue

                # sum the counts in rawhisto and count the occurence of the bin in sumhisto
                interpolation = np.interp(i[0], xp=temp[:,0], fp=temp[:,1])
                self.rawhisto[newbin] += interpolation
                self.sumhisto[newbin] += 1.0

                self.envelope_histogram[newbin] = np.max([interpolation,self.envelope_histogram[newbin]])

                datapoint = [i[1], i[0], interpolation]
                if time.time() - self.last_point_time > 1:
                    self.sig_new_data_point.emit(self.recent_avg)
                    self.last_point_time = time.time()
                    self.recent_count = 0
                else:
                    self.recent_count += 1
                    for j in range(3):
                        self.recent_avg[j] -= self.recent_avg[j] / self.recent_count
                        self.recent_avg[j] += datapoint[j] / self.recent_count

            # the plot data is the summed counts divided by the occurence of the respective bins
            self.histogram=self.rawhisto/self.sumhisto

        time.sleep(self._logic_update_timing*1e-3)

        self.sig_data_updated.emit()

        if self.getState() == 'running':
            self.sig_update_histogram_next.emit(False)


    def save_data(self):
        """ Save the counter trace data and writes it to a file.

        @return int: error code (0:OK, -1:error)
        """

        self._saving_stop_time=time.time()

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filelabel = 'laser_scan'
        timestamp = datetime.datetime.now()


        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Wavelength (nm), Signal (counts/s)':np.array([self.histogram_axis,self.histogram]).transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bins (#)'] = self._bins
        parameters['Xmin (nm)'] = self._xmin
        parameters['XMax (nm)'] = self._xmax
        parameters['Start Time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._acqusition_start_time))
        parameters['Stop Time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))

        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filelabel = 'laser_scan_wavemeter'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Time (s), Wavelength (nm)':self._wavelength_data}
        # write the parameters:
        parameters = OrderedDict()
        parameters['Acquisition Timing (ms)'] = self._logic_acquisition_timing
        parameters['Start Time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._acqusition_start_time))
        parameters['Stop Time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))

        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filelabel = 'laser_scan_counts'


        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Time (s),Signal (counts/s)':self._counter_logic._data_to_save}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._counter_logic._saving_start_time))
        parameters['Stop counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
        parameters['Length of counter window (# of events)'] = self._counter_logic._count_length
        parameters['Count frequency (Hz)'] = self._counter_logic._count_frequency
        parameters['Oversampling (Samples)'] = self._counter_logic._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._counter_logic._smooth_window_length

        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)


        self.logMsg('Laser Scan saved to:\n{0}'.format(filepath),
                    msgType='status', importance=3)

        return 0
