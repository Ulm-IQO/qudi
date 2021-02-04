# -*- coding: utf-8 -*-
"""
Definition of various metaclasses

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

from abc import ABCMeta
from PySide2.QtCore import QObject

__all__ = ('ABCQObjectMeta', 'InterfaceMeta', 'QObjectMeta')


QObjectMeta = type(QObject)


class ABCQObjectMeta(QObjectMeta, ABCMeta):
    """
    Metaclass for abstract QObject subclasses.
    """

    def __new__(mcs, name, bases, attributes):
        cls = super(ABCQObjectMeta, mcs).__new__(mcs, name, bases, attributes)
        # Compute set of abstract method names
        abstracts = {
            attr_name for attr_name, attr in attributes.items() if \
            getattr(attr, '__isabstractmethod__', False)
        }
        for base in bases:
            for attr_name in getattr(base, '__abstractmethods__', set()):
                attr = getattr(cls, attr_name, None)
                if getattr(attr, '__isabstractmethod__', False):
                    abstracts.add(attr_name)
        cls.__abstractmethods__ = frozenset(abstracts)
        return cls


class InterfaceMeta(ABCQObjectMeta):
    """

    """
    def __new__(mcs, name, bases, attributes):
        _attr_mapping = dict()
        for attr_name, attr in attributes.items():
            if isinstance(attr, property):
                mapping = getattr(attr.fget, '_interface_overload_mapping', None)
            else:
                mapping = getattr(attr, '_interface_overload_mapping', None)
            if mapping is not None:
                map_to, interface = mapping
                if map_to in _attr_mapping:
                    _attr_mapping[map_to][interface] = attr
                else:
                    _attr_mapping[map_to] = {interface: attr}
        cls = super(InterfaceMeta, mcs).__new__(mcs, name, bases, attributes)
        cls._meta_attribute_mapping = _attr_mapping
        abstract = getattr(cls, '__abstractmethods__', None)
        if abstract is not None:
            setattr(cls,
                    '__abstractmethods__',
                    frozenset(a for a in abstract if a in _attr_mapping))
        return cls
