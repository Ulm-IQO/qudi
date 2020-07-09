# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for scanning probe hardware.

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

from qudi.core.interface import abstract_interface_method
from qudi.core.meta import InterfaceMetaclass


class ScanningProbeInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for a scanning probe device

    A scanner device is hardware that can move multiple axes.
    """

    @abstract_interface_method
    def get_constraints(self):
        """ Get hardware constraints/limitations.

        @return dict: scanner constraints
        """
        pass

    @abstract_interface_method
    def reset(self):
        """ Hard reset of the hardware.
        """
        pass

    @abstract_interface_method
    def configure_scan(self, settings):
        """ Configure the hardware with all parameters needed for a 1D or 2D scan.

        @param ScanSettings settings: ScanSettings instance holding all parameters

        @return (bool, ScanSettings): Failure indicator (fail=True),
                                      altered ScanSettings instance (same as "settings")
        """
        pass

    @abstract_interface_method
    def move_absolute(self, position, velocity=None):
        """ Move the scanning probe to an absolute position as fast as possible or with a defined
        velocity.

        Log error and return current target position if something fails or a scan is in progress.
        """
        pass

    @abstract_interface_method
    def move_relative(self, position, velocity=None):
        """ Move the scanning probe by a relative distance from the current target position as fast
        as possible or with a defined velocity.

        Log error and return current target position if something fails or a 1D/2D scan is in
        progress.


        """
        pass

    @abstract_interface_method
    def get_target(self):
        """ Get the current target position of the scanner hardware
        (i.e. the "theoretical" position).

        @return dict: current target position per axis.
        """
        pass

    @abstract_interface_method
    def get_position(self):
        """ Get a snapshot of the actual scanner position (i.e. from position feedback sensors).
        For the same target this value can fluctuate according to the scanners positioning accuracy.

        For scanning devices that do not have position feedback sensors, simply return the target
        position (see also: ScanningProbeInterface.get_target).

        @return dict: current position per axis.
        """
        pass

    @abstract_interface_method
    def start_scan(self):
        """

        @return (bool): Failure indicator (fail=True)
        """
        pass

    @abstract_interface_method
    def stop_scan(self):
        """

        @return bool: Failure indicator (fail=True)
        """
        pass

    @abstract_interface_method
    def get_scan_data(self):
        """

        @return (bool, ScanData): Failure indicator (fail=True), ScanData instance used in the scan
        """
        pass

    @abstract_interface_method
    def emergency_stop(self):
        """

        @return:
        """
        pass


class ScanSettings:
    """ Data object holding the information needed for configuration of a scanning probe
    measurement run.

    Should be created and handed to the hardware by the measurement logic. First
    creation should be entirely done in __init__ (with all parameters).
    The hardware module should change invalid/dependent/rounded parameter values via properties in
    order to implicitly flag a change for the logic to react to.
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
        new_axes = tuple(str(ax) for ax in new_axes)
        self.has_changed = new_axes != self._axes
        self._axes = new_axes

    @property
    def ranges(self):
        return self._ranges

    @ranges.setter
    def ranges(self, new_ranges):
        for rng in new_ranges:
            if len(rng) != 2:
                raise ValueError(
                    'Each element of parameter "ranges" must be an iterable of length 2.')
        new_ranges = tuple((min(rng), max(rng)) for rng in new_ranges)
        self.has_changed = new_ranges != self._ranges
        self._ranges = new_ranges

    @property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, new_resolution):
        new_resolution = tuple(int(res) for res in new_resolution)
        self.has_changed = new_resolution != self._resolution
        self._resolution = new_resolution

    @property
    def px_frequency(self):
        return self._px_frequency

    @px_frequency.setter
    def px_frequency(self, new_freq):
        new_freq = float(new_freq)
        self.has_changed = new_freq != self._px_frequency
        self._px_frequency = new_freq

    @property
    def position_feedback(self):
        return self._position_feedback

    @position_feedback.setter
    def position_feedback(self, flag):
        flag = bool(flag)
        self.has_changed = flag != self._position_feedback
        self._position_feedback = flag

    @property
    def backscan_resolution(self):
        return self._backscan_resolution

    @backscan_resolution.setter
    def backscan_resolution(self, new_resolution):
        new_resolution = None if new_resolution is None else int(new_resolution)
        self.has_changed = new_resolution != self._backscan_resolution
        self._backscan_resolution = new_resolution

    @property
    def data_channels(self):
        return self._data_channels

    @data_channels.setter
    def data_channels(self, new_channels):
        new_channels = None if not new_channels else tuple(new_channels)
        self.has_changed = new_channels != self._data_channels
        self._data_channels = new_channels

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


class ScanData:
    """
    Object representing all data associated to a SPM measurement.
    """
    # TODO: Automatic interpolation of irregular positional data onto rectangular grid

    def __init__(self, axes_units, data_channel_units, scan_settings, timestamp=None):
        """

        @param dict axes_units: physical units for ALL axes. (No unit prefix)
        @param dict data_channel_units: physical units for ALL data channels. (No unit prefix)
        @param ScanSettings scan_settings: ScanSettings instance containing all scan parameters
        @param datetime.datetime timestamp: optional, timestamp used for creation time
        """
        # Sanity checking
        if not scan_settings.is_valid:
            raise ValueError('ScanSettings instance contains invalid parameters.')
        if not set(scan_settings.axes).issubset(axes_units):
            raise ValueError('Invalid scan axes encountered. Valid axes are: {0}'
                             ''.format(set(axes_units)))
        if not set(scan_settings.data_channels).issubset(data_channel_units):
            raise ValueError('Invalid data channels encountered. Valid channels are: {0}'
                             ''.format(set(data_channel_units)))
        if timestamp is not None and not isinstance(timestamp, datetime.datetime):
            raise TypeError('Timestamp must be a datetime.datetime instance. You can create a '
                            'timestamp by calling e.g. "datetime.datetime.now()"')

        self._axes_units = axes_units.copy()
        self._data_channel_units = data_channel_units.copy()
        self._scan_settings = scan_settings.copy()
        self.timestamp = datetime.datetime.now() if timestamp is None else timestamp

        self.__data_size = int(np.prod(self._scan_settings.resolution))
        if self._scan_settings.backscan_resolution is None:
            self.__backscan_data_size = None
        else:
            self.__backscan_data_size = int(np.prod(
                (self._scan_settings.backscan_resolution, *self._scan_settings.resolution[1:])))
        self.__current_data_index = 0

        # scan data
        self._data = {ch: np.zeros(self.__data_size) for ch in self._scan_settings.data_channels}
        if self.__backscan_data_size is None:
            self._backscan_data = None
        else:
            self._backscan_data = {ch: np.zeros(self.__backscan_data_size) for ch in
                                   self._scan_settings.data_channels}
        # position data
        if self._scan_settings.position_feedback:
            self._position_data = {ax: np.zeros(self.__data_size) for ax in self._axes_units}
            if self.__backscan_data_size is None:
                self._backscan_position_data = None
            else:
                self._backscan_position_data = {ax: np.zeros(self.__backscan_data_size) for ax in
                                                self._axes_units}
        else:
            self._position_data = None
            self._backscan_position_data = None
        return

    @property
    def scan_axes(self):
        return self._scan_settings.axes

    @property
    def scan_ranges(self):
        return self._scan_settings.ranges

    @property
    def scan_resolution(self):
        return self._scan_settings.resolution

    @property
    def backscan_resolution(self):
        if self._scan_settings.backscan_resolution is None:
            return None
        return (self._scan_settings.backscan_resolution, *self._scan_settings.resolution[1:])

    @property
    def scan_size(self):
        return self.__data_size

    @property
    def backscan_size(self):
        return self.__backscan_data_size

    @property
    def data_channels(self):
        return self._scan_settings.data_channels

    @property
    def data_channel_units(self):
        return self._data_channel_units.copy()

    @property
    def data(self):
        return self._data

    @property
    def backscan_data(self):
        return self._backscan_data

    @property
    def position_data(self):
        return self._position_data

    @property
    def backscan_position_data(self):
        return self._backscan_position_data

    def add_data(self, data, position=None):
        if position is None:
            if self._scan_settings.position_feedback:
                raise Exception('Positional data missing.')
        elif set(position) != set(self._axes_units):
            raise KeyError('position dict must contain all available axes {0}.'
                           ''.format(set(self._axes_units)))
        if set(data) != set(self._data_channel_units):
            raise KeyError('data dict must contain all available channels {0}.'
                           ''.format(set(self._data_channel_units)))

        size = len(data[tuple(data)[0]])
        stop_index = self.__current_data_index + size
        # Extend pre-allocated data arrays if the amount of data exceeds the planned size to avoid
        # data loss.
        # ToDo: Maybe implement that. Throw error for now.
        if stop_index > self.__data_size:
            raise Exception('Scan data exceeding pre-allocated data array.')
            # append_size = stop_index - self.__data_size
            # print('Ooops... Planned scan size of {0:d} points exceeded by {1:d} points.'
            #       ''.format(self.__data_size, append_size))
            # for channel in self._channels:
            #     self._data[channel] = np.append(self._data[channel], np.zeros(append_size))
            # for axis in self._axes:
            #     self._position_data[axis] = np.append(self._position_data[axis],
            #                                           np.zeros(append_size))
            # self.__data_size += append_size

        # Add channel data
        for channel, data_arr in data.items():
            self._data[channel][self.__current_data_index:stop_index] = data_arr
        # Add positional data
        if position is not None:
            for axis, pos_arr in position.items():
                self._position_data[axis][self.__current_data_index:stop_index] = pos_arr

        self.__current_data_index = stop_index
        return

    def add_data_point(self, data, position=None):
        start_index = self.__current_data_index
        stop_index = self.__current_data_index + 1
        return self._add_data(position, data, start_index, stop_index)


class ScannerChannel:
    """
    """
    def __init__(self, name, unit='', dtype=np.float64):
        if not isinstance(name, str):
            raise TypeError('Parameter "name" must be of type str.')
        if len(name) < 1:
            raise ValueError('Parameter "name" must be non-empty str.')
        if not isinstance(unit, str):
            raise TypeError('Parameter "unit" must be of type str.')
        if not isinstance(dtype, type):
            raise TypeError('Parameter "dtype" must be numpy-compatible type.')
        self._name = name
        self._unit = unit
        self._dtype = dtype

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def dtype(self):
        return self._dtype

    def copy(self):
        return ScannerChannel(name=self._name, unit=self._unit, dtype=self._dtype)


class ScannerAxis:
    """
    """

    def __init__(self, name, unit='', min_value=-np.inf, max_value=np.inf, min_step=-np.inf,
                 max_step=np.inf, min_resolution=1, max_resolution=np.inf):
        if not isinstance(name, str):
            raise TypeError('Parameter "name" must be of type str.')
        if len(name) < 1:
            raise ValueError('Parameter "name" must be non-empty str.')
        if not isinstance(unit, str):
            raise TypeError('Parameter "unit" must be of type str.')
        if not isinstance(min_resolution, int):
            raise TypeError('Parameter "min_resolution" must be of type int.')
        if not isinstance(max_resolution, int):
            raise TypeError('Parameter "max_resolution" must be of type int.')
        if max_resolution < min_resolution:
            raise ValueError('Parameter "max_resolution" must be >= "min_resolution".')
        if max_step < min_step:
            raise ValueError('Parameter "max_step" must be >= "min_step".')
        if max_value < min_value:
            raise ValueError('Parameter "max_value" must be >= "min_value".')
        self._name = name
        self._unit = unit
        self._resolution_bounds = (int(min_resolution), int(max_resolution))
        self._step_bounds = (float(min_step), float(max_step))
        self._value_bounds = (float(min_value), float(max_value))

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def resolution_bounds(self):
        return self._resolution_bounds

    @property
    def min_resolution(self):
        return self._resolution_bounds[0]

    @property
    def max_resolution(self):
        return self._resolution_bounds[1]

    @property
    def step_bounds(self):
        return self._step_bounds

    @property
    def min_step(self):
        return self._step_bounds[0]

    @property
    def max_step(self):
        return self._step_bounds[1]

    @property
    def value_bounds(self):
        return self._value_bounds

    @property
    def min_value(self):
        return self._value_bounds[0]

    @property
    def max_value(self):
        return self._value_bounds[1]

    def copy(self):
        return ScannerAxis(name=self._name,
                           unit=self._unit,
                           min_value=self.min_value,
                           max_value=self.max_value,
                           min_step=self.min_step,
                           max_step=self.max_step,
                           min_resolution=self.min_resolution,
                           max_resolution=self.max_resolution)


class ScanConstraints:
    """
    """
    def __init__(self, constraints=None):
        """ Copy constructor
        """
        self.data_channels
        if isinstance(constraints, ScanConstraints):
