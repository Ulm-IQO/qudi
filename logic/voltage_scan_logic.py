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

        # Sets the current position to the center of the maximal scanning range
        self._current_a = (self.a_range[0] + self.a_range[1]) / 2.

        # Sets connections between signals and functions
        self.signal_change_voltage.connect(self._change_voltage, QtCore.Qt.QueuedConnection)


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

    def start_scanner(self):
        """Setting up the scanner device and starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

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

        #self.signal_scan_lines_next.emit()
        return 0


    def _scan_line(self, start, end):
        """scanning an image in either depth or xy

        """
        current_position = self._scanning_device.get_scanner_position()

        try:
            # defines trace of positions for single line scan
            start_line = np.vstack((
                np.linspace(current_position[0], current_position[0], self.return_slowness),
                np.linspace(current_position[1], current_position[1], self.return_slowness),
                np.linspace(current_position[2], current_position[2], self.return_slowness),
                np.linspace(current_position[3], start, self.return_slowness)
                ))
            # scan of a single line
            start_line_counts = self._scanning_device.scan_line(start_line)

            # defines trace of positions for a single line scan
            line_up = np.vstack((
                np.linspace(current_position[0], current_position[0], self.return_slowness),
                np.linspace(current_position[1], current_position[1], self.return_slowness),
                np.linspace(current_position[2], current_position[2], self.return_slowness),
                np.linspace(start, end, self.return_slowness)
                ))
            # scan of a single line
            line_up_counts = self._scanning_device.scan_line(line_up)


        except Exception as e:
            self.logMsg('The scan went wrong, killing the scanner.', msgType='error')
            raise e

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
