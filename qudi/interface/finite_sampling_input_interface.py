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

from qudi.core.interface import abstract_interface_method
from qudi.core.meta import InterfaceMetaclass


class FiniteSamplingInputInterface(metaclass=InterfaceMetaclass):
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
        """ The sample rate (in Hz) at which the samples will be acquired.

        @return float: The current sample rate in Hz
        """
        pass

    @property
    @abstract_interface_method
    def frame_size(self):
        """ Currently set number of samples per channel to acquire for each data frame.

        @return int: Number of samples per frame
        """
        pass

    @property
    @abstract_interface_method
    def samples_in_buffer(self):
        """ Currently available samples per channel being held in the input buffer.
        This is the current minimum number of samples to be read with "get_buffered_samples()"
        without blocking.

        @return int: Number of unread samples per channel
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
    def set_frame_size(self, size):
        """ Will set the number of samples per channel to acquire within one frame.

        @param int size: The sample rate to set
        """
        pass

    @abstract_interface_method
    def start_buffered_acquisition(self):
        """ Will start the acquisition of a data frame in a non-blocking way.
        Must return immediately and not wait for the data acquisition to finish.

        Must raise exception if data acquisition can not be started.
        """
        pass

    @abstract_interface_method
    def stop_buffered_acquisition(self):
        """ Will abort the currently running data frame acquisition.
        Will return AFTER the data acquisition has been terminated without waiting for all samples
        to be acquired (if possible).

        Must NOT raise exceptions if no data acquisition is running.
        """
        pass

    @abstract_interface_method
    def get_buffered_samples(self, number_of_samples=None):
        """ Returns a chunk of the current data frame for all active channels read from the frame
        buffer.
        If parameter <number_of_samples> is omitted, this method will return the currently
        available samples within the frame buffer (i.e. the value of property <samples_in_buffer>).
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

        @return dict: Sample arrays (values) for each active channel (keys)
        """
        pass

    @abstract_interface_method
    def acquire_frame(self, frame_size=None):
        """ Acquire a single data frame for all active channels.
        This method call is blocking until the entire data frame has been acquired.

        If an explicit frame_size is given as parameter, it will not overwrite the property
        <frame_size> but just be valid for this single frame.

        See <start_buffered_acquisition>, <stop_buffered_acquisition> and <get_buffered_samples>
        for more details.

        @param int frame_size: optional, the number of samples to acquire in this frame

        @return dict: Sample arrays (values) for each active channel (keys)
        """
        pass


# ToDo: implement
# class FiniteSamplingInputConstraints:
#     """
#     """
#     def __init__(self):

