# -*- coding: utf-8 -*-
"""
Decorators and objects used for qudi interfaces

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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""


def interface_overload(overload, interface):
    assert isinstance(overload, str)
    assert isinstance(interface, str)

    def decorator(func):
        setattr(func, '_interface_overload_mapping', (overload, interface))
        return func
    return decorator


class InterfaceAttributeMapper:
    def __init__(self, parent, map_dict):
        self.__map_dict = map_dict.copy()
        self.__parent = parent

    def __getitem__(self, key):
        mapped_attr = self.__map_dict.get(key, None)
        if mapped_attr is None:
            raise KeyError
        return mapped_attr.__get__(self.__parent)

    def __setitem__(self, key, value):
        mapped_attr = self.__map_dict.get(key, None)
        if mapped_attr is None:
            raise KeyError
        if hasattr(mapped_attr, '__set__'):
            mapped_attr.__set__(self.__parent, value)
        else:
            self.__map_dict[key] = value

    def __delitem__(self, key):
        mapped_attr = self.__map_dict.get(key, None)
        if mapped_attr is None:
            raise KeyError
        if hasattr(mapped_attr, '__delete__'):
            mapped_attr.__delete__(self.__parent)
        else:
            del self.__map_dict[key]


class ScalarConstraint:
    """
    Constraint definition for a scalar variable hardware parameter.
    """
    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit=''):
        # allowed minimum value for parameter
        self.min = min
        # allowed maximum value for parameter
        self.max = max
        # allowed step size for parameter value changes (for spinboxes etc.)
        self.step = step
        # the default value for the parameter
        self.default = default
        # the unit of the parameter value(optional)
        self.unit = unit
        return
