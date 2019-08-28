"""
This file contains the Qudi interfuse to correct small aberration in the scanning setup

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

from core.module import Connector, ConfigOption
from logic.generic_logic import GenericLogic
from interface.confocal_scanner_interface import ConfocalScannerInterface


class ScannerAberrationInterfuse(GenericLogic, ConfocalScannerInterface):
    """ This interfuse produces a correction in x and y of simple aberration caused by working off axis

    Using a steering mirror to scan a sample by working off axis will induce small aberrations.
    This interfuse aim at correcting by providing a polynomial correction :
    (x, y) meter -> (x, y) angle

    The method implemented here use a general approach with numpy.polynomial.polynomial.polyval2d function

    The idea is to use multiple scans or optical design software to fit polynomially the deformation induced by the
     setup, then invert it with this module.

    Example config:

    scanner_aberration_interfuse:
        module.Class: 'interfuse.scanner_aberration_interfuse.ScannerAberrationInterfuse'
        connect:
            scanner: 'mydummyscanner'
        range_x: [0, 50e-6]
        range_y: [0, 50e-6]
        poly2d_x: [[0, 1], [0.5, 0]]
        poly2d_y: [[0, 0.5], [1, 0]]

    """

    scanner = Connector(interface='ConfocalScannerInterface')

    config_poly2d_x = ConfigOption('poly2d_x', [[0, 1], [0, 0]], missing='warn')
    config_poly2d_y = ConfigOption('poly2d_y', [[0, 0], [1, 0]], missing='warn')
    config_range_x = ConfigOption('range_x')
    config_range_y = ConfigOption('range_y')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module """
        try:
            self._poly2d_x = np.array(self.config_poly2d_x)
            self._poly2d_y = np.array(self.config_poly2d_y)
            _, _ = self._convert_point(0,0) # checks if works
        except ValueError:
            self.log.error('Configuration options poly2d_x or poly2d_y are not correct.')

        # Let's check for obvious errors : if the corners are not in range, something is wrong.
        # This does NOT guarantee EVERY point (x ,y) will be in range !
        corners = [(self.config_range_x[0], self.config_range_y[0]),
                   (self.config_range_x[0], self.config_range_y[1]),
                   (self.config_range_x[1], self.config_range_y[0]),
                   (self.config_range_x[1], self.config_range_y[1])]
        for corner in corners:
            x, y = self._convert_point(*corner)
            scanner_range = self.scanner().get_position_range()
            if not (scanner_range[0][0] <= x <= scanner_range[0][1]) or \
               not (scanner_range[1][0] <= x <= scanner_range[1][1]):
                self.log.error('Provided range does not match polynomes. Corner ({}, {}) transformed to ({}, {}) is not'
                               'in range.'.format(*corner, x, y))
        self._range_x = self.config_range_x
        self._range_y = self.config_range_y
        self._position = np.array([None, None])  # Position can not be known at activation

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module """
        pass

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        return self.scanner().reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        scanner_range = np.array(self.scanner().get_position_range())
        return np.array([self._range_x, self._range_y, *scanner_range[2:, :]])

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner  """
        return 0  # This parameter should not be changed by logic

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card. """
        return 0  # This parameter should not be changed by logic

    def get_scanner_axes(self):
        """ Pass through scanner axes """
        return self.scanner().get_scanner_axes()

    def get_scanner_count_channels(self):
        """ Pass through scanner counting channels """
        return self.scanner().get_scanner_count_channels()

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        return self.scanner().set_up_scanner_clock(clock_frequency, clock_channel)

    def set_up_scanner(self, counter_channel=None, photon_source=None, clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock """
        return self.scanner().set_up_scanner(counter_channel, photon_source, clock_channel, scanner_ao_channels)

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: position in x-direction (volts)
        @param float y: position in y-direction (volts)
        @param float z: position in z-direction (volts)
        @param float a: position in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        x = x if x is not None else self._position[0]
        y = y if y is not None else self._position[1]

        if x is not None and y is not None:  # after activation, if logic has not setted position once
            self._position[0] = x
            self._position[1] = y
            converted_x, converted_y = self._convert_point(x, y)
            self.scanner().scanner_set_position(converted_x, converted_y, z, a)
        else:
            self.log.warning('Position has not been initialized. Hardware not affected this time.')

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a)
        """
        scanner_position = np.array(self.scanner().get_scanner_position())
        return list(np.array([*self._position, *scanner_position[2:]]))

    def set_up_line(self, length=100):
        """ Sets up the analogue output for scanning a line. """
        return self.scanner().set_up_line(length)

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the positions pixels
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """
        transformed = line_path.copy()
        points_x, points_y = self._convert_point(line_path[0, :], line_path[1, :])
        transformed[0, :] = points_x
        transformed[1, :] = points_y
        return self.scanner().scan_line(transformed, pixel_clock)

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards """
        return self.scanner().close_scanner()

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards """
        return self.scanner().close_scanner_clock()

    def _convert_point(self, x, y):
        """ Convert one point or an array of point from input coordinate to output coordinate """
        res_x = np.polynomial.polynomial.polyval2d(x, y, self._poly2d_x.T)
        res_y = np.polynomial.polynomial.polyval2d(x, y, self._poly2d_y.T)
        return res_x, res_y
