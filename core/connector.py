# -*- coding: utf-8 -*-
"""
Connector object to establish connections between qudi modules.

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

import copy
import sys
from .interface import InterfaceMethod


class Connector:
    """ A connector where another module can be connected """

    def __init__(self, interface, *, name=None, optional=False):
        """
            @param name: name of the connector
            @param interface: interface class or name of the interface for this connector
            @param (bool) optional: the optionality of the connector
        """
        if not isinstance(interface, (str, type)):
            raise TypeError(
                'Parameter "interface" must be an interface class or the class name as str.')
        if name is not None and not isinstance(name, str):
            raise TypeError('Parameter "name" must be str type or None.')
        if not isinstance(optional, bool):
            raise TypeError('Parameter "optional" must be boolean.')
        self.interface = interface
        self.name = name
        self.optional = optional
        self.obj = None

    def __call__(self):
        """ Return reference to the module that this connector is connected to. """
        if self.obj is None:
            if self.optional:
                return None
            raise Exception(
                'Connector {0} (interface {1}) is not connected.'.format(self.name, self.interface))

        class ConnectedInterfaceProxy:
            """

            """
            def __getattribute__(*args):
                attr = getattr(self.obj, args[1])
                if isinstance(attr, InterfaceMethod):
                    return attr[self.interface]
                else:
                    return attr

            def __setattr__(*args):
                return setattr(self.obj, args[1], args[2])

            def __delattr__(*args):
                return delattr(self.obj, args[1])

            def __repr__(*args):
                return repr(self.obj)

            def __str__(*args):
                return str(self.obj)

            def __dir__(*args):
                return dir(self.obj)

            def __sizeof__(*args):
                return self.obj.__sizeof__()

        return ConnectedInterfaceProxy()

    @property
    def is_connected(self):
        return self.obj is not None

    def connect(self, target):
        """ Check if target is connectable by this connector and connect."""
        if isinstance(self.interface, str):
            bases = [cls.__name__ for cls in target.__class__.mro()]
            if self.interface not in bases:
                raise Exception(
                    'Module {0} connected to connector {1} does not implement interface {2}.'
                    ''.format(target, self.name, self.interface))

            self.obj = target
        elif isinstance(self.interface, type):
            if not isinstance(target, self.interface):
                raise Exception(
                    'Module {0} connected to connector {1} does not implement interface {2}.'
                    ''.format(target, self.name, self.interface.__name__))
            self.obj = target
        else:
            raise Exception(
                'Unknown type for <Connector>.interface: "{0}"'.format(type(self.interface)))
        return

    def disconnect(self):
        """ Disconnect connector. """
        self.obj = None

    # def __repr__(self):
    #     return '<{0}: name={1}, interface={2}, object={3}>'.format(
    #         self.__class__, self.name, self.ifname, self.obj)

    def copy(self, **kwargs):
        """ Create a new instance of Connector with copied values and update """
        newargs = {'name': copy.copy(self.name), 'interface': copy.copy(self.interface),
                   'optional': copy.copy(self.optional)}
        newargs.update(kwargs)
        return Connector(**newargs)
