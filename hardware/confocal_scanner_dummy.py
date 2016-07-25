# -*- coding: utf-8 -*-
"""
This file contains the QuDi dummy module for the confocal scanner.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import time

from core.base import Base
from interface.confocal_scanner_interface import ConfocalScannerInterface


class ConfocalScannerDummy(Base, ConfocalScannerInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'ConfocalScannerDummy'
    _modtype = 'hardware'
    # connectors
    _in = {'fitlogic': 'FitLogic'}
    _out = {'confocalscanner': 'ConfocalScannerInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

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

        self._fit_logic = self.connector['in']['fitlogic']['object']

        # put randomly distributed NVs in the scanner, first the x,y scan
        self._points = np.empty([self._num_points, 7])
        # amplitude
        self._points[:, 0] = np.random.normal(4e5,
                                              1e5,
                                              self._num_points)
        # x_zero
        self._points[:, 1] = np.random.uniform(self._position_range[0][0],
                                               self._position_range[0][1],
                                               self._num_points)
        # y_zero
        self._points[:, 2] = np.random.uniform(self._position_range[1][0],
                                               self._position_range[1][1],
                                               self._num_points)
        # sigma_x
        self._points[:, 3] = np.random.normal(0.7,
                                              0.1,
                                              self._num_points)
        # sigma_y
        self._points[:, 4] = np.random.normal(0.7,
                                              0.1,
                                              self._num_points)
        # theta
        self._points[:, 5] = 10
        # offset
        self._points[:, 6] = 0

        # now also the z-position
#       gaussian_function(self,x_data=None,amplitude=None, x_zero=None, sigma=None, offset=None):

        self._points_z = np.empty([self._num_points, 4])
        # amplitude
        self._points_z[:, 0] = np.random.normal(1,
                                                0.05,
                                                self._num_points)

        # x_zero
        self._points_z[:, 1] = np.random.uniform(45,
                                                 55,
                                                 self._num_points)

        # sigma
        self._points_z[:, 2] = np.random.normal(0.5,
                                              0.1,
                                              self._num_points)

        # offset
        self._points_z[:, 3] = 0

    def on_deactivate(self, e):
        """ Deactivate properly the confocal scanner dummy.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.logMsg('Scanning Device will be reset.',
                    msgType='warning')
        return 0

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        return self._position_range

    def set_position_range(self, myrange=[[0, 1], [0, 1], [0, 1], [0, 1]]):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray, )):
            self.logMsg('Given range is no array type.', msgType='error')
            return -1

        if len(myrange) != 4:
            self.logMsg('Given range should have dimension 4, but has {0:d} '
                        'instead.'.format(len(myrange)), msgType='error')
            return -1

        for pos in myrange:
            if len(pos) != 2:
                self.logMsg('Given range limit {1:d} should have dimension 2, '
                            'but has {0:d} instead.'.format(len(pos), pos),
                            msgType='error')
                return -1
            if pos[0]>pos[1]:
                self.logMsg('Given range limit {0:d} has the wrong '
                            'order.'.format(pos), msgType='error')
                return -1

        self._position_range = myrange

        return 0

    def set_voltage_range(self, myrange=[-10.,10.]):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray, )):
            self.logMsg('Given range is no array type.', msgType='error')
            return -1

        if len(myrange) != 2:
            self.logMsg('Given range should have dimension 2, but has {0:d} '
                        'instead.'.format(len(myrange)), msgType='error')
            return -1

        if myrange[0]>myrange[1]:
            self.logMsg('Given range limit {0:d} has the wrong '
                        'order.'.format(myrange), msgType='error')
            return -1

        if self.getState() == 'locked':
            self.logMsg('A Scanner is already running, close this one first.',
                        msgType='error')
            return -1

        self._voltage_range = myrange

        return 0


    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """

        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)

        self.logMsg('ConfocalScannerDummy>set_up_scanner_clock',
                    msgType='warning')

        time.sleep(0.2)

        return 0


    def set_up_scanner(self, counter_channel=None, photon_source=None,
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

        self.logMsg('ConfocalScannerDummy>set_up_scanner',
                    msgType='warning')

        #if self.getState() == 'locked' or self._scanner_counter_daq_task != None:
        #    self.logMsg('Another scanner is already running, close this one first.', \
        #    msgType='error')
        #    return -1

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

        if self.getState() == 'locked':
            self.logMsg('A Scanner is already running, close this one first.',
                        msgType='error')
            return -1

        time.sleep(0.01)

        self._current_position = [x, y, z, a]

        return 0

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """

        return self._current_position

    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """

        self._line_length = length

#        self.logMsg('ConfocalScannerInterfaceDummy>set_up_line',
#                    msgType='warning')

        return 0


    def scan_line(self, line_path = None):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage
                                      points

        @return float[]: the photon counts per second
        """

        #if self.getState() == 'locked':
        #    self.logMsg('A scan_line is already running, close this one first.', \
        #    msgType='error')
        #    return -1
        #
        #self.lock()

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray, )):
            self.logMsg('Given voltage list is no array type.',
                        msgType='error')
            return np.array([-1.])

        if np.shape(line_path)[1] != self._line_length:
            self.set_up_line(np.shape(line_path)[1])

        #print('line',line_path[0,:])
        count_data = np.random.uniform(0, 2e4, self._line_length)
        z_data = line_path[2, :]

        #TODO: Change the gaussian function here to the one from fitlogic and delete the local modules to calculate
        #the gaussian functions
        if line_path[0, 0] != line_path[0, 1]:
            x_data,y_data = np.meshgrid(line_path[0, :], line_path[1, 0])
            for i in range(self._num_points):
                count_data += self.twoD_gaussian_function((x_data,y_data),
                              *(self._points[i])) * ((self.gaussian_function(np.array(z_data),
                              *(self._points_z[i]))))
        else:
            x_data,y_data = np.meshgrid(line_path[0, 0], line_path[1, 0])
            for i in range(self._num_points):
                count_data += self.twoD_gaussian_function((x_data,y_data),
                              *(self._points[i])) * ((self.gaussian_function(z_data,
                              *(self._points_z[i]))))


        time.sleep(self._line_length*1./self._clock_frequency)
        time.sleep(self._line_length*1./self._clock_frequency)

#        self.logMsg('ConfocalScannerInterfaceDummy>scan_line: length {0:d}.'.format(self._line_length),
#                    msgType='warning')

        #self.unlock()

        # update the scanner position instance variable
        self._current_position = list(line_path[:, -1])

        return count_data

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.logMsg('ConfocalScannerDummy>close_scanner',  msgType='warning')

        self._scanner_counter_daq_task = None

        return 0

    def close_scanner_clock(self,power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.logMsg('ConfocalScannerDummy>close_scanner_clock',
                    msgType='warning')
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
        if not isinstance( x_data_tuple,(frozenset, list, set, tuple,
                            np.ndarray)):
            self.logMsg('Given range of axes is no array type.',
                        msgType='error')

        parameters=[amplitude,x_zero,y_zero,sigma_x,sigma_y,theta,offset]
        for var in parameters:
            if not isinstance(var,(float,int)):
                self.logMsg('Given range of parameter is no float or int.',
                            msgType='error')

        (x, y) = x_data_tuple
        x_zero = float(x_zero)
        y_zero = float(y_zero)

        a = (np.cos(theta)**2)/(2*sigma_x**2) \
                                    + (np.sin(theta)**2)/(2*sigma_y**2)
        b = -(np.sin(2*theta))/(4*sigma_x**2) \
                                    + (np.sin(2*theta))/(4*sigma_y**2)
        c = (np.sin(theta)**2)/(2*sigma_x**2) \
                                    + (np.cos(theta)**2)/(2*sigma_y**2)
        g = offset + amplitude*np.exp( - (a*((x-x_zero)**2) \
                                + 2*b*(x-x_zero)*(y-y_zero) \
                                + c*((y-y_zero)**2)))
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
            self.logMsg('Given range of axis is no array type.',
                        msgType='error')


        parameters=[amplitude,x_zero,sigma,offset]
        for var in parameters:
            if not isinstance(var,(float,int)):
                print('error',var)
                self.logMsg('Given range of parameter is no float or int.',
                            msgType='error')
        gaussian = amplitude*np.exp(-(x_data-x_zero)**2/(2*sigma**2))+offset
        return gaussian


