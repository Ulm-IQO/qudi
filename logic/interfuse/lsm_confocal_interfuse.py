# -*- coding: utf-8 -*-

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

import numpy as np

from core.connector import Connector
from logic.generic_logic import GenericLogic
from interface.temporary_scanning_interface import ScanSettings
from interface.confocal_scanner_interface import ConfocalScannerInterface


class LSMConfocalInterfuse(GenericLogic, ConfocalScannerInterface):
    """
    """

    lsm_scanner = Connector(interface='TemporaryScanningInterface')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__scan_settings = None

        self.__positioning_range = tuple()
        self.__available_axes = tuple()
        self.__available_data_channels = tuple()

        self.__current_line_index = 0
        self.__number_of_lines = -1

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        constr = self.lsm_scanner().get_constraints()
        ranges = [tuple(rng) for rng in constr['axes_position_ranges'].values()][:3]
        ranges.append((0, 0))
        self.__positioning_range = tuple(ranges)
        self.__available_axes = tuple([*constr['axes_position_ranges'], 'a'])
        self.__available_data_channels = tuple(constr['data_channel_units'])[:3]

        self.__current_line_index = 0
        self.__number_of_lines = -1
        self.__scan_settings = None

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
        """
        pass

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        return self.lsm_scanner().reset()

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        return self.__positioning_range

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning(
            '"set_position_range" is deprecated and should not be used. Method call ignored.')
        return -1

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning(
            '"set_voltage_range" is deprecated and should not be used. Method call ignored.')
        return -1

    def get_scanner_axes(self):
        """ Pass through scanner axes """
        return self.__available_axes

    def get_scanner_count_channels(self):
        """ Pass through scanner counting channels """
        return self.__available_data_channels

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def configure_scan(self, settings):
        """ Configure a scan job in hardware.
        This method is not part of the interface and is just a quick-and-dirty temporary solution
        (like this entire module).

        @param ScanSettings settings: ScanSettings instance holding all parameters for a scan job.

        @return (int, ScanSettings): Failure indicator (0: success, -1: failure),
                                     ScanSettings instance with actually set parameters
        """
        if self.lsm_scanner().module_state() == 'locked':
            self.log.error('Unable to configure scan parameters. Scan is still active.')
            return self.lsm_scanner().get_scan_settings()
        err, return_settings = self.lsm_scanner().configure_scan(settings)
        if err < 0:
            self.__scan_settings = None
            self.__number_of_lines = -1
        else:
            self.__scan_settings = return_settings.copy()
            if len(return_settings.resolution) == 1:
                self.__number_of_lines = 1
            else:
                self.__number_of_lines = return_settings.resolution[1]
        return err, return_settings

    def set_up_scanner(self, counter_channel=None, photon_source=None,
                       clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        @param str counter_channel: if defined, this is the physical channel of the counter
        @param str photon_source: if defined, this is the physical channel where the photons are to
                                  count from
        @param str clock_channel: if defined, this specifies the clock for the counter
        @param str scanner_ao_channels: if defined, this specifies the analog output channels

        @return int: error code (0:OK, -1:error)
        """
        return self.lsm_scanner().lock_scanner()

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        if self.lsm_scanner().module_state() == 'locked':
            self.log.error('Unable to set scanner position. Scan is still active.')
            return -1
        curr_pos = self.lsm_scanner().get_target()
        move_to = {ax: pos for ax, pos in zip(curr_pos, (x, y, z)) if
                   pos is not None and pos != curr_pos[ax]}
        new_pos = self.lsm_scanner().move_absolute(move_to)
        return -int(any(pos != move_to[ax] for ax, pos in new_pos.items()))

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        position = self.lsm_scanner().get_target()
        return (*position.values(), 0)

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the positions pixels
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """
        if self.lsm_scanner().module_state() != 'locked':
            self.log.error('Unable to get scan line. No scan is running.')
            return -1 * np.ones((1, len(self.__available_data_channels)))
        if self.__current_line_index >= self.__number_of_lines:
            self.log.error('Tried to overscan (too many lines).')
            return -1 * np.ones((1, len(self.__available_data_channels)))

        line = self.lsm_scanner().get_scan_line(self.__current_line_index)
        self.__current_line_index += 1

        data = np.empty(len(line_path), len(self.__available_data_channels))
        for i, channel in enumerate(self.__available_data_channels):
            data[:, i] = line[channel]
        return data

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self.lsm_scanner().unlock_scanner()

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0
