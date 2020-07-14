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
    def move_relative(self, distance, velocity=None):
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

    @property
    def axes(self):
        return self._axes

    @property
    def ranges(self):
        return self._ranges

    @property
    def resolution(self):
        return self._resolution

    @property
    def px_frequency(self):
        return self._px_frequency

    @property
    def position_feedback(self):
        return self._position_feedback

    @property
    def backscan_resolution(self):
        return self._backscan_resolution

    @property
    def data_channels(self):
        return self._data_channels

    @property
    def dimension(self):
        return len(self._axes)

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
                  'backscan_resolution': self._backscan_resolution}
        return params

    @classmethod
    def from_dict(cls, params):
        return cls(**params)


class ScanData:
    """
    Object representing all data associated to a SPM measurement.
    """

    def __init__(self, axes, channels, scan_axes, scan_range, scan_resolution, scan_frequency,
                 position_feedback=False):
        """

        @param ScannerAxis[] axes: all available ScannerAxis objects
        @param ScannerChannel[] channels: the names for each data channel
        @param str[] scan_axes: name of the axes involved in the scan
        @param float[][2] scan_range: inclusive range for each scan axis
        @param int[] scan_resolution: planned number of points for each scan axis
        @param float scan_frequency: Scan frequency of the fast axis
        @param bool position_feedback: optional, if the scanner position is saved for each pixel
        """
        # Sanity checking
        if len(scan_axes) != len(scan_range):
            raise ValueError('Parameters "scan_axes" and "scan_range" must have same len. Given '
                             '{0:d} and {1:d}, respectively.'.format(len(scan_axes),
                                                                     len(scan_range)))
        if len(scan_axes) != len(scan_resolution):
            raise ValueError('Parameters "scan_axes" and "scan_resolution" must have same len. '
                             'Given {0:d} and {1:d}, respectively.'.format(len(scan_axes),
                                                                           len(scan_resolution)))
        if not all(isinstance(ax, ScannerAxis) for ax in axes):
            raise TypeError('Parameter "axes" must be iterable containing only ScannerAxis objects')
        if not set(scan_axes).issubset(ax.name for ax in axes):
            raise ValueError('Parameter "scan_axes" ({0}) must contain a subset of available axes.'
                             ''.format(scan_axes))
        if not all(len(ax_range) == 2 for ax_range in scan_range):
            raise TypeError(
                'Parameter "scan_range" must be iterable containing only value pairs (len=2).')
        if not all(isinstance(res, (int, np.integer)) for res in scan_resolution):
            raise TypeError(
                'Parameter "scan_resolution" must be iterable containing only integers.')
        if not all(isinstance(ch, ScannerChannel) for ch in channels):
            raise TypeError(
                'Parameter "channels" must be iterable containing only ScannerChannel objects.')

        self._axes_units = {ax.name: ax.unit for ax in axes}
        self._scan_axes = tuple(str(ax) for ax in scan_axes)
        self._scan_range = {self._scan_axes[i]: (float(start), float(stop)) for i, (start, stop) in
                            enumerate(scan_range)}
        self._scan_resolution = {self._scan_axes[i]: int(res) for i, res in enumerate(scan_resolution)}
        self._channel_units = {ch.name: ch.unit for ch in channels}
        self._channel_dtypes = {ch.name: ch.dtype for ch in channels}
        self._position_feedback = bool(position_feedback)
        self._scan_frequency = float(scan_frequency)

        self.timestamp = None
        self._data = None
        self._position_data = None
        self._finished = False
        # TODO: Automatic interpolation onto rectangular grid needs to be implemented
        return

    @property
    def scan_axes(self):
        return self._scan_axes

    @property
    def axes(self):
        return tuple(self._axes_units)

    @property
    def axes_units(self):
        return self._axes_units.copy()

    @property
    def scan_range(self):
        return self._scan_range.copy()

    @property
    def scan_resolution(self):
        return self._scan_resolution.copy()

    @property
    def data_channels(self):
        return tuple(self._channel_units)

    @property
    def data_channel_units(self):
        return self._channel_units.copy()

    @property
    def scan_frequency(self):
        return self._scan_frequency

    @property
    def data(self):
        if self._data is not None:
            return self._data.copy()
        return None

    @property
    def position_data(self):
        if self._position_feedback and self._position_data is not None:
            return self._position_data.copy()
        return None

    @property
    def finished(self):
        return self._finished

    def new_data(self, timestamp=None):
        """

        @param timestamp:
        """
        print('NEW DATA CALLED')
        if timestamp is None:
            self.timestamp = datetime.datetime.now()
        elif isinstance(timestamp, datetime.datetime):
            self.timestamp = timestamp
        else:
            raise TypeError('Parameter "timestamp" must be datetime.datetime object.')

        scan_size = tuple(self._scan_resolution[ax] for ax in self._scan_axes)

        if self._position_feedback:
            self._position_data = {ax: np.full(scan_size, np.nan) for ax in self._axes_units}
        else:
            self._position_data = None
        self._data = {ch: np.full(scan_size, np.nan, dtype=dtype) for ch, dtype in
                      self._channel_dtypes.items()}
        self._finished = False
        return

    def add_line_data(self, data, line_index, start_index=0, position_data=None):
        if set(data) != set(self._channel_units):
            raise KeyError('data dict must contain all available data channels {0}.'
                           ''.format(tuple(self._channel_units)))

        stop_index = len(data[tuple(data)[0]]) + start_index

        if self._position_feedback and position_data is not None:
            if set(position_data) != set(self._axes_units):
                raise KeyError('position_data dict must contain all available axes {0}.'
                               ''.format(tuple(self._axes_units)))
            for ax, arr in position_data.items():
                self._position_data[ax][start_index:stop_index, line_index] = arr

        for ch, arr in data.items():
            self._data[ch][start_index:stop_index, line_index] = arr
        resolution = (self._scan_resolution[self._scan_axes[0]],
                      self._scan_resolution[self._scan_axes[1]])
        if line_index == (resolution[1] - 1) and stop_index >= resolution[0]:
            self._finished = True
        return


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
                 max_step=np.inf, min_resolution=1, max_resolution=np.inf, min_frequency=0,
                 max_frequency=np.inf):
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
        if max_frequency < min_frequency:
            raise ValueError('Parameter "max_frequency" must be >= "min_frequency".')
        self._name = name
        self._unit = unit
        self._resolution_bounds = (int(min_resolution), int(max_resolution))
        self._step_bounds = (float(min_step), float(max_step))
        self._value_bounds = (float(min_value), float(max_value))
        self._frequency_bounds = (float(min_frequency), float(max_frequency))

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

    @property
    def frequency_bounds(self):
        return self._frequency_bounds

    @property
    def min_frequency(self):
        return self._frequency_bounds[0]

    @property
    def max_frequency(self):
        return self._frequency_bounds[1]

    def clip_value(self, value):
        if value < self.min_value:
            return self.min_value
        elif value > self.max_value:
            return self.max_value
        return value

    def clip_resolution(self, res):
        if res < self.min_resolution:
            return self.min_resolution
        elif res > self.max_resolution:
            return self.max_resolution
        return res

    def copy(self):
        return ScannerAxis(name=self._name,
                           unit=self._unit,
                           min_value=self.min_value,
                           max_value=self.max_value,
                           min_step=self.min_step,
                           max_step=self.max_step,
                           min_resolution=self.min_resolution,
                           max_resolution=self.max_resolution,
                           min_frequency=self.min_frequency,
                           max_frequency=self.max_frequency)


class ScanConstraints:
    """
    """

    def __init__(self, axes, channels, backscan_configurable, has_position_feedback,
                 square_px_only):
        """
        """
        if not all(isinstance(ax, ScannerAxis) for ax in axes):
            raise TypeError('Parameter "axes" must be of type ScannerAxis.')
        if not all(isinstance(ch, ScannerChannel) for ch in channels):
            raise TypeError('Parameter "channels" must be of type ScannerChannel.')
        if not isinstance(backscan_configurable, bool):
            raise TypeError('Parameter "backscan_configurable" must be of type bool.')
        if not isinstance(has_position_feedback, bool):
            raise TypeError('Parameter "has_position_feedback" must be of type bool.')
        if not isinstance(square_px_only, bool):
            raise TypeError('Parameter "square_px_only" must be of type bool.')
        self._axes = {ax.name: ax for ax in axes}
        self._channels = {ch.name: ch for ch in channels}
        self._backscan_configurable = bool(backscan_configurable)
        self._has_position_feedback = bool(has_position_feedback)
        self._square_px_only = bool(square_px_only)

    @property
    def axes(self):
        return self._axes.copy()

    @property
    def channels(self):
        return self._channels.copy()

    @property
    def backscan_configurable(self):
        return self._backscan_configurable

    @property
    def has_position_feedback(self):
        return self._has_position_feedback

    @property
    def square_px_only(self):
        return self._square_px_only
