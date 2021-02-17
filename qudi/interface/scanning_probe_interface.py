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


class ScanData:
    """
    Object representing all data associated to a SPM measurement.
    """

    def __init__(self, channels, scan_axes, scan_range, scan_resolution, scan_frequency,
                 position_feedback_axes=None):
        """

        @param ScannerChannel[] channels: ScannerChannel objects involved in this scan
        @param ScannerAxis[] scan_axes: ScannerAxis instances involved in the scan
        @param float[][2] scan_range: inclusive range for each scan axis
        @param int[] scan_resolution: planned number of points for each scan axis
        @param float scan_frequency: Scan pixel frequency of the fast axis
        @param ScannerAxis[] position_feedback_axes: optional, axes for which to acquire position
                                                     feedback during the scan.
        """
        # Sanity checking
        if not (0 < len(scan_axes) <= 2):
            raise ValueError('ScanData can only be used for 1D or 2D scans.')
        if len(channels) < 1:
            raise ValueError('At least one data channel must be specified for a valid scan.')
        if len(scan_axes) != len(scan_range):
            raise ValueError('Parameters "scan_axes" and "scan_range" must have same len. Given '
                             '{0:d} and {1:d}, respectively.'.format(len(scan_axes),
                                                                     len(scan_range)))
        if len(scan_axes) != len(scan_resolution):
            raise ValueError('Parameters "scan_axes" and "scan_resolution" must have same len. '
                             'Given {0:d} and {1:d}, respectively.'.format(len(scan_axes),
                                                                           len(scan_resolution)))
        if not all(isinstance(ax, ScannerAxis) for ax in scan_axes):
            raise TypeError(
                'Parameter "scan_axes" must be iterable containing only ScannerAxis objects')
        if not all(len(ax_range) == 2 for ax_range in scan_range):
            raise TypeError(
                'Parameter "scan_range" must be iterable containing only value pairs (len=2).')
        if not all(isinstance(res, int) for res in scan_resolution):
            raise TypeError(
                'Parameter "scan_resolution" must be iterable containing only integers.')
        if not all(isinstance(ch, ScannerChannel) for ch in channels):
            raise TypeError(
                'Parameter "channels" must be iterable containing only ScannerChannel objects.')
        if not all(np.issubdtype(ch.dtype, np.floating) for ch in channels):
            raise TypeError('channel dtypes must be either builtin or numpy floating types')

        self._scan_axes = tuple(scan_axes)
        self._scan_range = tuple((float(start), float(stop)) for (start, stop) in scan_range)
        self._scan_resolution = tuple(int(res) for res in scan_resolution)
        self._scan_frequency = float(scan_frequency)
        self._channels = tuple(channels)
        if position_feedback_axes is None:
            self._position_feedback_axes = None
        else:
            self._position_feedback_axes = tuple(position_feedback_axes)

        self._timestamp = None
        self._data = None
        self._position_data = None
        # TODO: Automatic interpolation onto rectangular grid needs to be implemented
        return

    def __copy__(self):
        new_inst = ScanData(channels=self._channels,
                            scan_axes=self._scan_axes,
                            scan_range=self._scan_range,
                            scan_resolution=self._scan_resolution,
                            scan_frequency=self._scan_frequency,
                            position_feedback_axes=self._position_feedback_axes)
        new_inst._timestamp = self._timestamp
        if self._data is not None:
            new_inst._data = self._data.copy()
        if self._position_data is not None:
            new_inst._position_data = self._position_data.copy()
        return new_inst

    def __deepcopy__(self, memodict={}):
        return self.copy()

    def __eq__(self, other):
        if not isinstance(other, ScanData):
            raise NotImplemented

        attrs = ('_timestamp', '_scan_frequency', '_scan_axes', '_scan_range', '_scan_resolution',
                 '_channels', '_position_feedback_axes', '_data', '_position_data', '_timestamp')
        return all(getattr(self, a) == getattr(other, a) for a in attrs)

    @property
    def scan_axes(self):
        return tuple(ax.name for ax in self._scan_axes)

    @property
    def scan_range(self):
        return self._scan_range

    @property
    def scan_resolution(self):
        return self._scan_resolution

    @property
    def scan_frequency(self):
        return self._scan_frequency

    @property
    def channels(self):
        return tuple(ch.name for ch in self._channels)

    @property
    def channel_units(self):
        return {ch.name: ch.unit for ch in self._channels}

    @property
    def axes_units(self):
        units = {ax.name: ax.unit for ax in self._scan_axes}
        if self.has_position_feedback:
            units.update({ax.name: ax.unit for ax in self._position_feedback_axes})
        return units

    @property
    def data(self):
        return self._data

    @property
    def position_data(self):
        return self._position_data

    @property
    def has_position_feedback(self):
        return bool(self._position_feedback_axes)

    @property
    def scan_dimension(self):
        return len(self._scan_axes)

    def new_scan(self, timestamp=None):
        """

        @param timestamp:
        """
        if timestamp is None:
            self._timestamp = datetime.datetime.now()
        elif isinstance(timestamp, datetime.datetime):
            self._timestamp = timestamp
        else:
            raise TypeError('Optional parameter "timestamp" must be datetime.datetime object.')

        if self.has_position_feedback:
            self._position_data = {ax.name: np.full(self._scan_resolution, np.nan) for ax in
                                   self._position_feedback_axes}
        else:
            self._position_data = None
        self._data = {
            ch.name: np.full(self._scan_resolution, np.nan, dtype=ch.dtype) for ch in self._channels
        }
        return

    def copy(self):
        new_inst = ScanData(channels=self._channels,
                            scan_axes=self._scan_axes,
                            scan_range=self._scan_range,
                            scan_resolution=self._scan_resolution,
                            scan_frequency=self._scan_frequency,
                            position_feedback_axes=self._position_feedback_axes)
        new_inst._timestamp = self._timestamp
        if self._data is not None:
            new_inst._data = {ch: arr.copy() for ch, arr in self._data.items()}
        if self._position_data is not None:
            new_inst._position_data = {ch: arr.copy() for ch, arr in self._position_data.items()}
        return new_inst

    def to_dict(self):
        dict_repr = {
            'scan_axes': tuple(ax.to_dict() for ax in self._scan_axes),
            'scan_range': self._scan_range,
            'scan_resolution': self._scan_resolution,
            'scan_frequency': self._scan_frequency,
            'channels': tuple(ch.to_dict() for ch in self._channels),
            'position_feedback_axes': None if self._position_feedback_axes is None else tuple(
                ax.to_dict() for ax in self._position_feedback_axes),
            'timestamp': None if self._timestamp is None else self._timestamp.timestamp(),
            'data': None if self._data is None else {ch: d.copy() for ch, d in self._data.items()},
            'position_data': None if self._position_data is None else {ax: d.copy() for ax, d in
                                                                       self._position_data.items()}
        }
        return dict_repr

    @classmethod
    def from_dict(cls, dict_repr):
        scan_axes = tuple(ScannerAxis.from_dict(ax) for ax in dict_repr['scan_axes'])
        if dict_repr['position_feedback_axes'] is None:
            position_feedback_axes = None
        else:
            position_feedback_axes = tuple(
                ScannerAxis.from_dict(ax) for ax in dict_repr['position_feedback_axes']
            )
        channels = tuple(ScannerChannel.from_dict(ch) for ch in dict_repr['channels'])
        new_inst = cls(channels=channels,
                       scan_axes=scan_axes,
                       scan_range=dict_repr['scan_range'],
                       scan_resolution=dict_repr['scan_resolution'],
                       scan_frequency=dict_repr['scan_frequency'],
                       position_feedback_axes=position_feedback_axes)
        new_inst._data = dict_repr['data']
        new_inst._position_data = dict_repr['position_data']
        if dict_repr['timestamp'] is not None:
            new_inst._timestamp = datetime.datetime.fromtimestamp(dict_repr['timestamp'])
        return new_inst


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
        # FIXME: Implement proper numpy type checking
        if not isinstance(dtype, type):
            raise TypeError('Parameter "dtype" must be numpy-compatible type.')
        self._name = name
        self._unit = unit
        self._dtype = dtype

    def __eq__(self, other):
        if not isinstance(other, ScannerChannel):
            raise NotImplemented
        attrs = ('_name', '_unit', '_dtype')
        return all(getattr(self, a) == getattr(other, a) for a in attrs)

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def dtype(self):
        return self._dtype

    def to_dict(self):
        return {'name': self._name, 'unit': self._unit, 'dtype': self._dtype.__name__}

    @classmethod
    def from_dict(cls, dict_repr):
        dict_repr['dtype'] = getattr(np, dict_repr['dtype'])
        return ScannerChannel(**dict_repr)


class ScannerAxis:
    """
    """

    def __init__(self, name, unit='', value_range=(-np.inf, np.inf), step_range=(0, np.inf),
                 resolution_range=(1, np.inf), frequency_range=(0, np.inf)):
        if not isinstance(name, str):
            raise TypeError('Parameter "name" must be of type str.')
        if name == '':
            raise ValueError('Parameter "name" must be non-empty str.')
        if not isinstance(unit, str):
            raise TypeError('Parameter "unit" must be of type str.')
        if not (len(value_range) == len(step_range) == len(resolution_range) == len(
                frequency_range) == 2):
            raise ValueError('Range parameters must be iterables of length 2')

        self._name = name
        self._unit = unit
        self._resolution_range = (int(min(resolution_range)), int(max(resolution_range)))
        self._step_range = (float(min(step_range)), float(max(step_range)))
        self._value_range = (float(min(value_range)), float(max(value_range)))
        self._frequency_range = (float(min(frequency_range)), float(max(frequency_range)))

    def __eq__(self, other):
        if not isinstance(other, ScannerAxis):
            raise NotImplemented
        attrs = ('_name',
                 '_unit',
                 '_resolution_range',
                 '_step_range',
                 '_value_range',
                 '_frequency_range')
        return all(getattr(self, a) == getattr(other, a) for a in attrs)

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def resolution_range(self):
        return self._resolution_range

    @property
    def min_resolution(self):
        return self._resolution_range[0]

    @property
    def max_resolution(self):
        return self._resolution_range[1]

    @property
    def step_range(self):
        return self._step_range

    @property
    def min_step(self):
        return self._step_range[0]

    @property
    def max_step(self):
        return self._step_range[1]

    @property
    def value_range(self):
        return self._value_range

    @property
    def min_value(self):
        return self._value_range[0]

    @property
    def max_value(self):
        return self._value_range[1]

    @property
    def frequency_range(self):
        return self._frequency_range

    @property
    def min_frequency(self):
        return self._frequency_range[0]

    @property
    def max_frequency(self):
        return self._frequency_range[1]

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

    def clip_frequency(self, freq):
        if freq < self.min_frequency:
            return self.min_frequency
        elif freq > self.max_frequency:
            return self.max_frequency
        return freq

    def to_dict(self):
        dict_repr = {'name': self._name,
                     'unit': self._unit,
                     'value_range': self._value_range,
                     'step_range': self._step_range,
                     'resolution_range': self._resolution_range,
                     'frequency_range': self._frequency_range}
        return dict_repr

    @classmethod
    def from_dict(cls, dict_repr):
        return ScannerAxis(**dict_repr)


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
