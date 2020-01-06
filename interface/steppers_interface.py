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
from core.meta import InterfaceMetaclass


class SteppersInterface(metaclass=InterfaceMetaclass):
    """
    """
    @abc.abstractmethod
    def axis(self):
        """ Get a tuple of all axis identifier
        The axis identifier might be an integer or a string
        """
        pass

    @abc.abstractmethod
    def voltage_range(self, axis):
        """ Get the voltage range of an axis
        Return the voltage range in Volt as a tuple (min, max)
        """
        pass

    @abc.abstractmethod
    def frequency_range(self, axis):
        """ Get the frequency range of an axis
        Return the frequency range in Hertz as a tuple (min, max)
        """
        pass

    @abc.abstractmethod
    def position_range(self, axis):
        """ Get the position range of an axis
        Return the range in µm as a tuple (min, max)
        """
        pass

    @abc.abstractmethod
    def capacitance(self, axis, buffered=False):
        """ Get the capacitance of an axis
        If buffered is true, return last read value
        Return the capacitance in Farad
        """
        pass

    @abc.abstractmethod
    def voltage(self, axis, value=None, buffered=False):
        """ Get the voltage of an axis
        If buffered is true, return last read value
        Return the capacitance in Farad
        """
        pass

    @abc.abstractmethod
    def frequency(self, axis, value=None):
        """ Get the frequency of an axis
        If buffered is true, return last read value
        Return the capacitance in Farad
        """
        pass

    @abc.abstractmethod
    def steps(self, axis, number):
        """ Do X steps on an axis (positive or negative) in current configuration """
        pass

    @abc.abstractmethod
    def stop(self, axis=None):
        """ Stop movement of one or all axis. (All if axis=None) """
        pass
