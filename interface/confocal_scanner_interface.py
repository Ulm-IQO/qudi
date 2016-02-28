# -*- coding: utf-8 -*-

"""
This module contains the QuDi interface file for confocal scanner.

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

Copyright (C) 2015 Kay Jahnke kay.jahnke@alumni.uni-ulm.de
Copyright (C) 2015 Lachlan J. Rogers  lachlan.rogers@uni-ulm.de
"""

from core.util.customexceptions import InterfaceImplementationError


class ConfocalScannerInterface():
    """ This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    _modtype = 'ConfocalScannerInterface'
    _modclass = 'interface'

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>reset_hardware')
        return -1

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>get_position_range')
        return -1

    def set_position_range(self, myrange=[[0, 1], [0, 1], [0, 1], [0, 1]]):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>set_position_range')
        return -1

    def set_voltage_range(self, myrange=[-10., 10.]):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>set_voltage_range')
        return -1

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>set_up_scanner_clock')
        return -1

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

        raise InterfaceImplementationError('ConfocalScannerInterface>set_up_scanner')
        return -1

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>scanner_set_pos')
        return -1

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>get_scanner_pos')
        return -1

    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>set_up_line')
        return -1

    def scan_line(self, line_path=None):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the
                                     positions pixels

        @return float[]: the photon counts per second
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>scan_line')
        return [0.0]

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>close_scanner')
        return -1

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('ConfocalScannerInterface>close_scanner_clock')
        return -1
