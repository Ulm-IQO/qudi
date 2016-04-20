# -*- coding: utf-8 -*-
"""
Interfuse to do confocal scans with spectrometer data rather than APD count rates.

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

Copyright (C) 2015 Lachlan J. Rogers lachlan.j.rogers@quantum.diamonds
"""

from core.base import Base
from hardware.confocal_scanner_interface import ConfocalScannerInterface
import time

import numpy as np


class SpectrometerScannerInterfuse(Base, ConfocalScannerInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'confocalscannerinterface'
    _modtype = 'hardware'
    # connectors
    _in = {'fitlogic': 'FitLogic',
           'confocalscanner1': 'ConfocalScannerInterface',
           'spectrometer1': 'SpectrometerInterface'}
    _out = {'spectrometerscanner': 'ConfocalScannerInterface'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key, config[key]),
                        msgType='status')

        if 'clock_frequency' in config.keys():
            self._clock_frequency = config['clock_frequency']
        else:
            self._clock_frequency = 100
            self.logMsg('No clock_frequency configured taking 100 Hz instead.',
                        msgType='warning')


        # Internal parameters
        self._line_length = None
        self._scanner_counter_daq_task = None
        self._voltage_range = [-10., 10.]

        self._position_range = [[0., 100.], [0., 100.], [0., 100.], [0., 1.]]
        self._current_position = [0., 0., 0., 0.]

        self._num_points = 500

    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """

        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._scanner_hw = self.connector['in']['confocalscanner1']['object']
        self._spectrometer_hw = self.connector['in']['spectrometer1']['object']


    def deactivation(self, e):
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.logMsg('Scanning Device will be reset.',
                    msgType='warning')
        return 0

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        This is a direct pass-through to the scanner HW.

        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """
        return self._scanner_hw.get_position_range()

    def set_position_range(self, myrange=[[0,1],[0,1],[0,1],[0,1]]):
        """ Sets the physical range of the scanner.
        This is a direct pass-through to the scanner HW

        @param float [4][2] myrange: array of 4 ranges with an array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        self._scanner_hw.set_position_range(myrange=myrange)

        return 0

    def set_voltage_range(self, myrange=[-10.,10.]):
        """ Sets the voltage range of the NI Card.
        This is a direct pass-through to the scanner HW

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        self._scanner_hw.set_voltage_range(myrange=myrange)

        return 0


    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        This is a direct pass-through to the scanner HW

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """

        #return self._scanner_hw.set_up_scanner_clock(clock_frequency=clock_frequency, clock_channel=clock_channel)
        return 0

    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None, scanner_ao_channels = None):
        """ Configures the actual scanner with a given clock.

        TODO this is not technically required, because the spectrometer scanner does not need clock synchronisation.

        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string scanner_ao_channels: if defined, this specifies the analoque output channels

        @return int: error code (0:OK, -1:error)
        """

        self.logMsg('ConfocalScannerInterfaceDummy>set_up_scanner',
                    msgType='warning')

        return 0


    def scanner_set_position(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        This is a direct pass-through to the scanner HW

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        self._scanner_hw.scanner_set_position(x=x, y=y, z=z, a=a)

        return 0

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """

        return self._scanner_hw.get_scanner_position()

    def set_up_line(self, length=100):
        """ Set the line length
        Nothing else to do here, because the line will be scanned using multiple scanner_set_position calls.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        self._line_length = length
        return 0


    def scan_line(self, line_path = None):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points

        @return float[]: the photon counts per second
        """

        #if self.getState() == 'locked':
        #    self.logMsg('A scan_line is already running, close this one first.', \
        #    msgType='error')
        #    return -1
        #
        #self.lock()

        if not isinstance( line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given voltage list is no array type.', \
            msgType='error')
            return np.array([-1.])

        self.set_up_line(np.shape(line_path)[1])

        count_data = np.zeros(self._line_length)

        for i in xrange(self._line_length):
            coords = line_path[:,i]
            self.scanner_set_position(x=coords[0], y=coords[1], z=coords[2], a=coords[3])
            print(coords)
            print(i)

            # record spectral data
            this_spectrum_data = self._spectrometer_hw.recordSpectrum()
            #this_spectrum_data = [1,2,3,4,5]
            count_data[i] = np.sum(this_spectrum_data)
            time.sleep(0.2)

        return count_data

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        #self._scanner_hw.close_scanner()

        return 0

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        #self._scanner_hw.close_scanner_clock()
        return 0
