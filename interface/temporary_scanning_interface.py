# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for scanning probe hardware.
This file is only a temporary fix to interface LSM scanning hardware with the "old" confocal logic
(via a specialized interfuse).

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

import datetime
import numpy as np
from qtpy import QtCore

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class TemporaryScanningInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the connection between LSMConfocalInterfuse and LSM
    hardware module.
    """

    @abstract_interface_method
    def get_constraints(self):
        """ Get hardware constraints/limitations.

            example constraints (all the following keys must be present):

                constraints = dict()
                constraints['axes_frequency_ranges'] = {'x': (0, 1000),  # in Hz
                                                        'y': (0, 1000),  # in Hz
                                                        'z': (0, 500)    # in Hz
                                                        }
                constraints['axes_position_ranges'] = {'x': (0, 100e-6),     # in m
                                                       'y': (0, 100e-6),     # in m
                                                       'z': (-50e-6, 50e-6)  # in m
                                                       }
                constraints['axes_resolution_ranges'] = {'x': (1, 65536),  # in px
                                                         'y': (1, 65536),  # in px
                                                         'z': (1, 65536)   # in px
                                                         }
                constraints['axes_units'] = {'x': 'm', 'y': 'm', 'z': 'm'}
                constraints['data_channel_units'] = {'Photons': 'c/s', 'Lab Monkey': 'students/h'}
                constraints['square_px_only'] = False  # force pixels to be always square
                constraints['backscan_configurable'] = False  # allow user-configurable backscan

        @return dict: scanner hardware constraints
        """
        pass

    @abstract_interface_method
    def reset(self):
        """ Complete reset of the hardware state.

        @return int: Error value (0: success, -1: error)
        """
        pass

    @abstract_interface_method
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
        pass

    @abstract_interface_method
    def get_scan_settings(self):
        """ Returns the current scan settings as ScanSettings object.
        As long as "configure_scan" is not called again, this method will always return the same
        parameters independent of the scan run state.

        @return ScanSettings: Scan parameters defining a scanning probe run
        """
        pass

    @abstract_interface_method
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
        pass

    # @abstract_interface_method
    # def move_relative(self, position, velocity=None):
    #     """ Move the scanning probe by a relative distance from the current target position as fast
    #     as possible or with a defined velocity.
    #     Must wait and return after the movement has finished.
    #
    #     Log error and return current target position if something fails or a scan is in progress.
    #
    #     @param dict position: Contains relative distance (values) for axes (keys) to move
    #     @param dict velocity: optional, must contain same keys as position and specifies move
    #                           velocity in <axis_unit>/s
    #
    #     @return dict: The new target position (values) for ALL axes (keys)
    #     """
    #     pass

    @abstract_interface_method
    def get_target(self):
        """ Get the current target position of the scanner
        (i.e. the theoretical/ideal position).

        @return dict: current target position (values) per axis (keys)
        """
        pass

    # @abstract_interface_method
    # def get_position(self):
    #     """ Get a snapshot of the actual scanner position (i.e. from position feedback sensors).
    #     For the same target this value can fluctuate according to the scanners positioning accuracy.
    #
    #     For scanning devices that do not have position feedback sensors, simply return the target
    #     position (see also: ScanningProbeInterface.get_target).
    #
    #     @return dict: current position (values) per axis (keys)
    #     """
    #     pass

    @abstract_interface_method
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
        pass

    @abstract_interface_method
    def unlock_scanner(self):
        """ See lock_scanner

        @return int: Error indicator (0: success, -1: failure)

        --------------------------------------------------------------------------------------------
        This method will certainly be removed in the proper interface.
        --------------------------------------------------------------------------------------------
        """
        pass

    @abstract_interface_method
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
        pass

    # @abstract_interface_method
    # def emergency_stop(self):
    #     """
    #     --------------------------------------------------------------------------------------------
    #     Can be ignored for now.
    #     --------------------------------------------------------------------------------------------
    #     """
    #     pass


class ScanSettings:
    """ Data object holding the information needed for configuration of a scanning probe
    measurement run.
    """

    def __init__(self, axes, ranges, resolution, px_frequency, position_feedback,
                 data_channels=None, backscan_resolution=None):
        if len(axes) != len(ranges) or len(axes) != len(resolution):
            raise ValueError(
                'Parameters "axes", "ranges" and "resolution" must be iterables of same length.')
        for rng in ranges:
            if len(rng) != 2:
                raise ValueError(
                    'Each element of parameter "ranges" must be an iterable of length 2.')
        if px_frequency <= 0:
            raise ValueError('Parameter "px_frequency" must have a value > 0.')
        if any(res <= 0 for res in resolution) or (backscan_resolution is not None and backscan_resolution <= 0):
            raise ValueError('Scan axis resolutions must be integer values >= 1')

        # Actual parameter set
        self._axes = tuple(str(ax) for ax in axes)
        self._ranges = tuple((min(rng), max(rng)) for rng in ranges)
        self._resolution = tuple(int(res) for res in resolution)
        self._px_frequency = float(px_frequency)
        self._position_feedback = bool(position_feedback)
        self._backscan_resolution = None if backscan_resolution is None else int(
            backscan_resolution)
        self._data_channels = None if not data_channels else tuple(data_channels)

        # Flag to indicate a change of parameter values outside __init__
        self.has_changed = False

    @property
    def axes(self):
        return self._axes

    @axes.setter
    def axes(self, new_axes):
        self._axes = tuple(str(ax) for ax in new_axes)

    @property
    def ranges(self):
        return self._ranges

    @ranges.setter
    def ranges(self, new_ranges):
        for rng in new_ranges:
            if len(rng) != 2:
                raise ValueError(
                    'Each element of parameter "ranges" must be an iterable of length 2.')
        self._ranges = tuple((min(rng), max(rng)) for rng in new_ranges)

    @property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, new_resolution):
        self._resolution = tuple(int(res) for res in new_resolution)

    @property
    def px_frequency(self):
        return self._px_frequency

    @px_frequency.setter
    def px_frequency(self, new_freq):
        self._px_frequency = float(new_freq)

    @property
    def position_feedback(self):
        return self._position_feedback

    @position_feedback.setter
    def position_feedback(self, flag):
        self._position_feedback = bool(flag)

    @property
    def backscan_resolution(self):
        return self._backscan_resolution

    @backscan_resolution.setter
    def backscan_resolution(self, new_resolution):
        self._backscan_resolution = None if new_resolution is None else int(new_resolution)

    @property
    def data_channels(self):
        return self._data_channels

    @data_channels.setter
    def data_channels(self, new_channels):
        self._data_channels = None if not new_channels else tuple(new_channels)

    @property
    def is_valid(self):
        return len(self._axes) == len(self._resolution) == len(self._ranges)

    @property
    def dimension(self):
        if self.is_valid:
            return len(self._axes)
        return -1

    def copy(self, **kwargs):
        params = self.to_dict()
        params.update(kwargs)
        return self.from_dict(params)

    def to_dict(self):
        params = {'axes': self._axes,
                  'ranges': self._ranges,
                  'resolution': self._resolution,
                  'px_frequency': self._px_frequency,
                  'position_feedback': self._position_feedback,
                  'data_channels': self._data_channels,
                  'backscan_resolution': self._backscan_resolution
                  }
        return params

    @classmethod
    def from_dict(cls, params):
        return cls(**params)


# ToDo: Not used for now...
# class ScanData(QtCore.QObject):
#     """
#     Object representing all data associated to a SPM measurement.
#     """
#     # TODO: Automatic interpolation of irregular positional data onto rectangular grid
#
#     sigDataChanged = QtCore.Signal()
#
#     def __init__(self, axes_units, data_channel_units, scan_settings, timestamp=None):
#         """
#
#         @param dict axes_units: physical units for ALL axes. (No unit prefix)
#         @param dict data_channel_units: physical units for ALL data channels. (No unit prefix)
#         @param ScanSettings scan_settings: ScanSettings instance containing all scan parameters
#         @param datetime.datetime timestamp: optional, timestamp used for creation time
#         """
#         # Sanity checking
#         if not scan_settings.is_valid:
#             raise ValueError('ScanSettings instance contains invalid parameters.')
#         if not set(scan_settings.axes).issubset(axes_units):
#             raise ValueError('Invalid scan axes encountered. Valid axes are: {0}'
#                              ''.format(set(axes_units)))
#         if not set(scan_settings.data_channels).issubset(data_channel_units):
#             raise ValueError('Invalid data channels encountered. Valid channels are: {0}'
#                              ''.format(set(data_channel_units)))
#         if timestamp is not None and not isinstance(timestamp, datetime.datetime):
#             raise TypeError('Timestamp must be a datetime.datetime instance. You can create a '
#                             'timestamp by calling e.g. "datetime.datetime.now()"')
#
#         self._axes_units = axes_units.copy()
#         self._data_channel_units = data_channel_units.copy()
#         self._scan_settings = scan_settings.copy()
#         self.timestamp = datetime.datetime.now() if timestamp is None else timestamp
#
#         self.__data_size = int(np.prod(self._scan_settings.resolution))
#         if self._scan_settings.backscan_resolution is None:
#             self.__backscan_data_size = None
#         else:
#             self.__backscan_data_size = int(np.prod(
#                 (self._scan_settings.backscan_resolution, *self._scan_settings.resolution[1:])))
#         self.__current_data_index = 0
#
#         # scan data
#         self._data = {ch: np.zeros(self.__data_size) for ch in self._scan_settings.data_channels}
#         if self.__backscan_data_size is None:
#             self._backscan_data = None
#         else:
#             self._backscan_data = {ch: np.zeros(self.__backscan_data_size) for ch in
#                                    self._scan_settings.data_channels}
#         # position data
#         if self._scan_settings.position_feedback:
#             self._position_data = {ax: np.zeros(self.__data_size) for ax in self._axes_units}
#             if self.__backscan_data_size is None:
#                 self._backscan_position_data = None
#             else:
#                 self._backscan_position_data = {ax: np.zeros(self.__backscan_data_size) for ax in
#                                                 self._axes_units}
#         else:
#             self._position_data = None
#             self._backscan_position_data = None
#         return
#
#     @property
#     def scan_axes(self):
#         return self._scan_settings.axes
#
#     @property
#     def scan_ranges(self):
#         return self._scan_settings.ranges
#
#     @property
#     def scan_resolution(self):
#         return self._scan_settings.resolution
#
#     @property
#     def backscan_resolution(self):
#         if self._scan_settings.backscan_resolution is None:
#             return None
#         return (self._scan_settings.backscan_resolution, *self._scan_settings.resolution[1:])
#
#     @property
#     def scan_size(self):
#         return self.__data_size
#
#     @property
#     def backscan_size(self):
#         return self.__backscan_data_size
#
#     @property
#     def data_channels(self):
#         return self._scan_settings.data_channels
#
#     @property
#     def data_channel_units(self):
#         return self._data_channel_units.copy()
#
#     @property
#     def data(self):
#         return self._data
#
#     @property
#     def backscan_data(self):
#         return self._backscan_data
#
#     @property
#     def position_data(self):
#         return self._position_data
#
#     @property
#     def backscan_position_data(self):
#         return self._backscan_position_data
#
#     def add_data(self, data, position=None):
#         if position is None:
#             if self._scan_settings.position_feedback:
#                 raise Exception('Positional data missing.')
#         elif set(position) != set(self._axes_units):
#             raise KeyError('position dict must contain all available axes {0}.'
#                            ''.format(set(self._axes_units)))
#         if set(data) != set(self._data_channel_units):
#             raise KeyError('data dict must contain all available channels {0}.'
#                            ''.format(set(self._data_channel_units)))
#
#         size = len(data[tuple(data)[0]])
#         stop_index = self.__current_data_index + size
#         # Extend pre-allocated data arrays if the amount of data exceeds the planned size to avoid
#         # data loss.
#         # ToDo: Maybe implement that. Throw error for now.
#         if stop_index > self.__data_size:
#             raise Exception('Scan data exceeding pre-allocated data array.')
#             # append_size = stop_index - self.__data_size
#             # print('Ooops... Planned scan size of {0:d} points exceeded by {1:d} points.'
#             #       ''.format(self.__data_size, append_size))
#             # for channel in self._channels:
#             #     self._data[channel] = np.append(self._data[channel], np.zeros(append_size))
#             # for axis in self._axes:
#             #     self._position_data[axis] = np.append(self._position_data[axis],
#             #                                           np.zeros(append_size))
#             # self.__data_size += append_size
#
#         # Add channel data
#         for channel, data_arr in data.items():
#             self._data[channel][self.__current_data_index:stop_index] = data_arr
#         # Add positional data
#         if position is not None:
#             for axis, pos_arr in position.items():
#                 self._position_data[axis][self.__current_data_index:stop_index] = pos_arr
#
#         self.__current_data_index = stop_index
#         return
#
#     def add_data_point(self, data, position=None):
#         start_index = self.__current_data_index
#         stop_index = self.__current_data_index + 1
#         return self._add_data(position, data, start_index, stop_index)
