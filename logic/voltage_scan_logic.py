# -*- coding: utf-8 -*-
"""
This file contains a QuDi logic module for controlling scans of the
fourth analogue output channel.  It was originally written for
scanning laser frequency, but it can be used to control any parameter
in the experiment that is voltage controlled.  The hardware
range is typically -10 to +10 V.

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
Copyright (C) 2015 Jan M. Binder
Copyright (C) 2016 Lachlan J. Rogers
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime


class VoltageScanningLogic(GenericLogic):
    """This logic module controls scans of DC voltage on the fourth analogue
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """

    sig_data_updated = QtCore.Signal()

    _modclass = 'voltagescanninglogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'confocalscanner1': 'ConfocalScannerInterface',
            'savelogic': 'SaveLogic',
            }
    _out = {'voltagescanninglogic': 'VoltageScanningLogic'}

    signal_change_voltage = QtCore.Signal()
    signal_scan_next_line = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        """ Create VoltageScanningLogic object with connectors.

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

        self.stopRequested = False

    def activation(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        #default values for clock frequency and slowness
        #slowness: steps during retrace line
        self._clock_frequency = 1000.
        self.return_slowness = 50

        # Reads in the maximal scanning range. The unit of that scan range is
        # micrometer!
        self.a_range = self._scanning_device.get_position_range()[3]

        # Initialise the current position of all four scanner channels.
        self.current_position = self._scanning_device.get_scanner_position()

        # initialise the range for scanning
        self.scan_range = [self.a_range[0]/10, self.a_range[1]/10]

        # Sets the current position to the center of the maximal scanning range
        self._current_a = (self.a_range[0] + self.a_range[1]) / 2.

        # Sets connections between signals and functions
        self.signal_change_voltage.connect(self._change_voltage, QtCore.Qt.QueuedConnection)
        self.signal_scan_next_line.connect(self._do_next_line, QtCore.Qt.QueuedConnection)

        # Initialization of internal counter for scanning
        self._scan_counter = 0

        # Keep track of scan direction
        self.upwards_scan = True



        #############################
        # Configurable parameters

        self.number_of_repeats = 10

        # TODO: allow configuration with respect to measurement duration
        self.acquire_time = 20  # seconds

        ##############################

        # Initialie data matrix
        self._initialise_data_matrix()


    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
        pass

    def set_voltage(self, a = None):
        """Forwarding the desired output voltage to the scanning device.

        @param string tag: TODO

        @param float a: if defined, changes to postion in a-direction (microns)

        @return int: error code (0:OK, -1:error)
        """
        # print(tag, x, y, z)
        # Changes the respective value
        if a != None:
            self._current_a = a

        #Checks if the scanner is still running
        if self.getState() == 'locked' or self._scanning_device.getState() == 'locked':
            return -1
        else:
            self.signal_change_voltage.emit()
            return 0

    def _change_voltage(self):
        """ Threaded method to change the hardware position.

        @return int: error code (0:OK, -1:error)
        """
        self._scanning_device.scanner_set_position(a = self._current_a)
        return 0

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = int(clock_frequency)
        #checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            return 0

    def _initialise_data_matrix(self):
        """ Initializing the ODMR matrix plot. """

        self.scan_matrix = np.zeros( (self.number_of_repeats, self.return_slowness) )

    def start_scanning(self, v_min = None, v_max = None):
        """Setting up the scanner device and starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

        if v_min != None:
            self.scan_range[0] = v_min
        if v_max != None:
            self.scan_range[1] = v_max

        self._scan_counter = 0
        self.upwards_scan = True
        self._initialise_data_matrix()

        self.current_position = self._scanning_device.get_scanner_position()

        self.lock()
        self._scanning_device.lock()



        returnvalue = self._scanning_device.set_up_scanner_clock(clock_frequency = self._clock_frequency)
        if returnvalue < 0:
            self._scanning_device.unlock()
            self.unlock()
            self.set_position('scanner')
            return

        returnvalue = self._scanning_device.set_up_scanner()
        if returnvalue < 0:
            self._scanning_device.unlock()
            self.unlock()
            self.set_position('scanner')
            return

        self.signal_scan_next_line.emit()
        return 0

    def stop_scanning(self):
        """Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True

        return 0


    def _do_next_line(self):
        """If stopRequested then finish the scan, otherwise perform next repeat of the scan line

        """

        # stops scanning
        if self.stopRequested or self._scan_counter == self.number_of_repeats:
            if self.upwards_scan:
                ignored_counts = self._scan_line(self.scan_range[0], self.current_position[3])
            else:
                ignored_counts = self._scan_line(self.scan_range[0], self.current_position[3])
            with self.threadlock:
                self.kill_scanner()
                self.stopRequested = False
                self.unlock()
                return

        if self._scan_counter == 0:
            # move from current voltage to start of scan range.
            ignored_counts = self._scan_line(self.current_position[3], self.scan_range[0])

        if self.upwards_scan:
            counts = self._scan_line(self.scan_range[0], self.scan_range[1])
            self.upwards_scan = False
        else:
            counts = self._scan_line(self.scan_range[1], self.scan_range[0])
            self.upwards_scan = True

        self.scan_matrix[self._scan_counter] = counts

        self._scan_counter += 1
        self.signal_scan_next_line.emit()


    def _scan_line(self, voltage1, voltage2):
        """do a single voltage scan from voltage1 to voltage2

        """
        try:
            # defines trace of positions for single line scan
            scan_line = np.vstack((
                np.linspace(self.current_position[0], self.current_position[0], self.return_slowness),
                np.linspace(self.current_position[1], self.current_position[1], self.return_slowness),
                np.linspace(self.current_position[2], self.current_position[2], self.return_slowness),
                np.linspace(voltage1, voltage2, self.return_slowness)
                ))
            # scan of a single line
            counts_on_scan_line = self._scanning_device.scan_line(scan_line)

            return counts_on_scan_line

        except Exception as e:
            self.logMsg('The scan went wrong, killing the scanner.', msgType='error')
            self.stop_scanning()
            self.signal_scan_next_line.emit()
            raise e

    def kill_scanner(self):
        """Closing the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._scanning_device.close_scanner()
            self._scanning_device.close_scanner_clock()
        except Exception as e:
            self.logExc('Could not even close the scanner, giving up.', msgType='error')
            raise e
        try:
            self._scanning_device.unlock()
        except Exception as e:
            self.logExc('Could not unlock scanning device.', msgType='error')

        return 0

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
