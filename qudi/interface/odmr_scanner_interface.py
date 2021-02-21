# -*- coding: utf-8 -*-

"""
ToDo: Document

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
from qudi.core.util.helpers import in_range
from qudi.interface.finite_sampling_output_interface import SamplingOutputMode


class OdmrScannerInterface(Base):
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
    def sample_rate(self):
        """ The sample rate (in Hz) at which the samples will be emitted.

        @return float: The current sample rate in Hz
        """
        pass

    @property
    @abstractmethod
    def frame_size(self):
        """ Currently set number of samples per channel per frame to sample/acquire.

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
    def power(self):
        """ Currently set microwave scanning power in dBm.

        @return float: microwave scanning power (in dBm)
        """
        pass

    @abstractmethod
    def set_sample_rate(self, rate):
        """ Will set the sample rate to a new value.

        @param float rate: The sample rate to set
        """
        pass

    @abstractmethod
    def set_frequency_data(self, data):
        """ Sets the frequency values to scan.

        If <output_mode> is SamplingOutputMode.JUMP_LIST, data must be 1D numpy.ndarray containing
        the entire data frame of length <frame_size>.
        If <output_mode> is SamplingOutputMode.EQUIDISTANT_SWEEP, data must be iterable of
        length 3 representing the entire data frame to be constructed with numpy.linspace(),
        i.e. (start, stop, steps).

        Read-only property <frame_size> will change accordingly if this method is called.

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
    def set_power(self, pwr):
        """ Setter for microwave scanning power in dBm.

        @param float pwr: microwave scanning power to set (in dBm)
        """
        pass

    @abstractmethod
    def scan_frame(self):
        """ Perform a single scan over frequency values set by <set_frequency_data> and
        synchronously acquire data for all data channels.
        This method call is blocking until the entire data frame has been acquired.
        Size of the data array returned for each channel equals <frame_size>.

        @return dict: Frame data (values) for all active data channels (keys)
        """
        pass


class OdmrScannerConstraints:
    """ A container to hold all constraints for ODMR scanning devices.
    """

    def __init__(self, supported_output_modes, channel_units, frame_size_limits, sample_rate_limits,
                 frequency_limits, power_limits):
        assert len(sample_rate_limits) == 2, 'Sample rate limits must be iterable of length 2'
        assert len(frame_size_limits) == 2, 'Frame size limits must be iterable of length 2'
        assert len(frequency_limits) == 2, 'Frequency limits must be iterable of length 2'
        assert len(power_limits) == 2, 'Power limits must be iterable of length 2'
        assert all(lim > 0 for lim in sample_rate_limits), 'Sample rate limits must be > 0'
        assert all(lim > 0 for lim in frame_size_limits), 'Frame size limits must be > 0'
        assert all(lim > 0 for lim in frequency_limits), 'Frequency limits must be > 0'
        assert len(channel_units) > 0, 'Specify at least one data channel with unit'
        assert all(isinstance(name, str) and name for name in channel_units), \
            'Channel names must be non-empty strings'
        assert all(isinstance(unit, str) for unit in channel_units.values()), \
            'Channel units must be strings'
        assert all(isinstance(mode, SamplingOutputMode) for mode in supported_output_modes)

        self._supported_output_modes = frozenset(supported_output_modes)
        self._sample_rate_limits = (float(min(sample_rate_limits)), float(max(sample_rate_limits)))
        self._frame_size_limits = (int(round(min(frame_size_limits))),
                                   int(round(max(frame_size_limits))))
        self._frequency_limits = (float(min(frequency_limits)), float(max(frequency_limits)))
        self._power_limits = (float(min(power_limits)), float(max(power_limits)))
        self._channel_units = channel_units.copy()

    @property
    def supported_output_modes(self):
        return self._supported_output_modes

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

    @property
    def frequency_limits(self):
        return self._frequency_limits

    @property
    def min_frequency(self):
        return self._frequency_limits[0]

    @property
    def max_frequency(self):
        return self._frequency_limits[1]

    @property
    def power_limits(self):
        return self._power_limits

    @property
    def min_power(self):
        return self._power_limits[0]

    @property
    def max_power(self):
        return self._power_limits[1]

    def output_mode_supported(self, mode):
        return mode in self._supported_output_modes

    def channel_valid(self, channel):
        return channel in self._channel_units

    def sample_rate_in_range(self, rate):
        return in_range(rate, *self._sample_rate_limits)

    def frame_size_in_range(self, size):
        return in_range(size, *self._frame_size_limits)

    def frequency_in_range(self, frequency):
        return in_range(frequency, *self._frequency_limits)

    def power_in_range(self, pwr):
        return in_range(pwr, *self._power_limits)
