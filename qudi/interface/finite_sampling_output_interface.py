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

from enum import Enum
from qudi.core.meta import InterfaceMetaclass
from qudi.core.interface import abstract_interface_method


class SamplingOutputMode(Enum):
    JUMP_LIST = 0
    EQUIDISTANT_SWEEP = 1


class FiniteSamplingOutputInterface(metaclass=InterfaceMetaclass):
    """
    ToDo: Document
    """

    @property
    @abstract_interface_method
    def constraints(self):
        """
        ToDo: Document
        """
        pass

    @property
    @abstract_interface_method
    def active_channels(self):
        """ Names of all currently active channels.

        @return frozenset: The active channel name strings as set
        """
        pass

    @property
    @abstract_interface_method
    def sample_rate(self):
        """ The sample rate (in Hz) at which the samples will be emitted.

        @return float: The current sample rate in Hz
        """
        pass

    @property
    @abstract_interface_method
    def frame_size(self):
        """ Currently set number of samples per channel to emit for each data frame.

        @return int: Number of samples per frame
        """
        pass

    @property
    @abstract_interface_method
    def output_mode(self):
        """ Currently set output mode.

        @return SamplingOutputMode: Enum representing the currently active output mode
        """
        pass

    @property
    @abstract_interface_method
    def samples_in_buffer(self):
        """ Current number of samples per channel still pending to be emitted.

        @return int: Number of pending samples to be emitted
        """
        pass

    @abstract_interface_method
    def set_sample_rate(self, rate):
        """ Will set the sample rate to a new value.

        @param float rate: The sample rate to set
        """
        pass

    @abstract_interface_method
    def set_active_channels(self, channels):
        """ Will set the currently active channels. All other channels will be deactivated.

        @param iterable(str) channels: Iterable of channel names to set active.
        """
        pass

    @abstract_interface_method
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

    @abstract_interface_method
    def set_output_mode(self, mode):
        """ Setter for the current output mode.

        @param SamplingOutputMode mode: The output mode to set as SamplingOutputMode Enum
        """
        pass

    @abstract_interface_method
    def start_buffered_output(self):
        """ Will start the output of the previously set data frame in a non-blocking way.
        Must return immediately and not wait for the frame to finish.

        Must raise exception if frame output can not be started.
        """
        pass

    @abstract_interface_method
    def stop_buffered_output(self):
        """ Will abort the currently running data frame output.
        Will return AFTER the frame output has been terminated without waiting for all samples
        to be emitted (if possible).

        After the output has been stopped, the frame buffer will be empty in any case and must be
        repopulated for the next run using <set_frame_data>.

        Must NOT raise exceptions if no frame output is running.
        """
        pass

    @abstract_interface_method
    def emit_samples(self, data):
        """ Emit a single data frame for all active channels.
        This method call is blocking until the entire data frame has been emitted.

        Will not overwrite the property <frame_size>.

        See <start_buffered_output>, <stop_buffered_output> and <set_frame_data> for more details.

        @param dict data: The frame data (values) to be emitted for all active channels (keys)
        """
        pass
