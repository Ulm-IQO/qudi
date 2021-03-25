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
from qudi.core.enums import SamplingOutputMode


class FiniteSamplingIOInterface(Base):
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
        """ Names of all currently active input and output channels.

        @return (frozenset, frozenset): active input channels, active output channels
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
        """ Current number of acquired but unread samples per channel in the input buffer.

        @return int: Unread samples in input buffer
        """
        pass

    @abstractmethod
    def set_sample_rate(self, rate):
        """ Will set the sample rate to a new value.

        @param float rate: The sample rate to set
        """
        pass

    @abstractmethod
    def set_active_channels(self, input_channels, output_channels):
        """ Will set the currently active input and output channels.
        All other channels will be deactivated.

        @param iterable(str) input_channels: Iterable of input channel names to set active
        @param iterable(str) output_channels: Iterable of output channel names to set active
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
        i.e. (start, stop, steps).

        Calling this method will alter read-only property <frame_size>

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
    def start_buffered_frame(self):
        """ Will start the input and output of the previously set data frame in a non-blocking way.
        Must return immediately and not wait for the frame to finish.

        Must raise exception if frame output can not be started.
        """
        pass

    @abstractmethod
    def stop_buffered_frame(self):
        """ Will abort the currently running data frame input and output.
        Will return AFTER the io has been terminated without waiting for the frame to finish
        (if possible).

        After the io operation has been stopped, the output frame buffer will keep its state and
        can be re-run or overwritten by calling <set_frame_data>.
        The input frame buffer will also stay and can be emptied by reading the available samples.

        Must NOT raise exceptions if no frame output is running.
        """
        pass

    @abstractmethod
    def get_buffered_samples(self, number_of_samples=None):
        """ Returns a chunk of the current data frame for all active input channels read from the
        input frame buffer.
        If parameter <number_of_samples> is omitted, this method will return the currently
        available samples within the input frame buffer (i.e. the value of property
        <samples_in_buffer>).
        If <number_of_samples> is exceeding the currently available samples in the frame buffer,
        this method will block until the requested number of samples is available.
        If the explicitly requested number of samples is exceeding the number of samples pending
        for acquisition in the rest of this frame, raise an exception.

        Samples that have been already returned from an earlier call to this method are not
        available anymore and can be considered discarded by the hardware. So this method is
        effectively decreasing the value of property <samples_in_buffer> (until new samples have
        been read).

        If the data acquisition has been stopped before the frame has been acquired completely,
        this method must still return all available samples already read into buffer.

        @param int number_of_samples: optional, the number of samples to read from buffer

        @return dict: Sample arrays (values) for each active input channel (keys)
        """
        pass

    @abstractmethod
    def get_frame(self, data):
        """ Performs io for a single data frame for all active channels.
        This method call is blocking until the entire data frame has been emitted.

        See <start_buffered_output>, <stop_buffered_output> and <set_frame_data> for more details.

        @param dict data: The frame data (values) to be emitted for all active channels (keys)

        @return dict: Frame data (values) for all active input channels (keys)
        """
        pass


# ToDo: value limits for (output) channels
class FiniteSamplingIOConstraints:
    """ A container to hold all constraints for finite IO sampling devices.
    """
    def __init__(self, supported_output_modes, input_channel_units, output_channel_units,
                 frame_size_limits, sample_rate_limits):
        assert len(sample_rate_limits) == 2, 'Sample rate limits must be iterable of length 2'
        assert len(frame_size_limits) == 2, 'Frame size limits must be iterable of length 2'
        assert all(lim > 0 for lim in sample_rate_limits), 'Sample rate limits must be > 0'
        assert all(lim > 0 for lim in frame_size_limits), 'Frame size limits must be > 0'
        assert len(input_channel_units) > 0, 'Specify at least one input channel with unit'
        assert len(output_channel_units) > 0, 'Specify at least one output channel with unit'
        assert all(isinstance(name, str) and name for name in input_channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(name, str) and name for name in output_channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(unit, str) for unit in input_channel_units.values()), \
            'Channel units must be strings'
        assert all(isinstance(unit, str) for unit in output_channel_units.values()), \
            'Channel units must be strings'
        assert all(isinstance(mode, SamplingOutputMode) for mode in supported_output_modes)

        self._supported_output_modes = frozenset(supported_output_modes)
        self._sample_rate_limits = (float(min(sample_rate_limits)), float(max(sample_rate_limits)))
        self._frame_size_limits = (int(round(min(frame_size_limits))),
                                   int(round(max(frame_size_limits))))
        self._output_channel_units = output_channel_units.copy()
        self._input_channel_units = input_channel_units.copy()

    @property
    def supported_output_modes(self):
        return self._supported_output_modes

    @property
    def output_channel_units(self):
        return self._output_channel_units.copy()

    @property
    def input_channel_units(self):
        return self._input_channel_units.copy()

    @property
    def output_channel_names(self):
        return tuple(self._output_channel_units)

    @property
    def input_channel_names(self):
        return tuple(self._input_channel_units)

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

    def output_mode_supported(self, mode):
        return mode in self._supported_output_modes

    def output_channel_valid(self, channel):
        return channel in self._output_channel_units

    def input_channel_valid(self, channel):
        return channel in self._input_channel_units

    def sample_rate_in_range(self, rate):
        return in_range(rate, *self._sample_rate_limits)

    def frame_size_in_range(self, size):
        return in_range(size, *self._frame_size_limits)
