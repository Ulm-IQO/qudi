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
    """ This interface is used to manage multiples axis piezo steppers.

    This interface is not for doing scans. It is a wrapper around general piezo steppers features
    to control them "by hand".
    It can be useful for debugging or prototyping and also to provide tools for semi automatic calibration

    Piezo steppers are a useful device to access different zone of a sample over long distances.
    If you have a controller, you can use this interface to interact with it.

    ##### Getters and setters

    This interface implement getters and setters as only one overloaded function.
    For these function, if a value is provided, it is set as new value.
    In every case, the last value is returned

    ##### Buffered value

    Sometime you want to get the last read value of a parameter for a non critical fast application.
    In this case, you can pass the _buffered_ = True option so that the hardware module respond right away.

    """
    @abc.abstractmethod
    def axis(self):
        """ Get a tuple of all axis identifier

        @return tuple: Tuple of axis identifier (integer or string)
        """
        pass

    @abc.abstractmethod
    def voltage_range(self, axis):
        """ Get the voltage range of an axis

        @param str|int axis: An axis identifier

        @return tuple(float, float): the voltage range in Volt as a tuple (min, max)
        """
        pass

    @abc.abstractmethod
    def frequency_range(self, axis):
        """ Get the frequency range of an axis

        @param str|int axis: An axis identifier

        @return tuple(float, float): the frequency range in Hertz as a tuple (min, max)
        """
        pass

    @abc.abstractmethod
    def position_range(self, axis):
        """ Get the position range of an axis

        @param str|int axis: An axis identifier

        @return tuple(float, float): the range in µm as a tuple (min, max)
        """
        pass

    @abc.abstractmethod
    def capacitance(self, axis, buffered=False):
        """ Get the capacitance of an axis

        @param str|int axis: An axis identifier

        @param boolean: Only get last buffered value

        @return float: the capacitance in Farad
        """
        pass

    @abc.abstractmethod
    def voltage(self, axis, value=None, buffered=False):
        """ Get the voltage of an axis

        @param str|int axis: An axis identifier

        @param boolean: Only get last buffered value

        @return float: the voltage in Volt
        """
        pass

    @abc.abstractmethod
    def frequency(self, axis, value=None, buffered=False):
        """ Get the frequency of an axis

        @param str|int axis: An axis identifier

        @param boolean: Only get last buffered value

        @return float: the frequency in Hertz
        """
        pass

    @abc.abstractmethod
    def steps(self, axis, number):
        """ Do X steps on an axis (positive or negative) in current configuration

        @param str|int axis: An axis identifier
        @param integer number: The number of steps to do (positive or negative)

        @return boolean: success state
         """
        pass

    @abc.abstractmethod
    def stop(self, axis=None):
        """ Stop movement of one or all axis.

        @param str|int axis: (optional) An axis identifier

        @return boolean: success state

        If no axis is given, stop all axis
        """
        pass
