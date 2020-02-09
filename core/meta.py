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
from qtpy.QtCore import QObject
from .connector import Connector
from .statusvariable import StatusVar
from .configoption import ConfigOption

QObjectMeta = type(QObject)


class ModuleMeta(QObjectMeta):
    """
    Metaclass for Qudi modules
    """

    def __new__(cls, name, bases, attrs):
        """ Collect declared Connectors, ConfigOptions and StatusVars into dictionaries.

        @param class cls: class
        @param str name: name of class
        @param list bases: list of base classes of class
        @param dict attrs: attributes of class

        @return class: new class with collected connectors
        """
        new_obj = super().__new__(cls, name, bases, attrs)
        if not hasattr(new_obj, '_module_meta'):
            return new_obj

        # collect meta objects into dicts
        connectors = dict()
        config_options = dict()
        status_vars = dict()

        # First collect all meta objects already present in the _module_meta dict (from bases)
        for attr_name, conn in new_obj._module_meta.pop('connectors', dict()).items():
            connectors[attr_name] = conn.copy() if conn.name else conn.copy(name=attr_name)
        for attr_name, svar in new_obj._module_meta.pop('status_variables', dict()).items():
            status_vars[attr_name] = svar.copy() if svar.name else svar.copy(name=attr_name)
        for attr_name, copt in new_obj._module_meta.pop('config_options', dict()).items():
            config_options[attr_name] = copt.copy() if copt.name else copt.copy(name=attr_name)

        # Then we add the new meta objects introduced in this class
        for attr_name, attr in attrs.items():
            if isinstance(attr, Connector):
                connectors[attr_name] = attr.copy() if attr.name else attr.copy(name=attr_name)
            elif isinstance(attr, StatusVar):
                status_vars[attr_name] = attr.copy() if attr.name else attr.copy(name=attr_name)
            elif isinstance(attr, ConfigOption):
                config_options[attr_name] = attr.copy() if attr.name else attr.copy(name=attr_name)

        # At last the collected meta objects are combined into a new _module_meta dict and attached
        # to the returned object
        meta_attr = {'connectors': connectors,
                     'status_variables': status_vars,
                     'config_options': config_options}
        new_obj._module_meta = meta_attr
        return new_obj


class TaskMetaclass(QObjectMeta, ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass


class InterfaceMetaclass(ModuleMeta, ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass
