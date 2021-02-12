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

import weakref

__all__ = ('OverloadedAttribute', 'OverloadedAttributeMapper', 'ScalarConstraint')


class OverloadedAttributeMapper:
    def __init__(self):
        self._map_dict = dict()
        self._parent = lambda: None

    def add_mapping(self, key, obj):
        self._map_dict[key] = obj

    def remove_mapping(self, key):
        del self._map_dict[key]

    @property
    def parent(self):
        return self._parent()

    @parent.setter
    def parent(self, obj):
        self._parent = weakref.ref(obj)

    def get_mapped(self, key):
        if key not in self._map_dict:
            raise KeyError(f'No attribute overload found for key "{key}"')
        return self._map_dict[key]

    def __getitem__(self, key):
        mapped_obj = self.get_mapped(key)
        if hasattr(mapped_obj, '__get__'):
            return mapped_obj.__get__(self.parent)
        else:
            return mapped_obj

    def __setitem__(self, key, value):
        mapped_obj = self.get_mapped(key)
        if hasattr(mapped_obj, '__set__'):
            mapped_obj.__set__(self.parent, value)
        else:
            self._map_dict[key] = value

    def __delitem__(self, key):
        mapped_obj = self.get_mapped(key)
        if hasattr(mapped_obj, '__delete__'):
            mapped_obj.__delete__(self.parent)
        else:
            del self._map_dict[key]


class OverloadedAttribute:
    def __init__(self):
        self._attr_mapper = OverloadedAttributeMapper()

    def overload(self, key):
        def decorator(attr):
            self._attr_mapper.add_mapping(key, attr)
            return self
        return decorator

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        self._attr_mapper.parent = instance
        return self._attr_mapper

    def __set__(self, instance, value):
        raise AttributeError('can\'t set attribute')

    def __delete__(self, instance):
        raise AttributeError('can\'t delete attribute')

    def setter(self, key):
        obj = self._attr_mapper.get_mapped(key)

        def decorator(attr):
            self._attr_mapper.add_mapping(key, obj.setter(attr))
            return self

        return decorator

    def getter(self, key):
        obj = self._attr_mapper.get_mapped(key)

        def decorator(attr):
            self._attr_mapper.add_mapping(key, obj.getter(attr))
            return self

        return decorator

    def deleter(self, key):
        obj = self._attr_mapper.get_mapped(key)

        def decorator(attr):
            self._attr_mapper.add_mapping(key, obj.deleter(attr))
            return self

        return decorator


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
