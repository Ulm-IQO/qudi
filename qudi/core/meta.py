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

__all__ = ('ABCQObjectMeta', 'ModuleMeta', 'QObjectMeta', 'QudiObjectMeta')

from abc import ABCMeta
from PySide2.QtCore import QObject
from qudi.core.statusvariable import StatusVar
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption


QObjectMeta = type(QObject)


class ABCQObjectMeta(ABCMeta, QObjectMeta):
    """ Metaclass for abstract QObject subclasses.
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


class QudiObjectMeta(ABCQObjectMeta):
    """ General purpose metaclass for abstract QObject subclasses that include qudi meta objects
    (Connector, StatusVar, ConfigOption).
    Collects all meta objects in new "_meta" class variable for easier access.
    """
    def __new__(mcs, name, bases, attributes):
        cls = super().__new__(mcs, name, bases, attributes)

        meta = dict()

        # Collect qudi module meta attributes (Connector, StatusVar, ConfigOption) and put them
        # in the class variable dict "_meta" for easy bookkeeping and access.
        connectors = dict()
        status_vars = dict()
        config_opt = dict()
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if isinstance(attr, Connector):
                connectors[attr_name] = attr
            elif isinstance(attr, StatusVar):
                status_vars[attr_name] = attr
            elif isinstance(attr, ConfigOption):
                config_opt[attr_name] = attr
        meta.update({'connectors'      : connectors,
                     'status_variables': status_vars,
                     'config_options'  : config_opt})
        setattr(cls, '_meta', meta)
        return cls


class ModuleMeta(QudiObjectMeta):
    """ Metaclass for all qudi modules (GUI, logic and hardware)
    """

    def __new__(mcs, name, bases, attributes):
        cls = super().__new__(mcs, name, bases, attributes)

        # Determine module base key and add to _meta dict
        if getattr(cls, '_meta', None):
            for base in cls.mro():
                if base.__name__ == 'GuiBase':
                    cls._meta['base'] = 'gui'
                    break
                elif base.__name__ == 'LogicBase':
                    cls._meta['base'] = 'logic'
                    break
                elif base.__name__ == 'Base':
                    cls._meta['base'] = 'hardware'
                    break
        return cls
