# -*- coding: utf-8 -*-
"""
Interface for multiple axis open loop steppers.

---

This interface follow the guideline for which getters and setters are the same function overloaded

---

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

import abc
from core.util.interfaces import InterfaceMetaclass


class SteppersInterface(metaclass=InterfaceMetaclass):
    """
    """

    @abc.abstractmethod
    def voltage_range(self, axis):
        pass

    @abc.abstractmethod
    def frequency_range(self, axis):
        pass

    @abc.abstractmethod
    def position_range(self, axis):
        pass

    @abc.abstractmethod
    def capacitance(self, axis, buffered=False):
        pass

    @abc.abstractmethod
    def voltage(self, axis, value=None, buffered=False):
        pass

    @abc.abstractmethod
    def frequency(self, axis, value=None):
        pass

    def steps(self, axis, number):
        pass
