# -*- coding: utf-8 -*-
"""
Interfuse to do confocal scans with spectrometer data rather than APD count rates.

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

import time
import numpy as np

from core.base import Base
from interface.confocal_scanner_interface import ConfocalScannerInterface


class ConfocalScannerMotorInterfuse(Base, ConfocalScannerInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'confocalscannerinterface'
    _modtype = 'hardware'
    # connectors
    _connectors = {'fitlogic': 'FitLogic',
           'confocalscanner1': 'ConfocalScannerInterface',
                   'magnetinterface': 'MagnetInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        # if 'clock_frequency' in config.keys():
        #    self._clock_frequency = config['clock_frequency']
        # else:
        #    self._clock_frequency = 100
        #    self.log.warning('No clock_frequency configured taking 100 Hz '
        #            'instead.')

        self._clock_frequency = 100

        # Internal parameters
        self._line_length = None
        self._scanner_counter_daq_task = None
        self._voltage_range = [-1., 1.]

        self._position_range = [[0., 1.], [0., 1.], [0., 1.], [0., 0]]
        self._current_position = [0., 0., 0., 0.]

        self._num_points = 500

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._fit_logic = self.get_connector('fitlogic')
        self._confocal_hw = self.get_connector('confocalscanner1')
        self._motor_hw = self.get_connector('magnetinterface')


        #have to add these tilt variables for the logic to not give error
        self.tilt_variable_ax = 1
        self.tilt_variable_ay = 1
        self.tiltcorrection = False
        self.tilt_reference_x = 0
        self.tilt_reference_y = 0


        #Goto reference of motors

        #self._motor_hw.calibrate()

        self._count_frequency = 50

        self._clock_frequency_default = 100             # in Hz

        #must set these bits, especially for Nova Stage
        self._motor_hw.set_velocity({'x-axis':1e-3,'y-axis':1e-3,'z-axis':1e-3})

        constraints = self._motor_hw.get_constraints()

        self.position_range = []
        for label_axis in constraints:
            self.position_range.append([constraints[label_axis]['scan_min'],constraints[label_axis]['scan_max']])

        self.position_range.append([0,0])

    def on_deactivate(self, e):
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Scanning Device will be reset.')

        return 0

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        This is a direct pass-through to the scanner HW.l;;

        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """

        #check if this needs micrometres!

        #self.log.error('Scan range is {0}'.format(self.position_range))

        return self.position_range

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.
        This is a direct pass-through to the scanner HW

        @param float [4][2] myrange: array of 4 ranges with an array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Setting position range not currently implemented')






        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.
        This is a direct pass-through to the scanner HW

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        return 0

    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        This is a direct pass-through to the scanner HW

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """
        #self.log.info('No scanner clock on motor')
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
        #self.log.warning('set_up_scanner')
        return 0

    def get_scanner_axes(self):
        """ Pass through scanner axes. """

        n = 2

        possible_channels = ['x', 'y', 'z', 'a']

        return possible_channels[0:int(n)]

    def scanner_set_position(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        This is a direct pass-through to the scanner HW

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        #self._scanner_hw.scanner_set_position(x=x, y=y, z=z, a=a)

        # TODO: make this not hardcoded to axis name?
        move_dict = {}
        if x is not None:
            move_dict.update({'x-axis': x})
        if y is not None:
            move_dict.update({'y-axis': y})
        if z is not None:
            move_dict.update({'z-axis': z})

        #self.log.info(move_dict)
        self._motor_hw.move_abs(move_dict)

        #self.log.info('We want to be {0}'.format(move_dict))
        #self.log.info('We are {0}'.format(self._motor_hw.get_pos()))

        return 0

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z).
        """
        position_dict = self._motor_hw.get_pos()
        position_vect = []
        #self.log.info('motor interfuse reports {0}'.format(position_dict))

        label_dict = {'x-axis','y-axis','z-axis'}

        for k in sorted(label_dict):
            if position_dict.get(k) is not None:
                position_vect.append(position_dict[k])
        #y, z, x
        #Add random a channel
        #position_vect.append(0)
        #self.log.info('Current position in (x,y,z) is {0}'.format(position_vect))
        return position_vect

    def set_up_line(self, length=100):
        """ Set the line length
        Nothing else to do here, because the line will be scanned using multiple scanner_set_position calls.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        self._line_length = length
        return 0


    def scan_line(self, line_path = None, pixel_clock = False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points

        @return float[]: the photon counts per second
        """

        #if self.getState() == 'locked':
        #    self.log.error('A scan_line is already running, close this one first.')
        #    return -1
        #
        #self.lock()

        if not isinstance( line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.log.error('Given voltage list is no array type.')
            return np.array([-1.])

        # setting up the counter


        clock_status = self._confocal_hw.set_up_clock(clock_frequency=self._count_frequency)
        if clock_status < 0:
            return np.array([-1.])

        counter_status = self._confocal_hw.set_up_counter()
        if counter_status < 0:
            self._confocal_hw.close_clock()
            return np.array([-1.])

        self.set_up_line(np.shape(line_path)[1])

        #count_data = np.empty(
        #        (len(self.get_scanner_count_channels()), self._line_length),
        #       dtype=np.uint32)

        count_data = np.empty(
                (self._line_length, 1),
        dtype = np.uint32)

        #if dir == 1:
         #   line_path
          #  dir = -1

        for i in range(self._line_length):
            coords = line_path[:, i]

            #self.log.info('x is {0} and y is {1}'.format(coords[0],coords[1]))
            if len(coords) == 2: #  xy scan
                self.scanner_set_position(x=coords[0], y=coords[1])

            if len(coords) == 1: #  depth scan
                self.scanner_set_position(z=coords[0])
            # record counts
            #self.log.info(self._confocal_hw.get_counter())
            count = self._confocal_hw.get_counter()

            #self.log.info(self.get_scanner_position())

            count_data[i,0] = np.mean(count) # could be say, 10 values

        self._confocal_hw.close_counter(scanner=False)
        self._confocal_hw.close_clock(scanner=False)

        return count_data

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        self._motor_hw.abort()
        #self._scanner_hw.close_scanner()

        return 0

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        #self._scanner_hw.close_scanner_clock()
        return 0

    def  get_scanner_count_channels(self):

        return ['Ctr1']
