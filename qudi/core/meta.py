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

__all__ = ('ABCQObjectMeta', 'ModuleMeta', 'QObjectMeta')

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


class ModuleMeta(ABCQObjectMeta):
    """ Metaclass for all qudi modules (GUI, logic and hardware)
    """

    def __new__(mcs, name, bases, attributes):
        cls = super().__new__(mcs, name, bases, attributes)

        meta = dict()
        # Determine module base key and add to _module_meta dict
        for base in cls.mro():
            if base.__name__ == 'GuiBase':
                meta['base'] = 'gui'
                break
            elif base.__name__ == 'LogicBase':
                meta['base'] = 'logic'
                break
            elif base.__name__ == 'Base':
                meta['base'] = 'hardware'
                break

        # Do not bother to collect meta attributes if created class is no subclass of Base
        if meta:
            # Collect qudi module meta attributes (Connector, StatusVar, ConfigOption) and put them
            # in the class dict "_module_meta" for easy bookkeeping and access.
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
            setattr(cls, '_module_meta', meta)
        return cls
