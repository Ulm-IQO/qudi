# -*- coding: utf-8 -*-

"""
ToDo: Document
This file contains a dummy hardware module for the

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

from abc import abstractmethod
from qudi.core.module import Base
from qudi.util.helpers import in_range
from qudi.util.enums import SamplingOutputMode


class FiniteSamplingOutputInterface(Base):
    """
    ToDo: Document
    """

    @property
    @abstractmethod
    def constraints(self):
        """
        ToDo: Document
        """
        pass

    @property
    @abstractmethod
    def active_channels(self):
        """ Names of all currently active channels.

        @return frozenset: The active channel name strings as set
        """
        pass

    @property
    @abstractmethod
    def sample_rate(self):
        """ The sample rate (in Hz) at which the samples will be emitted.

        @return float: The current sample rate in Hz
        """
        pass

    @property
    @abstractmethod
    def frame_size(self):
        """ Currently set number of samples per channel to emit for each data frame.

        @return int: Number of samples per frame
        """
        pass

    @property
    @abstractmethod
    def output_mode(self):
        """ Currently set output mode.

        @return SamplingOutputMode: Enum representing the currently active output mode
        """
        pass

    @property
    @abstractmethod
    def samples_in_buffer(self):
        """ Current number of samples per channel still pending to be emitted.

        @return int: Number of pending samples to be emitted
        """
        pass

    @abstractmethod
    def set_sample_rate(self, rate):
        """ Will set the sample rate to a new value.

        @param float rate: The sample rate to set
        """
        pass

    @abstractmethod
    def set_active_channels(self, channels):
        """ Will set the currently active channels. All other channels will be deactivated.

        @param iterable(str) channels: Iterable of channel names to set active.
        """
        pass

    @abstractmethod
    def set_frame_data(self, data):
        """ Fills the frame buffer for the next data frame to be emitted. Data must be a dict
        containing exactly all active channels as keys with corresponding sample data as values.

        If <output_mode> is SamplingOutputMode.JUMP_LIST, the values must be 1D numpy.ndarrays
        containing the entire data frame.
        If <output_mode> is SamplingOutputMode.EQUIDISTANT_SWEEP, the values must be iterables of
        length 3 representing the entire data frame to be constructed with numpy.linspace(),
        i.e. (start, stop, frame_size).

        This method will also set the property <frame_size>.

        @param dict data: The frame data (values) to be set for all active channels (keys)
        """
        pass

    @abstractmethod
    def set_output_mode(self, mode):
        """ Setter for the current output mode.

        @param SamplingOutputMode mode: The output mode to set as SamplingOutputMode Enum
        """
        pass

    @abstractmethod
    def start_buffered_output(self):
        """ Will start the output of the previously set data frame in a non-blocking way.
        Must return immediately and not wait for the frame to finish.

        Must raise exception if frame output can not be started.
        """
        pass

    @abstractmethod
    def stop_buffered_output(self):
        """ Will abort the currently running data frame output.
        Will return AFTER the frame output has been terminated without waiting for all samples
        to be emitted (if possible).

        After the output has been stopped, the frame buffer will be empty in any case and must be
        repopulated for the next run using <set_frame_data>.

        Must NOT raise exceptions if no frame output is running.
        """
        pass

    @abstractmethod
    def emit_samples(self, data):
        """ Emit a single data frame for all active channels.
        This method call is blocking until the entire data frame has been emitted.

        Will not overwrite the property <frame_size>.

        See <start_buffered_output>, <stop_buffered_output> and <set_frame_data> for more details.

        @param dict data: The frame data (values) to be emitted for all active channels (keys)
        """
        pass


class FiniteSamplingOutputConstraints:
    """ A container to hold all constraints for finite output sampling devices.
    """
    def __init__(self, supported_modes, channel_units, frame_size_limits, sample_rate_limits):
        assert len(sample_rate_limits) == 2, 'Sample rate limits must be iterable of length 2'
        assert len(frame_size_limits) == 2, 'Frame size limits must be iterable of length 2'
        assert all(lim > 0 for lim in sample_rate_limits), 'Sample rate limits must be > 0'
        assert all(lim > 0 for lim in frame_size_limits), 'Frame size limits must be > 0'
        assert len(channel_units) > 0, 'Specify at least one channel with unit in config'
        assert all(isinstance(name, str) and name for name in channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(unit, str) for unit in channel_units.values()), \
            'Channel units must be strings'
        assert all(isinstance(mode, SamplingOutputMode) for mode in supported_modes)

        self._supported_modes = frozenset(supported_modes)
        self._sample_rate_limits = (float(min(sample_rate_limits)), float(max(sample_rate_limits)))
        self._frame_size_limits = (int(round(min(frame_size_limits))),
                                   int(round(max(frame_size_limits))))
        self._channel_units = channel_units.copy()

    @property
    def supported_modes(self):
        return self._supported_modes

    @property
    def channel_units(self):
        return self._channel_units.copy()

    @property
    def channel_names(self):
        return tuple(self._channel_units)

    @property
    def sample_rate_limits(self):
        return self._sample_rate_limits

    @property
    def min_sample_rate(self):
        return self._sample_rate_limits[0]

    @property
    def max_sample_rate(self):
        return self._sample_rate_limits[1]

    @property
    def frame_size_limits(self):
        return self._frame_size_limits

    @property
    def min_frame_size(self):
        return self._frame_size_limits[0]

    @property
    def max_frame_size(self):
        return self._frame_size_limits[1]

    def mode_supported(self, mode):
        return mode in self._supported_modes

    def channel_valid(self, channel):
        return channel in self._channel_units

    def sample_rate_in_range(self, rate):
        return in_range(rate, *self._sample_rate_limits)

    def frame_size_in_range(self, size):
        return in_range(size, *self._frame_size_limits)
