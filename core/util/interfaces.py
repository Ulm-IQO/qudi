# -*- coding: utf-8 -*-
"""
Metaclass for interfaces.

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


import abc
from qtpy.QtCore import QObject
from core.module import ModuleMeta

QObjectMeta = type(QObject)


class InterfaceMetaclass(ModuleMeta, abc.ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass


class TaskMetaclass(QObjectMeta, abc.ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass


class ScalarConstraint:
    """
    Constraint definition for a scalar variable hardware parameter.
    """
    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit=''):
        # allowed minimum value for parameter
        self.min = min
        # allowed maximum value for parameter
        self.max = max
        # allowed step size for parameter value changes (for spinboxes etc.)
        self.step = step
        # the default value for the parameter
        self.default = default
        # the unit of the parameter value(optional)
        self.unit = unit
        return


class InterfaceMethod:

    _latest_interface_method = None

    def __init__(self, default_callable, obj=None):
        self._obj = obj
        self._default_callable = default_callable
        self.registered = dict()
        self.__isabstractmethod__ = True
        InterfaceMethod._latest_interface_method = self

    def __get__(self, obj=None, cls=None):
        # It is executed when decorated func is referenced as a method: cls.func or obj.func.
        # if self.obj == obj and self.cls == cls:
        #     return self  # Use the same instance that is already processed by previous call to this __get__().

        # method_type = (
        #     'staticmethod' if isinstance(self._default_callable, staticmethod) else
        #     'classmethod' if isinstance(self._default_callable, classmethod) else
        #     'instancemethod'
        #     # No branch for plain function - correct method_type for it is already set in __init__() defaults.
        # )
        if obj is not None and obj is not self._obj:
            self._default_callable = self._default_callable.__get__(obj, cls)
            for interface in self.registered:
                self.registered[interface] = self.registered[interface].__get__(obj, cls)
        self._obj = obj
        # self.cls = cls
        # self.method_type = method_type
        return self
        # return object.__getattribute__(self, '__class__')(
        #     # Use specialized method_decorator (or descendant) instance, don't change current instance attributes - it leads to conflicts.
        #     self._default_callable.__get__(obj, cls), obj, cls,
        #     method_type)  # Use bound or unbound method with this underlying func.

    def __call__(self, *args, **kwargs):
        interface = kwargs.pop('interface', None)
        if interface and interface in self.registered:
            return self.registered[interface](*args, **kwargs)
        return self._default_callable(*args, **kwargs)

    # def __getattribute__(self, attr_name):  # Hiding traces of decoration.
    #     if attr_name in (
    #     '__init__', '__get__', '__call__', '__getattribute__', '_default_callable', 'registered', 'obj', 'cls', 'method_type', 'register'):  # Our known names. '__class__' is not included because is used only with explicit object.__getattribute__().
    #         return object.__getattribute__(self, attr_name)  # Stopping recursion.
    #     # All other attr_names, including auto-defined by system in self, are searched in decorated self.func, e.g.: __module__, __class__, __name__, __doc__, im_*, func_*, etc.
    #     return getattr(self._default_callable,
    #                    attr_name)  # Raises correct AttributeError if name is not found in decorated self.func.
    #
    def __repr__(self):  # Special case: __repr__ ignores __getattribute__.
        return self._default_callable.__repr__()

    @property
    def __isabstractmethod__(self):
        if hasattr(self._default_callable, '__isabstractmethod__'):
            return self._default_callable.__isabstractmethod__
        return False

    @__isabstractmethod__.setter
    def __isabstractmethod__(self, flag):
        self._default_callable.__isabstractmethod__ = bool(flag)

    @classmethod
    def register(cls, interface):
        def decorator(func):
            cls._latest_interface_method.registered[interface] = func
            cls._latest_interface_method.__isabstractmethod__ = False
            return func
        return decorator


def interface_method(func):
    return InterfaceMethod(func)
