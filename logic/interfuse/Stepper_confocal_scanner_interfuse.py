# -*- coding: utf-8 -*-
"""
Interfuse to do confocal scans with a piezo stepper rather than piezo scanner using the counter
interface to generate the right return.

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

import numpy as np

from core.base import Base
from interface.confocal_scanner_interface import ConfocalScannerInterface
from interface.piezo_stepper_interface import PiezoStepperInterface
from interface.analog_reader_interface import AnalogReaderInterface
from interface.slow_counter_interface import SlowCounterInterface

#TODO: Discuss how to implement switch between scan modes. That is scanner and stepper.

class StepperScannerInterfuse(Base, ConfocalScannerInterface, PiezoStepperInterface,
                              AnalogReaderInterface, SlowCounterInterface):

    _modtype = 'ConfocalScannerInterface'
    _modclass = 'hardware'

    # connectors
    _in = {'counter': 'SlowCounterInterface',
           'piezostepper1': 'PiezoStepperInterface',
           'analogreader1': 'AnalogReaderInterface',
           'confocalscanner': 'ConfocalScannerInterface'}
    _out = {'stepperscanner': 'ConfocalScannerInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))
        #TODO: I am not sure if this is correct

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.
        """
        self._counter = self.get_in_connector('counter')
        self._scanning_device1 = self.get_in_connector('piezostepper1')
        self._scanning_device2 = self.get_in_connector('confocalscanner')
        self._analog_reader = self.get_in_connector('analogreader1')


    def on_deactivate(self, e):
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        #TODO: Not sure what to do for the NIDAQ here, that is as there is no reset hardware in
        # counter. And also, should there be one in analog_reader?
        return self._scanning_device1.reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        This is a direct pass-through to the stepper hardware.

        @return float [n][2]: array of n ranges with an array containing lower
                              and upper limit,  n defined in config
        """

        return self._scanning_device1.get_position_range()

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.
        This is a direct pass-through to the stepper hardware.

        @param float [n][2] myrange: array of n ranges with an array containing
                                     lower and upper limit,  n defined in config

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device1.get_position_range(myrange)

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        pass

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    def set_up_scanner(self, counter_channel=None, photon_source=None,
                       clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        @param str counter_channel: if defined, this is the physical channel
                                    of the counter
        @param str photon_source: if defined, this is the physical channel where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str scanner_ao_channels: if defined, this specifies the analoque
                                        output channels

        @return int: error code (0:OK, -1:error)
        """
        pass

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        #if self.getState() == 'locked':
         #   self.log.error('Another scan_line is already running, close this one first.')
          #  return -1

        if x is not None:
            if not(self._position_range[0][0] <= x <= self._position_range[0][1]):
                self.log.error('You want to set x out of range: {0:f}.'.format(x))
                return -1
            self._current_position[0] = np.float(x)

        if y is not None:
            if not(self._position_range[1][0] <= y <= self._position_range[1][1]):
                self.log.error('You want to set y out of range: {0:f}.'.format(y))
                return -1
            self._current_position[1] = np.float(y)

        if z is not None:
            if not(self._position_range[2][0] <= z <= self._position_range[2][1]):
                self.log.error('You want to set z out of range: {0:f}.'.format(z))
                return -1
            self._current_position[2] = np.float(z)

        if a is not None:
            if not(self._position_range[3][0] <= a <= self._position_range[3][1]):
                self.log.error('You want to set a out of range: {0:f}.'.format(a))
                return -1
            self._current_position[3] = np.float(a)
        #Todo: This need to be an actual interfuse. First asking for the corrtesponding position
        #  we are at, then caluclating how many steps to make, moving them, then testing again
        # until a certain accuracy is achieved
        pass

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        #Todo: This need to ask the analog inputs from the API Hardware and change these to
        # position values
        pass

    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        pass

    def scan_line(self, line_path=None):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the
                                     positions pixels

        @return float[]: the photon counts per second
        """
        pass

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

