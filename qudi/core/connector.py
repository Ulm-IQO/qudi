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
from qudi.core.interface import OverloadedAttributeMapper


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
        raise Exception(f'Connector {self.name} (interface {self.interface}) is not connected.')

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
                raise Exception(f'Module {target} connected to connector {self.name} does not '
                                f'implement interface {self.interface}.')
        elif isinstance(self.interface, type):
            if not isinstance(target, self.interface):
                raise Exception(f'Module {target} connected to connector {self.name} does not '
                                f'implement interface {self.interface.__name__}.')
        else:
            raise Exception(f'Unknown type for <Connector>.interface: "{type(self.interface)}"')
        self._obj_proxy = _ConnectedInterfaceProxy(target, self.interface)
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


class _ConnectedInterfaceProxy:
    """ Instances of this class serve as proxies for qudi hardware modules to be able to hide
    overloaded attributes from the user when connecting via qudi.core.connector.Connector objects.

    Heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_obj_ref', '_interface', '__weakref__']

    def __init__(self, obj, interface):
        object.__setattr__(self, '_obj_ref', weakref.ref(obj))
        object.__setattr__(self, '_interface', interface)

    # proxying (special cases)
    def __getattribute__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if isinstance(attr, OverloadedAttributeMapper):
            return attr[object.__getattribute__(self, '_interface')]
        return attr

    def __delattr__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if isinstance(attr, OverloadedAttributeMapper):
            del attr[object.__getattribute__(self, '_interface')]
        else:
            delattr(obj, name)

    def __setattr__(self, name, value):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if isinstance(attr, OverloadedAttributeMapper):
            attr[object.__getattribute__(self, '_interface')] = value
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

    def __new__(cls, obj, interface, *args, **kwargs):
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
