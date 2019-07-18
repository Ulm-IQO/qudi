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
import inspect
from .interface import InterfaceMethod


class Connector:
    """ A connector where another module can be connected """

    def __init__(self, *, name=None, interface=None, optional=False):
        """
            @param name: name of the connector
            @param interface: interface class or name of the interface for this connector
            @param (bool) optional: the optionality of the connector
        """
        self.name = name
        self.interface = interface
        self.obj = None
        self.optional = optional

    def __call__(self):
        """ Return reference to the module that this connector is connected to. """
        if self.obj is None:
            if self.optional:
                return None
            raise Exception(
                'Connector {0} (interface {1}) is not connected.'
                ''.format(self.name, self.interface))

        class ConnectedInterfaceProxy:
            """

            """
            def __getattribute__(*args):
                attr = getattr(self.obj, args[1])
                if isinstance(attr, InterfaceMethod):
                    return attr[self.interface]
                else:
                    return attr
        return ConnectedInterfaceProxy()

    @property
    def is_connected(self):
        return self.obj is not None

    def connect(self, target):
        """ Check if target is connectable this connector and connect."""
        if isinstance(self.interface, str):
            bases = list(map(str, inspect.getmro(target.__class__)))

            interface_base = None
            for base in bases:
                if self.interface in base:
                    interface_base = base
                    break
            if interface_base is None:
                print('Warning: Incorrect interface "{0}" in the bases for connector "{1}". '
                      'Bases found: {2!s}'.format(self.interface, self.name, bases),
                      file=sys.stderr)

            self.obj = target
        else:
            if isinstance(target, self.interface):
                self.obj = target
            else:
                raise Exception(
                    'Module {0} connected to connector {1} does not implement interface {2}.'
                    ''.format(target, self.name, self.interface))

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
