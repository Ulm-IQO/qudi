# -*- coding: utf-8 -*-
"""
This file contains the Qudi dummy module for the confocal scanner.

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
import time

from core.module import Base, Connector, ConfigOption
from interface.confocal_scanner_interface import ConfocalScannerInterface


class ConfocalScannerDummy(Base, ConfocalScannerInterface):

    """ Dummy confocal scanner.
        Produces a picture with several gaussian spots.
    """
    _modclass = 'ConfocalScannerDummy'
    _modtype = 'hardware'

    # connectors
    fitlogic = Connector(interface='FitLogic')

    # config
    _clock_frequency = ConfigOption('clock_frequency', 100, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Internal parameters
        self._line_length = None
        self._voltage_range = [-10, 10]

        self._position_range = [[0, 100e-6], [0, 100e-6], [0, 100e-6], [0, 1e-6]]
        self._current_position = [0, 0, 0, 0][0:len(self.get_scanner_axes())]
        self._num_points = 500

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._fit_logic = self.get_connector('fitlogic')

        # put randomly distributed NVs in the scanner, first the x,y scan
        self._points = np.empty([self._num_points, 7])
        # amplitude
        self._points[:, 0] = np.random.normal(
            4e5,
            1e5,
            self._num_points)
        # x_zero
        self._points[:, 1] = np.random.uniform(
            self._position_range[0][0],
            self._position_range[0][1],
            self._num_points)
        # y_zero
        self._points[:, 2] = np.random.uniform(
            self._position_range[1][0],
            self._position_range[1][1],
            self._num_points)
        # sigma_x
        self._points[:, 3] = np.random.normal(
            0.7e-6,
            0.1e-6,
            self._num_points)
        # sigma_y
        self._points[:, 4] = np.random.normal(
            0.7e-6,
            0.1e-6,
            self._num_points)
        # theta
        self._points[:, 5] = 10
        # offset
        self._points[:, 6] = 0

        # now also the z-position
#       gaussian_function(self,x_data=None,amplitude=None, x_zero=None, sigma=None, offset=None):

        self._points_z = np.empty([self._num_points, 4])
        # amplitude
        self._points_z[:, 0] = np.random.normal(
            1,
            0.05,
            self._num_points)

        # x_zero
        self._points_z[:, 1] = np.random.uniform(
            45e-6,
            55e-6,
            self._num_points)

        # sigma
        self._points_z[:, 2] = np.random.normal(
            0.5e-6,
            0.1e-6,
            self._num_points)

        # offset
        self._points_z[:, 3] = 0

    def on_deactivate(self):
        """ Deactivate properly the confocal scanner dummy.
        """
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Scanning Device will be reset.')
        return 0

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        return self._position_range

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [[0, 1e-6], [0, 1e-6], [0, 1e-6], [0, 1e-6]]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray, )):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != 4:
            self.log.error('Given range should have dimension 4, but has '
                    '{0:d} instead.'.format(len(myrange)))
            return -1

        for pos in myrange:
            if len(pos) != 2:
                self.log.error('Given range limit {1:d} should have '
                        'dimension 2, but has {0:d} instead.'.format(
                            len(pos),
                            pos))
                return -1
            if pos[0]>pos[1]:
                self.log.error('Given range limit {0:d} has the wrong '
                        'order.'.format(pos))
                return -1

        self._position_range = myrange

        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [-10.,10.]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray, )):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != 2:
            self.log.error('Given range should have dimension 2, but has '
                    '{0:d} instead.'.format(len(myrange)))
            return -1

        if myrange[0]>myrange[1]:
            self.log.error('Given range limit {0:d} has the wrong '
                    'order.'.format(myrange))
            return -1

        if self.module_state() == 'locked':
            self.log.error('A Scanner is already running, close this one '
                    'first.')
            return -1

        self._voltage_range = myrange

        return 0

    def get_scanner_axes(self):
        """ Dummy scanner is always 3D cartesian.
        """
        return ['x', 'y', 'z', 'a']

    def get_scanner_count_channels(self):
        """ 3 counting channels in dummy confocal: normal, negative and a ramp."""
        return ['Norm', 'Neg', 'Ramp']

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """

        if clock_frequency is not None:
            self._clock_frequency = float(clock_frequency)

        self.log.debug('ConfocalScannerDummy>set_up_scanner_clock')
        time.sleep(0.2)
        return 0


    def set_up_scanner(self, counter_channels=None, sources=None,
                       clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        @param str counter_channel: if defined, this is the physical channel of
                                    the counter
        @param str photon_source: if defined, this is the physical channel where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str scanner_ao_channels: if defined, this specifies the analoque
                                        output channels

        @return int: error code (0:OK, -1:error)
        """

        self.log.debug('ConfocalScannerDummy>set_up_scanner')
        time.sleep(0.2)
        return 0


    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        if self.module_state() == 'locked':
            self.log.error('A Scanner is already running, close this one first.')
            return -1

        time.sleep(0.01)

        self._current_position = [x, y, z, a][0:len(self.get_scanner_axes())]
        return 0

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        return self._current_position[0:len(self.get_scanner_axes())]

    def _set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """

        self._line_length = length

#        self.log.debug('ConfocalScannerInterfaceDummy>set_up_line')
        return 0

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray, )):
            self.log.error('Given voltage list is no array type.')
            return np.array([[-1.]])

        if np.shape(line_path)[1] != self._line_length:
            self._set_up_line(np.shape(line_path)[1])

        count_data = np.random.uniform(0, 2e4, self._line_length)
        z_data = line_path[2, :]

        #TODO: Change the gaussian function here to the one from fitlogic and delete the local modules to calculate
        #the gaussian functions
        x_data = np.array(line_path[0, :])
        y_data = np.array(line_path[1, :])
        for i in range(self._num_points):
            count_data += self.twoD_gaussian_function((x_data, y_data), *(self._points[i])
                ) * self.gaussian_function(np.array(z_data), *(self._points_z[i]))

        time.sleep(self._line_length * 1. / self._clock_frequency)
        time.sleep(self._line_length * 1. / self._clock_frequency)

        # update the scanner position instance variable
        self._current_position = list(line_path[:, -1])

        return np.array([
                count_data,
                5e5 - count_data,
                np.ones(count_data.shape) * line_path[1, 0] * 100
            ]).transpose()

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.log.debug('ConfocalScannerDummy>close_scanner')
        return 0

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.log.debug('ConfocalScannerDummy>close_scanner_clock')
        return 0

############################################################################
#                                                                          #
#    the following two functions are needed to fluoreschence signal        #
#                             of the dummy NVs                             #
#                                                                          #
############################################################################


    def twoD_gaussian_function(self, x_data_tuple=None, amplitude=None,
                               x_zero=None, y_zero=None, sigma_x=None,
                               sigma_y=None, theta=None, offset=None):

        #FIXME: x_data_tuple: dimension of arrays

        """ This method provides a two dimensional gaussian function.

        @param (k,M)-shaped array x_data_tuple: x and y values
        @param float or int amplitude: Amplitude of gaussian
        @param float or int x_zero: x value of maximum
        @param float or int y_zero: y value of maximum
        @param float or int sigma_x: standard deviation in x direction
        @param float or int sigma_y: standard deviation in y direction
        @param float or int theta: angle for eliptical gaussians
        @param float or int offset: offset

        @return callable function: returns the function

        """
        # check if parameters make sense
        #FIXME: Check for 2D matrix
        if not isinstance( x_data_tuple,(frozenset, list, set, tuple, np.ndarray)):
            self.log.error('Given range of axes is no array type.')

        parameters = [amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset]
        for var in parameters:
            if not isinstance(var, (float, int)):
                self.log.error('Given range of parameter is no float or int.')

        (x, y) = x_data_tuple
        x_zero = float(x_zero)
        y_zero = float(y_zero)

        a = (np.cos(theta)**2) / (2 * sigma_x**2) + (np.sin(theta)**2) / (2 * sigma_y**2)
        b = -(np.sin(2 * theta)) / (4 * sigma_x**2) + (np.sin(2 * theta)) / (4 * sigma_y**2)
        c = (np.sin(theta)**2) / (2 * sigma_x**2) + (np.cos(theta)**2) / (2 * sigma_y**2)
        g = offset + amplitude * np.exp(
            - (a * ((x - x_zero)**2)
                + 2 * b * (x - x_zero) * (y - y_zero)
                + c * ((y - y_zero)**2)))
        return g.ravel()

    def gaussian_function(self, x_data=None, amplitude=None, x_zero=None,
                          sigma=None, offset=None):
        """ This method provides a one dimensional gaussian function.

        @param array x_data: x values
        @param float or int amplitude: Amplitude of gaussian
        @param float or int x_zero: x value of maximum
        @param float or int sigma: standard deviation
        @param float or int offset: offset

        @return callable function: returns a 1D Gaussian function

        """
        # check if parameters make sense
        if not isinstance( x_data,(frozenset, list, set, tuple, np.ndarray)):
            self.log.error('Given range of axis is no array type.')


        parameters=[amplitude,x_zero,sigma,offset]
        for var in parameters:
            if not isinstance(var,(float,int)):
                print('error',var)
                self.log.error('Given range of parameter is no float or int.')
        gaussian = amplitude*np.exp(-(x_data-x_zero)**2/(2*sigma**2))+offset
        return gaussian


