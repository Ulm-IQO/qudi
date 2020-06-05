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

import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.temporary_scanning_interface import TemporaryScanningInterface, ScanSettings


class TemporaryScanningDummy(Base, TemporaryScanningInterface):
    """
    Dummy scanning probe microscope. Produces a picture with several gaussian spots.

    Example config for copy-paste:

    scanning_probe_dummy:
        module.Class: 'scanning_probe_dummy.ScanningProbeDummy'
        spot_density: 4e6           # in 1/m², optional
        position_ranges:
            x: [0, 200e-6]
            y: [0, 200e-6]
            z: [-100e-6, 100e-6]
        frequency_ranges:
            x: [1, 5000]
            y: [1, 5000]
            z: [1, 1000]
        resolution_ranges:
            x: [1, 10000]
            y: [1, 10000]
            z: [2, 1000]
    """

    # config options
    _position_ranges = ConfigOption(name='position_ranges', missing='error')
    _frequency_ranges = ConfigOption(name='frequency_ranges', missing='error')
    _resolution_ranges = ConfigOption(name='resolution_ranges', missing='error')
    _spot_density = ConfigOption(name='spot_density', default=1e12/8)  # in 1/m²
    _spot_depth_range = ConfigOption(name='spot_depth_range', default=(-500e-9, 500e-9))
    _spot_size_dist = ConfigOption(name='spot_size_dist', default=(100e-9, 15e-9))
    _spot_amplitude_dist = ConfigOption(name='spot_amplitude_dist', default=(2e5, 4e4))
    _require_square_pixels = ConfigOption(name='require_square_pixels', default=False)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Scan process parameters
        self._scan_frequency = -1
        self._current_scan_ranges = [tuple(), tuple()]
        self._current_scan_axes = tuple()
        self._current_scan_resolution = tuple()
        self._current_position = dict()
        self._current_scan_settings = None
        self._scan_image = None

        # Try to simulate delays
        self._last_line_read = 0
        self._line_scan_time = 0

        # Randomized spot positions
        self._spots = dict()
        # "Hardware" constraints
        self._constraints = dict()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Set default process values
        self._current_position = {ax: min(rng) + (max(rng) - min(rng)) / 2 for ax, rng in
                                  self._position_ranges.items()}
        self._scan_image = np.zeros(self._current_scan_resolution)
        self._current_scan_settings = ScanSettings(
            axes=tuple(self._position_ranges)[:2],
            ranges=tuple(tuple(rng) for rng in tuple(self._position_ranges.values())[:2]),
            resolution=(100, 100),
            px_frequency=500,
            position_feedback=False,
            data_channels=('Photons',)
        )

        # Create fixed maps of spots for each scan axes configuration
        self._randomize_new_spots()

        self._last_line_read = 0
        self._line_scan_time = 0

        # Generate static constraints
        self._constraints = dict()
        self._constraints['axes_frequency_ranges'] = {
            ax: (min(rng), max(rng)) for ax, rng in self._frequency_ranges.items()
        }
        self._constraints['axes_position_ranges'] = {
            ax: (min(rng), max(rng)) for ax, rng in self._position_ranges.items()
        }
        self._constraints['axes_resolution_ranges'] = {
            ax: (min(rng), max(rng)) for ax, rng in self._resolution_ranges.items()
        }
        self._constraints['axes_units'] = {ax: 'm' for ax in self._position_ranges}
        self._constraints['data_channel_units'] = {'Photons': 'c/s'}
        self._constraints['square_px_only'] = bool(self._require_square_pixels)
        self._constraints['backscan_configurable'] = False

    def on_deactivate(self):
        """ Deactivate properly the scanner dummy.
        """
        self.reset()
        # free memory
        self._spots = dict()
        self._scan_image = None

    def _randomize_new_spots(self):
        self._spots = dict()
        for x_axis, x_range in self._position_ranges.items():
            for y_axis, y_range in self._position_ranges.items():
                if x_axis == y_axis:
                    continue
                x_min, x_max = min(x_range), max(x_range)
                y_min, y_max = min(y_range), max(y_range)
                print(x_range, y_range, self._spot_density)
                spot_count = int(round((x_max - x_min) * (y_max - y_min) * self._spot_density))

                # Fill in random spot information
                spot_dict = dict()
                # total number of spots
                spot_dict['count'] = spot_count
                # spot positions as (x, y) tuples
                spot_dict['pos'] = np.empty((spot_count, 2))
                spot_dict['pos'][:, 0] = np.random.uniform(x_min, x_max, spot_count)
                spot_dict['pos'][:, 1] = np.random.uniform(y_min, y_max, spot_count)
                # spot sizes as (sigma_x, sigma_y) tuples
                spot_dict['sigma'] = np.random.normal(
                    self._spot_size_dist[0], self._spot_size_dist[1], (spot_count, 2))
                # spot amplitudes
                spot_dict['amp'] = np.random.normal(
                    self._spot_amplitude_dist[0], self._spot_amplitude_dist[1], spot_count)
                # spot angle
                spot_dict['theta'] = np.random.uniform(0, np.pi, spot_count)

                # Add information to _spots dict
                self._spots[(x_axis, y_axis)] = spot_dict

    def reset(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('Scanning probe dummy has been reset.')
        return 0

    def get_constraints(self):
        """

        @return:
        """
        return self._constraints

    def configure_scan(self, settings):
        """ Configure the hardware with all parameters needed for a 1D or 2D scan.
        Do not start the scan or change module_state.
        Perform here all sanity checks against hardware constraints and return a parameter set with
        actually used values (logic will adapt to changes).

        The configured parameter set should be persistent in the hardware module until this method
        is called again (see also "get_scan_settings")

        @param ScanSettings settings: ScanSettings instance holding all parameters

        @return (int, ScanSettings): Failure indicator (0: success, -1: failure),
                                     ScanSettings instance with actually set parameters

        --------------------------------------------------------------------------------------------
        This method will probably remain (with only minor changes) in the actual scanning probe
        hardware interface. It means effort on this method implementation is not wasted.

        For this temporary solution you can completely ignore backscan parameters in the settings.
        Logic currently does not care how you trace back to the start of a scan line.
        --------------------------------------------------------------------------------------------
        """
        # Sanity checking
        if self.module_state() == 'locked':
            self.log.error('Unable to configure scan parameters while scan is running. '
                           'Stop scanning and try again.')
            return self._current_scan_settings.copy()
        if not set(settings.axes).issubset(self._position_ranges):
            self.log.error('Unknown axes names encountered. Valid axes are: {0}'
                           ''.format(set(self._position_ranges)))
            return self._current_scan_settings.copy()
        for i, ax in enumerate(settings.axes):
            pos_rng = self._position_ranges[ax]
            res_rng = self._resolution_ranges[ax]
            if min(settings.ranges[i]) < min(pos_rng) or max(settings.ranges[i]) > max(pos_rng):
                self.log.error(
                    'Scan range out of bounds for axis "{0}". Maximum possible range is: {1}'
                    ''.format(ax, list(pos_rng)))
                return self._current_scan_settings.copy()
            if settings.resolutions[i] < min(res_rng) or settings.resolutions[i] > max(res_rng):
                self.log.error(
                    'Scan resolution out of bounds for axis "{0}". Maximum possible range is: {1}'
                    ''.format(ax, list(res_rng)))
                return self._current_scan_settings.copy()
        fast_freq_range = self._frequency_ranges[settings.axes[0]]
        if settings.px_frequency < min(fast_freq_range) or settings.px_frequency > max(fast_freq_range):
            self.log.error(
                'Scan frequency out of bounds for fast axis "{0}". Maximum possible range is: {1}'
                ''.format(settings.axes[0], fast_freq_range))
            return self._current_scan_settings.copy()
        slow_freq_range = self._frequency_ranges[settings.axes[1]]
        slow_freq = settings.px_frequency / settings.resolutions[0]
        if slow_freq < min(slow_freq_range) or slow_freq > max(slow_freq_range):
            self.log.error(
                'Derived scan frequency out of bounds for slow axis "{0}". Maximum possible range '
                'is: {1}'.format(settings.axes[1], slow_freq_range))
            return self._current_scan_settings.copy()

        self._line_scan_time = settings.resolution[0] / settings.px_frequency
        self._scan_image = np.zeros(self._current_scan_resolution)
        self._current_scan_settings = settings.copy()
        return self._current_scan_settings.copy()

    def move_absolute(self, position, velocity=None):
        """ Move the scanning probe to an absolute position as fast as possible or with a defined
        velocity.
        Must wait and return after the movement has finished.

        Log error and return current target position if something fails or a scan is in progress.

        @param dict position: Contains absolute target positions (values) for axes (keys) to move
        @param dict velocity: optional, must contain same keys as position and specifies move
                              velocity in <axis_unit>/s

        @return dict: The new target position (values) for ALL axes (keys)
        """
        if self.module_state() == 'locked':
            self.log.error('Scanning in progress. Unable to move to position.')
        elif not set(position).issubset(self._position_ranges):
            self.log.error('Invalid axes encountered in position dict. Valid axes are: {0}'
                           ''.format(set(self._position_ranges)))
        else:
            if velocity is None:
                move_time = 0.01
            else:
                move_time = max(0.01, max(np.abs(pos - self._current_position[ax]) for ax, pos in
                                          position.items()) / velocity)
            time.sleep(move_time)
            self._current_position.update(position)
        return self._current_position

    def get_target(self):
        """ Get the current target position of the scanner
        (i.e. the theoretical/ideal position).

        @return dict: current target position (values) per axis (keys)
        """
        return self._current_position.copy()

    def lock_scanner(self):
        """ Change module state to 'locked' (by calling e.g. "self.module_state.lock()")
        Return success value if the module can be locked (i.e. it was in "idle" state before).
        Return error value if the module can not be locked (i.e. it was already locked).

        The module_state is used by the controlling logic module to determine if a scan is ongoing.
        More precisely it should be locked as long as not all scan data lines have been returned to
        the logic and direct movement commands are impossible.

        @return int: Error indicator (0: success, -1: failure)

        --------------------------------------------------------------------------------------------
        This method will certainly be removed in the proper interface.
        --------------------------------------------------------------------------------------------
        """
        if self.module_state() == 'locked':
            self.log.error('Unable to lock scanner and start scanning. Scan already in progress.')
            return -1
        self.module_state.lock()
        number_of_spots = self._spots[self._current_scan_settings.axes]['count']
        positions = self._spots[self._current_scan_settings.axes]['pos']
        amplitudes = self._spots[self._current_scan_settings.axes]['amp']
        sigmas = self._spots[self._current_scan_settings.axes]['sigma']
        thetas = self._spots[self._current_scan_settings.axes]['theta']

        x_values = np.linspace(self._current_scan_settings.ranges[0][0],
                               self._current_scan_settings.ranges[0][1],
                               self._current_scan_settings.resolution[0])
        y_values = np.linspace(self._current_scan_settings.ranges[1][0],
                               self._current_scan_settings.ranges[1][1],
                               self._current_scan_settings.resolution[1])
        xy_grid = np.meshgrid(x_values, y_values, indexing='ij')

        include_dist = self._spot_size_dist[0] + 5 * self._spot_size_dist[1]
        self._scan_image = np.random.uniform(0, 2e4, self._current_scan_settings.resolution)
        for i in range(number_of_spots):
            if positions[i][0] < self._current_scan_settings.ranges[0][0] - include_dist:
                continue
            if positions[i][0] > self._current_scan_settings.ranges[0][1] + include_dist:
                continue
            if positions[i][1] < self._current_scan_settings.ranges[1][0] - include_dist:
                continue
            if positions[i][1] > self._current_scan_settings.ranges[1][1] + include_dist:
                continue
            gauss = self.gaussian_2d(xy_grid,
                                     amp=amplitudes[i],
                                     pos=positions[i],
                                     sigma=sigmas[i],
                                     theta=thetas[i])
            self._scan_image += gauss

        self._last_line_read = time.time()
        return 0

    def unlock_scanner(self):
        """ See lock_scanner

        @return int: Error indicator (0: success, -1: failure)

        --------------------------------------------------------------------------------------------
        This method will certainly be removed in the proper interface.
        --------------------------------------------------------------------------------------------
        """
        if self.module_state() == 'idle':
            self.log.error('Unable to unlock scanner.')
            return -1
        return 0

    def get_scan_line(self, line_index):
        """ Return the scan data (for all configured data channels) for a single forward scan line
        with index "line_index" (starting at 0).
        The index is guaranteed to increase incrementally with each call and never occur twice.
        As soon as this method is called with the last index of a scan, the scan should be
        considered complete by the hardware module.
        This method will get called the same number of times as the configured slow axis resolution.

        All data arrays returned must have same length.

        In case of an error, return same length arrays (length 1 is ok) filled with -1 for each
        data channel.

        @return dict: one 1D numpy array of type np.float64 (values) for each data channel (keys)

        --------------------------------------------------------------------------------------------
        This method will certainly be removed in the proper interface.
        --------------------------------------------------------------------------------------------
        """
        if self.module_state() != 'locked':
            self.log.error()
            return {ch: -1 * np.ones((1, 1)) for ch in self._constraints['data_channel_units']}
        # Generate delay
        read_time = time.time()
        while read_time - self._last_line_read < self._line_scan_time:
            time.sleep(0.1)
            read_time = time.time()
        self._last_line_read = read_time
        # return line data
        return {tuple(self._constraints['data_channel_units'])[0]: self._scan_image[:, line_index]}

    @staticmethod
    def gaussian_2d(xy, amp, pos, sigma, theta=0, offset=0):
        x, y = xy
        sigx, sigy = sigma
        x0, y0 = pos
        a = np.cos(-theta) ** 2 / (2 * sigx ** 2) + np.sin(-theta) ** 2 / (2 * sigy ** 2)
        b = np.sin(2 * -theta) / (4 * sigy ** 2) - np.sin(2 * -theta) / (4 * sigx ** 2)
        c = np.sin(-theta) ** 2 / (2 * sigx ** 2) + np.cos(-theta) ** 2 / (2 * sigy ** 2)
        return offset + amp * np.exp(
            -(a * (x - x0) ** 2 + 2 * b * (x - x0) * (y - y0) + c * (y - y0) ** 2))
