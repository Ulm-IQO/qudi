# -*- coding: utf-8 -*-
"""
Qudi interface definitions for a simple multi/single channel setpoint device,
a simple multi/single channel process value reading device
and the combination of both (reading/setting setpoints and reading process value).

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
from qudi.core.module import InterfaceBase
from qudi.core.util.helpers import in_range

__all__ = ('ProcessSetpointInterface', 'ProcessValueInterface', 'ProcessControlInterface',
           'ProcessControlConstraints')


class ProcessSetpointInterface(InterfaceBase):
    """ A simple interface to control the setpoint for one or multiple process values.

    This interface is in fact a very general/universal interface that can be used for a lot of
    things. It can be used to interface any hardware where one to control one or multiple control
    values, like a temperature or how much a PhD student get paid.
    """

    @property
    @abstractmethod
    def constraints(self):
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.

        @return ProcessControlConstraints: Hardware constraints
        """
        pass

    @property
    @abstractmethod
    def channel_states(self):
        """ Current channel state for all channels. States are bool type and refer to active (True)
        and inactive (False).
        Example state dict: {'channel_1': True, 'channel_2': False}

        @return dict: Channel states (values) for each channel (keys)
        """
        pass

    @channel_states.setter
    def channel_states(self, states):
        """ Set channel state for all channels. States are bool type and refer to active (True)
        and inactive (False).
        Example state dict: {'channel_1': True, 'channel_2': False}

        @param dict states: Channel states (values) for each channel (keys) to set
        """
        pass

    @property
    @abstractmethod
    def setpoints(self):
        """ The current setpoints for all channels.

        @return dict: Currently set target values (values) for all channels (keys)
        """
        pass

    @setpoints.setter
    def setpoints(self, values):
        """ Set the setpoints for all channels at once.

        @param dict values: Target values (values) to set for all channels (keys)
        """
        pass

    @abstractmethod
    def set_channel_state(self, active, channel):
        """ Set channel state for a single channel. States are bool type and refer to active (True)
        and inactive (False).

        @param bool active: Channel state flag (active: True, inactive: False)
        @param str channel: The channel to set
        """
        pass

    @abstractmethod
    def get_channel_state(self, channel):
        """ Get current channel state for a single channel. States are bool type and refer to
        active (True) and inactive (False).

        @param str channel: The channel to set

        @return bool: Current channel state flag (active: True, inactive: False)
        """
        pass

    @abstractmethod
    def set_setpoint(self, value, channel):
        """ Set new setpoint for a single channel.

        @param float|int value: Setpoint value to set
        @param str channel: Channel to set
        """
        pass

    @abstractmethod
    def get_setpoint(self, channel):
        """ Get current setpoint for a single channel.

        @param str channel: Channel to get the setpoint for
        @return float|int: The current setpoint for <channel>
        """
        pass


class ProcessValueInterface(InterfaceBase):
    """ A simple interface to read one or multiple process values.

    This interface is in fact a very general/universal interface that can be used for a lot of
    things. It can be used to interface any hardware where one to control one or multiple control
    values, like a temperature or how much a PhD student get paid.
    """

    @property
    @abstractmethod
    def constraints(self):
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.

        @return ProcessControlConstraints: Hardware constraints
        """
        pass

    @property
    @abstractmethod
    def channel_states(self):
        """ Current channel state for all channels. States are bool type and refer to active (True)
        and inactive (False).
        Example state dict: {'channel_1': True, 'channel_2': False}

        @return dict: Channel states (values) for each channel (keys)
        """
        pass

    @channel_states.setter
    def channel_states(self, states):
        """ Set channel state for all channels. States are bool type and refer to active (True)
        and inactive (False).
        Example state dict: {'channel_1': True, 'channel_2': False}

        @param dict states: Channel states (values) for each channel (keys) to set
        """
        pass

    @property
    @abstractmethod
    def process_values(self):
        """ Read-Only property returning a snapshot of current process values for all channels.

        @return dict: Snapshot of the current process values (values) for all channels (keys)
        """
        pass

    @abstractmethod
    def set_channel_state(self, active, channel):
        """ Set channel state for a single channel. States are bool type and refer to active (True)
        and inactive (False).

        @param bool active: Channel state flag (active: True, inactive: False)
        @param str channel: The channel to set
        """
        pass

    @abstractmethod
    def get_channel_state(self, channel):
        """ Get current channel state for a single channel. States are bool type and refer to
        active (True) and inactive (False).

        @param str channel: The channel to set

        @return bool: Current channel state flag (active: True, inactive: False)
        """
        pass

    @abstractmethod
    def get_process_value(self, channel):
        """ Get current process value for a single channel.

        @param str channel: Channel to get the process value for
        @return float|int: The current process value for <channel>
        """
        pass


class ProcessControlInterface(ProcessSetpointInterface, ProcessValueInterface):
    """ A simple interface to control the setpoints for and read one or multiple process values.

    This interface is in fact a very general/universal interface that can be used for a lot of
    things. It can be used to interface any hardware where one to control one or multiple control
    values, like a temperature or how much a PhD student get paid.
    """
    pass


class ProcessControlConstraints:
    """ Data object holding the constraints for a set of process value channels.
    """
    def __init__(self, setpoint_channels, process_channels, units=None, limits=None, dtypes=None):
        """
        """
        if units is None:
            units = dict()
        if limits is None:
            limits = dict()
        if dtypes is None:
            dtypes = dict()
        all_channels = set(setpoint_channels)
        all_channels.update(process_channels)

        assert set(units).issubset(all_channels)
        assert all(isinstance(unit, str) for unit in units.values())
        assert set(limits).issubset(all_channels)
        assert all(len(lim) == 2 for lim in limits.values())
        assert set(dtypes).issubset(all_channels)
        assert all(t in (int, float) for t in dtypes.values())

        self._setpoint_channels = frozenset(setpoint_channels)
        self._process_channels = frozenset(process_channels)
        self._channel_units = {ch: units.get(ch, '') for ch in all_channels}
        self._channel_limits = {ch: limits.get(ch, (-np.inf, np.inf)) for ch in all_channels}
        self._channel_dtypes = {ch: dtypes.get(ch, float) for ch in all_channels}

    @property
    def all_channels(self):
        return self._setpoint_channels.union(self._process_channels)

    @property
    def setpoint_channels(self):
        return self._setpoint_channels

    @property
    def process_channels(self):
        return self._process_channels

    @property
    def channel_units(self):
        return self._channel_units.copy()

    @property
    def channel_limits(self):
        return self._channel_limits.copy()

    @property
    def channel_dtypes(self):
        return self._channel_dtypes.copy()

    def channel_value_in_range(self, value, channel):
        return in_range(value, *self._channel_limits[channel])
