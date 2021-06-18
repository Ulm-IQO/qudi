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
from functools import wraps
from inspect import signature, isfunction
from PySide2.QtCore import QObject
from qudi.core.statusvariable import StatusVar
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.util.network import net_copy_ndarray


QObjectMeta = type(QObject)


def _module_rpyc_argument_wrapper(func):
    sig = signature(func)
    if len(sig.parameters) > 0 and isinstance(func, staticmethod):

        @wraps(func)
        def wrapped(*args, **kwargs):
            sig.bind(*args, **kwargs)
            args = [net_copy_ndarray(arg) for arg in args]
            kwargs = {name: net_copy_ndarray(arg) for name, arg in kwargs.items()}
            return func(*args, **kwargs)
        wrapped.__signature__ = sig
        return wrapped
    elif len(sig.parameters) > 1:

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            sig.bind(self, *args, **kwargs)
            args = [net_copy_ndarray(arg) for arg in args]
            kwargs = {name: net_copy_ndarray(arg) for name, arg in kwargs.items()}
            return func(self, *args, **kwargs)
        wrapped.__signature__ = sig
        return wrapped
    return func


class ABCQObjectMeta(ABCMeta, QObjectMeta):
    """ Metaclass for abstract QObject subclasses.
    """

    def __new__(mcs, name, bases, attributes):
        module_bases = ('GuiBase', 'LogicBase', 'Base')
        if any(base.__name__ in module_bases for base in bases) and name not in module_bases:
            exclude_attrs = ('on_activate', 'on_deactivate', 'move_to_main_thread', 'show')
            for attr_name in list(attributes):
                attr = attributes[attr_name]
                if isfunction(attr) and attr_name not in exclude_attrs and attr_name[0] != '_':
                    attributes[attr_name] = _module_rpyc_argument_wrapper(attr)

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
