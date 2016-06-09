# -*- coding: utf-8 -*-
"""
Interface file for lasers where current and power can be set.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
"""
from core.util.customexceptions import InterfaceImplementationError
from enum import Enum

class ControlModes(Enum):
    MIXED = 0
    POWER = 1
    CURRENT = 2

class SimpleLaserInterface:
    _modtype = 'SimpleLaserInterface'
    _modclass = 'interface'

    def get_power(self):
        """ Return laser power
        @return float: Laser power in watts
        """
        raise InterfaceImplementationError('SimpleLaserInterface->getData')
        return -1

    def get_current(self):
        """ Return laser current
        @return float: laser current in amperes
        """
        raise InterfaceImplementationError('SimpleLaserInterface->getChannels')
        return -1

    def get_control_mode(self):
        raise InterfaceImplementationError('SimpleLaserInterface->getChannels')