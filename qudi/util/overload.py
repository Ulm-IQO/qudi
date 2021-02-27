# -*- coding: utf-8 -*-
"""
Decorators and objects used for overloading attributes and interfacing them.

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

__all__ = ('OverloadedAttribute', 'OverloadedAttributeMapper', 'OverloadProxy')


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


class OverloadProxy:
    """ Instances of this class serve as proxies for objects containing attributes of type
    OverloadedAttribute. It can be used to hide the overloading mechanism by fixing the overloaded
    attribute access key in a OverloadProxy instance. This allows for interfacing an overloaded
    attribute in the object represented by this proxy by normal "pythonic" means without the
    additional key-mapping lookup usually required by OverloadedAttribute.

    Heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_obj_ref', '_overload_key', '__weakref__']

    def __init__(self, obj, overload_key):
        object.__setattr__(self, '_obj_ref', weakref.ref(obj))
        object.__setattr__(self, '_overload_key', overload_key)

    # proxying (special cases)
    def __getattribute__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if isinstance(attr, OverloadedAttributeMapper):
            return attr[object.__getattribute__(self, '_overload_key')]
        return attr

    def __delattr__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if isinstance(attr, OverloadedAttributeMapper):
            del attr[object.__getattribute__(self, '_overload_key')]
        else:
            delattr(obj, name)

    def __setattr__(self, name, value):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if isinstance(attr, OverloadedAttributeMapper):
            attr[object.__getattribute__(self, '_overload_key')] = value
        else:
            setattr(obj, name, value)

    def __nonzero__(self):
        return bool(object.__getattribute__(self, '_obj_ref')())

    def __str__(self):
        return str(object.__getattribute__(self, '_obj_ref')())

    def __repr__(self):
        return repr(object.__getattribute__(self, '_obj_ref')())

    # factories
    _special_names = (
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', '__contains__',
        '__delitem__', '__delslice__', '__div__', '__divmod__', '__eq__', '__float__',
        '__floordiv__', '__ge__', '__getitem__', '__getslice__', '__gt__', '__hash__', '__hex__',
        '__iadd__', '__iand__', '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__',
        '__imod__', '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', '__long__',
        '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__oct__', '__or__',
        '__pos__', '__pow__', '__radd__', '__rand__', '__rdiv__', '__rdivmod__', '__reduce__',
        '__reduce_ex__', '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
        '__rxor__', '__setitem__', '__setslice__', '__sub__', '__truediv__', '__xor__', 'next',
    )

    @classmethod
    def _create_class_proxy(cls, theclass):
        """ creates a proxy for the given class
        """

        def make_method(name):
            def method(self, *args, **kw):
                return getattr(object.__getattribute__(self, '_obj_ref')(), name)(*args, **kw)

            return method

        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name) and not hasattr(cls, name):
                namespace[name] = make_method(name)
        return type(f'{cls.__name__}({theclass.__name__})', (cls,), namespace)

    def __new__(cls, obj, overload_key, *args, **kwargs):
        """ creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are passed to this
        class' __init__, so deriving classes can define an __init__ method of their own.

        note: _class_proxy_cache is unique per class (each deriving class must hold its own cache)
        """
        try:
            cache = cls.__dict__['_class_proxy_cache']
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        ins = object.__new__(theclass)
        return ins