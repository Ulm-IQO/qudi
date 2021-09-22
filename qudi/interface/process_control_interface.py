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

__all__ = ['ProcessSetpointInterface', 'ProcessValueInterface', 'ProcessControlInterface',
           'ProcessControlConstraints']

import numpy as np
from abc import abstractmethod
from typing import Iterable, Mapping, Union, Optional, Tuple, Type, Dict

from qudi.core.module import Base
from qudi.util.helpers import in_range


_Real = Union[int, float]


class ProcessControlConstraints:
    """ Data object holding the constraints for a set of process/setpoint channels.
    """
    def __init__(self, setpoint_channels: Optional[Iterable[str]] = None,
                 process_channels: Optional[Iterable[str]] = None,
                 units: Optional[Mapping[str, str]] = None,
                 limits: Optional[Mapping[str, Tuple[_Real, _Real]]] = None,
                 dtypes: Optional[Mapping[str, Union[Type[int], Type[float]]]] = None):
        """
        """
        if units is None:
            units = dict()
        if limits is None:
            limits = dict()
        if dtypes is None:
            dtypes = dict()
        if setpoint_channels is None:
            setpoint_channels = tuple()
        if process_channels is None:
            process_channels = tuple()

        self._setpoint_channels = tuple() if setpoint_channels is None else tuple(setpoint_channels)
        self._process_channels = tuple() if process_channels is None else tuple(process_channels)

        all_channels = set(self._setpoint_channels)
        all_channels.update(self._process_channels)

        assert set(units).issubset(all_channels)
        assert all(isinstance(unit, str) for unit in units.values())
        assert set(limits).issubset(all_channels)
        assert all(len(lim) == 2 for lim in limits.values())
        assert set(dtypes).issubset(all_channels)
        assert all(t in (int, float) for t in dtypes.values())

        self._channel_units = {ch: units.get(ch, '') for ch in all_channels}
        self._channel_limits = {ch: limits.get(ch, (-np.inf, np.inf)) for ch in all_channels}
        self._channel_dtypes = {ch: dtypes.get(ch, float) for ch in all_channels}

    @property
    def all_channels(self) -> Tuple[str, ...]:
        return *self.setpoint_channels, *self.process_channels

    @property
    def setpoint_channels(self) -> Tuple[str, ...]:
        return self._setpoint_channels

    @property
    def process_channels(self) -> Tuple[str, ...]:
        return self._process_channels

    @property
    def channel_units(self) -> Dict[str, str]:
        return self._channel_units.copy()

    @property
    def channel_limits(self) -> Dict[str, Tuple[_Real, _Real]]:
        return self._channel_limits.copy()

    @property
    def channel_dtypes(self) -> Dict[str, Union[Type[int], Type[float]]]:
        return self._channel_dtypes.copy()

    def channel_value_in_range(self, value: _Real, channel: str) -> Tuple[bool, _Real]:
        return in_range(value, *self._channel_limits[channel])


class ProcessSetpointInterface(Base):
    """ A simple interface to control the setpoint for one or multiple process values.

    This interface is in fact a very general/universal interface that can be used for a lot of
    things. It can be used to interface any hardware where one to control one or multiple control
    values, like a temperature or how much a PhD student get paid.
    """

    @property
    @abstractmethod
    def constraints(self) -> ProcessControlConstraints:
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.
        """
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """ Current activity state.
        State is bool type and refers to active (True) and inactive (False).
        """
        pass

    @is_active.setter
    def is_active(self, active: bool):
        """ Set activity state.
        State is bool type and refers to active (True) and inactive (False).
        """
        pass

    @property
    @abstractmethod
    def setpoints(self) -> Dict[str, _Real]:
        """ The current setpoints (values) for all channels (keys) """
        pass

    @setpoints.setter
    def setpoints(self, values: Mapping[str, _Real]):
        """ Set the setpoints (values) for all channels (keys) at once """
        pass

    @abstractmethod
    def set_activity_state(self, active: bool) -> None:
        """ Set activity state. State is bool type and refers to active (True) and inactive (False).
        """
        pass

    @abstractmethod
    def set_setpoint(self, value: _Real, channel: str) -> None:
        """ Set new setpoint for a single channel """
        pass

    @abstractmethod
    def get_setpoint(self, channel: str) -> _Real:
        """ Get current setpoint for a single channel """
        pass


class ProcessValueInterface(Base):
    """ A simple interface to read one or multiple process values.

    This interface is in fact a very general/universal interface that can be used for a lot of
    things. It can be used to interface any hardware where one to control one or multiple control
    values, like a temperature or how much a PhD student get paid.
    """

    @property
    @abstractmethod
    def constraints(self) -> ProcessControlConstraints:
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.
        """
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """ Current activity state.
        State is bool type and refers to active (True) and inactive (False).
        """
        pass

    @is_active.setter
    def is_active(self, active: bool):
        """ Set activity state.
        State is bool type and refers to active (True) and inactive (False).
        """
        pass

    @property
    @abstractmethod
    def process_values(self) -> Dict[str, _Real]:
        """ Read-Only property returning a snapshot of current process values (values) for all
        channels (keys).
        """
        pass

    @abstractmethod
    def set_activity_state(self, active: bool) -> None:
        """ Set activity state. State is bool type and refers to active (True) and inactive (False).
        """
        pass

    @abstractmethod
    def get_process_value(self, channel: str) -> _Real:
        """ Get current process value for a single channel """
        pass


class ProcessControlInterface(ProcessSetpointInterface, ProcessValueInterface):
    """ A simple interface to control the setpoints for and read one or multiple process values.

    This interface is in fact a very general/universal interface that can be used for a lot of
    things. It can be used to interface any hardware where one to control one or multiple control
    values, like a temperature or how much a PhD student get paid.
    """
    pass
