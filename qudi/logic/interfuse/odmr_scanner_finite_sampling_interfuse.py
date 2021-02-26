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

from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import RecursiveMutex
from qudi.interface.finite_sampling_output_interface import SamplingOutputMode
from qudi.interface.odmr_scanner_interface import OdmrScannerInterface, OdmrScannerConstraints


class OdmrScannerFiniteSamplingInterfuse(OdmrScannerInterface):
    """
    ToDo: Document
    """

    _frequency_sampler = Connector(name='frequency_sampler',
                                   interface='FiniteSamplingOutputInterface',
                                   optional=True)
    _data_sampler = Connector(name='data_sampler',
                              interface='FiniteSamplingInputInterface',
                              optional=True)
    _odmr_sampler = Connector(name='odmr_sampler',
                              interface='FiniteSamplingIOInterface',
                              optional=True)
    _power_setter = Connector(name='power_setter', interface='ProcessSetpointInterface')

    _power_channel = ConfigOption(name='power_channel', default=None)
    _frequency_channel = ConfigOption(name='frequency_channel', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()
        self._constraints = None

    def on_activate(self):
        """ Perform qudi module activation
        """
        freq_sampler = self._frequency_sampler()
        data_sampler = self._data_sampler()
        power_setter = self._power_setter()
        odmr_sampler = self._odmr_sampler()
        assert (freq_sampler is not None and data_sampler is not None) or odmr_sampler is not None,\
            'You need to either connect "odmr_sampler" with "FiniteSamplingIOInterface" or both, ' \
            '"data_sampler" and "frequency_sampler" with "FiniteSamplingInputInterface" and ' \
            '"FiniteSamplingOutputInterface" respectively.'

        # Determine which frequency channel to use
        if freq_sampler is None:
            output_channels = odmr_sampler.constraints.output_channel_names
        else:
            output_channels = freq_sampler.constraints.channel_names
        if self._frequency_channel is None:
            candidates = [ch for ch in output_channels if 'frequency' in ch.lower()]
            if not candidates:
                raise RuntimeError(
                    'Choosing a suitable frequency channel failed. Please specify '
                    '"frequency_channel" option in config.'
                )
            self._frequency_channel = candidates[0]
        else:
            if self._frequency_channel not in output_channels:
                raise ValueError(
                    f'Frequency channel "{self._frequency_channel}" specified in config does not '
                    f'match any channel available in hardware {output_channels}.'
                )

        # Determine which power channel to use
        setpoint_channels = power_setter.constraints.setpoint_channels
        if self._power_channel is None:
            candidates = [ch for ch in setpoint_channels if 'power' in ch.lower()]
            if not candidates:
                raise RuntimeError(
                    'Choosing a suitable power setpoint channel failed. Please specify '
                    '"power_channel" option in config.'
                )
            self._power_channel = candidates[0]
        else:
            if self._power_channel not in setpoint_channels:
                raise ValueError(
                    f'Power channel "{self._power_channel}" specified in config does not match any '
                    f'channel available in hardware {setpoint_channels}.'
                )

        # merge all component hardware constraints
        if odmr_sampler is None:
            freq_frame_limits = freq_sampler.constraints.frame_size_limits
            data_frame_limits = data_sampler.constraints.frame_size_limits
            freq_rate_limits = freq_sampler.constraints.sample_rate_limits
            data_rate_limits = data_sampler.constraints.sample_rate_limits
            self._constraints = OdmrScannerConstraints(
                supported_output_modes=freq_sampler.constraints.supported_output_modes,
                channel_units=data_sampler.constraints.channel_units,
                frequency_limits=(1e3, 6e9),  # FIXME:
                power_limits=power_setter.constraints.channel_limits[self._power_channel],
                frame_size_limits=(max(freq_frame_limits[0], data_frame_limits[0]),
                                   min(freq_frame_limits[1], data_frame_limits[1])),
                sample_rate_limits=(max(freq_rate_limits[0], data_rate_limits[0]),
                                    min(freq_rate_limits[1], data_rate_limits[1]))
            )
        else:
            self._constraints = OdmrScannerConstraints(
                supported_output_modes=odmr_sampler.constraints.supported_output_modes,
                channel_units=odmr_sampler.constraints.input_channel_units,
                frequency_limits=(1e3, 6e9),  # FIXME:
                power_limits=power_setter.constraints.channel_limits[self._power_channel],
                frame_size_limits=odmr_sampler.constraints.frame_size_limits,
                sample_rate_limits=odmr_sampler.constraints.sample_rate_limits
            )

    def on_deactivate(self):
        """ Perform qudi module deactivation
        """
        pass

    @property
    def constraints(self):
        """ ToDo: Document
        """
        return self._constraints

    @property
    def sample_rate(self):
        """ The sample rate (in Hz) at which the samples will be emitted.

        @return float: The current sample rate in Hz
        """
        with self._thread_lock:
            if self._odmr_sampler.is_connected:
                return self._odmr_sampler().sample_rate
            else:
                data = self._data_sampler().sample_rate
                frequency = self._frequency_sampler().sample_rate
                if data != frequency:
                    self.log.warning(
                        'data and frequency sampling rates have diverged. This should never happen!'
                    )
                return data

    @property
    def frame_size(self):
        """ Currently set number of samples per channel per frame to sample/acquire.

        @return int: Number of samples per frame
        """
        with self._thread_lock:
            if self._odmr_sampler.is_connected:
                return self._odmr_sampler().frame_size
            else:
                data = self._data_sampler().frame_size
                frequency = self._frequency_sampler().frame_size
                if data != frequency:
                    self.log.warning(
                        'data and frequency frame sizes have diverged. This should never happen!'
                    )
                return data

    @property
    def output_mode(self):
        """ Currently set output mode.

        @return SamplingOutputMode: Enum representing the currently active output mode
        """
        with self._thread_lock:
            if self._odmr_sampler.is_connected:
                return self._odmr_sampler().output_mode
            else:
                return self._frequency_sampler().output_mode

    @property
    def power(self):
        """ Currently set microwave scanning power in dBm.

        @return float: microwave scanning power (in dBm)
        """
        with self._thread_lock:
            return self._power_setter().get_setpoint(self._power_channel)

    def set_sample_rate(self, rate):
        """ Will set the sample rate to a new value.

        @param float rate: The sample rate to set
        """
        with self._thread_lock:
            if self._odmr_sampler.is_connected:
                self._odmr_sampler().set_sample_rate(rate)
            else:
                self._data_sampler().set_sample_rate(rate)
                self._frequency_sampler().set_sample_rate(rate)

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
        with self._thread_lock:
            if self._odmr_sampler.is_connected:
                sampler = self._odmr_sampler()
                curr_channels = sampler.active_channels[0]
                sampler.set_active_channels(curr_channels, {self._frequency_channel})
                sampler.set_frame_data({self._frequency_channel: data})
            else:
                freq_sampler = self._frequency_sampler()
                freq_sampler.set_active_channels({self._frequency_channel})
                freq_sampler.set_frame_data({self._frequency_channel: data})
                frame_size = freq_sampler.frame_size
                self._data_sampler().set_frame_size(frame_size)

    def set_output_mode(self, mode):
        """ Setter for the current output mode.

        @param SamplingOutputMode mode: The output mode to set as SamplingOutputMode Enum
        """
        with self._thread_lock:
            if self._odmr_sampler.is_connected:
                self._odmr_sampler().set_output_mode(mode)
            else:
                self._frequency_sampler().set_output_mode(mode)

    def set_power(self, pwr):
        """ Setter for microwave scanning power in dBm.

        @param float pwr: microwave scanning power to set (in dBm)
        """
        with self._thread_lock:
            return self._power_setter().set_setpoint(pwr, self._power_channel)

    def scan_frame(self):
        """ Perform a single scan over frequency values set by <set_frequency_data> and
        synchronously acquire data for all data channels.
        This method call is blocking until the entire data frame has been acquired.
        Size of the data array returned for each channel equals <frame_size>.

        @return dict: Frame data (values) for all active data channels (keys)
        """
        with self._thread_lock:
            channels = self._constraints.channel_names
            if self._odmr_sampler.is_connected:
                odmr_sampler = self._odmr_sampler()
                self.module_state.lock()
                try:
                    odmr_sampler.set_active_channels(frozenset(channels), {self._frequency_channel})
                    return odmr_sampler.get_frame()
                finally:
                    self.module_state.unlock()
            else:
                freq_sampler = self._frequency_sampler()
                data_sampler = self._data_sampler()
                self.module_state.lock()
                try:
                    freq_sampler.set_active_channels({self._frequency_channel})
                    data_sampler.set_active_channels(frozenset(channels))
                    freq_sampler.start_buffered_output()
                    data = data_sampler.acquire_frame()
                    freq_sampler.stop_buffered_output()
                    return data
                finally:
                    self.module_state.unlock()
