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

import weakref
from qudi.util.overload import OverloadProxy


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
        self._obj_proxy = None
        self._obj_ref = lambda: None

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

    def __call__(self):
        """ Return reference to the module that this connector is connected to. """
        if self.is_connected:
            return self._obj_proxy
        if self.optional:
            return None
        raise RuntimeError(f'Connector {self.name} (interface {self.interface}) is not connected.')

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memodict={}):
        return self.copy()

    @property
    def is_connected(self):
        return self._obj_proxy is not None

    def connect(self, target):
        """ Check if target is connectible by this connector and connect."""
        if isinstance(self.interface, str):
            bases = [cls.__name__ for cls in target.__class__.mro()]
            if self.interface not in bases:
                raise RuntimeError(
                    f'Module {target} connected to connector {self.name} does not implement '
                    f'interface {self.interface}.'
                )
            self._obj_proxy = OverloadProxy(target, self.interface)
        elif isinstance(self.interface, type):
            if not isinstance(target, self.interface):
                raise RuntimeError(
                    f'Module {target} connected to connector {self.name} does not implement '
                    f'interface {self.interface.__name__}.'
                )
            self._obj_proxy = OverloadProxy(target, self.interface.__class__.__name__)
        else:
            raise RuntimeError(f'Unknown type for <Connector>.interface: "{type(self.interface)}"')
        self._obj_ref = weakref.ref(target, self.__module_died_callback)
        return

    def __module_died_callback(self, ref=None):
        self.disconnect()

    def disconnect(self):
        """ Disconnect connector. """
        self._obj_proxy = None

    # def __repr__(self):
    #     return '<{0}: name={1}, interface={2}, object={3}>'.format(
    #         self.__class__, self.name, self.ifname, self.obj)

    def copy(self, **kwargs):
        """ Create a new instance of Connector with copied values and update """
        newargs = {'name': self.name, 'interface': self.interface, 'optional': self.optional}
        newargs.update(kwargs)
        return Connector(**newargs)
