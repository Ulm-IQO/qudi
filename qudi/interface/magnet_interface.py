# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control magnets.

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

class MagnetInterface(Base):
    """Interface class to define the abstract controlls and communication with all magnet devices.

    A magnet device is a device, which somehow creates/controlls a magnetic field. This can be a linear stage,
    several connected stages, a controllable current source or a full vector magnet.
    """

    @property
    @abstractmethod
    def constraints(self):
        """The magnet constraints object for this device.

               @return MagnetConstraints:
        """
        raise NotImplementedError

    @abstractmethod
    def get_optional_setings(self):

        raise NotImplementedError

    @abstractmethod
    def set_optional_settings(self, **kwargs):

        raise NotImplementedError

    @abstractmethod
    def get_axis_value(self,axis):

        raise NotImplementedError

    @abstractmethod
    def set_axis_value(self, axis, value):

        raise NotImplementedError

    @abstractmethod
    def calibrate(self):

        raise NotImplementedError

    @abstractmethod
    def abort(self):
        """ Stops movement or the actual current sweep """

        raise NotImplementedError

    @abstractmethod
    def get_status(self):

        raise NotImplementedError
