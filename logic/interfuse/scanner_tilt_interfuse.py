"""
This file contains the Qudi Interfuse between Magnet Logic and Motor Hardware.

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

import copy

from core.module import Connector
from logic.generic_logic import GenericLogic
from interface.confocal_scanner_interface import ConfocalScannerInterface


class ScannerTiltInterfuse(GenericLogic, ConfocalScannerInterface):
    """ This interfuse produces a Z correction corresponding to a tilted surface.
    """

    _modclass = 'ScannerTiltInterfuse'
    _modtype = 'interfuse'

    confocalscanner1 = Connector(interface='ConfocalScannerInterface')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._scanning_device = self.confocalscanner1()

        self.tilt_variable_ax = 1
        self.tilt_variable_ay = 1
        self.tiltcorrection = False
        self.tilt_reference_x = 0
        self.tilt_reference_y = 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        return self._scanning_device.get_position_range()

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [[0, 1], [0, 1], [0, 1], [0, 1]]
        return self._scanning_device.set_position_range(myrange)

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [-10., 10.]
        return self._scanning_device.set_voltage_range(myrange)

    def get_scanner_axes(self):
        """ Pass through scanner axes """
        return self._scanning_device.get_scanner_axes()

    def get_scanner_count_channels(self):
        """ Pass through scanner counting channels """
        return self._scanning_device.get_scanner_count_channels()

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.set_up_scanner_clock(clock_frequency, clock_channel)

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
        return self._scanning_device.set_up_scanner(
            counter_channel,
            photon_source,
            clock_channel,
            scanner_ao_channels)

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        if self.tiltcorrection:
            z += self._calc_dz(x, y)
            z_min = self.get_position_range()[2][0]
            z_max = self.get_position_range()[2][1]
            if not(z_min <= z <= z_max):
                z = min(max(z, z_min), z_max)
                self.log.warning(
                    'The entered z position is out of scanner '
                    'range! z was set to min/max.')
            return self._scanning_device.scanner_set_position(x, y, z, a)
        else:
            return self._scanning_device.scanner_set_position(x, y, z, a)

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        position = copy.copy(self._scanning_device.get_scanner_position())    # not tested atm
        if self.tiltcorrection:
            position[2] -= self._calc_dz(position[0], position[1])
            return position
        else:
            return position

    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.set_up_line(length)

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the positions pixels
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """
        if self.tiltcorrection:
            line_path[:][2] += self._calc_dz(line_path[:][0], line_path[:][1])
        return self._scanning_device.scan_line(line_path, pixel_clock)

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.close_scanner()

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.close_scanner_clock()

    def _calc_dz(self, x, y):
        """Calculates the change in z for given tilt correction."""
        if not self.tiltcorrection:
            return 0.
        else:
            dz = -(
                (x - self.tilt_reference_x) * self.tilt_variable_ax
                + (y - self.tilt_reference_y) * self.tilt_variable_ay
            )
            return dz
